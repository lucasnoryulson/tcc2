"""Recheck final-patch integration without recollecting historical campaigns."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.artifact_provenance import load_context_evidence
from scripts.analyze_pipeline_cost import analyze
from scripts.benchmark_scaling import write_json
from scripts.evaluate_selector_holdout import evaluate as evaluate_frozen
from scripts.evaluate_selector_sessions import evaluate as evaluate_sessions
from scripts.validate_mac_evaluation import validate


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(output, axpy_run, patch):
    output.mkdir(parents=True, exist_ok=False)
    regression = validate(output / 'regression')
    if regression['status'] != 'PASS':
        raise ValueError('Regression suite failed; inspect regression logs')

    with ZipFile(patch.with_suffix('.zip')) as archive:
        if archive.namelist() != [patch.name] or archive.testzip() is not None:
            raise ValueError('Unexpected or corrupt patch archive')
        if hashlib.sha256(archive.read(patch.name)).hexdigest() != sha(patch):
            raise ValueError('ZIP and standalone patch differ')

    _, bundle, _ = load_context_evidence(axpy_run / 'context.json')
    performance = bundle['performance']
    if (performance['repetitions'], performance['warmups'], performance['seed']) != (15, 3, 2026):
        raise ValueError('Unexpected AXPY sampling protocol')
    if performance['thread_counts'] != [1, 2, 4, 6, 8, 10] or len(performance['measurement_order']) != 126:
        raise ValueError('Incomplete AXPY thread grid or round order')
    cost = analyze(axpy_run)
    if cost['status'] != 'PREPARED' or cost['coordinator_step_seconds'] is not None:
        raise ValueError('AXPY smoke test must not claim an LLM call or promotion')
    write_json(output / 'axpy_cost.json', cost)

    linux = evaluate_sessions(ROOT / 'results/multiplatform/linux_xeon_2026-11-05_p15w3',
        ROOT / 'results/publication/scaling_linux_session02_2026-11-05', output / 'selector_linux')
    archived_path = ROOT / 'results/publication/selector_holdout_linux_2026-11-16'
    archived = json.loads((archived_path / 'report.json').read_text())
    if ({k: v for k, v in linux.items() if k != 'limitation'}
        != {k: v for k, v in archived.items() if k != 'limitation'}
        or (output / 'selector_linux/holdout.csv').read_bytes() != (archived_path / 'holdout.csv').read_bytes()):
        raise ValueError('Linux holdout metrics differ from supplied evidence')
    mac = evaluate_frozen(ROOT / 'results/multiplatform/mac_m5_2026-11-16_selector_frozen.json',
        ROOT / 'results/multiplatform/mac_m5_2026-11-16_p15w3_session02', output / 'selector_mac')
    archived_mac = json.loads((ROOT / 'results/multiplatform/selector_holdout_mac_2026-11-16/report.json').read_text())
    # A new checkout has another evaluation path. Compare all evidence hashes,
    # frozen choices and metrics without rewriting the historical report paths.
    if ({k: v for k, v in mac.items() if k != 'evaluation_campaign'}
        != {k: v for k, v in archived_mac.items() if k != 'evaluation_campaign'}):
        raise ValueError('Pre-existing frozen Mac holdout changed')

    promotion = ROOT / 'results/final-promoted/axpy-mac-2026-11-03/0d44fc52cce0b653dfa5d033bbf81f0a5595a9b6228dc1c8fee72c1abc292a52'
    manifest = json.loads((promotion / 'manifest.json').read_text())
    for relative, record in manifest['files'].items():
        if sha(promotion / relative) != record['sha256']:
            raise ValueError('Changed archived AXPY artifact: ' + relative)
    if sha(promotion / 'parallel.c') != manifest['candidate_sha256']:
        raise ValueError('Archived AXPY candidate identity mismatch')

    directory = ROOT / 'docs/monografia'
    source = directory / 'MONOGRAFIA_CONSOLIDADA.md'
    for relative in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', source.read_text()):
        (directory / relative).resolve(strict=True)
    from docx import Document
    from pypdf import PdfReader
    for path in (source.with_suffix('.docx'), directory / 'CAPA_PUCRS_CONSOLIDADA.docx'):
        with ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError('Corrupt Word package: ' + path.name)
        Document(path)
    word = Document(source.with_suffix('.docx'))
    pdf = PdfReader(source.with_suffix('.pdf'))
    pages = [page.extract_text() for page in pdf.pages]
    text = '\n'.join(pages)
    if any(not page.strip() for page in pages):
        raise ValueError('Blank PDF page')
    for needle in ('5.10.', '5.11.', '5.12.', '14/16', '3.360', '5.929', 'SUMÁRIO'):
        if needle not in text:
            raise ValueError('Missing consolidated PDF content: ' + needle)

    diff = subprocess.run(['git', 'diff', '--name-status', 'a1e4a6e', '--', 'results',
        'docs/monografia/REVISAO*'], cwd=ROOT, capture_output=True, text=True, check=True)
    if any(not line.startswith('A\t') for line in diff.stdout.splitlines()):
        raise ValueError('Pre-existing scientific evidence or manuscript changed')
    main = subprocess.check_output(['git', 'rev-parse', 'main'], cwd=ROOT, text=True).strip()
    if main != 'cc5406b79a1fac9446c6e0a25920243f82662a6e':
        raise ValueError('Unexpected main reference; inspect without rewriting it')
    files = [source, source.with_suffix('.docx'), source.with_suffix('.pdf'),
             directory / 'CAPA_PUCRS_CONSOLIDADA.docx', directory / 'referencias_consolidada.bib']
    result = dict(status='PASS', checked_utc=datetime.now(timezone.utc).isoformat(),
        base_commit='a1e4a6e', input_patch_sha256=sha(patch), zip_contains_same_patch=True,
        main_unchanged=main, regression=regression,
        axpy=dict(run=str(axpy_run), status=cost['status'], correctness='PASS', threads=performance['thread_counts'],
                  repetitions=15, warmups=3, seed=2026, measured_samples=105, warmup_samples=21,
                  candidate_sha256=performance['provenance']['inputs']['candidate']['sha256']),
        linux_holdout=dict(status=linux['status'], matches_supplied_metrics=True, cases=linux['cases']),
        mac_holdout=dict(status=mac['status'], unchanged=True, cases=mac['cases'], stable_cases=mac['stable_cases'],
                         evaluation_path_relocated=mac['evaluation_campaign'] != archived_mac['evaluation_campaign']),
        historical_axpy=dict(candidate_sha256=manifest['candidate_sha256'], verified_files=len(manifest['files']),
                             original_contract_not_current=True),
        consolidated=dict(pdf_pages=len(pages), word_tables=len(word.tables), word_images=len(word.inline_shapes)),
        files={str(path.relative_to(ROOT)): sha(path) for path in files},
        limitations='Technical AXPY smoke test, not a scientific campaign or live LLM promotion; '
                    'historical absolute paths not rewritten; no native Office layout certification')
    write_json(output / 'report.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--axpy-run', required=True, type=Path)
    parser.add_argument('--patch', required=True, type=Path)
    args = parser.parse_args()
    result = check(args.output.resolve(), args.axpy_run.resolve(), args.patch.resolve())
    print(json.dumps({'status': result['status'], 'consolidated': result['consolidated']}))
