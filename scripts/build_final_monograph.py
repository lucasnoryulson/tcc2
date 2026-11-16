"""Export the consolidated Markdown without overwriting prior revisions."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_multiplatform_material import format_word, pdf_export, fill_cover


def main():
    from docx import Document
    from docx.shared import RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    directory = ROOT / 'docs/monografia'
    source = directory / 'MONOGRAFIA_CONSOLIDADA.md'
    target = source.with_suffix('.docx')
    format_word(source, target, revision='')
    doc = Document(target)
    for name in ('Title', 'Heading 1', 'Heading 2', 'Heading 3', 'Pretexto'):
        style = doc.styles[name]
        style.font.color.rgb = RGBColor(0, 0, 0)
        if style.element.pPr is not None:
            for border in style.element.pPr.xpath('w:pBdr'):
                style.element.pPr.remove(border)
    for p in doc.paragraphs:
        if p.style.name in ('Title', 'Heading 1', 'Heading 2', 'Heading 3', 'Pretexto'):
            for run in p.runs:
                run.font.color.rgb = RGBColor(0, 0, 0)
    for table in doc.tables:
        table.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
        for row in table.rows:
            row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
    footer = doc.sections[0].footer.paragraphs[0]
    footer.clear()
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    doc.save(target)
    pdf_export(source, source.with_suffix('.pdf'), consolidated=True)
    fill_cover(directory / 'referencias_institucionais/capa-contracapa-graduacao.docx',
               directory / 'CAPA_PUCRS_CONSOLIDADA.docx',
               title='PARALELIZAÇÃO AUTOMÁTICA DE CÓDIGO BASEADA EM EVIDÊNCIAS: ',
               subtitle='Análise de Dependências, Seleção de Estratégias OpenMP e Avaliação de Modelos de Linguagem')


if __name__ == '__main__':
    main()
