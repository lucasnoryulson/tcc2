from pathlib import Path
import subprocess
import statistics
import csv
import os
import sys
import hashlib
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[1]

POLYBENCH_ROOT = (
    PROJECT_ROOT
    / "benchmarks"
    / "PolyBenchC-4.2.1"
)

UTILITIES_DIR = POLYBENCH_ROOT / "utilities"

THREAD_COUNTS = [1, 2, 4]
REPETITIONS = 5


BENCHMARKS = {

    "gemm": {
        "original":
            POLYBENCH_ROOT
            / "linear-algebra"
            / "blas"
            / "gemm"
            / "gemm.c",

        "candidate":
            PROJECT_ROOT
            / "kernels"
            / "gemm"
            / "manual_openmp.c",

        "include_dir":
            POLYBENCH_ROOT
            / "linear-algebra"
            / "blas"
            / "gemm",

        "reference":
            PROJECT_ROOT
            / "results"
            / "gemm"
            / "reference_output.txt",
    },

    "jacobi-2d": {
        "original":
            POLYBENCH_ROOT
            / "stencils"
            / "jacobi-2d"
            / "jacobi-2d.c",

        "candidate":
            PROJECT_ROOT
            / "kernels"
            / "jacobi-2d"
            / "manual_openmp.c",

        "include_dir":
            POLYBENCH_ROOT
            / "stencils"
            / "jacobi-2d",

        "reference":
            PROJECT_ROOT
            / "results"
            / "jacobi-2d"
            / "reference_output.txt",
    },

    "covariance": {
        "original":
            POLYBENCH_ROOT
            / "datamining"
            / "covariance"
            / "covariance.c",

        "candidate":
            PROJECT_ROOT
            / "kernels"
            / "covariance"
            / "manual_openmp.c",

        "include_dir":
            POLYBENCH_ROOT
            / "datamining"
            / "covariance",

        "reference":
            PROJECT_ROOT
            / "results"
            / "covariance"
            / "reference_output.txt",
    },
}


def compile_program(
    source,
    include_dir,
    binary,
    openmp=False,
    dump=False
):

    command = [
        "clang",
        "-O3",
        "-DLARGE_DATASET",
    ]

    if openmp:
        command.append("-fopenmp")

    if dump:
        command.append(
            "-DPOLYBENCH_DUMP_ARRAYS"
        )
    else:
        command.append(
            "-DPOLYBENCH_TIME"
        )

    command += [
        f"-I{UTILITIES_DIR}",
        f"-I{include_dir}",

        str(source),
        str(UTILITIES_DIR / "polybench.c"),

        "-o",
        str(binary),

        "-lm",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print("\nCOMPILE_ERROR")
        print(result.stderr)

        return False

    return True


def run_timed(
    binary,
    threads=None
):

    times = []

    env = os.environ.copy()

    if threads is not None:

        env["OMP_NUM_THREADS"] = str(threads)
        env["OMP_DYNAMIC"] = "FALSE"
        env["OMP_PROC_BIND"] = "TRUE"
        env["OMP_PLACES"] = "cores"

    for run in range(
        1,
        REPETITIONS + 1
    ):

        result = subprocess.run(
            [str(binary)],
            capture_output=True,
            text=True,
            env=env
        )

        if result.returncode != 0:

            raise RuntimeError(
                "Erro durante execução."
            )

        value = float(
            result.stdout.strip()
        )

        times.append(value)

        if threads is None:
            label = "SEQ"
        else:
            label = f"{threads}T"

        print(
            f"{label} "
            f"Run={run} "
            f"Time={value:.6f}s"
        )

    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "std_dev": statistics.pstdev(times),
        "min": min(times),
        "max": max(times),
    }


def calculate_hash(data):
    return hashlib.sha256(
        data
    ).hexdigest()


def validate_candidate(
    benchmark,
    config,
    build_dir
):

    print(
        "\n[3/5] Validando corretude..."
    )

    binary = (
        build_dir
        / f"{benchmark}_candidate_dump"
    )

    success = compile_program(
        config["candidate"],
        config["include_dir"],
        binary,
        openmp=True,
        dump=True
    )

    if not success:
        return False

    result = subprocess.run(
        [str(binary)],
        capture_output=True
    )

    if result.returncode != 0:

        print("RUNTIME_ERROR")

        return False

    candidate_hash = calculate_hash(
        result.stderr
    )

    reference_hash = calculate_hash(
        config["reference"].read_bytes()
    )

    print(
        f"Reference: {reference_hash}"
    )

    print(
        f"Candidate: {candidate_hash}"
    )

    if candidate_hash == reference_hash:

        print("CORRECT")

        return True

    print("INCORRECT")

    return False


def main():

    if len(sys.argv) != 2:

        print(
            "Uso: "
            "python3 scripts/benchmark.py "
            "<benchmark>"
        )

        print(
            "\nBenchmarks disponíveis:"
        )

        for name in BENCHMARKS:
            print(f"  - {name}")

        sys.exit(1)

    benchmark = sys.argv[1]

    if benchmark not in BENCHMARKS:

        print(
            f"Benchmark desconhecido: "
            f"{benchmark}"
        )

        sys.exit(1)

    config = BENCHMARKS[benchmark]

    build_dir = (
        PROJECT_ROOT
        / "build"
        / benchmark
    )

    results_dir = (
        PROJECT_ROOT
        / "results"
        / benchmark
    )

    build_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    results_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    seq_binary = (
        build_dir
        / f"{benchmark}_sequential"
    )

    omp_binary = (
        build_dir
        / f"{benchmark}_openmp"
    )

    print(
        "================================"
    )

    print(
        f"TCC2 HARNESS — {benchmark}"
    )

    print(
        "================================"
    )

    # --------------------------------
    # SEQUENCIAL
    # --------------------------------

    print(
        "\n[1/5] Compilando sequencial..."
    )

    if not compile_program(
        config["original"],
        config["include_dir"],
        seq_binary,
        openmp=False,
        dump=False
    ):

        sys.exit(1)

    print("Compilation: OK")

    print(
        "\n[2/5] Benchmark sequencial...\n"
    )

    sequential = run_timed(
        seq_binary
    )

    print(
        f"\nSequential median: "
        f"{sequential['median']:.6f}s"
    )

    # --------------------------------
    # CORRETUDE
    # --------------------------------

    if not validate_candidate(
        benchmark,
        config,
        build_dir
    ):

        print(
            "\nCandidato rejeitado."
        )

        sys.exit(1)

    # --------------------------------
    # PARALELO
    # --------------------------------

    print(
        "\n[4/5] Compilando OpenMP..."
    )

    if not compile_program(
        config["candidate"],
        config["include_dir"],
        omp_binary,
        openmp=True,
        dump=False
    ):

        sys.exit(1)

    print("Compilation: OK")

    print(
        "\n[5/5] Benchmark paralelo...\n"
    )

    parallel_results = []

    for threads in THREAD_COUNTS:

        print(
            f"--- {threads} THREAD(S) ---"
        )

        result = run_timed(
            omp_binary,
            threads
        )

        result["threads"] = threads

        parallel_results.append(
            result
        )

        print(
            f"Median="
            f"{result['median']:.6f}s\n"
        )

    one_thread = (
        parallel_results[0]["median"]
    )

    # --------------------------------
    # CSV
    # --------------------------------

    csv_file = (
        results_dir
        / "experiment_results.csv"
    )

    new_file = not csv_file.exists()

    with csv_file.open(
        "a",
        newline=""
    ) as file:

        writer = csv.writer(file)

        if new_file:

            writer.writerow([
                "timestamp",
                "benchmark",
                "version",
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

        # Sequencial
        writer.writerow([
            datetime.now().isoformat(),
            benchmark,
            "sequential",
            1,
            sequential["mean"],
            sequential["median"],
            sequential["std_dev"],
            sequential["min"],
            sequential["max"],
            1.0,
            1.0,
            1.0,
        ])

        # Paralelos
        for result in parallel_results:

            scaling = (
                one_thread
                / result["median"]
            )

            speedup = (
                sequential["median"]
                / result["median"]
            )

            efficiency = (
                speedup
                / result["threads"]
            )

            writer.writerow([
                datetime.now().isoformat(),
                benchmark,
                "openmp",
                result["threads"],
                result["mean"],
                result["median"],
                result["std_dev"],
                result["min"],
                result["max"],
                scaling,
                speedup,
                efficiency,
            ])

    # --------------------------------
    # RESUMO
    # --------------------------------

    print(
        "\n================================"
    )

    print("RESUMO")

    print(
        "================================"
    )

    print(
        f"Sequential: "
        f"{sequential['median']:.6f}s"
    )

    print()

    for result in parallel_results:

        speedup = (
            sequential["median"]
            / result["median"]
        )

        efficiency = (
            speedup
            / result["threads"]
        )

        print(
            f"{result['threads']} thread(s): "
            f"{result['median']:.6f}s | "
            f"speedup={speedup:.3f}x | "
            f"efficiency={efficiency:.3f}"
        )

    best = min(
        parallel_results,
        key=lambda x: x["median"]
    )

    best_speedup = (
        sequential["median"]
        / best["median"]
    )

    print()

    print(
        f"BEST: "
        f"{best['threads']} threads"
    )

    print(
        f"BEST SPEEDUP: "
        f"{best_speedup:.3f}x"
    )

    print(
        f"\nCSV: {csv_file}"
    )


if __name__ == "__main__":
    main()