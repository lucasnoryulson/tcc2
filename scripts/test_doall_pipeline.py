"""Regression coverage for the conservative single-loop DOALL path."""

import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis import code_transformer, strategy_planner
from analysis.artifact_provenance import load_context_evidence
from scripts.run_pipeline import run_pipeline
from scripts.test_toolchain import find_openmp_compiler


class DoallPipeline(unittest.TestCase):
    def test_planner_authorizes_only_one_unambiguous_candidate(self):
        one = {"loops": [{"classification": "DOALL_CANDIDATE", "loop_id": 1,
                           "iterator": "i", "confidence": "medium"}]}
        plan = strategy_planner.plan_doall(one, {1: {"depth": 0}})
        self.assertTrue(plan["direct_code_transformation"])
        self.assertEqual(plan["selected_loop"]["loop_id"], 1)

        two = {"loops": one["loops"] + [{"classification": "DOALL_CANDIDATE",
                                           "loop_id": 2, "iterator": "j",
                                           "confidence": "medium"}]}
        plan = strategy_planner.plan_doall(two, {1: {"depth": 0}, 2: {"depth": 1}})
        self.assertFalse(plan["direct_code_transformation"])
        self.assertIsNone(plan["selected_loop"])

    def test_transformer_rejects_ambiguous_or_unapproved_doall(self):
        source = ["void f(int n, double *a) {\n", "  for (int i=0;i<n;i++) a[i]=i;\n", "}\n"]
        static = {"loops": [{"id": 1, "start_line": 2}]}
        base = {"strategy": "DOALL", "schedule": "static", "selected_loop": {"loop_id": 1},
                "candidate_loops": [{"loop_id": 1}], "direct_code_transformation": False}
        with self.assertRaisesRegex(RuntimeError, "não autorizou"):
            code_transformer.apply_strategy(list(source), static, base)
        ambiguous = dict(base, direct_code_transformation=True,
                         candidate_loops=[{"loop_id": 1}, {"loop_id": 2}])
        with self.assertRaisesRegex(RuntimeError, "exatamente um"):
            code_transformer.apply_strategy(list(source), static, ambiguous)

    def test_real_axpy_pipeline_builds_verified_context(self):
        compiler = find_openmp_compiler()
        if compiler is None:
            self.skipTest("An OpenMP compiler is required.")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = argparse.Namespace(
                source=ROOT / "analysis/fixtures/axpy.c",
                driver=ROOT / "analysis/fixtures/axpy_driver.c",
                benchmark_driver=ROOT / "analysis/fixtures/axpy_benchmark_driver.c",
                compiler=compiler,
                threads=[1, 2],
                model="unused",
                timeout=30,
                prepare_only=True,
                work_dir=root / "work",
                output_dir=root / "promoted",
            )
            code, work = run_pipeline(args)
            self.assertEqual(code, 0)
            summary = json.loads((work / "summary.json").read_text())
            self.assertEqual(summary["status"], "PREPARED")
            candidate = (work / "candidate.c").read_text()
            self.assertIn("TCC2 AUTO-GENERATED: DOALL", candidate)
            self.assertIn("#pragma omp parallel for schedule(static)", candidate)
            context, bundle, _ = load_context_evidence(work / "context.json")
            self.assertEqual(context["validation"]["correctness_gate"], "PASS")
            self.assertEqual(context["pattern"]["classification"], "DOALL_CANDIDATE")
            self.assertEqual(bundle["correctness"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
