"""Controlled responses verify the study machinery, not LLM research outcomes."""

import argparse
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.artifact_provenance import load_context_evidence
from scripts import evaluate_coordinator as evaluation
from scripts import test_gate_contracts as fixtures
from scripts.test_toolchain import find_openmp_compiler


class CoordinatorEvaluation(unittest.TestCase):
    def setUp(self):
        self.compiler = find_openmp_compiler()
        if self.compiler is None:
            self.skipTest("An OpenMP compiler is required for evidence fixtures.")
        self.fixture = fixtures.GateContracts()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.work = self.fixture.work
        self.prepare()

    def prepare(self, candidate_time=0.5, one_thread_time=1.0):
        self.fixture.bind_performance(candidate_time=candidate_time, one_thread_time=one_thread_time)
        self.context_file = self.work / "context.json"
        self.context_file.write_text(json.dumps(self.fixture.build_context()))
        self.context, self.bundle, _ = load_context_evidence(self.context_file)

    def response(self, name="ACCEPT", threads=2):
        return {"decision": name, "next_action": {"ACCEPT": "PROMOTE_CANDIDATE", "REJECT": "REJECT_CANDIDATE",
                "RETUNE": "RETUNE_CONFIGURATION", "MODIFY": "SEND_TO_CODER"}[name],
                "recommended_threads": threads if name == "ACCEPT" else None,
                "recommended_configuration": None, "risk": "LOW", "reason": "Explicit test stub."}

    def trial(self, mode="coordinator", response=None, error=None):
        directory = self.work / ("trial-" + str(len(list(self.work.glob("trial-*")))))
        with patch.object(evaluation.coordinator, "call_ollama", side_effect=error,
                          return_value=(response if response is not None else self.response(),
                                        {"model": "test-stub", "eval_count": 10})) as call:
            result = evaluation.run_trial(self.context, self.bundle, mode, "test-stub", 2, directory)
        return result, call

    def args(self, baseline_only=False):
        return argparse.Namespace(contexts=[self.context_file], baseline_only=baseline_only,
                                  repetitions=2, seed=2026, model="test-stub", timeout=2,
                                  compiler=self.compiler, threads=[1, 2], output_dir=self.work / "evaluations")

    def test_all_modes_share_evidence_and_measured_result(self):
        before = copy.deepcopy(self.context)
        trials = [self.trial(mode)[0] for mode in evaluation.MODES]
        self.assertEqual(self.context, before)
        self.assertTrue(all(row["effective_accept"] for row in trials))
        self.assertEqual([row["speedup_vs_sequential"] for row in trials], [2.0] * 3)
        self.assertEqual([row["parallel_scaling_speedup"] for row in trials], [2.0] * 3)
        self.assertEqual([row["llm_calls"] for row in trials], [0, 1, 1])
        self.assertEqual([row["candidate_attempts"] for row in trials], [1, 1, 1])
        self.assertFalse(any(row["recovery_supported"] for row in trials))
        self.assertIsNone(trials[1]["raw_decision"]["recommended_configuration"])
        self.assertEqual(trials[1]["decision"]["recommended_configuration"], {"threads": 2})

    def test_ablation_changes_prompt_but_preserves_code_gates_and_measurements(self):
        full = evaluation.model_context(self.context, "coordinator")
        ablated = evaluation.model_context(self.context, "coordinator_without_analysis")
        self.assertNotEqual(evaluation.coordinator.build_user_prompt(full), evaluation.coordinator.build_user_prompt(ablated))
        for field in ("source", "validation", "performance", "agent_constraints"):
            self.assertEqual(full[field], ablated[field])
        for field in evaluation.ABLATION_FIELDS:
            self.assertEqual(ablated[field], {})
        result, _ = self.trial("coordinator_without_analysis")
        self.assertTrue(result["ablation_effective"])

    def test_no_gain_acceptance_is_blocked_and_counted(self):
        self.prepare(candidate_time=2.0, one_thread_time=2.0)
        baseline, call = self.trial("deterministic")
        call.assert_not_called()
        proposed, _ = self.trial()
        self.assertFalse(baseline["eligible"])
        self.assertTrue(proposed["nonadmissible_accept_proposal"])
        self.assertFalse(proposed["effective_accept"])
        self.assertEqual(proposed["speedup_vs_sequential"], 1.0)

    def test_transformation_gain_alone_is_not_parallel_admission(self):
        self.prepare(candidate_time=0.5, one_thread_time=0.4)
        result, _ = self.trial("deterministic")
        self.assertFalse(result["eligible"])
        self.assertFalse(result["effective_accept"])

    def test_unmeasured_or_boolean_threads_are_never_accepted(self):
        for threads in (99, True):
            result, _ = self.trial(response=self.response(threads=threads))
            self.assertFalse(result["effective_accept"])
            self.assertTrue(result["nonadmissible_accept_proposal"])

    def test_deferred_actions_do_not_claim_candidate_recovery(self):
        for name in ("RETUNE", "MODIFY", "REJECT"):
            result, _ = self.trial(response=self.response(name))
            self.assertFalse(result["effective_accept"])
            self.assertTrue(result["missed_eligible_opportunity"])
            self.assertIsNone(result["attempts_to_acceptable_candidate"])
            self.assertEqual(result["final_mode"], "sequential_fallback")

    def test_invalid_responses_and_timeouts_are_retained(self):
        for response in ([], {"decision": "UNKNOWN"}):
            result, _ = self.trial(response=response)
            self.assertIn(result["status"], ("INVALID", "ERROR"))
            self.assertFalse(result["effective_accept"])
        result, _ = self.trial(error=RuntimeError("OLLAMA_TIMEOUT"))
        self.assertEqual(result["status"], "TIMEOUT")
        result.update(case="dot", accounted_pipeline_seconds=None)
        group = evaluation.aggregate([result])[0]
        self.assertEqual(group["trials"], 1)
        self.assertEqual(group["failures"], 1)
        self.assertEqual(group["policy_agreement_rate"], 0)
        self.assertIsNone(group["median_accounted_pipeline_seconds"])

    def test_complete_campaign_order_evidence_and_output_are_reproducible(self):
        def execute():
            with patch.object(evaluation.coordinator, "call_ollama", return_value=(self.response(), {"model": "test-stub"})), \
                    contextlib.redirect_stdout(io.StringIO()):
                code, directory = evaluation.evaluate(self.args())
            self.assertEqual(code, 0)
            report = json.loads((directory / "results.json").read_text())
            self.assertEqual(report["status"], "COMPLETE")
            self.assertEqual(len(report["trials"]), 6)
            self.assertEqual(len(report["groups"]), 3)
            self.assertEqual(len({row["context_sha256"] for row in report["trials"]}), 1)
            self.assertTrue(all(row["accounted_pipeline_seconds"] is None for row in report["trials"]))
            self.assertTrue((directory / "report.md").is_file())
            self.assertEqual(len((directory / "trials.csv").read_text().splitlines()), 7)
            return [(row["repetition"], row["mode"], row["order_position"]) for row in report["trials"]]
        self.assertEqual(execute(), execute())

    def test_baseline_only_never_calls_llm_and_stays_pending(self):
        with patch.object(evaluation.coordinator, "call_ollama") as call, contextlib.redirect_stdout(io.StringIO()):
            code, directory = evaluation.evaluate(self.args(baseline_only=True))
        call.assert_not_called()
        self.assertEqual(code, 0)
        report = json.loads((directory / "results.json").read_text())
        self.assertEqual(report["status"], "BASELINE_ONLY")
        self.assertEqual(len(report["trials"]), 2)

    def test_inference_failure_keeps_all_trials_and_marks_incomplete(self):
        with patch.object(evaluation.coordinator, "call_ollama", side_effect=RuntimeError("OLLAMA_TIMEOUT")), \
                contextlib.redirect_stdout(io.StringIO()):
            code, directory = evaluation.evaluate(self.args())
        report = json.loads((directory / "results.json").read_text())
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "INCOMPLETE")
        self.assertEqual(len(report["trials"]), 6)
        self.assertEqual(sum(row["status"] == "TIMEOUT" for row in report["trials"]), 4)

    def test_ablation_without_prompt_change_cannot_complete_study(self):
        for field in evaluation.ABLATION_FIELDS:
            self.context.pop(field, None)
        self.context_file.write_text(json.dumps(self.context))
        with patch.object(evaluation.coordinator, "call_ollama", return_value=(self.response(), {})), \
                contextlib.redirect_stdout(io.StringIO()):
            code, directory = evaluation.evaluate(self.args())
        report = json.loads((directory / "results.json").read_text())
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "INCOMPLETE")
        self.assertTrue(any(row.get("ablation_effective") is False for row in report["trials"]))

    def test_changed_evidence_aborts_instead_of_publishing_stale_results(self):
        def tamper(*args):
            self.fixture.candidate.write_text("changed")
            return self.response(), {"model": "test-stub"}
        with patch.object(evaluation.coordinator, "call_ollama", side_effect=tamper), \
                contextlib.redirect_stdout(io.StringIO()):
            code, directory = evaluation.evaluate(self.args())
        report = json.loads((directory / "results.json").read_text())
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "FAILED")
        self.assertIn("error", report)


if __name__ == "__main__":
    unittest.main()
