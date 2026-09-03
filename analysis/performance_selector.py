import argparse
import csv
import json
import sys
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

NEAR_TIE_THRESHOLD = 0.02
MIN_SPEEDUP = 1.0


# ============================================================
# CSV
# ============================================================

def load_results(path):

    rows = []

    with path.open(
        newline=""
    ) as file:

        reader = csv.DictReader(
            file
        )

        for row in reader:

            rows.append({
                "mode":
                    row["mode"],

                "threads":
                    int(
                        row["threads"]
                    ),

                "median_seconds":
                    float(
                        row[
                            "median_seconds"
                        ]
                    ),

                "mean_seconds":
                    float(
                        row[
                            "mean_seconds"
                        ]
                    ),

                "speedup":
                    float(
                        row["speedup"]
                    ),

                "efficiency":
                    float(
                        row["efficiency"]
                    ),
            })

    return rows


# ============================================================
# SELECTOR
# ============================================================

def select_configuration(
    results
):

    sequential = None

    openmp = []

    for result in results:

        if result["mode"] == "sequential":

            sequential = result

        elif result["mode"] == "openmp":

            openmp.append(
                result
            )

    if sequential is None:

        raise RuntimeError(
            "Sequential baseline not found."
        )

    if not openmp:

        raise RuntimeError(
            "No OpenMP configurations found."
        )

    # --------------------------------------------------------
    # Only candidates that actually improve runtime.
    # --------------------------------------------------------

    improving = [
        result
        for result in openmp
        if result["speedup"] > MIN_SPEEDUP
    ]

    if not improving:

        return {
            "status":
                "NO_BENEFICIAL_CONFIGURATION",

            "recommended":
                None,

            "reason":
                (
                    "No OpenMP configuration "
                    "improved over the sequential "
                    "baseline."
                ),
        }

    # --------------------------------------------------------
    # Raw fastest configuration
    # --------------------------------------------------------

    raw_best = min(
        improving,
        key=lambda result:
            result["median_seconds"]
    )

    best_time = (
        raw_best[
            "median_seconds"
        ]
    )

    # --------------------------------------------------------
    # Near-tie detection
    #
    # A configuration belongs to the near-tie group when
    # its median is at most 2% slower than the fastest.
    # --------------------------------------------------------

    near_ties = []

    for result in improving:

        slowdown = (
            result["median_seconds"]
            / best_time
            - 1.0
        )

        if slowdown <= NEAR_TIE_THRESHOLD:

            candidate = dict(
                result
            )

            candidate[
                "slowdown_vs_fastest"
            ] = slowdown

            near_ties.append(
                candidate
            )

    # --------------------------------------------------------
    # Resource-aware selection
    #
    # If runtimes are effectively tied, prefer fewer threads.
    # --------------------------------------------------------

    recommended = min(
        near_ties,
        key=lambda result: (
            result["threads"],
            result["median_seconds"],
        )
    )

    if (
        recommended["threads"]
        == raw_best["threads"]
    ):

        decision = (
            "FASTEST_CONFIGURATION"
        )

        reason = (
            "The fastest configuration is also "
            "the resource-aware recommendation."
        )

    else:

        decision = (
            "RESOURCE_AWARE_NEAR_TIE"
        )

        reason = (
            "Multiple configurations are within "
            f"{NEAR_TIE_THRESHOLD * 100:.1f}% "
            "of the fastest median. The configuration "
            "using fewer threads was preferred."
        )

    return {
        "status":
            "SELECTED",

        "decision":
            decision,

        "sequential":
            sequential,

        "raw_fastest":
            raw_best,

        "near_tie_threshold":
            NEAR_TIE_THRESHOLD,

        "near_tie_candidates":
            near_ties,

        "recommended":
            recommended,

        "reason":
            reason,
    }


# ============================================================
# PRINTING
# ============================================================

def print_result(
    result
):

    print(
        "================================="
    )

    print(
        "TCC2 PERFORMANCE SELECTOR v0.1"
    )

    print(
        "================================="
    )

    print()

    print(
        f"Status: "
        f"{result['status']}"
    )

    if (
        result["status"]
        != "SELECTED"
    ):

        print(
            f"Reason: "
            f"{result['reason']}"
        )

        return

    raw_best = result[
        "raw_fastest"
    ]

    recommended = result[
        "recommended"
    ]

    print()

    print(
        "Raw fastest configuration:"
    )

    print(
        f"  Threads:    "
        f"{raw_best['threads']}"
    )

    print(
        f"  Median:     "
        f"{raw_best['median_seconds']:.9f} s"
    )

    print(
        f"  Speedup:    "
        f"{raw_best['speedup']:.3f}x"
    )

    print(
        f"  Efficiency: "
        f"{raw_best['efficiency']:.3f}"
    )

    print()

    print(
        "Near-tie candidates:"
    )

    for candidate in (
        result[
            "near_tie_candidates"
        ]
    ):

        print(
            f"  {candidate['threads']} thread(s): "
            f"{candidate['median_seconds']:.9f} s "
            f"| speedup "
            f"{candidate['speedup']:.3f}x "
            f"| efficiency "
            f"{candidate['efficiency']:.3f} "
            f"| slowdown vs fastest "
            f"{candidate['slowdown_vs_fastest'] * 100:.3f}%"
        )

    print()

    print(
        "Recommended configuration:"
    )

    print(
        f"  Threads:    "
        f"{recommended['threads']}"
    )

    print(
        f"  Median:     "
        f"{recommended['median_seconds']:.9f} s"
    )

    print(
        f"  Speedup:    "
        f"{recommended['speedup']:.3f}x"
    )

    print(
        f"  Efficiency: "
        f"{recommended['efficiency']:.3f}"
    )

    print()

    print(
        f"Decision: "
        f"{result['decision']}"
    )

    print(
        f"Reason: "
        f"{result['reason']}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "results",
        type=Path,
        help=(
            "CSV produzido pelo "
            "Performance Gate."
        )
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    args = parser.parse_args()

    input_file = (
        args.results.resolve()
    )

    if not input_file.exists():

        print(
            f"Arquivo não encontrado: "
            f"{input_file}"
        )

        sys.exit(1)

    results = load_results(
        input_file
    )

    selection = (
        select_configuration(
            results
        )
    )

    print_result(
        selection
    )

    if args.output:

        output_file = (
            args.output.resolve()
        )

    else:

        output_file = (
            input_file.parent
            / "auto_generated_selection.json"
        )

    output_file.write_text(
        json.dumps(
            selection,
            indent=2
        )
    )

    print()

    print(
        f"JSON salvo em: "
        f"{output_file}"
    )

    print(
        "================================="
    )


if __name__ == "__main__":
    main()
