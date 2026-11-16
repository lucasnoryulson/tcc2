"""Paired, archived OpenMP scaling measurements; no LLM or promotion involved."""

import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import shutil
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark import BENCHMARKS, POLYBENCH_ROOT, openmp_environment, parse_key_values


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def numeric_result(output):
    values = parse_key_values(output)
    actual, expected = float(values['result']), float(values['expected'])
    if not all(map(math.isfinite, (actual, expected))) or not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-12):
        raise ValueError(f"Incorrect Dot Product: {actual}, expected {expected}")
    seconds = float(values['run_ms']) / 1000
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Nonpositive/nonfinite timer")
    return seconds


def numeric_c_result(output, n):
    values = parse_key_values(output)
    period = [(i % 1000) / 1000 * ((i * 7) % 1000) / 1000 for i in range(1000)]
    expected = (n // 1000) * math.fsum(period) + math.fsum(period[:n % 1000])
    result = float(values['RESULT'])
    seconds = float(values['AVERAGE_SECONDS'])
    if not math.isfinite(result) or not math.isclose(result, expected, rel_tol=1e-9, abs_tol=1e-12):
        raise ValueError(f'Incorrect automatic Dot C: {result}, expected {expected}')
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('Nonpositive/nonfinite Dot C timer')
    return seconds


def summarize(rows):
    result = []
    keys = sorted({(r['kernel'], r['size'], r['variant'], r['threads']) for r in rows})
    medians = {key: statistics.median(r['seconds'] for r in rows if
               (r['kernel'], r['size'], r['variant'], r['threads']) == key) for key in keys}
    for kernel, size, variant, threads in keys:
        key = kernel, size, variant, threads
        values = [r['seconds'] for r in rows if (r['kernel'], r['size'], r['variant'], r['threads']) == key]
        median = medians[key]
        seq = medians[kernel, size, 'sequential', 1]
        one = medians[kernel, size, variant, 1]
        result.append(dict(kernel=kernel, size=size, variant=variant, threads=threads,
                           samples=len(values), median_seconds=median, mean_seconds=statistics.mean(values),
                           stdev_seconds=statistics.stdev(values) if len(values) > 1 else 0,
                           min_seconds=min(values), max_seconds=max(values),
                           speedup_total=seq / median, speedup_transformation=seq / one,
                           speedup_parallel=one / median, efficiency_parallel=one / median / threads))
    return result


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class Campaign:
    def __init__(self, directory, timeout):
        self.directory, self.timeout, self.count = directory, timeout, 0

    def run(self, command, threads=1, dump=False, check=True):
        self.count += 1
        env = openmp_environment(threads)
        # Remove inherited OpenMP tuning so the recorded policy is reproducible.
        for name in list(env):
            if name.startswith(('OMP_', 'KMP_', 'GOMP_')) and name not in ('OMP_NUM_THREADS', 'OMP_DYNAMIC', 'OMP_PROC_BIND', 'OMP_PLACES'):
                del env[name]
        started = datetime.now(timezone.utc).isoformat()
        before = time.monotonic()
        try:
            result = subprocess.run(list(map(str, command)), capture_output=True, env=env, timeout=self.timeout)
            stdout, stderr, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as error:
            stdout, stderr, code = error.stdout or b'', error.stderr or b'', None
        record = dict(command=list(map(str, command)), started_utc=started,
                      wall_seconds=time.monotonic() - before, threads=threads, returncode=code,
                      openmp_environment={k: env[k] for k in ('OMP_NUM_THREADS', 'OMP_DYNAMIC', 'OMP_PROC_BIND', 'OMP_PLACES')})
        for name, data in [('stdout', stdout), ('stderr', stderr)]:
            path = self.directory / 'logs' / f'{self.count:05d}.{name}'
            if dump:
                path = path.with_suffix(path.suffix + '.gz')
                with gzip.open(path, 'wb') as stream:
                    stream.write(data)
            else:
                path.write_bytes(data)
            record[name] = dict(path=str(path.relative_to(self.directory)), sha256=digest(data), bytes=len(data))
        with (self.directory / 'commands.jsonl').open('a') as stream:
            stream.write(json.dumps(record) + '\n')
        if check and code != 0:
            raise RuntimeError(f"Command {self.count} failed ({code}): {command}; see commands.jsonl")
        return stdout.decode(errors='replace'), stderr, self.count


def capture_environment(campaign, args):
    info = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(),
                machine=platform.machine(), python=sys.version, cpu_count=os.cpu_count(),
                affinity=sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
                inherited_tuning={k: v for k, v in os.environ.items() if k.startswith(('OMP_', 'KMP_', 'GOMP_'))},
                arguments=vars(args) | {'output': str(args.output)})
    commands = [['git', 'rev-parse', 'HEAD'], ['git', 'status', '--short'], ['git', 'diff'],
                ['git', 'submodule', 'status'], [args.cc, '--version'], [args.cxx, '--version'],
                ['uname', '-a']]
    info['compilers'] = {}
    for compiler in (args.cc, args.cxx):
        path = Path(shutil.which(compiler) or compiler).resolve(strict=True)
        info['compilers'][compiler] = dict(path=str(path), sha256=digest(path.read_bytes()))
    if platform.system() == 'Linux':
        commands += [['lscpu'], ['free', '-h'], ['uptime']]
        for path in ('/proc/meminfo', '/proc/loadavg', '/sys/fs/cgroup/cpu.max', '/sys/fs/cgroup/cpuset.cpus.effective'):
            if Path(path).exists():
                info[path] = Path(path).read_text()
        info['frequency_governors'] = {str(p): p.read_text().strip() for p in Path('/sys/devices/system/cpu').glob('cpu*/cpufreq/scaling_governor')}
    elif platform.system() == 'Darwin':
        commands += [['sw_vers'], ['sysctl', 'hw.model', 'hw.memsize', 'hw.ncpu', 'hw.perflevel0.physicalcpu', 'hw.perflevel1.physicalcpu'], ['pmset', '-g', 'batt']]
    for command in commands:
        if shutil.which(command[0]):
            stdout, _, _ = campaign.run(command, check=False)
            info[' '.join(command)] = stdout.strip()
    write_json(campaign.directory / 'environment.json', info)


def execute(args):
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    for child in ('logs', 'sources', 'bin'):
        (directory / child).mkdir()
    campaign = Campaign(directory, args.timeout)
    warmups = getattr(args, 'warmups', 1)
    report = dict(status='RUNNING', protocol='multiplatform-v2', started_utc=datetime.now(timezone.utc).isoformat(),
                  attribution='Dot C generated by the deterministic transformer; other variants are manual or pre-existing specific adaptations. No LLM inference.',
                  repetitions=args.repetitions, warmups=warmups, warmup_runs=[], inputs=[],
                  seed=args.seed, threads=args.threads, correctness=[], sources=[])
    write_json(directory / 'report.json', report)
    samples = []
    try:
        capture_environment(campaign, args)
        probe_source = directory / 'sources' / 'openmp_probe.c'
        probe_source.write_text('#include <omp.h>\n#include <stdio.h>\nint main(void) {\n#pragma omp parallel\n{\n#pragma omp single\nprintf("%d\\n", omp_get_num_threads());\n}\n}\n')
        probe = directory / 'bin' / 'openmp_probe'
        campaign.run([args.cc, '-O3', '-fopenmp', probe_source, '-o', probe])
        report['actual_team_sizes_probe'] = {}
        for threads in args.threads:
            stdout, _, _ = campaign.run([probe], threads)
            actual = int(stdout.strip())
            report['actual_team_sizes_probe'][str(threads)] = actual
            if actual != threads:
                raise ValueError(f'OpenMP probe started {actual}, requested {threads}')
        saved = {}

        def snapshot(path):
            path = path.resolve()
            if path not in saved:
                target = path if path.is_relative_to(directory / 'sources') else directory / 'sources' / path.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                if path != target:
                    shutil.copyfile(path, target)
                saved[path] = target
                origin = path.relative_to(directory) if path.is_relative_to(directory) else path.relative_to(ROOT)
                report['sources'].append(dict(original=str(origin), snapshot=str(target.relative_to(directory)), sha256=digest(target.read_bytes())))
            return saved[path]

        snapshot(Path(__file__))
        snapshot(ROOT / 'scripts/benchmark.py')
        snapshot(probe_source)
        if 'dot-auto' in args.kernels:
            original_c = snapshot(ROOT / 'analysis/fixtures/dot_product.c')
            analysis = directory / 'generated_analysis'
            for script, arguments in [
                ('static_analyzer.py', [original_c, '--output-dir', analysis]),
                ('dependence_analyzer.py', [analysis / 'dot_product_analysis.json']),
                ('pattern_classifier.py', [analysis / 'dot_product_analysis.json', analysis / 'dot_product_dependences.json']),
                ('strategy_planner.py', [analysis / 'dot_product_analysis.json', analysis / 'dot_product_patterns.json']),
                ('code_transformer.py', [original_c, analysis / 'dot_product_analysis.json',
                                         analysis / 'dot_product_strategy.json', '--output', directory / 'sources/generated/dot_auto.c']),
            ]:
                snapshot(ROOT / 'analysis' / script)
                # Tools locate house imports relative to the repository, so execute the original captured script.
                campaign.run([sys.executable, '-B', ROOT / 'analysis' / script, *arguments])
        for wrapper in ('benchmark_multiplatform.py', 'run_multiplatform_linux.sh', 'run_multiplatform_mac.sh'):
            if (ROOT / 'scripts' / wrapper).exists():
                snapshot(ROOT / 'scripts' / wrapper)
        for kernel in args.kernels:
            standalone = kernel in ('dot', 'dot-auto')
            config = BENCHMARKS['dot' if kernel == 'dot-auto' else kernel]
            variants = ({'sequential': original_c, 'automatic': directory / 'sources/generated/dot_auto.c'}
                        if kernel == 'dot-auto' else {'sequential': config['original'], 'manual': config['candidate']})
            if kernel == 'nussinov':
                variants |= {'simd_manual': ROOT / 'kernels/nussinov/simd_openmp.c',
                             'simd_auto': BENCHMARKS['nussinov-auto']['candidate']}
            sizes = (args.dot_sizes if kernel == 'dot' else getattr(args, 'auto_dot_sizes', [1024, 10000000])) if standalone else args.datasets
            for size in sizes:
                binaries, dumps = {}, {}
                if kernel == 'dot-auto':
                    template = snapshot(ROOT / 'analysis/fixtures/dot_benchmark_driver.c')
                    driver = directory / 'sources/generated' / f'dot_driver_{size}.c'
                    driver.write_text(template.read_text().replace('#define N 10000000', f'#define N {size}').replace(
                        '#define INNER_REPEATS 100', f'#define INNER_REPEATS {10000 if size <= 1024 else 100}'))
                    snapshot(driver)
                for variant, source in variants.items():
                    src = snapshot(source)
                    compiler = args.cxx if kernel == 'dot' else args.cc
                    flags = ['-O3'] + (['-std=c++14'] if kernel == 'dot' else [] if standalone else [f'-D{size}_DATASET'])
                    if variant != 'sequential':
                        flags.append('-fopenmp')
                    inputs = [str(src)]
                    if kernel == 'dot-auto':
                        inputs += [str(driver), '-lm']
                    elif not standalone:
                        for name in ('polybench.h', 'polybench.c'):
                            snapshot(POLYBENCH_ROOT / 'utilities' / name)
                        header_name = 'jacobi-2d' if kernel == 'jacobi-2d' else kernel
                        snapshot(config['include_dir'] / f'{header_name}.h')
                        # Full-precision floating dumps avoid accepting errors hidden by PolyBench's %.2f.
                        if kernel in ('gemm', 'jacobi-2d', 'covariance'):
                            header = saved[(config['include_dir'] / f'{header_name}.h').resolve()]
                            header.write_text(header.read_text().replace('%0.2lf ', '%.17g '))
                        utility = saved[(POLYBENCH_ROOT / 'utilities/polybench.c').resolve()]
                        flags += [f'-I{utility.parent}', f'-I{saved[(config["include_dir"] / f"{header_name}.h").resolve()].parent}']
                        inputs += [str(utility), '-lm']
                    if variant == 'sequential':
                        dimensions = {'N': size, 'DATA_TYPE': 'double'} if standalone else {}
                        if kernel == 'dot-auto':
                            dimensions['INNER_REPEATS'] = 10000 if size <= 1024 else 100
                        if not standalone:
                            macros, _, _ = campaign.run([compiler, *flags, '-dM', '-E', src])
                            dimensions = {parts[1]: ' '.join(parts[2:]) for line in macros.splitlines()
                                          if len(parts := line.split()) >= 3 and parts[1] in ('NI', 'NJ', 'NK', 'N', 'M', 'TSTEPS', 'DATA_TYPE')}
                        report['inputs'].append(dict(kernel=kernel, size=size, dimensions=dimensions))
                    binary = directory / 'bin' / f'{kernel}-{size}-{variant}'
                    binaries[variant] = binary
                    campaign.run([compiler, *flags, *([] if standalone else ['-DPOLYBENCH_TIME']), *inputs, '-o', binary])
                    if not standalone:
                        dumps[variant] = binary.with_name(binary.name + '-dump')
                        campaign.run([compiler, *flags, '-DPOLYBENCH_DUMP_ARRAYS', *inputs, '-o', dumps[variant]])
                    campaign.run(['otool', '-L', binary] if platform.system() == 'Darwin' else ['ldd', binary])
                configs = [(v, p) for v in variants for p in ([1] if v == 'sequential' else args.threads)]
                reference = None
                for variant, threads in configs:
                    binary = binaries[variant] if standalone else dumps[variant]
                    stdout, stderr, invocation = campaign.run([binary, *([str(size)] if kernel == 'dot' else [])], threads, dump=not standalone)
                    if kernel == 'dot':
                        numeric_result(stdout)
                    elif kernel == 'dot-auto':
                        numeric_c_result(stdout, size)
                    else:
                        if not stderr.startswith(b'==BEGIN DUMP_ARRAYS==') or b'==END   DUMP_ARRAYS==' not in stderr:
                            raise ValueError('Missing full-array dump')
                        if reference is None:
                            reference = stderr
                        if reference != stderr:
                            raise ValueError(f'Full-precision dump mismatch: {kernel} {size} {variant} {threads}T')
                    report['correctness'].append(dict(kernel=kernel, size=size, variant=variant, threads=threads, status='PASS', command=invocation,
                                                      mode='numeric_1e-9_1e-12' if standalone else 'full_precision_dump_exact'))
                rng = random.Random(args.seed)
                for repeat in range(1, warmups + 1):
                    order = configs.copy()
                    rng.shuffle(order)
                    for variant, threads in order:
                        _, _, invocation = campaign.run([binaries[variant], *([str(size)] if kernel == 'dot' else [])], threads)
                        report['warmup_runs'].append(dict(kernel=kernel, size=size, variant=variant, threads=threads,
                                                          repeat=repeat, command=invocation))
                for repeat in range(1, args.repetitions + 1):
                    order = configs.copy()
                    rng.shuffle(order)
                    for variant, threads in order:
                        stdout, _, invocation = campaign.run([binaries[variant], *([str(size)] if kernel == 'dot' else [])], threads)
                        seconds = numeric_result(stdout) if kernel == 'dot' else numeric_c_result(stdout, size) if kernel == 'dot-auto' else float(stdout.strip())
                        if not math.isfinite(seconds) or seconds <= 0:
                            raise ValueError('Nonpositive/nonfinite measurement')
                        row = dict(kernel=kernel, size=size, variant=variant, threads=threads, repeat=repeat, seconds=seconds, command=invocation)
                        samples.append(row)
                        with (directory / 'samples.jsonl').open('a') as stream:
                            stream.write(json.dumps(row) + '\n')
                    print(f'{kernel} {size}: block {repeat}/{args.repetitions}', flush=True)
        # Capture the bytes actually compiled, including the documented dump precision change.
        for record in report['sources']:
            record['snapshot_sha256'] = digest((directory / record['snapshot']).read_bytes())
        report['binaries'] = {str(p.relative_to(directory)): digest(p.read_bytes()) for p in (directory / 'bin').iterdir()}
        write_csv(directory / 'samples.csv', samples)
        summary = summarize(samples)
        write_csv(directory / 'summary.csv', summary)
        report.update(status='COMPLETE', measurements=len(samples), configurations=len(summary))
    except Exception as error:
        report.update(status='FAILED', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(directory / 'report.json', report)


def main(defaults=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New directory; existing paths are refused')
    parser.add_argument('--cc', default='clang')
    parser.add_argument('--cxx', default='clang++')
    parser.add_argument('--kernels', nargs='+', choices=['dot-auto', 'dot', 'gemm', 'nussinov', 'jacobi-2d', 'covariance'], default=['dot', 'gemm', 'nussinov'])
    parser.add_argument('--threads', nargs='+', type=int, default=[1, 2, 4])
    parser.add_argument('--dot-sizes', nargs='+', type=int, default=[1000000, 10000000])
    parser.add_argument('--auto-dot-sizes', nargs='+', type=int, default=[1024, 10000000])
    parser.add_argument('--datasets', nargs='+', choices=['MINI', 'SMALL', 'MEDIUM', 'LARGE', 'EXTRALARGE'], default=['MEDIUM', 'LARGE'])
    parser.add_argument('--repetitions', type=int, default=7)
    parser.add_argument('--warmups', type=int, default=1)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--timeout', type=int, default=600)
    parser.set_defaults(**(defaults or {}))
    args = parser.parse_args()
    for values in (args.threads, args.dot_sizes, args.auto_dot_sizes):
        if min(values) < 1 or len(values) != len(set(values)):
            parser.error('Sizes and threads must be distinct positive integers')
    if any(len(values) != len(set(values)) for values in (args.kernels, args.datasets)):
        parser.error('Do not repeat kernels or datasets')
    if max(args.auto_dot_sizes) > 2147483647 // 7:
        parser.error('Dot C input exceeds the existing driver integer-index limit')
    if 1 not in args.threads or args.repetitions < 2 or args.timeout < 1 or args.warmups < 1:
        parser.error('Include OpenMP 1T, at least two repetitions, and a positive timeout')
    execute(args)


if __name__ == '__main__':
    main()
