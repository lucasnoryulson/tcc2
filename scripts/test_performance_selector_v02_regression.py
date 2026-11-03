#!/usr/bin/env python3

import importlib.util
import math
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MODULE_PATH = (
    ROOT
    / "analysis"
    / "performance_selector.py"
)

spec = importlib.util.spec_from_file_location(
    "performance_selector",
    MODULE_PATH,
)

module = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    module
)


def close(
    actual,
    expected,
    tolerance=1e-9,
):
    assert math.isclose(
        actual,
        expected,
        rel_tol=tolerance,
        abs_tol=tolerance,
    ), (
        f"expected {expected}, "
        f"got {actual}"
    )


def make_result(
    mode,
    threads,
    median,
    speedup,
):
    return {
        "mode": mode,
        "threads": threads,
        "median_seconds": median,
        "mean_seconds": median,
        "speedup": speedup,
        "efficiency": (
            speedup / threads
        ),
    }


def test_current_csv_schema():

    csv_text = """timestamp,benchmark,validation_mode,version,threads,mean_seconds,median_seconds,std_dev,min_seconds,max_seconds,scaling_speedup,speedup_vs_sequential,efficiency_vs_sequential
x,test,exact,sequential,1,1.0,1.0,0,1,1,1.0,1.0,1.0
x,test,exact,openmp,1,0.8,0.8,0,0.8,0.8,1.0,1.25,1.25
x,test,exact,openmp,4,0.3,0.3,0,0.3,0.3,2.6666666667,3.3333333333,0.8333333333
"""

    with tempfile.TemporaryDirectory() as tmp:

        path = (
            Path(tmp)
            / "results.csv"
        )

        path.write_text(
            csv_text
        )

        rows = module.load_results(
            path
        )

    assert len(rows) == 3

    assert (
        rows[0]["mode"]
        == "sequential"
    )

    assert (
        rows[1]["mode"]
        == "openmp"
    )

    close(
        rows[2]["speedup"],
        3.3333333333,
    )


def test_parallel_success_metrics():

    results = [
        make_result(
            "sequential",
            1,
            1.0,
            1.0,
        ),
        make_result(
            "openmp",
            1,
            0.8,
            1.25,
        ),
        make_result(
            "openmp",
            2,
            0.5,
            2.0,
        ),
        make_result(
            "openmp",
            4,
            0.3,
            3.3333333333333335,
        ),
    ]

    result = (
        module.select_configuration(
            results
        )
    )

    assert (
        result["status"]
        == "SELECTED"
    )

    assert (
        result["parallel_status"]
        == "PARALLEL_SUCCESS"
    )

    assert (
        result["parallel_benefit"]
        is True
    )

    assert (
        result["recommended"]["threads"]
        == 4
    )

    close(
        result[
            "transformation_speedup"
        ],
        1.25,
    )

    close(
        result[
            "parallel_scaling_speedup"
        ],
        0.8 / 0.3,
    )

    close(
        result[
            "parallel_scaling_efficiency"
        ],
        (0.8 / 0.3) / 4,
    )

    close(
        result[
            "end_to_end_speedup"
        ],
        1.0 / 0.3,
    )

    close(
        result[
            "runtime_reduction"
        ],
        0.7,
    )


def test_transformation_only_not_parallel_success():

    results = [
        make_result(
            "sequential",
            1,
            1.0,
            1.0,
        ),
        make_result(
            "openmp",
            1,
            0.8,
            1.25,
        ),

        # Both multi-thread configurations are
        # faster than the original sequential
        # implementation, but slower than the
        # transformed one-thread implementation.
        make_result(
            "openmp",
            2,
            0.9,
            1.1111111111111112,
        ),
        make_result(
            "openmp",
            4,
            0.85,
            1.1764705882352942,
        ),
    ]

    result = (
        module.select_configuration(
            results
        )
    )

    assert (
        result["transformation_benefit"]
        is True
    )

    assert (
        result["parallel_benefit"]
        is False
    )

    assert (
        result["parallel_status"]
        == "PARALLEL_SCALING_FAILURE"
    )

    assert (
        result["decision"]
        == "TRANSFORMATION_ONLY"
    )

    assert (
        result["next_action"]
        == "MODIFY_PARALLEL_STRATEGY"
    )

    assert (
        result["recommended"]["threads"]
        == 1
    )


def main():

    test_current_csv_schema()

    print(
        "PASS: current CSV schema"
    )

    test_parallel_success_metrics()

    print(
        "PASS: separated performance metrics"
    )

    test_transformation_only_not_parallel_success()

    print(
        "PASS: transformation-only classification"
    )

    print()
    print(
        "Performance Selector v0.2 "
        "regression: PASS"
    )


if __name__ == "__main__":
    main()
