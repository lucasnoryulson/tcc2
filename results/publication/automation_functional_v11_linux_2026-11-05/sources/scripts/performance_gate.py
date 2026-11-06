import argparse
import csv
import json
import math
import os
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.artifact_provenance import (
    COMPILE_FLAGS, OPENMP_ENVIRONMENT, capture_run, file_record,
    load_correctness_report, measured_rows, verify_file, verify_provenance,
)

DEFAULT_COMPILER = "clang"

THREAD_COUNTS = [
    int(value)
    for value in os.environ.get(
        "TCC2_THREAD_COUNTS",
        "1,2,4"
    ).split(",")
]

EXTERNAL_REPEATS = 5


def run_command(
    command,
    environment=None
):
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
        timeout=120,
    )


def compile_program(
    compiler,
    driver,
    source,
    output,
    openmp
):
    command = [compiler, *COMPILE_FLAGS["candidate" if openmp else "sequential"]]

    command.extend([
        str(driver),
        str(source),
        "-lm",
        "-o",
        str(output),
    ])

    return run_command(
        command
    )


def parse_average_time(output):
    for line in output.splitlines():

        if line.startswith(
            "AVERAGE_SECONDS="
        ):

            value = line.split(
                "=",
                1
            )[1]

            seconds = float(value)
            if not math.isfinite(seconds) or seconds <= 0:
                raise ValueError("AVERAGE_SECONDS must be finite and positive.")
            return seconds

    raise ValueError(
        "AVERAGE_SECONDS not found."
    )


def execute(
    executable,
    threads=None
):
    environment = os.environ.copy()

    if threads is not None:
        environment.update(OPENMP_ENVIRONMENT, OMP_NUM_THREADS=str(threads))

    result = run_command(
        [
            str(executable)
        ],
        environment,
    )

    if result.returncode != 0:

        raise RuntimeError(
            result.stderr
        )

    return parse_average_time(
        result.stdout
    )


def benchmark(
    executable,
    threads=None
):
    times = []

    for repetition in range(
        1,
        EXTERNAL_REPEATS + 1
    ):

        value = execute(
            executable,
            threads
        )

        times.append(
            value
        )

        print(
            f"    Run {repetition}: "
            f"{value:.9f} s"
        )

    median = statistics.median(
        times
    )

    mean = statistics.mean(
        times
    )

    return {
        "times":
            times,

        "median":
            median,

        "mean":
            mean,

        "min":
            min(times),

        "max":
            max(times),
    }


def run_gate(sequential_source, candidate_source, driver, build_dir, compiler,
             counts, correctness_file, csv_file):
    if not counts or any(type(count) is not int or count < 1 for count in counts) or len(set(counts)) != len(counts):
        raise ValueError("Thread counts must be distinct positive integers.")
    correctness, correctness_ref = load_correctness_report(
        correctness_file, sequential_source, candidate_source,
    )
    if correctness["status"] != "PASS":
        raise ValueError("Performance requires correctness PASS.")
    if not set(counts).issubset(correctness["validated_threads"]):
        raise ValueError("Validate correctness for every benchmark thread count first.")
    provenance = capture_run(
        {"sequential": sequential_source, "candidate": candidate_source, "driver": driver},
        build_dir, compiler, correctness["provenance"]["campaign_id"],
    )
    if provenance["toolchain"] != correctness["provenance"]["toolchain"]:
        raise ValueError("Correctness and performance must use the same toolchain.")
    run_dir = Path(provenance["run_dir"])
    frozen_correctness = run_dir / "correctness.json"
    frozen_correctness.write_bytes(verify_file(correctness_ref))
    report = {
        "schema": "tcc2-performance-gate", "version": "0.1", "status": "FAIL",
        "provenance": provenance, "correctness_report": file_record(frozen_correctness),
        "thread_counts": counts, "repetitions": EXTERNAL_REPEATS,
        "configuration_dimensions": ["threads"],
        "compilation": {}, "binaries": {}, "measurements": [],
    }
    snapshots = {name: Path(item["snapshot"]) for name, item in provenance["inputs"].items()}
    for name in ("sequential", "candidate"):
        binary = run_dir / ("dot_" + name)
        result = compile_program(
            provenance["toolchain"]["path"], snapshots["driver"], snapshots[name],
            binary, name == "candidate",
        )
        report["compilation"][name] = {
            "command": result.args, "returncode": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr,
        }
        if result.returncode != 0:
            report["reason"] = f"{name} compile error."
            print(result.stderr)
            return report
        report["binaries"][name] = file_record(binary)

    print("Sequential benchmark:")
    result = benchmark(Path(report["binaries"]["sequential"]["path"]))
    report["measurements"].append({"mode": "sequential", "threads": 1, "times": result["times"]})
    for count in counts:
        print(f"OpenMP benchmark ({count} thread(s)):")
        result = benchmark(Path(report["binaries"]["candidate"]["path"]), count)
        report["measurements"].append({"mode": "openmp", "threads": count, "times": result["times"]})

    verify_provenance(provenance)
    verify_provenance(correctness["provenance"])
    for binary in report["binaries"].values():
        verify_file(binary)
    rows = measured_rows(report["measurements"])
    frozen_csv = run_dir / "performance.csv"
    with frozen_csv.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report["csv"] = file_record(frozen_csv)
    report["csv_file"] = str(csv_file.resolve())
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    csv_file.write_bytes(frozen_csv.read_bytes())
    report["status"] = "PASS" if any(row["speedup"] > 1 for row in rows[1:]) else "FAIL"
    print(f"PERFORMANCE GATE: {report['status']}")
    print(f"CSV salvo em: {csv_file}")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sequential", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--driver", required=True, type=Path)
    parser.add_argument("--correctness", required=True, type=Path,
                        help="Passing correctness report covering all benchmark threads.")
    parser.add_argument("--compiler", default=DEFAULT_COMPILER)
    parser.add_argument("--build-dir", type=Path, default=Path("build/performance_gate"))
    parser.add_argument("--csv", type=Path, default=Path("results/dot/auto_generated_performance.csv"))
    parser.add_argument("--output", type=Path,
                        help="JSON evidence; defaults to the CSV name with .report.json suffix.")
    args = parser.parse_args()
    args.csv = args.csv.resolve()
    output = args.output.resolve() if args.output else args.csv.with_suffix(".report.json")
    inputs = {args.sequential.resolve(), args.candidate.resolve(), args.driver.resolve(), args.correctness.resolve()}
    if args.csv in inputs or output in inputs or output == args.csv:
        parser.error("Evidence outputs must not overwrite inputs or each other.")
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"schema": "tcc2-performance-gate", "version": "0.1",
              "status": "FAIL", "reason": "Gate did not complete."}
    output.write_text(json.dumps(report, indent=2) + "\n")
    try:
        report = run_gate(
            args.sequential.resolve(), args.candidate.resolve(), args.driver.resolve(),
            args.build_dir.resolve(), args.compiler, THREAD_COUNTS,
            args.correctness.resolve(), args.csv,
        )
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report["reason"] = str(error)
        print(f"PERFORMANCE ERROR: {error}")
    output.write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
