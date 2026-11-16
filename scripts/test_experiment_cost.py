"""Telemetry must preserve real subprocess results and failed/zero-saving cases."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.measure_pipeline_cost import break_even, prepared_prefix
from scripts.process_timing import run_timed


class ExperimentCostTests(unittest.TestCase):
    def test_reused_prefix_must_not_include_prior_inference(self):
        with patch('scripts.measure_pipeline_cost.verify_prefix', return_value={'status': 'PREPARED'}):
            self.assertEqual(prepared_prefix(Path('.')), Path('.').resolve())
        for status in ('PROMOTED', 'NOT_PROMOTED', 'FAILED'):
            with self.subTest(status=status), patch('scripts.measure_pipeline_cost.verify_prefix', return_value={'status': status}):
                with self.assertRaisesRegex(ValueError, 'Only PREPARED'):
                    prepared_prefix(Path('.'))

    def test_break_even_requires_positive_saving_and_rounds_up(self):
        self.assertEqual(break_even(10, 3, 1.5), 7)
        self.assertIsNone(break_even(10, 3, 3))
        self.assertIsNone(break_even(10, 3, 4))

    def test_real_exit_code_and_output_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'timing.jsonl'
            with patch.dict(os.environ, TCC2_PROCESS_TIMING_LOG=str(log), TCC2_TIMING_STAGE='correctness'):
                result = run_timed([sys.executable, '-c', 'print("observed"); raise SystemExit(7)'],
                                   origin='test', capture_output=True, text=True)
            self.assertEqual(result.returncode, 7)
            self.assertEqual(result.stdout, 'observed\n')
            record = json.loads(log.read_text())
            self.assertEqual(record['returncode'], 7)
            self.assertEqual(record['stage'], 'correctness')
            self.assertGreater(record['wall_seconds'], 0)

    def test_timeout_is_logged_and_reraised(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'timing.jsonl'
            with patch.dict(os.environ, TCC2_PROCESS_TIMING_LOG=str(log)):
                with self.assertRaises(subprocess.TimeoutExpired):
                    run_timed([sys.executable, '-c', 'import time; time.sleep(2)'],
                              origin='test', timeout=.02, capture_output=True)
            record = json.loads(log.read_text())
            self.assertIsNone(record['returncode'])
            self.assertIn('TimeoutExpired', record['error'])
