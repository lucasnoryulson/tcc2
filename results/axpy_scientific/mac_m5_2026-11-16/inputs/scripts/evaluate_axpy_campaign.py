"""Archive two real AXPY pipeline sessions under a predeclared protocol."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.artifact_provenance import load_context_evidence
from scripts.analyze_pipeline_cost import analyze as analyze_cost, break_even
from scripts.analyze_scaling import enrich, figures, selections
from scripts.benchmark_scaling import Campaign, capture_environment, summarize, write_csv, write_json
from scripts.evaluate_selector_holdout import evaluate_rows
from scripts.run_pipeline import run_pipeline

PROTOCOL = ROOT / 'docs/experiments/AXPY_SCIENTIFIC_PROTOCOL_2026-11-16.json'
SOURCES = ['analysis/fixtures/axpy.c', 'analysis/fixtures/axpy_driver.c',
    'analysis/fixtures/axpy_benchmark_driver.c', 'analysis/artifact_provenance.py',
    'analysis/conservative_transform.py', 'analysis/static_analyzer.py',
    'analysis/dependence_analyzer.py', 'analysis/pattern_classifier.py',
    'analysis/strategy_planner.py', 'analysis/code_transformer.py',
    'analysis/performance_selector.py', 'agents/context_builder.py',
    'scripts/compile_correctness_gate.py', 'scripts/performance_gate.py',
    'scripts/run_pipeline.py', 'scripts/process_timing.py', 'scripts/benchmark_scaling.py',
    'scripts/analyze_scaling.py', 'scripts/analyze_pipeline_cost.py',
    'scripts/evaluate_selector_holdout.py', 'scripts/evaluate_axpy_campaign.py']


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def driver_text(template, n, repeats):
    if type(n) is not int or not 0 < n <= 2147483647 // 7 or type(repeats) is not int or repeats < 1:
        raise ValueError('Invalid AXPY input or repeat count')
    for marker in ('#define N 10000000', '#define INNER_REPEATS 40'):
        if template.count(marker) != 1:
            raise ValueError('Unexpected benchmark template')
    return template.replace('#define N 10000000', f'#define N {n}').replace(
        '#define INNER_REPEATS 40', f'#define INNER_REPEATS {repeats}')


def seal(directory):
    entries = [dict(path=str(p.relative_to(directory)), sha256=sha(p))
               for p in sorted(directory.rglob('*')) if p.is_file() and p.name != 'archive_manifest.json']
    write_json(directory / 'archive_manifest.json', entries)


def verify_seal(directory):
    entries = json.loads((directory / 'archive_manifest.json').read_text())
    actual = {str(p.relative_to(directory)) for p in directory.rglob('*')
              if p.is_file() and p.name != 'archive_manifest.json'}
    if len(entries) != len(actual) or {e['path'] for e in entries} != actual:
        raise ValueError('Archive files were added or removed')
    for entry in entries:
        path = (directory / entry['path']).resolve()
        if directory.resolve() not in path.parents or sha(path) != entry['sha256']:
            raise ValueError('Archive SHA-256 mismatch: ' + entry['path'])


def prepare(directory):
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / 'protocol.json', json.loads(PROTOCOL.read_text()))
    snapshots = []
    for relative in SOURCES:
        target = directory / 'inputs' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        snapshots.append(dict(original=relative, snapshot=str(target.relative_to(directory)), sha256=sha(target)))
    protocol = json.loads((directory / 'protocol.json').read_text())
    template = (directory / 'inputs/analysis/fixtures/axpy_benchmark_driver.c').read_text()
    for entry in protocol['inputs']:
        target = directory / 'inputs' / f"benchmark_{entry['n']}.c"
        target.write_text(driver_text(template, entry['n'], entry['inner_repeats']))
        snapshots.append(dict(original=None, snapshot=str(target.relative_to(directory)), sha256=sha(target)))
    write_json(directory / 'source_manifest.json', snapshots)
    write_json(directory / 'preparation.json', dict(status='PREPARED_NO_MEASUREMENTS', frozen_at_utc=utc(),
        protocol_sha256=sha(directory / 'protocol.json'),
        source_manifest_sha256=sha(directory / 'source_manifest.json'),
        git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()))


def verify_inputs(directory):
    preparation = json.loads((directory / 'preparation.json').read_text())
    for key, filename in [('protocol_sha256', 'protocol.json'), ('source_manifest_sha256', 'source_manifest.json')]:
        if sha(directory / filename) != preparation[key]:
            raise ValueError('Changed frozen protocol or source manifest')
    for entry in json.loads((directory / 'source_manifest.json').read_text()):
        if sha(directory / entry['snapshot']) != entry['sha256']:
            raise ValueError('Changed frozen input')
        if entry['original'] and sha(ROOT / entry['original']) != entry['sha256']:
            raise ValueError('Live harness/source changed since protocol freeze')
    return json.loads((directory / 'protocol.json').read_text())


def collect(directory, number, compiler):
    directory = directory.resolve()
    protocol = verify_inputs(directory)
    if number == 2:
        verify_session(directory / 'session01')
        frozen = json.loads((directory / 'frozen_selection.json').read_text())
        if sha(directory / 'session01/report.json') != frozen['session_report_sha256']:
            raise ValueError('First session changed after selection freeze')
    session = directory / f'session{number:02d}'
    session.mkdir(exist_ok=False)
    (session / 'logs').mkdir()
    report = dict(schema='tcc2-axpy-session-v1', status='RUNNING', started_utc=utc(),
                  protocol_sha256=sha(directory / 'protocol.json'), runs=[])
    write_json(session / 'report.json', report)
    campaign = Campaign(session, 120)
    capture_environment(campaign, argparse.Namespace(output=session, cc=compiler, cxx=compiler))
    # A probe verifies requested workers independently of kernel timing.
    probe_source = session / 'team_probe.c'
    probe_source.write_text('#include <omp.h>\n#include <stdio.h>\nint main(void) {\n#pragma omp parallel\n{\n#pragma omp single\nprintf("%d\\n", omp_get_num_threads());\n}\n}\n')
    probe = session / 'team_probe'
    campaign.run([compiler, '-O3', '-fopenmp', probe_source, '-o', probe])
    report['actual_team_sizes_probe'] = {}
    for threads in protocol['threads']:
        output, _, _ = campaign.run([probe], threads=threads)
        if int(output.strip()) != threads:
            raise ValueError('OpenMP probe did not create the requested team')
        report['actual_team_sizes_probe'][str(threads)] = threads
    samples, warmups, costs = [], [], []
    try:
        for entry in protocol['inputs']:
            n = entry['n']
            print(f'Session {number}, N={n}', flush=True)
            args = argparse.Namespace(source=directory / 'inputs/analysis/fixtures/axpy.c',
                driver=directory / 'inputs/analysis/fixtures/axpy_driver.c',
                benchmark_driver=directory / 'inputs' / f'benchmark_{n}.c', compiler=compiler,
                threads=protocol['threads'], repetitions=protocol['repetitions'], warmups=protocol['warmups'],
                seed=protocol['seed'], prepare_only=True, model='not-used', timeout=180,
                work_dir=session / f'n{n}', output_dir=session / 'unused-promotion')
            code, work = run_pipeline(args)
            if code:
                raise ValueError('Pipeline did not complete; retain failed session without retry')
            _, bundle, _ = load_context_evidence(work / 'context.json')
            for item in bundle['performance']['measurement_order']:
                row = dict(kernel='axpy', size=n, variant='sequential' if item['mode'] == 'sequential' else 'automatic',
                           threads=item['threads'], repeat=item['repeat'], seconds=item['seconds'])
                (samples if item['stage'] == 'measurement' else warmups).append(row)
            record = dict(n=n, work=str(work.relative_to(session)),
                performance_sha256=sha(work / 'performance.json'), correctness_sha256=sha(work / 'correctness.json'),
                candidate_sha256=bundle['performance']['provenance']['inputs']['candidate']['sha256'],
                benchmark_driver_sha256=bundle['performance']['provenance']['inputs']['driver']['sha256'],
                toolchain=bundle['performance']['provenance']['toolchain'])
            report['runs'].append(record)
            costs.append(dict(n=n, **analyze_cost(work)))
            write_json(session / 'report.json', report)
        summary = summarize(samples)
        write_csv(session / 'samples.csv', samples)
        write_csv(session / 'warmups.csv', warmups)
        write_csv(session / 'summary.csv', summary)
        write_json(session / 'selection.json', selections(summary))
        write_json(session / 'costs.json', costs)
        verify_inputs(directory)
        if shutil.which('pmset'):
            campaign.run(['pmset', '-g', 'batt'], check=False)
        report.update(status='COMPLETE', finished_utc=utc(), configurations=len(summary),
                      measured_samples=len(samples), warmup_samples=len(warmups))
        write_json(session / 'report.json', report)
        seal(session)
        verify_session(session)
    except Exception as error:
        report.update(status='FAILED', error=str(error), finished_utc=utc())
        write_json(session / 'report.json', report)
        raise


def verify_session(session):
    verify_seal(session)
    report = json.loads((session / 'report.json').read_text())
    protocol = verify_inputs(session.parent)
    if report['status'] != 'COMPLETE' or report['protocol_sha256'] != sha(session.parent / 'protocol.json'):
        raise ValueError('Incomplete or incompatible session')
    samples, warmups, costs = [], [], []
    for entry in report['runs']:
        work = session / entry['work']
        _, bundle, _ = load_context_evidence(work / 'context.json')
        performance = bundle['performance']
        inputs = performance['provenance']['inputs']
        if (sha(work / 'performance.json') != entry['performance_sha256']
            or sha(work / 'correctness.json') != entry['correctness_sha256']
            or performance['thread_counts'] != protocol['threads']
            or (performance['repetitions'], performance['warmups'], performance['seed'])
               != (protocol['repetitions'], protocol['warmups'], protocol['seed'])):
            raise ValueError('Changed gate or sampling protocol')
        if (entry['candidate_sha256'] != inputs['candidate']['sha256']
            or entry['benchmark_driver_sha256'] != inputs['driver']['sha256']
            or entry['toolchain'] != performance['provenance']['toolchain']
            or inputs['sequential']['sha256'] != sha(session.parent / 'inputs/analysis/fixtures/axpy.c')
            or inputs['driver']['sha256'] != sha(session.parent / 'inputs' / f"benchmark_{entry['n']}.c")):
            raise ValueError('Candidate, source, benchmark driver or compiler identity disagrees')
        for item in performance['measurement_order']:
            row = dict(kernel='axpy', size=entry['n'], variant='sequential' if item['mode'] == 'sequential' else 'automatic',
                       threads=item['threads'], repeat=item['repeat'], seconds=item['seconds'])
            (samples if item['stage'] == 'measurement' else warmups).append(row)
        costs.append(dict(n=entry['n'], **analyze_cost(work)))
    summary = summarize(samples)
    import csv
    for filename, rows in [('samples.csv', samples), ('warmups.csv', warmups), ('summary.csv', summary)]:
        with (session / filename).open() as stream:
            if list(csv.DictReader(stream)) != [{k: str(v) for k, v in row.items()} for row in rows]:
                raise ValueError('Derived table differs from gate observations: ' + filename)
    if (json.loads((session / 'selection.json').read_text()) != selections(summary)
        or json.loads((session / 'costs.json').read_text()) != costs
        or [r['n'] for r in report['runs']] != [r['n'] for r in protocol['inputs']]
        or (report['configurations'], report['measured_samples'], report['warmup_samples'])
           != (len(summary), len(samples), len(warmups))):
        raise ValueError('Session summary/selection/costs disagree')
    return report, summary, samples, costs


def freeze(directory):
    report, summary, _, _ = verify_session(directory / 'session01')
    path = directory / 'frozen_selection.json'
    if path.exists() or (directory / 'session02').exists():
        raise ValueError('Freeze only once, before collecting session 2')
    write_json(path, dict(frozen_at_utc=utc(), choices=selections(summary),
        session_finished_utc=report['finished_utc'], session_report_sha256=sha(directory / 'session01/report.json'),
        session_manifest_sha256=sha(directory / 'session01/archive_manifest.json'),
        selector_sha256=sha(ROOT / 'analysis/performance_selector.py')))


def analyze(directory, output):
    a, first, raw_a, costs_a = verify_session(directory / 'session01')
    b, second, raw_b, costs_b = verify_session(directory / 'session02')
    frozen = json.loads((directory / 'frozen_selection.json').read_text())
    if (datetime.fromisoformat(b['started_utc']) <= datetime.fromisoformat(frozen['frozen_at_utc'])
        or frozen['choices'] != selections(first)
        or frozen['session_report_sha256'] != sha(directory / 'session01/report.json')
        or frozen['session_manifest_sha256'] != sha(directory / 'session01/archive_manifest.json')
        or frozen['selector_sha256'] != sha(ROOT / 'analysis/performance_selector.py')):
        raise ValueError('Invalid freeze chronology or changed selection evidence')
    identities = lambda r: [{k: run[k] for k in ('n', 'candidate_sha256', 'benchmark_driver_sha256', 'toolchain')} for run in r['runs']]
    if identities(a) != identities(b):
        raise ValueError('Different candidate, benchmark input or compiler across sessions')
    output.mkdir(parents=True, exist_ok=False)
    policies, sensitivity, stability = evaluate_rows(first, second, frozen['choices'])
    for filename, rows in [('policies.csv', policies), ('sensitivity.csv', sensitivity), ('stability.csv', stability)]:
        write_csv(output / filename, rows)
    for number, summary, raw in [(1, first, raw_a), (2, second, raw_b)]:
        enriched = enrich(summary, raw)
        write_csv(output / f'measurements_session{number:02d}.csv', enriched)
        charts = output / f'figures_session{number:02d}'
        charts.mkdir()
        figures(enriched, charts, 15, selections(summary))
    amortization = []
    for cost in costs_a:
        case = next(r for r in policies if r['size'] == str(cost['n']) and r['policy'] == 'selector')
        amortization.append(dict(n=cost['n'], measured_prefix_seconds=cost['elapsed_seconds'],
            second_session_prefix_seconds=next(c['elapsed_seconds'] for c in costs_b if c['n'] == cost['n']),
            in_sample_prefix_break_even=cost['prefix_break_even'],
            holdout_prefix_break_even=break_even(cost['elapsed_seconds'],
                next(r['median_seconds'] for r in second if r['size'] == cost['n'] and r['variant'] == 'sequential'),
                case['median_seconds']),
            lower_bound_full_admission=True, new_llm_cost_measured=False))
    write_csv(output / 'amortization.csv', amortization)
    result = dict(status='COMPLETE', completed_utc=utc(), sessions=2,
        configurations_per_session=a['configurations'], measured_samples=a['measured_samples'] + b['measured_samples'],
        warmup_samples=a['warmup_samples'] + b['warmup_samples'],
        stable_cases=sum(r['unchanged'] for r in stability), cases=len(stability),
        selector_inadequate=sum(r['inadequate'] for r in policies if r['policy'] == 'selector'),
        first_report_sha256=sha(directory / 'session01/report.json'), second_report_sha256=sha(directory / 'session02/report.json'),
        frozen_choices_sha256=sha(directory / 'frozen_selection.json'), protocol_sha256=sha(directory / 'protocol.json'),
        amortization=amortization,
        limitations='One source, same host/day, no independent-machine or population inference. '
            'Input footprints are logical bytes, not measured cache/DRAM residency. Prefix-only costs exclude LLM and promotion.')
    write_json(output / 'report.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'session01', 'freeze', 'session02', 'analyze', 'verify'))
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--compiler', default='/opt/homebrew/opt/llvm/bin/clang')
    args = parser.parse_args()
    directory = args.directory.resolve()
    if args.command == 'prepare':
        prepare(directory)
    elif args.command.startswith('session'):
        collect(directory, int(args.command[-2:]), args.compiler)
    elif args.command == 'freeze':
        freeze(directory)
    elif args.command == 'analyze':
        if args.output is None:
            parser.error('--output is required for analysis')
        print(json.dumps(analyze(directory, args.output.resolve())))
    else:
        for number in (1, 2):
            verify_session(directory / f'session{number:02d}')
        print('VERIFIED')
