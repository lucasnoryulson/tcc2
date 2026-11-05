#!/usr/bin/env python3

import argparse
import contextlib
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
from scripts import run_pipeline as pipeline
from scripts import test_gate_contracts as fixtures
from scripts.test_toolchain import find_openmp_compiler


class PipelineIntegration(unittest.TestCase):
    def setUp(self):
        compiler = find_openmp_compiler()
        if compiler is None or shutil.which("clang") is None:
            self.skipTest("Clang and an OpenMP compiler are required for pipeline integration.")
        self.fixture = fixtures.GateContracts()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.work = self.fixture.work
        # These controlled times test pipeline behavior, not measured speedup.
        self.fixture.benchmark_driver.write_text(
            '#include <stdio.h>\n#include <stdlib.h>\nint main(void) {\n'
            '#ifdef _OPENMP\n'
            'puts(atoi(getenv("OMP_NUM_THREADS")) == 1 ? "AVERAGE_SECONDS=1.0" : "AVERAGE_SECONDS=0.5");\n'
            '#else\nputs("AVERAGE_SECONDS=2.0");\n#endif\nreturn 0;\n}\n'
        )
        self.args = argparse.Namespace(
            source=self.fixture.source, driver=self.fixture.driver,
            benchmark_driver=self.fixture.benchmark_driver,
            compiler=compiler, threads=[1, 2], model="test-stub", timeout=30,
            work_dir=self.work / "runs", output_dir=self.work / "promoted",
        )

    def execute(self, decision_name="ACCEPT"):
        actual_run = subprocess.run
        self.coordinator_calls = 0

        def with_local_coordinator(command, **kwargs):
            if len(command) < 3 or Path(str(command[2])).name != "coordinator_agent.py":
                return actual_run(command, **kwargs)
            self.coordinator_calls += 1
            context = json.loads(Path(command[3]).read_text())
            decision = {
                "decision": decision_name, "risk": "LOW", "reason": "Integration test stub.",
                "recommended_configuration": None, "evidence_used": ["test_stub"],
                "recommended_threads": context["performance"]["selection"]["recommended"]["threads"] if decision_name == "ACCEPT" else None,
                "next_action": "PROMOTE_CANDIDATE" if decision_name == "ACCEPT" else "REJECT_CANDIDATE",
            }
            output = io.StringIO()
            with patch.object(sys, "argv", list(map(str, command[2:]))), \
                    patch.object(coordinator_agent, "call_ollama", return_value=(decision, {"model": "test-stub"})), \
                    contextlib.redirect_stdout(output):
                coordinator_agent.main()
            return subprocess.CompletedProcess(command, 0, output.getvalue(), "")

        with patch.object(pipeline.subprocess, "run", side_effect=with_local_coordinator), \
                contextlib.redirect_stdout(io.StringIO()):
            return pipeline.run_pipeline(self.args)

    def test_full_pipeline_generates_revalidated_final_artifact(self):
        code, work = self.execute()
        self.assertEqual(code, 0, (work / "summary.json").read_text())
        self.assertEqual(self.coordinator_calls, 1)
        summary = json.loads((work / "summary.json").read_text())
        self.assertEqual(summary["status"], "PROMOTED")
        self.assertEqual([step["name"] for step in summary["steps"]], [
            "static", "dependences", "patterns", "strategy", "transform", "correctness",
            "performance", "selection", "context", "coordinator", "promotion",
        ])
        manifest_path = Path(summary["manifest"]["path"])
        self.assertEqual((manifest_path.parent / "parallel.c").read_bytes(), (work / "candidate.c").read_bytes())
        self.assertEqual(json.loads(manifest_path.read_text())["configuration"], {"threads": 2})

    def test_coordinator_rejection_stops_without_promotion(self):
        code, work = self.execute("REJECT")
        self.assertEqual(code, 1)
        summary = json.loads((work / "summary.json").read_text())
        self.assertEqual(summary["status"], "NOT_PROMOTED")
        self.assertEqual(summary["next_action"], "REJECT_CANDIDATE")
        self.assertFalse(self.args.output_dir.exists())

    def test_gate_failure_stops_before_coordinator(self):
        self.args.compiler = str(self.work / "missing-compiler")
        code, work = self.execute()
        self.assertEqual(code, 1)
        self.assertEqual(self.coordinator_calls, 0)
        summary = json.loads((work / "summary.json").read_text())
        self.assertEqual(summary["status"], "FAILED")
        self.assertEqual(summary["steps"][-1]["name"], "correctness")
        self.assertFalse(self.args.output_dir.exists())

    def test_prepare_only_measures_without_calling_coordinator_or_promoting(self):
        self.args.prepare_only = True
        code, work = self.execute()
        summary = json.loads((work / "summary.json").read_text())
        self.assertEqual(code, 0)
        self.assertEqual(summary["status"], "PREPARED")
        self.assertEqual(self.coordinator_calls, 0)
        self.assertEqual(Path(summary["context"]["path"]), work / "context.json")
        self.assertGreater(summary["elapsed_seconds"], 0)
        self.assertTrue(all(step["wall_seconds"] > 0 for step in summary["steps"]))
        self.assertFalse(self.args.output_dir.exists())

    def test_timeout_preserves_failed_stage_and_elapsed_time(self):
        with patch.object(pipeline.subprocess, "run", side_effect=subprocess.TimeoutExpired("static", 300)), \
                contextlib.redirect_stdout(io.StringIO()):
            code, work = pipeline.run_pipeline(self.args)
        summary = json.loads((work / "summary.json").read_text())
        self.assertEqual(code, 1)
        self.assertEqual(summary["status"], "FAILED")
        self.assertEqual(summary["steps"][0]["name"], "static")
        self.assertIsNone(summary["steps"][0]["returncode"])
        self.assertGreater(summary["steps"][0]["wall_seconds"], 0)
        self.assertTrue(Path(summary["steps"][0]["log"]).is_file())


if __name__ == "__main__":
    unittest.main()
