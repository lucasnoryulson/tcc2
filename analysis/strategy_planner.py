import argparse
import json
import sys
from pathlib import Path


# ============================================================
# JSON
# ============================================================

def load_json(path):
    return json.loads(
        path.read_text()
    )


# ============================================================
# STATIC LOOP HIERARCHY
# ============================================================

def get_depth(loop):
    return loop.get(
        "nesting_depth",
        loop.get("depth", 0)
    )


def build_loop_hierarchy(static_kernel):
    """
    Reconstruct a simple parent relationship from
    nesting depths.

    Example:

        Loop #1 depth 0
          Loop #2 depth 1
            Loop #3 depth 2

    becomes:

        #1 parent = None
        #2 parent = #1
        #3 parent = #2
    """

    loops = static_kernel.get(
        "loops",
        []
    )

    hierarchy = {}

    stack = []

    for loop in loops:

        loop_id = loop.get("id")

        depth = get_depth(loop)

        while stack:

            parent_loop = stack[-1]

            parent_depth = get_depth(
                parent_loop
            )

            if parent_depth < depth:
                break

            stack.pop()

        parent_id = None

        if stack:

            parent_id = stack[-1].get(
                "id"
            )

        hierarchy[loop_id] = {
            "id":
                loop_id,

            "iterator":
                loop.get("iterator"),

            "depth":
                depth,

            "parent_id":
                parent_id,

            "initialization":
                loop.get(
                    "initialization"
                ),

            "condition":
                loop.get(
                    "condition"
                ),

            "increment":
                loop.get(
                    "increment"
                ),
        }

        stack.append(
            loop
        )

    return hierarchy


def get_ancestors(
    loop_id,
    hierarchy
):
    """
    Return ancestors from nearest parent to root.
    """

    ancestors = []

    current = hierarchy.get(
        loop_id
    )

    while current:

        parent_id = current.get(
            "parent_id"
        )

        if parent_id is None:
            break

        parent = hierarchy.get(
            parent_id
        )

        if parent is None:
            break

        ancestors.append(
            parent
        )

        current = parent

    return ancestors


# ============================================================
# PATTERN HELPERS
# ============================================================

def find_pattern_loops(
    pattern_kernel,
    classification
):

    return [
        loop
        for loop in pattern_kernel.get(
            "loops",
            []
        )
        if loop.get(
            "classification"
        ) == classification
    ]


def reduction_operator(
    compound_operator
):
    """
    Convert:

        += -> +
        *= -> *
        &= -> &
    """

    mapping = {
        "+=": "+",
        "*=": "*",
        "&=": "&",
        "|=": "|",
        "^=": "^",
    }

    return mapping.get(
        compound_operator
    )


# ============================================================
# DOALL / MAP
# ============================================================

def plan_doall(
    pattern_kernel,
    hierarchy
):

    loops = find_pattern_loops(
        pattern_kernel,
        "DOALL_CANDIDATE"
    )

    candidates = []

    for loop in loops:

        loop_id = loop.get(
            "loop_id"
        )

        info = hierarchy.get(
            loop_id,
            {}
        )

        candidates.append({
            "loop_id":
                loop_id,

            "iterator":
                loop.get(
                    "iterator"
                ),

            "depth":
                info.get(
                    "depth"
                ),

            "confidence":
                loop.get(
                    "confidence"
                ),
        })

    return {
        "strategy":
            "DOALL",

        "openmp_construct":
            "parallel for",

        "schedule":
            "static",

        "synchronization":
            "implicit_end_barrier",

        "candidate_loops":
            candidates,

        "loop_selection":
            "defer_to_loop_hierarchy_analysis",

        "direct_code_transformation":
            False,

        "reason":
            (
                "DOALL evidence exists, but local "
                "loop analysis alone is not always "
                "sufficient to select the best "
                "nesting level."
            ),
    }


# ============================================================
# REDUCTION
# ============================================================

def plan_reduction(
    pattern_kernel,
    hierarchy
):

    loops = find_pattern_loops(
        pattern_kernel,
        "REDUCTION_CANDIDATE"
    )

    plans = []

    for loop in loops:

        loop_id = loop.get(
            "loop_id"
        )

        evidence = loop.get(
            "evidence",
            {}
        )

        reduction_type = evidence.get(
            "reduction_type"
        )

        # ----------------------------------------------------
        # Scalar reduction
        # ----------------------------------------------------

        if reduction_type == "scalar":

            updates = evidence.get(
                "scalar_updates",
                []
            )

            for update in updates:

                operator = (
                    reduction_operator(
                        update.get(
                            "operator"
                        )
                    )
                )

                plans.append({
                    "loop_id":
                        loop_id,

                    "iterator":
                        loop.get(
                            "iterator"
                        ),

                    "reduction_type":
                        "scalar",

                    "variable":
                        update.get(
                            "variable"
                        ),

                    "operator":
                        operator,

                    "openmp_construct":
                        "parallel for",

                    "openmp_clause":
                        (
                            f"reduction("
                            f"{operator}:"
                            f"{update.get('variable')}"
                            f")"
                        ),

                    "schedule":
                        "static",

                    "direct_code_transformation":
                        True,
                })

        # ----------------------------------------------------
        # Array-element accumulation
        # ----------------------------------------------------

        elif reduction_type == "array_element":

            updates = evidence.get(
                "updates",
                []
            )

            ancestors = get_ancestors(
                loop_id,
                hierarchy
            )

            for update in updates:

                operators = update.get(
                    "operators",
                    []
                )

                operator = None

                if operators:

                    operator = (
                        reduction_operator(
                            operators[0]
                        )
                    )

                plans.append({
                    "loop_id":
                        loop_id,

                    "iterator":
                        loop.get(
                            "iterator"
                        ),

                    "reduction_type":
                        "array_element",

                    "write":
                        update.get(
                            "write"
                        ),

                    "operator":
                        operator,

                    "parallelize_this_loop_directly":
                        False,

                    "preferred_policy":
                        (
                            "keep accumulation loop serial "
                            "and search for an independent "
                            "outer loop"
                        ),

                    "ancestor_loops":
                        [
                            {
                                "loop_id":
                                    ancestor.get(
                                        "id"
                                    ),

                                "iterator":
                                    ancestor.get(
                                        "iterator"
                                    ),

                                "depth":
                                    ancestor.get(
                                        "depth"
                                    ),
                            }

                            for ancestor
                            in ancestors
                        ],

                    "direct_code_transformation":
                        False,
                })

    return {
        "strategy":
            "REDUCTION",

        "reductions":
            plans,
    }


# ============================================================
# STENCIL
# ============================================================

def plan_stencil(
    pattern_kernel,
    hierarchy
):

    loops = find_pattern_loops(
        pattern_kernel,
        "STENCIL_CANDIDATE"
    )

    phases = []

    for loop in loops:

        loop_id = loop.get(
            "loop_id"
        )

        info = hierarchy.get(
            loop_id,
            {}
        )

        parent_id = info.get(
            "parent_id"
        )

        parent = hierarchy.get(
            parent_id
        )

        ancestors = get_ancestors(
            loop_id,
            hierarchy
        )

        root = None

        if ancestors:
            root = ancestors[-1]

        evidence = loop.get(
            "evidence",
            {}
        )

        phases.append({
            "stencil_loop_id":
                loop_id,

            "stencil_iterator":
                loop.get(
                    "iterator"
                ),

            "recommended_spatial_loop_id":
                (
                    parent.get("id")
                    if parent
                    else loop_id
                ),

            "recommended_spatial_iterator":
                (
                    parent.get("iterator")
                    if parent
                    else loop.get(
                        "iterator"
                    )
                ),

            "temporal_loop_id":
                (
                    root.get("id")
                    if root
                    else None
                ),

            "temporal_iterator":
                (
                    root.get("iterator")
                    if root
                    else None
                ),

            "offsets":
                evidence.get(
                    "offsets",
                    []
                ),

            "stencil_points":
                evidence.get(
                    "stencil_points"
                ),
        })

    return {
        "strategy":
            "STENCIL",

        "parallel_region":
            "persistent",

        "spatial_construct":
            "omp for",

        "schedule":
            "static",

        "keep_temporal_loop_order":
            True,

        "barrier_between_phases":
            True,

        "phases":
            phases,

        "direct_code_transformation":
            False,

        "reason":
            (
                "Spatial iterations can be parallel, "
                "but temporal and phase ordering must "
                "be preserved."
            ),
    }


# ============================================================
# WAVEFRONT
# ============================================================

def plan_wavefront(
    pattern_kernel,
    hierarchy
):

    loops = find_pattern_loops(
        pattern_kernel,
        "WAVEFRONT_CANDIDATE"
    )

    plans = []

    for loop in loops:

        loop_id = loop.get(
            "loop_id"
        )

        info = hierarchy.get(
            loop_id,
            {}
        )

        parent_id = info.get(
            "parent_id"
        )

        parent = hierarchy.get(
            parent_id
        )

        evidence = loop.get(
            "evidence",
            {}
        )

        dimensions = []

        if parent:

            dimensions.append(
                parent.get(
                    "iterator"
                )
            )

        dimensions.append(
            loop.get(
                "iterator"
            )
        )

        plans.append({
            "loop_id":
                loop_id,

            "original_iterators":
                dimensions,

            "dependence_offsets":
                evidence.get(
                    "offsets",
                    []
                ),

            "transformation":
                "wavefront_diagonalization",

            "direct_parallel_for":
                False,

            "restructure_iteration_space":
                True,

            "parallelize_within_front":
                True,

            "barrier_between_fronts":
                True,

            "schedule":
                "static",
        })

    return {
        "strategy":
            "WAVEFRONT",

        "wavefronts":
            plans,

        "direct_code_transformation":
            False,

        "reason":
            (
                "Loop-carried dependences prevent a "
                "direct parallel-for transformation."
            ),
    }


# ============================================================
# MIXED
# ============================================================

def plan_mixed(
    pattern_kernel,
    hierarchy
):

    doall = plan_doall(
        pattern_kernel,
        hierarchy
    )

    reduction = plan_reduction(
        pattern_kernel,
        hierarchy
    )

    unresolved = find_pattern_loops(
        pattern_kernel,
        "UNKNOWN_DEPENDENCE"
    )

    return {
        "strategy":
            "MIXED",

        "components": {
            "map_doall":
                doall,

            "reductions":
                reduction,
        },

        "unresolved_regions":
            [
                {
                    "loop_id":
                        loop.get(
                            "loop_id"
                        ),

                    "iterator":
                        loop.get(
                            "iterator"
                        ),

                    "reason":
                        loop.get(
                            "reason"
                        ),
                }

                for loop
                in unresolved
            ],

        "direct_code_transformation":
            False,

        "reason":
            (
                "The kernel contains multiple "
                "parallel patterns and requires "
                "a composed transformation plan."
            ),
    }


# ============================================================
# KERNEL PLANNER
# ============================================================

def plan_kernel(
    static_kernel,
    pattern_kernel
):

    hierarchy = build_loop_hierarchy(
        static_kernel
    )

    classification = (
        pattern_kernel.get(
            "classification"
        )
    )

    if classification == "DOALL_CANDIDATE":

        strategy = plan_doall(
            pattern_kernel,
            hierarchy
        )

    elif classification == "REDUCTION_CANDIDATE":

        strategy = plan_reduction(
            pattern_kernel,
            hierarchy
        )

    elif classification == "STENCIL_CANDIDATE":

        strategy = plan_stencil(
            pattern_kernel,
            hierarchy
        )

    elif classification == "WAVEFRONT_CANDIDATE":

        strategy = plan_wavefront(
            pattern_kernel,
            hierarchy
        )

    elif classification == "MIXED_CANDIDATE":

        strategy = plan_mixed(
            pattern_kernel,
            hierarchy
        )

    else:

        strategy = {
            "strategy":
                "NO_SAFE_PLAN",

            "direct_code_transformation":
                False,

            "reason":
                (
                    "The current classifier did not "
                    "produce a sufficiently resolved "
                    "parallel pattern."
                ),
        }

    return {
        "kernel":
            pattern_kernel.get(
                "name"
            ),

        "detected_pattern":
            classification,

        "family":
            pattern_kernel.get(
                "family"
            ),

        "classification_confidence":
            pattern_kernel.get(
                "confidence"
            ),

        "strategy":
            strategy,
    }


# ============================================================
# PRINTING
# ============================================================

def print_plan(plan):

    print()

    print(
        f"Kernel: {plan['kernel']}"
    )

    print(
        f"Pattern: "
        f"{plan['detected_pattern']}"
    )

    print(
        f"Family: "
        f"{plan['family']}"
    )

    print(
        f"Classification confidence: "
        f"{plan['classification_confidence']}"
    )

    strategy = plan.get(
        "strategy",
        {}
    )

    print(
        f"Strategy: "
        f"{strategy.get('strategy')}"
    )

    print()

    print(
        json.dumps(
            strategy,
            indent=2
        )
    )


# ============================================================
# MAIN
# ============================================================

def analyze(
    static_file,
    patterns_file
):

    static_data = load_json(
        static_file
    )

    pattern_data = load_json(
        patterns_file
    )

    print(
        "================================="
    )

    print(
        "TCC2 STRATEGY PLANNER v0.1"
    )

    print(
        "================================="
    )

    print(
        f"Static:   {static_file}"
    )

    print(
        f"Patterns: {patterns_file}"
    )

    static_kernels = {
        kernel.get("name"):
            kernel

        for kernel in static_data.get(
            "kernels",
            []
        )
    }

    output = {
        "version":
            "0.1",

        "source":
            static_data.get(
                "source"
            ),

        "plans":
            [],
    }

    for pattern_kernel in (
        pattern_data.get(
            "kernels",
            []
        )
    ):

        name = pattern_kernel.get(
            "name"
        )

        static_kernel = (
            static_kernels.get(
                name
            )
        )

        if static_kernel is None:

            print(
                f"Kernel {name} não encontrado "
                "no Static Analyzer JSON."
            )

            continue

        plan = plan_kernel(
            static_kernel,
            pattern_kernel
        )

        output[
            "plans"
        ].append(
            plan
        )

        print_plan(
            plan
        )

    stem = (
        patterns_file.stem
        .replace(
            "_patterns",
            ""
        )
    )

    output_file = (
        patterns_file.parent
        / f"{stem}_strategy.json"
    )

    output_file.write_text(
        json.dumps(
            output,
            indent=2
        )
    )

    print()

    print(
        "================================="
    )

    print(
        f"JSON salvo em: "
        f"{output_file}"
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
        "static",
        type=Path,
        help=(
            "JSON produzido pelo "
            "Static Analyzer"
        )
    )

    parser.add_argument(
        "patterns",
        type=Path,
        help=(
            "JSON produzido pelo "
            "Pattern Classifier"
        )
    )

    args = parser.parse_args()

    static_file = (
        args.static.resolve()
    )

    patterns_file = (
        args.patterns.resolve()
    )

    if not static_file.exists():

        print(
            f"Arquivo não encontrado: "
            f"{static_file}"
        )

        sys.exit(1)

    if not patterns_file.exists():

        print(
            f"Arquivo não encontrado: "
            f"{patterns_file}"
        )

        sys.exit(1)

    analyze(
        static_file,
        patterns_file
    )


if __name__ == "__main__":
    main()
