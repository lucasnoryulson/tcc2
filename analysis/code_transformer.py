import argparse
import json
import re
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
# ADAPTIVE TARGET RESOLUTION
# ============================================================

REPO_ROOT = Path(
    __file__
).resolve().parents[1]


def resolve_source_path(
    source
):
    """
    Resolve absolute and repository-relative
    source paths to one canonical path.
    """

    source_path = Path(
        source
    )

    if not source_path.is_absolute():
        source_path = (
            REPO_ROOT
            / source_path
        )

    return source_path.resolve()


def verify_source_consistency(
    static_data,
    target_source
):
    """
    Prevent compiler feedback from being combined
    with static analysis generated for another
    source-code version.
    """

    static_source = static_data.get(
        "source"
    )

    if not static_source:
        raise RuntimeError(
            "Static Analyzer JSON does not contain "
            "a source field."
        )

    if not target_source:
        raise RuntimeError(
            "Adaptive plan does not contain "
            "target.source."
        )

    static_path = resolve_source_path(
        static_source
    )

    target_path = resolve_source_path(
        target_source
    )

    if static_path != target_path:
        raise RuntimeError(
            "STALE_ANALYSIS_ERROR: "
            "Static Analyzer source does not match "
            "the source referenced by compiler "
            "feedback. "
            f"Static='{static_path}', "
            f"Target='{target_path}'."
        )

    return {
        "static_source":
            str(static_path),
        "target_source":
            str(target_path),
        "match": True,
    }


def find_innermost_loop_for_line(
    static_kernel,
    source_line
):
    """
    Find all loops containing source_line and
    select the smallest source interval.

    The smallest interval corresponds to the
    structurally innermost loop when loop ranges
    are properly nested.
    """

    matches = []

    for loop in static_kernel.get(
        "loops",
        []
    ):

        start = loop.get(
            "start_line"
        )

        end = loop.get(
            "end_line"
        )

        if (
            start is None
            or end is None
        ):
            continue

        if (
            start
            <= source_line
            <= end
        ):
            matches.append(
                loop
            )

    if not matches:
        raise RuntimeError(
            "No loop in the Static Analyzer "
            f"contains source line {source_line}."
        )

    return min(
        matches,
        key=lambda loop: (
            loop["end_line"]
            - loop["start_line"]
        ),
    )


def resolve_adaptive_target(
    static_data,
    adaptive_plan
):
    """
    Resolve an Adaptive Strategy Planner target
    into a concrete Static Analyzer loop.
    """

    target = adaptive_plan.get(
        "target",
        {}
    )

    kernel_name = target.get(
        "function"
    )

    target_source = target.get(
        "source"
    )

    source_line = target.get(
        "line"
    )

    if not kernel_name:
        raise RuntimeError(
            "Adaptive plan target does not contain "
            "a function name."
        )

    if source_line is None:
        raise RuntimeError(
            "Adaptive plan target does not contain "
            "a source line."
        )

    source_check = (
        verify_source_consistency(
            static_data,
            target_source,
        )
    )

    static_kernel = find_static_kernel(
        static_data,
        kernel_name,
    )

    if static_kernel is None:
        raise RuntimeError(
            f"Kernel '{kernel_name}' was not found "
            "in Static Analyzer JSON."
        )

    loop = find_innermost_loop_for_line(
        static_kernel,
        source_line,
    )

    return {
        "kernel":
            kernel_name,

        "diagnostic_line":
            source_line,

        "loop_id":
            loop.get("id"),

        "iterator":
            loop.get("iterator"),

        "start_line":
            loop.get("start_line"),

        "end_line":
            loop.get("end_line"),

        "reads":
            loop.get("reads", []),

        "writes":
            loop.get("writes", []),

        "scalar_updates":
            loop.get(
                "scalar_updates",
                [],
            ),

        "source_check":
            source_check,
    }


# ============================================================
# ADAPTIVE SCALAR ACCUMULATOR
# ============================================================

def transform_adaptive_scalar_accumulator(
    source_lines,
    target_resolution,
):
    """
    Rewrite a conservative max-reduction-like
    memory update:

        target = max_score(target, expression);

    into a local scalar accumulator:

        DATA_TYPE tcc2_best = target;

        for (...) {
            DATA_TYPE tcc2_candidate = expression;
            tcc2_best = max_score(
                tcc2_best,
                tcc2_candidate
            );
        }

        target = tcc2_best;

    The transformation is deliberately
    conservative. It refuses unsupported shapes
    instead of guessing.
    """

    start_line = target_resolution.get(
        "start_line"
    )

    end_line = target_resolution.get(
        "end_line"
    )

    writes = target_resolution.get(
        "writes",
        [],
    )

    if (
        start_line is None
        or end_line is None
    ):
        raise RuntimeError(
            "Adaptive target does not contain "
            "valid loop source boundaries."
        )

    if len(writes) != 1:
        raise RuntimeError(
            "SCALAR_ACCUMULATOR requires exactly "
            "one loop write target."
        )

    target = writes[0].get(
        "expression"
    )

    if not target:
        raise RuntimeError(
            "Loop write target does not contain "
            "an expression."
        )

    start_index = start_line - 1
    end_index = end_line

    if (
        start_index < 0
        or end_index > len(source_lines)
        or start_index >= end_index
    ):
        raise RuntimeError(
            "Invalid loop source range for "
            "SCALAR_ACCUMULATOR."
        )

    loop_text = "".join(
        source_lines[
            start_index:end_index
        ]
    )

    if (
        "TCC2 AUTO-GENERATED: "
        "SCALAR_ACCUMULATOR"
        in loop_text
    ):
        raise RuntimeError(
            "SCALAR_ACCUMULATOR already appears "
            "to have been applied."
        )

    escaped_target = re.escape(
        target
    )

    pattern = re.compile(
        rf"(?P<indent>^[ \t]*)"
        rf"{escaped_target}"
        rf"\s*=\s*"
        rf"max_score\s*\(\s*"
        rf"{escaped_target}"
        rf"\s*,\s*"
        rf"(?P<expr>.*?)"
        rf"\s*\)\s*;",
        re.MULTILINE
        | re.DOTALL,
    )

    matches = list(
        pattern.finditer(
            loop_text
        )
    )

    if len(matches) != 1:
        raise RuntimeError(
            "SCALAR_ACCUMULATOR expected exactly "
            "one update matching "
            "'target = max_score(target, expr)'; "
            f"found {len(matches)}."
        )

    match = matches[0]

    assignment_indent = (
        match.group("indent")
    )

    expression = re.sub(
        r"\s+",
        " ",
        match.group("expr").strip(),
    )

    loop_first_line = source_lines[
        start_index
    ]

    loop_indent = leading_whitespace(
        loop_first_line
    )

    replacement = (
        f"{assignment_indent}"
        f"DATA_TYPE tcc2_candidate = "
        f"{expression};\n"
        f"\n"
        f"{assignment_indent}"
        f"tcc2_best = max_score(\n"
        f"{assignment_indent}"
        f"    tcc2_best,\n"
        f"{assignment_indent}"
        f"    tcc2_candidate\n"
        f"{assignment_indent}"
        f");"
    )

    transformed_loop = (
        loop_text[
            :match.start()
        ]
        + replacement
        + loop_text[
            match.end():
        ]
    )

    prefix = (
        f"{loop_indent}"
        "/* TCC2 AUTO-GENERATED: "
        "SCALAR_ACCUMULATOR */\n"
        f"{loop_indent}"
        f"DATA_TYPE tcc2_best = {target};\n"
        "\n"
    )

    suffix = (
        "\n"
        f"{loop_indent}"
        f"{target} = tcc2_best;\n"
    )

    generated = (
        prefix
        + transformed_loop
        + suffix
    )

    source_lines[
        start_index:end_index
    ] = [
        generated
    ]

    return {
        "action":
            "APPLY_SCALAR_ACCUMULATOR",

        "loop_id":
            target_resolution.get(
                "loop_id"
            ),

        "iterator":
            target_resolution.get(
                "iterator"
            ),

        "start_line":
            start_line,

        "end_line":
            end_line,

        "target":
            target,

        "accumulator":
            "tcc2_best",

        "candidate":
            "tcc2_candidate",
    }


# ============================================================
# ADAPTIVE EXPLICIT SIMD REDUCTION
# ============================================================

def transform_adaptive_explicit_simd_reduction(
    source_lines,
    target_resolution,
):
    """
    Insert an explicit OpenMP SIMD reduction
    before a loop when Static Analyzer evidence
    proves a supported scalar reduction.

    v0.1 intentionally supports only MAX.
    """

    start_line = target_resolution.get(
        "start_line"
    )

    scalar_updates = target_resolution.get(
        "scalar_updates",
        [],
    )

    if start_line is None:
        raise RuntimeError(
            "Adaptive SIMD target does not "
            "contain start_line."
        )

    reductions = [
        update
        for update in scalar_updates
        if (
            update.get("update_kind")
            == "reduction"
            and update.get(
                "self_reference"
            ) is True
        )
    ]

    if len(reductions) != 1:
        raise RuntimeError(
            "EXPLICIT_SIMD_REDUCTION requires "
            "exactly one structurally detected "
            "scalar reduction; "
            f"found {len(reductions)}."
        )

    reduction = reductions[0]

    variable = reduction.get(
        "variable"
    )

    operator = reduction.get(
        "reduction_operator"
    )

    if not variable:
        raise RuntimeError(
            "Detected scalar reduction does "
            "not contain a variable."
        )

    if operator != "max":
        raise RuntimeError(
            "Code Transformer adaptive SIMD "
            "v0.1 supports only max reduction; "
            f"received '{operator}'."
        )

    index = start_line - 1

    if (
        index < 0
        or index >= len(source_lines)
    ):
        raise RuntimeError(
            "Invalid source line for "
            "EXPLICIT_SIMD_REDUCTION."
        )

    target_line = source_lines[
        index
    ]

    if "for" not in target_line:
        raise RuntimeError(
            "Static Analyzer target line does "
            "not appear to contain a for loop."
        )

    previous_window = "".join(
        source_lines[
            max(0, index - 4):
            index
        ]
    )

    if (
        "#pragma omp simd"
        in previous_window
        or
        "TCC2 AUTO-GENERATED: "
        "EXPLICIT_SIMD_REDUCTION"
        in previous_window
    ):
        raise RuntimeError(
            "Explicit SIMD transformation "
            "already appears to be present."
        )

    indentation = leading_whitespace(
        target_line
    )

    marker_line = (
        indentation
        + "/* TCC2 AUTO-GENERATED: "
        + "EXPLICIT_SIMD_REDUCTION */\n"
    )

    pragma = (
        indentation
        + "#pragma omp simd "
        + f"reduction(max:{variable})\n"
    )

    source_lines[
        index:index
    ] = [
        marker_line,
        pragma,
    ]

    return {
        "action":
            "APPLY_EXPLICIT_SIMD_REDUCTION",

        "loop_id":
            target_resolution.get(
                "loop_id"
            ),

        "iterator":
            target_resolution.get(
                "iterator"
            ),

        "start_line":
            start_line,

        "variable":
            variable,

        "reduction_operator":
            operator,

        "pragma":
            pragma.strip(),

        "evidence":
            reduction.get(
                "evidence"
            ),
    }


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
