#!/usr/bin/env python3

import contextlib
import copy
import csv
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents import context_builder, coordinator_agent
from analysis import artifact_provenance as provenance
from analysis import performance_selector as selector
from scripts import compile_correctness_gate as correctness
from scripts import performance_gate as performance
from scripts.test_toolchain import find_openmp_compiler


class GateContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.source = self.work / 'dot_product.c'
        self.candidate = self.work / 'dot_product_openmp.c'
        self.driver = self.work / 'dot_driver.c'
        for target, source in (
            (self.source, ROOT / 'analysis/fixtures/dot_product.c'),
            (self.candidate, ROOT / 'generated/dot_product_openmp.c'),
            (self.driver, ROOT / 'analysis/fixtures/dot_driver.c'),
        ):
            shutil.copyfile(source, target)
        self.benchmark_driver = self.work / 'benchmark_driver.c'
        self.benchmark_driver.write_text('#include <stdio.h>\nint main(void) { return 0; }\n')
        self.report_path = self.work / 'correctness.json'
        self.performance_path = self.work / 'performance.json'
        self.csv_path = self.work / 'performance.csv'
        self.selection_path = self.work / 'selection.json'
        self.compiler = find_openmp_compiler() or 'gcc'

    def run_cli(self, *extra):
        return subprocess.run(
            [sys.executable, '-B', str(ROOT / 'scripts/compile_correctness_gate.py'),
             '--sequential', str(self.source), '--candidate', str(self.candidate),
             '--driver', str(self.driver), '--compiler', self.compiler, '--threads', '1', '2',
             '--build-dir', str(self.work / 'build'), '--output', str(self.report_path), *extra],
            capture_output=True, text=True, timeout=30,
        )

    def gate_report(self, failed_stage=None):
        index = 0

        def compile_mock(compiler, driver, source, binary, openmp):
            nonlocal index
            code = int(index == failed_stage)
            index += 1
            if not code:
                binary.write_bytes(b'mock executable')
            return {'command': [compiler, str(driver), str(source)],
                    'returncode': code, 'stdout': '', 'stderr': ''}

        executions = [{'returncode': 0, 'stdout': '1.0', 'stderr': ''} for _ in range(3)]
        if failed_stage in (2, 3):
            executions[failed_stage - 2]['returncode'] = 1
        with patch.object(correctness, 'compile_program', side_effect=compile_mock), \
                patch.object(correctness, 'execute_program', side_effect=executions), \
                contextlib.redirect_stdout(io.StringIO()):
            return correctness.run_gate(
                self.source, self.candidate, self.driver, self.work / 'build', self.compiler, [1, 2],
            )

    def bind_performance(self, report=None, candidate_time=0.5, one_thread_time=1.0):
        if report is None:
            report = self.gate_report()
        self.report_path.write_text(json.dumps(report))

        def compile_mock(compiler, driver, source, binary, openmp):
            binary.write_bytes(b'mock benchmark executable')
            return subprocess.CompletedProcess([compiler, str(driver), str(source)], 0, '', '')

        with patch.object(performance, 'compile_program', side_effect=compile_mock), \
                patch.object(performance, 'benchmark', side_effect=[
                    {'times': [1.0] * 5}, {'times': [one_thread_time] * 5},
                    {'times': [candidate_time] * 5},
                ]), contextlib.redirect_stdout(io.StringIO()):
            measured = performance.run_gate(
                self.source, self.candidate, self.benchmark_driver, self.work / 'performance',
                self.compiler, [1, 2], self.report_path, self.csv_path,
            )
        self.performance_path.write_text(json.dumps(measured))
        _, rows, reference = provenance.load_performance_report(self.performance_path, self.csv_path)
        selection = selector.select_configuration(rows)
        selection['evidence'] = {
            'performance_report': reference,
            'candidate_id': measured['provenance']['candidate_id'],
            'campaign_id': measured['provenance']['campaign_id'],
        }
        self.selection_path.write_text(json.dumps(selection))
        return report, measured, selection

    def build_context(self):
        output = (ROOT / 'analysis/output').resolve()
        return context_builder.build_context(
            self.source.resolve(), self.candidate.resolve(), output / 'dot_analysis.json',
            output / 'dot_dependences.json', output / 'dot_patterns.json',
            output / 'dot_strategy.json', self.selection_path.resolve(),
            correctness_file=self.report_path.resolve(),
        )

    def test_real_dot_gate_and_context(self):
        if find_openmp_compiler() is None:
            self.skipTest('An OpenMP compiler is required for the real integration test.')
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(self.report_path.read_text())
        self.bind_performance(report)
        context = self.build_context()
        self.assertEqual(context['validation']['correctness_gate'], 'PASS')
        self.assertEqual(report['validated_threads'], [1, 2])
        self.assertEqual(context['source']['candidate_sha256'], provenance.sha256(self.candidate.read_bytes()))
        self.assertEqual(context['source']['candidate_id'], report['provenance']['candidate_id'])
        output = ROOT / 'analysis/output'
        context_path = self.work / 'context.json'
        result = subprocess.run(
            [sys.executable, '-B', str(ROOT / 'agents/context_builder.py'),
             '--source', str(self.source), '--candidate', str(self.candidate),
             '--static', str(output / 'dot_analysis.json'),
             '--dependences', str(output / 'dot_dependences.json'),
             '--patterns', str(output / 'dot_patterns.json'),
             '--strategy', str(output / 'dot_strategy.json'),
             '--selection', str(self.selection_path),
             '--correctness', str(self.report_path), '--output', str(context_path)],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(context_path.read_text()), context)

    def test_real_incorrect_candidate(self):
        if find_openmp_compiler() is None:
            self.skipTest('An OpenMP compiler is required for the real integration test.')
        self.candidate.write_text('double kernel_dot(int n, const double *a, const double *b) { return 0; }\n')
        result = self.run_cli()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report, _ = provenance.load_correctness_report(self.report_path, self.source, self.candidate)
        self.assertEqual(report['status'], 'FAIL')
        with self.assertRaises(ValueError):
            performance.run_gate(self.source, self.candidate, self.benchmark_driver,
                                 self.work / 'performance', self.compiler, [1], self.report_path, self.csv_path)

    def test_compile_and_runtime_failures_do_not_pass(self):
        for failed_stage in range(4):
            with self.subTest(stage=failed_stage):
                report = self.gate_report(failed_stage)
                self.report_path.write_text(json.dumps(report))
                loaded, _ = provenance.load_correctness_report(self.report_path, self.source, self.candidate)
                self.assertEqual(loaded['status'], 'FAIL')

    def test_missing_inputs_or_compiler_invalidate_previous_pass(self):
        for extra in (('--candidate', str(self.work / 'missing.c')),
                      ('--compiler', str(self.work / 'missing-compiler'))):
            self.report_path.write_text(json.dumps(self.gate_report()))
            result = self.run_cli(*extra)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(self.report_path.read_text())['status'], 'FAIL')

    def test_report_cannot_overwrite_source(self):
        original = self.source.read_bytes()
        result = self.run_cli('--output', str(self.source))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.source.read_bytes(), original)

    def test_bare_pass_legacy_and_inconsistent_reports_are_rejected(self):
        valid, _, _ = self.bind_performance()
        bad_reports = [{'status': 'PASS'}, [], {**valid, 'status': []}, {**valid, 'version': '0.1'}]
        for section in ('compilation', 'execution', 'validation', 'provenance', 'thread_results'):
            report = copy.deepcopy(valid)
            del report[section]
            bad_reports.append(report)
        for section, key, value in (('compilation', 'candidate', {'returncode': 1}),
                                    ('validation', 'correct', False)):
            report = copy.deepcopy(valid)
            report[section][key] = value
            bad_reports.append(report)
        for report in bad_reports:
            with self.subTest(report=report), self.assertRaises(ValueError):
                self.report_path.write_text(json.dumps(report))
                self.build_context()

    def test_changed_inputs_are_rejected_even_at_the_same_path(self):
        self.bind_performance()
        for path in (self.source, self.candidate, self.driver, self.benchmark_driver):
            original = path.read_bytes()
            path.write_bytes(original + b'\n/* changed after measurement */\n')
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'SHA-256'):
                self.build_context()
            path.write_bytes(original)

    def test_changed_snapshot_or_binary_is_rejected(self):
        _, measured, _ = self.bind_performance()
        paths = [Path(measured['provenance']['inputs']['candidate']['snapshot']),
                 Path(measured['binaries']['candidate']['path'])]
        for path in paths:
            original = path.read_bytes()
            path.write_bytes(original + b'changed')
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'SHA-256'):
                self.build_context()
            path.write_bytes(original)

    def test_changed_csv_is_rejected(self):
        self.bind_performance()
        self.csv_path.write_text(self.csv_path.read_text().replace('0.5', '0.4'))
        with self.assertRaisesRegex(ValueError, 'CSV'):
            provenance.load_performance_report(self.performance_path, self.csv_path)

    def test_changed_selection_is_rejected(self):
        _, _, selection = self.bind_performance()
        selection['recommended']['threads'] = 32
        self.selection_path.write_text(json.dumps(selection))
        with self.assertRaisesRegex(ValueError, 'Selection disagrees'):
            self.build_context()

    def test_changed_raw_measurements_are_rejected(self):
        _, measured, _ = self.bind_performance()
        measured['measurements'][1]['times'] = [0.1] * 5
        self.performance_path.write_text(json.dumps(measured))
        with self.assertRaisesRegex(ValueError, 'CSV disagrees'):
            provenance.load_performance_report(self.performance_path)

    def test_changed_performance_report_reference_is_rejected(self):
        _, measured, _ = self.bind_performance()
        measured['repetitions'] = 20
        self.performance_path.write_text(json.dumps(measured))
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            self.build_context()

    def test_mixed_campaigns_are_rejected(self):
        self.bind_performance()
        another = self.gate_report()
        self.report_path.write_text(json.dumps(another))
        with self.assertRaisesRegex(ValueError, 'evidence disagree'):
            self.build_context()

    def test_coordinator_binds_decision_to_its_input_context(self):
        self.bind_performance()
        context = self.build_context()
        context_path = self.work / 'context.json'
        context_path.write_text(json.dumps(context))
        decision_path = self.work / 'decision.json'
        decision = {
            'decision': 'ACCEPT', 'next_action': 'PROMOTE_CANDIDATE', 'risk': 'LOW',
            'recommended_threads': context['performance']['selection']['recommended']['threads'],
        }
        argv = ['coordinator_agent.py', str(context_path), '--output', str(decision_path)]
        with patch.object(sys, 'argv', argv), \
                patch.object(coordinator_agent, 'call_ollama', return_value=(decision, {})), \
                contextlib.redirect_stdout(io.StringIO()):
            coordinator_agent.main()
        output = json.loads(decision_path.read_text())
        self.assertEqual(output['evidence']['candidate_id'], context['source']['candidate_id'])
        self.assertEqual(output['evidence']['campaign_id'], context['source']['campaign_id'])
        self.assertEqual(output['evidence']['context'], provenance.file_record(context_path))
        context_path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            provenance.verify_file(output['evidence']['context'])

    def test_unvalidated_threads_are_rejected_before_benchmark(self):
        self.report_path.write_text(json.dumps(self.gate_report()))
        with patch.object(performance, 'benchmark') as benchmark, self.assertRaisesRegex(ValueError, 'every benchmark thread'):
            performance.run_gate(self.source, self.candidate, self.benchmark_driver,
                                 self.work / 'performance', self.compiler, [1, 4], self.report_path, self.csv_path)
        benchmark.assert_not_called()

    def test_changed_toolchain_flags_are_rejected(self):
        report, _, _ = self.bind_performance()
        report['provenance']['compile_flags']['candidate'].append('-ffast-math')
        self.report_path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, 'configuration'):
            self.build_context()

    def test_numeric_validation_must_match_execution_output(self):
        report, _, _ = self.bind_performance()
        report['thread_results'][0]['execution']['stdout'] = '0.0'
        self.report_path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, 'execution output'):
            self.build_context()

    def test_performance_failure_invalidates_previous_pass_report(self):
        self.bind_performance()
        result = subprocess.run(
            [sys.executable, '-B', str(ROOT / 'scripts/performance_gate.py'),
             '--sequential', str(self.source), '--candidate', str(self.candidate),
             '--driver', str(self.benchmark_driver), '--compiler', str(self.work / 'missing-compiler'),
             '--correctness', str(self.report_path), '--build-dir', str(self.work / 'performance'),
             '--csv', str(self.csv_path), '--output', str(self.performance_path)],
            env={**os.environ, 'TCC2_THREAD_COUNTS': '1,2'},
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(self.performance_path.read_text())['status'], 'FAIL')
        with self.assertRaises(ValueError):
            provenance.load_performance_report(self.performance_path, self.csv_path)

    def test_report_for_another_source_is_rejected(self):
        self.bind_performance()
        another = self.work / 'another.c'
        another.write_bytes(self.source.read_bytes())
        with self.assertRaisesRegex(ValueError, 'another sequential'):
            provenance.load_correctness_report(self.report_path, another, self.candidate)

    def test_legacy_selection_has_no_provenance(self):
        _, _, selection = self.bind_performance()
        del selection['evidence']
        self.selection_path.write_text(json.dumps(selection))
        with self.assertRaisesRegex(ValueError, 'no benchmark provenance'):
            self.build_context()

    def test_source_change_during_gate_cannot_pass(self):
        original_execute = correctness.execute_program
        original_source = self.candidate.read_bytes()

        def execute(binary, threads=None):
            if threads is not None:
                self.candidate.write_bytes(original_source + b'\n/* changed during gate */\n')
            return original_execute(binary, threads)

        with patch.object(correctness, 'execute_program', side_effect=execute):
            # Exercise the in-process gate so the injected mutation reaches its final check.
            if find_openmp_compiler() is None:
                self.skipTest('An OpenMP compiler is required.')
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'SHA-256'):
                correctness.run_gate(self.source, self.candidate, self.driver,
                                     self.work / 'mutation', self.compiler, [1, 2])

    def test_nonfinite_correctness_output_is_rejected(self):
        for value in ('nan', 'inf', '-inf', '', 'not-a-number'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                correctness.parse_numeric_output(value)

    def test_invalid_benchmark_times_are_rejected(self):
        for value in ('nan', 'inf', '-inf', '0', '-1', 'not-a-number'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                performance.parse_average_time(f'AVERAGE_SECONDS={value}')

    def test_invalid_thread_counts(self):
        for threads in (0, -1, True, [], [1, 1], [1, -1]):
            with self.subTest(threads=threads), self.assertRaises(ValueError):
                correctness.run_gate(self.source, self.candidate, self.driver,
                                     self.work / 'build', self.compiler, threads)

    def test_performance_status_and_csv(self):
        for candidate_time, expected_status in ((0.5, 'PASS'), (1.0, 'FAIL'), (2.0, 'FAIL')):
            with self.subTest(time=candidate_time):
                _, measured, _ = self.bind_performance(candidate_time=candidate_time)
                self.assertEqual(measured['status'], expected_status)
                with self.csv_path.open() as file:
                    rows = list(csv.DictReader(file))
                self.assertEqual(len(rows), 3)
                self.assertEqual(float(rows[-1]['speedup']), 1.0 / candidate_time)

    def test_real_performance_cli_selector_and_provenance(self):
        if find_openmp_compiler() is None:
            self.skipTest('An OpenMP compiler is required for the CLI integration test.')
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for candidate_time, expected_exit in ((0.5, 0), (2.0, 1)):
            # Controlled timings test CLI/evidence linkage, not actual parallel speedup.
            self.benchmark_driver.write_text(
                '#include <stdio.h>\nint main(void) {\n#ifdef _OPENMP\n'
                f'puts("AVERAGE_SECONDS={candidate_time}");\n'
                '#else\nputs("AVERAGE_SECONDS=1.0");\n#endif\nreturn 0;\n}\n'
            )
            result = subprocess.run(
                [sys.executable, '-B', str(ROOT / 'scripts/performance_gate.py'),
                 '--sequential', str(self.source), '--candidate', str(self.candidate),
                 '--driver', str(self.benchmark_driver), '--compiler', self.compiler,
                 '--correctness', str(self.report_path), '--build-dir', str(self.work / 'performance'),
                 '--csv', str(self.csv_path), '--output', str(self.performance_path)],
                env={**os.environ, 'TCC2_THREAD_COUNTS': '1,2'},
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, expected_exit, result.stdout + result.stderr)
            provenance.load_performance_report(self.performance_path, self.csv_path)
            result = subprocess.run(
                [sys.executable, '-B', str(ROOT / 'analysis/performance_selector.py'), str(self.csv_path),
                 '--performance-report', str(self.performance_path), '--output', str(self.selection_path)],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            context = self.build_context()
            self.assertEqual(context['source']['candidate_id'], 'sha256:' + provenance.sha256(self.candidate.read_bytes()))


if __name__ == '__main__':
    unittest.main()
