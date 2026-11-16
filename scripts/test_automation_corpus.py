"""Regression checks for the explicit standalone safety boundary and live oracles."""
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from analysis.conservative_transform import certify_kernel
from analysis import code_transformer, static_analyzer, strategy_planner
from scripts.evaluate_automation_corpus import CATALOG, driver_text, load_catalog, transform_status
from scripts import evaluate_automation_corpus as corpus_study
from scripts.test_toolchain import find_openmp_compiler


class AutomationCorpus(unittest.TestCase):
    def setUp(self):
        if not shutil.which('clang'):
            self.skipTest('Clang AST required.')
        self.catalog = load_catalog(CATALOG)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)

    def kernel(self, path):
        return static_analyzer.find_kernel_functions(static_analyzer.run_clang(path, []))[0]

    def case(self, identifier):
        return next(case for case in self.catalog['cases'] if case['id'] == identifier)

    def test_transform_crash_or_timeout_is_not_rewarded_as_a_correct_refusal(self):
        refused = {'status': 'REFUSED'}
        supported = {'status': 'SUPPORTED'}
        self.assertEqual(transform_status(1, False, refused, 'UNSUPPORTED_STANDALONE: dependence'), 'REFUSED')
        self.assertEqual(transform_status(1, False, refused, b'UNSUPPORTED_STANDALONE: dependence'), 'REFUSED')
        self.assertEqual(transform_status(1, False, refused, 'Traceback: missing file'), 'ERROR')
        self.assertEqual(transform_status(None, False, refused, 'UNSUPPORTED_STANDALONE: timeout'), 'ERROR')
        self.assertEqual(transform_status(-11, False, refused, 'UNSUPPORTED_STANDALONE: crash'), 'ERROR')
        self.assertEqual(transform_status(0, False, supported, ''), 'ERROR')
        self.assertEqual(transform_status(0, True, refused, ''), 'ERROR')
        self.assertEqual(transform_status(0, True, supported, ''), 'ACCEPTED')

    def manifest(self):
        records = [corpus_study.archive_record(self.work, path) for path in sorted(self.work.rglob('*'))
                   if path.is_file() and path.name != 'archive_manifest.json']
        corpus_study.write_json(self.work / 'archive_manifest.json', records)

    def test_complete_negative_coverage_remains_analyzable(self):
        programs = [dict(id='technical', split='test', expected_support=True, accepted=False,
                         transform_status='REFUSED', functional_inputs=[])]
        coverage = corpus_study.coverage_counts(programs)
        corpus_study.write_json(self.work / 'coverage.json', dict(programs=programs, coverage=coverage))
        corpus_study.write_json(self.work / 'report.json', dict(status='COVERAGE_MISMATCH', measured=False, coverage=coverage))
        self.manifest()
        self.assertEqual(corpus_study.verify_archive(self.work)['report']['coverage']['all']['false_refusals'], 1)

    def test_archive_checks_binary_attribution_core_statistics_and_selection(self):
        programs = [dict(id='technical', split='test', expected_support=True, accepted=True,
                         transform_status='ACCEPTED', functional_inputs=[{'status': 'PASS'}])]
        coverage = corpus_study.coverage_counts(programs)
        corpus_study.write_json(self.work / 'coverage.json', dict(programs=programs, coverage=coverage))
        configs, rows, commands = [], [], []
        for variant, threads, seconds in [('sequential', 1, 3.0), ('pipeline_openmp', 1, 3.0), ('pipeline_openmp', 2, 1.0)]:
            binary = f'technical_{variant}_{threads}'
            configs.append(dict(kernel='technical', size='small', variant=variant, threads=threads, binary=binary))
            output = self.work / (binary + '.stdout')
            output.write_text(f'0\nAVERAGE_SECONDS={seconds}\n')
            commands.append(dict(command=[str(self.work / binary)], returncode=0, threads=threads, stdout={'path': output.name}))
            rows.append(dict(kernel='technical', size='small', variant=variant, threads=threads,
                             repeat=1, seconds=seconds, command_id=len(commands)))
        command_path = self.work / 'commands.jsonl'
        command_path.write_text(''.join(json.dumps(command) + '\n' for command in commands))
        corpus_study.write_json(self.work / 'configurations.json', configs)
        for name in ('samples.csv', 'warmups.csv'):
            corpus_study.write_csv(self.work / name, rows)
        summary = corpus_study.enrich(corpus_study.summarize(rows), rows)
        corpus_study.write_csv(self.work / 'summary.csv', summary)
        corpus_study.write_json(self.work / 'selection.json', corpus_study.selections(summary))
        corpus_study.write_json(self.work / 'report.json', dict(status='COMPLETE', coverage=coverage, measured=True,
            sample_count=3, warmup_count=3, protocol=dict(samples=1, warmups=1)))
        self.manifest()
        self.assertEqual(corpus_study.verify_archive(self.work)['status'], 'VERIFIED')
        original_commands = command_path.read_text()
        commands[-1]['command'] = commands[0]['command']
        command_path.write_text(''.join(json.dumps(command) + '\n' for command in commands))
        self.manifest()
        with self.assertRaisesRegex(ValueError, 'another configuration'):
            corpus_study.verify_archive(self.work)
        command_path.write_text(original_commands)
        wrong = copy.deepcopy(summary)
        wrong[-1]['median_seconds'] = .25
        corpus_study.write_csv(self.work / 'summary.csv', wrong)
        self.manifest()
        with self.assertRaisesRegex(ValueError, 'summary differs'):
            corpus_study.verify_archive(self.work)
        corpus_study.write_csv(self.work / 'summary.csv', summary)
        corpus_study.write_json(self.work / 'selection.json', [])
        self.manifest()
        with self.assertRaisesRegex(ValueError, 'Selection differs'):
            corpus_study.verify_archive(self.work)

    def test_all_28_structural_sources_follow_declared_safety_contract(self):
        cases = self.catalog['cases']
        self.assertEqual(len(cases), 28)
        self.assertEqual(sum(case['expected_support'] for case in cases), 14)
        self.assertEqual({case['split'] for case in cases}, {'development', 'test'})
        for case in cases:
            with self.subTest(case=case['id']):
                path = CATALOG.parent / case['source']
                result = certify_kernel(self.kernel(path), path.read_text())
                self.assertEqual(result['status'] == 'SUPPORTED', case['expected_support'], result)
                if case['expected_support']:
                    self.assertEqual(result['pattern'], case['pattern'])

    def test_readonly_stencil_is_doall_but_inplace_neighbor_is_refused(self):
        for identifier, accepted in [('readonly_stencil', True), ('inplace_neighbor', False), ('prefix_dependency', False)]:
            path = CATALOG.parent / self.case(identifier)['source']
            self.assertEqual(certify_kernel(self.kernel(path), path.read_text())['status'] == 'SUPPORTED', accepted)

    def test_existing_dot_remains_supported_and_accumulator_recurrence_is_not(self):
        dot = CATALOG.parent.parent / 'dot_product.c'
        self.assertEqual(certify_kernel(self.kernel(dot), dot.read_text())['pattern'], 'REDUCTION')
        path = CATALOG.parent / 'self_referential_reduction.c'
        self.assertEqual(certify_kernel(self.kernel(path), path.read_text())['status'], 'REFUSED')

    def test_transform_rechecks_real_source_and_refuses_a_forged_safe_plan(self):
        source = self.work / 'unsafe.c'
        source.write_text((CATALOG.parent / 'missing_restrict.c').read_text())
        static = self.work / 'static.json'
        static.write_text(json.dumps({'kernels': [{'name': 'kernel_case', 'loops': [],
                                                  'direct_transform_contract': {'status':'SUPPORTED','pattern':'DOALL'}}]}))
        strategy = self.work / 'strategy.json'
        strategy.write_text(json.dumps({'plans':[{'kernel':'kernel_case','strategy':{
            'strategy':'DOALL','direct_code_transformation':True}}]}))
        with self.assertRaisesRegex(RuntimeError, 'UNSUPPORTED_STANDALONE'):
            code_transformer.transform(source, static, strategy, self.work / 'candidate.c')
        self.assertFalse((self.work / 'candidate.c').exists())

    def test_stale_loop_metadata_is_not_used_for_source_insertion(self):
        source = CATALOG.parent / 'affine_vector.c'
        ast = self.kernel(source)
        contract = certify_kernel(ast, source.read_text())
        static = self.work / 'static.json'
        static.write_text(json.dumps({'kernels':[{'name':'kernel_case','loops':[{'id':1,'start_line':9999}],
                                                  'direct_transform_contract':contract}]}))
        strategy = self.work / 'strategy.json'
        strategy.write_text(json.dumps({'plans':[{'kernel':'kernel_case','strategy':{
            'strategy':'DOALL','direct_code_transformation':True}}]}))
        output = self.work / 'candidate.c'
        code_transformer.transform(source, static, strategy, output)
        self.assertIn('#pragma omp parallel for schedule(static)\n    for', output.read_text())

    def test_crlf_offsets_are_preserved_before_pragma_insertion(self):
        source = self.work / 'crlf.c'
        text = '\n' * 80 + (CATALOG.parent / 'affine_vector.c').read_text()
        source.write_bytes(text.replace('\n', '\r\n').encode())
        static = self.work / 'static.json'
        static.write_text(json.dumps({'kernels': [{'name': 'kernel_case', 'loops': []}]}))
        strategy = self.work / 'strategy.json'
        strategy.write_text(json.dumps({'plans': [{'kernel': 'kernel_case', 'strategy': {
            'strategy': 'DOALL', 'direct_code_transformation': True}}]}))
        output = self.work / 'candidate.c'
        code_transformer.transform(source, static, strategy, output)
        self.assertIn('#pragma omp parallel for schedule(static)\n    for', output.read_text())
        compiler = find_openmp_compiler()
        if compiler:
            subprocess.run([compiler, '-fopenmp', '-fsyntax-only', str(output)], check=True, capture_output=True)

    def test_included_kernel_body_is_not_a_standalone_transform_target(self):
        (self.work / 'kernel.h').write_text((CATALOG.parent / 'affine_vector.c').read_text())
        source = self.work / 'wrapper.c'
        source.write_text('#include "kernel.h"\n')
        result = certify_kernel(self.kernel(source), source.read_text())
        self.assertEqual(result['status'], 'REFUSED')
        definition = (CATALOG.parent / 'affine_vector.c').read_text()
        self.assertEqual(certify_kernel(self.kernel(source), definition)['status'], 'REFUSED')

    def test_cleanup_attribute_cannot_hide_a_side_effect_in_reduction(self):
        source = self.work / 'cleanup.c'
        source.write_text('void cleanup(double *p);\n'
                          'double kernel_case(int n, const double *A, const double *B) {\n'
                          ' double sum __attribute__((cleanup(cleanup))) = 0.0;\n'
                          ' for (int i = 0; i < n; i++) { sum += A[i]; }\n'
                          ' return sum;\n}\n')
        result = certify_kernel(self.kernel(source), source.read_text())
        self.assertEqual(result['status'], 'REFUSED')

    def test_openmp_conditional_cannot_change_the_certified_loop_body(self):
        for prefix, directive in [('', '#'), ('/* comment */ ', '#'), ('', '%:')]:
            source = self.work / 'conditional.c'
            source.write_text(f'{prefix}{directive}ifdef _OPENMP\n{directive}define TERM Y[i-1]\n'
                              f'{directive}else\n{directive}define TERM A[i]\n{directive}endif\n'
                              'void kernel_case(int n,const double *restrict A,const double *restrict B,double *restrict Y) {\n'
                              ' for(int i=1;i<n;i++) { Y[i]=TERM; }\n}\n')
            result = certify_kernel(self.kernel(source), source.read_text())
            self.assertEqual(result['status'], 'REFUSED')

    def test_non_newline_ascii_whitespace_does_not_shift_insertion(self):
        source = self.work / 'whitespace.c'
        source.write_bytes(('/* whitespace\v\f */\n' + (CATALOG.parent / 'affine_vector.c').read_text()).encode())
        static = self.work / 'static.json'
        static.write_text(json.dumps({'kernels': [{'name': 'kernel_case', 'loops': []}]}))
        strategy = self.work / 'strategy.json'
        strategy.write_text(json.dumps({'plans': [{'kernel': 'kernel_case', 'strategy': {
            'strategy': 'DOALL', 'direct_code_transformation': True}}]}))
        output = self.work / 'candidate.c'
        code_transformer.transform(source, static, strategy, output)
        self.assertIn('#pragma omp parallel for schedule(static)\n    for', output.read_text())
        compiler = find_openmp_compiler()
        if compiler:
            subprocess.run([compiler, '-fopenmp', '-fsyntax-only', str(output)], check=True, capture_output=True)

    def test_iterator_cannot_shadow_the_bound_parameter(self):
        source = self.work / 'shadow.c'
        source.write_text((CATALOG.parent / 'affine_vector.c').read_text().replace('int i = 0; i < n; i++', 'int n = 0; n < n; n++').replace('[i]', '[n]'))
        self.assertEqual(certify_kernel(self.kernel(source), source.read_text())['status'], 'REFUSED')

    def test_ignored_controls_and_spliced_pragma_tokens_are_refused(self):
        source = CATALOG.parent / 'affine_vector.c'
        base = source.read_text()
        for index, token in enumerate(('\0', '%:', '??=', '_Pragma', '_Pra\\\ngma', '__attribute__((unused))')):
            mutated = self.work / f'control_{index}.c'
            text = '/* ' + token + ' */\n' + base
            mutated.write_bytes(text.encode())
            self.assertEqual(certify_kernel(self.kernel(mutated), text)['status'], 'REFUSED')

    def test_per_element_oracle_rejects_wrong_array_even_with_cancelling_checksum(self):
        compiler = find_openmp_compiler()
        if not compiler:
            self.skipTest('C compiler required.')
        case = self.case('affine_vector')
        driver = self.work / 'driver.c'
        driver.write_text(driver_text(case, 1024))
        source = self.work / 'candidate.c'
        source.write_text('void kernel_case(int n,const double*A,const double*B,double*Y) {\n'
                          ' for(int i=0;i<n;i++) Y[i]=2*A[i]+B[i]; Y[0]+=1; Y[1]-=1; }\n')
        binary = self.work / 'wrong'
        subprocess.run([compiler,'-O3',str(driver),str(source),'-lm','-o',str(binary)],check=True,capture_output=True)
        self.assertEqual(subprocess.run([str(binary)],capture_output=True).returncode,3)
        source.write_text((CATALOG.parent / 'affine_vector.c').read_text())
        subprocess.run([compiler,'-O3',str(driver),str(source),'-lm','-o',str(binary)],check=True,capture_output=True)
        self.assertEqual(subprocess.run([str(binary)],capture_output=True).returncode,0)

    def test_clamp_inputs_exercise_the_upper_saturation_branch(self):
        compiler = find_openmp_compiler()
        if not compiler:
            self.skipTest('C compiler required.')
        source, driver, binary = self.work / 'clamp.c', self.work / 'driver.c', self.work / 'clamp'
        original = (CATALOG.parent / 'clamp.c').read_text()
        driver.write_text(driver_text(self.case('clamp'), 1024))
        source.write_text(original.replace('(A[i] > 1.0 ? 1.0 : A[i])', 'A[i]'))
        subprocess.run([compiler, '-O3', str(driver), str(source), '-lm', '-o', str(binary)], check=True, capture_output=True)
        self.assertEqual(subprocess.run([str(binary)], capture_output=True).returncode, 3)
        source.write_text(original)
        subprocess.run([compiler, '-O3', str(driver), str(source), '-lm', '-o', str(binary)], check=True, capture_output=True)
        self.assertEqual(subprocess.run([str(binary)], capture_output=True).returncode, 0)

    def test_bounds_steps_macros_and_other_side_effects_fail_closed(self):
        base = (CATALOG.parent / 'affine_vector.c').read_text()
        mutations = [
            base.replace('i++','i += 2'),
            base.replace('i < n','i <= n'),
            base.replace('Y[i] =','Y[i + 1] ='),
            base.replace('A[i] +','(A[i] = 1.0) +').replace('const double *restrict A','double *restrict A'),
            base.replace('Y[i] = 2.0 * A[i] + B[i];','Y[i] = (n--, A[i]);'),
            base.replace('for (int i = 0;','for (int i = 2;'),
        ]
        for index, text in enumerate(mutations):
            source = self.work / f'unsafe_{index}.c'
            source.write_text(text)
            self.assertEqual(certify_kernel(self.kernel(source),text)['status'],'REFUSED',text)


if __name__ == '__main__':
    unittest.main()
