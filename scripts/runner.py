from pathlib import Path
import subprocess
import hashlib
import statistics
import csv
from datetime import datetime


# -------------------------------------------------------
# Caminhos do projeto
# -------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

POLYBENCH_ROOT = (
    PROJECT_ROOT
    / "benchmarks"
    / "PolyBenchC-4.2.1"
)

GEMM_DIR = (
    POLYBENCH_ROOT
    / "linear-algebra"
    / "blas"
    / "gemm"
)

UTILITIES_DIR = POLYBENCH_ROOT / "utilities"

BUILD_DIR = PROJECT_ROOT / "build" / "gemm"
RESULTS_DIR = PROJECT_ROOT / "results" / "gemm"

BUILD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------
# Configuração do experimento
# -------------------------------------------------------

COMPILER = "clang"
OPTIMIZATION = "-O3"
REPETITIONS = 5

SOURCE_FILE = GEMM_DIR / "gemm.c"
POLYBENCH_FILE = UTILITIES_DIR / "polybench.c"

TIMING_BINARY = BUILD_DIR / "gemm_time"
REFERENCE_BINARY = BUILD_DIR / "gemm_reference"

REFERENCE_OUTPUT = RESULTS_DIR / "reference_output.txt"
CSV_FILE = RESULTS_DIR / "baseline.csv"


def run_command(command):
    """Executa um comando e interrompe caso exista erro."""

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("Erro ao executar comando:")
        print(" ".join(map(str, command)))
        print(result.stderr)
        raise RuntimeError("Falha durante execução.")

    return result


# -------------------------------------------------------
# Compilação
# -------------------------------------------------------

def compile_timing_version():

    print("\n[1/5] Compilando versão para medição...")

    command = [
        COMPILER,
        OPTIMIZATION,
        "-DLARGE_DATASET",
        "-DPOLYBENCH_TIME",
        f"-I{UTILITIES_DIR}",
        str(SOURCE_FILE),
        str(POLYBENCH_FILE),
        "-o",
        str(TIMING_BINARY),
        "-lm",
    ]

    run_command(command)

    print("OK")


def compile_reference_version():

    print("\n[2/5] Compilando versão de referência...")

    command = [
        COMPILER,
        OPTIMIZATION,
        "-DLARGE_DATASET",
        "-DPOLYBENCH_DUMP_ARRAYS",
        f"-I{UTILITIES_DIR}",
        str(SOURCE_FILE),
        str(POLYBENCH_FILE),
        "-o",
        str(REFERENCE_BINARY),
        "-lm",
    ]

    run_command(command)

    print("OK")


# -------------------------------------------------------
# Execução e medição
# -------------------------------------------------------

def benchmark():

    print(f"\n[3/5] Executando GEMM {REPETITIONS} vezes...")

    times = []

    for execution in range(1, REPETITIONS + 1):

        result = run_command([str(TIMING_BINARY)])

        time_value = float(result.stdout.strip())

        times.append(time_value)

        print(
            f"Execução {execution}: "
            f"{time_value:.6f} s"
        )

    return times


# -------------------------------------------------------
# Geração da referência
# -------------------------------------------------------

def generate_reference():

    print("\n[4/5] Gerando saída sequencial de referência...")

    result = subprocess.run(
        [str(REFERENCE_BINARY)],
        capture_output=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Erro durante geração da referência."
        )

    # PolyBench escreve os arrays em stderr.
    REFERENCE_OUTPUT.write_bytes(result.stderr)

    sha256 = hashlib.sha256(result.stderr).hexdigest()

    print(f"Arquivo: {REFERENCE_OUTPUT}")
    print(f"SHA-256: {sha256}")

    return sha256


# -------------------------------------------------------
# Salvar resultados
# -------------------------------------------------------

def save_results(times, sha256):

    mean_time = statistics.mean(times)
    median_time = statistics.median(times)
    minimum = min(times)
    maximum = max(times)
    std_dev = statistics.pstdev(times)

    new_file = not CSV_FILE.exists()

    with CSV_FILE.open("a", newline="") as file:

        writer = csv.writer(file)

        if new_file:
            writer.writerow([
                "timestamp",
                "benchmark",
                "dataset",
                "compiler",
                "optimization",
                "repetitions",
                "mean_seconds",
                "median_seconds",
                "min_seconds",
                "max_seconds",
                "std_dev",
                "reference_sha256",
            ])

        writer.writerow([
            datetime.now().isoformat(),
            "gemm",
            "LARGE",
            COMPILER,
            OPTIMIZATION,
            REPETITIONS,
            mean_time,
            median_time,
            minimum,
            maximum,
            std_dev,
            sha256,
        ])

    print("\n[5/5] Resultados salvos.")

    print("\n==============================")
    print("RESUMO DO EXPERIMENTO")
    print("==============================")

    print("Benchmark: GEMM")
    print("Dataset: LARGE")
    print(f"Compilador: {COMPILER}")
    print(f"Otimização: {OPTIMIZATION}")
    print(f"Execuções: {REPETITIONS}")

    print()
    print(f"Média:   {mean_time:.6f} s")
    print(f"Mediana: {median_time:.6f} s")
    print(f"Mínimo:  {minimum:.6f} s")
    print(f"Máximo:  {maximum:.6f} s")
    print(f"Desvio:  {std_dev:.6f} s")

    print()
    print(f"SHA-256: {sha256}")

    print()
    print(f"CSV: {CSV_FILE}")


# -------------------------------------------------------
# Programa principal
# -------------------------------------------------------

def main():

    print("==============================")
    print("TCC2 Experimental Runner")
    print("==============================")

    compile_timing_version()

    compile_reference_version()

    times = benchmark()

    sha256 = generate_reference()

    save_results(times, sha256)


if __name__ == "__main__":
    main()
