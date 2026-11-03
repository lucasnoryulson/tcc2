import argparse
import csv
import os
import statistics
import subprocess
import sys
from pathlib import Path


DEFAULT_COMPILER = "clang"

THREAD_COUNTS = [
    1,
    2,
    4,
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
    )


def compile_program(
    compiler,
    driver,
    source,
    output,
    openmp
):
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

            return float(
                value
            )

    raise ValueError(
        "AVERAGE_SECONDS not found."
    )


def execute(
    executable,
    threads=None
):
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
        "--compiler",
        default=DEFAULT_COMPILER,
    )

    parser.add_argument(
        "--build-dir",
        type=Path,
        default=Path(
            "build/performance_gate"
        ),
    )

    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(
            "results/dot/auto_generated_performance.csv"
        ),
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

    csv_file = (
        args.csv.resolve()
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

    build_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    csv_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    sequential_binary = (
        build_dir
        / "dot_sequential"
    )

    candidate_binary = (
        build_dir
        / "dot_openmp"
    )

    print(
        "================================="
    )

    print(
        "TCC2 PERFORMANCE GATE v0.1"
    )

    print(
        "================================="
    )

    print()
    print(
        "Compiling sequential..."
    )

    result = compile_program(
        args.compiler,
        driver,
        sequential_source,
        sequential_binary,
        False,
    )

    if result.returncode != 0:

        print(
            "SEQUENTIAL COMPILE ERROR"
        )

        print(
            result.stderr
        )

        sys.exit(1)

    print(
        "Sequential: COMPILE_SUCCESS"
    )

    print()
    print(
        "Compiling OpenMP candidate..."
    )

    result = compile_program(
        args.compiler,
        driver,
        candidate_source,
        candidate_binary,
        True,
    )

    if result.returncode != 0:

        print(
            "CANDIDATE COMPILE ERROR"
        )

        print(
            result.stderr
        )

        sys.exit(1)

    print(
        "Candidate: COMPILE_SUCCESS"
    )

    print()
    print(
        "Sequential benchmark:"
    )

    sequential = benchmark(
        sequential_binary
    )

    sequential_median = (
        sequential[
            "median"
        ]
    )

    print()
    print(
        f"Sequential median: "
        f"{sequential_median:.9f} s"
    )

    rows = []

    rows.append({
        "mode":
            "sequential",

        "threads":
            1,

        "median_seconds":
            sequential_median,

        "mean_seconds":
            sequential["mean"],

        "speedup":
            1.0,

        "efficiency":
            1.0,
    })

    best_threads = None
    best_speedup = 0.0
    best_median = None

    for threads in THREAD_COUNTS:

        print()
        print(
            f"OpenMP benchmark "
            f"({threads} thread(s)):"
        )

        result = benchmark(
            candidate_binary,
            threads,
        )

        median = result[
            "median"
        ]

        speedup = (
            sequential_median
            / median
        )

        efficiency = (
            speedup
            / threads
        )

        print()
        print(
            f"  Median:     "
            f"{median:.9f} s"
        )

        print(
            f"  Speedup:    "
            f"{speedup:.3f}x"
        )

        print(
            f"  Efficiency: "
            f"{efficiency:.3f}"
        )

        rows.append({
            "mode":
                "openmp",

            "threads":
                threads,

            "median_seconds":
                median,

            "mean_seconds":
                result["mean"],

            "speedup":
                speedup,

            "efficiency":
                efficiency,
        })

        if speedup > best_speedup:

            best_speedup = (
                speedup
            )

            best_threads = (
                threads
            )

            best_median = (
                median
            )

    with csv_file.open(
        "w",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "mode",
                "threads",
                "median_seconds",
                "mean_seconds",
                "speedup",
                "efficiency",
            ],
        )

        writer.writeheader()

        writer.writerows(
            rows
        )

    print()
    print(
        "================================="
    )

    print(
        "PERFORMANCE SUMMARY"
    )

    print(
        "================================="
    )

    print(
        f"Sequential median: "
        f"{sequential_median:.9f} s"
    )

    print(
        f"Best OpenMP median: "
        f"{best_median:.9f} s"
    )

    print(
        f"Best threads: "
        f"{best_threads}"
    )

    print(
        f"Best speedup: "
        f"{best_speedup:.3f}x"
    )

    print()

    if best_speedup > 1.0:

        print(
            "PERFORMANCE GATE: PASS"
        )

        print(
            "Generated candidate improves "
            "performance."
        )

    else:

        print(
            "PERFORMANCE GATE: FAIL"
        )

        print(
            "Generated candidate does not "
            "improve performance."
        )

    print()

    print(
        f"CSV salvo em: "
        f"{csv_file}"
    )

    print(
        "================================="
    )


if __name__ == "__main__":
    main()
