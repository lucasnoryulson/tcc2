"""Measure worker compute/barrier intervals in separate instrumented kernel copies."""
import argparse
import gzip
import json
from pathlib import Path
import random
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark_scaling import Campaign, digest, write_csv, write_json


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Instrumentation expects exactly one source anchor: ' + old[:100])
    return source.replace(old, new)


def instrument(source, kernel):
    declarations = ('\n#include <omp.h>\nstatic double tcc_work[64], tcc_wait[64];\n'
                    'static unsigned long long tcc_items[64];\n'
                    'static void tcc_profile_print(void) {\n'
                    ' for (int t=0; t<omp_get_max_threads(); ++t)\n'
                    '  fprintf(stderr,"TCC2_PROFILE %d %llu %.17g %.17g\\n", t, tcc_items[t], tcc_work[t], tcc_wait[t]);\n}\n')
    source = replace_once(source, '#include <math.h>', '#include <math.h>' + declarations)
    start = 'int tid=omp_get_thread_num(); double tcc_start=omp_get_wtime();\n'
    barrier = ('\ntcc_work[tid] += omp_get_wtime()-tcc_start;\n'
               'tcc_start=omp_get_wtime();\n#pragma omp barrier\n'
               'tcc_wait[tid] += omp_get_wtime()-tcc_start;\n'
               'tcc_start=omp_get_wtime();\n')
    if kernel == 'covariance':
        marker = '#pragma omp for schedule(static)\n  for (i = 0; i < _PB_M; i++)'
        source = replace_once(source, marker, start + marker.replace('schedule(static)', 'schedule(static) nowait'))
        source = replace_once(source, 'cov[i][j] = SCALAR_VAL(0.0);', '++tcc_items[tid];\n        cov[i][j] = SCALAR_VAL(0.0);')
        source = replace_once(source, 'cov[j][i] = cov[i][j];\n      }\n}', 'cov[j][i] = cov[i][j];\n      }\n' + barrier + '}')
    elif kernel == 'nussinov':
        source = replace_once(source, 'for (d = 1; d < _PB_N; d++) {',
                              'int tid=omp_get_thread_num(); double tcc_start;\n        for (d = 1; d < _PB_N; d++) {\n tcc_start=omp_get_wtime();')
        source = replace_once(source, '#pragma omp for schedule(static)', '#pragma omp for schedule(static) nowait')
        source = replace_once(source, 'j = i + d;', '++tcc_items[tid];\n                j = i + d;')
        marker = '            /*\n             * IMPORTANT:'
        source = replace_once(source, marker, barrier + marker)
    elif kernel == 'jacobi-2d':
        source = replace_once(source, '  for (t = 0; t < _PB_TSTEPS; t++)', start + '  for (t = 0; t < _PB_TSTEPS; t++)')
        source = source.replace('#pragma omp for schedule(static)', '#pragma omp for schedule(static) nowait')
        source = replace_once(source, 'A[1+i][j] + A[i-1][j]);', 'A[1+i][j] + A[i-1][j]);' + barrier)
        source = replace_once(source, 'B[1+i][j] + B[i-1][j]);', 'B[1+i][j] + B[i-1][j]);' + barrier)
    else:
        raise ValueError(kernel)
    source = replace_once(source, '#pragma endscop', 'tcc_profile_print();\n#pragma endscop')
    return source


def run(args):
    archive = args.campaign.resolve()
    report = json.loads((archive / 'report.json').read_text())
    if report['status'] != 'COMPLETE':
        raise ValueError('A complete source campaign is required')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    for name in ('logs', 'sources', 'bin'):
        (output / name).mkdir()
    campaign = Campaign(output, 600)
    rows, checks, sources = [], [], []
    for kernel in ('nussinov', 'jacobi-2d', 'covariance'):
        old = archive / 'sources/kernels' / kernel / 'manual_openmp.c'
        measured = next(s for s in report['sources'] if s['snapshot'] == str(old.relative_to(archive)))
        if digest(old.read_bytes()) != measured['snapshot_sha256']:
            raise ValueError('Source identity changed')
        source = output / 'sources' / f'{kernel}_profile.c'
        source.write_text(instrument(old.read_text(), kernel))
        sources.append(dict(original_sha256=digest(old.read_bytes()), instrumented=str(source.relative_to(output)), sha256=digest(source.read_bytes())))
        header_dir = archive / 'sources/benchmarks/PolyBenchC-4.2.1' / ('medley/nussinov' if kernel == 'nussinov' else 'stencils/jacobi-2d' if kernel == 'jacobi-2d' else 'datamining/covariance')
        utilities = archive / 'sources/benchmarks/PolyBenchC-4.2.1/utilities'
        for size in ('MEDIUM', 'LARGE'):
            binary = output / 'bin' / f'{kernel}-{size}'
            flags = ['-O3', '-fopenmp', f'-D{size}_DATASET', '-DPOLYBENCH_TIME', '-DPOLYBENCH_DUMP_ARRAYS']
            campaign.run([args.compiler, *flags, f'-I{header_dir}', f'-I{utilities}', source, utilities / 'polybench.c', '-lm', '-o', binary])
            correctness = next(c for c in report['correctness'] if c['kernel'] == kernel and c['size'] == size and c['variant'] == 'sequential')
            commands = [json.loads(s) for s in (archive / 'commands.jsonl').read_text().splitlines()]
            refpath = archive / commands[correctness['command']-1]['stderr']['path']
            reference = gzip.decompress(refpath.read_bytes()) if refpath.suffix == '.gz' else refpath.read_bytes()
            order = [(repeat, p) for repeat in range(1, 4) for p in (1, 4, 10)]
            random.Random(2026).shuffle(order)
            for repeat, threads in order:
                _, stderr, invocation = campaign.run([binary], threads, dump=True)
                clean = b'\n'.join(line for line in stderr.split(b'\n') if not line.startswith(b'TCC2_PROFILE '))
                if clean != reference:
                    raise ValueError(f'Instrumented dump differs: {kernel} {size} {threads}')
                checks.append(dict(kernel=kernel, size=size, threads=threads, repeat=repeat, status='PASS', command=invocation))
                for tid, items, compute, wait in re.findall(rb'TCC2_PROFILE (\d+) (\d+) (\S+) (\S+)', stderr):
                    rows.append(dict(kernel=kernel, size=size, threads=threads, repeat=repeat, worker=int(tid),
                                     assigned_items=int(items), compute_seconds=float(compute), barrier_seconds=float(wait), command=invocation))
    write_csv(output / 'workers.csv', rows)
    write_json(output / 'report.json', dict(status='COMPLETE', source_campaign=str(archive), sources=sources, correctness=checks,
        protocol='Three instrumented observations per MEDIUM/LARGE and 1/4/10T; no pooling with primary campaign',
        scope='Covariance: triangular phase only; Nussinov: all diagonals; Jacobi: two spatial sweeps per timestep',
        limitations='Clock reads, counters, explicit barriers and output change code; wall intervals include scheduling and imbalance. No cache or DRAM counters; worker IDs do not identify P/E cores.'))
    return dict(observations=len(checks), workers=len(rows))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compiler', default='/opt/homebrew/opt/llvm/bin/clang')
    print(json.dumps(run(parser.parse_args())))
