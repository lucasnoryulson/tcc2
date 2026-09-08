import argparse
import json
import re
import sys
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

PERCENT_RE = re.compile(
    r"\(\s*\+\-\s*([0-9.]+)%\s*\)"
)

VALUE_RE = re.compile(
    r"^\s*([\d,]+)\s+(.+?)\s+\(\s*\+\-\s*([0-9.]+)%\s*\)"
)

TIME_RE = re.compile(
    r"^\s*([0-9.]+)\s+\+\-\s+([0-9.]+)\s+seconds time elapsed"
)


# ============================================================
# HELPERS
# ============================================================

def parse_number(value):
    return float(value.replace(",", ""))


def parse_perf_file(path):
    text = path.read_text()

    counters = {}
    elapsed_seconds = None

    for line in text.splitlines():

        match = VALUE_RE.match(line)

        if match:
            value = parse_number(match.group(1))
            event = match.group(2).strip()

            counters[event] = value

            continue

        match = TIME_RE.match(line)

        if match:
            elapsed_seconds = float(
                match.group(1)
            )

    if not counters:
        raise RuntimeError(
            f"No performance counters found in {path}"
        )

    if elapsed_seconds is None:
        raise RuntimeError(
            f"Elapsed time not found in {path}"
        )

    return {
        "file": str(path),
        "counters": counters,
        "time_elapsed_seconds": elapsed_seconds,
    }


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(data):

    counters = data["counters"]

    cycles = counters.get("cycles")
    instructions = counters.get("instructions")

    cache_references = counters.get(
        "cache-references"
    )

    cache_misses = counters.get(
        "cache-misses"
    )

    branches = counters.get("branches")
    branch_misses = counters.get(
        "branch-misses"
    )

    ipc = None

    if cycles and cycles > 0:
        ipc = instructions / cycles

    cache_miss_rate = None

    if (
        cache_references
        and cache_references > 0
    ):
        cache_miss_rate = (
            cache_misses
            / cache_references
            * 100.0
        )

    branch_miss_rate = None

    if (
        branches
        and branches > 0
    ):
        branch_miss_rate = (
            branch_misses
            / branches
            * 100.0
        )

    return {
        "cycles": cycles,
        "instructions": instructions,
        "ipc": ipc,
        "cache_references": cache_references,
        "cache_misses": cache_misses,
        "cache_miss_rate_percent":
            cache_miss_rate,
        "branches": branches,
        "branch_misses": branch_misses,
        "branch_miss_rate_percent":
            branch_miss_rate,
        "time_elapsed_seconds":
            data["time_elapsed_seconds"],
    }


# ============================================================
# COMPARISON
# ============================================================

def compare_profiles(
    sequential,
    parallel
):

    seq = sequential["metrics"]
    omp = parallel["metrics"]

    speedup = (
        seq["time_elapsed_seconds"]
        / omp["time_elapsed_seconds"]
    )

    result = {
        "speedup": speedup,
        "sequential": seq,
        "openmp": omp,
    }

    if (
        seq["ipc"] is not None
        and omp["ipc"] is not None
    ):
        result["ipc_change_percent"] = (
            (
                omp["ipc"]
                / seq["ipc"]
            )
            - 1.0
        ) * 100.0

    if (
        seq["cache_miss_rate_percent"]
        is not None
        and omp["cache_miss_rate_percent"]
        is not None
    ):
        result["cache_miss_rate_change_percent"] = (
            (
                omp["cache_miss_rate_percent"]
                / seq["cache_miss_rate_percent"]
            )
            - 1.0
        ) * 100.0

    if (
        seq["branch_miss_rate_percent"]
        is not None
        and omp["branch_miss_rate_percent"]
        is not None
    ):
        result["branch_miss_rate_change_percent"] = (
            (
                omp["branch_miss_rate_percent"]
                / seq["branch_miss_rate_percent"]
            )
            - 1.0
        ) * 100.0

    return result


# ============================================================
# SUMMARY
# ============================================================

def build_summary(
    sequential_file,
    openmp_file,
    threads
):

    sequential_raw = parse_perf_file(
        sequential_file
    )

    openmp_raw = parse_perf_file(
        openmp_file
    )

    sequential = {
        "file":
            sequential_raw["file"],

        "metrics":
            calculate_metrics(
                sequential_raw
            ),
    }

    openmp = {
        "file":
            openmp_raw["file"],

        "threads":
            threads,

        "metrics":
            calculate_metrics(
                openmp_raw
            ),
    }

    comparison = compare_profiles(
        sequential,
        openmp
    )

    return {
        "schema":
            "tcc2-profiling-summary",

        "version":
            "0.1",

        "sequential":
            sequential,

        "openmp":
            openmp,

        "comparison":
            comparison,
    }


# ============================================================
# PRINT
# ============================================================

def print_summary(summary):

    seq = summary["sequential"]["metrics"]
    omp = summary["openmp"]["metrics"]
    comparison = summary["comparison"]

    print(
        "========================================"
    )

    print(
        "TCC2 PROFILING PARSER v0.1"
    )

    print(
        "========================================"
    )

    print()

    print("Sequential:")
    print(
        f"  Time:              "
        f"{seq['time_elapsed_seconds']:.6f} s"
    )
    print(
        f"  IPC:               "
        f"{seq['ipc']:.3f}"
    )
    print(
        f"  Cache miss rate:   "
        f"{seq['cache_miss_rate_percent']:.2f}%"
    )
    print(
        f"  Branch miss rate:  "
        f"{seq['branch_miss_rate_percent']:.3f}%"
    )

    print()

    print(
        f"OpenMP "
        f"{summary['openmp']['threads']}T:"
    )

    print(
        f"  Time:              "
        f"{omp['time_elapsed_seconds']:.6f} s"
    )

    print(
        f"  IPC:               "
        f"{omp['ipc']:.3f}"
    )

    print(
        f"  Cache miss rate:   "
        f"{omp['cache_miss_rate_percent']:.2f}%"
    )

    print(
        f"  Branch miss rate:  "
        f"{omp['branch_miss_rate_percent']:.3f}%"
    )

    print()

    print(
        f"Speedup:             "
        f"{comparison['speedup']:.3f}x"
    )

    print(
        f"IPC change:          "
        f"{comparison['ipc_change_percent']:+.2f}%"
    )

    print(
        f"Cache miss change:   "
        f"{comparison['cache_miss_rate_change_percent']:+.2f}%"
    )

    print(
        f"Branch miss change:  "
        f"{comparison['branch_miss_rate_change_percent']:+.2f}%"
    )


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Parse TCC2 perf stat outputs "
            "and generate structured profiling evidence."
        )
    )

    parser.add_argument(
        "--sequential",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--openmp",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--threads",
        required=True,
        type=int,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    try:

        summary = build_summary(
            args.sequential,
            args.openmp,
            args.threads,
        )

        args.output.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        args.output.write_text(
            json.dumps(
                summary,
                indent=2
            )
        )

        print_summary(summary)

        print()

        print(
            f"Saved: {args.output}"
        )

    except Exception as exc:

        print(
            f"ERROR: {exc}",
            file=sys.stderr
        )

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
