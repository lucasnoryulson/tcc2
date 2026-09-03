import argparse
import math
import os
import subprocess
import sys
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

REL_TOL = 1e-9
ABS_TOL = 1e-12

DEFAULT_COMPILER = "clang"


# ============================================================
# COMMAND EXECUTION
# ============================================================

def run_command(
    command,
    environment=None
):
    """
    Execute a command and return CompletedProcess.
    """

    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )


# ============================================================
# COMPILATION
# ============================================================

def compile_program(
    compiler,
    driver,
    source,
    output,
    openmp
):
    """
    Compile one version of the program.
    """

    command = [
        compiler,
        "-O3",
    ]

    if openmp:

        command.append(
            "-fopenmp"
        )

    command.extend([
        str(driver),
        str(source),
        "-lm",
        "-o",
        str(output),
    ])

    result = run_command(
        command
    )

    return {
        "command":
            command,

        "returncode":
            result.returncode,

        "stdout":
            result.stdout,

        "stderr":
            result.stderr,
    }


# ============================================================
# EXECUTION
# ============================================================

def execute_program(
    executable,
    threads=None
):
    """
    Execute compiled program.

    OpenMP execution receives a controlled environment.
    """

    environment = os.environ.copy()

    if threads is not None:

        environment[
            "OMP_NUM_THREADS"
        ] = str(threads)

        environment[
            "OMP_DYNAMIC"
        ] = "FALSE"

        environment[
            "OMP_PROC_BIND"
        ] = "TRUE"

        environment[
            "OMP_PLACES"
        ] = "cores"

    result = run_command(
        [str(executable)],
        environment
    )

    return {
        "returncode":
            result.returncode,

        "stdout":
            result.stdout.strip(),

        "stderr":
            result.stderr.strip(),
    }


# ============================================================
# NUMERIC VALIDATION
# ============================================================

def parse_numeric_output(text):
    """
    The current fixture prints one floating-point value.
    """

    text = text.strip()

    if not text:

        raise ValueError(
            "Program produced empty output."
        )

    first_line = (
        text.splitlines()[0]
    )

    return float(
        first_line
    )


def validate_numeric(
    reference,
    candidate
):
    absolute_error = abs(
        candidate - reference
    )

    if reference != 0:

        relative_error = (
            absolute_error
            / abs(reference)
        )

    else:

        relative_error = (
            absolute_error
        )

    correct = math.isclose(
        candidate,
        reference,
        rel_tol=REL_TOL,
        abs_tol=ABS_TOL,
    )

    return {
        "reference":
            reference,

        "candidate":
            candidate,

        "absolute_error":
            absolute_error,

        "relative_error":
            relative_error,

        "correct":
            correct,
    }


# ============================================================
# PRINT HELPERS
# ============================================================

def print_compilation(
    name,
    result
):
    print()

    print(
        f"{name} compilation:"
    )

    print(
        "  Command:"
    )

    print(
        "  "
        + " ".join(
            result["command"]
        )
    )

    if result["returncode"] == 0:

        print(
            "  Status: COMPILE_SUCCESS"
        )

    else:

        print(
            "  Status: COMPILE_ERROR"
        )

        if result["stderr"]:

            print()
            print(
                result["stderr"]
            )


# ============================================================
# GATE
# ============================================================

def run_gate(
    sequential_source,
    candidate_source,
    driver,
    build_dir,
    compiler,
    threads
):
    build_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    sequential_binary = (
        build_dir
        / "dot_gate_sequential"
    )

    candidate_binary = (
        build_dir
        / "dot_gate_candidate"
    )

    # --------------------------------------------------------
    # Compile sequential
    # --------------------------------------------------------

    sequential_compile = (
        compile_program(
            compiler,
            driver,
            sequential_source,
            sequential_binary,
            openmp=False,
        )
    )

    print_compilation(
        "Sequential",
        sequential_compile
    )

    if (
        sequential_compile[
            "returncode"
        ]
        != 0
    ):

        print()
        print(
            "================================="
        )
        print(
            "GATE RESULT: FAIL"
        )
        print(
            "Reason: sequential compile error"
        )
        print(
            "================================="
        )

        return 1

    # --------------------------------------------------------
    # Compile candidate
    # --------------------------------------------------------

    candidate_compile = (
        compile_program(
            compiler,
            driver,
            candidate_source,
            candidate_binary,
            openmp=True,
        )
    )

    print_compilation(
        "OpenMP candidate",
        candidate_compile
    )

    if (
        candidate_compile[
            "returncode"
        ]
        != 0
    ):

        print()
        print(
            "================================="
        )
        print(
            "GATE RESULT: FAIL"
        )
        print(
            "Reason: candidate compile error"
        )
        print(
            "================================="
        )

        return 1

    # --------------------------------------------------------
    # Execute sequential
    # --------------------------------------------------------

    sequential_run = (
        execute_program(
            sequential_binary
        )
    )

    if (
        sequential_run[
            "returncode"
        ]
        != 0
    ):

        print()
        print(
            "Sequential execution:"
        )

        print(
            "  Status: RUNTIME_ERROR"
        )

        print(
            sequential_run[
                "stderr"
            ]
        )

        print()
        print(
            "================================="
        )
        print(
            "GATE RESULT: FAIL"
        )
        print(
            "================================="
        )

        return 1

    # --------------------------------------------------------
    # Execute candidate
    # --------------------------------------------------------

    candidate_run = (
        execute_program(
            candidate_binary,
            threads=threads,
        )
    )

    if (
        candidate_run[
            "returncode"
        ]
        != 0
    ):

        print()
        print(
            "OpenMP execution:"
        )

        print(
            "  Status: RUNTIME_ERROR"
        )

        print(
            candidate_run[
                "stderr"
            ]
        )

        print()
        print(
            "================================="
        )
        print(
            "GATE RESULT: FAIL"
        )
        print(
            "================================="
        )

        return 1

    # --------------------------------------------------------
    # Parse output
    # --------------------------------------------------------

    try:

        reference = (
            parse_numeric_output(
                sequential_run[
                    "stdout"
                ]
            )
        )

        candidate = (
            parse_numeric_output(
                candidate_run[
                    "stdout"
                ]
            )
        )

    except ValueError as error:

        print()

        print(
            f"OUTPUT_ERROR: {error}"
        )

        print()

        print(
            "================================="
        )
        print(
            "GATE RESULT: FAIL"
        )
        print(
            "================================="
        )

        return 1

    # --------------------------------------------------------
    # Correctness validation
    # --------------------------------------------------------

    validation = (
        validate_numeric(
            reference,
            candidate
        )
    )

    print()

    print(
        "Execution:"
    )

    print(
        f"  Sequential result: "
        f"{reference:.17g}"
    )

    print(
        f"  OpenMP result:     "
        f"{candidate:.17g}"
    )

    print(
        f"  Threads:           "
        f"{threads}"
    )

    print()

    print(
        "Numeric validation:"
    )

    print(
        f"  Absolute error: "
        f"{validation['absolute_error']:.12e}"
    )

    print(
        f"  Relative error: "
        f"{validation['relative_error']:.12e}"
    )

    print(
        f"  Relative tolerance: "
        f"{REL_TOL:.12e}"
    )

    print(
        f"  Absolute tolerance: "
        f"{ABS_TOL:.12e}"
    )

    print()

    if validation["correct"]:

        print(
            "Correctness: CORRECT"
        )

        print()

        print(
            "================================="
        )

        print(
            "GATE RESULT: PASS"
        )

        print(
            "Candidate is allowed to proceed "
            "to performance evaluation."
        )

        print(
            "================================="
        )

        return 0

    print(
        "Correctness: INCORRECT"
    )

    print()

    print(
        "================================="
    )

    print(
        "GATE RESULT: FAIL"
    )

    print(
        "Candidate must NOT proceed "
        "to performance evaluation."
    )

    print(
        "================================="
    )

    return 1


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--sequential",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--candidate",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--driver",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--build-dir",
        type=Path,
        default=Path(
            "build/gates"
        ),
    )

    parser.add_argument(
        "--compiler",
        default=DEFAULT_COMPILER,
    )

    parser.add_argument(
        "--threads",
        type=int,
        default=4,
    )

    args = parser.parse_args()

    sequential_source = (
        args.sequential.resolve()
    )

    candidate_source = (
        args.candidate.resolve()
    )

    driver = (
        args.driver.resolve()
    )

    build_dir = (
        args.build_dir.resolve()
    )

    for path in [
        sequential_source,
        candidate_source,
        driver,
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
        "TCC2 COMPILE + CORRECTNESS GATE"
    )

    print(
        "================================="
    )

    print(
        f"Sequential: "
        f"{sequential_source}"
    )

    print(
        f"Candidate:  "
        f"{candidate_source}"
    )

    print(
        f"Driver:     "
        f"{driver}"
    )

    print(
        f"Compiler:   "
        f"{args.compiler}"
    )

    print(
        f"Threads:    "
        f"{args.threads}"
    )

    result = run_gate(
        sequential_source,
        candidate_source,
        driver,
        build_dir,
        args.compiler,
        args.threads,
    )

    sys.exit(
        result
    )


if __name__ == "__main__":
    main()
