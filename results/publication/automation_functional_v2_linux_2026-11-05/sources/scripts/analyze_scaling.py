"""Verify an archived scaling campaign and render descriptive tables/figures."""
import argparse
import csv
import gzip
import json
import random
import statistics
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark_scaling import digest, numeric_c_result, summarize, write_csv, write_json
from scripts.consolidate_experiments import normalize
from analysis.performance_selector import select_configuration


def verify(directory):
    report = json.loads((directory / 'report.json').read_text())
    if report['status'] != 'COMPLETE':
        raise ValueError('Only COMPLETE campaigns can be analyzed')
    for source in report['sources']:
        if digest((directory / source['snapshot']).read_bytes()) != source['snapshot_sha256']:
            raise ValueError(f"Changed source: {source['snapshot']}")
    for path, expected in report['binaries'].items():
        if digest((directory / path).read_bytes()) != expected:
            raise ValueError(f'Changed binary: {path}')
    commands = [json.loads(line) for line in (directory / 'commands.jsonl').read_text().splitlines()]
    for command in commands:
        for name in ('stdout', 'stderr'):
            record = command[name]
            path = directory / record['path']
            data = gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes()
            if digest(data) != record['sha256'] or len(data) != record['bytes']:
                raise ValueError(f'Changed command output: {path}')
    rows = [json.loads(line) for line in (directory / 'samples.jsonl').read_text().splitlines()]
    seen = set()
    for row in rows:
        key = row['kernel'], row['size'], row['variant'], row['threads'], row['repeat']
        if key in seen or not 1 <= row['repeat'] <= report['repetitions']:
            raise ValueError('Duplicate or invalid repetition')
        seen.add(key)
        command = commands[row['command'] - 1]
        if command['returncode'] != 0 or command['threads'] != row['threads']:
            raise ValueError('Invalid measurement command')
        path = directory / command['stdout']['path']
        output = path.read_text()
        if row['kernel'] == 'dot':
            from scripts.benchmark_scaling import numeric_result
            seconds = numeric_result(output)
        elif row['kernel'] == 'dot-auto':
            seconds = numeric_c_result(output, row['size'])
        else:
            seconds = float(output.strip())
        if seconds != row['seconds']:
            raise ValueError('Sample does not match command output')
    summary = summarize(rows)
    if len(rows) != report['measurements'] or len(summary) != report['configurations']:
        raise ValueError('Incomplete measurements')
    expected = {(r['kernel'], r['size'], r['variant'], r['threads']) for r in summary}
    correct = {(r['kernel'], r['size'], r['variant'], r['threads']) for r in report['correctness'] if r['status'] == 'PASS'}
    if expected != correct or any(r['samples'] != report['repetitions'] for r in summary):
        raise ValueError('Missing correctness/repetitions')
    if 'warmup_runs' in report:
        counts = {key: set() for key in expected}
        for warm in report['warmup_runs']:
            key = warm['kernel'], warm['size'], warm['variant'], warm['threads']
            if key not in counts or warm['repeat'] in counts[key]:
                raise ValueError('Invalid/duplicate warm-up')
            command = commands[warm['command'] - 1]
            if command['returncode'] != 0 or command['threads'] != warm['threads']:
                raise ValueError('Failed warm-up')
            counts[key].add(warm['repeat'])
        if any(ids != set(range(1, report['warmups'] + 1)) for ids in counts.values()):
            raise ValueError('Missing warm-ups')
    with (directory / 'summary.csv').open() as stream:
        stored = list(csv.DictReader(stream))
    if stored != [{k: str(v) for k, v in row.items()} for row in summary]:
        raise ValueError('Summary differs from raw samples')
    return report, summary


def percentile(values, fraction):
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def enrich(summary, raw, resamples=5000, seed=2026):
    groups = {}
    for row in sorted(raw, key=lambda r: r['repeat']):
        groups.setdefault((row['kernel'], row['size'], row['variant'], row['threads']), []).append(row['seconds'])
    result = []
    for row in summary:
        row = dict(row)
        key = row['kernel'], row['size'], row['variant'], row['threads']
        values = groups[key]
        median = statistics.median(values)
        row.update(mad_seconds=statistics.median(abs(v - median) for v in values),
                   q1_seconds=percentile(values, .25), q3_seconds=percentile(values, .75))
        row['iqr_seconds'] = row['q3_seconds'] - row['q1_seconds']
        distributions = {name: [] for name in ('median_seconds', 'speedup_total', 'speedup_transformation', 'speedup_parallel', 'efficiency_parallel')}
        if len(values) >= 15:
            seq = groups[key[0], key[1], 'sequential', 1]
            one = groups[key[0], key[1], key[2], 1]
            rng = random.Random(seed)
            # A measurement block contains every configuration; resample whole block IDs together.
            for _ in range(resamples):
                indices = [rng.randrange(len(values)) for _ in values]
                tp = statistics.median(values[i] for i in indices)
                ts = statistics.median(seq[i] for i in indices)
                t1 = statistics.median(one[i] for i in indices)
                for name, value in zip(distributions, (tp, ts / tp, ts / t1, t1 / tp, t1 / tp / row['threads'])):
                    distributions[name].append(value)
        for name, values_ci in distributions.items():
            row[name + '_ci95_low'] = percentile(values_ci, .025) if values_ci else None
            row[name + '_ci95_high'] = percentile(values_ci, .975) if values_ci else None
        result.append(row)
    return result


def selections(summary):
    results = []
    for kernel, size, variant in sorted({(r['kernel'], r['size'], r['variant']) for r in summary if r['variant'] != 'sequential'}):
        rows = [dict(mode='sequential' if r['variant'] == 'sequential' else 'openmp',
                     threads=r['threads'], median_seconds=r['median_seconds'], mean_seconds=r['mean_seconds'])
                for r in summary if (r['kernel'], r['size']) == (kernel, size) and r['variant'] in ('sequential', variant)]
        selection = select_configuration(normalize(rows))
        results.append(dict(kernel=kernel, size=size, variant=variant, selection=selection))
    return results


def figures(summary, output, repetitions, choices):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    panels = sorted({(r['kernel'], str(r['size'])) for r in summary})
    files = []
    for metric, ylabel in [('median_seconds', 'Tempo do kernel (s)'),
                           ('speedup_total', 'Speedup total Tseq/Tₚ'),
                           ('speedup_parallel', 'Escalabilidade T₁/Tₚ'),
                           ('efficiency_parallel', 'Eficiência (T₁/Tₚ)/p')]:
        nrows = (len(panels) + 1) // 2
        fig, axes = plt.subplots(nrows, 2, figsize=(11, nrows * 3.4), squeeze=False)
        for ax, (kernel, size) in zip(axes.flat, panels):
            rows = [r for r in summary if r['kernel'] == kernel and str(r['size']) == size]
            for variant in sorted({r['variant'] for r in rows} - {'sequential'}):
                curve = sorted((r for r in rows if r['variant'] == variant), key=lambda r: r['threads'])
                x, y = [r['threads'] for r in curve], [r[metric] for r in curve]
                ax.plot(x, y, 'o-', label=variant)
                if all(r.get(metric + '_ci95_low') is not None for r in curve):
                    ax.vlines(x, [r[metric + '_ci95_low'] for r in curve],
                              [r[metric + '_ci95_high'] for r in curve], alpha=.7)
            threads = sorted({r['threads'] for r in rows})
            if metric == 'median_seconds':
                seq = next(r['median_seconds'] for r in rows if r['variant'] == 'sequential')
                ax.axhline(seq, color='black', linestyle=':', label='sequencial')
            elif metric == 'speedup_parallel':
                ax.plot(threads, threads, '--', color='gray', label='ideal homogêneo')
            elif metric == 'speedup_total':
                ax.axhline(1, color='gray', linestyle='--', label='sequencial')
            else:
                ax.axhline(1, color='gray', linestyle='--')
            ax.set(title=f'{kernel} — {size}', xlabel='Threads', ylabel=ylabel, xticks=threads)
            ax.grid(alpha=.25)
            ax.legend(fontsize=8)
        for ax in list(axes.flat)[len(panels):]:
            ax.set_visible(False)
        fig.suptitle(f'Medianas de {repetitions} amostras; barras = IC bootstrap percentil de 95%')
        fig.tight_layout()
        for extension in ('png', 'svg', 'pdf'):
            path = output / f'{metric}.{extension}'
            fig.savefig(path, dpi=160)
            files.append(path.name)
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, max(4, len(choices) * .4)))
    labels, recommended, fastest = [], [], []
    for choice in choices:
        selection = choice['selection']
        labels.append(f"{choice['kernel']} / {choice['size']} / {choice['variant']}")
        recommended.append((selection.get('recommended') or {}).get('threads', 0))
        candidates = [r for r in summary if (r['kernel'], r['size'], r['variant']) == (choice['kernel'], choice['size'], choice['variant'])]
        fastest.append(min(candidates, key=lambda r: r['median_seconds'])['threads'])
    positions = list(range(len(labels)))
    ax.barh([p - .17 for p in positions], recommended, height=.33, label='Selector (0 = sequencial)')
    ax.barh([p + .17 for p in positions], fastest, height=.33, label='Menor mediana OpenMP')
    ax.set(yticks=positions, yticklabels=labels, xlabel='Threads', title='Configuração medida e recomendação determinística')
    ax.legend()
    ax.grid(axis='x', alpha=.25)
    fig.tight_layout()
    for extension in ('png', 'svg', 'pdf'):
        path = output / f'recommended_configuration.{extension}'
        fig.savefig(path, dpi=160)
        files.append(path.name)
    plt.close(fig)
    return dict(matplotlib=matplotlib.__version__, files=files)


def analyze(directory, output, no_plots=False):
    report, summary = verify(directory)
    output.mkdir(parents=True, exist_ok=False)
    raw = [json.loads(line) for line in (directory / 'samples.jsonl').read_text().splitlines()]
    summary = enrich(summary, raw, seed=report['seed'])
    choices = selections(summary)
    write_csv(output / 'measurements.csv', summary)
    write_json(output / 'selection.json', choices)
    write_csv(output / 'selection.csv', [dict(kernel=c['kernel'], size=c['size'], variant=c['variant'],
              status=c['selection']['status'], recommended_threads=(c['selection'].get('recommended') or {}).get('threads'),
              recommended_seconds=(c['selection'].get('recommended') or {}).get('median_seconds')) for c in choices])
    method = dict(method='paired complete-block percentile bootstrap', resamples=5000, confidence=.95,
                  seed=report['seed'], minimum_samples=15, quartiles='linear interpolation, inclusive',
                  mad='median(abs(x - median(x))), unscaled', stdev='sample (n-1)',
                  caveat='Conditional on these blocks; stationarity/independence not established; no cross-machine pooling or multiple-comparison correction')
    write_json(output / 'statistics_method.json', method)
    plots = {} if no_plots else figures(summary, output, report['repetitions'], choices)
    write_json(output / 'verification.json', dict(status='VERIFIED_ARCHIVE', campaign=str(directory),
               analyzer_sha256=digest(Path(__file__).read_bytes()),
               report_sha256=digest((directory / 'report.json').read_bytes()),
               commands_sha256=digest((directory / 'commands.jsonl').read_bytes()),
               raw_samples_sha256=digest((directory / 'samples.jsonl').read_bytes()),
               configurations=report['configurations'], measurements=report['measurements'], plots=plots))
    lines = ['# Escalabilidade OpenMP — ' + directory.name, '',
             'Fonte: `' + str(directory) + '`. Fontes, binários e saídas conferidos por SHA-256; resumos recalculados das amostras.', '',
             f"{report['repetitions']} amostras externas; {report['warmups']} aquecimentos por configuração; blocos embaralhados (seed {report['seed']}).",
             'Dot C automático usa o transformador determinístico real; demais variantes são manuais ou adaptações específicas preexistentes. Não houve inferência LLM.', '',
             '| Kernel | Entrada | Variante | Threads | Mediana (s) | Mín.–máx. (s) | S total | S transf. | S paralelo | E paralela |',
             '|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for row in summary:
        r = row
        lines.append(f"| {r['kernel']} | {r['size']} | {r['variant']} | {r['threads']} | {r['median_seconds']:.9f} | {r['min_seconds']:.9f}–{r['max_seconds']:.9f} | {r['speedup_total']:.4f} | {r['speedup_transformation']:.4f} | {r['speedup_parallel']:.4f} | {r['efficiency_parallel']:.4f} |")
    lines += ['', 'S total = Tseq/Tp; S transf. = Tseq/T1 da mesma variante; S paralelo = T1/Tp; E paralela = (T1/Tp)/p.',
              'Os CSVs incluem MAD, IQR, desvio padrão amostral e IC percentil bootstrap de 95%, 5.000 reamostragens de blocos completos, seed 2026, para n ≥ 15.',
              'Os intervalos são condicionais a esta campanha; não comprovam estacionariedade nem significância entre plataformas.',
              'O probe confirma o tamanho das equipes no runtime, sem provar a localização de cada thread dos kernels.',
              'Validação de arrays usa binários de dump separados com os mesmos flags de otimização; não prova ausência de races.',
              'Tempos excluem inicialização dos arrays, compilação e inferência. O Dot C++ inclui a primeira inicialização OpenMP; o PolyBench inicializa a equipe no flush antes do timer.',
              'A coleta M5 equivalente ainda precisa ser executada; dados históricos não formam um experimento pareado com esta coleta.']
    if not no_plots:
        lines += ['', '![Tempos](median_seconds.png)', '', '![Speedup total](speedup_total.png)', '', '![Escalabilidade](speedup_parallel.png)', '', '![Eficiência](efficiency_parallel.png)', '', '![Configuração recomendada](recommended_configuration.png)']
    (output / 'REPORT.md').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campaign', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--no-plots', action='store_true')
    args = parser.parse_args()
    analyze(args.campaign.resolve(), args.output.resolve(), args.no_plots)
