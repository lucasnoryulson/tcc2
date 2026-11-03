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
        line_start=180,
        line_end=230,
    )

    event_ok = (
        result["dominant_event"]
        == case["expected_event"]
    )

    strategies_ok = (
        result["candidate_strategy_queue"]
        == case["expected_strategies"]
    )

    passed = (
        event_ok
        and strategies_ok
    )

    return (
        passed,
        result,
    )


def main():
    passed_count = 0

    print(
        "================================="
    )
    print(
        "Compiler Feedback Analyzer v0.1"
    )
    print(
        "Regression Test"
    )
    print(
        "================================="
    )

    for case in CASES:

        passed, result = run_case(
            case
        )

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print()
        print(
            f"{case['name']}: "
            f"{status}"
        )

        print(
            "  expected event:",
            case["expected_event"],
        )

        print(
            "  actual event:  ",
            result[
                "dominant_event"
            ],
        )

        print(
            "  expected strategies:",
            case[
                "expected_strategies"
            ],
        )

        print(
            "  actual strategies:  ",
            result[
                "candidate_strategy_queue"
            ],
        )

        if passed:
            passed_count += 1

    print()
    print(
        "================================="
    )

    if passed_count == len(CASES):

        print(
            "Compiler Feedback regression: "
            "PASS"
        )

    else:

        print(
            "Compiler Feedback regression: "
            "FAIL"
        )

    print(
        f"{passed_count}/"
        f"{len(CASES)} cases behaved "
        f"as expected."
    )

    print(
        "================================="
    )

    if passed_count != len(CASES):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
