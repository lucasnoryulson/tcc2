"""Paired decision study: deterministic policy, Coordinator, and analysis ablation."""

import argparse
import copy
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agents import coordinator_agent as coordinator
from analysis.artifact_provenance import file_record, load_context_evidence, parallel_selection, sha256, verify_file
from scripts.run_pipeline import run_pipeline

MODES = ("deterministic", "coordinator", "coordinator_without_analysis")
ABLATION_FIELDS = ("static_analysis", "dependence_analysis", "pattern", "strategy", "deterministic_evidence")


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def model_context(context, mode):
    view = copy.deepcopy(context)
    if mode == "coordinator_without_analysis":
        for field in ABLATION_FIELDS:
            view[field] = {}
    return view


def run_trial(context, bundle, mode, model, timeout, directory):
    directory.mkdir()
    started = time.perf_counter()
    try:
        configuration, selected, one_thread = parallel_selection(bundle)
        eligible, policy_reason = True, "Measured parallel selection is admissible."
    except ValueError as error:
        eligible, policy_reason = False, str(error)
        configuration = selected = one_thread = None
    trial = {
        "mode": mode, "status": "OK", "eligible": eligible, "policy_reason": policy_reason,
        "candidate_attempts": 1, "llm_calls": int(mode != "deterministic"),
        "recovery_supported": False, "metadata": {}, "raw_decision": None,
        "validation_errors": [], "monetary_cost": None,
    }
    decision = None
    if mode == "deterministic":
        decision = {"decision": "ACCEPT" if eligible else "REJECT",
                    "next_action": "PROMOTE_CANDIDATE" if eligible else "REJECT_CANDIDATE",
                    "recommended_threads": configuration["threads"] if eligible else None,
                    "recommended_configuration": configuration, "risk": "LOW"}
        trial["decision_wall_seconds"] = time.perf_counter() - started
    else:
        view = model_context(context, mode)
        prompts = {"system": coordinator.build_system_prompt(), "user": coordinator.build_user_prompt(view),
                   "format": coordinator.DECISION_SCHEMA, "temperature": 0, "model": model}
        write_json(directory / "prompt.json", prompts)
        trial["prompt_sha256"] = sha256((directory / "prompt.json").read_bytes())
        trial["ablation_effective"] = (
            prompts["user"] != coordinator.build_user_prompt(context)
            if mode == "coordinator_without_analysis" else None
        )
        call_started = time.perf_counter()
        try:
            raw, metadata = coordinator.call_ollama(model, view, timeout)
            trial.update(raw_decision=copy.deepcopy(raw), metadata=metadata)
            if not isinstance(raw, dict):
                raise ValueError("Coordinator response must be a JSON object.")
            decision = coordinator.enrich_deterministic_configuration(copy.deepcopy(raw), context)
        except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
            trial.update(status="TIMEOUT" if "TIMEOUT" in str(error).upper() else "ERROR", error=str(error))
        trial["call_wall_seconds"] = time.perf_counter() - call_started
        trial["decision_wall_seconds"] = time.perf_counter() - started

    validation_started = time.perf_counter()
    if decision is not None:
        try:
            trial["validation_errors"] = coordinator.validate_decision(decision, context)
        except (TypeError, AttributeError) as error:
            trial["validation_errors"] = [str(error)]
        if trial["validation_errors"]:
            trial["status"] = "INVALID"
    proposal = decision if decision is not None else trial["raw_decision"]
    proposes_accept = isinstance(proposal, dict) and proposal.get("decision") == "ACCEPT"
    matches_configuration = eligible and isinstance(decision, dict) and (
        type(decision.get("recommended_threads")) is int
        and decision["recommended_threads"] == configuration["threads"]
        and decision.get("recommended_configuration") == configuration
    )
    accepted = bool(trial["status"] == "OK" and proposes_accept and matches_configuration)
    sequential_time = bundle["measurements"][0]["median_seconds"]
    final_time = selected["median_seconds"] if accepted else sequential_time
    trial.update(
        decision=decision, effective_accept=accepted,
        nonadmissible_accept_proposal=bool(proposes_accept and not matches_configuration),
        missed_eligible_opportunity=bool(eligible and not accepted),
        policy_agreement=bool(trial["status"] == "OK" and (
            accepted if eligible else not proposes_accept)),
        attempts_to_acceptable_candidate=1 if accepted else None,
        final_mode="openmp" if accepted else "sequential_fallback",
        selected_configuration=configuration if accepted else None,
        measured_final_seconds=final_time, speedup_vs_sequential=sequential_time / final_time,
        parallel_scaling_speedup=one_thread["median_seconds"] / final_time if accepted else None,
        validation_wall_seconds=time.perf_counter() - validation_started,
        trial_wall_seconds=time.perf_counter() - started,
    )
    write_json(directory / "trial.json", trial)
    return trial


def aggregate(trials):
    groups = []
    for case, mode in sorted({(trial["case"], trial["mode"]) for trial in trials}):
        rows = [trial for trial in trials if (trial["case"], trial["mode"]) == (case, mode)]
        groups.append({
            "case": case, "mode": mode, "trials": len(rows),
            "valid_responses": sum(row["status"] == "OK" for row in rows),
            "failures": sum(row["status"] != "OK" for row in rows),
            "timeouts": sum(row["status"] == "TIMEOUT" for row in rows),
            "policy_agreement_rate": sum(row["policy_agreement"] for row in rows) / len(rows),
            "effective_accept_rate": sum(row["effective_accept"] for row in rows) / len(rows),
            "nonadmissible_accept_proposals": sum(row["nonadmissible_accept_proposal"] for row in rows),
            "missed_eligible_opportunities": sum(row["missed_eligible_opportunity"] for row in rows),
            "llm_calls": sum(row["llm_calls"] for row in rows),
            "observed_prompt_tokens": sum(row["metadata"].get("prompt_eval_count") or 0 for row in rows)
                if any(row["metadata"].get("prompt_eval_count") is not None for row in rows) else None,
            "observed_generated_tokens": sum(row["metadata"].get("eval_count") or 0 for row in rows)
                if any(row["metadata"].get("eval_count") is not None for row in rows) else None,
            "median_decision_seconds": statistics.median(row["decision_wall_seconds"] for row in rows),
            "min_decision_seconds": min(row["decision_wall_seconds"] for row in rows),
            "max_decision_seconds": max(row["decision_wall_seconds"] for row in rows),
            "median_accounted_pipeline_seconds": statistics.median(row["accounted_pipeline_seconds"] for row in rows)
                if all(row["accounted_pipeline_seconds"] is not None for row in rows) else None,
            "median_speedup_vs_sequential": statistics.median(row["speedup_vs_sequential"] for row in rows),
        })
    return groups


def save_results(directory, report):
    report["groups"] = aggregate(report["trials"])
    write_json(directory / "results.json", report)
    columns = ("case", "repetition", "mode", "status", "eligible", "effective_accept", "policy_agreement",
               "nonadmissible_accept_proposal", "missed_eligible_opportunity", "candidate_attempts", "llm_calls",
               "decision_wall_seconds", "validation_wall_seconds", "shared_prefix_seconds",
               "accounted_pipeline_seconds", "speedup_vs_sequential", "parallel_scaling_speedup")
    with (directory / "trials.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["trials"])
    lines = ["# Avaliação pareada do Coordinator", "", f"Estado: **{report['status']}**.", "",
             "Mesmos candidatos e medições em todos os modos. Concordância é com a política de promoção,",
             "não um julgamento independente de qualidade. Falhas permanecem no denominador.", "",
             "| Caso | Modo | Válidas/total | Concordância | Aceitação | Decisão (s, mediana) | Speedup vs seq. |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for group in report["groups"]:
        lines.append(f"| {group['case']} | {group['mode']} | {group['valid_responses']}/{group['trials']} | "
                     f"{group['policy_agreement_rate']:.0%} | {group['effective_accept_rate']:.0%} | "
                     f"{group['median_decision_seconds']:.6f} | {group['median_speedup_vs_sequential']:.3f} |")
    lines += ["", "O speedup usa medições compartilhadas; uma recusa/falha retorna ao sequencial (1×).",
              "O tempo contabilizado soma o prefixo real compartilhado ao custo de cada decisão/validação;",
              "não é uma nova execução independente do pipeline. Não inclui publicação/revalidação final.",
              "Há um candidato por caso e nenhuma recuperação automática por RETUNE/MODIFY nesta avaliação.",
              "Repetições da LLM reutilizam evidências e não são novas amostras de desempenho do kernel.",
              "Dois tamanhos de Dot Product não permitem generalização para outros padrões.", "",
              "Comparações da LLM só podem ser discutidas após concluir as inferências reais."]
    if report.get("error"):
        lines += ["", "Erro: " + report["error"]]
    (directory / "report.md").write_text("\n".join(lines) + "\n")


def evaluate(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="evaluation-", dir=args.output_dir.resolve()))
    started = time.perf_counter()
    report = {"schema": "tcc2-coordinator-evaluation", "version": "0.1", "status": "RUNNING",
              "created_at": datetime.now(timezone.utc).isoformat(), "settings": {
                  "model": args.model, "timeout_seconds": args.timeout, "seed": args.seed,
                  "repetitions": args.repetitions, "baseline_only": args.baseline_only,
                  "temperature": 0, "order": "seeded_shuffle_per_case_and_repetition",
              }, "implementation": [file_record(path) for path in (
                  Path(__file__), ROOT / "agents/coordinator_agent.py", ROOT / "analysis/artifact_provenance.py",
                  ROOT / "analysis/performance_selector.py", ROOT / "scripts/run_pipeline.py",
              )], "cases": [], "trials": []}
    save_results(directory, report)
    try:
        cases = []
        if args.contexts:
            cases = [(f"case_{index + 1}", path.resolve(), None) for index, path in enumerate(args.contexts)]
        else:
            for name, driver in (("dot_large", "dot_benchmark_driver.c"), ("dot_small", "dot_small_benchmark_driver.c")):
                pipeline_args = argparse.Namespace(
                    source=ROOT / "analysis/fixtures/dot_product.c", driver=ROOT / "analysis/fixtures/dot_driver.c",
                    benchmark_driver=ROOT / "analysis/fixtures" / driver, compiler=args.compiler,
                    threads=args.threads, model=args.model, timeout=args.timeout, prepare_only=True,
                    work_dir=directory / name, output_dir=directory / "unused_promotions",
                )
                code, work = run_pipeline(pipeline_args)
                if code:
                    raise RuntimeError(f"Case preparation failed; see {work / 'summary.json'}")
                summary = json.loads((work / "summary.json").read_text())
                cases.append((name, work / "context.json", summary["elapsed_seconds"]))
        randomizer = random.Random(args.seed)
        modes = MODES[:1] if args.baseline_only else MODES
        for name, path, prefix_seconds in cases:
            context, bundle, reference = load_context_evidence(path)
            report["cases"].append({"case": name, "context": reference,
                                    "candidate_id": context["source"]["candidate_id"],
                                    "campaign_id": context["source"]["campaign_id"],
                                    "shared_prefix_seconds": prefix_seconds,
                                    "evidence": bundle["references"],
                                    "measurements": bundle["measurements"]})
            for repetition in range(1, args.repetitions + 1):
                order = list(modes)
                randomizer.shuffle(order)
                for position, mode in enumerate(order):
                    print(f"{name} {repetition}/{args.repetitions}: {mode}", flush=True)
                    trial = run_trial(context, bundle, mode, args.model, args.timeout,
                                      directory / f"{name}-{repetition}-{mode}")
                    trial.update(case=name, repetition=repetition, order_position=position,
                                 context_sha256=reference["sha256"], shared_prefix_seconds=prefix_seconds,
                                 accounted_pipeline_seconds=prefix_seconds + trial["trial_wall_seconds"]
                                 if prefix_seconds is not None else None)
                    write_json(directory / f"{name}-{repetition}-{mode}" / "trial.json", trial)
                    report["trials"].append(trial)
                    save_results(directory, report)
            verify_file(reference)
            load_context_evidence(path)
        for case in report["cases"]:
            verify_file(case["context"])
            load_context_evidence(Path(case["context"]["path"]))
        for reference in report["implementation"]:
            verify_file(reference)
        report["status"] = "BASELINE_ONLY" if args.baseline_only else "COMPLETE"
        if any(trial["status"] != "OK" or trial.get("ablation_effective") is False for trial in report["trials"]):
            report["status"] = "INCOMPLETE"
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report.update(status="FAILED", error=str(error))
    report["experiment_wall_seconds"] = time.perf_counter() - started
    save_results(directory, report)
    print(f"{report['status']}: {directory / 'report.md'}", flush=True)
    return (0 if report["status"] in ("BASELINE_ONLY", "COMPLETE") else 1), directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contexts", type=Path, nargs="+", help="Existing provenance-bound contexts; otherwise prepare two real Dot Product sizes.")
    parser.add_argument("--compiler", default="gcc")
    parser.add_argument("--threads", type=int, nargs="+", default=[1, 2])
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/coordinator_evaluation")
    args = parser.parse_args()
    if args.repetitions < 1 or args.timeout < 1 or (
        len(set(args.threads)) != len(args.threads) or min(args.threads) < 1
        or 1 not in args.threads or not any(count > 1 for count in args.threads)
    ):
        parser.error("Use positive timeout/repetitions and distinct positive threads including 1 and a parallel count.")
    return evaluate(args)[0]


if __name__ == "__main__":
    sys.exit(main())
