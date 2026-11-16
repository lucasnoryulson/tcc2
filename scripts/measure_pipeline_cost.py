"""Measure real pipeline stages and paired deterministic/LLM admission costs."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.artifact_provenance import file_record, load_context_evidence
from scripts.benchmark_scaling import write_csv, write_json
from scripts.evaluate_coordinator import run_trial
from scripts.promote_candidate import promote_candidate
from scripts.run_pipeline import run_pipeline
from scripts.analyze_pipeline_cost import analyze as verify_prefix


def break_even(cost, sequential, optimized):
    saving = sequential - optimized
    return math.ceil(cost / saving) if saving > 0 else None


def prepared_prefix(path):
    """Reject a prior inference/decision to avoid double counting its cost."""
    work = path.resolve()
    if verify_prefix(work)['status'] != 'PREPARED':
        raise ValueError('Only PREPARED evidence can be reused as a deterministic prefix')
    return work


def measure(args):
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    timing_log = args.output / 'process_timings.jsonl'
    os.environ['TCC2_PROCESS_TIMING_LOG'] = str(timing_log)
    report = dict(schema='tcc2-pipeline-cost-v1', status='RUNNING',
                  started_utc=datetime.now(timezone.utc).isoformat(),
                  protocol='New decision/promotion trials on a shared verified prefix; inspect prefix sampling separately',
                  model=args.model, repetitions=args.repetitions, trials=[], prefixes=[])
    source_archive = args.output / 'harness_sources'
    source_archive.mkdir()
    report['harness_sources'] = {}
    for name in ('measure_pipeline_cost.py', 'run_pipeline.py', 'process_timing.py',
                 'compile_correctness_gate.py', 'performance_gate.py', 'promote_candidate.py'):
        target = source_archive / name
        target.write_bytes((ROOT / 'scripts' / name).read_bytes())
        report['harness_sources'][name] = file_record(target)
    write_json(args.output / 'report.json', report)
    for endpoint in ('version', 'tags', 'ps'):
        with urllib.request.urlopen('http://127.0.0.1:11434/api/' + endpoint, timeout=10) as response:
            write_json(args.output / ('ollama_' + endpoint + '_before.json'), json.load(response))
    stages, rows = [], []
    for repeat in range(1, args.repetitions + 1):
        reused = getattr(args, 'prepared_run', None)
        if reused:
            work = prepared_prefix(reused)
            code = 0
        else:
            pipeline_args = argparse.Namespace(source=ROOT / 'analysis/fixtures/dot_product.c',
                driver=ROOT / 'analysis/fixtures/dot_driver.c', benchmark_driver=ROOT / 'analysis/fixtures/dot_benchmark_driver.c',
                compiler=args.compiler, threads=args.threads, model=args.model, timeout=args.timeout,
                work_dir=args.output / f'prefix-{repeat}', output_dir=args.output / 'unused', prepare_only=True)
            code, work = run_pipeline(pipeline_args)
        summary = json.loads((work / 'summary.json').read_text())
        report['prefixes'].append(dict(repetition=repeat, summary=file_record(work / 'summary.json'),
                                        status=summary['status'], elapsed_seconds=summary['elapsed_seconds'],
                                        reused_frozen_prefix=bool(reused)))
        if code:
            report['status'] = 'FAILED_PREFIX'
            write_json(args.output / 'report.json', report)
            return report
        context, bundle, context_ref = load_context_evidence(work / 'context.json')
        # Reused evidence was measured in its original campaign, not in this log.
        timings = [json.loads(s) for s in timing_log.read_text().splitlines()] if timing_log.exists() else []
        for step in summary['steps']:
            nested = [r for r in timings if r['stage'] == step['name']
                      and any(str(work) in arg for arg in r['command'])]
            compilation = sum(r['wall_seconds'] for r in nested if r['kind'] == 'compilation')
            execution = sum(r['wall_seconds'] for r in nested if r['kind'] == 'execution')
            stages.append(dict(repetition=repeat, stage=step['name'], inclusive_seconds=step['wall_seconds'],
                               compilation_seconds=None if reused else compilation,
                               execution_seconds=None if reused else execution,
                               overhead_seconds=None if reused else step['wall_seconds'] - compilation - execution))
        sequential = bundle['measurements'][0]['median_seconds']
        trial_root = args.output / f'decisions-{repeat}'
        trial_root.mkdir()
        # Alternate order between repetitions; all arms reuse the same frozen prefix.
        order = ('deterministic', 'coordinator') if repeat % 2 else ('coordinator', 'deterministic')
        for mode in order:
            trial = run_trial(context, bundle, mode, args.model, args.timeout, trial_root / mode)
            trial.update(repetition=repeat, context=context_ref)
            promotion_seconds, published = 0., None
            if trial['effective_accept']:
                decision = dict(trial['decision'])
                if mode == 'deterministic':
                    decision.update(reason='Real verified selection satisfies deterministic admission.',
                                    evidence_used=['linked correctness', 'measured selection'])
                envelope = dict(schema='tcc2-coordinator-decision', version='0.2',
                                model='deterministic-policy' if mode == 'deterministic' else args.model,
                                decision=decision,
                                evidence=dict(context=context_ref,
                                              candidate_id=context['source']['candidate_id'],
                                              campaign_id=context['source']['campaign_id']),
                                llm_metadata=trial['metadata'])
                decision_path = trial_root / mode / 'decision.json'
                write_json(decision_path, envelope)
                begin = time.perf_counter()
                try:
                    published = promote_candidate(decision_path, args.output / f'promoted-{repeat}-{mode}')
                except (OSError, ValueError, RuntimeError) as error:
                    trial['promotion_error'] = str(error)
                promotion_seconds = time.perf_counter() - begin
            cost = summary['elapsed_seconds'] + trial['trial_wall_seconds'] + promotion_seconds
            optimized = trial['measured_final_seconds']
            rows.append(dict(repetition=repeat, mode=mode, status=trial['status'],
                             accepted=trial['effective_accept'], promoted=published is not None,
                             shared_prefix_seconds=summary['elapsed_seconds'],
                             decision_seconds=trial['decision_wall_seconds'],
                             decision_validation_seconds=trial['validation_wall_seconds'],
                             promotion_seconds=promotion_seconds, total_accounted_seconds=cost,
                             sequential_seconds=sequential, optimized_seconds=optimized,
                             saving_per_execution_seconds=sequential - optimized,
                             break_even_executions=break_even(cost, sequential, optimized),
                             llm_calls=trial['llm_calls']))
            trial['promotion'] = str(published) if published else None
            report['trials'].append(trial)
            write_json(args.output / 'report.json', report)
            if trial['status'] == 'TIMEOUT':
                report['status'] = 'INCOMPLETE_TIMEOUT'
                report['finished_utc'] = datetime.now(timezone.utc).isoformat()
                write_json(args.output / 'report.json', report)
                write_csv(args.output / 'costs.csv', rows)
                write_csv(args.output / 'stages.csv', stages)
                return report
    report.update(status='COMPLETE' if all(r['status'] == 'OK' and (not r['accepted'] or r['promoted']) for r in rows) else 'COMPLETE_WITH_FAILURES',
                  finished_utc=datetime.now(timezone.utc).isoformat(),
                  accounting='A reused frozen prefix is measured once for all trials; otherwise once per repetition. '
                    'Both arms share prefix evidence. Totals are accounting comparisons, not independent end-to-end runs. '
                    'Promotion includes fresh compilation and validation; stage CSV is inclusive and must not be summed twice.')
    write_csv(args.output / 'costs.csv', rows)
    write_csv(args.output / 'stages.csv', stages)
    write_json(args.output / 'report.json', report)
    with urllib.request.urlopen('http://127.0.0.1:11434/api/ps', timeout=10) as response:
        write_json(args.output / 'ollama_ps_after.json', json.load(response))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compiler', default='/opt/homebrew/opt/llvm/bin/clang')
    parser.add_argument('--threads', type=int, nargs='+', default=[1, 2, 4, 6, 8, 10])
    parser.add_argument('--model', default='llama3.1:8b')
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--prepared-run', type=Path,
                        help='Reuse one verified immutable prefix; decision/promotion trials remain new. '
                             'Totals are accounting comparisons, not repeated independent pipelines.')
    args = parser.parse_args()
    if args.repetitions < 1 or args.timeout < 1 or len(set(args.threads)) != len(args.threads) or 1 not in args.threads or min(args.threads) < 1:
        parser.error('Use positive repetitions/timeout and distinct positive threads including 1')
    print(json.dumps({'status': measure(args)['status']}))
