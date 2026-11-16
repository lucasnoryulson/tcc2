"""Preserve the prior revision and export the reviewed consolidated source only.

This checks package/content structure, not native Word pagination or the
authenticated complete PUCRS model. It never regenerates historical revisions.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark_scaling import write_json
from scripts.build_final_monograph import main as export_book

BOOK = ROOT / 'docs/monografia'
ARCHIVE_REVISION = 'c364407'
ARCHIVE_NAMES = ('MONOGRAFIA_CONSOLIDADA.md', 'MONOGRAFIA_CONSOLIDADA.docx',
    'MONOGRAFIA_CONSOLIDADA.pdf', 'CAPA_PUCRS_CONSOLIDADA.docx',
    'referencias_consolidada.bib', 'AXPY_SCIENTIFIC_2026-11-16_MANIFEST.json')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preserve():
    archived = {}
    for name in ARCHIVE_NAMES:
        source = BOOK / name
        target = source.with_name(source.stem + '_PRE_BANCA_2026-11-16' + source.suffix)
        expected = hashlib.sha256(subprocess.check_output(['git', 'show',
            ARCHIVE_REVISION + ':docs/monografia/' + name], cwd=ROOT)).hexdigest()
        if not target.exists():
            if sha(source) != expected:
                raise ValueError('Current file already has unarchived edits: ' + name)
            shutil.copyfile(source, target)
        if sha(target) != expected:
            raise ValueError('Preserved revision was changed: ' + target.name)
        archived[str(target.relative_to(ROOT))] = expected
    return archived


def build():
    previous = preserve()
    source = BOOK / 'MONOGRAFIA_CONSOLIDADA.md'
    text = source.read_text()
    for image in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', text):
        (BOOK / image).resolve(strict=True)
    export_book()
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt
    from pypdf import PdfReader
    doc = Document(source.with_suffix('.docx'))
    for paragraph in doc.paragraphs:
        if paragraph.text.startswith(('Tabela ', 'Fonte:')):
            paragraph.paragraph_format.first_line_indent = Cm(0)
            paragraph.paragraph_format.line_spacing = 1
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            paragraph.paragraph_format.keep_with_next = paragraph.text.startswith('Tabela ')
            for run in paragraph.runs:
                run.font.name = 'Times New Roman'
                run.font.size = Pt(10)
        if paragraph.text.startswith('Fonte:'):
            paragraph.paragraph_format.keep_with_next = False
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.line_spacing = 1
                    paragraph.paragraph_format.first_line_indent = Cm(0)
    doc.save(source.with_suffix('.docx'))
    pdf = PdfReader(source.with_suffix('.pdf'))
    if any(not p.extract_text().strip() for p in pdf.pages):
        raise ValueError('Blank PDF page')
    outputs = [source, source.with_suffix('.docx'), source.with_suffix('.pdf'),
               BOOK / 'CAPA_PUCRS_CONSOLIDADA.docx', BOOK / 'referencias_consolidada.bib']
    result = dict(created_utc=datetime.now(timezone.utc).isoformat(), previous_revision_sha256=previous,
        files={str(p.relative_to(ROOT)): sha(p) for p in outputs}, pdf_pages=len(pdf.pages),
        word_tables=len(doc.tables), word_images=len(doc.inline_shapes),
        scope='A4, margins, captions, fields and readable PDF checked in software. '
              'PDF is a separate ReportLab content export, not a native Word render. '
              'Complete PUCRS model requires institutional login; approval/committee data not inferred.')
    write_json(BOOK / 'BANCA_2026-11-16_MANIFEST.json', result)
    print(json.dumps({k: result[k] for k in ('pdf_pages', 'word_tables', 'word_images')}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-only', action='store_true')
    args = parser.parse_args()
    preserve() if args.archive_only else build()
