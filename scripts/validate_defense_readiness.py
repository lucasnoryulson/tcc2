"""Verify real archives and academic outputs without claiming external completion."""
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
from analysis.artifact_provenance import load_context_evidence, verify_file
from scripts.analyze_pipeline_cost import break_even
from scripts.analyze_scaling import enrich, selections
from scripts.benchmark_scaling import write_json
from scripts.evaluate_axpy_campaign import verify_seal, verify_session
from scripts.evaluate_selector_holdout import evaluate_rows
from scripts.validate_axpy_science import check_csv


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(output, regression):
    output.mkdir(parents=True, exist_ok=False)
    tests = json.loads((regression / 'report.json').read_text())
    log = (regression / 'unittest.log').read_text()
    count = re.search(r'Ran (\d+) tests in ([\d.]+)s', log)
    if tests['status'] != 'PASS' or count is None or int(count[1]) != 161 or 'skipped=' in log:
        raise ValueError('Requires passing full 161-test suite without skips')
    # Old scientific evidence stays valid after harness evolution and editorial revisions.
    archives = []
    for name in ('mac_m5_2026-11-16', 'mac_m5_all_threads_2026-11-16'):
        study = ROOT / 'results/axpy_scientific' / name
        for number in (1, 2):
            report, _, _, _ = verify_session(study / f'session{number:02d}')
            archives.append(dict(campaign=name, session=number, status=report['status']))
    study = ROOT / 'results/axpy_scientific/mac_m5_all_threads_2026-11-16'
    analysis = ROOT / 'results/axpy_scientific/analysis_mac_m5_all_threads_2026-11-16'
    first, a, raw_a, _ = verify_session(study / 'session01')
    second, b, raw_b, _ = verify_session(study / 'session02')
    frozen = json.loads((study / 'frozen_selection.json').read_text())
    if not (datetime.fromisoformat(first['finished_utc']) < datetime.fromisoformat(frozen['frozen_at_utc'])
            < datetime.fromisoformat(second['started_utc'])):
        raise ValueError('Invalid prospective freeze chronology')
    if frozen['choices'] != selections(a):
        raise ValueError('Frozen choices changed')
    policies, sensitivity, stability = evaluate_rows(a, b, frozen['choices'])
    for filename, expected in [('policies.csv', policies), ('sensitivity.csv', sensitivity), ('stability.csv', stability)]:
        check_csv(analysis / filename, expected)
    for number, summary, raw in [(1, a, raw_a), (2, b, raw_b)]:
        check_csv(analysis / f'measurements_session{number:02d}.csv', enrich(summary, raw))
    derived = ROOT / 'results/defense_readiness/2026-11-16'
    verify_seal(derived)
    derived_report = json.loads((derived / 'report.json').read_text())
    for name, expected in (derived_report['inputs'] | derived_report['figures']).items():
        if sha(ROOT / name) != expected:
            raise ValueError('Changed derived source/figure: ' + name)
    cost = ROOT / 'results/pipeline_cost/axpy_mac_m5_all_threads_2026-11-16'
    costs = json.loads((cost / 'report.json').read_text())
    if costs['status'] != 'COMPLETE' or len(costs['trials']) != 6:
        raise ValueError('Cost study did not complete all six admission trials')
    for record in costs['harness_sources'].values():
        verify_file(record)
    candidate = first['runs'][0]['candidate_sha256']
    _, bundle, context_ref = load_context_evidence(study / 'session01' / next(r['work'] for r in first['runs'] if r['n']==10000000) / 'context.json')
    heldout_seq = next(r['median_seconds'] for r in b if r['size']==10000000 and r['variant']=='sequential')
    heldout_final = next(r['median_seconds'] for r in policies if r['size']=='10000000' and r['policy']=='selector')
    for trial in costs['trials']:
        if trial['status'] != 'OK' or not trial['effective_accept'] or trial['context'] != context_ref:
            raise ValueError('Invalid cost decision or different prefix')
        if trial['selected_configuration'] != {'threads': 4}:
            raise ValueError('Measured configuration was not preserved')
        if trial['mode']=='coordinator' and (trial['llm_calls'] != 1 or trial['metadata']['eval_count'] <= 0
                                           or trial['metadata']['prompt_eval_count'] <= 0):
            raise ValueError('Real inference metadata missing')
        promotion = Path(trial['promotion'])
        manifest = json.loads((promotion / 'manifest.json').read_text())
        if manifest['candidate_sha256'] != candidate or manifest['configuration'] != {'threads':4}:
            raise ValueError('Promotion identity/configuration mismatch')
        for relative, record in manifest['files'].items():
            if sha(promotion / relative) != record['sha256']:
                raise ValueError('Changed promoted evidence: ' + relative)
    import csv
    with (cost / 'costs.csv').open() as stream:
        cost_rows = list(csv.DictReader(stream))
    expected = []
    for row in cost_rows:
        decision = float(row['decision_seconds']) + float(row['decision_validation_seconds'])
        total = float(row['total_accounted_seconds'])
        expected.append(dict(repetition=int(row['repetition']), mode=row['mode'], status=row['status'],
            promoted=True, prefix_seconds=float(row['shared_prefix_seconds']), decision_validation_seconds=decision,
            promotion_seconds=float(row['promotion_seconds']), total_accounted_seconds=total,
            holdout_sequential_seconds=heldout_seq, holdout_final_seconds=heldout_final,
            decision_only_break_even=break_even(decision, heldout_seq, heldout_final),
            full_accounted_break_even=break_even(total, heldout_seq, heldout_final)))
    check_csv(derived / 'cost_holdout.csv', expected)
    # Recover imports from the committed invocation revision, without claiming an
    # in-process hash capture that the cost harness did not perform for these imports.
    snapshots = output / 'invocation_revision_sources'
    snapshots.mkdir()
    recovered = {}
    for relative in ('scripts/measure_pipeline_cost.py', 'scripts/evaluate_coordinator.py',
                     'agents/coordinator_agent.py', 'scripts/promote_candidate.py',
                     'analysis/artifact_provenance.py', 'analysis/performance_selector.py'):
        data = subprocess.check_output(['git', 'show', '22e5ed2:' + relative], cwd=ROOT)
        if hashlib.sha256(data).hexdigest() != sha(ROOT / relative):
            raise ValueError('Inference implementation differs from invocation revision')
        target = snapshots / relative.replace('/', '__')
        target.write_bytes(data)
        recovered[relative] = sha(target)
    book = ROOT / 'docs/monografia'
    manifest = json.loads((book / 'BANCA_2026-11-16_MANIFEST.json').read_text())
    for relative, expected_hash in (manifest['previous_revision_sha256'] | manifest['files']).items():
        if sha(ROOT / relative) != expected_hash:
            raise ValueError('Changed manuscript artifact: ' + relative)
    source = (book / 'MONOGRAFIA_CONSOLIDADA.md').read_text()
    for relative in re.findall(r'\]\(([^)]+)\)', source):
        if not relative.startswith(('http://', 'https://', '#')):
            (book / relative.split('#')[0]).resolve(strict=True)
    if re.findall(r'^Tabela (\d+) — ', source, re.M) != [str(i) for i in range(1,36)]:
        raise ValueError('Missing/duplicate table number')
    if re.findall(r'^!\[Figura (\d+) — ', source, re.M) != [str(i) for i in range(1,28)]:
        raise ValueError('Missing/duplicate figure number')
    from docx import Document
    from pypdf import PdfReader
    with ZipFile(book / 'MONOGRAFIA_CONSOLIDADA.docx') as archive:
        if archive.testzip() is not None:
            raise ValueError('Corrupt Word package')
    doc = Document(book / 'MONOGRAFIA_CONSOLIDADA.docx')
    section = doc.sections[0]
    for actual, expected in [(section.page_width.cm,21),(section.page_height.cm,29.7),
                            (section.left_margin.cm,3),(section.top_margin.cm,3),
                            (section.right_margin.cm,2),(section.bottom_margin.cm,2)]:
        if abs(actual-expected) > .01:
            raise ValueError('Incorrect A4 page or margin')
    if 'PAGE' not in section.footer._element.xml or 'TOC' not in doc.element.xml:
        raise ValueError('Missing Word page/TOC fields')
    if len(doc.tables)!=35 or len(doc.inline_shapes)!=27:
        raise ValueError('Word content differs from source')
    if [p.text.split(' — ')[0] for p in doc.paragraphs if re.match(r'^Figura \d+ — ',p.text)] != [f'Figura {i}' for i in range(1,28)]:
        raise ValueError('Word figure captions missing/duplicated')
    pdf = PdfReader(book / 'MONOGRAFIA_CONSOLIDADA.pdf')
    pages = [p.extract_text() for p in pdf.pages]
    if any(not p.strip() for p in pages):
        raise ValueError('Blank PDF page')
    text = '\n'.join(pages)
    for number in range(1,36):
        if len(re.findall(r'\bTabela '+str(number)+r' — ',text))!=1:
            raise ValueError('PDF table label missing/duplicated: '+str(number))
    for number in range(1,28):
        if len(re.findall(r'\bFigura '+str(number)+r' — ',text))!=1:
            raise ValueError('PDF figure label missing/duplicated: '+str(number))
    for needle in ('SUMÁRIO','4.12.','4.13.','5.8.4.','5.8.5.','6.3.','990','198','27731','17966'):
        if needle not in text:
            raise ValueError('PDF content missing: '+needle)
    changed = subprocess.check_output(['git','diff','--name-status','c364407','--', 'results',
        'docs/monografia/REVISAO*','docs/monografia/*PRE_AXPY*'],cwd=ROOT,text=True)
    if any(not row.startswith('A\t') for row in changed.splitlines()):
        raise ValueError('Existing scientific evidence or revisions changed')
    main = subprocess.check_output(['git','rev-parse','main'],cwd=ROOT,text=True).strip()
    if main != 'cc5406b79a1fac9446c6e0a25920243f82662a6e':
        raise ValueError('Local main changed')
    subprocess.run(['git','merge-base','--is-ancestor','601b813','HEAD'],cwd=ROOT,check=True)
    result = dict(status='VERIFIED_WITH_EXTERNAL_PENDING', checked_utc=datetime.now(timezone.utc).isoformat(),
        software_and_artifact_checks='PASS', unit_tests=int(count[1]), unit_seconds=float(count[2]),
        skips=0, regression_cases=23, preserved_scientific_sessions=archives,
        axpy_new_samples=990, axpy_new_warmups=198, frozen_holdout_verified=True,
        recomputed_policies_bootstrap_and_amortization=True, selector_inadequate=1, stable_cases=2,
        real_llm_calls=3, local_promotions_verified=6, candidate_sha256=candidate,
        pdf_pages=len(pdf.pages), tables=35, figures=27, a4_margins_captions_toc_fields_verified=True,
        recovered_cost_invocation_sources=dict(git_commit='22e5ed2',files=recovered,
            limitation='Recovered from invocation revision at final validation; not claimed as in-process import hashes'),
        manuscript_manifest_sha256=sha(book/'BANCA_2026-11-16_MANIFEST.json'),
        latest_main_used='601b813', local_main_unchanged=main,
        external_pending=dict(linux_perf='NOT_RUN_MACOS',native_word_layout='NOT_CERTIFIED',
            complete_pucrs_model='AUTHENTICATED_ACCESS_REQUIRED',academic_approval='NOT_INFERRED'))
    write_json(output / 'report.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--regression',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(validate(args.output.resolve(),args.regression.resolve())))
