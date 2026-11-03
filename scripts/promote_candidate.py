"""Publish a measured candidate only after Coordinator approval and revalidation."""

import argparse
import contextlib
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agents.coordinator_agent import validate_decision
from analysis.artifact_provenance import (
    file_record, load_context_evidence, parallel_selection, read_report, sha256, verify_file, verify_provenance,
)
from scripts.compile_correctness_gate import run_gate


def promotion_identifier(campaign_id, candidate_id):
    return sha256(json.dumps([campaign_id, candidate_id]).encode())


def rebase_paths(value, staging, published):
    if isinstance(value, dict):
        return {key: rebase_paths(item, staging, published) for key, item in value.items()}
    if isinstance(value, list):
        return [rebase_paths(item, staging, published) for item in value]
    prefix = str(staging) + os.sep
    if isinstance(value, str) and value.startswith(prefix):
        return str(published) + os.sep + value[len(prefix):]
    return value


def promote_candidate(decision_file, output_dir):
    decision, decision_ref = read_report(decision_file)
    if decision.get("schema") != "tcc2-coordinator-decision" or decision.get("version") != "0.2":
        raise ValueError("A Coordinator v0.2 decision is required.")
    body = decision.get("decision")
    if not isinstance(body, dict) or (
        body.get("decision"), body.get("next_action")
    ) != ("ACCEPT", "PROMOTE_CANDIDATE"):
        raise ValueError("Only ACCEPT with PROMOTE_CANDIDATE can publish a candidate.")
    evidence = decision.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError("Decision has no bound input evidence.")
    context_ref = evidence.get("context")
    verify_file(context_ref)
    context, bundle, verified_context_ref = load_context_evidence(Path(context_ref["path"]))
    if verified_context_ref != context_ref:
        raise ValueError("Context changed while loading evidence.")
    correctness, performance = bundle["correctness"], bundle["performance"]
    references = bundle["references"]
    provenance = performance["provenance"]
    for field in ("candidate_id", "campaign_id"):
        if evidence.get(field) != provenance[field]:
            raise ValueError(f"Decision refers to another {field}.")
    inputs = correctness["provenance"]["inputs"]
    captured = {
        name: verify_file({"path": item["snapshot"], "sha256": item["sha256"]})
        for name, item in inputs.items()
    }
    configuration, selected, one_thread = parallel_selection(bundle)
    threads = configuration["threads"]
    if (
        type(body.get("recommended_threads")) is not int
        or body["recommended_threads"] != threads
        or body.get("recommended_configuration") != configuration
    ):
        raise ValueError("Coordinator configuration differs from the measured selection.")
    errors = validate_decision(body, context)
    if errors:
        raise ValueError("Invalid Coordinator decision: " + "; ".join(errors))
    rows = bundle["measurements"]

    root = output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    identifier = promotion_identifier(provenance["campaign_id"], provenance["candidate_id"])
    published = root / identifier
    lock = root / ("." + identifier + ".lock")
    # shortcut: a killed process may leave this lock; inspect the run before removing it.
    with lock.open("x"):
        pass
    staging = None
    try:
        if published.exists() or published.is_symlink():
            raise FileExistsError(f"Promotion already exists: {published}")
        staging = Path(tempfile.mkdtemp(prefix="." + identifier + ".", dir=root))
        archive = staging / "evidence"
        archive.mkdir()
        (staging / "parallel.c").write_bytes(captured["candidate"])
        (archive / "sequential.c").write_bytes(captured["sequential"])
        (archive / "correctness_driver.c").write_bytes(captured["driver"])
        benchmark_driver = provenance["inputs"]["driver"]
        (archive / "benchmark_driver.c").write_bytes(verify_file({
            "path": benchmark_driver["snapshot"], "sha256": benchmark_driver["sha256"],
        }))
        origins = {"decision": decision_ref, "context": context_ref, **references}
        for name, reference in origins.items():
            (archive / (name + ".json")).write_bytes(verify_file(reference))
        (archive / "performance.csv").write_bytes(verify_file(performance["csv"]))
        for kind, report in (("correctness", correctness), ("performance", performance)):
            for name, binary in report["binaries"].items():
                (archive / (kind + "_" + name + ".bin")).write_bytes(verify_file(binary))

        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            revalidation = run_gate(
                archive / "sequential.c", staging / "parallel.c", archive / "correctness_driver.c",
                staging / "revalidation", provenance["toolchain"]["path"], [threads],
            )
        if revalidation["status"] != "PASS":
            raise ValueError("Fresh correctness revalidation failed: " + revalidation.get("reason", "gate FAIL"))
        if revalidation["provenance"]["candidate_id"] != provenance["candidate_id"]:
            raise ValueError("Revalidated bytes differ from the measured candidate.")
        if revalidation["provenance"]["toolchain"] != provenance["toolchain"]:
            raise ValueError("Revalidation toolchain differs from the measured toolchain.")
        (staging / "revalidation.log").write_text(log.getvalue())
        (staging / "revalidation.json").write_text(json.dumps(
            rebase_paths(revalidation, staging, published), indent=2,
        ) + "\n")
        if sha256((staging / "parallel.c").read_bytes()) != inputs["candidate"]["sha256"]:
            raise ValueError("Published candidate changed during staging.")
        for reference in origins.values():
            verify_file(reference)
        verify_provenance(correctness["provenance"])
        verify_provenance(provenance)
        for report in (correctness, performance):
            for binary in report["binaries"].values():
                verify_file(binary)
        files = {
            path.relative_to(staging).as_posix(): {"sha256": file_record(path)["sha256"]}
            for path in sorted(staging.rglob("*")) if path.is_file()
        }
        manifest = {
            "schema": "tcc2-promoted-candidate", "version": "0.1", "status": "PROMOTED",
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "promotion_id": identifier, "candidate_id": provenance["candidate_id"],
            "campaign_id": provenance["campaign_id"], "configuration": configuration,
            "coordinator_model": decision.get("model"),
            "candidate_sha256": inputs["candidate"]["sha256"], "origins": origins,
            "toolchain": provenance["toolchain"], "compile_flags": provenance["compile_flags"],
            "link_flags": provenance["link_flags"], "openmp_environment": provenance["openmp_environment"],
            "measured_configuration": selected,
            "metrics": {
                "end_to_end_speedup": rows[0]["median_seconds"] / selected["median_seconds"],
                "transformation_speedup": rows[0]["median_seconds"] / one_thread["median_seconds"],
                "parallel_scaling_speedup": one_thread["median_seconds"] / selected["median_seconds"],
                "parallel_scaling_efficiency": one_thread["median_seconds"] / selected["median_seconds"] / threads,
            },
            "revalidation": {"status": "PASS", "report": "revalidation.json", "threads": threads},
            "reproduce_correctness": [
                sys.executable, str(Path(__file__).with_name("compile_correctness_gate.py").resolve()),
                "--sequential", str(published / "evidence/sequential.c"),
                "--candidate", str(published / "parallel.c"),
                "--driver", str(published / "evidence/correctness_driver.c"),
                "--compiler", provenance["toolchain"]["path"], "--threads", str(threads),
                "--build-dir", str(root.parent / "promotion_checks" / identifier),
            ],
            "files": files,
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        if published.exists() or published.is_symlink():
            raise FileExistsError(f"Promotion already exists: {published}")
        staging.rename(published)
        return published
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging)
        lock.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("decision", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("results/promoted"))
    args = parser.parse_args()
    try:
        result = promote_candidate(args.decision.resolve(), args.output_dir)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"PROMOTION_BLOCKED: {error}")
        return 1
    print(f"PROMOTED: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
