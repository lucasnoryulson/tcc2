"""Portable compiler discovery for tests that execute real OpenMP code."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def find_openmp_compiler():
    candidates = [
        os.environ.get("TCC2_OPENMP_COMPILER"),
        "/opt/homebrew/opt/llvm/bin/clang",
        shutil.which("gcc"),
        shutil.which("clang"),
    ]
    source = "#include <omp.h>\nint main(void) { return omp_get_max_threads() < 1; }\n"
    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        resolved = str(Path(candidate).resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        try:
            with tempfile.TemporaryDirectory() as directory:
                result = subprocess.run(
                    [resolved, "-fopenmp", "-x", "c", "-", "-o", str(Path(directory) / "probe")],
                    input=source,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            return resolved
    return None
