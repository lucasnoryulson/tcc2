"""Describe separate same-platform sessions without pooling their raw samples."""
import argparse
import csv
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analyze_scaling import verify, selections
from scripts.benchmark_scaling import digest, write_csv, write_json
from scripts.compare_multiplatform import compile_flags


def identity(row):
    return row['kernel'], str(row['size']), row['variant'], int(row['threads'])


def platform_identity(environment):
    fields = {'Architecture', 'CPU(s)', 'Model name', 'Thread(s) per core',
              'Core(s) per socket', 'Socket(s)', 'L1d cache', 'L1i cache', 'L2 cache', 'L3 cache'}
    cpu = {key.strip(): value.strip() for line in environment.get('lscpu', '').splitlines()
           if ':' in line for key, value in [line.split(':', 1)] if key.strip() in fields}
    apple = {key: value for key, value in environment.items() if key.startswith('sysctl ')}
    return {k: environment.get(k) for k in ('machine', 'platform', 'affinity', 'compilers')} | {'cpu': cpu, 'apple_hardware': apple}


def summarize_sessions(summaries):
    if len(summaries) < 2:
        raise ValueError('At least two separately named sessions are required')
    by_session = [{identity(r): r for r in rows} for rows in summaries]
    common = set.intersection(*(set(rows) for rows in by_session))
    if not common:
        raise ValueError('No common measured configurations')
    rows = []
    for key in sorted(common):
        medians = [group[key]['median_seconds'] for group in by_session]
        average = statistics.mean(medians)
        row = dict(zip(('kernel', 'size', 'variant', 'threads'), key))
        row.update(sessions=len(medians), minimum_session_median=min(medians),
                   maximum_session_median=max(medians), mean_session_median=average,
                   sample_sd_session_medians=statistics.stdev(medians),
                   cv_session_medians=statistics.stdev(medians) / average,
                   maximum_over_minimum=max(medians) / min(medians))
        row.update({f'session_{i + 1}_median': value for i, value in enumerate(medians)})
        rows.append(row)
    return rows


def compare(paths, output, no_plots=False):
    paths = [p.resolve() for p in paths]
    if len(set(paths)) != len(paths):
        raise ValueError('Repeated archive paths are not independent sessions')
    archives = [verify(p) for p in paths]
    reference, reference_rows = archives[0]
    environment = json.loads((paths[0] / 'environment.json').read_text())
    base_code = {s['original']: s['snapshot_sha256'] for s in reference['sources']
                 if Path(s['original']).suffix in ('.c', '.h', '.cpp')}
    base_flags = compile_flags(paths[0])
    for path, (report, other_rows) in zip(paths[1:], archives[1:]):
        for field in ('protocol', 'repetitions', 'warmups', 'seed', 'threads'):
            if report[field] != reference[field]:
                raise ValueError(f'Incompatible session {field}: {path}')
        other_environment = json.loads((path / 'environment.json').read_text())
        if platform_identity(other_environment) != platform_identity(environment):
            raise ValueError(f'Different compiler/platform identity: {path}')
        code = {s['original']: s['snapshot_sha256'] for s in report['sources']
                if Path(s['original']).suffix in ('.c', '.h', '.cpp')}
        if base_code != code:
            raise ValueError(f'Different compiled source/header identities or bytes: {path}')
        flags = compile_flags(path)
        common = {identity(r) for r in reference_rows} & {identity(r) for r in other_rows}
        common_inputs = {(kernel, size) for kernel, size, _, _ in common}
        def inputs(data):
            found = {(r['kernel'], str(r['size'])): r for r in data['inputs']}
            if not common_inputs <= found.keys():
                raise ValueError('Missing measured input identity.')
            return {key: found[key] for key in common_inputs}
        if inputs(reference) != inputs(report):
            raise ValueError(f'Different common measured dimensions: {path}')
        required_binaries = {f'{kernel}-{size}-{variant}' for kernel, size, variant, _ in common}
        if not required_binaries <= base_flags.keys() & flags.keys():
            raise ValueError('Missing compilation flags for common configurations.')
        if any(base_flags[k] != flags[k] for k in base_flags.keys() & flags.keys()):
            raise ValueError(f'Different shared compilation flags: {path}')
    summaries = [rows for _, rows in archives]
    table = summarize_sessions(summaries)
    output.mkdir(parents=True, exist_ok=False)
    write_csv(output / 'session_medians.csv', table)
    choices = []
    for path, (report, summary) in zip(paths, archives):
        for row in selections(summary):
            selected = row['selection'].get('recommended') or {}
            choices.append(dict(session=path.name, kernel=row['kernel'], size=row['size'],
                                variant=row['variant'], recommended_threads=selected.get('threads'),
                                status=row['selection']['status']))
    write_csv(output / 'session_selections.csv', choices)
    provenance = [dict(path=str(p), report_sha256=digest((p / 'report.json').read_bytes()),
                       samples_sha256=digest((p / 'samples.jsonl').read_bytes()),
                       started_utc=r['started_utc'], finished_utc=r['finished_utc'],
                       configurations=r['configurations'], measurements=r['measurements'])
                  for p, (r, _) in zip(paths, archives)]
    write_json(output / 'report.json', dict(status='VERIFIED_SEPARATE_SESSIONS', sessions=provenance,
               common_configurations=len(table), method='Descriptive variation of session medians; no pooled raw observations',
               limitation='Same machine and day; sequential sessions do not establish independence or controlled thermals',
               analyzer_sha256=digest(Path(__file__).read_bytes())))
    lines = ['# Repetibilidade entre sessões Linux', '',
             f'{len(paths)} coletas separadas; {len(table)} configurações comuns. Cada mediana conserva as quinze observações da sua própria sessão.', '',
             'Não se agrupam amostras nem se estima um IC populacional com apenas estas sessões. O CV abaixo descreve as medianas observadas; não identifica uma causa para sua mudança.', '',
             '| Caso / entrada / variante / threads | Medianas por sessão (s) | Máximo/mínimo | CV das medianas |',
             '|---|---|---:|---:|']
    for row in table:
        name = ' / '.join(str(row[k]) for k in ('kernel', 'size', 'variant', 'threads'))
        times = '; '.join(f"{row[f'session_{i + 1}_median']:.6g}" for i in range(len(paths)))
        lines.append(f"| {name} | {times} | {row['maximum_over_minimum']:.4f} | {row['cv_session_medians']:.4f} |")
    lines += ['', 'As recomendações de cada sessão estão em session_selections.csv. As curvas do M5 permanecem pendentes. Sessões do mesmo dia/host não são máquinas independentes e não tornam frequência ou temperatura controladas.', '']
    (output / 'REPORT.md').write_text('\n'.join(lines))
    if not no_plots:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, max(5, len(table) * .21)))
        for index, path in enumerate(paths):
            ratios = [r[f'session_{index + 1}_median'] / r['session_1_median'] for r in table]
            ax.plot(ratios, range(len(table)), 'o', markersize=4, label=path.name)
        ax.set_yticks(range(len(table)), [' / '.join(str(r[k]) for k in ('kernel', 'size', 'variant', 'threads')) for r in table], fontsize=7)
        ax.axvline(1, color='gray', linestyle='--')
        ax.set_xlabel('Mediana da mesma configuração / mediana da primeira sessão')
        ax.set_title('Sessões separadas; valores descritivos, sem agrupamento de amostras')
        ax.grid(alpha=.2)
        ax.legend(fontsize=7)
        fig.tight_layout()
        for extension in ('png', 'svg', 'pdf'):
            fig.savefig(output / f'session_variation.{extension}', dpi=180)
        plt.close(fig)
    return dict(sessions=len(paths), common_configurations=len(table))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campaigns', nargs='+', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--no-plots', action='store_true')
    args = parser.parse_args()
    print(json.dumps(compare(args.campaigns, args.output, args.no_plots)))
