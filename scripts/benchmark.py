from pathlib import Path
import argparse
import subprocess
import statistics
import csv
import os
import sys
import hashlib
import math
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[1]

POLYBENCH_ROOT = (
    PROJECT_ROOT
    / "benchmarks"
    / "PolyBenchC-4.2.1"
)

UTILITIES_DIR = POLYBENCH_ROOT / "utilities"

THREAD_COUNTS = [
    int(value)
    for value in os.environ.get(
        "TCC2_THREAD_COUNTS",
        "1,2,4"
    ).split(",")
]
REPETITIONS = 5
CSV_COLUMNS = [
    "timestamp", "benchmark", "validation_mode", "version", "threads",
    "mean_seconds", "median_seconds", "std_dev", "min_seconds", "max_seconds",
    "scaling_speedup", "speedup_vs_sequential", "efficiency_vs_sequential",
]


BENCHMARKS = {

    "gemm": {
        "type": "polybench",

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

        "validation": "exact",
    },

    "jacobi-2d": {
        "type": "polybench",

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

        "validation": "exact",
    },

    "covariance": {
        "type": "polybench",

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

        "validation": "exact",
    },

    "dot": {
        "type": "standalone",

        "original":
            PROJECT_ROOT
            / "kernels"
            / "dot"
            / "sequential.cpp",

        "candidate":
            PROJECT_ROOT
            / "kernels"
            / "dot"
            / "manual_openmp.cpp",

        "validation": "numeric",

        "arguments": [
            "10000000"
        ],

        "rel_tol": 1e-9,
        "abs_tol": 1e-12,
    },

    "wavefront": {
    "type": "standalone",

    "original":
        PROJECT_ROOT
        / "kernels"
        / "wavefront"
        / "sequential.cpp",

    "candidate":
        PROJECT_ROOT
        / "kernels"
        / "wavefront"
        / "manual_openmp.cpp",

    "validation": "numeric",

    "arguments": [
        "4000"
    ],

    "rel_tol": 1e-12,
    "abs_tol": 1e-12,
},
  "nussinov": {
    "type": "polybench",

    "original":
        POLYBENCH_ROOT
        / "medley"
        / "nussinov"
        / "nussinov.c",

    "candidate":
        PROJECT_ROOT
        / "kernels"
        / "nussinov"
        / "manual_openmp.c",

    "include_dir":
        POLYBENCH_ROOT
        / "medley"
        / "nussinov",

    "reference":
        PROJECT_ROOT
        / "results"
        / "nussinov"
        / "reference_output.txt",

    "validation": "exact",
},

  "nussinov-auto": {
    "type": "polybench",

    "original":
        POLYBENCH_ROOT
        / "medley"
        / "nussinov"
        / "nussinov.c",

    "candidate":
        PROJECT_ROOT
        / "analysis"
        / "output"
        / "generated"
        / "nussinov_simd_auto.c",

    "include_dir":
        POLYBENCH_ROOT
        / "medley"
        / "nussinov",

    "reference":
        PROJECT_ROOT
        / "results"
        / "nussinov-auto"
        / "reference_output.txt",

    "validation": "exact",
},
}


def openmp_environment(threads):

    env = os.environ.copy()

    env["OMP_NUM_THREADS"] = str(threads)
    env["OMP_DYNAMIC"] = "FALSE"
    env["OMP_PROC_BIND"] = "TRUE"
    env["OMP_PLACES"] = "cores"

    return env


def compile_polybench(
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

        print("COMPILE_ERROR")
        print(result.stderr)

        return False

    return True


def compile_standalone(
    source,
    binary,
    openmp=False
):

    command = [
        "clang++",
        "-O3",
        "-std=c++14",
    ]

    if openmp:
        command.append("-fopenmp")

    command += [
        str(source),
        "-o",
        str(binary),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print("COMPILE_ERROR")
        print(result.stderr)

        return False

    return True


def compile_program(
    config,
    source,
    binary,
    openmp=False,
    dump=False
):

    if config["type"] == "polybench":

        return compile_polybench(
            source,
            config["include_dir"],
            binary,
            openmp=openmp,
            dump=dump
        )

    return compile_standalone(
        source,
        binary,
        openmp=openmp
    )


def parse_key_values(text):

    values = {}

    for line in text.splitlines():

        if "=" not in line:
            continue

        key, value = line.split(
            "=",
            1
        )

        values[key.strip()] = (
            value.strip()
        )

    return values


def run_once(
    config,
    binary,
    threads=None
):

    if threads is None:
        env = os.environ.copy()
    else:
        env = openmp_environment(
            threads
        )

    arguments = [
        str(binary)
    ]

    arguments += config.get(
        "arguments",
        []
    )

    result = subprocess.run(
        arguments,
        capture_output=True,
        text=True,
        env=env
    )

    if result.returncode != 0:

        print(result.stderr)

        raise RuntimeError(
            "Erro durante execução."
        )

    if config["type"] == "polybench":

        return float(
            result.stdout.strip()
        )

    values = parse_key_values(
        result.stdout
    )

    if "run_ms" not in values:

        print(result.stdout)

        raise RuntimeError(
            "run_ms não encontrado."
        )

    milliseconds = float(
        values["run_ms"]
    )

    return milliseconds / 1000.0


def run_timed(
    config,
    binary,
    threads=None
):

    times = []

    for run in range(
        1,
        REPETITIONS + 1
    ):

        value = run_once(
            config,
            binary,
            threads
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
        "mean":
            statistics.mean(times),

        "median":
            statistics.median(times),

        "std_dev":
            statistics.pstdev(times),

        "min":
            min(times),

        "max":
            max(times),
    }


def calculate_hash(data):

    return hashlib.sha256(
        data
    ).hexdigest()


def validate_exact(
    benchmark,
    config,
    build_dir
):

    candidate_binary = (
        build_dir
        / f"{benchmark}_candidate_dump"
    )

    sequential_binary = (
        build_dir
        / f"{benchmark}_sequential_dump"
    )

    # --------------------------------------------------------
    # Compile candidate with OpenMP.
    # --------------------------------------------------------

    success = compile_program(
        config,
        config["candidate"],
        candidate_binary,
        openmp=True,
        dump=True
    )

    if not success:
        return False

    # --------------------------------------------------------
    # Compile local sequential reference using the same
    # compiler, optimization flags and environment.
    # --------------------------------------------------------

    success = compile_program(
        config,
        config["original"],
        sequential_binary,
        openmp=False,
        dump=True
    )

    if not success:
        return False

    # --------------------------------------------------------
    # Execute local sequential reference.
    # --------------------------------------------------------

    sequential_result = subprocess.run(
        [str(sequential_binary)],
        capture_output=True
    )

    if sequential_result.returncode != 0:

        print(
            "SEQUENTIAL_RUNTIME_ERROR"
        )

        return False

    # --------------------------------------------------------
    # Execute OpenMP candidate.
    # --------------------------------------------------------

    candidate_result = subprocess.run(
        [str(candidate_binary)],
        capture_output=True,
        env=openmp_environment(4)
    )

    if candidate_result.returncode != 0:

        print(
            "CANDIDATE_RUNTIME_ERROR"
        )

        return False

    # PolyBench dumps arrays to stderr.
    sequential_hash = (
        calculate_hash(
            sequential_result.stderr
        )
    )

    candidate_hash = (
        calculate_hash(
            candidate_result.stderr
        )
    )

    print(
        "Reference source: "
        "local sequential / same toolchain"
    )

    print(
        f"Reference: {sequential_hash}"
    )

    print(
        f"Candidate: {candidate_hash}"
    )

    if candidate_hash == sequential_hash:

        print(
            "Validation mode: EXACT"
        )

        print(
            "CORRECT"
        )

        return True

    print(
        "Validation mode: EXACT"
    )

    print(
        "INCORRECT"
    )

    return False


def validate_numeric(
    config,
    binary,
    seq_binary
):

    env = openmp_environment(4)

    arguments = [
        str(binary)
    ]

    arguments += config.get(
        "arguments",
        []
    )

    result = subprocess.run(
        arguments,
        capture_output=True,
        text=True,
        env=env
    )

    if result.returncode != 0:

        print("RUNTIME_ERROR")
        print(result.stderr)

        return False

    values = parse_key_values(
        result.stdout
    )

    if "result" not in values:

        print(result.stdout)

        print(
            "Resultado numérico "
            "não encontrado."
        )

        return False

    candidate = float(
        values["result"]
    )

    # Se o próprio programa fornece
    # o resultado esperado, usamos ele.
    if "expected" in values:

        expected = float(
            values["expected"]
        )

        reference_source = (
            "program_expected"
        )

    else:

        # Caso contrário, executamos
        # a versão sequencial e usamos
        # seu resultado como referência.

        seq_arguments = [
            str(seq_binary)
        ]

        seq_arguments += config.get(
            "arguments",
            []
        )

        seq_result = subprocess.run(
            seq_arguments,
            capture_output=True,
            text=True
        )

        if seq_result.returncode != 0:

            print(
                "Erro executando "
                "referência sequencial."
            )

            return False

        seq_values = parse_key_values(
            seq_result.stdout
        )

        if "result" not in seq_values:

            print(seq_result.stdout)

            print(
                "Resultado da referência "
                "não encontrado."
            )

            return False

        expected = float(
            seq_values["result"]
        )

        reference_source = (
            "sequential_output"
        )

    absolute_error = abs(
        candidate - expected
    )

    if expected != 0.0:

        relative_error = (
            absolute_error
            / abs(expected)
        )

    else:

        relative_error = (
            absolute_error
        )

    rel_tol = config[
        "rel_tol"
    ]

    abs_tol = config[
        "abs_tol"
    ]

    correct = math.isclose(
        candidate,
        expected,
        rel_tol=rel_tol,
        abs_tol=abs_tol
    )

    print("Validation mode: NUMERIC")

    print(
        f"Reference source: "
        f"{reference_source}"
    )

    print(
        f"Expected: "
        f"{expected:.17g}"
    )

    print(
        f"Candidate: "
        f"{candidate:.17g}"
    )

    print(
        f"Absolute error: "
        f"{absolute_error:.17g}"
    )

    print(
        f"Relative error: "
        f"{relative_error:.17g}"
    )

    print(
        f"Relative tolerance: "
        f"{rel_tol}"
    )

    print(
        f"Absolute tolerance: "
        f"{abs_tol}"
    )

    if correct:

        print("CORRECT")

        return True

    print("INCORRECT")

    return False


def validate_candidate(
    benchmark,
    config,
    build_dir,
    omp_binary,
    seq_binary
):

    print(
        "\n[4/5] Validando corretude..."
    )

    if config["validation"] == "exact":

        return validate_exact(
            benchmark,
            config,
            build_dir
        )

    return validate_numeric(
        config,
        omp_binary,
        seq_binary
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark", choices=BENCHMARKS)
    parser.add_argument("--results-dir", type=Path, help="Fresh campaign directory, separate from historical results.")
    args = parser.parse_args()
    benchmark = args.benchmark
    if len(set(THREAD_COUNTS)) != len(THREAD_COUNTS) or 1 not in THREAD_COUNTS or any(count < 1 for count in THREAD_COUNTS):
        parser.error("Use distinct positive TCC2_THREAD_COUNTS including 1.")

    config = BENCHMARKS[
        benchmark
    ]

    build_dir = (
        PROJECT_ROOT
        / "build"
        / benchmark
    )

    results_dir = args.results_dir or (
        PROJECT_ROOT
        / "results"
        / benchmark
    )
    csv_file = results_dir / "experiment_results.csv"
    if csv_file.is_symlink() or (args.results_dir is not None and csv_file.exists()):
        parser.error("Campaign CSV already exists; select a fresh --results-dir.")
    if csv_file.exists():
        with csv_file.open(newline="") as stream:
            reader = csv.reader(stream)
            if next(reader, None) != CSV_COLUMNS or any(len(row) != len(CSV_COLUMNS) for row in reader):
                parser.error("Existing CSV has an incompatible schema; use --results-dir with a fresh directory.")

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

    print(
        "\n[1/5] Compilando sequencial..."
    )

    if not compile_program(
        config,
        config["original"],
        seq_binary,
        openmp=False
    ):

        sys.exit(1)

    print("Compilation: OK")

    print(
        "\n[2/5] Benchmark sequencial...\n"
    )

    sequential = run_timed(
        config,
        seq_binary
    )

    print(
        f"\nSequential median: "
        f"{sequential['median']:.6f}s"
    )

    print(
        "\n[3/5] Compilando OpenMP..."
    )

    if not compile_program(
        config,
        config["candidate"],
        omp_binary,
        openmp=True
    ):

        sys.exit(1)

    print("Compilation: OK")

    if not validate_candidate(
        benchmark,
        config,
        build_dir,
        omp_binary,
        seq_binary
    ):

        print(
            "\nCandidato rejeitado."
        )

        sys.exit(1)

    print(
        "\n[5/5] Benchmark paralelo...\n"
    )

    parallel_results = []

    for threads in THREAD_COUNTS:

        print(
            f"--- {threads} THREAD(S) ---"
        )

        result = run_timed(
            config,
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

    one_thread = next(result["median"] for result in parallel_results if result["threads"] == 1)

    csv_file = (
        results_dir
        / "experiment_results.csv"
    )

    new_file = not csv_file.exists()

    timestamp = (
        datetime.now().isoformat()
    )

    with csv_file.open(
        "a",
        newline=""
    ) as file:

        writer = csv.writer(file)

        if new_file:

            writer.writerow(CSV_COLUMNS)

        writer.writerow([
            timestamp,
            benchmark,
            config["validation"],
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
                timestamp,
                benchmark,
                config["validation"],
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
