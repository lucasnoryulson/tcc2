"""Unit tests for Coordinator output contracts and controlled scenarios."""

import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agents import coordinator_agent as coordinator
from scripts import evaluate_coordinator_scenarios as scenarios


def response(decision, action):
    return {
        "decision": decision,
        "recommended_threads": 2 if decision == "ACCEPT" else None,
        "recommended_configuration": None,
        "reason": "Controlled test response.",
        "next_action": action,
        "risk": "LOW",
        "evidence_used": ["controlled_fixture"],
    }


class CoordinatorScenarioTests(unittest.TestCase):
    def test_schema_declares_complete_configuration_contract(self):
        schema = coordinator.DECISION_SCHEMA
        self.assertIn("recommended_configuration", schema["properties"])
        self.assertIn("recommended_configuration", schema["required"])
        self.assertNotIn("oneOf", schema)
        self.assertIn("null", schema["properties"]["recommended_threads"]["type"])
        self.assertIn("null", schema["properties"]["recommended_configuration"]["type"])

    def test_prompt_spells_out_reject_null_contract(self):
        prompt = coordinator.build_user_prompt(scenarios.base_context())
        self.assertIn("REJECT -> REJECT_CANDIDATE", prompt)
        self.assertIn("recommended_configuration must both be null", prompt)

    def test_nonaccept_operational_configuration_is_invalid(self):
        context = scenarios.base_context()
        for name, action in (("REJECT", "REJECT_CANDIDATE"),
                             ("RETUNE", "RETUNE_CONFIGURATION"),
                             ("MODIFY", "SEND_TO_CODER")):
            decision = response(name, action)
            decision["recommended_threads"] = 2
            decision["recommended_configuration"] = {"threads": 2}
            errors = coordinator.validate_decision(decision, context)
            self.assertIn(f"{name} requires recommended_threads to be null", errors)
            self.assertIn(f"{name} requires recommended_configuration to be null", errors)

    def test_accept_without_selector_recommendation_is_invalid(self):
        context = scenarios.base_context()
        context["performance"]["selection"].update(
            status="INSUFFICIENT_CONFIGURATIONS", recommended=None
        )
        errors = coordinator.validate_decision(
            response("ACCEPT", "PROMOTE_CANDIDATE"), context
        )
        self.assertIn(
            "ACCEPT requires performance selection status SELECTED with a recommended configuration",
            errors,
        )

    def test_each_scenario_accepts_its_expected_response(self):
        actions = {
            "accept": ("ACCEPT", "PROMOTE_CANDIDATE"),
            "reject": ("REJECT", "REJECT_CANDIDATE"),
            "retune": ("RETUNE", "RUN_MORE_BENCHMARKS"),
            "modify": ("MODIFY", "SEND_TO_DEBUGGER"),
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, (context, expected, expected_actions) in scenarios.scenarios().items():
                decision, action = actions[name]
                with patch.object(scenarios.coordinator, "call_ollama",
                                  return_value=(response(decision, action), {"model": "stub"})):
                    trial = scenarios.run_trial(name, context, expected, expected_actions,
                                                "coordinator", "stub", 1, root / name)
                self.assertEqual(trial["status"], "OK")
                self.assertTrue(trial["oracle_match"])

    def test_campaign_retains_all_modes_and_scenarios(self):
        mapping = {
            "accept": response("ACCEPT", "PROMOTE_CANDIDATE"),
            "reject": response("REJECT", "REJECT_CANDIDATE"),
            "retune": response("RETUNE", "RETUNE_CONFIGURATION"),
            "modify": response("MODIFY", "SEND_TO_DEBUGGER"),
        }

        def fake_call(model, context, timeout):
            if context.get("validation", {}).get("correctness_gate") == "FAIL":
                name = "modify"
            else:
                status = context.get("performance", {}).get("selection", {}).get("status")
                name = {"SELECTED": "accept", "NO_BENEFICIAL_CONFIGURATION": "reject",
                        "INSUFFICIENT_CONFIGURATIONS": "retune"}.get(status)
                if name is None:
                    # The ablation deliberately removes analysis but preserves performance.
                    name = "accept"
            return mapping[name], {"model": "stub"}

        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(scenarios.coordinator, "call_ollama", side_effect=fake_call), \
                contextlib.redirect_stdout(io.StringIO()):
            args = argparse.Namespace(model="stub", timeout=1, repetitions=1, seed=2026,
                                      output_dir=Path(temporary))
            code, directory = scenarios.evaluate(args)
            report = json.loads((directory / "results.json").read_text())
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(len(report["trials"]), 8)
        self.assertEqual(report["summary"]["oracle_matches"], 8)


if __name__ == "__main__":
    unittest.main()
