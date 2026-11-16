"""The scientific AXPY harness must preserve inputs and detect archive changes."""
import json
import contextlib
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import evaluate_axpy_campaign as campaign
from scripts.performance_gate import parse_average_time
from scripts.test_toolchain import find_openmp_compiler


class AxpyCampaignTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.template = (campaign.ROOT / 'analysis/fixtures/axpy_benchmark_driver.c').read_text()

    def test_default_driver_is_byte_identical_to_existing_fixture(self):
        self.assertEqual(campaign.driver_text(self.template, 10000000, 40), self.template)

    def test_specialization_changes_only_the_two_declared_constants(self):
        driver = campaign.driver_text(self.template, 1024, 10000)
        self.assertEqual(driver.replace('#define N 1024', '#define N 10000000').replace(
            '#define INNER_REPEATS 10000', '#define INNER_REPEATS 40'), self.template)
        self.assertIn('for (int i = 0; i < N; ++i)', driver)
        self.assertIn('!isfinite(out[i])', driver)

    def test_invalid_input_and_repeat_counts_are_rejected(self):
        for n, repeats in [(0, 40), (-1, 40), (True, 40), (1, 0), (1, True), (2147483647, 1)]:
            with self.subTest(n=n, repeats=repeats), self.assertRaises(ValueError):
                campaign.driver_text(self.template, n, repeats)

    def test_changed_template_markers_are_rejected(self):
        for text in (self.template.replace('#define N 10000000', '#define N 1'),
                     self.template + '\n#define INNER_REPEATS 40\n'):
            with self.assertRaises(ValueError):
                campaign.driver_text(text, 1024, 10000)

    def test_archive_detects_modified_added_and_removed_files(self):
        path = self.directory / 'sample.json'
        path.write_text('original')
        campaign.seal(self.directory)
        campaign.verify_seal(self.directory)
        path.write_text('changed')
        with self.assertRaises(ValueError):
            campaign.verify_seal(self.directory)
        path.write_text('original')
        extra = self.directory / 'unrecorded'
        extra.write_text('extra')
        with self.assertRaises(ValueError):
            campaign.verify_seal(self.directory)
        extra.unlink()
        path.unlink()
        with self.assertRaises(ValueError):
            campaign.verify_seal(self.directory)

    def test_archive_manifest_cannot_escape_its_directory(self):
        (self.directory / 'archive_manifest.json').write_text(json.dumps([
            {'path': '../outside', 'sha256': 'not-a-hash'}]))
        with self.assertRaises(ValueError):
            campaign.verify_seal(self.directory)

    def test_existing_session_cannot_be_overwritten(self):
        with patch.object(campaign, 'verify_inputs', return_value={}):
            (self.directory / 'session01').mkdir()
            with self.assertRaises(FileExistsError):
                campaign.collect(self.directory, 1, 'not-called')

    def test_archived_verification_does_not_require_current_harness_bytes(self):
        output = self.directory / 'frozen'
        campaign.prepare(output)
        entries = json.loads((output / 'source_manifest.json').read_text())
        # The archive remains self-contained after a new harness revision.
        with patch.object(campaign, 'ROOT', self.directory / 'different-checkout'):
            campaign.verify_inputs(output)
            with self.assertRaises(FileNotFoundError):
                campaign.verify_inputs(output, require_live=True)
        self.assertGreater(len(entries), 20)

    def test_alternative_protocol_is_frozen_without_modifying_default(self):
        protocol = json.loads(campaign.PROTOCOL.read_text())
        protocol['threads'] = list(range(1, 11))
        alternative = self.directory / 'all_threads.json'
        alternative.write_text(json.dumps(protocol))
        output = self.directory / 'all_threads'
        campaign.prepare(output, alternative)
        self.assertEqual(campaign.verify_inputs(output)['threads'], list(range(1, 11)))
        self.assertEqual(json.loads(campaign.PROTOCOL.read_text())['threads'], [1, 2, 4, 6, 8, 10])

    def test_generated_timed_driver_rejects_errors_that_cancel_in_checksum(self):
        compiler = find_openmp_compiler() or shutil.which('cc')
        if compiler is None:
            self.skipTest('C compiler required')
        driver = self.directory / 'driver.c'
        driver.write_text(campaign.driver_text(self.template, 1024, 10000))
        source = self.directory / 'axpy.c'
        original = (campaign.ROOT / 'analysis/fixtures/axpy.c').read_text()
        binary = self.directory / 'axpy'
        for correct in (True, False):
            source.write_text(original if correct else original.replace(
                '    }\n}', '    }\n    output[0] += 1; output[1] -= 1;\n}'))
            subprocess.run([compiler, '-O3', str(driver), str(source), '-lm', '-o', str(binary)],
                           check=True, capture_output=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0 if correct else 3)
            if correct:
                self.assertGreater(parse_average_time(result.stdout), 0)

    def test_real_sessions_freeze_and_archive_tamper_detection(self):
        compiler = find_openmp_compiler()
        if compiler is None or shutil.which('clang') is None:
            self.skipTest('Clang AST and OpenMP compiler required')
        protocol = json.loads(campaign.PROTOCOL.read_text())
        protocol.update(inputs=[{'n': 1024, 'inner_repeats': 10000}], threads=[1, 2], repetitions=2, warmups=1)
        protocol_path = self.directory / 'test_protocol.json'
        protocol_path.write_text(json.dumps(protocol))
        output = self.directory / 'campaign'
        with patch.object(campaign, 'PROTOCOL', protocol_path), contextlib.redirect_stdout(io.StringIO()):
            campaign.prepare(output)
            campaign.collect(output, 1, compiler)
            campaign.freeze(output)
            with self.assertRaises(ValueError):
                campaign.freeze(output)
            campaign.collect(output, 2, compiler)
        first, _, samples, _ = campaign.verify_session(output / 'session01')
        self.assertEqual((first['configurations'], len(samples), first['warmup_samples']), (3, 6, 3))
        campaign.verify_session(output / 'session02')
        report = json.loads((output / 'session02/report.json').read_text())
        work = output / 'session02' / report['runs'][0]['work']
        performance = json.loads((work / 'performance.json').read_text())
        binary = Path(performance['binaries']['candidate']['path'])
        binary.write_bytes(binary.read_bytes() + b'changed')
        with self.assertRaises(ValueError):
            campaign.verify_session(output / 'session02')


if __name__ == '__main__':
    unittest.main()
