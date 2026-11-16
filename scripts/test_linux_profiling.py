"""Parser/contract tests: synthetic records are not Linux counter evidence."""
import argparse
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import profile_linux_followup as profiling


class LinuxProfilingTests(unittest.TestCase):
    def test_paired_cpu_counters_and_cache_ratio(self):
        values = profiling.parse_perf('100;;cycles;100;100.00\n250;;instructions;100;100.00\n'
                                      '40;;cache-references;100;100.00\n4;;cache-misses;100;100.00\n')
        self.assertEqual(profiling.ratios(values), dict(ipc=2.5, cache_miss_fraction=.1))

    def test_unavailable_is_not_zero(self):
        values = profiling.parse_perf('<not supported>;;cycles;0;0\n<not counted>;;instructions;0;0\n')
        self.assertEqual([r['status'] for r in values], ['NOT_SUPPORTED', 'NOT_COUNTED'])
        self.assertTrue(all(r['value'] is None for r in values))
        self.assertIsNone(profiling.ratios(values)['ipc'])

    def test_nonfinite_negative_and_zero_denominator(self):
        values = profiling.parse_perf('0;;cycles\n1;;instructions\nnan;;cache-misses\n-1;;cache-references\n')
        self.assertIsNone(profiling.ratios(values)['ipc'])
        self.assertIsNone(profiling.ratios(values)['cache_miss_fraction'])

    def test_pmu_specific_events_are_not_silently_combined(self):
        values = profiling.parse_perf('10;;cpu_core/cycles/\n20;;cpu_atom/instructions/\n')
        self.assertIsNone(profiling.ratios(values)['ipc'])

    def test_non_linux_rejected_before_creating_archive(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(profiling.platform, 'system', return_value='Darwin'):
            args = argparse.Namespace(output=Path(directory) / 'new')
            with self.assertRaisesRegex(ValueError, 'Linux perf'):
                profiling.collect(args)
            self.assertFalse(args.output.exists())

    def test_changed_campaign_binary_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'report.json').write_text(json.dumps(dict(status='COMPLETE', binaries={
                'bin/dot-auto-10000000-sequential': 'not-its-hash'})))
            (root / 'bin').mkdir()
            (root / 'bin/dot-auto-10000000-sequential').write_text('not executable')
            with self.assertRaisesRegex(ValueError, 'Changed archived binary'):
                profiling.resolve_targets(root)


if __name__ == '__main__':
    unittest.main()
