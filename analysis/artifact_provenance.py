"""Local evidence linking gate inputs, executables and measured configurations."""

import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import uuid


COMPILE_FLAGS = {"sequential": ["-O3"], "candidate": ["-O3", "-fopenmp"]}
OPENMP_ENVIRONMENT = {
    "OMP_DYNAMIC": "FALSE", "OMP_PROC_BIND": "TRUE", "OMP_PLACES": "cores",
}
REL_TOL = 1e-9
ABS_TOL = 1e-12


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def file_record(path):
    path = path.resolve(strict=True)
    return {"path": str(path), "sha256": sha256(path.read_bytes())}


def verify_file(record):
    if not isinstance(record, dict) or not isinstance(record.get("path"), str):
        raise ValueError("Missing artifact identity.")
    path = Path(record["path"])
    if not path.is_absolute() or not path.is_file():
        raise ValueError(f"Missing artifact: {path}")
    data = path.read_bytes()
    if sha256(data) != record.get("sha256"):
        raise ValueError(f"SHA-256 mismatch: {path}")
    return data


def read_report(path):
    data = path.read_bytes()
    report = json.loads(data)
    if not isinstance(report, dict):
        raise ValueError("Gate report must be a JSON object.")
    return report, {"path": str(path.resolve()), "sha256": sha256(data)}


def capture_run(inputs, build_dir, compiler, campaign_id=None):
    compiler_path = shutil.which(compiler)
    if compiler_path is None:
        raise ValueError(f"Compiler not found: {compiler}")
    toolchain = file_record(Path(compiler_path))
    version = subprocess.run(
        [toolchain["path"], "--version"], capture_output=True, text=True, check=True,
    )
    toolchain["version"] = version.stdout.strip()
    run_id = uuid.uuid4().hex
    run_dir = build_dir.resolve() / run_id
    run_dir.mkdir(parents=True)
    artifacts = {}
    for name, path in inputs.items():
        path = path.resolve(strict=True)
        data = path.read_bytes()
        # shortcut: project headers are not captured; extend dependency capture before supporting them.
        snapshot = run_dir / name / path.name
        snapshot.parent.mkdir()
        snapshot.write_bytes(data)
        artifacts[name] = {
            "path": str(path), "sha256": sha256(data),
            "snapshot": str(snapshot),
        }
    return {
        "campaign_id": campaign_id or uuid.uuid4().hex,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "candidate_id": "sha256:" + artifacts["candidate"]["sha256"],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "runtime_environment": {
            key: value for key, value in os.environ.items()
            if key.startswith(("OMP_", "GOMP_", "KMP_"))
        },
        "inputs": artifacts,
        "toolchain": toolchain,
        "compile_flags": {name: flags[:] for name, flags in COMPILE_FLAGS.items()},
        "link_flags": ["-lm"],
        "openmp_environment": dict(OPENMP_ENVIRONMENT),
    }


def verify_provenance(provenance, expected_inputs=None):
    if not isinstance(provenance, dict):
        raise ValueError("Missing gate provenance; regenerate the gate report.")
    campaign = provenance.get("campaign_id")
    if not isinstance(campaign, str) or not campaign:
        raise ValueError("Missing campaign identity.")
    inputs = provenance.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != {"sequential", "candidate", "driver"}:
        raise ValueError("Incomplete input provenance.")
    for name, record in inputs.items():
        verify_file(record)
        if not isinstance(record.get("snapshot"), str):
            raise ValueError(f"Missing {name} snapshot.")
        verify_file({"path": record["snapshot"], "sha256": record["sha256"]})
        if expected_inputs and name in expected_inputs:
            if Path(record["path"]).resolve() != expected_inputs[name].resolve():
                raise ValueError(f"Gate report refers to another {name} file.")
    if provenance.get("candidate_id") != "sha256:" + inputs["candidate"]["sha256"]:
        raise ValueError("Candidate identity disagrees with its hash.")
    verify_file(provenance.get("toolchain"))
    if (
        provenance.get("compile_flags") != COMPILE_FLAGS
        or provenance.get("link_flags") != ["-lm"]
        or provenance.get("openmp_environment") != OPENMP_ENVIRONMENT
    ):
        raise ValueError("Unsupported or inconsistent gate configuration.")


def load_correctness_report(path, source_file, candidate_file):
    report, reference = read_report(path)
    if (
        report.get("schema") != "tcc2-correctness-gate"
        or report.get("version") != "0.2"
        or report.get("status") not in ("PASS", "FAIL")
    ):
        raise ValueError("Invalid or legacy correctness report; regenerate it.")
    verify_provenance(report.get("provenance"), {
        "sequential": source_file, "candidate": candidate_file,
    })
    if report["status"] == "PASS":
        if report.get("tolerances") != {"relative": REL_TOL, "absolute": ABS_TOL}:
            raise ValueError("Unsupported correctness tolerances.")
        compilations = report.get("compilation")
        binaries = report.get("binaries")
        if not isinstance(compilations, dict) or not isinstance(binaries, dict):
            raise ValueError("Correctness PASS lacks compilation or executable evidence.")
        for name in ("sequential", "candidate"):
            result = compilations.get(name)
            if not isinstance(result, dict) or result.get("returncode") != 0:
                raise ValueError(f"Correctness PASS has no successful compilation: {name}.")
            verify_file(binaries.get(name))
        executions = report.get("execution")
        sequential = executions.get("sequential") if isinstance(executions, dict) else None
        if not isinstance(sequential, dict) or sequential.get("returncode") != 0:
            raise ValueError("Correctness PASS has no successful sequential execution.")
        runs = report.get("thread_results")
        if not isinstance(runs, list) or not runs:
            raise ValueError("Correctness PASS has no thread validation results.")
        threads = []
        for run in runs:
            if not isinstance(run, dict) or not isinstance(run.get("validation"), dict):
                raise ValueError("Incomplete correctness thread result.")
            count = run.get("threads")
            validation = run["validation"]
            if type(count) is not int or count < 1:
                raise ValueError("Invalid validated thread count.")
            execution = run.get("execution")
            if not isinstance(execution, dict) or execution.get("returncode") != 0:
                raise ValueError("Correctness PASS contains a failed execution.")
            values = [validation.get("reference"), validation.get("candidate")]
            if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
                raise ValueError("Missing finite numeric validation.")
            outputs = [sequential.get("stdout"), execution.get("stdout")]
            if any(not isinstance(output, str) or not output.strip() for output in outputs):
                raise ValueError("Missing numeric execution output.")
            if [float(output.strip().splitlines()[0]) for output in outputs] != values:
                raise ValueError("Numeric validation disagrees with execution output.")
            if validation.get("correct") is not True or not math.isclose(
                *values, rel_tol=REL_TOL, abs_tol=ABS_TOL,
            ):
                raise ValueError("Correctness PASS contradicts numeric validation.")
            threads.append(count)
        if report.get("validated_threads") != threads or len(set(threads)) != len(threads):
            raise ValueError("Validated threads disagree with execution results.")
        if report.get("validation") != runs[-1]["validation"]:
            raise ValueError("Correctness summary disagrees with thread validation.")
        if executions.get("candidate") != runs[-1]["execution"]:
            raise ValueError("Candidate execution summary disagrees with thread results.")
        requested = report.get("threads")
        if ([requested] if type(requested) is int else requested) != threads:
            raise ValueError("Requested and validated thread counts disagree.")
    if report.get("inputs") != {
        name: item["path"] for name, item in report["provenance"]["inputs"].items()
    }:
        raise ValueError("Correctness input paths disagree with provenance.")
    return report, reference


def measured_rows(measurements):
    if not isinstance(measurements, list) or len(measurements) < 2:
        raise ValueError("Missing raw benchmark measurements.")
    rows = []
    seen = set()
    for measurement in measurements:
        if not isinstance(measurement, dict):
            raise ValueError("Invalid benchmark measurement.")
        mode, threads = measurement.get("mode"), measurement.get("threads")
        if mode not in ("sequential", "openmp") or type(threads) is not int or threads < 1:
            raise ValueError("Invalid measured configuration.")
        if (mode, threads) in seen or (mode == "sequential" and (rows or threads != 1)):
            raise ValueError("Duplicate configuration or invalid sequential baseline.")
        seen.add((mode, threads))
        times = measurement.get("times")
        if not isinstance(times, list) or not times or any(
            type(value) not in (int, float) or not math.isfinite(value) or value <= 0
            for value in times
        ):
            raise ValueError("Invalid raw benchmark times.")
        median = statistics.median(times)
        if not rows and mode != "sequential":
            raise ValueError("Missing sequential baseline.")
        speedup = rows[0]["median_seconds"] / median if rows else 1.0
        if not math.isfinite(speedup):
            raise ValueError("Non-finite benchmark speedup.")
        rows.append({
            "mode": mode, "threads": threads, "median_seconds": median,
            "mean_seconds": statistics.mean(times), "speedup": speedup,
            "efficiency": speedup / threads,
        })
    return rows


def load_performance_report(path, csv_path=None):
    report, reference = read_report(path)
    if (
        report.get("schema") != "tcc2-performance-gate"
        or report.get("version") != "0.1"
        or report.get("status") not in ("PASS", "FAIL")
    ):
        raise ValueError("Invalid performance report.")
    provenance = report.get("provenance")
    verify_provenance(provenance)
    correctness_ref = report.get("correctness_report")
    verify_file(correctness_ref)
    inputs = provenance["inputs"]
    correctness, _ = load_correctness_report(
        Path(correctness_ref["path"]), Path(inputs["sequential"]["path"]),
        Path(inputs["candidate"]["path"]),
    )
    if correctness["status"] != "PASS":
        raise ValueError("Benchmark has no passing correctness report.")
    other = correctness["provenance"]
    if provenance["campaign_id"] != other["campaign_id"]:
        raise ValueError("Correctness and performance campaigns disagree.")
    if provenance["toolchain"] != other["toolchain"]:
        raise ValueError("Correctness and performance toolchains disagree.")
    for name in ("sequential", "candidate"):
        if inputs[name]["sha256"] != other["inputs"][name]["sha256"]:
            raise ValueError("Correctness and performance input hashes disagree.")
    binaries = report.get("binaries")
    compilations = report.get("compilation")
    if not isinstance(binaries, dict) or set(binaries) != {"sequential", "candidate"}:
        raise ValueError("Missing benchmark executable identities.")
    for name, binary in binaries.items():
        verify_file(binary)
        compiled = compilations.get(name) if isinstance(compilations, dict) else None
        if not isinstance(compiled, dict) or compiled.get("returncode") != 0:
            raise ValueError("Benchmark contains unsuccessful compilation.")
    if report.get("configuration_dimensions") != ["threads"]:
        raise ValueError("Unsupported benchmark configuration dimensions.")
    rows = measured_rows(report.get("measurements"))
    thread_counts = [row["threads"] for row in rows if row["mode"] == "openmp"]
    if not set(thread_counts).issubset(correctness["validated_threads"]):
        raise ValueError("Benchmark includes threads without correctness validation.")
    if report.get("thread_counts") != thread_counts:
        raise ValueError("Benchmark thread counts disagree with measurements.")
    if type(report.get("repetitions")) is not int or report["repetitions"] < 1:
        raise ValueError("Invalid benchmark repetition count.")
    if any(len(item["times"]) != report.get("repetitions") for item in report["measurements"]):
        raise ValueError("Benchmark repetition counts disagree.")
    expected_status = "PASS" if any(row["speedup"] > 1 for row in rows[1:]) else "FAIL"
    if report["status"] != expected_status:
        raise ValueError("Performance status contradicts measured times.")
    csv_data = verify_file(report.get("csv"))
    if csv_path is not None and sha256(csv_path.read_bytes()) != report["csv"]["sha256"]:
        raise ValueError("CSV does not belong to this benchmark report.")
    csv_rows = list(csv.DictReader(io.StringIO(csv_data.decode())))
    if len(csv_rows) != len(rows) or any(
        csv_row.get(key) != str(value)
        for csv_row, row in zip(csv_rows, rows) for key, value in row.items()
    ):
        raise ValueError("CSV disagrees with raw benchmark measurements.")
    return report, rows, reference


def load_selection_evidence(selection_file, correctness_file, source_file, candidate_file):
    from analysis.performance_selector import select_configuration

    correctness, correctness_ref = load_correctness_report(correctness_file, source_file, candidate_file)
    selection, selection_ref = read_report(selection_file)
    evidence = selection.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError("Selection has no benchmark provenance; regenerate it with --performance-report.")
    performance_ref = evidence.get("performance_report")
    verify_file(performance_ref)
    performance, measured, _ = load_performance_report(Path(performance_ref["path"]))
    provenance = performance["provenance"]
    if (
        evidence.get("campaign_id") != provenance["campaign_id"]
        or evidence.get("candidate_id") != provenance["candidate_id"]
        or correctness_ref["sha256"] != performance["correctness_report"]["sha256"]
    ):
        raise ValueError("Selection, correctness and performance evidence disagree.")
    if {key: value for key, value in selection.items() if key != "evidence"} != select_configuration(measured):
        raise ValueError("Selection disagrees with the deterministic benchmark result.")
    references = {"correctness": correctness_ref, "performance": performance_ref, "selection": selection_ref}
    for reference in references.values():
        verify_file(reference)
    return {
        "correctness": correctness, "performance": performance,
        "selection": selection, "measurements": measured, "references": references,
    }


def load_context_evidence(context_file):
    """Verify the canonical context and its bound gate/selection artifacts."""
    context, reference = read_report(context_file)
    if not isinstance(context, dict) or (
        context.get("schema"), context.get("version")
    ) != ("tcc2-agent-context", "0.3"):
        raise ValueError("A provenance-bound context v0.3 is required.")
    source = context.get("source")
    validation = context.get("validation")
    performance_context = context.get("performance")
    if not all(isinstance(item, dict) for item in (source, validation, performance_context)):
        raise ValueError("Incomplete input context.")
    selection_ref = performance_context.get("selection_file")
    verify_file(selection_ref)
    for field in ("sequential_file", "candidate_file"):
        if not isinstance(source.get(field), str) or not Path(source[field]).is_absolute():
            raise ValueError(f"Context requires an absolute {field} path.")
    correctness_file = validation.get("correctness_report_file")
    if not isinstance(correctness_file, str):
        raise ValueError("Context has no correctness report.")
    bundle = load_selection_evidence(
        Path(selection_ref["path"]), Path(correctness_file),
        Path(source["sequential_file"]), Path(source["candidate_file"]),
    )
    correctness, performance = bundle["correctness"], bundle["performance"]
    selection, references = bundle["selection"], bundle["references"]
    provenance = performance["provenance"]
    if (
        performance_context.get("selection") != selection
        or performance_context.get("report") != references["performance"]
        or validation.get("correctness_report_sha256") != references["correctness"]["sha256"]
        or validation.get("correctness_report") != correctness
        or validation.get("correctness_gate") != "PASS"
    ):
        raise ValueError("Context disagrees with verified gate/selection evidence.")
    for field in ("candidate_id", "campaign_id"):
        if source.get(field) != provenance[field]:
            raise ValueError(f"Context refers to another {field}.")
    inputs = correctness["provenance"]["inputs"]
    captured = {}
    for name, item in inputs.items():
        captured[name] = verify_file({"path": item["snapshot"], "sha256": item["sha256"]})
    for name in ("sequential", "candidate"):
        if source.get(name + "_sha256") != inputs[name]["sha256"] or source.get(name + "_code") != captured[name].decode():
            raise ValueError("Context code differs from the validated candidate or original.")
    verify_file(reference)
    return context, bundle, reference


def parallel_selection(bundle):
    """Shared admission policy; the caller must first verify the evidence bundle."""
    selection, performance = bundle["selection"], bundle["performance"]
    if (
        selection.get("status") != "SELECTED"
        or selection.get("parallel_status") != "PARALLEL_SUCCESS"
        or selection.get("next_action") != "PROMOTE_CANDIDATE"
        or performance["status"] != "PASS"
    ):
        raise ValueError("Selection does not establish a successful parallel candidate.")
    recommended = selection.get("recommended")
    if not isinstance(recommended, dict) or recommended.get("mode") != "openmp":
        raise ValueError("Selection has no measured OpenMP recommendation.")
    threads = recommended.get("threads")
    if type(threads) is not int or threads < 2:
        raise ValueError("Parallel promotion requires at least two measured threads.")
    rows = bundle["measurements"]
    selected = next(row for row in rows if row["mode"] == "openmp" and row["threads"] == threads)
    one_thread = next((row for row in rows if row["mode"] == "openmp" and row["threads"] == 1), None)
    if one_thread is None or selected["median_seconds"] >= min(rows[0]["median_seconds"], one_thread["median_seconds"]):
        raise ValueError("Selected configuration must improve both sequential and one-thread baselines.")

    return {"threads": threads}, selected, one_thread
