from pathlib import Path
import subprocess
import statistics
import csv
import os
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[1]

POLYBENCH_ROOT = (
    PROJECT_ROOT
    / "benchmarks"
    / "PolyBenchC-4.2.1"
)

UTILITIES_DIR = POLYBENCH_ROOT / "utilities"

COVARIANCE_DIR = (
    POLYBENCH_ROOT
    / "datamining"
    / "covariance"
)

SOURCE = (
    PROJECT_ROOT
    / "kernels"
    / "covariance"
    / "manual_openmp.c"
)

BUILD_DIR = PROJECT_ROOT / "build" / "covariance"
RESULTS_DIR = PROJECT_ROOT / "results" / "covariance"

BUILD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

BINARY = BUILD_DIR / "covariance_openmp_time"

CSV_FILE = (
    RESULTS_DIR
    / "openmp_scaling.csv"
)

THREAD_COUNTS = [1, 2, 4]
REPETITIONS = 5

# Baseline sequencial obtido anteriormente
SEQUENTIAL_BASELINE = 12.17804366


def compile_program():

    print("[1/3] Compilando Covariance OpenMP...")

    command = [
        "clang",
        "-O3",
        "-fopenmp",
        "-DLARGE_DATASET",
        "-DPOLYBENCH_TIME",

        f"-I{UTILITIES_DIR}",
        f"-I{COVARIANCE_DIR}",

        str(SOURCE),
        str(UTILITIES_DIR / "polybench.c"),

        "-o",
        str(BINARY),

        "-lm",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("Erro de compilação.")

    print("OK")


def run_with_threads(thread_count):

    times = []

    env = os.environ.copy()

    env["OMP_NUM_THREADS"] = str(thread_count)
    env["OMP_DYNAMIC"] = "FALSE"
    env["OMP_PROC_BIND"] = "TRUE"
    env["OMP_PLACES"] = "cores"

    for run in range(1, REPETITIONS + 1):

        result = subprocess.run(
            [str(BINARY)],
            capture_output=True,
            text=True,
            env=env
        )

        if result.returncode != 0:
            raise RuntimeError("Erro durante execução.")

        time_value = float(result.stdout.strip())

        times.append(time_value)

        print(
            f"Threads={thread_count} "
            f"Run={run} "
            f"Time={time_value:.6f}s"
        )

    return times


def main():

    compile_program()

    print("\n[2/3] Executando benchmarks...\n")

    all_results = []

    for threads in THREAD_COUNTS:

        print(f"--- {threads} THREAD(S) ---")

        times = run_with_threads(threads)

        median = statistics.median(times)
        mean = statistics.mean(times)
        std_dev = statistics.pstdev(times)

        all_results.append({
            "threads": threads,
            "mean": mean,
            "median": median,
            "std_dev": std_dev,
            "min": min(times),
            "max": max(times),
        })

        print(
            f"Median={median:.6f}s "
            f"Mean={mean:.6f}s\n"
        )

    openmp_one_thread = all_results[0]["median"]

    print("\n[3/3] RESULTADOS\n")

    new_file = not CSV_FILE.exists()

    with CSV_FILE.open("a", newline="") as file:

        writer = csv.writer(file)

        if new_file:

            writer.writerow([
                "timestamp",
                "threads",
                "mean_seconds",
                "median_seconds",
                "std_dev",
                "min_seconds",
                "max_seconds",
                "scaling_speedup",
                "speedup_vs_sequential",
                "efficiency_vs_sequential",
            ])

        for result in all_results:

            scaling_speedup = (
                openmp_one_thread
                / result["median"]
            )

            speedup_vs_sequential = (
                SEQUENTIAL_BASELINE
                / result["median"]
            )

            efficiency = (
                speedup_vs_sequential
                / result["threads"]
            )

            writer.writerow([
                datetime.now().isoformat(),
                result["threads"],
                result["mean"],
                result["median"],
                result["std_dev"],
                result["min"],
                result["max"],
                scaling_speedup,
                speedup_vs_sequential,
                efficiency,
            ])

            print(
                f"{result['threads']} thread(s): "
                f"{result['median']:.6f}s | "
                f"scaling={scaling_speedup:.3f}x | "
                f"vs_seq={speedup_vs_sequential:.3f}x | "
                f"efficiency={efficiency:.3f}"
            )

    print(f"\nCSV salvo em: {CSV_FILE}")


if __name__ == "__main__":
    main()
