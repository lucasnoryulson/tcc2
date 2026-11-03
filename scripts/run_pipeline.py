"""Run the supported standalone C/OpenMP pipeline through final promotion."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.artifact_provenance import file_record, load_performance_report, read_report
from scripts.promote_candidate import promote_candidate


def run_pipeline(args):
    started = time.perf_counter()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="run-", dir=args.work_dir.resolve()))
    summary = {"schema": "tcc2-pipeline-run", "version": "0.1", "status": "RUNNING", "steps": []}
    summary_file = work / "summary.json"

    def save():
        summary["elapsed_seconds"] = time.perf_counter() - started
        summary_file.write_text(json.dumps(summary, indent=2) + "\n")

    def step(name, arguments, allow_no_gain=False):
        command = [sys.executable, "-B", *map(str, arguments)]
        print(f"{name}: running", flush=True)
        log = work / (name + ".log")
        step_started = time.perf_counter()
        try:
            result = subprocess.run(
                command, cwd=ROOT, capture_output=True, text=True,
                env={**os.environ, "TCC2_THREAD_COUNTS": ",".join(map(str, args.threads))},
                timeout=max(300, args.timeout + 15),
            )
        except subprocess.TimeoutExpired as error:
            log.write_text(str(error))
            summary["steps"].append({"name": name, "command": command, "returncode": None,
                                     "error": str(error), "log": str(log),
                                     "wall_seconds": time.perf_counter() - step_started})
            save()
            raise
        log.write_text(result.stdout + result.stderr)
        summary["steps"].append({"name": name, "command": command, "returncode": result.returncode,
                                 "log": str(log), "wall_seconds": time.perf_counter() - step_started})
        save()
        if result.returncode != 0:
            if allow_no_gain and result.returncode == 1:
                report, _, _ = load_performance_report(work / "performance.json", work / "performance.csv")
                if report["status"] == "FAIL":
                    return
            raise RuntimeError(f"{name} failed; see {log}")

    source = args.source.resolve()
    candidate = work / "candidate.c"
    analysis = work / "analysis"
    save()
    try:
        step("static", [ROOT / "analysis/static_analyzer.py", source, "--output-dir", analysis])
        files = list(analysis.glob("*_analysis.json"))
        if len(files) != 1:
            raise ValueError("Expected exactly one static analysis output.")
        static = files[0]
        stem = static.stem.removesuffix("_analysis")
        dependences = analysis / (stem + "_dependences.json")
        patterns = analysis / (stem + "_patterns.json")
        strategy = analysis / (stem + "_strategy.json")
        step("dependences", [ROOT / "analysis/dependence_analyzer.py", static])
        step("patterns", [ROOT / "analysis/pattern_classifier.py", static, dependences])
        step("strategy", [ROOT / "analysis/strategy_planner.py", static, patterns])
        step("transform", [ROOT / "analysis/code_transformer.py", source, static, strategy, "--output", candidate])
        step("correctness", [
            ROOT / "scripts/compile_correctness_gate.py", "--sequential", source, "--candidate", candidate,
            "--driver", args.driver.resolve(), "--compiler", args.compiler, "--threads", *args.threads,
            "--build-dir", work / "correctness", "--output", work / "correctness.json",
        ])
        step("performance", [
            ROOT / "scripts/performance_gate.py", "--sequential", source, "--candidate", candidate,
            "--driver", args.benchmark_driver.resolve(), "--compiler", args.compiler,
            "--correctness", work / "correctness.json", "--build-dir", work / "performance",
            "--csv", work / "performance.csv", "--output", work / "performance.json",
        ], allow_no_gain=True)
        step("selection", [
            ROOT / "analysis/performance_selector.py", work / "performance.csv",
            "--performance-report", work / "performance.json", "--output", work / "selection.json",
        ])
        step("context", [
            ROOT / "agents/context_builder.py", "--source", source, "--candidate", candidate,
            "--static", static, "--dependences", dependences, "--patterns", patterns, "--strategy", strategy,
            "--selection", work / "selection.json", "--correctness", work / "correctness.json",
            "--output", work / "context.json",
        ])
        summary["context"] = file_record(work / "context.json")
        if getattr(args, "prepare_only", False):
            summary.update(status="PREPARED")
            save()
            return 0, work
        step("coordinator", [
            ROOT / "agents/coordinator_agent.py", work / "context.json", "--model", args.model,
            "--timeout", args.timeout, "--output", work / "decision.json",
        ])
        decision, _ = read_report(work / "decision.json")
        if (decision["decision"]["decision"], decision["decision"]["next_action"]) != ("ACCEPT", "PROMOTE_CANDIDATE"):
            summary.update(status="NOT_PROMOTED", next_action=decision["decision"]["next_action"])
            save()
            print(f"No promotion: {summary['next_action']}. Evidence: {summary_file}")
            return 1, work
        promotion_started = time.perf_counter()
        promoted = promote_candidate(work / "decision.json", args.output_dir)
        summary["steps"].append({"name": "promotion", "returncode": 0, "directory": str(promoted),
                                 "wall_seconds": time.perf_counter() - promotion_started})
        summary.update(status="PROMOTED", manifest=file_record(promoted / "manifest.json"))
        save()
        print(f"PROMOTED: {promoted}\nRun evidence: {summary_file}")
        return 0, work
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        summary.update(status="FAILED", reason=str(error))
        save()
        print(f"PIPELINE_STOPPED: {error}\nRun evidence: {summary_file}")
        return 1, work


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "analysis/fixtures/dot_product.c")
    parser.add_argument("--driver", type=Path, default=ROOT / "analysis/fixtures/dot_driver.c")
    parser.add_argument("--benchmark-driver", type=Path, default=ROOT / "analysis/fixtures/dot_benchmark_driver.c")
    parser.add_argument("--compiler", default="gcc")
    parser.add_argument("--threads", type=int, nargs="+", default=[1, 2])
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--prepare-only", action="store_true", help="Stop after verified context creation, before calling the LLM.")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--work-dir", type=Path, default=ROOT / "build/pipeline")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/promoted")
    args = parser.parse_args()
    if (
        any(count < 1 for count in args.threads) or len(set(args.threads)) != len(args.threads)
        or 1 not in args.threads or not any(count >= 2 for count in args.threads)
        or args.timeout <= 0
    ):
        parser.error("Use distinct positive threads including 1 and a parallel configuration, and a positive timeout.")
    code, _ = run_pipeline(args)
    return code


if __name__ == "__main__":
    sys.exit(main())
