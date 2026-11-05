"""Write the numerical report and the separate manuscript from verified analysis tables."""
import argparse
import csv
import json
import hashlib
import os
from pathlib import Path
import re


def number(value):
    return f'{float(value):.6g}' if value is not None and value != '' else '—'


def generate(campaign, analysis, report_file, manuscript):
    report = json.loads((campaign / 'report.json').read_text())
    verified = json.loads((analysis / 'verification.json').read_text())
    if report['status'] != 'COMPLETE' or verified['status'] != 'VERIFIED_ARCHIVE':
        raise ValueError('Completed and verified campaign required')
    if report['repetitions'] != 15 or report['warmups'] != 3:
        raise ValueError('This report requires the requested 15-sample/3-warmup protocol')
    if hashlib.sha256((campaign / 'report.json').read_bytes()).hexdigest() != verified['report_sha256']:
        raise ValueError('Analysis refers to another campaign report')
    rows = list(csv.DictReader((analysis / 'measurements.csv').open()))
    choices = json.loads((analysis / 'selection.json').read_text())
    assert len(rows) == report['configurations']
    assert sum(int(r['samples']) for r in rows) == report['measurements']
    table = ['| Caso | Entrada | Variante | Recomendação | Tp (s) | S total | S paralelo | E paralela |',
             '|---|---|---|---:|---:|---:|---:|---:|']
    fastest_table = ['| Caso / entrada / variante | Menor mediana OpenMP | Recomendação | Estado |',
                     '|---|---:|---:|---|']
    order = {'dot-auto': 0, 'dot': 1, 'gemm': 2, 'nussinov': 3, 'jacobi-2d': 4, 'covariance': 5}
    for choice in sorted(choices, key=lambda c: order.get(c['kernel'], 99)):
        key = choice['kernel'], str(choice['size']), choice['variant']
        candidates = [r for r in rows if (r['kernel'], r['size'], r['variant']) == key]
        fastest = min(candidates, key=lambda r: float(r['median_seconds']))
        selected = choice['selection'].get('recommended')
        p = selected['threads'] if selected else None
        row = next(r for r in rows if (r['kernel'], r['size'], r['variant'], r['threads']) ==
                   (key[0], key[1], key[2] if p else 'sequential', str(p or 1)))
        label = f'{p}T' if p else 'sequencial'
        table.append(f"| {key[0]} | {key[1]} | {key[2]} | {label} | {number(row['median_seconds'])} | {number(row['speedup_total'])} | {number(row['speedup_parallel']) if p else '—'} | {number(row['efficiency_parallel']) if p else '—'} |")
        fastest_table.append(f"| {' / '.join(key)} | {fastest['threads']}T; {number(fastest['median_seconds'])} s | {label} | {choice['selection']['status']} |")
    detail = ['| Caso | Entrada | Variante | Threads | Mediana (s) | Média (s) | DP amostral | MAD | IQR | IC95% mediana |',
              '|---|---|---|---:|---:|---:|---:|---:|---:|---|']
    for r in rows:
        detail.append(f"| {r['kernel']} | {r['size']} | {r['variant']} | {r['threads']} | {number(r['median_seconds'])} | {number(r['mean_seconds'])} | {number(r['stdev_seconds'])} | {number(r['mad_seconds'])} | {number(r['iqr_seconds'])} | [{number(r['median_seconds_ci95_low'])}; {number(r['median_seconds_ci95_high'])}] |")
    lines = ['# Avaliação multiplataforma — campanha de quinze medições', '',
             f"Campanha: `{campaign}`. Estado {report['status']}; {report['configurations']} configurações, {report['measurements']} amostras, {len(report['warmup_runs'])} aquecimentos e {len(report['correctness'])} validações.", '',
             'As amostras anteriores e os históricos não foram combinados com esta campanha. Não houve inferência LLM.', '',
             '## Recomendação por entrada e variante', '', *table, '',
             'S total=Tseq/Tp; S paralelo=T1/Tp; E paralela=(T1/Tp)/p. O CSV também contém Tseq/T1 e ICs das razões.', '',
             '## Menor mediana e política de quase empate', '', *fastest_table, '',
             'A coluna de menor mediana considera somente OpenMP; ela não implica ganho contra o sequencial. A recomendação aplica o Selector real, com quase empate de 2%. Seleção analítica não promove código.', '',
             '## Estatística por configuração', '', *detail, '',
             'DP amostral usa n−1; MAD não é escalado; quartis usam interpolação linear inclusiva. ICs: bootstrap percentil pareado por blocos, 5.000 réplicas, seed 2026, 95%, somente com n≥15.', '',
             'Esses ICs são condicionais aos blocos medidos. Não demonstram independência temporal, causalidade de arquitetura ou significância entre plataformas. Nenhum outlier foi removido.', '',
             '## Artefatos e execução no M5', '',
             'Fontes e entradas, logs e amostras estão no diretório da campanha. O diretório de análise contém `measurements.csv`, `selection.json`, `statistics_method.json`, `verification.json` e as figuras em PNG/SVG/PDF.', '',
             'Usar `scripts/run_multiplatform_mac.sh` com um diretório novo e analisar as saídas com `scripts/analyze_scaling.py`. A comparação direta é feita com `scripts/compare_multiplatform.py`, que exige compatibilidade e mantém curvas distintas.', '',
             'A coleta equivalente M5 está pendente. Não há novas medições Mac neste relatório. Os números históricos permanecem contextuais, com suas lacunas de proveniência.', '',
             '## Limites', '',
             'Máquina sem isolamento exclusivo ou frequência/temperatura fixadas. Não houve detector de races, contadores de hardware, medição de energia ou banda física. As variantes manuais e adaptações específicas não são ganhos da LLM.', '']
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text('\n'.join(lines)+'\n')
    section = ['### 5.8. Campanha principal Linux: três aquecimentos e quinze medições', '',
               f"A nova campanha concluiu {report['configurations']} configurações, {report['measurements']} amostras externas, {len(report['warmup_runs'])} aquecimentos e {len(report['correctness'])} validações aprovadas. As observações pertencem aos cinco algoritmos e seis casos compilados descritos na metodologia. Nenhum tempo anterior foi usado para preencher essa contagem.", '',
               *table, '', *fastest_table, '',
               'Os valores são arredondados para apresentação; amostras e resumos completos permanecem nos CSVs. A menor mediana OpenMP pode perder para o sequencial e pode diferir da recomendação por quase empate. Os gráficos usam o mesmo baseline 1T da variante e entrada, com ICs bootstrap condicionais.', '']
    for kernel in sorted({r['kernel'] for r in rows}, key=lambda k: order.get(k, 99)):
        section += [f'![Escalabilidade de {kernel} nas duas entradas; barras indicam IC95% bootstrap](figures_multiplatform/scaling_{kernel}.png)', '']
    selected_figure = Path(os.path.relpath(analysis.resolve() / 'recommended_configuration.png', manuscript.parent.resolve())).as_posix()
    section += [f'![Configurações mais rápidas e recomendações do Selector]({selected_figure})', '',
                'A comparação com a nova campanha M5 permanece pendente. As curvas do acervo de setembro e novembro têm protocolos próprios e não completam a nova matriz. Os resultados novos caracterizam códigos e configurações; não uma melhoria decisória da LLM.', '']
    text = manuscript.read_text()
    if '### 5.8.' in text:
        text = re.sub(r'### 5\.8\..*?(?=## 6\. Discussão)', '\n'.join(section)+'\n', text, flags=re.S)
    else:
        text = text.replace('## 6. Discussão', '\n'.join(section)+'\n## 6. Discussão', 1)
    manuscript.write_text(text)
    return dict(configurations=len(rows), samples=report['measurements'], recommendations=len(choices))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--report', type=Path, default=Path('docs/experiments/MULTIPLATFORM_REPORT.md'))
    parser.add_argument('--manuscript', type=Path, default=Path('docs/monografia/REVISAO_MULTIPLATAFORMA.md'))
    args = parser.parse_args()
    print(json.dumps(generate(args.campaign, args.analysis, args.report, args.manuscript)))
