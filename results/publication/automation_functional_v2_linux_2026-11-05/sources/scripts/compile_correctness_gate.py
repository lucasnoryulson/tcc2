import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.artifact_provenance import (
    ABS_TOL, COMPILE_FLAGS, OPENMP_ENVIRONMENT, REL_TOL,
    capture_run, file_record, verify_file, verify_provenance,
)

# ============================================================
# CONFIGURATION
# ============================================================

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
        timeout=120,
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

    command = [compiler, *COMPILE_FLAGS["candidate" if openmp else "sequential"]]

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
        environment.update(OPENMP_ENVIRONMENT, OMP_NUM_THREADS=str(threads))

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

    value = float(first_line)
    if not math.isfinite(value):
        raise ValueError("Program produced non-finite output.")
    return value


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

def run_gate(sequential_source, candidate_source, driver, build_dir, compiler, threads):
    counts = [threads] if type(threads) is int else threads
    if not isinstance(counts, list) or not counts or any(
        type(count) is not int or count < 1 for count in counts
    ) or len(set(counts)) != len(counts):
        raise ValueError("Threads must be distinct positive integers.")

    provenance = capture_run(
        {"sequential": sequential_source, "candidate": candidate_source, "driver": driver},
        build_dir, compiler,
    )
    run_dir = Path(provenance["run_dir"])
    snapshots = {name: Path(item["snapshot"]) for name, item in provenance["inputs"].items()}
    report = {
        "schema": "tcc2-correctness-gate", "version": "0.2", "status": "FAIL",
        "inputs": {name: item["path"] for name, item in provenance["inputs"].items()},
        "compiler": compiler, "threads": threads, "validated_threads": [],
        "tolerances": {"relative": REL_TOL, "absolute": ABS_TOL},
        "provenance": provenance, "compilation": {}, "binaries": {},
        "execution": {}, "thread_results": [],
    }
    for name in ("sequential", "candidate"):
        binary = run_dir / ("dot_gate_" + name)
        compiled = compile_program(
            provenance["toolchain"]["path"], snapshots["driver"], snapshots[name],
            binary, openmp=name == "candidate",
        )
        report["compilation"][name] = compiled
        print_compilation(name, compiled)
        if compiled["returncode"] != 0:
            report["reason"] = f"{name} compile error."
            print("GATE RESULT: FAIL")
            return report
        report["binaries"][name] = file_record(binary)

    sequential_run = execute_program(Path(report["binaries"]["sequential"]["path"]))
    report["execution"]["sequential"] = sequential_run
    if sequential_run["returncode"] != 0:
        report["reason"] = "Sequential runtime error."
        print(sequential_run["stderr"])
        print("GATE RESULT: FAIL")
        return report
    try:
        reference = parse_numeric_output(sequential_run["stdout"])
    except ValueError as error:
        report["reason"] = str(error)
        print(f"OUTPUT_ERROR: {error}")
        print("GATE RESULT: FAIL")
        return report

    for count in counts:
        candidate_run = execute_program(Path(report["binaries"]["candidate"]["path"]), count)
        report["execution"]["candidate"] = candidate_run
        run = {"threads": count, "execution": candidate_run}
        report["thread_results"].append(run)
        if candidate_run["returncode"] != 0:
            report["reason"] = f"Candidate runtime error with {count} threads."
            print(candidate_run["stderr"])
            print("GATE RESULT: FAIL")
            return report
        try:
            candidate = parse_numeric_output(candidate_run["stdout"])
        except ValueError as error:
            report["reason"] = str(error)
            print(f"OUTPUT_ERROR: {error}")
            print("GATE RESULT: FAIL")
            return report
        validation = validate_numeric(reference, candidate)
        run["validation"] = validation
        report["validation"] = validation
        print(f"Threads: {count}; sequential: {reference:.17g}; candidate: {candidate:.17g}")
        print(f"Absolute error: {validation['absolute_error']:.12e}; "
              f"relative error: {validation['relative_error']:.12e}")
        print(f"Tolerances: relative={REL_TOL}; absolute={ABS_TOL}")
        if not validation["correct"]:
            report["reason"] = f"Numeric validation failed with {count} threads."
            print("Correctness: INCORRECT")
            print("GATE RESULT: FAIL")
            return report
        report["validated_threads"].append(count)

    verify_provenance(provenance)
    for binary in report["binaries"].values():
        verify_file(binary)
    report["status"] = "PASS"
    print("Correctness: CORRECT")
    print("GATE RESULT: PASS")
    return report


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
        nargs="+",
        default=[4],
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Write the correctness result as JSON for the Context Builder.",
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

    report = {
        "schema": "tcc2-correctness-gate",
        "version": "0.2",
        "status": "FAIL",
        "reason": "Gate did not complete.",
    }
    if args.output is not None:
        args.output = args.output.resolve()
        if args.output in {
            sequential_source, candidate_source, driver,
            build_dir / "dot_gate_sequential", build_dir / "dot_gate_candidate",
        }:
            parser.error("The report must not overwrite a source or executable.")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")

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

    try:
        report = run_gate(
            sequential_source,
            candidate_source,
            driver,
            build_dir,
            args.compiler,
            args.threads,
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report["reason"] = str(error)
        print(f"GATE ERROR: {error}")

    if args.output is not None:
        args.output.write_text(json.dumps(report, indent=2) + "\n")

    sys.exit(
        0 if report["status"] == "PASS" else 1
    )


if __name__ == "__main__":
    main()
