"""Technical tests: mock model transports are not scientific LLM observations."""

import argparse
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import evaluate_diagnostics as study
from scripts.report_publication import verify_diagnostics


class DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = study.verify_catalog(study.DEFAULT_CATALOG)

    def test_catalog_family_split_and_baseline_rubric(self):
        self.assertEqual(len(self.catalog['cases']), 24)
        families = {}
        for case in self.catalog['cases']:
            families.setdefault(case['family'], set()).add(case['split'])
            result = study.score(case, study.model_view(case), study.rules(study.model_view(case)))
            self.assertTrue(result['cause_action_correct'], case['id'])
            self.assertEqual(result['unsupported_claims'], 0)
        self.assertTrue(all(len(splits) == 1 for splits in families.values()))
        # This verifies annotation/rule consistency, not independent scientific accuracy.

    def test_prompt_excludes_oracle_paths_and_answer_fields(self):
        case = copy.deepcopy(self.catalog['cases'][0])
        case['oracle']['secret'] = 'ANSWER_SENTINEL'
        case['evidence']['observations'][0]['data'].update(
            path='/home/operator/NO_PARALLEL_GAIN/file', recommendation='ANSWER_SENTINEL')
        user = study.prompt(case)['user']
        self.assertNotIn('ANSWER_SENTINEL', user)
        self.assertNotIn('/home/operator', user)
        self.assertNotIn('oracle', user)
        self.assertNotIn('development', user)
        self.assertNotIn(case['id'], user)

    def test_ablation_and_support_use_only_visible_facts(self):
        case = next(case for case in self.catalog['cases'] if case['evidence']['analysis'])
        full, ablated = study.model_view(case), study.model_view(case, True)
        self.assertEqual(ablated['analysis'], [])
        self.assertEqual(full['observations'], ablated['observations'])
        record = full['analysis'][0]
        field, value = next((key, value) for key, value in record['data'].items() if isinstance(value, str))
        output = {'cause': 'UNDETERMINED', 'action': 'ESCALATE', 'abstain': True,
                  'claims': [{'fact_id': record['id'], 'field': field, 'value': value}]}
        self.assertEqual(study.score(case, full, output)['unsupported_claims'], 0)
        self.assertEqual(study.score(case, ablated, output)['unsupported_claims'], 1)

    def test_schema_claim_types_and_dangerous_invalid_proposal(self):
        case = self.catalog['cases'][0]
        view = study.model_view(case)
        output = study.rules(view)
        self.assertTrue(study.validate(output))
        output['claims'] = [{'fact_id': 'unknown', 'field': 'value', 'value': 999}]
        self.assertEqual(study.score(case, view, output)['unsupported_claims'], 1)
        output['action'] = 'PROMOTE_CANDIDATE'
        self.assertFalse(study.validate(output))
        self.assertTrue(study.score(case, view, output)['dangerous_proposal'])
        output['claims'][0]['value'] = float('nan')
        self.assertFalse(study.validate(output))
        self.assertFalse(study.validate({'cause': 'COMPILE_ERROR'}))

    def test_catalog_and_snapshot_tamper_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = directory / 'catalog.json'
            catalog = copy.deepcopy(self.catalog)
            catalog['cases'] = [catalog['cases'][0]]
            evidence = directory / 'evidence.csv'
            evidence.write_text('original')
            catalog['cases'][0]['provenance'] = [{'snapshot': evidence.name, 'sha256': study.digest(evidence)}]
            study.write_json(path, catalog)
            path.with_suffix('.sha256').write_text(study.digest(path))
            study.verify_catalog(path)
            evidence.write_text('tampered')
            with self.assertRaisesRegex(ValueError, 'Evidence snapshot'):
                study.verify_catalog(path)
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Frozen catalog'):
                study.verify_catalog(path)

    def test_json_numbers_are_equivalent_but_booleans_and_strings_are_not(self):
        case = self.catalog['cases'][0]
        view = study.model_view(case)
        output = study.rules(view)
        output['claims'] = [{'fact_id': 'f1', 'field': 'samples_per_configuration', 'value': 15.0}]
        self.assertEqual(study.score(case, view, output)['unsupported_claims'], 0)
        output['claims'][0]['value'] = '15'
        self.assertEqual(study.score(case, view, output)['unsupported_claims'], 1)
        view['observations'][0]['data']['flag'] = True
        output['claims'] = [{'fact_id': 'f1', 'field': 'flag', 'value': 1}]
        self.assertEqual(study.score(case, view, output)['unsupported_claims'], 1)
    def test_timeout_no_retry_and_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(catalog=study.DEFAULT_CATALOG, split='development', case_ids=['d01'],
                output=Path(tmp) / 'run', model='SIMULATED_TRANSPORT_FOR_TEST', endpoint='http://invalid',
                baseline_only=False, repetitions=1, timeout=1, seed=1, num_ctx=4096, num_predict=128)
            with patch.object(study, 'call_model', side_effect=TimeoutError('timed out')) as transport, \
                 patch.object(study.urllib.request, 'urlopen', side_effect=OSError('technical simulation')):
                report = study.evaluate(args)
            self.assertEqual(transport.call_count, 1)
            self.assertEqual(report['status'], 'INCOMPLETE_TIMEOUT')
            self.assertEqual(len(report['trials']), 3)
            model_groups = [group for group in report['groups'] if group['mode'] != 'rules']
            self.assertTrue(all(group['attempts'] == 1 and group['cause_correct_rate'] == 0 for group in model_groups))
            self.assertEqual(sum(group['timeouts'] for group in model_groups), 1)
            self.assertEqual(sum(group['not_run_count'] for group in model_groups), 1)
            for trial in report['trials']:
                self.assertTrue((args.output / next(path.name for path in args.output.iterdir() if path.is_dir() and trial['mode'] in path.name) / 'prompt.json').exists())

    def test_output_collision_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(catalog=study.DEFAULT_CATALOG, split='development', case_ids=['d01'], output=Path(tmp))
            with self.assertRaises(FileExistsError):
                study.evaluate(args)

    def test_archived_diagnosis_is_rescored_and_raw_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(catalog=study.DEFAULT_CATALOG, split='development', case_ids=['d01'],
                output=Path(tmp) / 'run', model='TECHNICAL_RULES_TEST', endpoint='http://invalid',
                baseline_only=True, repetitions=1, timeout=1, seed=2026, num_ctx=4096, num_predict=128)
            data = study.evaluate(args)
            self.assertEqual(verify_diagnostics(args.output)['status'], 'BASELINE_ONLY')
            trial = data['trials'][0]
            work = next(path for path in args.output.iterdir() if path.is_dir())
            trial['cause_action_correct'] = False
            study.write_json(args.output / 'results.json', data)
            study.write_json(work / 'trial.json', trial)
            with self.assertRaisesRegex(ValueError, 'score differs'):
                verify_diagnostics(args.output)
            trial['cause_action_correct'] = True
            study.write_json(args.output / 'results.json', data)
            study.write_json(work / 'trial.json', trial)
            for field, value, message in [('metadata', {'eval_count': 99}, 'metadata differs'),
                                          ('ablation_effective', True, 'derived fields differ')]:
                original = trial[field]
                trial[field] = value
                study.write_json(args.output / 'results.json', data)
                study.write_json(work / 'trial.json', trial)
                with self.assertRaisesRegex(ValueError, message):
                    verify_diagnostics(args.output)
                trial[field] = original
            study.write_json(args.output / 'results.json', data)
            study.write_json(work / 'trial.json', trial)
            (work / 'raw_response.json').write_text('tampered')
            with self.assertRaisesRegex(ValueError, 'Raw diagnostic response changed'):
                verify_diagnostics(args.output)


if __name__ == '__main__':
    unittest.main()
