from pathlib import Path
import subprocess
import statistics
import math
import csv
import os
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SEQ_SOURCE = (
    PROJECT_ROOT
    / "kernels"
    / "wavefront"
    / "sequential.cpp"
)

TILED_SOURCE = (
    PROJECT_ROOT
    / "kernels"
    / "wavefront"
    / "tiled_openmp.cpp"
)

BUILD_DIR = (
    PROJECT_ROOT
    / "build"
    / "wavefront"
)

RESULTS_DIR = (
    PROJECT_ROOT
    / "results"
    / "wavefront"
)

SEQ_BINARY = (
    BUILD_DIR
    / "wavefront_sequential_autotune"
)

TILED_BINARY = (
    BUILD_DIR
    / "wavefront_tiled_autotune"
)

CSV_FILE = (
    RESULTS_DIR
    / "tiled_autotuning.csv"
)


N = 4000

BLOCK_SIZES = [
    16,
    32,
    64,
    128,
    256,
]

THREAD_COUNTS = [
    1,
    2,
    4,
]

REPETITIONS = 5

REL_TOL = 1e-12
ABS_TOL = 1e-12


def compile_programs():

    BUILD_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        "[1/4] Compilando sequencial..."
    )

    seq_command = [
        "clang++",
        "-O3",
        "-std=c++14",
        str(SEQ_SOURCE),
        "-o",
        str(SEQ_BINARY),
    ]

    result = subprocess.run(
        seq_command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print(result.stderr)

        raise RuntimeError(
            "Erro compilando sequencial."
        )

    print("Sequential compilation: OK")

    print(
        "\nCompilando tiled OpenMP..."
    )

    tiled_command = [
        "clang++",
        "-O3",
        "-std=c++14",
        "-fopenmp",
        str(TILED_SOURCE),
        "-o",
        str(TILED_BINARY),
    ]

    result = subprocess.run(
        tiled_command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print(result.stderr)

        raise RuntimeError(
            "Erro compilando tiled."
        )

    print("Tiled compilation: OK")


def parse_output(text):

    values = {}

    for line in text.splitlines():

        if "=" not in line:
            continue

        key, value = line.split(
            "=",
            1
        )

        values[
            key.strip()
        ] = value.strip()

    return values


def calculate_stats(values):

    return {
        "mean":
            statistics.mean(values),

        "median":
            statistics.median(values),

        "std_dev":
            statistics.pstdev(values),

        "min":
            min(values),

        "max":
            max(values),
    }


def run_sequential():

    print(
        "\n[2/4] Medindo baseline sequencial...\n"
    )

    times = []
    reference = None

    for run in range(
        1,
        REPETITIONS + 1
    ):

        result = subprocess.run(
            [
                str(SEQ_BINARY),
                str(N),
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            print(result.stderr)

            raise RuntimeError(
                "Erro executando sequencial."
            )

        values = parse_output(
            result.stdout
        )

        value = float(
            values["result"]
        )

        run_ms = float(
            values["run_ms"]
        )

        if reference is None:
            reference = value

        else:

            if not math.isclose(
                value,
                reference,
                rel_tol=REL_TOL,
                abs_tol=ABS_TOL
            ):

                raise RuntimeError(
                    "Baseline sequencial "
                    "não reprodutível."
                )

        times.append(
            run_ms
        )

        print(
            f"SEQ "
            f"Run={run} "
            f"Time={run_ms:.6f} ms "
            f"Result={value:.15f}"
        )

    stats = calculate_stats(
        times
    )

    print()

    print(
        f"Sequential median: "
        f"{stats['median']:.6f} ms"
    )

    print(
        f"Reference result: "
        f"{reference:.17g}"
    )

    return stats, reference


def make_openmp_env(threads):

    env = os.environ.copy()

    env[
        "OMP_NUM_THREADS"
    ] = str(threads)

    env[
        "OMP_DYNAMIC"
    ] = "FALSE"

    env[
        "OMP_PROC_BIND"
    ] = "TRUE"

    env[
        "OMP_PLACES"
    ] = "cores"

    return env


def run_configuration(
    block_size,
    threads,
    reference
):

    env = make_openmp_env(
        threads
    )

    times = []

    max_absolute_error = 0.0

    for run in range(
        1,
        REPETITIONS + 1
    ):

        result = subprocess.run(
            [
                str(TILED_BINARY),
                str(N),
                str(block_size),
            ],
            capture_output=True,
            text=True,
            env=env
        )

        if result.returncode != 0:

            print(result.stderr)

            raise RuntimeError(
                "Erro executando tiled."
            )

        values = parse_output(
            result.stdout
        )

        candidate = float(
            values["result"]
        )

        run_ms = float(
            values["run_ms"]
        )

        absolute_error = abs(
            candidate - reference
        )

        max_absolute_error = max(
            max_absolute_error,
            absolute_error
        )

        correct = math.isclose(
            candidate,
            reference,
            rel_tol=REL_TOL,
            abs_tol=ABS_TOL
        )

        if not correct:

            print(result.stdout)

            raise RuntimeError(
                f"Resultado incorreto: "
                f"block={block_size}, "
                f"threads={threads}"
            )

        times.append(
            run_ms
        )

        print(
            f"Block={block_size:<3} "
            f"Threads={threads} "
            f"Run={run} "
            f"Time={run_ms:.6f} ms"
        )

    stats = calculate_stats(
        times
    )

    stats[
        "max_absolute_error"
    ] = max_absolute_error

    return stats


def main():

    print(
        "====================================="
    )

    print(
        "TCC2 — WAVEFRONT TILED AUTOTUNING"
    )

    print(
        "====================================="
    )

    print(
        f"N={N}"
    )

    print(
        f"Blocks={BLOCK_SIZES}"
    )

    print(
        f"Threads={THREAD_COUNTS}"
    )

    print(
        f"Repetitions={REPETITIONS}"
    )

    compile_programs()

    sequential, reference = (
        run_sequential()
    )

    print(
        "\n[3/4] Executando espaço "
        "de configurações...\n"
    )

    results = []

    total_configs = (
        len(BLOCK_SIZES)
        *
        len(THREAD_COUNTS)
    )

    config_number = 0

    for block_size in BLOCK_SIZES:

        for threads in THREAD_COUNTS:

            config_number += 1

            print()
            print(
                "-------------------------------------"
            )

            print(
                f"Config "
                f"{config_number}/"
                f"{total_configs}"
            )

            print(
                f"BLOCK_SIZE={block_size} "
                f"THREADS={threads}"
            )

            print(
                "-------------------------------------"
            )

            stats = run_configuration(
                block_size,
                threads,
                reference
            )

            speedup = (
                sequential["median"]
                /
                stats["median"]
            )

            efficiency = (
                speedup
                /
                threads
            )

            results.append({
                "block_size":
                    block_size,

                "threads":
                    threads,

                "mean":
                    stats["mean"],

                "median":
                    stats["median"],

                "std_dev":
                    stats["std_dev"],

                "min":
                    stats["min"],

                "max":
                    stats["max"],

                "speedup":
                    speedup,

                "efficiency":
                    efficiency,

                "max_absolute_error":
                    stats[
                        "max_absolute_error"
                    ],
            })

            print(
                f"\nMedian="
                f"{stats['median']:.6f} ms"
            )

            print(
                f"Speedup vs sequential="
                f"{speedup:.3f}x"
            )

            print(
                f"Efficiency="
                f"{efficiency:.3f}"
            )

    print(
        "\n[4/4] Salvando resultados..."
    )

    timestamp = (
        datetime.now().isoformat()
    )

    with CSV_FILE.open(
        "w",
        newline=""
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow([
            "timestamp",
            "n",
            "sequential_median_ms",
            "block_size",
            "threads",
            "mean_ms",
            "median_ms",
            "std_dev_ms",
            "min_ms",
            "max_ms",
            "speedup_vs_sequential",
            "efficiency",
            "max_absolute_error",
        ])

        for result in results:

            writer.writerow([
                timestamp,
                N,
                sequential[
                    "median"
                ],
                result[
                    "block_size"
                ],
                result[
                    "threads"
                ],
                result[
                    "mean"
                ],
                result[
                    "median"
                ],
                result[
                    "std_dev"
                ],
                result[
                    "min"
                ],
                result[
                    "max"
                ],
                result[
                    "speedup"
                ],
                result[
                    "efficiency"
                ],
                result[
                    "max_absolute_error"
                ],
            ])

    ranked = sorted(
        results,
        key=lambda x: x[
            "median"
        ]
    )

    print(
        "\n====================================="
    )

    print(
        "RANKING"
    )

    print(
        "====================================="
    )

    for position, result in enumerate(
        ranked,
        start=1
    ):

        print(
            f"{position:2}. "
            f"block="
            f"{result['block_size']:<3} "
            f"threads="
            f"{result['threads']} "
            f"median="
            f"{result['median']:.6f} ms "
            f"speedup="
            f"{result['speedup']:.3f}x"
        )

    best = ranked[0]

    print(
        "\n====================================="
    )

    print(
        "BEST CONFIGURATION"
    )

    print(
        "====================================="
    )

    print(
        f"BLOCK_SIZE: "
        f"{best['block_size']}"
    )

    print(
        f"THREADS: "
        f"{best['threads']}"
    )

    print(
        f"MEDIAN: "
        f"{best['median']:.6f} ms"
    )

    print(
        f"SPEEDUP: "
        f"{best['speedup']:.3f}x"
    )

    print(
        f"EFFICIENCY: "
        f"{best['efficiency']:.3f}"
    )

    print(
        f"\nCSV: "
        f"{CSV_FILE}"
    )


if __name__ == "__main__":
    main()
