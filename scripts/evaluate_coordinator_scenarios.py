"""Evaluate Coordinator decision coverage with explicit synthetic scenarios.

This complements, but never replaces, the provenance-bound kernel campaign.  It
tests decision semantics and structured-output reliability; its synthetic
measurements are not performance evidence.
"""

import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agents import coordinator_agent as coordinator
from analysis.artifact_provenance import file_record, sha256, verify_file

MODES = ("coordinator", "coordinator_without_analysis")
ABLATION_FIELDS = ("dependence_analysis", "pattern", "strategy", "deterministic_evidence")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def base_context():
    return {
        "task": "Controlled Coordinator decision scenario; not a kernel benchmark.",
        "source": {
            "sequential_code": "double f(double *a, int n) { return a[n - 1]; }",
            "candidate_code": "double f(double *a, int n) { return a[n - 1]; }",
        },
        "pattern": {"name": "controlled_fixture"},
        "strategy": {"name": "controlled_fixture"},
        "dependence_analysis": {"status": "SAFE"},
        "validation": {"correctness_gate": "PASS"},
        "performance": {"selection": {
            "status": "SELECTED",
            "configuration_dimensions": ["threads"],
            "recommended": {"threads": 2, "median_seconds": 0.5},
            "raw_fastest": {"threads": 2, "median_seconds": 0.5},
            "best_parallel": {"threads": 2, "median_seconds": 0.5},
            "best_one_thread": {"threads": 1, "median_seconds": 1.0},
            "near_tie_candidates": [{"threads": 2, "median_seconds": 0.5}],
        }},
        "profiling": {},
        "deterministic_evidence": {
            "parallel_status": "PARALLEL_SUCCESS",
            "measured_parallel_speedup": 2.0,
        },
        "agent_constraints": ["This is a controlled decision fixture, not measured research evidence."],
    }


def scenarios():
    accept = base_context()

    reject = base_context()
    reject["performance"]["selection"] = {
        "status": "NO_BENEFICIAL_CONFIGURATION",
        "configuration_dimensions": ["threads"],
        "recommended": None,
        "raw_fastest": {"threads": 1, "median_seconds": 1.05},
        "best_one_thread": {"threads": 1, "median_seconds": 1.05},
        "best_parallel": {"threads": 2, "median_seconds": 1.20},
        "near_tie_candidates": [],
    }
    reject["deterministic_evidence"] = {
        "parallel_status": "NO_USEFUL_PATH",
        "measured_parallel_speedup": 0.875,
        "assessment": "Correct candidate, but no useful measured performance path remains.",
    }

    retune = base_context()
    retune["performance"]["selection"] = {
        "status": "INSUFFICIENT_CONFIGURATIONS",
        "configuration_dimensions": ["threads"],
        "recommended": None,
        "raw_fastest": {"threads": 1, "median_seconds": 1.0},
        "best_one_thread": {"threads": 1, "median_seconds": 1.0},
        "best_parallel": None,
        "near_tie_candidates": [],
    }
    retune["deterministic_evidence"] = {
        "parallel_status": "INSUFFICIENT_CONFIGURATIONS",
        "assessment": "Transformation appears valid, but no configuration above one thread was measured.",
    }

    modify = base_context()
    modify["validation"] = {
        "correctness_gate": "FAIL",
        "failure_kind": "OUTPUT_MISMATCH",
        "assessment": "Candidate output differs from the sequential reference and requires repair.",
    }
    modify["performance"] = {"selection": {}}
    modify["deterministic_evidence"] = {
        "parallel_status": "NOT_EVALUATED",
        "assessment": "Correctness failure blocks benchmarking and requires debugging.",
    }

    return {
        "accept": (accept, "ACCEPT", {"PROMOTE_CANDIDATE"}),
        "reject": (reject, "REJECT", {"REJECT_CANDIDATE"}),
        "retune": (retune, "RETUNE", {"RETUNE_CONFIGURATION", "RUN_MORE_BENCHMARKS"}),
        "modify": (modify, "MODIFY", {"SEND_TO_DEBUGGER"}),
    }


def model_context(context, mode):
    view = copy.deepcopy(context)
    if mode == "coordinator_without_analysis":
        for field in ABLATION_FIELDS:
            view[field] = {}
    return view


def run_trial(name, context, expected_decision, expected_actions, mode, model, timeout, directory):
    directory.mkdir()
    view = model_context(context, mode)
    prompt = {
        "system": coordinator.build_system_prompt(),
        "user": coordinator.build_user_prompt(view),
        "format": coordinator.DECISION_SCHEMA,
        "temperature": 0,
        "model": model,
    }
    write_json(directory / "prompt.json", prompt)
    started = time.perf_counter()
    trial = {
        "scenario": name,
        "mode": mode,
        "expected_decision": expected_decision,
        "expected_actions": sorted(expected_actions),
        "prompt_sha256": sha256((directory / "prompt.json").read_bytes()),
        "status": "OK",
        "validation_errors": [],
    }
    try:
        raw, metadata = coordinator.call_ollama(model, view, timeout)
        if not isinstance(raw, dict):
            raise ValueError("Coordinator response must be a JSON object.")
        decision = coordinator.enrich_deterministic_configuration(copy.deepcopy(raw), context)
        errors = coordinator.validate_decision(decision, context)
        trial.update(raw_decision=raw, decision=decision, metadata=metadata, validation_errors=errors)
        if errors:
            trial["status"] = "INVALID"
    except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
        trial.update(status="TIMEOUT" if "TIMEOUT" in str(error).upper() else "ERROR", error=str(error))
    decision = trial.get("decision", {})
    trial["oracle_match"] = bool(
        trial["status"] == "OK"
        and decision.get("decision") == expected_decision
        and decision.get("next_action") in expected_actions
    )
    trial["wall_seconds"] = time.perf_counter() - started
    write_json(directory / "trial.json", trial)
    return trial


def save_report(directory, report):
    rows = report["trials"]
    report["summary"] = {
        "trials": len(rows),
        "valid_responses": sum(row["status"] == "OK" for row in rows),
        "oracle_matches": sum(row["oracle_match"] for row in rows),
        "failures": sum(row["status"] != "OK" for row in rows),
        "median_wall_seconds": statistics.median(row["wall_seconds"] for row in rows) if rows else None,
    }
    write_json(directory / "results.json", report)
    summary = report["summary"]
    lines = [
        "# Cobertura controlada de decisões do Coordinator",
        "",
        f"Estado: **{report['status']}**.",
        "",
        f"Respostas válidas: {summary['valid_responses']}/{summary['trials']}.",
        f"Correspondências com o oráculo: {summary['oracle_matches']}/{summary['trials']}.",
        "",
        "Os cenários e tempos são sintéticos. Este ensaio verifica semântica de decisão e",
        "confiabilidade da saída estruturada; não constitui evidência de desempenho de kernels.",
    ]
    (directory / "report.md").write_text("\n".join(lines) + "\n")


def evaluate(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="scenarios-", dir=args.output_dir.resolve()))
    report = {
        "schema": "tcc2-coordinator-controlled-scenarios",
        "version": "0.1",
        "status": "RUNNING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "settings": {"model": args.model, "timeout_seconds": args.timeout,
                     "repetitions": args.repetitions, "seed": args.seed, "temperature": 0},
        "implementation": [file_record(path) for path in (Path(__file__), ROOT / "agents/coordinator_agent.py")],
        "trials": [],
    }
    save_report(directory, report)
    randomizer = random.Random(args.seed)
    try:
        jobs = []
        for repetition in range(1, args.repetitions + 1):
            for name, (context, expected, actions) in scenarios().items():
                for mode in MODES:
                    jobs.append((repetition, name, context, expected, actions, mode))
        randomizer.shuffle(jobs)
        for index, (repetition, name, context, expected, actions, mode) in enumerate(jobs, 1):
            print(f"{index}/{len(jobs)}: {name} {mode}", flush=True)
            trial = run_trial(name, context, expected, actions, mode, args.model, args.timeout,
                              directory / f"{index:02d}-{name}-{repetition}-{mode}")
            trial["repetition"] = repetition
            report["trials"].append(trial)
            save_report(directory, report)
        for reference in report["implementation"]:
            verify_file(reference)
        report["status"] = "COMPLETE" if all(row["status"] == "OK" and row["oracle_match"]
                                                for row in report["trials"]) else "INCOMPLETE"
    except (OSError, ValueError, RuntimeError) as error:
        report.update(status="FAILED", error=str(error))
    save_report(directory, report)
    print(f"{report['status']}: {directory / 'report.md'}", flush=True)
    return (0 if report["status"] == "COMPLETE" else 1), directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/coordinator_scenarios")
    args = parser.parse_args()
    if args.timeout < 1 or args.repetitions < 1:
        parser.error("Use positive timeout and repetitions.")
    return evaluate(args)[0]


if __name__ == "__main__":
    sys.exit(main())
