import importlib.util
from pathlib import Path


module_path = Path(
    "analysis/autotuning_selector.py"
)

spec = importlib.util.spec_from_file_location(
    "autotuning_selector",
    module_path,
)

selector = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    selector
)


def config(
    block,
    threads,
    median,
    speedup,
    efficiency,
    error=0.0,
):
    return {
        "block_size": block,
        "threads": threads,
        "mean_seconds": median,
        "median_seconds": median,
        "std_dev_seconds": 0.0,
        "min_seconds": median,
        "max_seconds": median,
        "speedup": speedup,
        "efficiency": efficiency,
        "max_absolute_error": error,
    }


def data(results):
    return {
        "timestamp": "synthetic",
        "n": 4000,
        "sequential_median_seconds": 0.010,
        "results": results,
    }


# ============================================================
# 1. PARALLEL_SUCCESS
# ============================================================

result = selector.select_configuration(
    data([
        config(64, 1, 0.0090, 1.111, 1.111),
        config(64, 2, 0.0060, 1.667, 0.833),
        config(64, 4, 0.0040, 2.500, 0.625),
    ])
)

assert result["status"] == "SELECTED"
assert result["parallel_status"] == "PARALLEL_SUCCESS"
assert result["parallel_benefit"] is True
assert result["decision"] == "FASTEST_CONFIGURATION"
assert result["recommended"]["threads"] == 4


# ============================================================
# 2. PARALLEL_SCALING_FAILURE
# ============================================================

result = selector.select_configuration(
    data([
        config(64, 1, 0.0080, 1.250, 1.250),
        config(64, 2, 0.0120, 0.833, 0.417),
        config(64, 4, 0.0140, 0.714, 0.179),
    ])
)

assert result["status"] == "SELECTED"
assert (
    result["parallel_status"]
    == "PARALLEL_SCALING_FAILURE"
)
assert result["transformation_benefit"] is True
assert result["parallel_benefit"] is False
assert result["decision"] == "TRANSFORMATION_ONLY"
assert result["recommended"]["threads"] == 1
assert (
    result["next_action"]
    == "MODIFY_PARALLEL_STRATEGY"
)


# ============================================================
# 3. RESOURCE_AWARE_NEAR_TIE
# ============================================================

result = selector.select_configuration(
    data([
        config(64, 4, 0.00500, 2.000, 0.500),
        config(128, 2, 0.00509, 1.965, 0.982),
        config(256, 1, 0.00800, 1.250, 1.250),
    ])
)

assert result["status"] == "SELECTED"
assert result["parallel_status"] == "PARALLEL_SUCCESS"

assert (
    result["raw_fastest"]["threads"]
    == 4
)

assert (
    result["decision"]
    == "RESOURCE_AWARE_NEAR_TIE"
)

assert result["recommended"]["threads"] == 2
assert result["recommended"]["block_size"] == 128

assert (
    len(result["near_tie_candidates"])
    == 2
)


# ============================================================
# 4. NO_CORRECT_CONFIGURATION
# ============================================================

result = selector.select_configuration(
    data([
        config(
            64,
            2,
            0.005,
            2.0,
            1.0,
            error=1e-5,
        ),
        config(
            64,
            4,
            0.004,
            2.5,
            0.625,
            error=1e-4,
        ),
    ])
)

assert (
    result["status"]
    == "NO_CORRECT_CONFIGURATION"
)

assert result["recommended"] is None


print(
    "================================="
)

print(
    "Autotuning Selector v0.1 "
    "regression: PASS"
)

print(
    "4/4 cases behaved as expected."
)

print(
    "================================="
)
