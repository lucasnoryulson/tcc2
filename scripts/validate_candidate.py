from pathlib import Path
import subprocess
import hashlib
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

POLYBENCH_ROOT = (
    PROJECT_ROOT
    / "benchmarks"
    / "PolyBenchC-4.2.1"
)

UTILITIES_DIR = POLYBENCH_ROOT / "utilities"

BUILD_DIR = PROJECT_ROOT / "build" / "candidates"
BUILD_DIR.mkdir(parents=True, exist_ok=True)


BENCHMARKS = {

    "gemm": {
        "source_dir":
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
        "source_dir":
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
    "source_dir":
        POLYBENCH_ROOT
        / "datamining"
        / "covariance",

    "reference":
        PROJECT_ROOT
        / "results"
        / "covariance"
        / "reference_output.txt",
    },
    "nussinov": {
    "source_dir":
        POLYBENCH_ROOT
        / "medley"
        / "nussinov",

    "reference":
        PROJECT_ROOT
        / "results"
        / "nussinov"
        / "reference_output.txt",
    },
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def compile_candidate(source, benchmark):

    benchmark_dir = BENCHMARKS[benchmark]["source_dir"]

    binary = BUILD_DIR / f"{benchmark}_{source.stem}"

    command = [
        "clang",
        "-O3",
        "-fopenmp",
        "-DLARGE_DATASET",
        "-DPOLYBENCH_DUMP_ARRAYS",

        f"-I{UTILITIES_DIR}",
        f"-I{benchmark_dir}",

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

        return None

    return binary


def run_candidate(binary):

    result = subprocess.run(
        [str(binary)],
        capture_output=True
    )

    if result.returncode != 0:

        print("\nRUNTIME_ERROR")

        return None

    return result.stderr


def validate(benchmark, source):

    reference_path = BENCHMARKS[benchmark]["reference"]

    print("==============================")
    print("Candidate Validator")
    print("==============================")

    print(f"Benchmark: {benchmark}")
    print(f"Source: {source}")

    if not reference_path.exists():

        print("\nREFERENCE_NOT_FOUND")
        print(reference_path)

        return

    binary = compile_candidate(
        source,
        benchmark
    )

    if binary is None:
        return

    print("Compilation: OK")

    output = run_candidate(binary)

    if output is None:
        return

    print("Execution: OK")

    reference = reference_path.read_bytes()

    reference_hash = sha256(reference)
    candidate_hash = sha256(output)

    print()
    print(f"Reference: {reference_hash}")
    print(f"Candidate: {candidate_hash}")

    print()

    if reference_hash == candidate_hash:

        print("==============================")
        print("CORRECT")
        print("==============================")

    else:

        print("==============================")
        print("INCORRECT")
        print("==============================")


def main():

    if len(sys.argv) != 3:

        print(
            "Uso:"
        )

        print(
            "python3 validate_candidate.py "
            "<benchmark> <arquivo.c>"
        )

        print()
        print("Benchmarks disponíveis:")

        for benchmark in BENCHMARKS:
            print(f"  - {benchmark}")

        sys.exit(1)

    benchmark = sys.argv[1]

    if benchmark not in BENCHMARKS:

        print(
            f"Benchmark desconhecido: {benchmark}"
        )

        sys.exit(1)

    source = Path(
        sys.argv[2]
    ).resolve()

    if not source.exists():

        print(
            f"Arquivo não encontrado: {source}"
        )

        sys.exit(1)

    validate(
        benchmark,
        source
    )


if __name__ == "__main__":
    main()
