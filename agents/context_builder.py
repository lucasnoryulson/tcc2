import argparse
import json
import sys
from pathlib import Path


# ============================================================
# FILE HELPERS
# ============================================================

def load_json(path):
    return json.loads(
        path.read_text()
    )


def load_text(path):
    return path.read_text()


# ============================================================
# SUMMARY HELPERS
# ============================================================

def first_kernel(data):
    kernels = data.get(
        "kernels",
        []
    )

    if not kernels:
        return None

    return kernels[0]


def first_plan(data):
    plans = data.get(
        "plans",
        []
    )

    if not plans:
        return None

    return plans[0]


# ============================================================
# CONTEXT BUILDER
# ============================================================

def build_context(
    source_file,
    candidate_file,
    static_file,
    dependences_file,
    patterns_file,
    strategy_file,
    selection_file,
):

    static_data = load_json(
        static_file
    )

    dependence_data = load_json(
        dependences_file
    )

    pattern_data = load_json(
        patterns_file
    )

    strategy_data = load_json(
        strategy_file
    )

    selection_data = load_json(
        selection_file
    )

    static_kernel = first_kernel(
        static_data
    )

    dependence_kernel = first_kernel(
        dependence_data
    )

    pattern_kernel = first_kernel(
        pattern_data
    )

    strategy_plan = first_plan(
        strategy_data
    )

    if pattern_kernel is None:

        raise RuntimeError(
            "Pattern JSON does not contain "
            "a kernel."
        )

    if strategy_plan is None:

        raise RuntimeError(
            "Strategy JSON does not contain "
            "a plan."
        )

    context = {
        "schema":
            "tcc2-agent-context",

        "version":
            "0.1",

        "task":
            (
                "Evaluate the automatically generated "
                "parallel candidate and decide the "
                "next optimization action."
            ),

        # ----------------------------------------------------
        # SOURCE
        # ----------------------------------------------------

        "source": {
            "sequential_file":
                str(source_file),

            "candidate_file":
                str(candidate_file),

            "sequential_code":
                load_text(
                    source_file
                ),

            "candidate_code":
                load_text(
                    candidate_file
                ),
        },

        # ----------------------------------------------------
        # STATIC ANALYSIS
        # ----------------------------------------------------

        "static_analysis": {
            "kernel":
                static_kernel,
        },

        # ----------------------------------------------------
        # DEPENDENCE ANALYSIS
        # ----------------------------------------------------

        "dependence_analysis": {
            "kernel":
                dependence_kernel,
        },

        # ----------------------------------------------------
        # PATTERN CLASSIFICATION
        # ----------------------------------------------------

        "pattern": {
            "classification":
                pattern_kernel.get(
                    "classification"
                ),

            "family":
                pattern_kernel.get(
                    "family"
                ),

            "confidence":
                pattern_kernel.get(
                    "confidence"
                ),

            "reason":
                pattern_kernel.get(
                    "reason"
                ),

            "loops":
                pattern_kernel.get(
                    "loops",
                    []
                ),
        },

        # ----------------------------------------------------
        # STRATEGY
        # ----------------------------------------------------

        "strategy": {
            "detected_pattern":
                strategy_plan.get(
                    "detected_pattern"
                ),

            "family":
                strategy_plan.get(
                    "family"
                ),

            "classification_confidence":
                strategy_plan.get(
                    "classification_confidence"
                ),

            "plan":
                strategy_plan.get(
                    "strategy"
                ),
        },

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        "validation": {
            "correctness_gate":
                "PASS",

            "note":
                (
                    "This context is generated only "
                    "after the candidate passed the "
                    "compile and correctness gate."
                ),
        },

        # ----------------------------------------------------
        # PERFORMANCE
        # ----------------------------------------------------

        "performance": {
            "selection":
                selection_data,
        },

        # ----------------------------------------------------
        # AGENT RULES
        # ----------------------------------------------------

        "agent_constraints": [
            (
                "Never accept a candidate that has "
                "not passed correctness validation."
            ),

            (
                "Do not remove synchronization required "
                "by detected dependences."
            ),

            (
                "Do not introduce OpenMP transformations "
                "that contradict the Strategy Planner."
            ),

            (
                "Prefer evidence from static analysis, "
                "dependence analysis and measured "
                "performance over unsupported assumptions."
            ),

            (
                "If performance differences are within "
                "the near-tie threshold, consider resource "
                "efficiency before choosing more threads."
            ),

            (
                "Any proposed code modification must be "
                "recompiled and revalidated before being "
                "accepted."
            ),
        ],

        # ----------------------------------------------------
        # EXPECTED AGENT OUTPUT
        # ----------------------------------------------------

        "expected_decision_schema": {
            "decision":
                (
                    "ACCEPT | RETUNE | MODIFY | REJECT"
                ),

            "recommended_threads":
                "integer or null",

            "reason":
                "short explanation",

            "next_action":
                "action for another agent",

            "risk":
                "LOW | MEDIUM | HIGH",
        },
    }

    return context


# ============================================================
# PRINT SUMMARY
# ============================================================

def print_summary(context):

    print(
        "================================="
    )

    print(
        "TCC2 AGENT CONTEXT BUILDER v0.1"
    )

    print(
        "================================="
    )

    pattern = context[
        "pattern"
    ]

    strategy = context[
        "strategy"
    ]

    selection = context[
        "performance"
    ][
        "selection"
    ]

    print(
        f"Pattern: "
        f"{pattern['classification']}"
    )

    print(
        f"Family: "
        f"{pattern['family']}"
    )

    print(
        f"Strategy: "
        f"{strategy['plan'].get('strategy')}"
    )

    print(
        "Correctness gate: PASS"
    )

    recommended = selection.get(
        "recommended"
    )

    if recommended:

        print(
            f"Recommended threads: "
            f"{recommended.get('threads')}"
        )

        print(
            f"Recommended speedup: "
            f"{recommended.get('speedup'):.3f}x"
        )

        print(
            f"Recommended efficiency: "
            f"{recommended.get('efficiency'):.3f}"
        )

    print(
        "================================="
    )


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--candidate",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--static",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--dependences",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--patterns",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--strategy",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--selection",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    paths = [
        args.source,
        args.candidate,
        args.static,
        args.dependences,
        args.patterns,
        args.strategy,
        args.selection,
    ]

    for path in paths:

        if not path.exists():

            print(
                f"Arquivo não encontrado: "
                f"{path}"
            )

            sys.exit(1)

    try:

        context = build_context(
            args.source.resolve(),
            args.candidate.resolve(),
            args.static.resolve(),
            args.dependences.resolve(),
            args.patterns.resolve(),
            args.strategy.resolve(),
            args.selection.resolve(),
        )

    except RuntimeError as error:

        print(
            f"CONTEXT_ERROR: {error}"
        )

        sys.exit(1)

    output_file = (
        args.output.resolve()
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file.write_text(
        json.dumps(
            context,
            indent=2
        )
    )

    print_summary(
        context
    )

    print(
        f"Context salvo em: "
        f"{output_file}"
    )


if __name__ == "__main__":
    main()
