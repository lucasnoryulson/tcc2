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
            openmp.append(result)

    if sequential is None:
        raise RuntimeError(
            "Sequential baseline not found."
        )

    if not openmp:
        raise RuntimeError(
            "No OpenMP configurations found."
        )

    # --------------------------------------------------------
    # Separate transformation benefit from true parallel gain.
    # --------------------------------------------------------

    one_thread = next(
        (
            result
            for result in openmp
            if result["threads"] == 1
        ),
        None,
    )

    parallel_configs = [
        result
        for result in openmp
        if result["threads"] >= 2
    ]

    transformation_benefit = (
        one_thread is not None
        and one_thread["speedup"] > MIN_SPEEDUP
    )

    improving_parallel = [
        result
        for result in parallel_configs
        if result["speedup"] > MIN_SPEEDUP
    ]

    parallel_benefit = bool(
        improving_parallel
    )

    best_parallel = None

    if parallel_configs:

        best_parallel = min(
            parallel_configs,
            key=lambda result:
                result["median_seconds"],
        )

    # --------------------------------------------------------
    # Overall beneficial configurations.
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

            "decision":
                "NO_BENEFIT",

            "parallel_status":
                "NO_BENEFIT",

            "sequential":
                sequential,

            "one_thread":
                one_thread,

            "best_parallel":
                best_parallel,

            "transformation_benefit":
                False,

            "parallel_benefit":
                False,

            "recommended":
                None,

            "next_action":
                "MODIFY_OR_REJECT_CANDIDATE",

            "reason":
                (
                    "No OpenMP configuration "
                    "improved over the sequential "
                    "baseline."
                ),
        }

    # --------------------------------------------------------
    # Raw fastest beneficial configuration.
    # --------------------------------------------------------

    raw_best = min(
        improving,
        key=lambda result:
            result["median_seconds"],
    )

    best_time = (
        raw_best["median_seconds"]
    )

    # --------------------------------------------------------
    # Near-tie detection.
    # --------------------------------------------------------

    near_ties = []

    for result in improving:

        slowdown = (
            result["median_seconds"]
            / best_time
            - 1.0
        )

        if slowdown <= NEAR_TIE_THRESHOLD:

            candidate = dict(result)

            candidate[
                "slowdown_vs_fastest"
            ] = slowdown

            near_ties.append(
                candidate
            )

    # --------------------------------------------------------
    # Resource-aware recommendation.
    # --------------------------------------------------------

    recommended = min(
        near_ties,
        key=lambda result: (
            result["threads"],
            result["median_seconds"],
        ),
    )

    # --------------------------------------------------------
    # True parallel scaling classification.
    # --------------------------------------------------------

    if parallel_benefit:

        parallel_status = (
            "PARALLEL_SUCCESS"
        )

        next_action = (
            "PROMOTE_CANDIDATE"
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
                "the resource-aware recommendation. "
                "At least one configuration using "
                "two or more threads outperformed "
                "the sequential baseline."
            )

        else:

            decision = (
                "RESOURCE_AWARE_NEAR_TIE"
            )

            reason = (
                "Multiple configurations are within "
                f"{NEAR_TIE_THRESHOLD * 100:.1f}% "
                "of the fastest median. The "
                "configuration using fewer threads "
                "was preferred. At least one "
                "configuration using two or more "
                "threads outperformed the sequential "
                "baseline."
            )

    else:

        parallel_status = (
            "PARALLEL_SCALING_FAILURE"
        )

        decision = (
            "TRANSFORMATION_ONLY"
        )

        next_action = (
            "MODIFY_PARALLEL_STRATEGY"
        )

        reason = (
            "The candidate improves runtime only "
            "in its one-thread OpenMP configuration. "
            "No configuration using two or more "
            "threads outperformed the sequential "
            "baseline. The observed benefit cannot "
            "be classified as successful parallel "
            "scaling."
        )

    return {
        "status":
            "SELECTED",

        "decision":
            decision,

        "parallel_status":
            parallel_status,

        "sequential":
            sequential,

        "one_thread":
            one_thread,

        "best_parallel":
            best_parallel,

        "transformation_benefit":
            transformation_benefit,

        "parallel_benefit":
            parallel_benefit,

        "raw_fastest":
            raw_best,

        "near_tie_threshold":
            NEAR_TIE_THRESHOLD,

        "near_tie_candidates":
            near_ties,

        "recommended":
            recommended,

        "next_action":
            next_action,

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
        "TCC2 PERFORMANCE SELECTOR v0.2"
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
