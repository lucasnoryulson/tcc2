import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "analysis"
    / "output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def get_line(node):

    loc = node.get(
        "loc",
        {}
    )

    if "line" in loc:
        return loc["line"]

    source_range = node.get(
        "range",
        {}
    )

    begin = source_range.get(
        "begin",
        {}
    )

    return begin.get(
        "line"
    )


def walk(node):

    yield node

    for child in node.get(
        "inner",
        []
    ):

        yield from walk(
            child
        )


def get_referenced_variables(node):

    variables = set()

    for item in walk(node):

        if item.get("kind") != "DeclRefExpr":
            continue

        referenced = item.get(
            "referencedDecl",
            {}
        )

        name = referenced.get(
            "name"
        )

        if name:
            variables.add(name)

    return sorted(
        variables
    )


def get_operators(node):

    operators = []

    interesting_kinds = {
        "BinaryOperator",
        "CompoundAssignOperator",
        "UnaryOperator",
    }

    for item in walk(node):

        if item.get("kind") not in interesting_kinds:
            continue

        opcode = item.get(
            "opcode"
        )

        if opcode:
            operators.append(
                opcode
            )

    return operators


def count_array_accesses(node):

    count = 0

    for item in walk(node):

        if item.get(
            "kind"
        ) == "ArraySubscriptExpr":

            count += 1

    return count


def extract_loops(
    node,
    current_depth=0,
    loops=None
):

    if loops is None:
        loops = []

    kind = node.get(
        "kind"
    )

    new_depth = current_depth

    if kind == "ForStmt":

        new_depth = (
            current_depth + 1
        )

        loop = {
            "id":
                f"loop_{len(loops) + 1}",

            "kind":
                "for",

            "line":
                get_line(node),

            "nesting_depth":
                new_depth,

            "referenced_variables":
                get_referenced_variables(
                    node
                ),

            "operators":
                get_operators(
                    node
                ),

            "array_access_count":
                count_array_accesses(
                    node
                ),
        }

        loops.append(
            loop
        )

    for child in node.get(
        "inner",
        []
    ):

        extract_loops(
            child,
            new_depth,
            loops
        )

    return loops


def run_clang_ast(
    source,
    function_name
):

    extension = source.suffix.lower()

    if extension in {
        ".cpp",
        ".cc",
        ".cxx"
    }:

        compiler = "clang++"

        language_args = [
            "-std=c++14"
        ]

    else:

        compiler = "clang"

        language_args = [
            "-std=c11"
        ]

    command = [
        compiler,
        *language_args,

        "-Xclang",
        "-ast-dump=json",

        "-Xclang",
        "-ast-dump-filter",

        "-Xclang",
        function_name,

        "-fsyntax-only",

        str(source),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print(
            "CLANG ERROR"
        )

        print(
            result.stderr
        )

        sys.exit(1)

    try:

        return json.loads(
            result.stdout
        )

    except json.JSONDecodeError:

        print(
            "Não foi possível "
            "interpretar o AST JSON."
        )

        print(
            result.stdout[:1000]
        )

        sys.exit(1)


def main():

    if len(sys.argv) != 3:

        print(
            "Uso:"
        )

        print(
            "python3 scripts/"
            "static_analyzer.py "
            "<source> <function>"
        )

        sys.exit(1)

    source = Path(
        sys.argv[1]
    ).resolve()

    function_name = (
        sys.argv[2]
    )

    if not source.exists():

        print(
            f"Arquivo não encontrado: "
            f"{source}"
        )

        sys.exit(1)

    print(
        "================================"
    )

    print(
        "TCC2 STATIC ANALYZER"
    )

    print(
        "================================"
    )

    print(
        f"Source: {source}"
    )

    print(
        f"Function: {function_name}"
    )

    print(
        "\n[1/2] Gerando Clang AST..."
    )

    ast = run_clang_ast(
        source,
        function_name
    )

    print(
        "AST: OK"
    )

    print(
        "\n[2/2] Extraindo loops..."
    )

    loops = extract_loops(
        ast
    )

    analysis = {
        "source":
            str(source),

        "function":
            function_name,

        "loop_count":
            len(loops),

        "loops":
            loops,
    }

    print(
        json.dumps(
            analysis,
            indent=2
        )
    )

    output_file = (
        OUTPUT_DIR
        /
        (
            source.stem
            + "_"
            + function_name
            + ".json"
        )
    )

    with output_file.open(
        "w"
    ) as file:

        json.dump(
            analysis,
            file,
            indent=2
        )

    print(
        f"\nAnalysis saved: "
        f"{output_file}"
    )


if __name__ == "__main__":
    main()
