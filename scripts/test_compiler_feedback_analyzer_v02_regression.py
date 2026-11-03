#!/usr/bin/env python3

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(ROOT),
)

from analysis.compiler_feedback_analyzer import analyze_file


CASES = [
    {
        "name": "MANUAL_MEMORY_DEPENDENCE",
        "file": (
            ROOT
            / "results/mac_m5_2026-09-10/"
              "performance/nussinov/diagnostics/"
              "vectorization.txt"
        ),
        "expected_event":
            "VECTORIZATION_BLOCKED_MEMORY_DEPENDENCE",
        "expected_strategies": [
            "SCALAR_ACCUMULATOR",
            "LOOP_RESTRUCTURE",
        ],
    },
    {
        "name": "ACCUMULATOR_COST_MODEL",
        "file": (
            ROOT
            / "results/mac_m5_2026-09-10/"
              "performance/nussinov/diagnostics/"
              "accumulator_vectorization.txt"
        ),
        "expected_event":
            "VECTORIZATION_REJECTED_BY_COST_MODEL",
        "expected_strategies": [
            "EXPLICIT_SIMD_TRIAL",
        ],
    },
    {
        "name": "SIMD_APPLIED",
        "file": (
            ROOT
            / "results/mac_m5_2026-09-10/"
              "performance/nussinov/diagnostics/"
              "simd_vectorization.txt"
        ),
        "expected_event":
            "VECTORIZATION_APPLIED",
        "expected_strategies": [],
    },
]


def run_case(case):

    result = analyze_file(
        case["file"],
        function_name="kernel_nussinov",
    )

    event_ok = (
        result["dominant_event"]
        == case["expected_event"]
    )

    strategies_ok = (
        result["candidate_strategy_queue"]
        == case["expected_strategies"]
    )

    function_ok = (
        result["filter_mode"]
        == "function"
        and result["function_filter"]
        is not None
        and result["function_filter"]["name"]
        == "kernel_nussinov"
        and len(
            result["function_filter"][
                "source_ranges"
            ]
        ) >= 1
    )

    return (
        event_ok
        and strategies_ok
        and function_ok,
        result,
    )


def main():

    passed = 0

    print(
        "================================="
    )
    print(
        "Compiler Feedback Analyzer v0.2"
    )
    print(
        "Regression Test"
    )
    print(
        "================================="
    )

    for case in CASES:

        ok, result = run_case(
            case
        )

        print()
        print(
            f"{case['name']}: "
            f"{'PASS' if ok else 'FAIL'}"
        )

        print(
            "  filter_mode:",
            result["filter_mode"],
        )

        print(
            "  dominant_event:",
            result["dominant_event"],
        )

        print(
            "  strategies:",
            result[
                "candidate_strategy_queue"
            ],
        )

        ranges = result[
            "function_filter"
        ]["source_ranges"]

        print(
            "  discovered ranges:",
            [
                (
                    r["diagnostic_source"],
                    r["start"],
                    r["end"],
                )
                for r in ranges
            ],
        )

        if ok:
            passed += 1

    print()
    print(
        "================================="
    )

    if passed == len(CASES):
        print(
            "Compiler Feedback v0.2 "
            "regression: PASS"
        )
    else:
        print(
            "Compiler Feedback v0.2 "
            "regression: FAIL"
        )

    print(
        f"{passed}/{len(CASES)} "
        "cases behaved as expected."
    )

    print(
        "================================="
    )

    if passed != len(CASES):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
