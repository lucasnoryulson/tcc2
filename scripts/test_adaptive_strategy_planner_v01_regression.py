#!/usr/bin/env python3

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(ROOT),
)

from analysis.adaptive_strategy_planner import build_plan


CASES = [
    {
        "name": "MANUAL_TO_ACCUMULATOR",
        "feedback": (
            ROOT
            / "analysis/output/"
              "nussinov_feedback_manual_v02.json"
        ),
        "expected_strategy":
            "SCALAR_ACCUMULATOR",
        "expected_action":
            "APPLY_SCALAR_ACCUMULATOR",
        "expected_stage":
            "CODE_TRANSFORMER",
    },
    {
        "name": "ACCUMULATOR_TO_SIMD",
        "feedback": (
            ROOT
            / "analysis/output/"
              "nussinov_feedback_accumulator_v02.json"
        ),
        "expected_strategy":
            "EXPLICIT_SIMD_TRIAL",
        "expected_action":
            "APPLY_EXPLICIT_SIMD_REDUCTION",
        "expected_stage":
            "CODE_TRANSFORMER",
    },
    {
        "name": "SIMD_TO_MEASUREMENT",
        "feedback": (
            ROOT
            / "analysis/output/"
              "nussinov_feedback_simd_v02.json"
        ),
        "expected_strategy":
            None,
        "expected_action":
            "MEASURE_EXISTING_CANDIDATE",
        "expected_stage":
            "CORRECTNESS_AND_PERFORMANCE",
    },
]


def run_case(case):
    feedback = json.loads(
        case["feedback"].read_text()
    )

    plan = build_plan(
        feedback
    )

    checks = [
        (
            plan["selected_strategy"]
            == case["expected_strategy"]
        ),
        (
            plan["action"]
            == case["expected_action"]
        ),
        (
            plan["next_stage"]
            == case["expected_stage"]
        ),
        (
            plan["requires_correctness_gate"]
            is True
        ),
        (
            plan["requires_performance_gate"]
            is True
        ),
    ]

    return all(checks), plan


def main():
    passed = 0

    print(
        "================================="
    )
    print(
        "Adaptive Strategy Planner v0.1"
    )
    print(
        "Regression Test"
    )
    print(
        "================================="
    )

    for case in CASES:
        ok, plan = run_case(
            case
        )

        print()
        print(
            f"{case['name']}: "
            f"{'PASS' if ok else 'FAIL'}"
        )

        print(
            "  strategy:",
            plan["selected_strategy"],
        )

        print(
            "  action:",
            plan["action"],
        )

        print(
            "  next_stage:",
            plan["next_stage"],
        )

        if ok:
            passed += 1

    print()
    print(
        "================================="
    )

    if passed == len(CASES):
        print(
            "Adaptive Strategy regression: PASS"
        )
    else:
        print(
            "Adaptive Strategy regression: FAIL"
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
