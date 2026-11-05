#!/usr/bin/env python3

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(
    __file__
).resolve().parents[1]

def load(path):
    if not path.exists():
        raise RuntimeError(
            f"Missing analysis file: {path}"
        )

    return json.loads(
        path.read_text()
    )


def main():
    # Exercise fresh outputs on this checkout; archived absolute paths belong to their original host.
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        includes = ROOT / "benchmarks/PolyBenchC-4.2.1"
        for source in (ROOT / "kernels/nussinov/manual_openmp.c",
                       ROOT / "analysis/output/generated/nussinov_accumulator_auto.c"):
            subprocess.run([sys.executable, "-B", str(ROOT / "analysis/static_analyzer.py"), str(source),
                            "--include", str(includes / "utilities"),
                            "--include", str(includes / "medley/nussinov"),
                            "--output-dir", str(output)], check=True, capture_output=True, text=True, timeout=60)
        manual_file = output / "nussinov_manual_openmp_analysis.json"
        auto_file = output / "nussinov_accumulator_auto_analysis.json"
        manual = load(manual_file)
        auto = load(auto_file)

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
        manual_file.resolve()
        != auto_file.resolve()
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
        manual_file.name
    )

    print(
        " ",
        auto_file.name
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
