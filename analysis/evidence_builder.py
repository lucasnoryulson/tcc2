#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


SCHEMA = "tcc2-deterministic-evidence"
VERSION = "0.1"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def classify_delta(value, higher_is_better):
    if value is None:
        return "UNKNOWN"

    if abs(value) < 1e-12:
        return "UNCHANGED"

    if higher_is_better:
        return "IMPROVED" if value > 0 else "REGRESSED"

    return "IMPROVED" if value < 0 else "REGRESSED"


def extract_correctness(context):
    validation = context.get("validation", {})

    gate = validation.get("correctness_gate")

    if gate is None:
        return {
            "status": "UNKNOWN",
            "passed": None,
        }

    normalized = str(gate).upper()

    return {
        "status": normalized,
        "passed": normalized == "PASS",
    }


def build_performance_evidence(selection):
    sequential = selection.get("sequential", {})
    fastest = selection.get("raw_fastest", {})
    recommended = selection.get("recommended", {})
    near_tie_candidates = selection.get("near_tie_candidates", [])

    threshold = selection.get("near_tie_threshold")

    recommended_mode = recommended.get("mode")
    recommended_threads = recommended.get("threads")

    recommended_is_near_tie = any(
        candidate.get("mode") == recommended_mode
        and candidate.get("threads") == recommended_threads
        for candidate in near_tie_candidates
    )

    speedup = recommended.get("speedup")

    return {
        "source": "dedicated_benchmark",
        "primary_runtime_evidence": True,

        "sequential": {
            "median_seconds": sequential.get("median_seconds"),
        },

        "fastest_configuration": {
            "mode": fastest.get("mode"),
            "threads": fastest.get("threads"),
            "median_seconds": fastest.get("median_seconds"),
            "speedup": fastest.get("speedup"),
        },

        "recommended_configuration": {
            "mode": recommended_mode,
            "threads": recommended_threads,
            "median_seconds": recommended.get("median_seconds"),
            "speedup": speedup,
            "efficiency": recommended.get("efficiency"),
            "slowdown_vs_fastest": recommended.get(
                "slowdown_vs_fastest"
            ),
        },

        "performance_improved": (
            speedup is not None and speedup > 1.0
        ),

        "near_tie": {
            "threshold_fraction": threshold,
            "threshold_percent": (
                threshold * 100.0
                if threshold is not None
                else None
            ),
            "meaning": (
                "A candidate configuration is near-tied when its "
                "runtime is within the configured slowdown threshold "
                "relative to the fastest measured candidate "
                "configuration. This threshold does not define a "
                "range of acceptable absolute speedup values."
            ),
            "recommended_is_near_tie": recommended_is_near_tie,
            "candidate_count": len(near_tie_candidates),
        },

        "selection_status": selection.get("status"),
        "selection_decision": selection.get("decision"),
        "selection_reason": selection.get("reason"),
    }


def build_profiling_evidence(profiling):
    comparison = profiling.get("comparison", {})

    ipc_change = comparison.get("ipc_change_percent")
    cache_change = comparison.get(
        "cache_miss_rate_change_percent"
    )
    branch_change = comparison.get(
        "branch_miss_rate_change_percent"
    )

    return {
        "source": "perf_stat",
        "primary_runtime_evidence": False,
        "role": (
            "Complementary microarchitectural evidence. "
            "It may explain performance behavior but does not "
            "replace the dedicated benchmark for the main runtime "
            "decision."
        ),

        "perf_speedup": comparison.get("speedup"),

        "ipc": {
            "change_percent": ipc_change,
            "assessment": classify_delta(
                ipc_change,
                higher_is_better=True,
            ),
            "meaning": "Higher IPC is treated as better.",
        },

        "cache_miss_rate": {
            "change_percent": cache_change,
            "assessment": classify_delta(
                cache_change,
                higher_is_better=False,
            ),
            "meaning": (
                "Lower cache miss rate is treated as better."
            ),
        },

        "branch_miss_rate": {
            "change_percent": branch_change,
            "assessment": classify_delta(
                branch_change,
                higher_is_better=False,
            ),
            "meaning": (
                "Lower branch miss rate is treated as better."
            ),
        },
    }


def build_evidence(context, selection, profiling):
    correctness = extract_correctness(context)
    performance = build_performance_evidence(selection)
    hardware = build_profiling_evidence(profiling)

    regressions = []

    for metric in (
        "ipc",
        "cache_miss_rate",
        "branch_miss_rate",
    ):
        if hardware[metric]["assessment"] == "REGRESSED":
            regressions.append(metric)

    return {
        "schema": SCHEMA,
        "version": VERSION,

        "correctness": correctness,

        "performance": performance,

        "hardware_profiling": hardware,

        "derived_facts": {
            "candidate_correct": correctness["passed"],
            "dedicated_benchmark_improved":
                performance["performance_improved"],
            "recommended_threads":
                performance[
                    "recommended_configuration"
                ]["threads"],
            "profiling_regressions": regressions,
            "profiling_regression_count": len(regressions),
            "profiling_has_regressions": len(regressions) > 0,
        },

        "coordinator_guidance": [
            (
                "Use dedicated benchmark results as the primary "
                "runtime evidence."
            ),
            (
                "Use hardware profiling only as complementary "
                "microarchitectural evidence."
            ),
            (
                "Do not reinterpret near_tie_threshold as an "
                "absolute speedup interval."
            ),
            (
                "Do not reverse the supplied IMPROVED, REGRESSED, "
                "or UNCHANGED assessments."
            ),
        ],
    }


def print_summary(evidence):
    correctness = evidence["correctness"]
    perf = evidence["performance"]
    profile = evidence["hardware_profiling"]

    recommended = perf["recommended_configuration"]
    near_tie = perf["near_tie"]

    print("========================================")
    print("TCC2 DETERMINISTIC EVIDENCE BUILDER v0.1")
    print("========================================")
    print(f"Correctness: {correctness['status']}")
    print()
    print("Primary benchmark:")
    print(
        f"  Recommended threads: "
        f"{recommended['threads']}"
    )
    print(
        f"  Speedup: "
        f"{recommended['speedup']:.3f}x"
    )
    print(
        f"  Improved: "
        f"{perf['performance_improved']}"
    )
    print()
    print("Near-tie:")
    print(
        f"  Threshold: "
        f"{near_tie['threshold_percent']:.2f}%"
    )
    print(
        f"  Recommended is near-tie: "
        f"{near_tie['recommended_is_near_tie']}"
    )
    print()
    print("Hardware profiling:")
    print(
        f"  IPC: "
        f"{profile['ipc']['assessment']} "
        f"({profile['ipc']['change_percent']:+.2f}%)"
    )
    print(
        f"  Cache miss rate: "
        f"{profile['cache_miss_rate']['assessment']} "
        f"({profile['cache_miss_rate']['change_percent']:+.2f}%)"
    )
    print(
        f"  Branch miss rate: "
        f"{profile['branch_miss_rate']['assessment']} "
        f"({profile['branch_miss_rate']['change_percent']:+.2f}%)"
    )
    print("========================================")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--context",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--selection",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--profiling",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    context = load_json(args.context)
    selection = load_json(args.selection)
    profiling = load_json(args.profiling)

    evidence = build_evidence(
        context,
        selection,
        profiling,
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with args.output.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            evidence,
            f,
            indent=2,
        )

    print_summary(evidence)
    print()
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
