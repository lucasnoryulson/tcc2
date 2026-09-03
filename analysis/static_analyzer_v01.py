import argparse
import json
import subprocess
import sys
from pathlib import Path


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


def find_kernel_functions(node):
    kernels = []

    if (
        node.get("kind") == "FunctionDecl"
        and node.get("name", "").startswith("kernel_")
    ):
        kernels.append(node)

    for child in node.get("inner", []):
        kernels.extend(
            find_kernel_functions(child)
        )

    return kernels


def get_location(node):
    source_range = node.get("range", {})

    begin = source_range.get("begin", {})
    end = source_range.get("end", {})

    return {
        "start_line": begin.get("line"),
        "start_column": begin.get("col"),
        "end_line": end.get("line"),
        "end_column": end.get("col"),
    }


def collect_referenced_variables(node):
    variables = set()

    if node.get("kind") == "DeclRefExpr":

        referenced = node.get(
            "referencedDecl",
            {}
        )

        name = referenced.get("name")

        if name:
            variables.add(name)

    for child in node.get("inner", []):
        variables.update(
            collect_referenced_variables(child)
        )

    return variables


def find_base_array(node):
    if node.get("kind") == "DeclRefExpr":

        referenced = node.get(
            "referencedDecl",
            {}
        )

        return referenced.get("name")

    for child in node.get("inner", []):

        result = find_base_array(child)

        if result:
            return result

    return None


def collect_array_accesses(node):
    arrays = []

    if node.get("kind") == "ArraySubscriptExpr":

        name = find_base_array(node)

        if name:
            arrays.append(name)

    for child in node.get("inner", []):
        arrays.extend(
            collect_array_accesses(child)
        )

    return arrays


def collect_operators(node):
    operators = []

    if node.get("kind") == "BinaryOperator":

        opcode = node.get("opcode")

        if opcode:
            operators.append(opcode)

    if node.get("kind") == "CompoundAssignOperator":

        opcode = node.get("opcode")

        if opcode:
            operators.append(opcode)

    for child in node.get("inner", []):
        operators.extend(
            collect_operators(child)
        )

    return operators


def extract_loops(
    node,
    nesting_depth=0,
    loops=None
):

    if loops is None:
        loops = []

    is_loop = node.get("kind") == "ForStmt"

    if is_loop:

        location = get_location(node)

        variables = sorted(
            collect_referenced_variables(node)
        )

        arrays = sorted(
            set(
                collect_array_accesses(node)
            )
        )

        operators = collect_operators(node)

        loop_data = {
            "id": len(loops) + 1,

            "nesting_depth":
                nesting_depth,

            "start_line":
                location["start_line"],

            "end_line":
                location["end_line"],

            "variables":
                variables,

            "arrays":
                arrays,

            "operators":
                operators,
        }

        loops.append(loop_data)

    next_depth = (
        nesting_depth + 1
        if is_loop
        else nesting_depth
    )

    for child in node.get("inner", []):

        extract_loops(
            child,
            next_depth,
            loops
        )

    return loops


def analyze(source, include_dirs):

    print("==============================")
    print("TCC2 STATIC ANALYZER v0.1")
    print("==============================")

    print(f"Source: {source}")

    ast = run_clang(
        source,
        include_dirs
    )

    kernels = find_kernel_functions(ast)

    if not kernels:
        print("Nenhuma função kernel_* encontrada.")
        sys.exit(1)

    final_result = {
        "source": str(source),
        "kernels": []
    }

    for kernel in kernels:

        name = kernel.get(
            "name",
            "unknown"
        )

        loops = extract_loops(kernel)

        print()
        print(f"Kernel: {name}")
        print(f"Loops encontrados: {len(loops)}")

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
                "  Variables: "
                + ", ".join(
                    loop["variables"]
                )
            )

            print(
                "  Arrays: "
                + ", ".join(
                    loop["arrays"]
                )
            )

            print(
                "  Operators: "
                + ", ".join(
                    loop["operators"]
                )
            )

        final_result["kernels"].append({
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

    output_file = (
        output_dir
        / f"{source.stem}_analysis.json"
    )

    output_file.write_text(
        json.dumps(
            final_result,
            indent=2
        )
    )

    print()
    print("==============================")
    print(f"JSON salvo em: {output_file}")
    print("==============================")


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
