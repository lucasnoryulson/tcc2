"""Archive controlled program coverage and optional paired real scaling samples.

Hand-authored sources are controlled tests, not an external program population.
The existing correctness gate is reused; its driver additionally checks every
output element against a specification formula, then emits a scalar checksum.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark_scaling import Campaign, capture_environment, summarize, write_csv, write_json
from scripts.analyze_scaling import enrich, selections
from scripts.performance_gate import parse_average_time

CATALOG = ROOT / 'analysis/fixtures/publication_corpus/catalog.json'


def transform_status(returncode, candidate_exists, contract, stderr):
    stderr = stderr.decode('utf-8', errors='replace') if isinstance(stderr, bytes) else stderr
    if returncode == 0:
        return 'ACCEPTED' if candidate_exists and contract.get('status') == 'SUPPORTED' else 'ERROR'
    if returncode is not None and contract.get('status') == 'REFUSED' and 'UNSUPPORTED_STANDALONE:' in stderr:
        return 'REFUSED'
    return 'ERROR'


def driver_text(case, n, repeats=1):
    if not case['expected_support']:
        raise ValueError('No candidate driver is generated for an expected refusal.')
    reduction = case['pattern'] == 'REDUCTION'
    declaration = 'double kernel_case(int, const double *, const double *);' if reduction else 'void kernel_case(int, const double *restrict, const double *restrict, double *restrict);'
    call = 'result = kernel_case(n, A, B);' if reduction else 'kernel_case(n, A, B, Y);'
    validation = '''
    long double total = 0.0L;
    for (int i = 0; i < n; i++) total += expected_value(i);
    double expected = (double)total;
    if (!isfinite(result) || fabs(result - expected) > 1e-12 + 1e-9 * fabs(expected)) return 3;
    ''' if reduction else '''
    long double total = 0.0L;
    for (int i = 0; i < n; i++) {
        double expected = expected_value(i);
        if (!isfinite(Y[i]) || fabs(Y[i] - expected) > 1e-12 + 1e-9 * fabs(expected)) return 3;
        total += Y[i];
    }
    result = (double)total;
    '''
    return f'''#define _POSIX_C_SOURCE 200809L
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
{declaration}
static double input_a(int i) {{ return ((i % 23) - 11) / 16.0; }}
static double input_b(int i) {{ return (((i * 7) % 19) - 9) / 32.0; }}
static double expected_value(int i) {{
    double a = input_a(i), b = input_b(i);
    return {case['oracle_expression']};
}}
static double seconds(struct timespec t) {{ return t.tv_sec + t.tv_nsec * 1e-9; }}
int main(void) {{
    const int n = {n}, repeats = {repeats};
    double *A = malloc((size_t)(n + 2) * sizeof(double));
    double *B = malloc((size_t)(n + 2) * sizeof(double));
    double *Y = malloc((size_t)(n + 2) * sizeof(double));
    if (!A || !B || !Y) {{ free(A); free(B); free(Y); return 2; }}
    for (int i = 0; i < n + 2; i++) {{ A[i] = input_a(i); B[i] = input_b(i); Y[i] = NAN; }}
    double result = 0.0;
    struct timespec begin, end;
    if (clock_gettime(CLOCK_MONOTONIC, &begin)) return 4;
    for (int repetition = 0; repetition < repeats; repetition++) {{ {call} }}
    if (clock_gettime(CLOCK_MONOTONIC, &end)) return 4;
    {validation}
    printf("%.17g\\nAVERAGE_SECONDS=%.17g\\n", result, (seconds(end) - seconds(begin)) / repeats);
    free(A); free(B); free(Y);
    return 0;
}}
'''


def load_catalog(path):
    catalog = json.loads(path.read_text())
    cases = catalog['cases']
    if len({case['id'] for case in cases}) != len(cases):
        raise ValueError('Duplicate source identity.')
    for case in cases:
        source = (path.parent / case['source']).resolve()
        if source.parent != path.parent.resolve() or not source.is_file() or case['split'] not in ('development', 'test'):
            raise ValueError('Invalid source path or split.')
        if len({entry['id'] for entry in case['inputs']}) != len(case['inputs']):
            raise ValueError('Duplicate input identity.')
        if any(not isinstance(entry['n'], int) or not 0 < entry['n'] <= 2147483647 // 7 - 2 for entry in case['inputs']):
            raise ValueError('Input extent risks C integer overflow.')
    return catalog


def archive_record(directory, path):
    return dict(path=str(path.relative_to(directory)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def verify_archive(directory):
    directory = directory.resolve()
    manifest = json.loads((directory / 'archive_manifest.json').read_text())
    paths = [record['path'] for record in manifest]
    if len(set(paths)) != len(paths):
        raise ValueError('Duplicate archive identity.')
    actual = {str(path.relative_to(directory)) for path in directory.rglob('*')
              if path.is_file() and path.name != 'archive_manifest.json'}
    if actual != set(paths):
        raise ValueError('Archive files were added or removed.')
    for record in manifest:
        path = (directory / record['path']).resolve()
        if directory not in path.parents or archive_record(directory, path) != record:
            raise ValueError('Archive SHA-256 mismatch: ' + record['path'])
    report = json.loads((directory / 'report.json').read_text())
    if report['status'] != 'COMPLETE':
        raise ValueError('Incomplete coverage or campaign.')
    if report['measured']:
        commands = [json.loads(line) for line in (directory / 'commands.jsonl').read_text().splitlines()]
        configs = json.loads((directory / 'configurations.json').read_text())
        config_keys = {(c['kernel'], c['size'], c['variant'], c['threads']) for c in configs}
        for filename, expected_rounds, expected_count in [('samples.csv', report['protocol']['samples'], report['sample_count']),
                                                        ('warmups.csv', report['protocol']['warmups'], report['warmup_count'])]:
            rows = list(csv.DictReader((directory / filename).open()))
            if len(rows) != expected_count or len(rows) != len(configs) * expected_rounds:
                raise ValueError('Incomplete rounds: ' + filename)
            for repeat in range(1, expected_rounds + 1):
                block = [r for r in rows if int(r['repeat']) == repeat]
                keys = [(r['kernel'], r['size'], r['variant'], int(r['threads'])) for r in block]
                if len(keys) != len(config_keys) or set(keys) != config_keys:
                    raise ValueError('Missing or duplicate configuration in measurement round.')
            for row in rows:
                command = commands[int(row['command_id']) - 1]
                text = (directory / command['stdout']['path']).read_text()
                if command['returncode'] != 0 or command['threads'] != int(row['threads']) or parse_average_time(text) != float(row['seconds']):
                    raise ValueError('Sample does not match its archived execution.')
    return dict(status='VERIFIED', files=len(manifest), report=report)


def run(args):
    catalog = load_catalog(args.catalog)
    cases = [case for case in catalog['cases'] if not args.case or case['id'] in args.case]
    if not cases or (args.case and set(args.case) != {case['id'] for case in cases}):
        raise ValueError('Unknown case identifier.')
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    for child in ('logs', 'sources', 'cases', 'binaries'):
        (directory / child).mkdir()
    campaign = Campaign(directory, 120)
    write_json(directory / 'report.json', dict(schema='tcc2-automation-corpus-evaluation', status='RUNNING'))
    args.cxx = args.cc
    capture_environment(campaign, SimpleNamespace(**{
        key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()
    }))
    snapshots = []
    needed = [args.catalog, ROOT / 'analysis/conservative_transform.py', ROOT / 'analysis/static_analyzer.py',
              ROOT / 'analysis/dependence_analyzer.py', ROOT / 'analysis/pattern_classifier.py',
              ROOT / 'analysis/strategy_planner.py', ROOT / 'analysis/code_transformer.py',
              ROOT / 'scripts/evaluate_automation_corpus.py', ROOT / 'scripts/compile_correctness_gate.py',
              ROOT / 'analysis/artifact_provenance.py', ROOT / 'scripts/benchmark_scaling.py',
              ROOT / 'scripts/analyze_scaling.py', ROOT / 'scripts/performance_gate.py',
              ROOT / 'analysis/performance_selector.py', ROOT / 'scripts/consolidate_experiments.py']
    needed += [(args.catalog.parent / case['source']) for case in cases]
    for source in needed:
        relative = source.resolve().relative_to(ROOT)
        target = directory / 'sources' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        snapshots.append(archive_record(directory, target))
    write_json(directory / 'source_manifest.json', snapshots)
    records, configurations, binaries = [], [], []
    for case in cases:
        print('CASE ' + case['id'], flush=True)
        work = directory / 'cases' / case['id']
        work.mkdir()
        source = directory / 'sources' / (args.catalog.parent / case['source']).relative_to(ROOT)
        obj = work / 'original.o'
        campaign.run([args.cc, '-O3', '-c', source, '-o', obj])
        binaries.append(archive_record(directory, obj))
        analysis = work / 'analysis'
        campaign.run([sys.executable, '-B', ROOT / 'analysis/static_analyzer.py', source, '--output-dir', analysis])
        static_files = list(analysis.glob('*_analysis.json'))
        if len(static_files) != 1:
            raise ValueError('Expected exactly one static analysis artifact.')
        stem = static_files[0].stem.removesuffix('_analysis')
        for script, arguments in [
            ('dependence_analyzer.py', [static_files[0]]),
            ('pattern_classifier.py', [static_files[0], analysis / (stem + '_dependences.json')]),
            ('strategy_planner.py', [static_files[0], analysis / (stem + '_patterns.json')]),
        ]:
            campaign.run([sys.executable, '-B', ROOT / 'analysis' / script, *arguments])
        candidate = work / 'candidate.c'
        _, transformer_stderr, command_id = campaign.run([sys.executable, '-B', ROOT / 'analysis/code_transformer.py', source,
            static_files[0], analysis / (stem + '_strategy.json'), '--output', candidate], check=False)
        last_command = json.loads((directory / 'commands.jsonl').read_text().splitlines()[-1])
        contract = json.loads(static_files[0].read_text())['kernels'][0]['direct_transform_contract']
        status = transform_status(last_command['returncode'], candidate.is_file(), contract, transformer_stderr)
        accepted = status == 'ACCEPTED'
        record = dict(id=case['id'], split=case['split'], pattern=case['pattern'], expected_support=case['expected_support'],
                      accepted=accepted, transform_status=status, transform_command_id=command_id, functional_inputs=[],
                      contract=contract)
        records.append(record)
        if not accepted or not case['expected_support']:
            continue  # An expected-unsafe candidate is never executed.
        for entry in case['inputs']:
            driver = work / ('driver_' + entry['id'] + '.c')
            driver.write_text(driver_text(case, entry['n']))
            correctness = work / ('correctness_' + entry['id'] + '.json')
            campaign.run([sys.executable, '-B', ROOT / 'scripts/compile_correctness_gate.py', '--sequential', source,
                '--candidate', candidate, '--driver', driver, '--compiler', args.cc, '--threads', *map(str, args.threads),
                '--build-dir', work / ('gate_' + entry['id']), '--output', correctness])
            report = json.loads(correctness.read_text())
            if report['status'] != 'PASS':
                raise RuntimeError('Correctness gate failed: ' + str(correctness))
            record['functional_inputs'].append(dict(input=entry, status='PASS', report=archive_record(directory, correctness)))
            if not args.measure:
                continue
            benchmark_driver = work / ('benchmark_' + entry['id'] + '.c')
            repeats = 1000 if entry['n'] <= 1024 else 20
            benchmark_driver.write_text(driver_text(case, entry['n'], repeats))
            driver_object = work / ('benchmark_' + entry['id'] + '.o')
            # Compile the driver once without autopar: GCC must not prewarm its workers
            # by parallelizing initialization/validation outside the measured kernel.
            campaign.run([args.cc, '-O3', '-c', benchmark_driver, '-o', driver_object])
            binaries.append(archive_record(directory, driver_object))
            arms = [('sequential', 1, source, ['-O3'])]
            arms += [('pipeline_openmp', threads, candidate, ['-O3', '-fopenmp']) for threads in args.threads]
            if args.gcc_baseline:
                arms += [('gcc_autopar', threads, source, ['-O3', '-ftree-parallelize-loops=' + str(threads), '-fopt-info-loop-optimized']) for threads in args.threads]
            for variant, threads, input_source, flags in arms:
                binary = directory / 'binaries' / f"{case['id']}_{entry['id']}_{variant}_{threads}"
                kernel_object = binary.with_suffix('.o')
                campaign.run([args.cc, *flags, '-c', input_source, '-o', kernel_object])
                campaign.run([args.cc, driver_object, kernel_object,
                              *(['-fopenmp'] if variant != 'sequential' else []), '-lm', '-o', binary])
                campaign.run([binary], threads=threads)  # All timed drivers validate after their timer.
                binaries.append(archive_record(directory, kernel_object))
                binaries.append(archive_record(directory, binary))
                configurations.append(dict(kernel=case['id'], size=entry['id'], variant=variant,
                    threads=threads, n=entry['n'], internal_repeats=repeats, binary=str(binary.relative_to(directory))))
    coverage = {}
    for split in ('development', 'test', 'all'):
        selected = [record for record in records if split == 'all' or record['split'] == split]
        coverage[split] = dict(programs=len(selected), supported_expected=sum(r['expected_support'] for r in selected),
            unsupported_expected=sum(not r['expected_support'] for r in selected),
            accepted=sum(r['accepted'] for r in selected),
            true_acceptances=sum(r['accepted'] and r['expected_support'] for r in selected),
            false_acceptances=sum(r['accepted'] and not r['expected_support'] for r in selected),
            true_refusals=sum(r['transform_status'] == 'REFUSED' and not r['expected_support'] for r in selected),
            false_refusals=sum(r['transform_status'] == 'REFUSED' and r['expected_support'] for r in selected),
            unexpected_errors=sum(r['transform_status'] == 'ERROR' for r in selected),
            functional_inputs_passed=sum(len(r['functional_inputs']) for r in selected))
    write_json(directory / 'coverage.json', dict(provenance=catalog['provenance'], coverage=coverage, programs=records))
    write_json(directory / 'binary_manifest.json', binaries)
    write_json(directory / 'configurations.json', configurations)
    raw, warmups = [], []
    if args.measure:
        rng = random.Random(args.seed)
        for phase, count, target in [('warmup', args.warmups, warmups), ('measurement', args.samples, raw)]:
            for repeat in range(1, count + 1):
                order = list(configurations)
                rng.shuffle(order)
                print(f'{phase} {repeat}/{count}: {len(order)} configurations', flush=True)
                for position, config in enumerate(order):
                    stdout, _, command_id = campaign.run([directory / config['binary']], threads=config['threads'])
                    seconds = parse_average_time(stdout)
                    target.append({key: config[key] for key in ('kernel', 'size', 'variant', 'threads')} |
                        dict(repeat=repeat, position=position, seconds=seconds, command_id=command_id))
        write_csv(directory / 'samples.csv', raw)
        write_csv(directory / 'warmups.csv', warmups)
        summary = enrich(summarize(raw), raw, seed=args.seed)
        write_csv(directory / 'summary.csv', summary)
        write_json(directory / 'selection.json', selections(summary))
    failed = sum(coverage['all'][key] for key in ('false_acceptances', 'false_refusals', 'unexpected_errors'))
    result = dict(schema='tcc2-automation-corpus-evaluation', version='1.0', status='COMPLETE' if not failed else 'COVERAGE_MISMATCH',
        completed_utc=datetime.now(timezone.utc).isoformat(), coverage=coverage, measured=bool(args.measure),
        sample_count=len(raw), warmup_count=len(warmups), configurations=len(configurations),
        protocol=dict(samples=args.samples, warmups=args.warmups, seed=args.seed, threads=args.threads,
                      timer='CLOCK_MONOTONIC; per-call mean within external process; first worker initialization included',
                      oracle='Formula per element; long-double sum oracle; every timed process validates outside timer',
                      bootstrap='5000 paired complete-round percentile resamples; seed shared with collection; n>=15',
                      gcc_baseline='Original source -O3 -ftree-parallelize-loops=p; identical compiler to original and pipeline; flag is not proof of actual parallelization' if args.gcc_baseline else None,
                      limitations=['Controlled authored corpus; convenience selection, no population inference.',
                                   'Development/test split is fixed but author designed both; not an untouched external benchmark.',
                                   'Correctness applies to deterministic tested inputs; not a proof, race detector, or runtime restrict check.',
                                   'Bootstrap assumes sufficient stationarity; does not establish between-session reproducibility.']))
    write_json(directory / 'report.json', result)
    # Relative hashes cover all generated evidence without depending on absolute paths.
    manifest = [archive_record(directory, path) for path in sorted(directory.rglob('*')) if path.is_file()]
    write_json(directory / 'archive_manifest.json', manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=CATALOG)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compiler', dest='cc', default='clang')
    parser.add_argument('--gcc-baseline', help='GCC executable, must resolve to the same executable as --compiler')
    parser.add_argument('--threads', type=int, nargs='+', default=[1, 2, 4])
    parser.add_argument('--case', nargs='+')
    parser.add_argument('--measure', action='store_true')
    parser.add_argument('--verify', action='store_true', help='Verify a completed archive; never execute archived binaries.')
    parser.add_argument('--samples', type=int, default=15)
    parser.add_argument('--warmups', type=int, default=3)
    parser.add_argument('--seed', type=int, default=2026)
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify_archive(args.output), ensure_ascii=False, indent=2))
        return 0
    if (min(args.threads) < 1 or len(set(args.threads)) != len(args.threads) or 1 not in args.threads
            or args.samples < 1 or args.warmups < 0):
        parser.error('Use distinct positive threads including 1, samples>=1 and warmups>=0.')
    if args.gcc_baseline and (not shutil.which(args.gcc_baseline) or not shutil.which(args.cc)
            or Path(shutil.which(args.gcc_baseline)).resolve() != Path(shutil.which(args.cc)).resolve()):
        parser.error('GCC baseline and pipeline must use the identical compiler executable.')
    preexisting = args.output.exists()
    try:
        return run(args)
    except (OSError, RuntimeError, ValueError) as error:
        if not preexisting and args.output.is_dir():
            write_json(args.output / 'report.json', dict(schema='tcc2-automation-corpus-evaluation', status='FAILED', reason=str(error)))
        raise


if __name__ == '__main__':
    sys.exit(main())
