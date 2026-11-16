"""Check the final AXPY campaign, existing regression log and academic exports."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analyze_scaling import enrich, selections
from scripts.benchmark_scaling import write_json
from scripts.evaluate_axpy_campaign import verify_session
from scripts.evaluate_selector_holdout import evaluate_rows


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_csv(path, expected):
    with path.open() as stream:
        actual = list(csv.DictReader(stream))
    encoded = [{k: '' if v is None else str(v) for k, v in row.items()} for row in expected]
    if actual != encoded:
        raise ValueError('Derived CSV differs from independent recomputation: ' + str(path))


def validate(output):
    if (output / 'report.json').exists():
        raise FileExistsError('Do not overwrite an existing validation report')
    regression = json.loads((output / 'regression/report.json').read_text())
    log = (output / 'regression/unittest.log').read_text()
    counts = re.search(r'Ran (\d+) tests in ([\d.]+)s', log)
    if regression['status'] != 'PASS' or counts is None or int(counts[1]) != 152 or 'skipped=' in log:
        raise ValueError('A passing 152-test regression suite without skips is required')
    study = ROOT / 'results/axpy_scientific/mac_m5_2026-11-16'
    analysis = ROOT / 'results/axpy_scientific/analysis_mac_m5_2026-11-16'
    a, first, raw_a, _ = verify_session(study / 'session01')
    b, second, raw_b, _ = verify_session(study / 'session02')
    frozen = json.loads((study / 'frozen_selection.json').read_text())
    report = json.loads((analysis / 'report.json').read_text())
    if not (datetime.fromisoformat(a['finished_utc']) < datetime.fromisoformat(frozen['frozen_at_utc'])
            < datetime.fromisoformat(b['started_utc'])):
        raise ValueError('Choices were not frozen strictly between collection sessions')
    if (frozen['choices'] != selections(first) or report['status'] != 'COMPLETE'
        or (report['measured_samples'], report['warmup_samples'], report['configurations_per_session']) != (630, 126, 21)
        or report['first_report_sha256'] != sha(study / 'session01/report.json')
        or report['second_report_sha256'] != sha(study / 'session02/report.json')
        or report['frozen_choices_sha256'] != sha(study / 'frozen_selection.json')
        or frozen['selector_sha256'] != sha(ROOT / 'analysis/performance_selector.py')):
        raise ValueError('Invalid scientific campaign/selection identity')
    policies, sensitivity, stability = evaluate_rows(first, second, frozen['choices'])
    for filename, rows in [('policies.csv', policies), ('sensitivity.csv', sensitivity), ('stability.csv', stability)]:
        check_csv(analysis / filename, rows)
    for number, summary, raw in [(1, first, raw_a), (2, second, raw_b)]:
        values = enrich(summary, raw)
        check_csv(analysis / f'measurements_session{number:02d}.csv', values)
        for row in values:
            for field in ('median_seconds', 'speedup_total', 'speedup_transformation', 'speedup_parallel', 'efficiency_parallel'):
                low, high = row[field + '_ci95_low'], row[field + '_ci95_high']
                if not all(math.isfinite(v) and v > 0 for v in (low, high)) or low > high:
                    raise ValueError('Invalid conditional bootstrap interval')
    manifest = json.loads((ROOT / 'docs/monografia/AXPY_SCIENTIFIC_2026-11-16_MANIFEST.json').read_text())
    for relative, expected in (manifest['previous_revision_sha256'] | manifest['files']).items():
        if sha(ROOT / relative) != expected:
            raise ValueError('Changed manuscript artifact: ' + relative)
    from docx import Document
    from pypdf import PdfReader
    book = ROOT / 'docs/monografia/MONOGRAFIA_CONSOLIDADA'
    with ZipFile(book.with_suffix('.docx')) as archive:
        if archive.testzip() is not None:
            raise ValueError('Corrupt Word ZIP')
    word, pdf = Document(book.with_suffix('.docx')), PdfReader(book.with_suffix('.pdf'))
    section = word.sections[0]
    for actual, expected in [(section.left_margin.cm, 3), (section.right_margin.cm, 2),
                              (section.top_margin.cm, 3), (section.bottom_margin.cm, 2),
                              (section.page_width.cm, 21), (section.page_height.cm, 29.7)]:
        if abs(actual - expected) > .01:
            raise ValueError('Unexpected A4 page or document margins')
    if 'PAGE' not in section.footer._element.xml:
        raise ValueError('Word page-number field missing')
    pages = [page.extract_text() for page in pdf.pages]
    if any(not text.strip() for text in pages):
        raise ValueError('Blank PDF page')
    text = '\n'.join(pages)
    for expected in ('5.8.2.', '5.8.3.', '630', '126', '84220', '42162'):
        if expected not in text:
            raise ValueError('Missing AXPY PDF content: ' + expected)
    differences = subprocess.check_output(['git', 'diff', '--name-status', '85acd66', '--',
        'results', 'docs/monografia/REVISAO*'], cwd=ROOT, text=True)
    if any(not line.startswith('A\t') for line in differences.splitlines()):
        raise ValueError('Pre-existing scientific results or revisions changed')
    main = subprocess.check_output(['git', 'rev-parse', 'main'], cwd=ROOT, text=True).strip()
    if main != 'cc5406b79a1fac9446c6e0a25920243f82662a6e':
        raise ValueError('Unexpected main ref; do not rewrite it')
    result = dict(status='PASS', checked_utc=datetime.now(timezone.utc).isoformat(),
        unit_tests=int(counts[1]), unit_seconds=float(counts[2]), skips=0, regression_cases=23,
        two_session_archives='VERIFIED', scientific_samples=630, scientific_warmups=126,
        configurations_per_session=21, frozen_before_holdout=True,
        recomputed_policies_and_bootstrap=True, archived_previous_revision_verified=True,
        candidate_sha256=a['runs'][0]['candidate_sha256'],
        pdf_pages=len(pages), word_tables=len(word.tables), word_images=len(word.inline_shapes),
        a4_margins_and_page_field_verified=True, main_unchanged=main,
        study_report_sha256=sha(analysis / 'report.json'), manuscript_manifest_sha256=sha(ROOT / 'docs/monografia/AXPY_SCIENTIFIC_2026-11-16_MANIFEST.json'),
        preflight_corrections=['Canonicalized macOS /var versus /private/var test paths',
                              'Used declared 10000 inner calls for microtests to avoid zero-resolution timings'],
        limitations='Native Word/ABNT review not certified; no new LLM or promotion; low battery while charging and uncontrolled thermals; prefix-only amortization')
    write_json(output / 'report.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.output.resolve())))
