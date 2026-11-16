import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.artifact_provenance import load_performance_report

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

        fieldnames = set(
            reader.fieldnames or []
        )

        # Support both the legacy experiment CSV schema
        # and the current benchmark.py schema.
        mode_column = (
            "mode"
            if "mode" in fieldnames
            else "version"
        )

        speedup_column = (
            "speedup"
            if "speedup" in fieldnames
            else "speedup_vs_sequential"
        )

        efficiency_column = (
            "efficiency"
            if "efficiency" in fieldnames
            else "efficiency_vs_sequential"
        )

        required = {
            mode_column,
            "threads",
            "median_seconds",
            "mean_seconds",
            speedup_column,
            efficiency_column,
        }

        missing = required - fieldnames

        if missing:
            raise ValueError(
                "CSV is missing required columns: "
                + ", ".join(
                    sorted(missing)
                )
            )

        for row in reader:

            rows.append({
                "mode":
                    row[mode_column],

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
                        row[
                            speedup_column
                        ]
                    ),

                "efficiency":
                    float(
                        row[
                            efficiency_column
                        ]
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

    transformation_speedup = None

    if one_thread is not None:
        transformation_speedup = (
            sequential["median_seconds"]
            / one_thread["median_seconds"]
        )

    transformation_benefit = (
        transformation_speedup is not None
        and transformation_speedup > MIN_SPEEDUP
    )

    parallel_scaling_candidates = []

    if one_thread is not None:

        for result in parallel_configs:

            candidate = dict(result)

            parallel_scaling_speedup = (
                one_thread["median_seconds"]
                / result["median_seconds"]
            )

            candidate[
                "parallel_scaling_speedup"
            ] = parallel_scaling_speedup

            candidate[
                "parallel_scaling_efficiency"
            ] = (
                parallel_scaling_speedup
                / result["threads"]
            )

            parallel_scaling_candidates.append(
                candidate
            )

    improving_parallel = [
        result
        for result in parallel_scaling_candidates
        if (
            result["parallel_scaling_speedup"]
            > MIN_SPEEDUP
        )
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
    # Scientifically separated performance metrics.
    # --------------------------------------------------------

    end_to_end_speedup = (
        sequential["median_seconds"]
        / recommended["median_seconds"]
    )

    runtime_reduction = (
        1.0
        - (
            recommended["median_seconds"]
            / sequential["median_seconds"]
        )
    )

    parallel_scaling_speedup = None
    parallel_scaling_efficiency = None

    if one_thread is not None:

        parallel_scaling_speedup = (
            one_thread["median_seconds"]
            / recommended["median_seconds"]
        )

        parallel_scaling_efficiency = (
            parallel_scaling_speedup
            / recommended["threads"]
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
                "the transformed one-thread baseline."
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
            "threads outperformed the transformed "
            "one-thread baseline. The observed "
            "benefit cannot "
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

        "transformation_speedup":
            transformation_speedup,

        "parallel_scaling_speedup":
            parallel_scaling_speedup,

        "parallel_scaling_efficiency":
            parallel_scaling_efficiency,

        "end_to_end_speedup":
            end_to_end_speedup,

        "runtime_reduction":
            runtime_reduction,

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
        f"  End-to-end speedup: "
        f"{result['end_to_end_speedup']:.3f}x"
    )

    print()
    print(
        "Performance decomposition:"
    )

    if result["transformation_speedup"] is not None:
        print(
            f"  Transformation speedup:      "
            f"{result['transformation_speedup']:.3f}x"
        )

    if result["parallel_scaling_speedup"] is not None:
        print(
            f"  Parallel scaling speedup:    "
            f"{result['parallel_scaling_speedup']:.3f}x"
        )

    if result["parallel_scaling_efficiency"] is not None:
        print(
            f"  Parallel scaling efficiency: "
            f"{result['parallel_scaling_efficiency'] * 100:.2f}%"
        )

    print(
        f"  Runtime reduction:           "
        f"{result['runtime_reduction'] * 100:.2f}%"
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

    parser.add_argument(
        "--performance-report", type=Path,
        help="Verify gate provenance and attach it to the selection.",
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

    evidence = None
    if args.performance_report is not None:
        report, results, reference = load_performance_report(
            args.performance_report.resolve(), input_file,
        )
        evidence = {
            "performance_report": reference,
            "campaign_id": report["provenance"]["campaign_id"],
            "candidate_id": report["provenance"]["candidate_id"],
        }
    else:
        results = load_results(input_file)

    selection = (
        select_configuration(
            results
        )
    )
    if evidence is not None:
        selection["evidence"] = evidence

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
