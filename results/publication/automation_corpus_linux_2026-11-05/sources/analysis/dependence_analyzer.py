import argparse
import json
import re
import sys
from pathlib import Path


# ============================================================
# AFFINE INDEX PARSER
# ============================================================

def remove_outer_parentheses(expression):
    """
    Remove simple outer parentheses.

    Examples:

        (i)     -> i
        ((j))   -> j
    """

    expression = expression.strip()

    changed = True

    while changed:
        changed = False

        if (
            expression.startswith("(")
            and expression.endswith(")")
        ):
            expression = expression[1:-1].strip()
            changed = True

    return expression


def parse_affine_index(expression):
    """
    Parse simple affine array indices.

    Supported examples:

        i
        j
        k
        i+1
        i-1
        j+2
        k-3

    Returns:

        {
            "variable": "i",
            "offset": 1
        }

    Complex expressions are intentionally left unresolved.
    """

    if expression is None:
        return None

    expression = expression.replace(
        " ",
        ""
    )

    expression = remove_outer_parentheses(
        expression
    )

    pattern = (
        r"^"
        r"([A-Za-z_][A-Za-z0-9_]*)"
        r"(?:(\+|-)(\d+))?"
        r"$"
    )

    match = re.match(
        pattern,
        expression
    )

    if not match:
        return None

    variable = match.group(1)

    sign = match.group(2)
    value = match.group(3)

    offset = 0

    if value is not None:

        offset = int(value)

        if sign == "-":
            offset *= -1

    return {
        "variable": variable,
        "offset": offset,
    }


# ============================================================
# ACCESS COMPARISON
# ============================================================

def compare_indices(
    write_index,
    read_index
):
    """
    Compare one dimension of a WRITE with one dimension
    of a READ.

    Example:

        WRITE: i
        READ:  i+1

        offset = +1
    """

    write_affine = parse_affine_index(
        write_index
    )

    read_affine = parse_affine_index(
        read_index
    )

    if (
        write_affine is None
        or read_affine is None
    ):
        return {
            "resolved": False,
            "write": write_index,
            "read": read_index,
            "reason": "non_affine_expression",
        }

    if (
        write_affine["variable"]
        != read_affine["variable"]
    ):
        return {
            "resolved": False,
            "write": write_index,
            "read": read_index,
            "write_variable":
                write_affine["variable"],
            "read_variable":
                read_affine["variable"],
            "reason": "different_iterators",
        }

    offset = (
        read_affine["offset"]
        - write_affine["offset"]
    )

    return {
        "resolved": True,
        "variable":
            write_affine["variable"],
        "offset":
            offset,
        "write":
            write_index,
        "read":
            read_index,
    }


def compare_accesses(
    write_access,
    read_access
):
    """
    Compare READ and WRITE accesses to the same array.

    Example:

        WRITE:
            table[i][j]

        READ:
            table[i+1][j-1]

        Result:
            [+1, -1]
    """

    if (
        write_access["array"]
        != read_access["array"]
    ):
        return None

    write_indices = write_access.get(
        "indices",
        []
    )

    read_indices = read_access.get(
        "indices",
        []
    )

    if (
        len(write_indices)
        != len(read_indices)
    ):
        return {
            "array":
                write_access["array"],

            "write":
                write_access["expression"],

            "read":
                read_access["expression"],

            "relation":
                "rank_mismatch",

            "resolved":
                False,
        }

    dimensions = []

    all_resolved = True

    offsets = []

    carried_by = []

    for write_index, read_index in zip(
        write_indices,
        read_indices
    ):

        comparison = compare_indices(
            write_index,
            read_index
        )

        dimensions.append(
            comparison
        )

        if not comparison["resolved"]:

            all_resolved = False
            offsets.append(None)

        else:

            offset = comparison[
                "offset"
            ]

            offsets.append(
                offset
            )

            if offset != 0:

                carried_by.append(
                    comparison[
                        "variable"
                    ]
                )

    if all_resolved:

        if all(
            offset == 0
            for offset in offsets
        ):

            relation = "same_location"

        else:

            relation = "shifted_access"

    else:

        relation = "symbolic_relation"

    return {
        "array":
            write_access["array"],

        "write":
            write_access["expression"],

        "read":
            read_access["expression"],

        "resolved":
            all_resolved,

        "relation":
            relation,

        "offsets":
            offsets,

        "carried_by":
            sorted(set(carried_by)),

        "dimensions":
            dimensions,
    }


# ============================================================
# LOOP ANALYSIS
# ============================================================

def analyze_loop(loop):
    """
    Compare all READS against all WRITES belonging
    to the same array.
    """

    dependencies = []

    reads = loop.get(
        "reads",
        []
    )

    writes = loop.get(
        "writes",
        []
    )

    for write_access in writes:

        for read_access in reads:

            if (
                write_access.get("array")
                != read_access.get("array")
            ):
                continue

            dependency = (
                compare_accesses(
                    write_access,
                    read_access
                )
            )

            if dependency:
                dependencies.append(
                    dependency
                )

    return dependencies


# ============================================================
# PRINTING
# ============================================================

def format_offset(offset):
    if offset is None:
        return "?"

    if offset > 0:
        return f"+{offset}"

    return str(offset)


def print_dependency(
    dependency
):

    print(
        f"      WRITE: "
        f"{dependency['write']}"
    )

    print(
        f"      READ:  "
        f"{dependency['read']}"
    )

    print(
        f"      Relation: "
        f"{dependency['relation']}"
    )

    offsets = dependency.get(
        "offsets"
    )

    if offsets is not None:

        formatted = ", ".join(
            format_offset(offset)
            for offset in offsets
        )

        print(
            f"      Offset: "
            f"[{formatted}]"
        )

    carried_by = dependency.get(
        "carried_by",
        []
    )

    if carried_by:

        print(
            "      Carried by: "
            + ", ".join(carried_by)
        )

    print()


# ============================================================
# ANALYZER
# ============================================================

def analyze(input_file):

    data = json.loads(
        input_file.read_text()
    )

    print(
        "=================================="
    )

    print(
        "TCC2 DEPENDENCE ANALYZER v0.3"
    )

    print(
        "=================================="
    )

    print(
        f"Input: {input_file}"
    )

    output = {
        "version": "0.3",
        "source":
            data.get("source"),
        "kernels": [],
    }

    for kernel in data.get(
        "kernels",
        []
    ):

        kernel_name = kernel.get(
            "name",
            "unknown"
        )

        print()
        print(
            f"Kernel: {kernel_name}"
        )

        kernel_output = {
            "name":
                kernel_name,
            "loops": [],
        }

        for loop in kernel.get(
            "loops",
            []
        ):

            dependencies = (
                analyze_loop(loop)
            )

            print()
            print(
                f"  Loop #{loop['id']}"
            )

            print(
                f"    Iterator: "
                f"{loop.get('iterator')}"
            )

            if not dependencies:

                print(
                    "    Dependence candidates: "
                    "(none)"
                )

            else:

                print(
                    f"    Dependence candidates: "
                    f"{len(dependencies)}"
                )

                print()

                for dependency in dependencies:

                    print_dependency(
                        dependency
                    )

            kernel_output[
                "loops"
            ].append({
                "id":
                    loop["id"],

                "iterator":
                    loop.get(
                        "iterator"
                    ),

                "dependencies":
                    dependencies,
            })

        output[
            "kernels"
        ].append(
            kernel_output
        )

    output_dir = (
        input_file.parent
    )

    source_stem = (
        input_file.stem
        .replace(
            "_analysis",
            ""
        )
    )

    output_file = (
        output_dir
        / (
            source_stem
            + "_dependences.json"
        )
    )

    output_file.write_text(
        json.dumps(
            output,
            indent=2
        )
    )

    print()
    print(
        "=================================="
    )

    print(
        f"JSON salvo em: {output_file}"
    )

    print(
        "=================================="
    )


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "input",
        type=Path,
        help=(
            "JSON produzido pelo "
            "static_analyzer.py"
        )
    )

    args = parser.parse_args()

    input_file = (
        args.input.resolve()
    )

    if not input_file.exists():

        print(
            f"Arquivo não encontrado: "
            f"{input_file}"
        )

        sys.exit(1)

    analyze(
        input_file
    )


if __name__ == "__main__":
    main()
