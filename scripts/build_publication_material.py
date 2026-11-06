"""Export new publication-review files while preserving all earlier manuscripts."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_academic_material import powerpoint_export, word_export
from scripts.build_multiplatform_material import fill_cover, format_word, pdf_export
from scripts.evaluate_automation_corpus import verify_archive
from scripts.report_publication import verify_diagnostics


def figures(corpus, diagnoses, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    output.mkdir(parents=True, exist_ok=True)

    def save(fig, name):
        fig.tight_layout()
        for extension in ('png', 'svg', 'pdf'):
            fig.savefig(output / f'{name}.{extension}', dpi=180)
        plt.close(fig)

    verified = verify_archive(corpus)
    counts = verified['report']['coverage']['all']
    fig, ax = plt.subplots(figsize=(8, 4))
    labels = ['Aceitas conforme\ncontrato', 'Recusadas conforme\ncontrato', 'Aceitações\nindevidas', 'Recusas\nindevidas', 'Erros\ninesperados']
    values = [counts[k] for k in ('true_acceptances', 'true_refusals', 'false_acceptances', 'false_refusals', 'unexpected_errors')]
    ax.bar(labels, values, color=['#27856f', '#377eac', '#bd5544', '#dd9c40', '#875f9a'])
    ax.set(ylabel='Fontes C distintas', title='Corpus autoral controlado: cobertura contra especificação de suporte')
    for i, value in enumerate(values):
        ax.text(i, value + .15, str(value), ha='center')
    save(fig, 'corpus_coverage')

    with (corpus / 'summary.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    choices = json.loads((corpus / 'selection.json').read_text())
    kernels = sorted({r['kernel'] for r in rows})
    fig, ax = plt.subplots(figsize=(11, 5))
    for offset, variant, color in [(-.19, 'pipeline_openmp', '#27856f'), (.19, 'gcc_autopar', '#dd9c40')]:
        if variant not in {r['variant'] for r in rows}:
            continue
        values, labels, intervals = [], [], []
        for kernel in kernels:
            choice = next(c for c in choices if c['kernel'] == kernel and c['size'] == 'large' and c['variant'] == variant)
            selected = choice['selection'].get('recommended')
            p = selected['threads'] if selected else None
            row = next(r for r in rows if r['kernel'] == kernel and r['size'] == 'large'
                       and r['variant'] == (variant if p else 'sequential') and int(r['threads']) == (p or 1))
            values.append(float(row['speedup_total']))
            intervals.append((float(row['speedup_total_ci95_low']), float(row['speedup_total_ci95_high'])))
            labels.append(str(p) + 'T' if p else 'seq')
        x = [i + offset for i in range(len(kernels))]
        ax.bar(x, values, width=.36, label=variant, color=color)
        ax.vlines(x, [low for low, _ in intervals], [high for _, high in intervals], color='#253645', alpha=.8)
        for pos, value, label in zip(x, values, labels):
            ax.text(pos, value + .025, label, ha='center', fontsize=7, rotation=90)
    ax.axhline(1, color='gray', linestyle='--')
    ax.set_xticks(range(len(kernels)), kernels, rotation=65, ha='right', fontsize=8)
    ax.set(ylabel='Tseq / Tp recomendado', title='N=1.000.000; mesmo compilador, fontes e driver; escolha por método')
    ax.grid(axis='y', alpha=.2)
    ax.legend()
    save(fig, 'corpus_selected_speedup')

    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for column, kernel in enumerate(('affine_vector', 'inner_product')):
        for line, size in enumerate(('small', 'large')):
            ax = axes[line, column]
            for variant, label in [('pipeline_openmp', 'OpenMP gerado'), ('gcc_autopar', 'GCC autopar')]:
                curve = sorted((r for r in rows if r['kernel'] == kernel and r['size'] == size and r['variant'] == variant),
                               key=lambda r: int(r['threads']))
                if not curve:
                    continue
                x = [int(r['threads']) for r in curve]
                curve_line, = ax.plot(x, [float(r['speedup_total']) for r in curve], 'o-', label=label)
                ax.vlines(x, [float(r['speedup_total_ci95_low']) for r in curve],
                          [float(r['speedup_total_ci95_high']) for r in curve], color=curve_line.get_color(), alpha=.6)
            ax.axhline(1, color='gray', linestyle='--')
            ax.set(title=f"{kernel}; N={'1.024' if size == 'small' else '1.000.000'}",
                   xlabel='Threads configuradas', ylabel='Ganho total Tseq/Tp', xticks=(1, 2, 4))
            ax.grid(alpha=.2)
            ax.legend(fontsize=8)
    fig.suptitle('Exemplos definidos por classe; IC95% condicional de rodadas pareadas')
    save(fig, 'corpus_example_curves')

    groups = []
    for path in diagnoses:
        report = verify_diagnostics(path)
        for group in report['groups']:
            if group['split'] != 'heldout':
                continue
            if group['mode'] == 'rules' and any(label == 'Regras' for label, _ in groups):
                continue
            label = 'Regras' if group['mode'] == 'rules' else report['settings']['model'] + '\n' + ('Completo' if group['mode'] == 'coordinator' else 'Sem análise')
            groups.append((label, group))
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax, metric, title in zip(axes, ('cause_action_correct_rate', 'schema_valid_rate'),
                                 ('Causa e ação conforme anotação', 'Resposta conforme schema')):
        ax.bar(range(len(groups)), [g[metric] for _, g in groups], color='#377eac')
        ax.set_xticks(range(len(groups)), [label for label, _ in groups], rotation=45, ha='right', fontsize=8)
        ax.set(ylim=(0, 1.12), title=title, ylabel='Fração dos slots planejados')
        for i, (_, g) in enumerate(groups):
            ax.text(i, g[metric] + .025, f"{g['attempted_count']}/{g['attempts']}\nexecutados", ha='center', fontsize=7)
        ax.grid(axis='y', alpha=.2)
    fig.suptitle('Conformidade à rubrica autoral; 12 vistas heldout por braço')
    save(fig, 'diagnostic_heldout')

    fig, axes = plt.subplots(1, 2, figsize=(14, 4))
    for ax, title, pragma in zip(axes, ('Sequencial', 'Candidato gerado'), ('', '  #pragma omp parallel for schedule(static)\n')):
        code = ('void kernel_case(int n,\n  const double *restrict A,\n  const double *restrict B,\n  double *restrict Y)\n{\n' + pragma +
                '  for (int i = 0; i < n; i++)\n    Y[i] = 2.0 * A[i] + B[i];\n}')
        ax.text(0, .94, code, va='top', family='monospace', fontsize=12)
        ax.set_title(title, fontsize=15)
        ax.axis('off')
    fig.suptitle('DOALL: buffers disjuntos conforme restrict; atribuição independente')
    save(fig, 'doall_example')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--diagnostics', type=Path, nargs='+', required=True)
    args = parser.parse_args()
    writing = ROOT / 'docs/monografia'
    source = writing / 'REVISAO_PUBLICACAO.md'
    output = writing / 'figures_publication'
    figures(args.corpus, args.diagnostics, output)
    checks = format_word(source, writing / 'REVISAO_PUBLICACAO.docx', revision='Revisão para fortalecimento científico — 06/11/2026')
    pdf_export(source, writing / 'REVISAO_PUBLICACAO.pdf')
    fill_cover(writing / 'referencias_institucionais/capa-contracapa-graduacao.docx',
               writing / 'CAPA_PUCRS_PUBLICACAO.docx', title='PARALELIZAÇÃO OPENMP BASEADA EM EVIDÊNCIAS: ',
               subtitle='Pipeline verificável, escalabilidade e limites de um Coordinator LLM')
    article = ROOT / 'docs/publication/ARTICLE_DRAFT.md'
    word_export(article, article.with_suffix('.docx'))
    pdf_export(article, article.with_suffix('.pdf'))
    slides = ROOT / 'docs/defesa/SLIDES_PUBLICACAO.md'
    powerpoint_export(slides, slides.with_name('DEFESA_PUBLICACAO.pptx'))
    outputs = [source, writing / 'REVISAO_PUBLICACAO.docx', writing / 'REVISAO_PUBLICACAO.pdf',
               writing / 'CAPA_PUCRS_PUBLICACAO.docx', article, article.with_suffix('.docx'), article.with_suffix('.pdf'),
               slides, slides.with_name('DEFESA_PUBLICACAO.pptx'), *output.glob('*')]
    manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(), word_checks=checks,
                    renderer='ReportLab content review; native Office and institutional approval pending',
                    files={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs})
    (writing / 'PUBLICATION_WRITING_MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(checks))


if __name__ == '__main__':
    main()
