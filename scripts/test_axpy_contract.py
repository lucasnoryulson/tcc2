"""Regression cases for the AXPY fixture without weakening the AST contract."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from analysis import static_analyzer
from analysis.conservative_transform import certify_kernel
from scripts.test_toolchain import find_openmp_compiler

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'analysis/fixtures/axpy.c'
DRIVER = ROOT / 'analysis/fixtures/axpy_driver.c'


class AxpyContract(unittest.TestCase):
    def test_certifies_axpy_and_refuses_unsafe_variations(self):
        if not shutil.which('clang'):
            self.skipTest('Clang AST required')
        text = FIXTURE.read_text()
        variants = [
            (text, 'SUPPORTED'),
            (text.replace('output[i]', 'output[i % 2]'), 'REFUSED'),
            (text.replace('output[i]', 'output[0]'), 'REFUSED'),
            (text.replace('*restrict', '*'), 'REFUSED'),
            (text.replace('alpha * X[i] + Y[i]', 'alpha * X[i] + output[i]'), 'REFUSED'),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for index, (source, expected) in enumerate(variants):
                with self.subTest(index=index):
                    path = Path(directory) / f'case{index}.c'
                    path.write_text(source)
                    kernel = static_analyzer.find_kernel_functions(static_analyzer.run_clang(path, []))[0]
                    self.assertEqual(certify_kernel(kernel, source)['status'], expected)

    def test_full_output_oracle_accepts_correct_and_rejects_cancelling_errors(self):
        compiler = find_openmp_compiler() or shutil.which('cc')
        if not compiler:
            self.skipTest('C compiler required')
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            binary = directory / 'axpy'
            subprocess.run([compiler, '-O3', str(DRIVER), str(FIXTURE), '-lm', '-o', str(binary)], check=True)
            self.assertEqual(subprocess.run([str(binary)], capture_output=True).returncode, 0)
            wrong = directory / 'wrong.c'
            wrong.write_text(FIXTURE.read_text().replace('    }\n}', '    }\n    output[0] += 1; output[1] -= 1;\n}'))
            subprocess.run([compiler, '-O3', str(DRIVER), str(wrong), '-lm', '-o', str(binary)], check=True)
            self.assertEqual(subprocess.run([str(binary)], capture_output=True).returncode, 3)


if __name__ == '__main__':
    unittest.main()
