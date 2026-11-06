"""Render the separate multiplatform manuscript, figures and review Office/PDF files."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_academic_material import plain, word_export


def architecture_figures(directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle

    directory.mkdir(parents=True, exist_ok=True)

    def save(fig, name):
        fig.tight_layout()
        for extension in ('png', 'svg', 'pdf'):
            fig.savefig(directory / f'{name}.{extension}', dpi=180)
        plt.close(fig)

    def box(ax, x, y, text, color='#dfedf7', width=2.1):
        ax.add_patch(FancyBboxPatch((x, y), width, .72, boxstyle='round,pad=.04', facecolor=color, edgecolor='#245365'))
        ax.text(x + width / 2, y + .36, text, ha='center', va='center', fontsize=14)

    def arrow(ax, start, end):
        ax.annotate('', xy=end, xytext=start, arrowprops=dict(arrowstyle='->', color='#245365', lw=1.4))

    fig, ax = plt.subplots(figsize=(11, 5))
    labels = ['1. AST Clang', '2. Dependências', '3. Padrões', '4. Planejamento',
              '5. Transformação', '6. Corretude', '7. Desempenho', '8. Selector',
              '9. Contexto', '10. Coordinator\núnica LLM', '11. Promoção\n+ revalidação', 'Bundle\ncódigo + evidências']
    positions = [(0, 3), (2.6, 3), (5.2, 3), (7.8, 3), (7.8, 1.6), (5.2, 1.6), (2.6, 1.6), (0, 1.6),
                 (0, .2), (2.6, .2), (5.2, .2), (7.8, .2)]
    for i, ((x, y), label) in enumerate(zip(positions, labels)):
        box(ax, x, y, label, '#fff0ca' if i == 9 else '#ddf2e7' if i == 11 else '#dfedf7')
        if i:
            px, py = positions[i - 1]
            if y == py:
                arrow(ax, (px + 2.15, py + .36) if x > px else (px - .05, py + .36),
                      (x - .05, y + .36) if x > px else (x + 2.15, y + .36))
            else:
                arrow(ax, (px + 1.05, py - .05), (x + 1.05, y + .77))
    ax.text(4.9, -.55, 'Falha: encerra com evidências. PREPARED termina antes da LLM.\nGEMM e demais variantes manuais têm coleta separada do runner de geração.', ha='center', fontsize=10)
    ax.set(xlim=(-.2, 10.2), ylim=(-.9, 4))
    ax.axis('off')
    save(fig, 'arquitetura_componentes')

    fig, ax = plt.subplots(figsize=(11, 5))
    box(ax, 3.7, 4, 'Contexto verificado')
    box(ax, 3.7, 2.8, 'Coordinator + validador', '#fff0ca')
    arrow(ax, (4.75, 3.95), (4.75, 3.57))
    for x, text in [(0, 'RETUNE'), (2.6, 'MODIFY'), (5.2, 'REJECT'), (7.8, 'ACCEPT')]:
        box(ax, x, 1.5, text)
        arrow(ax, (4.75, 2.75), (x + 1.05, 2.27))
        if text != 'ACCEPT':
            arrow(ax, (x + 1.05, 1.45), (x + 1.05, 1.05))
            box(ax, x, .3, 'Encerra\nsem publicação', '#f9e2dd')
        else:
            arrow(ax, (x + 1.05, 1.45), (x + 1.05, 1.05))
            box(ax, x, .3, 'Admissão +\nrevalidação', '#ddf2e7')
    ax.text(4.8, -.55, 'ACCEPT só publica se configuração medida, ganhos e corretude forem confirmados.\nRETUNE/MODIFY não executam busca ou reparo no runner atual.', ha='center', fontsize=10)
    ax.set(xlim=(-.2, 10.2), ylim=(-.9, 4.9))
    ax.axis('off')
    save(fig, 'fluxo_decisao')

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    n = 7
    for i in range(n):
        for j in range(n):
            color = '#ddd' if j < i else '#468ec7' if j - i == 3 else '#e5eef5'
            ax.add_patch(Rectangle((j, n - 1 - i), .92, .92, facecolor=color, edgecolor='white'))
            if j >= i:
                ax.text(j + .46, n - 1 - i + .46, f'{i},{j}', ha='center', va='center', fontsize=11)
    target = (4.46, n - 1 - 1 + .46)
    for i, j in [(1, 3), (2, 4), (2, 3)]:
        arrow(ax, (j + .46, n - 1 - i + .46), target)
    ax.set(xlim=(-.4, 7.1), ylim=(-1.1, 7.2), aspect='equal', title='Nussinov: diagonal d = 3 em azul')
    ax.text(3.4, -.7, 'Células da mesma diagonal são concorrentes.\nDependências e partições consultam intervalos menores.', ha='center', fontsize=10)
    ax.axis('off')
    save(fig, 'nussinov_diagonais')


def kernel_figures(analysis, directory):
    import csv
    import matplotlib.pyplot as plt
    rows = list(csv.DictReader((analysis / 'measurements.csv').open()))
    for kernel in sorted({r['kernel'] for r in rows}):
        sizes = sorted({r['size'] for r in rows if r['kernel'] == kernel})
        fig, axes = plt.subplots(1, len(sizes), figsize=(8.5, 3.8), squeeze=False)
        for ax, size in zip(axes.flat, sizes):
            data = [r for r in rows if r['kernel'] == kernel and r['size'] == size]
            for variant in sorted({r['variant'] for r in data} - {'sequential'}):
                curve = sorted((r for r in data if r['variant'] == variant), key=lambda r: int(r['threads']))
                x = [int(r['threads']) for r in curve]
                ax.plot(x, [float(r['speedup_parallel']) for r in curve], 'o-', label=variant)
                if all(r['speedup_parallel_ci95_low'] for r in curve):
                    ax.vlines(x, [float(r['speedup_parallel_ci95_low']) for r in curve],
                              [float(r['speedup_parallel_ci95_high']) for r in curve], alpha=.6)
            x = sorted({int(r['threads']) for r in data})
            ax.plot(x, x, '--', color='gray', label='ideal homogêneo')
            ax.set(title=f'{kernel} / {size}', xlabel='Threads', ylabel='T₁/Tₚ', xticks=x)
            ax.set_xlabel('Threads', fontsize=12)
            ax.set_ylabel('T₁/Tₚ', fontsize=12)
            ax.tick_params(labelsize=11)
            ax.grid(alpha=.25)
            ax.legend(fontsize=10)
        fig.tight_layout()
        for extension in ('png', 'svg', 'pdf'):
            fig.savefig(directory / f'scaling_{kernel}.{extension}', dpi=180)
        plt.close(fig)


def fill_cover(template, target,
               title='SISTEMAS MULTIAGENTES PARA REESTRUTURAÇÃO AUTÔNOMA DE CÓDIGOS: ',
               subtitle='Análise de dependências, paralelização OpenMP e coordenação baseada em evidências'):
    from lxml import etree as ET
    replacements = {'ESCOLA': 'ESCOLA POLITÉCNICA', 'CURSO ': 'CURSO DE CIÊNCIA DA COMPUTAÇÃO',
                    'NOME DO AUTOR EM MAIÚSCULAS': 'LUCAS NORY ULSON',
                    'TÍTULO EM MAIÚSCULAS E NEGRITO: ': title,
                    'SUBTÍTULO DO TRABALHO SEM NEGRITO': subtitle,
                    'Ano': '2026'}
    with ZipFile(template) as src, ZipFile(target, 'w') as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == 'word/document.xml':
                tree = ET.fromstring(data)
                for element in tree.iter():
                    if element.tag.endswith('}t') and element.text in replacements:
                        element.text = replacements[element.text]
                data = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
            dst.writestr(item, data)


def format_word(source, target, revision='Revisão multiplataforma — 05/11/2026'):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.enum.style import WD_STYLE_TYPE
    from docx.oxml import OxmlElement
    from docx.shared import Cm, Pt

    word_export(source, target)
    doc = Document(target)
    section = doc.sections[0]
    section.top_margin = section.left_margin = Cm(3)
    section.bottom_margin = section.right_margin = Cm(2)
    doc.styles['Normal'].font.name = 'Times New Roman'
    doc.styles['Normal'].font.size = Pt(12)
    for paragraph in doc.paragraphs:
        is_code = any(run.font.name == 'Courier New' for run in paragraph.runs)
        is_caption = bool(paragraph.runs) and all(run.italic for run in paragraph.runs)
        if paragraph._p.xpath('.//w:drawing'):
            paragraph.paragraph_format.first_line_indent = Cm(0)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            continue
        if paragraph.style.name == 'Normal' and not is_code and not is_caption:
            paragraph.paragraph_format.line_spacing = 1.5
            paragraph.paragraph_format.first_line_indent = Cm(1.25)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraphs = doc.paragraphs
    figure_number = 0
    for i, paragraph in enumerate(paragraphs):
        if i and paragraph.runs and all(r.italic for r in paragraph.runs) and paragraphs[i-1]._p.xpath('.//w:drawing'):
            figure_number += 1
            image = paragraphs[i-1]
            paragraph.text = f'Figura {figure_number} — ' + paragraph.text
            paragraph.paragraph_format.line_spacing = 1
            paragraph.paragraph_format.keep_with_next = True
            image.paragraph_format.keep_with_next = True
            for run in paragraph.runs:
                run.font.size = Pt(10)
            image._p.addprevious(paragraph._p)
            credit = doc.add_paragraph('Fonte: elaboração a partir do código e dos resultados do projeto.')
            credit.paragraph_format.line_spacing = 1
            for run in credit.runs:
                run.font.size = Pt(9)
            image._p.addnext(credit._p)
    for table in doc.tables:
        table.autofit = False
        for column in table.columns:
            column.width = Cm(16/len(table.columns))
        for row in table.rows:
            for cell in row.cells:
                cell.width = Cm(16/len(table.columns))
    footer = section.footer.paragraphs[0]
    footer.text = revision + ' — '
    field = OxmlElement('w:fldSimple')
    from docx.oxml.ns import qn
    field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    introduction = next(p for p in doc.paragraphs if p.text.startswith('1. Introdução'))
    front_style = doc.styles.add_style('Pretexto', WD_STYLE_TYPE.PARAGRAPH)
    front_style.base_style = doc.styles['Heading 1']
    outline = OxmlElement('w:outlineLvl')
    outline.set(qn('w:val'), '9')
    front_style.element.get_or_add_pPr().append(outline)
    for paragraph in doc.paragraphs:
        if paragraph.text.startswith('1. Introdução'):
            break
        if paragraph.style.name == 'Heading 1':
            paragraph.style = front_style
    toc_break = doc.add_paragraph()
    toc_break.add_run().add_break(WD_BREAK.PAGE)
    for paragraph in (toc_break, doc.add_paragraph('SUMÁRIO', style=front_style)):
        introduction._p.addprevious(paragraph._p)
    toc = doc.add_paragraph()
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'TOC \\o "1-3" \\h \\z \\u')
    toc._p.append(field)
    introduction._p.addprevious(toc._p)
    page_break = doc.add_paragraph()
    page_break.add_run().add_break(WD_BREAK.PAGE)
    introduction._p.addprevious(page_break._p)
    update = OxmlElement('w:updateFields')
    update.set(qn('w:val'), 'true')
    doc.settings.element.append(update)
    doc.core_properties.modified = datetime.now(timezone.utc)
    doc.save(target)
    reopened = Document(target)
    expected = len(re.findall(r'^!\[[^]]*\]\([^)]+\)$', source.read_text(), re.MULTILINE))
    assert len(reopened.inline_shapes) == expected
    assert any(run.font.name == 'Courier New' for p in reopened.paragraphs for run in p.runs)
    return dict(tables=len(reopened.tables), images=len(reopened.inline_shapes), paragraphs=len(reopened.paragraphs))


def pdf_export(source, target):
    from html import escape
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.platypus.tableofcontents import TableOfContents
    from PIL import Image as PILImage

    font_dir = Path('/usr/share/fonts/truetype/dejavu')
    if not font_dir.is_dir():
        import matplotlib
        font_dir = Path(matplotlib.get_data_path()) / 'fonts/ttf'
    for name, filename in [('ReviewSerif', 'DejaVuSerif.ttf'), ('ReviewSans', 'DejaVuSans.ttf'), ('ReviewMono', 'DejaVuSansMono.ttf')]:
        if (font_dir / filename).is_file():
            pdfmetrics.registerFont(TTFont(name, str(font_dir / filename)))
    available = pdfmetrics.getRegisteredFontNames()
    serif = 'ReviewSerif' if 'ReviewSerif' in available else 'Times-Roman'
    sans = 'ReviewSans' if 'ReviewSans' in available else 'Helvetica'
    mono = 'ReviewMono' if 'ReviewMono' in available else 'Courier'
    styles = getSampleStyleSheet()
    body = ParagraphStyle('ReviewBody', fontName=serif, fontSize=12, leading=18, spaceAfter=8, alignment=4)
    caption = ParagraphStyle('ReviewCaption', parent=body, fontSize=8, leading=11, alignment=1)
    cell = ParagraphStyle('ReviewCell', fontName=sans, fontSize=7, leading=9)
    code = ParagraphStyle('ReviewCode', fontName=mono, fontSize=7.5, leading=10, spaceAfter=10)
    headings = {i: ParagraphStyle(f'ReviewH{i}', fontName=sans, fontSize={1:18, 2:15, 3:12, 4:11}[i],
                                 leading={1:23, 2:20, 3:17, 4:15}[i], spaceBefore=14, spaceAfter=9,
                                 keepWithNext=True) for i in range(1, 5)}
    class ReviewPDF(SimpleDocTemplate):
        def afterFlowable(self, flowable):
            if isinstance(flowable, Paragraph) and flowable.style.name.startswith('ReviewH'):
                title = flowable.getPlainText()
                if re.match(r'^\d+\.', title) or title.startswith(('Referências', 'Apêndice')):
                    level = max(0, int(flowable.style.name[-1]) - 2)
                    key = hashlib.sha256(title.encode()).hexdigest()[:16]
                    self.canv.bookmarkPage(key)
                    self.notify('TOCEntry', (level, title, self.page, key))

    document = ReviewPDF(str(target), pagesize=A4, leftMargin=3*cm, rightMargin=2*cm,
                                 topMargin=3*cm, bottomMargin=2*cm, title=plain(source.read_text().splitlines()[0].lstrip('# ')), author='Lucas Nory Ulson')
    story = []
    figure_number = 0
    lines = source.read_text().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        heading = re.match(r'^(#{1,4})\s+(.+)', line)
        image = re.fullmatch(r'!\[([^]]*)\]\(([^)]+)\)', line)
        if line.startswith('```'):
            i += 1
            block = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                block.append(lines[i])
                i += 1
            if i == len(lines):
                raise ValueError('Unclosed PDF code block')
            story.append(Preformatted('\n'.join(block), code, maxLineLength=100))
        elif heading:
            if heading[2].startswith('1. Introdução'):
                toc = TableOfContents()
                toc.levelStyles = [ParagraphStyle(f'TOC{i}', fontName=serif, fontSize=10, leading=14,
                                                   leftIndent=i*12, firstLineIndent=0, spaceBefore=3) for i in range(3)]
                story += [PageBreak(), Paragraph('SUMÁRIO', headings[2]), toc, PageBreak()]
            story.append(Paragraph(escape(plain(heading[2])), headings[len(heading[1])]))
        elif image:
            figure_number += 1
            path = (source.parent / image[2]).resolve(strict=True)
            with PILImage.open(path) as pic:
                width, height = pic.size
            scale = min(16*cm/width, 20*cm/height)
            story.append(KeepTogether([Paragraph(escape(f'Figura {figure_number} — {image[1]}'), caption),
                         Image(str(path), width=width*scale, height=height*scale),
                         Paragraph('Fonte: elaboração a partir do código e dos resultados do projeto.', caption), Spacer(1, 8)]))
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', x) for x in cells):
                    rows.append([Paragraph(escape(plain(x)), cell) for x in cells])
                i += 1
            table = Table(rows, colWidths=[16*cm/len(rows[0])]*len(rows[0]), repeatRows=1)
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dfeaf4')),
                                        ('GRID',(0,0),(-1,-1),.4,colors.HexColor('#888888')),
                                        ('VALIGN',(0,0),(-1,-1),'TOP'), ('TOPPADDING',(0,0),(-1,-1),5),
                                        ('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story += [table, Spacer(1, 8)]
            continue
        else:
            text = [line]
            while i + 1 < len(lines) and lines[i+1].strip() and not re.match(r'^(#|\||!\[|```|- |\d+\. )', lines[i+1]):
                i += 1
                text.append(lines[i].strip())
            story.append(Paragraph(escape(plain(' '.join(text))), body))
        i += 1

    def footer(canvas, doc):
        canvas.setFont(sans, 7)
        canvas.drawString(3*cm, 1.1*cm, 'PDF de revisão de conteúdo — ReportLab; conferência institucional pendente')
        canvas.drawRightString(19*cm, 1.1*cm, str(doc.page))

    document.multiBuild(story, onFirstPage=footer, onLaterPages=footer)
    assert target.read_bytes().startswith(b'%PDF-')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis', type=Path, required=True)
    args = parser.parse_args()
    writing = ROOT / 'docs/monografia'
    source = writing / 'REVISAO_MULTIPLATAFORMA.md'
    figures = writing / 'figures_multiplatform'
    architecture_figures(figures)
    kernel_figures(args.analysis, figures)
    cover_template = writing / 'referencias_institucionais/capa-contracapa-graduacao.docx'
    fill_cover(cover_template, writing / 'CAPA_PUCRS_MULTIPLATAFORMA.docx')
    checks = format_word(source, writing / 'REVISAO_MULTIPLATAFORMA.docx')
    pdf_export(source, writing / 'REVISAO_MULTIPLATAFORMA.pdf')
    paths = [source, writing / 'REVISAO_MULTIPLATAFORMA.docx', writing / 'REVISAO_MULTIPLATAFORMA.pdf',
             writing / 'CAPA_PUCRS_MULTIPLATAFORMA.docx', *figures.glob('*')]
    manifest = dict(generated_utc=datetime.now(timezone.utc).isoformat(), word_checks=checks,
                    pdf_renderer='ReportLab review PDF; not a native Office rendering',
                    files={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (writing / 'MULTIPLATFORM_WRITING_MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(checks))


if __name__ == '__main__':
    main()
