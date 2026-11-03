#!/usr/bin/env python3

import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agents import coordinator_agent
from analysis.artifact_provenance import file_record, load_correctness_report, sha256
from scripts import promote_candidate as executor
from scripts import test_gate_contracts as fixtures
from scripts.test_toolchain import find_openmp_compiler


class CandidatePromotion(unittest.TestCase):
    def setUp(self):
        if find_openmp_compiler() is None:
            self.skipTest("An OpenMP compiler is required for promotion revalidation.")
        self.fixture = fixtures.GateContracts()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.work = self.fixture.work
        self.output = self.work / "promoted"
        self.decision_file = self.work / "decision.json"

    def prepare(self, candidate_time=0.5, one_thread_time=1.0):
        self.fixture.bind_performance(candidate_time=candidate_time, one_thread_time=one_thread_time)
        context = self.fixture.build_context()
        context_file = self.work / "context.json"
        context_file.write_text(json.dumps(context))
        recommended = context["performance"]["selection"].get("recommended") or {"threads": 2}
        threads = recommended["threads"]
        decision = {
            "schema": "tcc2-coordinator-decision", "version": "0.2", "model": "test-stub",
            "decision": {
                "decision": "ACCEPT", "next_action": "PROMOTE_CANDIDATE", "risk": "LOW",
                "recommended_threads": threads, "recommended_configuration": {"threads": threads},
            },
            "evidence": {
                "context": file_record(context_file), "candidate_id": context["source"]["candidate_id"],
                "campaign_id": context["source"]["campaign_id"],
            },
        }
        self.decision_file.write_text(json.dumps(decision))
        return decision

    def assert_blocked(self, error=ValueError):
        with patch.object(executor, "run_gate") as gate, self.assertRaises(error):
            executor.promote_candidate(self.decision_file, self.output)
        gate.assert_not_called()
        self.assertFalse(self.output.exists() and list(self.output.iterdir()))

    def test_valid_promotion_revalidates_and_archives_exact_bytes(self):
        self.prepare()
        original = self.fixture.candidate.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            published = executor.promote_candidate(self.decision_file, self.output)
        self.assertEqual((published / "parallel.c").read_bytes(), original)
        manifest = json.loads((published / "manifest.json").read_text())
        self.assertEqual(manifest["configuration"], {"threads": 2})
        self.assertEqual(manifest["candidate_sha256"], sha256(original))
        self.assertGreater(manifest["metrics"]["parallel_scaling_speedup"], 1)
        for name, identity in manifest["files"].items():
            self.assertEqual(sha256((published / name).read_bytes()), identity["sha256"], name)
        revalidation, _ = load_correctness_report(
            published / "revalidation.json", published / "evidence/sequential.c", published / "parallel.c",
        )
        self.assertEqual(revalidation["status"], "PASS")
        result = subprocess.run(manifest["reproduce_correctness"], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_retune_modify_reject_and_wrong_action_never_promote(self):
        original = self.prepare()
        for state, action in (("RETUNE", "RETUNE_CONFIGURATION"), ("MODIFY", "SEND_TO_CODER"),
                              ("REJECT", "REJECT_CANDIDATE"), ("ACCEPT", "RUN_MORE_BENCHMARKS")):
            decision = copy.deepcopy(original)
            decision["decision"].update(decision=state, next_action=action)
            self.decision_file.write_text(json.dumps(decision))
            with self.subTest(state=state):
                self.assert_blocked()

    def test_unmeasured_or_inconsistent_configuration_never_promotes(self):
        original = self.prepare()
        for threads, config in ((32, {"threads": 32}), (2, {"threads": 1}),
                                (2, None), (True, {"threads": True}), (2, {"threads": 2, "block_size": 64})):
            decision = copy.deepcopy(original)
            decision["decision"].update(recommended_threads=threads, recommended_configuration=config)
            self.decision_file.write_text(json.dumps(decision))
            with self.subTest(threads=threads, config=config):
                self.assert_blocked()

    def test_changed_candidate_driver_or_original_never_promotes(self):
        self.prepare()
        for path in (self.fixture.candidate, self.fixture.source, self.fixture.driver, self.fixture.benchmark_driver):
            original = path.read_bytes()
            path.write_bytes(original + b"\n/* changed */\n")
            with self.subTest(path=path):
                self.assert_blocked()
            path.write_bytes(original)

    def test_changed_decision_binding_or_context_never_promotes(self):
        original = self.prepare()
        for field in ("candidate_id", "campaign_id"):
            decision = copy.deepcopy(original)
            decision["evidence"][field] = "another-identity"
            self.decision_file.write_text(json.dumps(decision))
            with self.subTest(field=field):
                self.assert_blocked()
        self.decision_file.write_text(json.dumps(original))
        Path(original["evidence"]["context"]["path"]).write_text("{}")
        self.assert_blocked()

    def test_manual_pass_or_legacy_decision_never_promotes(self):
        self.prepare()
        self.fixture.report_path.write_text(json.dumps({"status": "PASS"}))
        self.assert_blocked()
        self.decision_file.write_text(json.dumps({"decision": "ACCEPT", "next_action": "PROMOTE_CANDIDATE"}))
        self.assert_blocked()

    def test_no_performance_gain_or_only_transformation_gain_never_promotes(self):
        for candidate_time, one_thread_time in ((2.0, 1.0), (0.5, 0.4)):
            self.prepare(candidate_time, one_thread_time)
            with self.subTest(candidate_time=candidate_time, one_thread_time=one_thread_time):
                self.assert_blocked()

    def test_fresh_gate_failure_leaves_no_final_artifact(self):
        self.prepare()
        with patch.object(executor, "run_gate", return_value={"status": "FAIL"}), self.assertRaisesRegex(ValueError, "revalidation failed"):
            executor.promote_candidate(self.decision_file, self.output)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_incorrect_code_with_fabricated_pass_is_rejected_by_real_gate(self):
        self.fixture.candidate.write_text(
            "double kernel_dot(int n, const double *a, const double *b) { return 0; }\n"
        )
        # The fixture fabricates consistent PASS records; fresh execution must still reject the code.
        self.prepare()
        with self.assertRaisesRegex(ValueError, "revalidation failed"):
            executor.promote_candidate(self.decision_file, self.output)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_timeout_or_copy_failure_leaves_no_final_artifact(self):
        self.prepare()
        with patch.object(executor, "run_gate", side_effect=subprocess.TimeoutExpired("gate", 120)), \
                self.assertRaises(subprocess.TimeoutExpired):
            executor.promote_candidate(self.decision_file, self.output)
        self.assertEqual(list(self.output.iterdir()), [])
        original_write = Path.write_bytes

        def fail_candidate(path, data):
            if path.name == "parallel.c":
                raise OSError("injected write failure")
            return original_write(path, data)

        with patch.object(Path, "write_bytes", fail_candidate), self.assertRaises(OSError):
            executor.promote_candidate(self.decision_file, self.output)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_candidate_change_during_revalidation_blocks_publication(self):
        self.prepare()
        actual_gate = executor.run_gate

        def change_after_gate(*args):
            result = actual_gate(*args)
            self.fixture.candidate.write_bytes(self.fixture.candidate.read_bytes() + b"\n/* changed */\n")
            return result

        with patch.object(executor, "run_gate", side_effect=change_after_gate), self.assertRaisesRegex(ValueError, "SHA-256"):
            executor.promote_candidate(self.decision_file, self.output)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_duplicate_promotion_preserves_existing_files(self):
        self.prepare()
        published = executor.promote_candidate(self.decision_file, self.output)
        original = (published / "manifest.json").read_bytes()
        with patch.object(executor, "run_gate") as gate, self.assertRaises(FileExistsError):
            executor.promote_candidate(self.decision_file, self.output)
        gate.assert_not_called()
        self.assertEqual((published / "manifest.json").read_bytes(), original)

    def test_path_traversal_and_symlink_destination(self):
        decision = self.prepare()
        identifier = executor.promotion_identifier("../../escape", "../../candidate")
        self.assertRegex(identifier, r"^[a-f0-9]{64}$")
        self.output.mkdir()
        outside = self.work / "outside"
        outside.mkdir()
        real_identifier = executor.promotion_identifier(decision["evidence"]["campaign_id"], decision["evidence"]["candidate_id"])
        (self.output / real_identifier).symlink_to(outside, target_is_directory=True)
        with patch.object(executor, "run_gate") as gate, self.assertRaises(FileExistsError):
            executor.promote_candidate(self.decision_file, self.output)
        gate.assert_not_called()
        self.assertEqual(list(outside.iterdir()), [])

    def test_coordinator_invokes_promotion_after_validated_accept(self):
        decision = self.prepare()
        context_file = Path(decision["evidence"]["context"]["path"])
        argv = ["coordinator_agent.py", str(context_file), "--output", str(self.decision_file),
                "--model", "test-stub", "--promote-to", str(self.output)]
        with patch.object(sys, "argv", argv), \
                patch.object(coordinator_agent, "call_ollama", return_value=(decision["decision"], {"model": "test-stub"})), \
                contextlib.redirect_stdout(io.StringIO()):
            coordinator_agent.main()
        manifests = list(self.output.glob("*/manifest.json"))
        self.assertEqual(len(manifests), 1)
        self.assertEqual(json.loads(manifests[0].read_text())["status"], "PROMOTED")


if __name__ == "__main__":
    unittest.main()
