"""Incorporate verified AXPY observations while retaining the 78-page revision."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark_scaling import write_json
from scripts.build_final_monograph import main as export_book
from scripts.evaluate_axpy_campaign import verify_session

STUDY = ROOT / 'results/axpy_scientific/mac_m5_2026-11-16'
ANALYSIS = ROOT / 'results/axpy_scientific/analysis_mac_m5_2026-11-16'
BOOK = ROOT / 'docs/monografia'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def number(value, digits=3):
    return f'{float(value):.{digits}f}'.replace('.', ',')


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unexpected manuscript anchor: ' + old[:80])
    return text.replace(old, new, 1)


def build():
    for n in (1, 2):
        verify_session(STUDY / f'session{n:02d}')
    report = json.loads((ANALYSIS / 'report.json').read_text())
    if report['status'] != 'COMPLETE' or report['measured_samples'] != 630:
        raise ValueError('Complete scientific AXPY evidence is required')
    previous = {}
    for name in ('MONOGRAFIA_CONSOLIDADA.md', 'MONOGRAFIA_CONSOLIDADA.docx',
                 'MONOGRAFIA_CONSOLIDADA.pdf', 'CAPA_PUCRS_CONSOLIDADA.docx'):
        source = BOOK / name
        target = source.with_name(source.stem + '_PRE_AXPY_2026-11-16' + source.suffix)
        expected = hashlib.sha256(subprocess.check_output(['git', 'show', '85acd66:docs/monografia/' + name], cwd=ROOT)).hexdigest()
        if not target.exists():
            if sha(source) != expected:
                raise ValueError('Unarchived manuscript edits: ' + name)
            shutil.copyfile(source, target)
        if sha(target) != expected:
            raise ValueError('Previous revision changed: ' + target.name)
        previous[str(target.relative_to(ROOT))] = expected
    source = BOOK / 'MONOGRAFIA_CONSOLIDADA.md'
    if sha(source) != previous['docs/monografia/MONOGRAFIA_CONSOLIDADA_PRE_AXPY_2026-11-16.md']:
        manifest_path = BOOK / 'AXPY_SCIENTIFIC_2026-11-16_MANIFEST.json'
        if not manifest_path.exists():
            raise ValueError('Current manuscript differs without a generated manifest')
        generated = json.loads(manifest_path.read_text())
        if any(sha(ROOT / name) != expected for name, expected in generated['files'].items()):
            raise ValueError('Generated outputs contain manual edits; do not silently overwrite them')
    text = (BOOK / 'MONOGRAFIA_CONSOLIDADA_PRE_AXPY_2026-11-16.md').read_text()
    frozen = json.loads((STUDY / 'frozen_selection.json').read_text())
    first = rows(ANALYSIS / 'measurements_session01.csv')
    second = rows(ANALYSIS / 'measurements_session02.csv')
    policies = [r for r in rows(ANALYSIS / 'policies.csv') if r['policy'] == 'selector']
    table = ['| N | Seleção S1 | Mediana selecionada (µs) | S total S1 [IC95%] | S paralelo S1 | E paralela S1 |',
             '|---|---:|---:|---:|---:|---:|']
    heldout = ['| N | Configuração congelada | S total S2 | Excesso sobre melhor S2 | Inadequada (>2%) |',
               '|---|---:|---:|---:|---|']
    for choice in frozen['choices']:
        n = choice['size']
        label = format(n, ',').replace(',', '.')
        selected = choice['selection'].get('recommended')
        p, variant = (selected['threads'], 'automatic') if selected else (1, 'sequential')
        row = next(r for r in first if (int(r['size']), r['variant'], int(r['threads'])) == (n, variant, p))
        config = str(p) + 'T' if selected else 'seq.'
        interval = f"{number(row['speedup_total'])} [{number(row['speedup_total_ci95_low'])}; {number(row['speedup_total_ci95_high'])}]"
        scale, efficiency = (number(row['speedup_parallel']), number(row['efficiency_parallel'])) if selected else ('—', '—')
        table.append(f"| {label} | {config} | {number(float(row['median_seconds']) * 1e6, 4)} | {interval} | {scale} | {efficiency} |")
        later = next(r for r in policies if int(r['size']) == n)
        heldout.append(f"| {label} | {config} | {number(later['speedup_total'])} | {number(later['regret_percent'])}% | {'Sim' if later['inadequate'] == 'True' else 'Não'} |")
    costs = ['| N | Preparo S1 (s) | Preparo S2 (s) | Equilíbrio do preparo S1 na latência S2 (chamadas) |',
             '|---|---:|---:|---:|']
    for row in report['amortization']:
        equilibrium = str(row['holdout_prefix_break_even']) if row['holdout_prefix_break_even'] is not None else 'não definido'
        label = format(row['n'], ',').replace(',', '.')
        costs.append(f"| {label} | {number(row['measured_prefix_seconds'])} | {number(row['second_session_prefix_seconds'])} | {equilibrium} |")
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figure_directory = BOOK / 'figures_axpy_2026-11-16'
    figure_directory.mkdir(exist_ok=True)
    image_lines = []
    figure_files = []
    for choice in frozen['choices']:
        n = choice['size']
        fig, ax = plt.subplots(figsize=(7, 3.8))
        for label, values, color in [('S1', first, '#245b8a'), ('S2', second, '#21755b')]:
            curve = sorted((r for r in values if int(r['size']) == n and r['variant'] == 'automatic'), key=lambda r: int(r['threads']))
            x = [int(r['threads']) for r in curve]
            ax.plot(x, [float(r['speedup_total']) for r in curve], 'o-', label=label, color=color)
            ax.vlines(x, [float(r['speedup_total_ci95_low']) for r in curve],
                      [float(r['speedup_total_ci95_high']) for r in curve], color=color, alpha=.7)
        ax.axhline(1, linestyle='--', color='gray', label='sequencial')
        ax.set(title=f"AXPY — N={format(n, ',').replace(',', '.')}", xlabel='Threads', ylabel='Ganho total Tseq/Tp', xticks=[1, 2, 4, 6, 8, 10])
        ax.tick_params(labelsize=11)
        ax.xaxis.label.set_fontsize(12)
        ax.yaxis.label.set_fontsize(12)
        ax.legend(fontsize=10, ncol=3, loc='lower center', bbox_to_anchor=(.5, 1.01), frameon=False)
        ax.set_title(ax.get_title(), pad=38)
        ax.grid(alpha=.25)
        fig.tight_layout()
        for extension in ('png', 'svg', 'pdf'):
            path = figure_directory / f'axpy_{n}.{extension}'
            fig.savefig(path, dpi=180)
            figure_files.append(path)
        plt.close(fig)
        image_lines.append(f'![AXPY N={n}: sessões separadas; barras são IC95% condicionais](figures_axpy_2026-11-16/axpy_{n}.png)')
    methods = '''
O protocolo AXPY foi fixado antes das medições em `82de6e0`. As duas sessões
utilizam N=1.024, 1.000.000 e 10.000.000, com respectivamente 10.000, 100 e 40
chamadas internas por processo. Cada entrada tem sete configurações:
sequencial e OpenMP em 1/2/4/6/8/10T;
o conjunto tem 21 por sessão. Quinze processos medidos e três aquecimentos
por configuração totalizam 630 medições e 126 aquecimentos nas duas sessões.
O intervalo ocioso previsto entre sessões é de 30 segundos. Toda execução
temporizada verifica sua saída integralmente fora do intervalo do kernel.
As três áreas double ocupam logicamente 24.576, 24.000.000 e 240.000.000 bytes;
isso não mede residência de cache nem tráfego DRAM. As amostras não são somadas
ao corpus de 28 fontes ou às campanhas multiplataforma anteriores.
'''
    section = '\n\n'.join(['#### 5.8.2. Nova campanha científica AXPY', methods.strip(),
        '\n'.join(table),
        'As medianas, médias, DP amostrais, MAD, IQR e IC95% de todas as configurações permanecem nos CSVs. '
        'Os intervalos são bootstrap percentil de 5.000 reamostragens de rodadas completas, condicionais à coleta; '
        'não são testes de significância nem estimativas populacionais. A linha sequencial é a própria referência, não um ganho.',
        '\n\n'.join(image_lines),
        'As escolhas foram congeladas em arquivo com SHA-256 antes do início da segunda sessão. O limiar de quase empate permanece em 2%, sem ajustes no holdout.',
        '\n'.join(heldout),
        f"A recomendação permaneceu igual em {report['stable_cases']}/3 casos. Nenhuma das três escolhas congeladas "
        'ficou mais de 2% acima da menor mediana da segunda sessão, incluindo sequencial. Isso descreve três entradas '
        'do mesmo kernel, não três programas independentes. O caso pequeno conservou o sequencial; aumentar threads não foi presumido benéfico.',
        '#### 5.8.3. Amortização do preparo determinístico AXPY', '\n'.join(costs),
        'C é o tempo observado do prefixo real: análises, geração, compilação, corretude, amostragem, seleção e contexto. '
        'A economia por chamada usa a configuração congelada e as novas medianas da S2. Não houve nova inferência LLM nem promoção: '
        'estes pontos amortizam somente o preparo, constituindo limites inferiores para o custo completo de admissão. '
        'Não se transportou a latência LLM histórica ao novo candidato. Sem economia positiva, o equilíbrio não é definido. '
        'As duas observações de custo por entrada não sustentam IC populacional.',
        'O macOS registrou energia externa com bateria em 3%, carregando. A carga inicial baixa, a ausência de controle '
        'dedicado de temperatura/frequência e a execução no mesmo host/dia limitam a interpretação. O probe confirmou '
        'equipes de 1/2/4/6/8/10 workers, não sua alocação P/E durante o kernel. Não se inferem causas físicas de memória '
        'das curvas. Todas as configurações lentas e sem ganho foram mantidas.',
        'Fontes: [protocolo fixado](../experiments/AXPY_SCIENTIFIC_PROTOCOL_2026-11-16.json), '
        '[arquivos das sessões](../../results/axpy_scientific/mac_m5_2026-11-16/), '
        '[análise completa](../../results/axpy_scientific/analysis_mac_m5_2026-11-16/report.json).'])
    text = replace_once(text, '### 5.8. AXPY: resultado histórico no M5 e novo contrato',
        '### 5.8. AXPY: histórico e campanha científica sob o novo contrato\n\n#### 5.8.1. Resultado histórico de 03/11')
    text = replace_once(text, 'A nova fonte e os dois drivers descritos em §3.8 precisam passar pela nova\ncoleta; nenhum tempo histórico foi atribuído à implementação atual. Este caso\nnão altera os denominadores de §5.1–5.4.',
        'A subseção seguinte avalia a fonte e os drivers atuais. Nenhum tempo histórico\nfoi atribuído a essa implementação, nem seus dados alteram os denominadores de §5.1–5.4.')
    text = replace_once(text, '### 5.9. Transferência da seleção entre sessões Linux', section + '\n\n### 5.9. Transferência da seleção entre sessões Linux')
    text = replace_once(text, '## 5. Resultados',
        'A extensão científica AXPY usa as três entradas e os números fixos de chamadas\n'
        'internas descritos em §5.8.2, mantendo quinze medições externas e três\n'
        'aquecimentos. O protocolo e os hashes foram fixados antes da primeira\n'
        'sessão; as escolhas foram congeladas antes da segunda. O custo relatado\n'
        'para AXPY é exclusivamente o preparo determinístico observado.\n\n## 5. Resultados')
    text = replace_once(text, '### 5.6. Estudo histórico de admissão do Coordinator no Mac',
        'A bateria da campanha AXPY acrescentou nove testes do harness e drivers,\n'
        'totalizando 152 testes aprovados, sem skips, além dos 23 casos de regressão.\n'
        'As correções de aliases de caminhos temporários e de quantização de\n'
        'temporizador nos microtestes ocorreram antes da coleta científica.\n'
        'A verificação final recompõe políticas, ICs, hashes e cópias da monografia\n'
        'anterior, além de conferir A4, margens e campo de paginação no Word.\n'
        'Ela não certifica renderização nativa nem aprovação institucional.\n\n'
        '### 5.6. Estudo histórico de admissão do Coordinator no Mac')
    text = replace_once(text, 'e a campanha científica do AXPY com o novo contrato permanecem pendentes.',
        'permanecem indisponíveis. A campanha AXPY sob o contrato atualizado foi concluída\nem duas sessões, com 630 medições e nenhuma escolha congelada inadequada nos três tamanhos.')
    text = replace_once(text, 'The equivalent M5 campaign is complete; physical cache/DRAM counters and a\nscientific AXPY campaign under the updated contract remain unavailable.',
        'The equivalent M5 and updated-contract AXPY campaigns are complete. The latter\ncontains 630 observations in two sessions, with no frozen choice over 2% slower\nthan the later measured oracle across three sizes. Physical cache/DRAM counters remain unavailable.')
    text = replace_once(text, 'A campanha científica AXPY sob o contrato\natualizado e contadores físicos de cache/DRAM permanecem pendentes.',
        'A campanha científica AXPY sob o contrato\natualizado foi concluída com três entradas e 630 medições. Na avaliação posterior,\nos ganhos das escolhas congeladas nas duas entradas maiores foram aproximadamente\n1,192×, enquanto a menor conservou o sequencial; nenhuma excedeu o limiar\noperacional de inadequação. A amortização medida cobre somente o prefixo\ndeterminístico, não inferência ou promoção. Contadores físicos de cache/DRAM\npermanecem indisponíveis.')
    text = replace_once(text, 'sujeito a nova execução |', 'avaliado em duas sessões científicas, sem nova promoção LLM |')
    source.write_text(text)
    report_path = ROOT / 'docs/experiments/AXPY_SCIENTIFIC_2026-11-16_REPORT.md'
    report_path.write_text('# Campanha científica AXPY no Apple M5 — 16/11/2026\n\n' + section + '\n\n'
        'A monografia consolidada incorpora estes resultados. A revisão anterior de 78 páginas permanece em '
        '`MONOGRAFIA_CONSOLIDADA_PRE_AXPY_2026-11-16.*`. O profiling físico e a revisão nativa institucional '
        'não foram concluídos por esta campanha.\n')
    # Figures and protocol links above are relative to the manuscript directory.
    # The experiment report lives in docs/experiments, at the same depth.
    report_path.write_text(report_path.read_text().replace('../experiments/', './').replace(
        '(figures_axpy_', '(../monografia/figures_axpy_'))
    with report_path.open('a') as stream:
        stream.write('''
## Reprodução e testes

Execute na raiz `tcc2`, com LLVM/OpenMP no PATH. Para análise e exportações,
instale `requirements-experimental.txt` em um venv local. Os nomes abaixo são
novos para preservar a coleta arquivada:

```bash
python3 -B scripts/evaluate_axpy_campaign.py prepare --directory results/axpy_scientific/repeat
python3 -B scripts/evaluate_axpy_campaign.py session01 --directory results/axpy_scientific/repeat
python3 -B scripts/evaluate_axpy_campaign.py freeze --directory results/axpy_scientific/repeat
sleep 30
python3 -B scripts/evaluate_axpy_campaign.py session02 --directory results/axpy_scientific/repeat
python3 -B scripts/evaluate_axpy_campaign.py analyze --directory results/axpy_scientific/repeat --output results/axpy_scientific/analysis_repeat
python3 -B scripts/evaluate_axpy_campaign.py verify --directory results/axpy_scientific/repeat
```

O gerador `scripts/build_axpy_material.py` é específico da campanha arquivada
de 16/11 e só reexporta seus próprios arquivos se os hashes ainda coincidirem;
edições manuais divergentes são recusadas. Não o use para substituir dados por
outra coleta. O resultado dos testes finais e da verificação acadêmica está em
[report.json](../../results/validation/axpy_scientific_2026-11-16/report.json).
A suíte ampliada aprovou 152 testes sem skips e 23 casos de regressão. Os avisos
legados de arquivos CSV não fechados foram conservados nos logs, sem falhas.
''')
    export_book()
    from docx import Document
    from pypdf import PdfReader
    word, pdf = Document(source.with_suffix('.docx')), PdfReader(source.with_suffix('.pdf'))
    outputs = [source, source.with_suffix('.docx'), source.with_suffix('.pdf'),
               BOOK / 'CAPA_PUCRS_CONSOLIDADA.docx', report_path, *figure_files]
    write_json(BOOK / 'AXPY_SCIENTIFIC_2026-11-16_MANIFEST.json', dict(
        created_utc=datetime.now(timezone.utc).isoformat(), previous_revision_sha256=previous,
        study_report_sha256=sha(ANALYSIS / 'report.json'),
        files={str(p.relative_to(ROOT)): sha(p) for p in outputs},
        pdf_pages=len(pdf.pages), word_tables=len(word.tables), word_images=len(word.inline_shapes),
        renderer='ReportLab content export; native Word/ABNT review remains required'))
    print(json.dumps(dict(pdf_pages=len(pdf.pages), word_tables=len(word.tables), word_images=len(word.inline_shapes))))


if __name__ == '__main__':
    build()
