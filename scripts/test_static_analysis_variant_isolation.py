#!/usr/bin/env python3

import json
from pathlib import Path

ROOT = Path(
    __file__
).resolve().parents[1]

MANUAL = (
    ROOT
    / "analysis/output/"
      "nussinov_manual_openmp_analysis.json"
)

AUTO = (
    ROOT
    / "analysis/output/"
      "nussinov_accumulator_auto_analysis.json"
)


def load(path):
    if not path.exists():
        raise RuntimeError(
            f"Missing analysis file: {path}"
        )

    return json.loads(
        path.read_text()
    )


def main():

    manual = load(
        MANUAL
    )

    auto = load(
        AUTO
    )

    print(
        "================================="
    )

    print(
        "Static Analysis Variant Isolation"
    )

    print(
        "Regression Test"
    )

    print(
        "================================="
    )

    manual_source = Path(
        manual["source"]
    ).resolve()

    auto_source = Path(
        auto["source"]
    ).resolve()

    expected_manual = (
        ROOT
        / "kernels/nussinov/"
          "manual_openmp.c"
    ).resolve()

    expected_auto = (
        ROOT
        / "analysis/output/generated/"
          "nussinov_accumulator_auto.c"
    ).resolve()

    manual_ok = (
        manual_source
        == expected_manual
    )

    auto_ok = (
        auto_source
        == expected_auto
    )

    distinct_ok = (
        MANUAL.resolve()
        != AUTO.resolve()
    )

    print()
    print(
        "MANUAL_SOURCE:",
        "PASS" if manual_ok else "FAIL"
    )

    print(
        " ",
        manual_source
    )

    print()
    print(
        "AUTO_SOURCE:",
        "PASS" if auto_ok else "FAIL"
    )

    print(
        " ",
        auto_source
    )

    print()
    print(
        "DISTINCT_OUTPUTS:",
        "PASS" if distinct_ok else "FAIL"
    )

    print(
        " ",
        MANUAL.name
    )

    print(
        " ",
        AUTO.name
    )

    passed = (
        manual_ok
        and auto_ok
        and distinct_ok
    )

    print()
    print(
        "================================="
    )

    print(
        "Variant isolation:",
        "PASS" if passed else "FAIL"
    )

    print(
        "================================="
    )

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
