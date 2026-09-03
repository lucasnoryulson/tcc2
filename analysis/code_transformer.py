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
# HELPERS
# ============================================================

def find_static_kernel(
    static_data,
    kernel_name
):
    for kernel in static_data.get(
        "kernels",
        []
    ):

        if kernel.get("name") == kernel_name:
            return kernel

    return None


def find_loop(
    static_kernel,
    loop_id
):
    for loop in static_kernel.get(
        "loops",
        []
    ):

        if loop.get("id") == loop_id:
            return loop

    return None


def leading_whitespace(line):
    return line[
        :len(line) - len(line.lstrip())
    ]


# ============================================================
# REDUCTION TRANSFORMATION
# ============================================================

def transform_scalar_reduction(
    source_lines,
    static_kernel,
    reduction_plan
):
    """
    Insert an OpenMP reduction pragma before the
    target loop.

    Example:

        for (int i = 0; i < n; i++)

    becomes:

        #pragma omp parallel for reduction(+:sum) schedule(static)
        for (int i = 0; i < n; i++)
    """

    loop_id = reduction_plan.get(
        "loop_id"
    )

    loop = find_loop(
        static_kernel,
        loop_id
    )

    if loop is None:

        raise RuntimeError(
            f"Loop #{loop_id} não encontrado "
            "no Static Analyzer JSON."
        )

    start_line = loop.get(
        "start_line"
    )

    if start_line is None:

        raise RuntimeError(
            f"Loop #{loop_id} não possui "
            "start_line."
        )

    #
    # JSON line numbers are 1-based.
    # Python list indices are 0-based.
    #
    index = start_line - 1

    if (
        index < 0
        or index >= len(source_lines)
    ):

        raise RuntimeError(
            f"Linha inválida para loop #{loop_id}: "
            f"{start_line}"
        )

    target_line = source_lines[index]

    indentation = leading_whitespace(
        target_line
    )

    clause = reduction_plan.get(
        "openmp_clause"
    )

    schedule = reduction_plan.get(
        "schedule",
        "static"
    )

    if not clause:

        raise RuntimeError(
            "Reduction plan não contém "
            "openmp_clause."
        )

    pragma = (
        indentation
        + "#pragma omp parallel for "
        + clause
        + f" schedule({schedule})\n"
    )

    marker = (
        indentation
        + "/* TCC2 AUTO-GENERATED: "
        + "REDUCTION */\n"
    )

    #
    # Avoid inserting the same transformation twice.
    #
    previous_text = ""

    if index > 0:
        previous_text = source_lines[
            index - 1
        ]

    if "#pragma omp parallel for" in previous_text:

        raise RuntimeError(
            "O loop já parece possuir uma "
            "diretiva OpenMP."
        )

    source_lines[index:index] = [
        marker,
        pragma,
    ]

    return {
        "loop_id":
            loop_id,

        "start_line":
            start_line,

        "pragma":
            pragma.strip(),

        "reduction_variable":
            reduction_plan.get(
                "variable"
            ),

        "reduction_operator":
            reduction_plan.get(
                "operator"
            ),
    }


# ============================================================
# STRATEGY DISPATCH
# ============================================================

def apply_strategy(
    source_lines,
    static_kernel,
    strategy
):
    strategy_type = strategy.get(
        "strategy"
    )

    transformations = []

    # --------------------------------------------------------
    # REDUCTION
    # --------------------------------------------------------

    if strategy_type == "REDUCTION":

        reductions = strategy.get(
            "reductions",
            []
        )

        if not reductions:

            raise RuntimeError(
                "Strategy REDUCTION sem "
                "reductions."
            )

        #
        # Insert from later source lines to earlier ones.
        # This prevents line-number shifts if multiple
        # transformations are inserted.
        #
        reductions = sorted(
            reductions,
            key=lambda item: (
                find_loop(
                    static_kernel,
                    item.get("loop_id")
                ) or {}
            ).get(
                "start_line",
                0
            ),
            reverse=True,
        )

        for reduction in reductions:

            if (
                reduction.get(
                    "reduction_type"
                )
                != "scalar"
            ):

                raise RuntimeError(
                    "Code Transformer v0.1 "
                    "suporta apenas redução escalar "
                    "direta."
                )

            if not reduction.get(
                "direct_code_transformation",
                False
            ):

                raise RuntimeError(
                    "Planner não autorizou "
                    "transformação direta."
                )

            result = (
                transform_scalar_reduction(
                    source_lines,
                    static_kernel,
                    reduction
                )
            )

            transformations.append(
                result
            )

        return transformations

    # --------------------------------------------------------
    # EVERYTHING ELSE
    # --------------------------------------------------------

    raise RuntimeError(
        f"Strategy '{strategy_type}' ainda não "
        "é suportada pelo Code Transformer v0.1."
    )


# ============================================================
# TRANSFORM
# ============================================================

def transform(
    source_file,
    static_file,
    strategy_file,
    output_file
):
    static_data = load_json(
        static_file
    )

    strategy_data = load_json(
        strategy_file
    )

    plans = strategy_data.get(
        "plans",
        []
    )

    if not plans:

        raise RuntimeError(
            "Strategy JSON não contém planos."
        )

    #
    # v0.1 handles one kernel per file.
    #
    plan = plans[0]

    kernel_name = plan.get(
        "kernel"
    )

    strategy = plan.get(
        "strategy",
        {}
    )

    static_kernel = find_static_kernel(
        static_data,
        kernel_name
    )

    if static_kernel is None:

        raise RuntimeError(
            f"Kernel '{kernel_name}' não encontrado "
            "no Static Analyzer JSON."
        )

    source_lines = (
        source_file
        .read_text()
        .splitlines(
            keepends=True
        )
    )

    transformations = apply_strategy(
        source_lines,
        static_kernel,
        strategy
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file.write_text(
        "".join(source_lines)
    )

    return {
        "kernel":
            kernel_name,

        "source":
            str(source_file),

        "output":
            str(output_file),

        "transformations":
            transformations,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "source",
        type=Path,
        help="Código C sequencial."
    )

    parser.add_argument(
        "static",
        type=Path,
        help=(
            "JSON produzido pelo "
            "Static Analyzer."
        )
    )

    parser.add_argument(
        "strategy",
        type=Path,
        help=(
            "JSON produzido pelo "
            "Strategy Planner."
        )
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Arquivo C de saída."
    )

    args = parser.parse_args()

    source_file = (
        args.source.resolve()
    )

    static_file = (
        args.static.resolve()
    )

    strategy_file = (
        args.strategy.resolve()
    )

    output_file = (
        args.output.resolve()
    )

    for path in [
        source_file,
        static_file,
        strategy_file,
    ]:

        if not path.exists():

            print(
                f"Arquivo não encontrado: "
                f"{path}"
            )

            sys.exit(1)

    print(
        "================================="
    )

    print(
        "TCC2 CODE TRANSFORMER v0.1"
    )

    print(
        "================================="
    )

    try:

        result = transform(
            source_file,
            static_file,
            strategy_file,
            output_file
        )

    except RuntimeError as error:

        print(
            f"TRANSFORMATION_ERROR: "
            f"{error}"
        )

        sys.exit(1)

    print(
        f"Kernel: {result['kernel']}"
    )

    print(
        f"Source: {result['source']}"
    )

    print(
        f"Output: {result['output']}"
    )

    print()

    print(
        "Transformations:"
    )

    for transformation in (
        result["transformations"]
    ):

        print(
            f"  Loop #"
            f"{transformation['loop_id']}"
        )

        print(
            f"    Original line: "
            f"{transformation['start_line']}"
        )

        print(
            f"    Pragma: "
            f"{transformation['pragma']}"
        )

    print()

    print(
        "================================="
    )

    print(
        "TRANSFORMATION_SUCCESS"
    )

    print(
        "================================="
    )


if __name__ == "__main__":
    main()
