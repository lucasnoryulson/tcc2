import argparse
import json
import re
import sys
from pathlib import Path


# ============================================================
# CONSTANTS
# ============================================================

REDUCTION_OPERATORS = {
    "+=",
    "*=",
    "&=",
    "|=",
    "^=",
}


# ============================================================
# JSON
# ============================================================

def load_json(path):
    return json.loads(
        path.read_text()
    )


# ============================================================
# HIGH-LEVEL FAMILIES
# ============================================================

def pattern_family(pattern):

    families = {
        "DOALL_CANDIDATE":
            "MAP / DATA_PARALLEL",

        "REDUCTION_CANDIDATE":
            "REDUCE / AGGREGATION",

        "STENCIL_CANDIDATE":
            "STENCIL",

        "WAVEFRONT_CANDIDATE":
            "WAVEFRONT / DOACROSS",

        "MIXED_CANDIDATE":
            "MIXED / MAP+REDUCE",

        "UNKNOWN_DEPENDENCE":
            "UNKNOWN",

        "NO_DIRECT_EVIDENCE":
            "UNKNOWN",

        "MIXED_OR_UNKNOWN":
            "MIXED / UNKNOWN",

        "UNKNOWN":
            "UNKNOWN",
    }

    return families.get(
        pattern,
        "UNKNOWN"
    )


# ============================================================
# GENERAL HELPERS
# ============================================================

def expression_uses_iterator(
    access,
    iterator
):
    """
    Check whether an array access uses the current
    loop iterator in at least one dimension.

    Example:

        iterator = j
        C[i][j] -> True

        iterator = k
        C[i][j] -> False
    """

    if not iterator:
        return False

    for index in access.get(
        "indices",
        []
    ):

        #
        # Use token matching instead of substring matching.
        #
        tokens = re.findall(
            r"[A-Za-z_][A-Za-z0-9_]*",
            index
        )

        if iterator in tokens:
            return True

    return False


# ============================================================
# AFFINE INDEX NORMALIZATION
# ============================================================

def remove_parentheses(expression):

    expression = expression.strip()

    while (
        expression.startswith("(")
        and expression.endswith(")")
    ):

        expression = (
            expression[1:-1]
            .strip()
        )

    return expression


def parse_affine_index(expression):
    """
    Parse simple affine expressions.

    Supported:

        i
        j

        i+1
        i-1

        1+i
        1+j

        j+2
        2+j

    Returns for j+1:

        {
            "variable": "j",
            "offset": 1
        }
    """

    if expression is None:
        return None

    expression = (
        expression
        .replace(" ", "")
    )

    expression = remove_parentheses(
        expression
    )

    # --------------------------------------------------------
    # Plain iterator
    # --------------------------------------------------------

    match = re.match(
        r"^([A-Za-z_][A-Za-z0-9_]*)$",
        expression
    )

    if match:

        return {
            "variable":
                match.group(1),

            "offset":
                0,
        }

    # --------------------------------------------------------
    # iterator +/- constant
    # --------------------------------------------------------

    match = re.match(
        r"^"
        r"([A-Za-z_][A-Za-z0-9_]*)"
        r"([+-])"
        r"(\d+)"
        r"$",
        expression
    )

    if match:

        variable = (
            match.group(1)
        )

        operator = (
            match.group(2)
        )

        value = int(
            match.group(3)
        )

        if operator == "-":
            value *= -1

        return {
            "variable":
                variable,

            "offset":
                value,
        }

    # --------------------------------------------------------
    # constant + iterator
    #
    # 1+i
    # 1+j
    # --------------------------------------------------------

    match = re.match(
        r"^"
        r"(\d+)"
        r"\+"
        r"([A-Za-z_][A-Za-z0-9_]*)"
        r"$",
        expression
    )

    if match:

        return {
            "variable":
                match.group(2),

            "offset":
                int(
                    match.group(1)
                ),
        }

    return None


# ============================================================
# STENCIL
# ============================================================

def compare_stencil_index(
    write_index,
    read_index
):

    write_affine = (
        parse_affine_index(
            write_index
        )
    )

    read_affine = (
        parse_affine_index(
            read_index
        )
    )

    if (
        write_affine is None
        or read_affine is None
    ):
        return None

    if (
        write_affine["variable"]
        != read_affine["variable"]
    ):
        return None

    return (
        read_affine["offset"]
        - write_affine["offset"]
    )


def calculate_stencil_offset(
    write_access,
    read_access
):

    write_indices = (
        write_access.get(
            "indices",
            []
        )
    )

    read_indices = (
        read_access.get(
            "indices",
            []
        )
    )

    if (
        len(write_indices)
        != len(read_indices)
    ):
        return None

    offsets = []

    for write_index, read_index in zip(
        write_indices,
        read_indices
    ):

        offset = (
            compare_stencil_index(
                write_index,
                read_index
            )
        )

        if offset is None:
            return None

        offsets.append(
            offset
        )

    return offsets


def is_unit_neighborhood(offset):

    if not offset:
        return False

    return all(
        abs(value) <= 1
        for value in offset
    )


def opposite_offset(offset):

    return tuple(
        -value
        for value in offset
    )


def find_stencil_evidence(
    static_loop
):

    if not static_loop:
        return None

    reads = static_loop.get(
        "reads",
        []
    )

    writes = static_loop.get(
        "writes",
        []
    )

    if not reads or not writes:
        return None

    best_candidate = None

    for write_access in writes:

        write_array = (
            write_access.get(
                "array"
            )
        )

        read_groups = {}

        for read_access in reads:

            read_array = (
                read_access.get(
                    "array"
                )
            )

            if not read_array:
                continue

            #
            # First version of the Stencil detector
            # focuses on cross-array / double-buffer
            # patterns.
            #
            # Jacobi:
            #
            # B <- A neighborhood
            # A <- B neighborhood
            #
            if read_array == write_array:
                continue

            offset = (
                calculate_stencil_offset(
                    write_access,
                    read_access
                )
            )

            if offset is None:
                continue

            if not is_unit_neighborhood(
                offset
            ):
                continue

            read_groups.setdefault(
                read_array,
                []
            ).append({
                "read":
                    read_access.get(
                        "expression"
                    ),

                "offset":
                    offset,
            })

        for (
            read_array,
            accesses
        ) in read_groups.items():

            unique = {}

            for access in accesses:

                key = tuple(
                    access["offset"]
                )

                unique[key] = access

            offsets = list(
                unique.keys()
            )

            if not offsets:
                continue

            dimensions = len(
                offsets[0]
            )

            center = tuple(
                0
                for _ in range(
                    dimensions
                )
            )

            center_present = (
                center in offsets
            )

            neighbors = [
                offset
                for offset in offsets
                if offset != center
            ]

            if (
                not center_present
                or len(neighbors) < 2
            ):
                continue

            symmetric_pairs = 0
            checked = set()

            for offset in neighbors:

                if offset in checked:
                    continue

                opposite = (
                    opposite_offset(
                        offset
                    )
                )

                if opposite in neighbors:

                    symmetric_pairs += 1

                    checked.add(
                        offset
                    )

                    checked.add(
                        opposite
                    )

            points = len(
                offsets
            )

            if (
                points >= 5
                and symmetric_pairs >= 2
            ):

                confidence = "high"

            else:

                confidence = "medium"

            candidate = {
                "write":
                    write_access.get(
                        "expression"
                    ),

                "write_array":
                    write_array,

                "read_array":
                    read_array,

                "dimensions":
                    dimensions,

                "offsets":
                    [
                        list(offset)
                        for offset
                        in sorted(offsets)
                    ],

                "stencil_points":
                    points,

                "center_present":
                    center_present,

                "symmetric_pairs":
                    symmetric_pairs,

                "confidence":
                    confidence,
            }

            if (
                best_candidate is None
                or candidate[
                    "stencil_points"
                ]
                > best_candidate[
                    "stencil_points"
                ]
            ):

                best_candidate = (
                    candidate
                )

    return best_candidate


# ============================================================
# ARRAY REDUCTION
# ============================================================

def find_array_reduction_evidence(
    static_loop,
    same_location,
    iterator
):
    """
    Detect reduction-like updates on an array element.

    Example:

        for (i = 0; i < N; i++)
            mean[j] += data[i][j];

    iterator = i

    WRITE:
        mean[j]

    Since i is NOT part of mean[j], every iteration
    contributes to the same array element.

    This is reduction-like behavior.

    Another example:

        for (k = 0; k < N; k++)
            cov[i][j] += data[k][i] * data[k][j];

    iterator = k

    WRITE:
        cov[i][j]

    Again, k does not participate in the WRITE index.
    """

    if not static_loop:
        return []

    if not iterator:
        return []

    writes = static_loop.get(
        "writes",
        []
    )

    operators = static_loop.get(
        "operators",
        []
    )

    compatible_operators = [
        operator
        for operator in operators
        if operator in REDUCTION_OPERATORS
    ]

    if not compatible_operators:
        return []

    same_location_writes = {
        dependency.get("write")
        for dependency in same_location
    }

    evidence = []

    for write in writes:

        expression = write.get(
            "expression"
        )

        if (
            expression
            not in same_location_writes
        ):
            continue

        iterator_in_write = (
            expression_uses_iterator(
                write,
                iterator
            )
        )

        #
        # Critical reduction criterion:
        #
        # the accumulation loop iterator does not
        # participate in the written location.
        #
        if iterator_in_write:
            continue

        evidence.append({
            "type":
                "array_element",

            "write":
                expression,

            "iterator":
                iterator,

            "iterator_in_write":
                False,

            "operators":
                compatible_operators,
        })

    return evidence


# ============================================================
# LOOP CLASSIFICATION
# ============================================================

def classify_loop(
    static_loop,
    dependence_loop
):

    dependencies = (
        dependence_loop.get(
            "dependencies",
            []
        )
    )

    iterator = (
        dependence_loop.get(
            "iterator"
        )
    )

    shifted = [
        dependency
        for dependency in dependencies
        if dependency.get(
            "relation"
        ) == "shifted_access"
    ]

    symbolic = [
        dependency
        for dependency in dependencies
        if dependency.get(
            "relation"
        ) == "symbolic_relation"
    ]

    same_location = [
        dependency
        for dependency in dependencies
        if dependency.get(
            "relation"
        ) == "same_location"
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

        scalar_updates = (
            static_loop.get(
                "scalar_updates",
                []
            )
        )

    # --------------------------------------------------------
    # WAVEFRONT
    # --------------------------------------------------------

    if shifted:

        offsets = [
            dependency.get(
                "offsets"
            )
            for dependency
            in shifted
        ]

        classification = (
            "WAVEFRONT_CANDIDATE"
        )

        return {
            "classification":
                classification,

            "family":
                pattern_family(
                    classification
                ),

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
    # SCALAR REDUCTION
    # --------------------------------------------------------

    scalar_reduction_updates = [
        update
        for update in scalar_updates
        if update.get(
            "operator"
        ) in REDUCTION_OPERATORS
    ]

    if scalar_reduction_updates:

        classification = (
            "REDUCTION_CANDIDATE"
        )

        return {
            "classification":
                classification,

            "family":
                pattern_family(
                    classification
                ),

            "confidence":
                "medium",

            "reason":
                (
                    "A scalar variable is updated "
                    "with a reduction-compatible "
                    "compound operator inside the loop."
                ),

            "evidence": {
                "reduction_type":
                    "scalar",

                "scalar_updates":
                    scalar_reduction_updates,
            }
        }

    # --------------------------------------------------------
    # ARRAY-ELEMENT REDUCTION
    # --------------------------------------------------------

    array_reduction = (
        find_array_reduction_evidence(
            static_loop,
            same_location,
            iterator
        )
    )

    if array_reduction:

        classification = (
            "REDUCTION_CANDIDATE"
        )

        return {
            "classification":
                classification,

            "family":
                pattern_family(
                    classification
                ),

            "confidence":
                "medium",

            "reason":
                (
                    "The loop repeatedly updates the "
                    "same array element while the "
                    "current iterator does not "
                    "participate in the written index."
                ),

            "evidence": {
                "reduction_type":
                    "array_element",

                "updates":
                    array_reduction,
            }
        }

    # --------------------------------------------------------
    # STENCIL
    # --------------------------------------------------------

    stencil = (
        find_stencil_evidence(
            static_loop
        )
    )

    if stencil:

        classification = (
            "STENCIL_CANDIDATE"
        )

        return {
            "classification":
                classification,

            "family":
                pattern_family(
                    classification
                ),

            "confidence":
                stencil[
                    "confidence"
                ],

            "reason":
                (
                    "A regular multidimensional "
                    "neighborhood of array reads "
                    "was detected around the "
                    "written element."
                ),

            "evidence":
                stencil,
        }

    # --------------------------------------------------------
    # SYMBOLIC
    # --------------------------------------------------------

    if symbolic:

        classification = (
            "UNKNOWN_DEPENDENCE"
        )

        return {
            "classification":
                classification,

            "family":
                pattern_family(
                    classification
                ),

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
    # DOALL / MAP
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

            classification = (
                "DOALL_CANDIDATE"
            )

            return {
                "classification":
                    classification,

                "family":
                    pattern_family(
                        classification
                    ),

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
                        len(
                            same_location
                        ),

                    "iterator_in_write":
                        True,

                    "operators":
                        operators,
                }
            }

    # --------------------------------------------------------
    # NO DIRECT EVIDENCE
    # --------------------------------------------------------

    if not dependencies:

        classification = (
            "NO_DIRECT_EVIDENCE"
        )

        return {
            "classification":
                classification,

            "family":
                pattern_family(
                    classification
                ),

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

    classification = (
        "UNKNOWN"
    )

    return {
        "classification":
            classification,

        "family":
            pattern_family(
                classification
            ),

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

    for dependence_loop in (
        dependence_kernel.get(
            "loops",
            []
        )
    ):

        loop_id = (
            dependence_loop.get(
                "id"
            )
        )

        static_loop = None

        for candidate in (
            static_kernel.get(
                "loops",
                []
            )
        ):

            if (
                candidate.get("id")
                == loop_id
            ):

                static_loop = candidate
                break

        classification = (
            classify_loop(
                static_loop,
                dependence_loop
            )
        )

        classification[
            "loop_id"
        ] = loop_id

        classification[
            "iterator"
        ] = dependence_loop.get(
            "iterator"
        )

        loop_results.append(
            classification
        )

    # --------------------------------------------------------
    # Collect evidence
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

    stencil_loops = [
        result
        for result in loop_results
        if result["classification"]
        == "STENCIL_CANDIDATE"
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
    # MIXED
    #
    # Current strong Mixed pattern:
    #
    # MAP / DOALL + REDUCTION
    #
    # This corresponds naturally to the higher-level
    # MapReduce family.
    # --------------------------------------------------------

    if (
        doall_loops
        and reduction_loops
    ):

        kernel_class = (
            "MIXED_CANDIDATE"
        )

        if symbolic_loops:
            confidence = "medium"
        else:
            confidence = "high"

        reason = (
            "The kernel contains both "
            "MAP/DOALL and REDUCE/AGGREGATION "
            "regions."
        )

    # --------------------------------------------------------
    # WAVEFRONT
    # --------------------------------------------------------

    elif wavefront_loops:

        kernel_class = (
            "WAVEFRONT_CANDIDATE"
        )

        confidence = "high"

        reason = (
            "At least one loop contains "
            "resolved shifted dependences."
        )

    # --------------------------------------------------------
    # REDUCTION
    # --------------------------------------------------------

    elif reduction_loops:

        kernel_class = (
            "REDUCTION_CANDIDATE"
        )

        confidence = "medium"

        reason = (
            "At least one loop contains "
            "a reduction update."
        )

    # --------------------------------------------------------
    # STENCIL
    # --------------------------------------------------------

    elif stencil_loops:

        kernel_class = (
            "STENCIL_CANDIDATE"
        )

        if any(
            loop["confidence"] == "high"
            for loop in stencil_loops
        ):

            confidence = "high"

        else:

            confidence = "medium"

        reason = (
            "At least one loop contains "
            "a regular neighborhood access pattern."
        )

    # --------------------------------------------------------
    # DOALL
    # --------------------------------------------------------

    elif (
        doall_loops
        and not symbolic_loops
    ):

        kernel_class = (
            "DOALL_CANDIDATE"
        )

        confidence = "medium"

        reason = (
            "Independent-index candidates "
            "were detected and no shifted or "
            "symbolic dependences were found."
        )

    # --------------------------------------------------------
    # SYMBOLIC
    # --------------------------------------------------------

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

        "family":
            pattern_family(
                kernel_class
            ),

        "confidence":
            confidence,

        "reason":
            reason,

        "loops":
            loop_results,
    }


# ============================================================
# PRINTING
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
        f"Family: "
        f"{result['family']}"
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
            f"  Loop #{loop['loop_id']} "
            f"({loop['iterator']})"
        )

        print(
            f"    Pattern: "
            f"{loop['classification']}"
        )

        print(
            f"    Family: "
            f"{loop['family']}"
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

            for key, value in (
                evidence.items()
            ):

                print(
                    f"      {key}: "
                    f"{value}"
                )


# ============================================================
# MAIN
# ============================================================

def analyze(
    static_file,
    dependence_file
):

    static_data = (
        load_json(
            static_file
        )
    )

    dependence_data = (
        load_json(
            dependence_file
        )
    )

    print(
        "================================="
    )

    print(
        "TCC2 PATTERN CLASSIFIER v0.6"
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
        "version":
            "0.6",

        "source":
            static_data.get(
                "source"
            ),

        "kernels":
            [],
    }

    static_kernels = {
        kernel.get("name"):
            kernel

        for kernel in (
            static_data.get(
                "kernels",
                []
            )
        )
    }

    for dependence_kernel in (
        dependence_data.get(
            "kernels",
            []
        )
    ):

        name = (
            dependence_kernel.get(
                "name"
            )
        )

        static_kernel = (
            static_kernels.get(
                name
            )
        )

        if static_kernel is None:

            print(
                f"Kernel {name} "
                "não encontrado no "
                "Static Analyzer JSON."
            )

            continue

        result = (
            classify_kernel(
                static_kernel,
                dependence_kernel
            )
        )

        output[
            "kernels"
        ].append(
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
        .replace(
            "_dependences",
            ""
        )
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

    parser = (
        argparse.ArgumentParser()
    )

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