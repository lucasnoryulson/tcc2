import argparse
import csv
import json
from pathlib import Path


NEAR_TIE_THRESHOLD = 0.02
MIN_SPEEDUP = 1.0
MAX_ABSOLUTE_ERROR = 1e-12


def load_results(path):
    with path.open(newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise RuntimeError(
            "Autotuning CSV is empty."
        )

    # Preserve only the newest campaign if a CSV ever
    # contains more than one execution.
    latest_timestamp = max(
        row["timestamp"]
        for row in rows
    )

    rows = [
        row
        for row in rows
        if row["timestamp"] == latest_timestamp
    ]

    results = []

    for row in rows:
        results.append({
            "block_size":
                int(row["block_size"]),

            "threads":
                int(row["threads"]),

            "mean_seconds":
                float(row["mean_ms"]) / 1000.0,

            "median_seconds":
                float(row["median_ms"]) / 1000.0,

            "std_dev_seconds":
                float(row["std_dev_ms"]) / 1000.0,

            "min_seconds":
                float(row["min_ms"]) / 1000.0,

            "max_seconds":
                float(row["max_ms"]) / 1000.0,

            "speedup":
                float(
                    row["speedup_vs_sequential"]
                ),

            "efficiency":
                float(row["efficiency"]),

            "max_absolute_error":
                float(
                    row["max_absolute_error"]
                ),
        })

    baseline_ms = float(
        rows[0]["sequential_median_ms"]
    )

    n = int(
        rows[0]["n"]
    )

    return {
        "timestamp": latest_timestamp,
        "n": n,
        "sequential_median_seconds":
            baseline_ms / 1000.0,
        "results": results,
    }


def select_configuration(data):

    results = data["results"]

    # --------------------------------------------------------
    # Correct configurations only.
    # --------------------------------------------------------

    correct = [
        result
        for result in results
        if result["max_absolute_error"]
        <= MAX_ABSOLUTE_ERROR
    ]

    if not correct:
        return {
            "status":
                "NO_CORRECT_CONFIGURATION",

            "recommended":
                None,

            "reason":
                "No numerically valid autotuning "
                "configuration was found.",
        }

    # --------------------------------------------------------
    # Separate 1T transformation effects from multicore gain.
    # --------------------------------------------------------

    one_thread_configs = [
        result
        for result in correct
        if result["threads"] == 1
    ]

    parallel_configs = [
        result
        for result in correct
        if result["threads"] >= 2
    ]

    best_one_thread = (
        min(
            one_thread_configs,
            key=lambda result:
                result["median_seconds"],
        )
        if one_thread_configs
        else None
    )

    improving_parallel = [
        result
        for result in parallel_configs
        if result["speedup"] > MIN_SPEEDUP
    ]

    best_parallel = (
        min(
            improving_parallel,
            key=lambda result:
                result["median_seconds"],
        )
        if improving_parallel
        else None
    )

    transformation_benefit = (
        best_one_thread is not None
        and
        best_one_thread["speedup"]
        > MIN_SPEEDUP
    )

    parallel_benefit = (
        best_parallel is not None
    )

    # --------------------------------------------------------
    # Any configuration improving over sequential.
    # --------------------------------------------------------

    improving = [
        result
        for result in correct
        if result["speedup"] > MIN_SPEEDUP
    ]

    sequential = {
        "mode":
            "sequential",

        "threads":
            1,

        "block_size":
            None,

        "median_seconds":
            data[
                "sequential_median_seconds"
            ],

        "speedup":
            1.0,

        "efficiency":
            1.0,
    }

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

            "best_one_thread":
                best_one_thread,

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
                "No valid autotuning configuration "
                "improved over the sequential baseline.",
        }

    # --------------------------------------------------------
    # Raw fastest full configuration.
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
    # Near-tie across complete configurations.
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

            near_ties.append(candidate)

    # --------------------------------------------------------
    # Resource-aware:
    # among effectively tied configurations, use fewer
    # threads. block_size is preserved as part of the
    # selected configuration, but is not treated as a
    # resource-count metric.
    # --------------------------------------------------------

    recommended = min(
        near_ties,
        key=lambda result: (
            result["threads"],
            result["median_seconds"],
        ),
    )

    if parallel_benefit:

        parallel_status = (
            "PARALLEL_SUCCESS"
        )

        next_action = (
            "PROMOTE_CANDIDATE"
        )

        if (
            recommended["block_size"]
            == raw_best["block_size"]
            and
            recommended["threads"]
            == raw_best["threads"]
        ):
            decision = (
                "FASTEST_CONFIGURATION"
            )

            reason = (
                "The fastest complete autotuning "
                "configuration is also the "
                "resource-aware recommendation. "
                "At least one configuration using "
                "two or more threads outperformed "
                "the sequential baseline."
            )

        else:
            decision = (
                "RESOURCE_AWARE_NEAR_TIE"
            )

            reason = (
                "Multiple complete autotuning "
                "configurations are within "
                f"{NEAR_TIE_THRESHOLD * 100:.1f}% "
                "of the fastest median. Fewer "
                "threads were preferred while "
                "preserving block_size."
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
            "Only one-thread autotuning "
            "configurations improve runtime. "
            "No configuration using two or more "
            "threads outperformed the sequential "
            "baseline."
        )

    return {
        "status":
            "SELECTED",

        "decision":
            decision,

        "parallel_status":
            parallel_status,

        "configuration_dimensions": [
            "block_size",
            "threads",
        ],

        "search_space": {
            "n":
                data["n"],

            "block_sizes":
                sorted({
                    result["block_size"]
                    for result in results
                }),

            "thread_counts":
                sorted({
                    result["threads"]
                    for result in results
                }),

            "configurations":
                len(results),
        },

        "sequential":
            sequential,

        "best_one_thread":
            best_one_thread,

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


def print_result(result):

    print(
        "================================="
    )
    print(
        "TCC2 AUTOTUNING SELECTOR v0.1"
    )
    print(
        "================================="
    )

    print(
        f"Status: {result['status']}"
    )

    if (
        result["status"]
        != "SELECTED"
    ):
        print(
            f"Reason: {result['reason']}"
        )
        return

    raw = result["raw_fastest"]
    recommended = result["recommended"]

    print()
    print("Raw fastest configuration:")
    print(
        f"  Block size: {raw['block_size']}"
    )
    print(
        f"  Threads:    {raw['threads']}"
    )
    print(
        f"  Median:     "
        f"{raw['median_seconds']:.9f} s"
    )
    print(
        f"  Speedup:    {raw['speedup']:.3f}x"
    )
    print(
        f"  Efficiency: "
        f"{raw['efficiency']:.3f}"
    )

    print()
    print("Near-tie candidates:")

    for candidate in (
        result["near_tie_candidates"]
    ):
        print(
            f"  block={candidate['block_size']} "
            f"threads={candidate['threads']} | "
            f"{candidate['median_seconds']:.9f} s | "
            f"speedup {candidate['speedup']:.3f}x | "
            f"slowdown "
            f"{candidate['slowdown_vs_fastest'] * 100:.3f}%"
        )

    print()
    print("Recommended configuration:")
    print(
        f"  Block size: "
        f"{recommended['block_size']}"
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
        f"Parallel status: "
        f"{result['parallel_status']}"
    )
    print(
        f"Decision: {result['decision']}"
    )
    print(
        f"Next action: {result['next_action']}"
    )
    print(
        f"Reason: {result['reason']}"
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "results",
        type=Path,
        help="CSV produced by the autotuner.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    if not args.results.exists():
        print(
            f"File not found: {args.results}"
        )
        raise SystemExit(1)

    try:
        data = load_results(
            args.results
        )

        result = select_configuration(
            data
        )

    except (
        RuntimeError,
        KeyError,
        ValueError,
    ) as error:

        print(
            f"SELECTOR_ERROR: {error}"
        )
        raise SystemExit(1)

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            result,
            indent=2,
        )
    )

    print_result(result)

    print()
    print(
        f"JSON saved to: "
        f"{args.output.resolve()}"
    )
    print(
        "================================="
    )


if __name__ == "__main__":
    main()
