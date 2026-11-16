"""Archive whole-process Linux perf counters without fabricating unavailable data."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.artifact_provenance import load_performance_report
from scripts.benchmark import openmp_environment
from scripts.benchmark_scaling import write_csv, write_json

CASES = [('dot-auto', '10000000', 'automatic'), ('gemm', 'LARGE', 'manual'),
         ('nussinov', 'LARGE', 'manual'), ('jacobi-2d', 'LARGE', 'manual'),
         ('covariance', 'LARGE', 'manual')]
EVENT_GROUPS = [('cpu', '{cycles,instructions}'), ('cache', '{cache-references,cache-misses}'),
                ('scheduler', 'context-switches,cpu-migrations')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_perf(text):
    """perf -x ';': keep raw columns and explicit not-supported/not-counted states."""
    values = []
    for row in csv.reader(text.splitlines(), delimiter=';'):
        if len(row) < 3 or row[0].lstrip().startswith('#'):
            continue
        raw, unit, event = (cell.strip() for cell in row[:3])
        if not event or event in ('seconds time elapsed', 'seconds user', 'seconds sys'):
            continue
        value, status = None, 'UNAVAILABLE'
        try:
            number = float(raw)
            if math.isfinite(number) and number >= 0:
                value, status = number, 'COUNTED'
        except ValueError:
            if 'not supported' in raw:
                status = 'NOT_SUPPORTED'
            elif 'not counted' in raw:
                status = 'NOT_COUNTED'
        values.append(dict(event=event, value=value, unit=unit, status=status,
                           raw_value=raw, raw_columns=row[3:]))
    return values


def ratios(values):
    # Do not combine PMU-specific, missing or separately executed events.
    counted = {r['event']: r['value'] for r in values if r['status'] == 'COUNTED'}
    def ratio(top, bottom):
        return counted[top] / counted[bottom] if top in counted and counted.get(bottom, 0) > 0 else None
    return dict(ipc=ratio('instructions', 'cycles'), cache_miss_fraction=ratio('cache-misses', 'cache-references'))


def resolve_targets(campaign, axpy_session=None):
    report = json.loads((campaign / 'report.json').read_text())
    if report.get('status') != 'COMPLETE':
        raise ValueError('Requires a complete input campaign')
    targets = []
    for kernel, size, variant in CASES:
        for mode in ('sequential', variant):
            relative = f'bin/{kernel}-{size}-{mode}'
            binary = campaign / relative
            expected = report.get('binaries', {}).get(relative)
            if not binary.is_file() or not expected:
                raise ValueError('Missing archived binary/hash: ' + relative)
            if sha(binary) != expected:
                raise ValueError('Changed archived binary: ' + relative)
            targets.append(dict(kernel=kernel, size=size, variant=mode, binary=binary.resolve(), sha256=expected))
    if axpy_session is not None:
        session = json.loads((axpy_session / 'report.json').read_text())
        if session.get('status') != 'COMPLETE':
            raise ValueError('Requires a complete AXPY session')
        entry = next((r for r in session['runs'] if r['n'] == 10000000), None)
        if entry is None:
            raise ValueError('AXPY largest input not found')
        work = axpy_session / entry['work']
        performance, _, _ = load_performance_report(work / 'performance.json', work / 'performance.csv')
        for mode, variant in [('sequential', 'sequential'), ('candidate', 'automatic')]:
            binary = Path(performance['binaries'][mode]['path'])
            targets.append(dict(kernel='axpy', size='10000000', variant=variant,
                                binary=binary, sha256=sha(binary)))
    return targets


def collect(args):
    if platform.system() != 'Linux':
        raise ValueError('Linux perf cannot be collected on this operating system')
    if shutil.which('perf') is None:
        raise ValueError('perf is not installed; no counters collected')
    if args.output.exists():
        raise FileExistsError('Output already exists; archives must not be overwritten')
    targets = resolve_targets(args.campaign.resolve(), args.axpy_session.resolve() if args.axpy_session else None)
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    (output / 'logs').mkdir()
    report = dict(schema='tcc2-linux-perf-v2', status='RUNNING',
        started_utc=datetime.now(timezone.utc).isoformat(), campaign=str(args.campaign.resolve()),
        campaign_report_sha256=sha(args.campaign / 'report.json'), threads=args.threads,
        repetitions=args.repetitions, axpy_included=args.axpy_session is not None, observations=[],
        scope='Whole process including initialization, validation and runtime, not kernel-only. '
              'IPC is ratio of paired perf means, not mean per-run IPC. '
              'Generic cache events do not measure DRAM bandwidth or prove a causal bottleneck.')
    if args.axpy_session:
        report['axpy_report_sha256'] = sha(args.axpy_session / 'report.json')
    write_json(output / 'report.json', report)
    commands = []
    def run(command, name, env=None):
        command = list(map(str, command))
        begin = time.perf_counter()
        try:
            result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=args.timeout)
            code, stdout, stderr = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as error:
            code = None
            stdout, stderr = error.stdout or b'', error.stderr or b''
            stdout = stdout.decode(errors='replace') if isinstance(stdout, bytes) else stdout
            stderr = stderr.decode(errors='replace') if isinstance(stderr, bytes) else stderr
            stderr += '\nTIMEOUT; no retry\n'
        (output / 'logs' / (name + '.stdout')).write_text(stdout)
        (output / 'logs' / (name + '.stderr')).write_text(stderr)
        commands.append(dict(command=command, returncode=code, wall_seconds=time.perf_counter() - begin,
            log=name, openmp_environment={k: v for k, v in (env or {}).items() if k.startswith('OMP_')}))
        write_json(output / 'commands.json', commands)
        return code
    for name, command in [('perf_version', ['perf', '--version']), ('perf_list', ['perf', 'list']),
                          ('lscpu', ['lscpu']), ('uname', ['uname', '-a']),
                          ('compiler', [args.compiler, '--version'])]:
        run(command, name)
    environment = dict(affinity=sorted(os.sched_getaffinity(0)), python=sys.version, platform=platform.platform(),
        inherited_tuning={k: v for k, v in os.environ.items() if k.startswith(('OMP_', 'KMP_', 'GOMP_'))})
    for file in ('/proc/sys/kernel/perf_event_paranoid', '/proc/meminfo', '/proc/loadavg', '/sys/fs/cgroup/cpu.max'):
        if Path(file).is_file():
            environment[file] = Path(file).read_text()
    write_json(output / 'environment.json', environment)
    rows = []
    groups = EVENT_GROUPS + [(f'memory{i}', event) for i, event in enumerate(args.memory_event)]
    for target in targets:
        for threads in ([1] if target['variant'] == 'sequential' else args.threads):
            environment = openmp_environment(threads)
            environment['LC_ALL'] = 'C'
            for key in list(environment):
                if key.startswith(('OMP_', 'KMP_', 'GOMP_')) and key not in ('OMP_NUM_THREADS', 'OMP_DYNAMIC', 'OMP_PROC_BIND', 'OMP_PLACES'):
                    del environment[key]
            for group, events in groups:
                name = f"{target['kernel']}-{target['variant']}-{threads}T-{group}"
                counters = output / (name + '.perf.csv')
                command = ['perf', 'stat', '--no-big-num', '-x', ';', '-r', str(args.repetitions),
                           '-e', events, '-o', str(counters), '--', str(target['binary'])]
                code = run(command, name, environment)
                values = parse_perf(counters.read_text()) if counters.exists() else []
                observation = dict(kernel=target['kernel'], size=target['size'], variant=target['variant'],
                    threads=threads, binary=str(target['binary']), binary_sha256=target['sha256'], group=group,
                    requested_events=events, returncode=code, counters=values,
                    status='COUNTED' if code == 0 and values and all(r['status'] == 'COUNTED' for r in values) else 'UNAVAILABLE',
                    ratios=ratios(values) if code == 0 else dict(ipc=None, cache_miss_fraction=None))
                report['observations'].append(observation)
                for value in values:
                    rows.append({k: observation[k] for k in ('kernel', 'size', 'variant', 'threads', 'group')} |
                                {k: value[k] for k in ('event', 'value', 'unit', 'status')})
                if sha(target['binary']) != target['sha256']:
                    raise ValueError('Measured binary changed during collection')
                write_json(output / 'report.json', report)
    if rows:
        write_csv(output / 'counters.csv', rows)
    report.update(status='COMPLETE' if args.axpy_session and all(o['status'] == 'COUNTED' for o in report['observations']) else 'PARTIAL',
                  finished_utc=datetime.now(timezone.utc).isoformat())
    write_json(output / 'report.json', report)
    for source in ('profile_linux_followup.py', 'profile_linux_followup.sh'):
        shutil.copyfile(ROOT / 'scripts' / source, output / source)
    write_json(output / 'archive_manifest.json', [dict(path=str(p.relative_to(output)), sha256=sha(p))
        for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'archive_manifest.json'])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campaign', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--axpy-session', type=Path)
    parser.add_argument('--threads', nargs='+', type=int, default=[1, 2, 4])
    parser.add_argument('--repetitions', type=int, default=5)
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--compiler', default='clang')
    parser.add_argument('--memory-event', action='append', default=[], help='Explicit supported PMU event from perf list')
    args = parser.parse_args()
    if (args.repetitions < 1 or args.timeout < 1 or min(args.threads) < 1
        or len(set(args.threads)) != len(args.threads) or any(';' in e for e in args.memory_event)):
        parser.error('Use positive counts, distinct threads and valid event names')
    result = collect(args)
    print(result['status'])
    return 0 if result['status'] == 'COMPLETE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
