import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


# ============================================================
# CLANG
# ============================================================

def run_clang(source, include_dirs):

    command = [
        "clang",
        "-Xclang",
        "-ast-dump=json",
        "-fsyntax-only",
        "-Wno-unknown-pragmas",
        "-DLARGE_DATASET",
    ]

    for include_dir in include_dirs:
        command.append(
            f"-I{include_dir}"
        )

    command.append(str(source))

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("Erro ao executar Clang:")
        print(result.stderr)
        sys.exit(1)

    return json.loads(result.stdout)


# ============================================================
# SOURCE TEXT
# ============================================================

def get_offset(location):

    if not location:
        return None

    if "offset" in location:
        return location["offset"]

    expansion = location.get(
        "expansionLoc",
        {}
    )

    if "offset" in expansion:
        return expansion["offset"]

    spelling = location.get(
        "spellingLoc",
        {}
    )

    return spelling.get("offset")


def get_token_length(location):

    if not location:
        return 0

    if "tokLen" in location:
        return location["tokLen"]

    expansion = location.get(
        "expansionLoc",
        {}
    )

    if "tokLen" in expansion:
        return expansion["tokLen"]

    spelling = location.get(
        "spellingLoc",
        {}
    )

    return spelling.get(
        "tokLen",
        0
    )


def source_text(node, source_code):

    node_range = node.get(
        "range",
        {}
    )

    begin = node_range.get(
        "begin",
        {}
    )

    end = node_range.get(
        "end",
        {}
    )

    start = get_offset(begin)
    finish = get_offset(end)

    if start is None or finish is None:
        return None

    finish += get_token_length(end)

    if start < 0:
        return None

    if finish > len(source_code):
        return None

    return source_code[
        start:finish
    ].strip()


# ============================================================
# GENERIC AST HELPERS
# ============================================================

def find_kernel_functions(node):

    kernels = []

    if (
        node.get("kind")
        == "FunctionDecl"
        and node.get(
            "name",
            ""
        ).startswith("kernel_")
    ):
        kernels.append(node)

    for child in node.get(
        "inner",
        []
    ):

        kernels.extend(
            find_kernel_functions(child)
        )

    return kernels


def get_location(node):

    source_range = node.get(
        "range",
        {}
    )

    begin = source_range.get(
        "begin",
        {}
    )

    end = source_range.get(
        "end",
        {}
    )

    return {
        "start_line":
            begin.get("line"),

        "start_column":
            begin.get("col"),

        "end_line":
            end.get("line"),

        "end_column":
            end.get("col"),
    }


# ============================================================
# ARRAY ACCESS
# ============================================================

def find_decl_name(node):

    if node.get(
        "kind"
    ) == "DeclRefExpr":

        referenced = node.get(
            "referencedDecl",
            {}
        )

        return referenced.get(
            "name"
        )

    for child in node.get(
        "inner",
        []
    ):

        result = find_decl_name(
            child
        )

        if result:
            return result

    return None


def parse_array_access(
    node,
    source_code
):
    """
    Reconstruct an ArraySubscriptExpr using the AST.

    This works even when accesses occur inside macro
    expansions such as max_score() and match().

    Examples:

        C[i][j]
        A[i][k]
        table[i+1][j-1]
    """

    node = unwrap_expression(
        node
    )

    if (
        not node
        or node.get("kind")
        != "ArraySubscriptExpr"
    ):
        return None

    children = node.get(
        "inner",
        []
    )

    if len(children) < 2:
        return None

    base_node = unwrap_expression(
        children[0]
    )

    index_node = children[1]

    indices = []

    #
    # Multidimensional array:
    #
    # table[i][j]
    #
    # The base of the outer ArraySubscriptExpr
    # is another ArraySubscriptExpr.
    #
    if (
        base_node
        and base_node.get("kind")
        == "ArraySubscriptExpr"
    ):

        parent_access = (
            parse_array_access(
                base_node,
                source_code
            )
        )

        if not parent_access:
            return None

        array_name = (
            parent_access["array"]
        )

        indices.extend(
            parent_access["indices"]
        )

    else:

        array_name = find_decl_name(
            base_node
        )

    if not array_name:
        return None

    index_text = expression_to_text(
        index_node,
        source_code
    )

    indices.append(
        index_text
    )

    expression = array_name

    for index in indices:

        expression += (
            f"[{index}]"
        )

    return {
        "array": array_name,
        "indices": indices,
        "expression": expression,
    }

def unwrap_expression(node):
    """
    Remove AST wrapper nodes that do not change the
    logical expression.

    Clang commonly places nodes such as ImplicitCastExpr
    around array bases and indices.
    """

    wrapper_kinds = {
        "ImplicitCastExpr",
        "ParenExpr",
        "CStyleCastExpr",
        "ConstantExpr",
        "ExprWithCleanups",
        "FullExpr",
    }

    current = node

    while (
        current
        and current.get("kind") in wrapper_kinds
    ):

        children = current.get(
            "inner",
            []
        )

        if len(children) != 1:
            break

        current = children[0]

    return current


def expression_to_text(
    node,
    source_code
):
    """
    Reconstruct simple expressions directly from the AST.

    This is more reliable than source offsets when the
    expression originated inside a C macro expansion.

    Examples:

        i
        j - 1
        i + 1
        k + 1
    """

    node = unwrap_expression(node)

    if not node:
        return "?"

    kind = node.get("kind")

    if kind == "DeclRefExpr":

        referenced = node.get(
            "referencedDecl",
            {}
        )

        return referenced.get(
            "name",
            "?"
        )

    if kind == "IntegerLiteral":

        return str(
            node.get(
                "value",
                "?"
            )
        )

    if kind == "FloatingLiteral":

        return str(
            node.get(
                "value",
                "?"
            )
        )

    if kind == "CharacterLiteral":

        return str(
            node.get(
                "value",
                "?"
            )
        )

    if kind == "UnaryOperator":

        children = node.get(
            "inner",
            []
        )

        opcode = node.get(
            "opcode",
            ""
        )

        if children:

            operand = expression_to_text(
                children[0],
                source_code
            )

            if node.get("isPostfix"):

                return (
                    f"{operand}{opcode}"
                )

            return (
                f"{opcode}{operand}"
            )

    if kind == "BinaryOperator":

        children = node.get(
            "inner",
            []
        )

        if len(children) >= 2:

            left = expression_to_text(
                children[0],
                source_code
            )

            right = expression_to_text(
                children[1],
                source_code
            )

            opcode = node.get(
                "opcode",
                "?"
            )

            return (
                f"{left}{opcode}{right}"
            )

    if kind == "ArraySubscriptExpr":

        access = parse_array_access(
            node,
            source_code
        )

        if access:
            return access[
                "expression"
            ]

    #
    # Fallback for AST nodes that have a valid
    # source range.
    #
    text = source_text(
        node,
        source_code
    )

    if text:

        text = re.sub(
            r"\s+",
            "",
            text
        )

        return text

    return "?"

def collect_array_reads(
    node,
    source_code,
    results=None
):

    if results is None:
        results = []

    kind = node.get(
        "kind"
    )

    #
    # Do not descend into nested loops.
    # They will receive their own analysis.
    #
    if kind == "ForStmt":
        return results

    #
    # Assignment:
    #
    #   A[i] = B[i]
    #
    # LHS is WRITE.
    # RHS is READ.
    #
    if (
        kind == "BinaryOperator"
        and node.get("opcode") == "="
    ):

        children = node.get(
            "inner",
            []
        )

        if len(children) >= 2:

            collect_array_reads(
                children[1],
                source_code,
                results
            )

        return results

    #
    # Compound assignment:
    #
    #   C[i] += A[i]
    #
    # LHS is both READ and WRITE.
    #
    if kind == "CompoundAssignOperator":

        children = node.get(
            "inner",
            []
        )

        for child in children:

            collect_array_reads(
                child,
                source_code,
                results
            )

        return results

    #
    # Array access.
    #
    if kind == "ArraySubscriptExpr":

        access = parse_array_access(
            node,
            source_code
        )

        if (
            access
            and access["array"]
        ):
            results.append(
                access
            )

        #
        # Do NOT recursively enter the nested
        # ArraySubscriptExpr base, otherwise
        # C[i][j] also becomes C[i].
        #
        return results

    for child in node.get(
        "inner",
        []
    ):

        collect_array_reads(
            child,
            source_code,
            results
        )

    return results


def collect_array_writes(
    node,
    source_code,
    results=None
):

    if results is None:
        results = []

    kind = node.get(
        "kind"
    )

    if kind == "ForStmt":
        return results

    #
    # A[i] = ...
    #
    if (
        kind == "BinaryOperator"
        and node.get("opcode") == "="
    ):

        children = node.get(
            "inner",
            []
        )

        if children:

            lhs = children[0]

            if (
                lhs.get("kind")
                == "ArraySubscriptExpr"
            ):

                access = parse_array_access(
                    lhs,
                    source_code
                )

                if access:
                    results.append(
                        access
                    )

        #
        # There may be assignments deeper
        # inside RHS expressions.
        #
        for child in children[1:]:

            collect_array_writes(
                child,
                source_code,
                results
            )

        return results

    #
    # C[i] += ...
    # C[i] *= ...
    #
    if kind == "CompoundAssignOperator":

        children = node.get(
            "inner",
            []
        )

        if children:

            lhs = children[0]

            if (
                lhs.get("kind")
                == "ArraySubscriptExpr"
            ):

                access = parse_array_access(
                    lhs,
                    source_code
                )

                if access:
                    results.append(
                        access
                    )

        for child in children[1:]:

            collect_array_writes(
                child,
                source_code,
                results
            )

        return results

    for child in node.get(
        "inner",
        []
    ):

        collect_array_writes(
            child,
            source_code,
            results
        )

    return results


def collect_scalar_updates(
    node,
    source_code,
    results=None
):
    """
    Detect compound assignments to scalar variables.

    Example:

        sum += A[i] * B[i]

    becomes:

        {
            "variable": "sum",
            "operator": "+=",
            "rhs": "A[i]*B[i]"
        }

    Array updates such as C[i][j] += ...
    are intentionally ignored here because they are
    handled by the array READ/WRITE analysis.
    """

    if results is None:
        results = []

    kind = node.get("kind")

    #
    # Nested loops receive their own analysis.
    #
    if kind == "ForStmt":
        return results

    if kind == "CompoundAssignOperator":

        children = node.get(
            "inner",
            []
        )

        if len(children) >= 2:

            lhs = unwrap_expression(
                children[0]
            )

            rhs = children[1]

            if (
                lhs
                and lhs.get("kind")
                == "DeclRefExpr"
            ):

                referenced = lhs.get(
                    "referencedDecl",
                    {}
                )

                variable = referenced.get(
                    "name"
                )

                if variable:

                    operator = node.get(
                        "opcode"
                    )

                    rhs_text = expression_to_text(
                        rhs,
                        source_code
                    )

                    results.append({
                        "variable":
                            variable,

                        "operator":
                            operator,

                        "rhs":
                            rhs_text,

                        "expression":
                            (
                                f"{variable} "
                                f"{operator} "
                                f"{rhs_text}"
                            ),
                    })

    for child in node.get(
        "inner",
        []
    ):

        collect_scalar_updates(
            child,
            source_code,
            results
        )

    return results
# ============================================================
# OPERATORS
# ============================================================

def collect_operators(
    node,
    operators=None
):

    if operators is None:
        operators = []

    kind = node.get(
        "kind"
    )

    #
    # Nested loops will be analyzed
    # separately.
    #
    if kind == "ForStmt":
        return operators

    if kind in (
        "BinaryOperator",
        "CompoundAssignOperator",
        "UnaryOperator",
    ):

        opcode = node.get(
            "opcode"
        )

        if opcode:
            operators.append(
                opcode
            )

    for child in node.get(
        "inner",
        []
    ):

        collect_operators(
            child,
            operators
        )

    return operators


# ============================================================
# LOOP HEADER
# ============================================================

def extract_for_header(
    loop_node,
    source_code
):

    text = source_text(
        loop_node,
        source_code
    )

    if not text:
        return {
            "iterator": None,
            "initialization": None,
            "condition": None,
            "increment": None,
        }

    match = re.search(
        r"\bfor\s*\((.*?)\)",
        text,
        re.DOTALL
    )

    if not match:

        return {
            "iterator": None,
            "initialization": None,
            "condition": None,
            "increment": None,
        }

    header = match.group(1)

    pieces = header.split(";")

    if len(pieces) != 3:

        return {
            "iterator": None,
            "initialization": header,
            "condition": None,
            "increment": None,
        }

    initialization = pieces[0].strip()
    condition = pieces[1].strip()
    increment = pieces[2].strip()

    iterator = None

    iterator_match = re.search(
        r"(?:[A-Za-z_][A-Za-z0-9_]*\s+)?"
        r"([A-Za-z_][A-Za-z0-9_]*)"
        r"\s*=",
        initialization
    )

    if iterator_match:

        iterator = (
            iterator_match.group(1)
        )

    return {
        "iterator": iterator,
        "initialization":
            initialization,

        "condition":
            condition,

        "increment":
            increment,
    }


# ============================================================
# LOOP BODY
# ============================================================

def find_loop_body(loop_node):

    children = loop_node.get(
        "inner",
        []
    )

    #
    # Usually the body is the last child.
    #
    for child in reversed(children):

        if child.get("kind") in (
            "CompoundStmt",
            "ForStmt",
            "IfStmt",
        ):
            return child

    if children:
        return children[-1]

    return None


def unique_accesses(accesses):

    result = []
    seen = set()

    for access in accesses:

        key = access.get(
            "expression"
        )

        if key in seen:
            continue

        seen.add(key)

        result.append(access)

    return result


# ============================================================
# LOOP EXTRACTION
# ============================================================

def extract_loops(
    node,
    source_code,
    nesting_depth=0,
    loops=None
):

    if loops is None:
        loops = []

    kind = node.get(
        "kind"
    )

    is_loop = (
        kind == "ForStmt"
    )

    if is_loop:

        location = get_location(
            node
        )

        header = extract_for_header(
            node,
            source_code
        )

        body = find_loop_body(
            node
        )

        if body:

            reads = unique_accesses(
                collect_array_reads(
                    body,
                    source_code
                )
            )

            writes = unique_accesses(
                collect_array_writes(
                    body,
                    source_code
                )
            )

            operators = collect_operators(
                body
            )

            scalar_updates = collect_scalar_updates(
                body,
                source_code
            )

        else:

            reads = []
            writes = []
            operators = []
            scalar_updates = []

        loop_data = {

            "id":
                len(loops) + 1,

            "nesting_depth":
                nesting_depth,

            "start_line":
                location["start_line"],

            "end_line":
                location["end_line"],

            "iterator":
                header["iterator"],

            "initialization":
                header["initialization"],

            "condition":
                header["condition"],

            "increment":
                header["increment"],

            "reads":
                reads,

            "writes":
                writes,

            "operators":
                operators,

            "scalar_updates":
                scalar_updates,
        }

        loops.append(
            loop_data
        )

    next_depth = (
        nesting_depth + 1
        if is_loop
        else nesting_depth
    )

    for child in node.get(
        "inner",
        []
    ):

        extract_loops(
            child,
            source_code,
            next_depth,
            loops
        )

    return loops


# ============================================================
# OUTPUT
# ============================================================

def print_accesses(
    label,
    accesses
):

    print(f"  {label}:")

    if not accesses:

        print("    (none)")
        return

    for access in accesses:

        print(
            "    "
            + access["expression"]
        )


def analyze(
    source,
    include_dirs
):

    print(
        "=============================="
    )

    print(
        "TCC2 STATIC ANALYZER v0.2"
    )

    print(
        "=============================="
    )

    print(
        f"Source: {source}"
    )

    source_code = (
        source.read_text(
            errors="replace"
        )
    )

    ast = run_clang(
        source,
        include_dirs
    )

    kernels = find_kernel_functions(
        ast
    )

    if not kernels:

        print(
            "Nenhuma função kernel_* encontrada."
        )

        sys.exit(1)

    final_result = {
        "version": "0.2",
        "source": str(source),
        "kernels": []
    }

    for kernel in kernels:

        name = kernel.get(
            "name",
            "unknown"
        )

        loops = extract_loops(
            kernel,
            source_code
        )

        print()
        print(
            f"Kernel: {name}"
        )

        print(
            f"Loops encontrados: {len(loops)}"
        )

        for loop in loops:

            print()
            print(
                f"Loop #{loop['id']}"
            )

            print(
                f"  Depth: "
                f"{loop['nesting_depth']}"
            )

            print(
                f"  Lines: "
                f"{loop['start_line']} - "
                f"{loop['end_line']}"
            )

            print(
                f"  Iterator: "
                f"{loop['iterator']}"
            )

            print(
                f"  Init: "
                f"{loop['initialization']}"
            )

            print(
                f"  Condition: "
                f"{loop['condition']}"
            )

            print(
                f"  Increment: "
                f"{loop['increment']}"
            )

            print_accesses(
                "READS",
                loop["reads"]
            )

            print_accesses(
                "WRITES",
                loop["writes"]
            )

            print(
                "  Operators: "
                + (
                    ", ".join(
                        loop["operators"]
                    )
                    if loop["operators"]
                    else "(none)"
                )
            )

        final_result[
            "kernels"
        ].append({
            "name": name,
            "loops": loops
        })

    output_dir = (
        Path(__file__).resolve().parent
        / "output"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    #
    # Use kernel name instead of source filename.
    #
    if len(kernels) == 1:

        kernel_name = kernels[0].get(
            "name",
            source.stem
        )

        if kernel_name.startswith(
            "kernel_"
        ):
            kernel_name = (
                kernel_name[
                    len("kernel_"):
                ]
            )

        output_name = (
            f"{kernel_name}_analysis.json"
        )

    else:

        output_name = (
            f"{source.stem}_analysis.json"
        )

    output_file = (
        output_dir
        / output_name
    )

    output_file.write_text(
        json.dumps(
            final_result,
            indent=2
        )
    )

    print()
    print(
        "=============================="
    )

    print(
        f"JSON salvo em: "
        f"{output_file}"
    )

    print(
        "=============================="
    )


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "source",
        type=Path
    )

    parser.add_argument(
        "--include",
        action="append",
        default=[]
    )

    args = parser.parse_args()

    analyze(
        args.source.resolve(),
        [
            Path(path).resolve()
            for path in args.include
        ]
    )


if __name__ == "__main__":
    main()
