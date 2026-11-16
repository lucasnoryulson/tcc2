"""Archive tests, preserved-history checks and integrity checks of Mac deliverables."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.benchmark_scaling import write_json


def validate(output):
    output.mkdir(parents=True, exist_ok=False)
    checks = []
    env = dict(os.environ, PATH='/opt/homebrew/opt/llvm/bin:' + os.environ.get('PATH', ''))
    commands = [('unittest', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_*.py', '-q'])]
    for name in ('adaptive_strategy_planner_v01', 'autotuning_selector_v01',
                 'compiler_feedback_analyzer_v01', 'compiler_feedback_analyzer_v02',
                 'coordinator_v02', 'performance_selector_v02'):
        commands.append((name, [sys.executable, '-B', f'scripts/test_{name}_regression.py']))
    commands += [('static_isolation', [sys.executable, '-B', 'scripts/test_static_analysis_variant_isolation.py']),
                 ('linux_wrapper_syntax', ['bash', '-n', 'scripts/profile_linux_followup.sh'])]
    for name, command in commands:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        (output / (name + '.log')).write_text(result.stdout + result.stderr)
        checks.append(dict(name=name, command=command, returncode=result.returncode))
        print(name, result.returncode, flush=True)
    history = subprocess.run(['git', 'diff', '--name-status', '0d3b547', '--', 'results',
                              'docs/monografia/REVISAO_PUBLICACAO.md', 'docs/monografia/REVISAO_PUBLICACAO.docx',
                              'docs/monografia/REVISAO_PUBLICACAO.pdf'], cwd=ROOT, capture_output=True, text=True, check=True)
    changed_history = [line for line in history.stdout.splitlines() if not line.startswith('A\t')]
    checks.append(dict(name='previous_results_and_manuscript_preserved', changed_existing=changed_history,
                       returncode=int(bool(changed_history))))
    manifest_file = ROOT / 'docs/monografia/MAC_EVALUATION_2026-11-16_MANIFEST.json'
    manifest = json.loads(manifest_file.read_text())
    for name, expected in (manifest['previous_manuscript_sha256'] | manifest['files']).items():
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError('Changed manuscript artifact: ' + name)
    from docx import Document
    from pypdf import PdfReader
    base = ROOT / 'docs/monografia/REVISAO_EXPERIMENTAL_MAC_2026-11-16'
    with ZipFile(base.with_suffix('.docx')) as archive:
        if archive.testzip() is not None:
            raise ValueError('Corrupt Word package')
    word = Document(base.with_suffix('.docx'))
    pdf = PdfReader(base.with_suffix('.pdf'))
    text = '\n'.join(page.extract_text() for page in pdf.pages)
    for needle in ('5.8.', '5.9.', '5.10.', '5.11.', 'Amdahl', 'Roofline', '14/16'):
        if needle not in text:
            raise ValueError('Missing PDF content: ' + needle)
    checks.append(dict(name='academic_exports', returncode=0, pdf_pages=len(pdf.pages),
                       word_tables=len(word.tables), word_images=len(word.inline_shapes)))
    promoted = list((ROOT / 'results/pipeline_cost/mac_m5_2026-11-16').glob('promoted-*/*/manifest.json'))
    for path in promoted:
        data = json.loads(path.read_text())
        for name, record in data['files'].items():
            if hashlib.sha256((path.parent / name).read_bytes()).hexdigest() != record['sha256']:
                raise ValueError('Changed promoted artifact: ' + str(path.parent / name))
        if hashlib.sha256((path.parent / 'parallel.c').read_bytes()).hexdigest() != data['candidate_sha256']:
            raise ValueError('Candidate hash mismatch')
    checks.append(dict(name='promotion_manifests', returncode=0, count=len(promoted)))
    result = dict(status='PASS' if all(c['returncode'] == 0 for c in checks) else 'FAIL',
                  checked_utc=datetime.now(timezone.utc).isoformat(), checks=checks,
                  limitations='Software and artifact checks; no native Word layout certification or proof of general numerical equivalence')
    write_json(output / 'report.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.output.resolve())
    print(result['status'])
    raise SystemExit(result['status'] != 'PASS')
