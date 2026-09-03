import argparse
import json
import sys
from pathlib import Path


# ============================================================
# HELPERS
# ============================================================

def load_json(path):
    return json.loads(
        path.read_text()
    )


def find_loop(static_data, loop_id):
    """
    Find loop information in the Static Analyzer JSON.
    """

    for kernel in static_data.get(
        "kernels",
        []
    ):

        for loop in kernel.get(
            "loops",
            []
        ):

            if loop.get("id") == loop_id:
                return loop

    return None


def expression_uses_iterator(
    access,
    iterator
):
    """
    Check whether an array WRITE is indexed by the
    current loop iterator.

    Example:

        C[i][j]

    when iterator = j

    -> True
    """

    if not iterator:
        return False

    for index in access.get(
        "indices",
        []
    ):

        if iterator in index:
            return True

    return False


# ============================================================
# LOOP CLASSIFICATION
# ============================================================

def classify_loop(
    static_loop,
    dependence_loop
):
    """
    Deterministic pattern classifier.

    Current supported classifications:

        DOALL_CANDIDATE
        REDUCTION_CANDIDATE
        WAVEFRONT_CANDIDATE
        UNKNOWN_DEPENDENCE
        NO_DIRECT_EVIDENCE
        UNKNOWN
    """

    dependencies = dependence_loop.get(
        "dependencies",
        []
    )

    iterator = dependence_loop.get(
        "iterator"
    )

    shifted = [
        dependency
        for dependency in dependencies
        if dependency.get("relation")
        == "shifted_access"
    ]

    symbolic = [
        dependency
        for dependency in dependencies
        if dependency.get("relation")
        == "symbolic_relation"
    ]

    same_location = [
        dependency
        for dependency in dependencies
        if dependency.get("relation")
        == "same_location"
    ]

    writes = []
    operators = []
    scalar_updates = []

    if static_loop:

        writes = static_loop.get(
            "writes",
            []
        )

        operators = static_loop.get(
            "operators",
            []
        )

        scalar_updates = static_loop.get(
            "scalar_updates",
            []
        )

    # --------------------------------------------------------
    # WAVEFRONT
    # --------------------------------------------------------

    if shifted:

        offsets = [
            dependency.get(
                "offsets"
            )
            for dependency in shifted
        ]

        return {
            "classification":
                "WAVEFRONT_CANDIDATE",

            "confidence":
                "high",

            "reason":
                (
                    "Shifted accesses to the same "
                    "written array were detected."
                ),

            "evidence": {
                "shifted_accesses":
                    len(shifted),

                "offsets":
                    offsets,

                "symbolic_relations":
                    len(symbolic),
            }
        }

    # --------------------------------------------------------
    # REDUCTION
    # --------------------------------------------------------

    reduction_operators = {
        "+=",
        "*=",
        "&=",
        "|=",
        "^=",
    }

    reduction_updates = [
        update
        for update in scalar_updates
        if update.get("operator")
        in reduction_operators
    ]

    if reduction_updates:

        return {
            "classification":
                "REDUCTION_CANDIDATE",

            "confidence":
                "medium",

            "reason":
                (
                    "A scalar variable is updated "
                    "with a reduction-compatible "
                    "compound operator inside the loop."
                ),

            "evidence": {
                "scalar_updates":
                    reduction_updates,

                "reduction_operators":
                    [
                        update.get("operator")
                        for update
                        in reduction_updates
                    ],
            }
        }

    # --------------------------------------------------------
    # SYMBOLIC / UNKNOWN
    # --------------------------------------------------------

    if symbolic:

        return {
            "classification":
                "UNKNOWN_DEPENDENCE",

            "confidence":
                "low",

            "reason":
                (
                    "The loop contains relationships "
                    "that the current affine analyzer "
                    "cannot resolve."
                ),

            "evidence": {
                "symbolic_relations":
                    len(symbolic),
            }
        }

    # --------------------------------------------------------
    # POSSIBLE DOALL
    # --------------------------------------------------------

    if same_location and writes:

        iterator_in_write = any(
            expression_uses_iterator(
                write,
                iterator
            )
            for write in writes
        )

        if iterator_in_write:

            return {
                "classification":
                    "DOALL_CANDIDATE",

                "confidence":
                    "medium",

                "reason":
                    (
                        "Only same-location updates "
                        "were detected and the current "
                        "iterator participates in the "
                        "written array index."
                    ),

                "evidence": {
                    "same_location":
                        len(same_location),

                    "iterator_in_write":
                        True,

                    "operators":
                        operators,
                }
            }

    # --------------------------------------------------------
    # NO DIRECT MEMORY EVIDENCE
    # --------------------------------------------------------

    if not dependencies:

        return {
            "classification":
                "NO_DIRECT_EVIDENCE",

            "confidence":
                "low",

            "reason":
                (
                    "No direct READ/WRITE dependence "
                    "candidate was associated with "
                    "this loop level."
                ),

            "evidence": {}
        }

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    return {
        "classification":
            "UNKNOWN",

        "confidence":
            "low",

        "reason":
            "Insufficient evidence.",

        "evidence": {}
    }


# ============================================================
# KERNEL CLASSIFICATION
# ============================================================

def classify_kernel(
    static_kernel,
    dependence_kernel
):

    loop_results = []

    for dependence_loop in dependence_kernel.get(
        "loops",
        []
    ):

        loop_id = dependence_loop.get(
            "id"
        )

        static_loop = None

        for candidate in static_kernel.get(
            "loops",
            []
        ):

            if candidate.get("id") == loop_id:

                static_loop = candidate

                break

        classification = classify_loop(
            static_loop,
            dependence_loop
        )

        classification["loop_id"] = (
            loop_id
        )

        classification["iterator"] = (
            dependence_loop.get(
                "iterator"
            )
        )

        loop_results.append(
            classification
        )

    # --------------------------------------------------------
    # Kernel-level evidence
    # --------------------------------------------------------

    wavefront_loops = [
        result
        for result in loop_results
        if result["classification"]
        == "WAVEFRONT_CANDIDATE"
    ]

    reduction_loops = [
        result
        for result in loop_results
        if result["classification"]
        == "REDUCTION_CANDIDATE"
    ]

    doall_loops = [
        result
        for result in loop_results
        if result["classification"]
        == "DOALL_CANDIDATE"
    ]

    symbolic_loops = [
        result
        for result in loop_results
        if result["classification"]
        == "UNKNOWN_DEPENDENCE"
    ]

    # --------------------------------------------------------
    # Kernel-level decision
    # --------------------------------------------------------

    if wavefront_loops:

        kernel_class = (
            "WAVEFRONT_CANDIDATE"
        )

        confidence = "high"

        reason = (
            "At least one loop contains "
            "resolved shifted dependences."
        )

    elif reduction_loops:

        kernel_class = (
            "REDUCTION_CANDIDATE"
        )

        confidence = "medium"

        reason = (
            "At least one loop contains "
            "a scalar reduction update."
        )

    elif doall_loops and not symbolic_loops:

        kernel_class = (
            "DOALL_CANDIDATE"
        )

        confidence = "medium"

        reason = (
            "Independent-index candidates "
            "were detected and no shifted or "
            "symbolic dependences were found."
        )

    elif symbolic_loops:

        kernel_class = (
            "MIXED_OR_UNKNOWN"
        )

        confidence = "low"

        reason = (
            "Unresolved symbolic relationships "
            "remain in the kernel."
        )

    else:

        kernel_class = (
            "UNKNOWN"
        )

        confidence = "low"

        reason = (
            "Current analysis produced "
            "insufficient evidence."
        )

    return {
        "name":
            dependence_kernel.get(
                "name",
                "unknown"
            ),

        "classification":
            kernel_class,

        "confidence":
            confidence,

        "reason":
            reason,

        "loops":
            loop_results,
    }


# ============================================================
# PRINT
# ============================================================

def print_result(result):

    print()

    print(
        f"Kernel: {result['name']}"
    )

    print(
        f"Classification: "
        f"{result['classification']}"
    )

    print(
        f"Confidence: "
        f"{result['confidence']}"
    )

    print(
        f"Reason: "
        f"{result['reason']}"
    )

    print()

    print(
        "Loop classifications:"
    )

    for loop in result["loops"]:

        print()

        print(
            f"  Loop #{loop['loop_id']}"
            f" ({loop['iterator']})"
        )

        print(
            f"    Pattern: "
            f"{loop['classification']}"
        )

        print(
            f"    Confidence: "
            f"{loop['confidence']}"
        )

        print(
            f"    Reason: "
            f"{loop['reason']}"
        )

        evidence = loop.get(
            "evidence",
            {}
        )

        if evidence:

            print(
                "    Evidence:"
            )

            for key, value in evidence.items():

                print(
                    f"      {key}: "
                    f"{value}"
                )


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze(
    static_file,
    dependence_file
):

    static_data = load_json(
        static_file
    )

    dependence_data = load_json(
        dependence_file
    )

    print(
        "================================="
    )

    print(
        "TCC2 PATTERN CLASSIFIER v0.4.1"
    )

    print(
        "================================="
    )

    print(
        f"Static:     {static_file}"
    )

    print(
        f"Dependence: {dependence_file}"
    )

    output = {
        "version": "0.4.1",

        "source":
            static_data.get(
                "source"
            ),

        "kernels": [],
    }

    static_kernels = {
        kernel.get("name"):
            kernel

        for kernel in static_data.get(
            "kernels",
            []
        )
    }

    for dependence_kernel in (
        dependence_data.get(
            "kernels",
            []
        )
    ):

        name = dependence_kernel.get(
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

        result = classify_kernel(
            static_kernel,
            dependence_kernel
        )

        output["kernels"].append(
            result
        )

        print_result(
            result
        )

    output_dir = (
        dependence_file.parent
    )

    stem = (
        dependence_file.stem
    )

    stem = stem.replace(
        "_dependences",
        ""
    )

    output_file = (
        output_dir
        / f"{stem}_patterns.json"
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
        "dependences",
        type=Path,
        help=(
            "JSON produzido pelo "
            "Dependence Analyzer"
        )
    )

    args = parser.parse_args()

    static_file = (
        args.static.resolve()
    )

    dependence_file = (
        args.dependences.resolve()
    )

    if not static_file.exists():

        print(
            f"Arquivo não encontrado: "
            f"{static_file}"
        )

        sys.exit(1)

    if not dependence_file.exists():

        print(
            f"Arquivo não encontrado: "
            f"{dependence_file}"
        )

        sys.exit(1)

    analyze(
        static_file,
        dependence_file
    )


if __name__ == "__main__":
    main()