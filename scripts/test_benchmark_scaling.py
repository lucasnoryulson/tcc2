"""Numerical, metric and real-compiler checks for the scaling campaign."""
import argparse
import json
from pathlib import Path
import tempfile
import unittest

from scripts.benchmark_scaling import execute, numeric_result, summarize
from scripts.analyze_scaling import enrich, selections, verify
from scripts.compare_multiplatform import comparability
from scripts.test_toolchain import find_openmp_compiler


class ScalingTests(unittest.TestCase):
    def test_real_generated_dot_c_and_three_archived_warmups(self):
        compiler = find_openmp_compiler()
        if not compiler:
            self.skipTest('No OpenMP compiler')
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(output=Path(directory) / 'automatic', cc=compiler, cxx=compiler,
                                      kernels=['dot-auto'], threads=[1, 2], dot_sizes=[1024], auto_dot_sizes=[1024],
                                      datasets=['MINI'], repetitions=2, warmups=3, seed=2026, timeout=30)
            execute(args)
            report, rows = verify(args.output)
            self.assertEqual(len(report['warmup_runs']), 9)
            self.assertEqual(report['measurements'], 6)
            self.assertIn('#pragma omp parallel for reduction(+:sum)',
                          (args.output / 'sources/generated/dot_auto.c').read_text())
            self.assertEqual(len(rows), 3)

    def test_cross_platform_comparison_rejects_changed_protocol_input_and_code(self):
        import copy
        report = dict(protocol='multiplatform-v2', repetitions=15, warmups=3, seed=2026,
                      inputs=[dict(kernel='dot', size=10, dimensions={'N': 10})],
                      sources=[dict(original='kernel.c', snapshot_sha256='measured')])
        self.assertEqual(comparability(report, copy.deepcopy(report)), [])
        for name in ('repetitions', 'warmups'):
            other = copy.deepcopy(report)
            other[name] = 7
            self.assertIn(name, comparability(report, other))
        other = copy.deepcopy(report)
        other['sources'][0]['snapshot_sha256'] = 'changed'
        self.assertIn('compiled source/header/driver bytes', comparability(report, other))
        other = copy.deepcopy(report)
        other['inputs'][0]['dimensions']['N'] = 20
        self.assertIn('inputs/dimensions', comparability(report, other))

    def test_dispersion_and_paired_bootstrap_preserve_known_ratios(self):
        raw = [dict(kernel='dot', size=10, variant=v, threads=p, repeat=i, seconds=i * t)
               for i in range(1, 16) for v, p, t in [('sequential', 1, 12), ('manual', 1, 8), ('manual', 4, 2)]]
        result = next(r for r in enrich(summarize(raw), raw, resamples=200) if r['threads'] == 4)
        self.assertEqual(result['mad_seconds'], 8)
        self.assertEqual(result['iqr_seconds'], 14)
        self.assertEqual(result['speedup_total_ci95_low'], 6)
        self.assertEqual(result['speedup_total_ci95_high'], 6)
        self.assertEqual(result['speedup_parallel_ci95_low'], 4)
        self.assertEqual(result['efficiency_parallel_ci95_low'], 1)
        small = [r for r in raw if r['repeat'] <= 7]
        self.assertIsNone(enrich(summarize(small), small)[0]['median_seconds_ci95_low'])

    def test_selector_distinguishes_fastest_and_near_tie_recommendation(self):
        rows = [dict(kernel='dot', size=10, variant=v, threads=p, seconds=t)
                for v, p, t in [('sequential', 1, 12), ('manual', 1, 8), ('manual', 2, 2.01), ('manual', 4, 2)]]
        selection = selections(summarize(rows))[0]['selection']
        self.assertEqual(selection['raw_fastest']['threads'], 4)
        self.assertEqual(selection['recommended']['threads'], 2)

    def test_reject_invalid_result_and_time(self):
        for output in ('result=nan\nexpected=1\nrun_ms=1',
                       'result=2\nexpected=1\nrun_ms=1',
                       'result=1\nexpected=1\nrun_ms=0',
                       'result=inf\nexpected=inf\nrun_ms=1'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                numeric_result(output)
        self.assertEqual(numeric_result('result=1\nexpected=1\nrun_ms=2'), .002)

    def test_separate_baselines_and_preserve_samples(self):
        rows = [dict(kernel='dot', size=10, variant=v, threads=p, seconds=t)
                for v, p, t in [('sequential', 1, 12), ('manual', 1, 8), ('manual', 4, 2)]]
        result = next(r for r in summarize(rows) if r['threads'] == 4)
        self.assertEqual(result['speedup_total'], 6)
        self.assertEqual(result['speedup_transformation'], 1.5)
        self.assertEqual(result['speedup_parallel'], 4)
        self.assertEqual(result['efficiency_parallel'], 1)

    def test_real_dot_and_collision(self):
        compiler = find_openmp_compiler()
        if not compiler:
            self.skipTest('No OpenMP compiler')
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(output=Path(directory) / 'campaign', cc=compiler,
                                      cxx=compiler, kernels=['dot'], threads=[1, 2], dot_sizes=[1024],
                                      datasets=['MINI'], repetitions=2, seed=2026, timeout=30)
            # GCC needs an explicit C++ standard library when invoked by its C driver.
            args.cxx = 'g++' if 'gcc' in Path(compiler).name else compiler
            execute(args)
            report = json.loads((args.output / 'report.json').read_text())
            self.assertEqual(report['status'], 'COMPLETE')
            self.assertEqual(report['measurements'], 6)
            self.assertEqual(len(report['correctness']), 3)
            self.assertTrue(report['binaries'])
            self.assertEqual(verify(args.output)[0]['measurements'], 6)
            original_warmups = report['warmup_runs']
            report['warmup_runs'] = original_warmups[:-1]
            (args.output / 'report.json').write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'Missing warm-ups'):
                verify(args.output)
            report['warmup_runs'] = original_warmups
            report_path = args.output / 'report.json'
            report_path.write_text(json.dumps(report))
            output = next((args.output / 'logs').glob('*.stdout'))
            output.write_bytes(output.read_bytes() + b'changed')
            with self.assertRaisesRegex(ValueError, 'Changed command output'):
                verify(args.output)
            with self.assertRaises(FileExistsError):
                execute(args)


if __name__ == '__main__':
    unittest.main()
