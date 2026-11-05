"""Check campaign isolation, metric denominators and honest evidence classification."""

import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import consolidate_experiments as consolidation
from scripts import test_gate_contracts as fixtures
from scripts import benchmark, autotune_wavefront
from scripts.test_toolchain import find_openmp_compiler


class ExperimentConsolidation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def rows(self, block=None):
        rows = [{"mode": mode, "threads": threads, "median_seconds": seconds, "mean_seconds": seconds}
                for mode, threads, seconds in (("sequential", 1, 12), ("openmp", 1, 6), ("openmp", 2, 2))]
        if block:
            for row in rows[1:]:
                row["block_size"] = block
        return rows

    def test_sequential_speedup_scaling_and_efficiency_have_distinct_baselines(self):
        selected = consolidation.normalize(self.rows())[-1]
        self.assertEqual(selected["speedup"], 6)
        self.assertEqual(selected["parallel_scaling_speedup"], 3)
        self.assertEqual(selected["parallel_scaling_efficiency"], 1.5)
        self.assertEqual(selected["efficiency"], 3)

    def test_tiled_scaling_uses_same_block_size_instead_of_fastest_other_variant(self):
        rows = self.rows(64)
        rows.append({"mode": "openmp", "threads": 1, "block_size": 16, "median_seconds": 1.0, "mean_seconds": 1.0})
        selected = next(row for row in consolidation.normalize(rows) if row["threads"] == 2)
        self.assertEqual(selected["parallel_scaling_speedup"], 3)

    def test_multiple_baselines_duplicate_configs_and_nonfinite_times_are_rejected(self):
        for rows in (self.rows() + self.rows(), self.rows() + [self.rows()[1]],
                     [dict(row, median_seconds=float("nan")) for row in self.rows()]):
            with self.assertRaises(ValueError):
                consolidation.normalize(rows)

    def test_absent_one_thread_is_unknown_instead_of_invented_scaling(self):
        rows = consolidation.normalize([self.rows()[0], self.rows()[2]])
        self.assertIsNone(rows[-1]["parallel_scaling_speedup"])
        self.assertIsNone(rows[-1]["parallel_scaling_efficiency"])

    def test_csv_with_appended_different_schema_is_rejected_and_inventoried(self):
        results = self.work / "results"
        results.mkdir()
        path = results / "mixed.csv"
        path.write_text("version,threads,median_seconds\nsequential,1,1\nexact,openmp,2,0.5\n")
        with self.assertRaises(ValueError):
            consolidation.csv_rows(path)
        record = consolidation.inventory(self.work, self.work / "output")[0]
        self.assertIn("HEADER_MISMATCH lines 3", record["issues"])

    def test_duplicate_inventory_files_are_identified_without_pooling(self):
        results = self.work / "results"
        results.mkdir()
        first = results / "a.csv"
        first.write_text("mode,threads,seconds\nsequential,1,1\n")
        (results / "b.csv").write_bytes(first.read_bytes())
        records = consolidation.inventory(self.work, self.work / "output")
        self.assertEqual(records[1]["duplicate_of"], "results/a.csv")

    def test_raw_logs_recover_individual_samples_and_reject_duplicate_runs(self):
        path = self.work / "raw.txt"
        path.write_text("SEQ Run=1 Time=2s\nSEQ Run=2 Time=4s\n1T Run=1 Time=1s\n")
        rows = consolidation.raw_measurements(path, "harness_log")
        normalized = consolidation.normalize(rows)
        self.assertEqual(normalized[0]["sample_count"], 2)
        self.assertEqual(normalized[0]["median_seconds"], 3)
        self.assertEqual(normalized[0]["std_dev_seconds"], 1)
        path.write_text(path.read_text() + "SEQ Run=1 Time=9s\n")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            consolidation.raw_measurements(path, "harness_log")

    def test_nan_and_missing_run_identifiers_in_logs_are_not_silently_dropped(self):
        path = self.work / "raw.txt"
        for content in ("SEQ Run=1 Time=nans\n", "SEQ Run=1 Time=1s\nSEQ Run=3 Time=3s\n"):
            path.write_text(content)
            with self.assertRaises(ValueError):
                consolidation.raw_measurements(path, "harness_log")

    def test_summary_raw_disagreement_is_rejected(self):
        path = self.work / "data.csv"
        path.write_text("mode,threads,median_seconds,mean_seconds\nsequential,1,10,10\nopenmp,1,5,5\n")
        (self.work / "raw.txt").write_text("SEQ Run=1 Time=10s\n1T Run=1 Time=9s\n")
        with self.assertRaisesRegex(ValueError, "disagree"):
            consolidation.load_campaign({"source": "data.csv", "format": "normalized_csv", "raw_source": "raw.txt"}, self.work)

    def test_explicit_timestamp_does_not_mix_campaigns(self):
        path = self.work / "data.csv"
        path.write_text("timestamp,version,threads,median_seconds,mean_seconds\n"
                        "old,sequential,1,100,100\nold,openmp,1,1,1\n"
                        "new,sequential,1,12,12\nnew,openmp,1,6,6\nnew,openmp,2,2,2\n")
        rows, _, selected, status, _ = consolidation.load_campaign(
            {"source": "data.csv", "format": "normalized_csv", "timestamp": "new"}, self.work)
        self.assertEqual(len(rows), 3)
        self.assertEqual(selected["speedup"], 6)
        self.assertEqual(status, "HISTORICAL_UNBOUND")

    def test_archived_local_summary_is_not_treated_as_verified_without_original_files(self):
        archived = {"cases": [{"case": "dot", "measurements": self.rows(),
                                "context": {"path": str(self.work / "missing.json"), "sha256": "x"}}]}
        (self.work / "summary.json").write_text(json.dumps(archived))
        _, _, _, status, provenance = consolidation.load_campaign(
            {"source": "summary.json", "format": "evaluation_case", "case": "dot"}, self.work)
        self.assertEqual(status, "ARCHIVED_SUMMARY_ONLY")
        self.assertIsNone(provenance)

    def test_tampered_local_evidence_aborts_instead_of_becoming_historical(self):
        if find_openmp_compiler() is None:
            self.skipTest("An OpenMP compiler is required for the fixture.")
        fixture = fixtures.GateContracts()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.bind_performance()
        context = fixture.work / "context.json"
        context.write_text(json.dumps(fixture.build_context()))
        from analysis.artifact_provenance import file_record
        archived = {"cases": [{"case": "dot", "context": file_record(context), "measurements": self.rows()}]}
        (self.work / "summary.json").write_text(json.dumps(archived))
        fixture.candidate.write_text("tampered")
        with self.assertRaises(ValueError):
            consolidation.load_campaign({"source": "summary.json", "format": "evaluation_case", "case": "dot"}, self.work)

    def test_direct_context_evidence_is_verified_and_keeps_samples(self):
        if find_openmp_compiler() is None:
            self.skipTest("An OpenMP compiler is required for the fixture.")
        fixture = fixtures.GateContracts()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.bind_performance()
        context = fixture.work / "context.json"
        context.write_text(json.dumps(fixture.build_context()))
        rows, _, _, status, provenance = consolidation.load_campaign(
            {"source": str(context.relative_to(context.anchor)), "format": "context_evidence"},
            Path(context.anchor),
        )
        self.assertEqual(status, "VERIFIED_LOCAL_GATES")
        self.assertIsNotNone(provenance)
        self.assertTrue(all(row["sample_count"] for row in rows))

    def test_output_cannot_overwrite_source_or_follow_output_symlink(self):
        source = self.work / "source.csv"
        source.write_text("preserve me")
        output = self.work / "output"
        output.mkdir()
        (output / "matrix.csv").symlink_to(source)
        with patch.object(sys, "argv", ["consolidate", "--output-dir", str(output)]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(consolidation.main(), 1)
        self.assertEqual(source.read_text(), "preserve me")

    def test_repository_catalog_has_expected_coverage_and_keeps_sources_unchanged(self):
        catalog = json.loads((ROOT / "docs/experiment_catalog.json").read_text())
        paths = {ROOT / case[field] for case in catalog["campaigns"] for field in ("source", "archived_summary")
                 if case.get(field) and (ROOT / case[field]).is_file()}
        before = {path: path.read_bytes() for path in paths}
        campaigns = consolidation.consolidate(catalog, ROOT)
        self.assertEqual(len(campaigns), 22)
        self.assertTrue({"gemm", "dot", "jacobi-2d", "covariance", "nussinov", "wavefront"}.issubset({case["kernel"] for case in campaigns}))
        self.assertTrue(all(case["evidence_status"] == "HISTORICAL_UNBOUND" for case in campaigns
                            if case["format"] not in ("evaluation_case", "context_evidence")))
        nussinov = next(case for case in campaigns if case["id"] == "nussinov_auto_0911")
        self.assertAlmostEqual(nussinov["selected"]["parallel_scaling_efficiency"], 0.7513, places=4)
        self.assertEqual({path: path.read_bytes() for path in paths}, before)

    def test_explicit_archived_context_is_not_relabelled_as_verified(self):
        from analysis.artifact_provenance import sha256
        archived = self.work / 'archived.json'
        archived.write_text(json.dumps({'campaigns': [{'id': 'fixture', 'measurements': self.rows()}]}))
        spec = dict(id='fixture', source='missing.json', format='context_evidence',
                    archived_summary='archived.json', archived_summary_sha256=sha256(archived.read_bytes()))
        rows, _, _, status, provenance = consolidation.load_campaign(spec, self.work)
        self.assertEqual(status, 'ARCHIVED_SUMMARY_ONLY')
        self.assertIsNone(provenance)
        self.assertEqual(rows[0]['median_seconds'], 12)
        archived.write_text(archived.read_text() + ' ')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            consolidation.load_campaign(spec, self.work)

    def test_invalid_present_context_does_not_fall_back_to_archived_summary(self):
        (self.work / 'context.json').write_text('{}')
        spec = dict(id='fixture', source='context.json', format='context_evidence', archived_summary='absent.json')
        with self.assertRaises(ValueError):
            consolidation.load_campaign(spec, self.work)

    def test_harness_rejects_incompatible_historical_header_before_compiling(self):
        result = self.work / "results/gemm/experiment_results.csv"
        result.parent.mkdir(parents=True)
        result.write_text("timestamp,benchmark,version,threads\nold,gemm,sequential,1\n")
        before = result.read_bytes()
        with patch.object(benchmark, "PROJECT_ROOT", self.work), patch.object(sys, "argv", ["benchmark", "gemm"]), \
                patch.object(benchmark, "compile_program") as compile_program, \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            benchmark.main()
        compile_program.assert_not_called()
        self.assertEqual(result.read_bytes(), before)

    def test_both_harnesses_refuse_to_overwrite_explicit_campaign_directory(self):
        for module, filename, positional in ((benchmark, "experiment_results.csv", ["dot"]),
                                             (autotune_wavefront, "tiled_autotuning.csv", [])):
            target = self.work / filename
            target.write_text("preserve me")
            with patch.object(module, "RESULTS_DIR", self.work, create=True), \
                    patch.object(module, "CSV_FILE", self.work / "unused", create=True), \
                    patch.object(sys, "argv", ["harness", *positional, "--results-dir", str(self.work)]), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                module.main()
            self.assertEqual(target.read_text(), "preserve me")

    def test_harness_scaling_uses_actual_one_thread_even_when_thread_order_differs(self):
        def stats(value):
            return {"mean": value, "median": value, "std_dev": 0, "min": value, "max": value}
        output = self.work / "campaign"
        with patch.object(benchmark, "PROJECT_ROOT", self.work), patch.object(benchmark, "THREAD_COUNTS", [2, 1]), \
                patch.object(benchmark, "compile_program", return_value=True), \
                patch.object(benchmark, "validate_candidate", return_value=True), \
                patch.object(benchmark, "run_timed", side_effect=[stats(12), stats(2), stats(6)]), \
                patch.object(sys, "argv", ["benchmark", "dot", "--results-dir", str(output)]), \
                contextlib.redirect_stdout(io.StringIO()):
            benchmark.main()
        rows = consolidation.csv_rows(output / "experiment_results.csv")
        selected = next(row for row in rows if row["threads"] == "2")
        self.assertEqual(float(selected["scaling_speedup"]), 3)
        self.assertEqual(float(selected["speedup_vs_sequential"]), 6)
        self.assertEqual(set(rows[0]), set(benchmark.CSV_COLUMNS))

    def test_cli_generates_complete_tables_and_samples_without_plotting_dependency(self):
        output = self.work / "report"
        result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/consolidate_experiments.py"),
                                 "--no-plots", "--output-dir", str(output)], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((output / "report.json").read_text())
        self.assertEqual(len(report["campaigns"]), 22)
        self.assertEqual(len(consolidation.csv_rows(output / "matrix.csv")), 22)
        self.assertGreater(len(consolidation.csv_rows(output / "samples.csv")), 100)
        self.assertFalse(report["plots"]["files"])
        self.assertTrue((output / "REPORT.md").is_file())


if __name__ == "__main__":
    unittest.main()
