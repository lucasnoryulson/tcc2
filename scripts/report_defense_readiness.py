"""Derive the defense-stage AXPY tables from intact, separate real archives."""
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analyze_pipeline_cost import break_even
from scripts.benchmark_scaling import write_csv, write_json
from scripts.build_axpy_material import sha, number
from scripts.evaluate_axpy_campaign import verify_session, seal

STUDY = ROOT / 'results/axpy_scientific/mac_m5_all_threads_2026-11-16'
ANALYSIS = ROOT / 'results/axpy_scientific/analysis_mac_m5_all_threads_2026-11-16'
COST = ROOT / 'results/pipeline_cost/axpy_mac_m5_all_threads_2026-11-16'


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def build(output):
    first, _, _, _ = verify_session(STUDY / 'session01')
    second, _, _, _ = verify_session(STUDY / 'session02')
    frozen = json.loads((STUDY / 'frozen_selection.json').read_text())
    protocol = json.loads((STUDY / 'protocol.json').read_text())
    if protocol['threads'] != list(range(1, 11)):
        raise ValueError('All integer team sizes 1..10 are required')
    freeze_time = datetime.fromisoformat(frozen['frozen_at_utc'])
    gap = (datetime.fromisoformat(second['started_utc']) - datetime.fromisoformat(first['finished_utc'])).total_seconds()
    if not datetime.fromisoformat(first['finished_utc']) < freeze_time < datetime.fromisoformat(second['started_utc']) or gap < 30:
        raise ValueError('Invalid freeze chronology or cooldown')
    cost = json.loads((COST / 'report.json').read_text())
    if cost['status'] not in ('COMPLETE', 'COMPLETE_WITH_FAILURES', 'INCOMPLETE_TIMEOUT'):
        raise ValueError('Cost trials must have finished before generating the report')
    output.mkdir(parents=True, exist_ok=False)
    measured = {i: rows(ANALYSIS / f'measurements_session{i:02d}.csv') for i in (1, 2)}
    policies = [r for r in rows(ANALYSIS / 'policies.csv') if r['policy'] == 'selector']
    stats = ['| N | Configuração congelada S1 | Mediana S1 (µs) | Média S1 (µs) | DP S1 (µs) | S total S1 [IC95%] | E paralela S1 |',
             '|---|---:|---:|---:|---:|---:|---:|']
    later = ['| N | Escolha S1 | Escolha S2 | S total da escolha congelada na S2 | Excesso sobre melhor S2 | Inadequada (>2%) |',
             '|---|---:|---:|---:|---:|---|']
    stability = rows(ANALYSIS / 'stability.csv')
    for choice in frozen['choices']:
        n = choice['size']
        selected = choice['selection'].get('recommended')
        p, variant = (selected['threads'], 'automatic') if selected else (1, 'sequential')
        label = f'{p}T' if selected else 'seq.'
        entry = next(r for r in measured[1] if (int(r['size']), r['variant'], int(r['threads'])) == (n, variant, p))
        interval = f"{number(entry['speedup_total'])} [{number(entry['speedup_total_ci95_low'])}; {number(entry['speedup_total_ci95_high'])}]"
        stats.append(f"| {n:,} | {label} | {number(float(entry['median_seconds'])*1e6, 4)} | "
            f"{number(float(entry['mean_seconds'])*1e6, 4)} | {number(float(entry['stdev_seconds'])*1e6, 4)} | "
            f"{interval} | {number(entry['efficiency_parallel']) if selected else '—'} |")
        policy = next(r for r in policies if int(r['size']) == n)
        stable = next(r for r in stability if int(r['size']) == n)
        s2 = 'seq.' if stable['holdout_sequential'] == 'True' else stable['holdout_threads'] + 'T'
        later.append(f"| {n:,} | {label} | {s2} | {number(policy['speedup_total'])} | "
                     f"{number(policy['regret_percent'])}% | {'Sim' if policy['inadequate']=='True' else 'Não'} |")
    totals = []
    for i in (1, 2):
        raw = rows(STUDY / f'session{i:02d}/samples.csv')
        warm = rows(STUDY / f'session{i:02d}/warmups.csv')
        for entry in measured[i]:
            n, p, variant = int(entry['size']), int(entry['threads']), entry['variant']
            repeats = next(r['inner_repeats'] for r in protocol['inputs'] if r['n'] == n)
            match = lambda r: (int(r['size']), int(r['threads']), r['variant']) == (n, p, variant)
            totals.append(dict(session=i, n=n, variant=variant, threads=p, inner_repeats=repeats,
                measured_kernel_seconds_reconstructed=sum(float(r['seconds'])*repeats for r in raw if match(r)),
                warmup_kernel_seconds_reconstructed=sum(float(r['seconds'])*repeats for r in warm if match(r))))
    write_csv(output / 'kernel_time_totals.csv', totals)
    wall = []
    for i, report in ((1, first), (2, second)):
        session = STUDY / f'session{i:02d}'
        timings = [json.loads(s) for s in (session / 'process_timings.jsonl').read_text().splitlines()]
        for entry in report['runs']:
            work = session / entry['work']
            summary = json.loads((work / 'summary.json').read_text())
            for step in summary['steps']:
                nested = [r for r in timings if r['stage'] == step['name'] and any(str(work) in c for c in r['command'])]
                wall.append(dict(session=i, n=entry['n'], stage=step['name'], inclusive_wall_seconds=step['wall_seconds'],
                    compilation_wall_seconds=sum(r['wall_seconds'] for r in nested if r['kind']=='compilation'),
                    execution_wall_seconds=sum(r['wall_seconds'] for r in nested if r['kind']=='execution')))
    write_csv(output / 'pipeline_stage_times.csv', wall)
    heldout = next(r for r in measured[2] if r['size']=='10000000' and r['variant']=='sequential')
    heldout_time = float(next(r for r in policies if r['size']=='10000000')['median_seconds'])
    costs = rows(COST / 'costs.csv')
    cost_rows = []
    for row in costs:
        accepted = row['promoted'] == 'True'
        optimized = heldout_time if accepted else float(heldout['median_seconds'])
        decision = float(row['decision_seconds']) + float(row['decision_validation_seconds'])
        total = float(row['total_accounted_seconds'])
        cost_rows.append(dict(repetition=int(row['repetition']), mode=row['mode'], status=row['status'],
            promoted=accepted, prefix_seconds=float(row['shared_prefix_seconds']), decision_validation_seconds=decision,
            promotion_seconds=float(row['promotion_seconds']), total_accounted_seconds=total,
            holdout_sequential_seconds=float(heldout['median_seconds']), holdout_final_seconds=optimized,
            decision_only_break_even=break_even(decision, float(heldout['median_seconds']), optimized),
            full_accounted_break_even=break_even(total, float(heldout['median_seconds']), optimized)))
    write_csv(output / 'cost_holdout.csv', cost_rows)
    table_cost = ['| Braço | Tentativas | Promoções | Decisão + validação mediana (s) | Promoção mediana (s) | Total contabilizado mediano (s) | Equilíbrio mediano na S2 (chamadas) |',
                  '|---|---:|---:|---:|---:|---:|---:|']
    for mode in ('deterministic', 'coordinator'):
        data = [r for r in cost_rows if r['mode'] == mode]
        points = [r['full_accounted_break_even'] for r in data if r['full_accounted_break_even'] is not None]
        table_cost.append(f"| {mode} | {len(data)}/3 | {sum(r['promoted'] for r in data)} | "
            f"{number(statistics.median(r['decision_validation_seconds'] for r in data), 6)} | "
            f"{number(statistics.median(r['promotion_seconds'] for r in data))} | "
            f"{number(statistics.median(r['total_accounted_seconds'] for r in data))} | "
            f"{statistics.median(points):g} |" if points else f'| {mode} | {len(data)}/3 | — | — | — | — | não definido |')
    # Separate the complete campaign from the previous grid and the technical run.
    comparison = ['| Campanha / N=10 milhões | Threads medidas | Medições por configuração | Tseq S1 (ms) | Escolha S1; Tp (ms) | Ganho total S1 |',
                  '|---|---|---:|---:|---:|---:|']
    for title, directory in [('Seis equipes, anterior', ROOT / 'results/axpy_scientific/mac_m5_2026-11-16'),
                              ('Todas as equipes, atual', STUDY)]:
        config = json.loads((directory / 'protocol.json').read_text())
        summary = rows(directory / 'session01/summary.csv')
        choice = next(r for r in json.loads((directory / 'session01/selection.json').read_text()) if r['size']==10000000)['selection']['recommended']
        seq = next(r for r in summary if r['size']=='10000000' and r['variant']=='sequential')
        comparison.append(f"| {title} | {'/'.join(map(str, config['threads']))} | 15 | "
            f"{number(float(seq['median_seconds'])*1000)} | {choice['threads']}T; "
            f"{number(choice['median_seconds']*1000)} | {number(choice['speedup'])} |")
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figure_dir = ROOT / 'docs/monografia/figures_banca_2026-11-16'
    figure_dir.mkdir(exist_ok=False)
    figures = []
    for n in (1024, 1000000, 10000000):
        fig, ax = plt.subplots(figsize=(9, 4.8))
        for i in (1, 2):
            curve = sorted((r for r in measured[i] if int(r['size'])==n and r['variant']=='automatic'), key=lambda r:int(r['threads']))
            x = [int(r['threads']) for r in curve]
            line, = ax.plot(x, [float(r['speedup_total']) for r in curve], 'o-', label=f'Sessão {i}')
            ax.vlines(x, [float(r['speedup_total_ci95_low']) for r in curve], [float(r['speedup_total_ci95_high']) for r in curve], color=line.get_color(), alpha=.55)
        ax.axhline(1, color='gray', linestyle='--', label='Sequencial = 1')
        if n==1024:
            ax.set_yscale('log')
        ax.set(xlabel='Threads OpenMP configuradas', ylabel='Ganho total Tseq/Tp', xticks=list(range(1,11)), title=f'AXPY N={n:,}; duas sessões, sem juntar amostras')
        ax.legend(loc='lower center', bbox_to_anchor=(.5,1.08), ncol=3)
        ax.set_title(ax.get_title(), pad=45)
        ax.grid(alpha=.2)
        fig.tight_layout()
        for extension in ('png', 'svg', 'pdf'):
            path = figure_dir / f'axpy_all_threads_{n}.{extension}'
            fig.savefig(path, dpi=180)
            figures.append(path)
        plt.close(fig)
    lines = ['# AXPY: campanha final com todas as equipes — 16/11/2026', '',
        '## Protocolo e integridade', '',
        'Protocolo fixado em `62f84f0`, sobre branch derivada da main `601b813`. '
        'As duas sessões usam os fixtures existentes, três tamanhos, sequencial e OpenMP 1–10T. '
        'São 33 configurações por sessão, quinze medições e três aquecimentos: 990 medições e 198 aquecimentos. '
        f'O intervalo entre sessões foi {gap:.3f} s. A escolha foi congelada por SHA-256 antes da S2. '
        'Os 66 pares configuração–sessão passaram pela corretude integral dos vetores. '
        'Os prefixos terminam PREPARED porque a coleta termina antes da LLM; a campanha científica COMPLETE '
        'é sustentada pelo protocolo, duas sessões, amostras e análise, não pelo status isolado do runner.', '',
        '## Resultados e estabilidade', '', '\n'.join(stats), '', '\n'.join(later), '',
        'A escolha mudou em um dos três tamanhos. A recomendação congelada de 6T para um milhão de elementos '
        'ficou 2,088% acima da menor mediana posterior (10T), cruzando ligeiramente o limite operacional de 2%. '
        'A recomendação da própria S2 foi 4T por quase empate; ela não foi usada para corrigir a escolha congelada. '
        'Inadequação operacional não significa erro de corretude nem diferença estatisticamente confirmada. '
        'Os IC95% são bootstrap percentil pareado de 5.000 rodadas, condicionais à sessão. '
        'Nenhum tempo foi excluído como outlier.', '',
        *[f'![AXPY N={n}, OpenMP 1–10T: ganhos e IC95% condicionais por sessão](../monografia/figures_banca_2026-11-16/axpy_all_threads_{n}.png)' for n in (1024,1000000,10000000)], '',
        '## Comparação contextual, sem agregar campanhas', '', '\n'.join(comparison), '',
        'O candidato gerado conserva SHA-256 `'+first['runs'][0]['candidate_sha256']+'`. '
        'O ganho maior da campanha atual não é uma otimização nova: o baseline sequencial ficou mais lento, '
        'o conjunto de threads mudou e as condições de sessão não foram isoladas. '
        'O histórico de 03/11 usa outro contrato; a execução de 105 medições foi apenas validação técnica. '
        'Nenhum desses tempos foi usado para completar as 990 observações.', '',
        '## Custos reais e amortização', '', '\n'.join(table_cost), '',
        'Os braços reutilizam um único prefixo determinístico S1 de N=10 milhões. Há três novas decisões '
        'por braço; não são três novas medições do prefixo ou seis pipelines independentes. '
        'A promoção recompila e revalida; o mesmo candidato e a configuração 4T são impostos pelos gates. '
        'A amortização da tabela usa as latências da S2 e custo total por tentativa antes de resumir. '
        'Decisão isolada, preparo e promoção estão discriminados nos CSVs. '
        'Reuso, entrada, economia positiva e condições equivalentes são hipóteses do cálculo, não uma promessa de economia futura. '
        'O custo real da LLM não foi substituído pela latência histórica. '
        'Tempos de kernel somados foram reconstruídos multiplicando cada média por seu número fixo de chamadas internas; '
        'há arredondamento de até a resolução de impressão do driver. O custo de parede inclui inicialização e validação, '
        'e não deve ser confundido com esse somatório.', '',
        '## Condições e limites', '',
        'Apple M5, 10 núcleos (4 P/6 E), 16 GiB, macOS 26.6.2, LLVM Homebrew 23.1.1. '
        'O probe confirmou todos os tamanhos de equipe, não sua alocação P/E. Energia externa e bateria 3–4%, '
        'indicada como carregando; sem controle térmico, de frequência ou exclusividade do host. '
        'A inferência ocorreu depois das duas sessões, sem concorrência com benchmarks ou testes. '
        'Nenhum contador perf Linux foi coletado no macOS. Uma fonte e três tamanhos não estimam generalização '
        'entre programas ou máquinas; duas sessões no mesmo dia não são independência populacional.', '']
    (output / 'REPORT.md').write_text('\n\n'.join(lines))
    result = dict(status='COMPLETE', scientific_samples=990, scientific_warmups=198,
        configurations_per_session=33, frozen_before_second_session=True, cooldown_seconds=gap,
        source_main_commit='601b813', candidate_sha256=first['runs'][0]['candidate_sha256'],
        selector_inadequate=1, stable_cases=2, cases=3, cost_status=cost['status'],
        report_sha256=sha(output / 'REPORT.md'),
        inputs={str(p.relative_to(ROOT)):sha(p) for p in [STUDY / 'session01/report.json', STUDY / 'session02/report.json',
            STUDY / 'frozen_selection.json', ANALYSIS / 'report.json', COST / 'report.json']},
        figures={str(p.relative_to(ROOT)):sha(p) for p in figures},
        linux_perf_status='NOT_RUN_MACOS', institutional_full_model='AUTHENTICATION_REQUIRED')
    write_json(output / 'report.json', result)
    seal(output)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.output.resolve())))
