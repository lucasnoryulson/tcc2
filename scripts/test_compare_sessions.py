import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.compare_sessions import compare, platform_identity, summarize_sessions


class SessionSummaryTests(unittest.TestCase):
    def test_separate_medians_and_intersection(self):
        def row(size, seconds):
            return dict(kernel='example', size=size, variant='manual', threads=2, median_seconds=seconds)
        result = summarize_sessions([[row(1, 2), row(2, 999)], [row(1, 4)], [row(1, 6)]])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['mean_session_median'], 4)
        self.assertEqual(result[0]['sample_sd_session_medians'], 2)
        self.assertEqual(result[0]['maximum_over_minimum'], 3)
        self.assertEqual(result[0]['session_2_median'], 4)

    def test_insufficient_or_disjoint(self):
        with self.assertRaises(ValueError):
            summarize_sessions([[]])
        with self.assertRaises(ValueError):
            summarize_sessions([[], []])

    def test_frequency_is_observation_not_machine_identity(self):
        first = {'machine': 'x86_64', 'lscpu': 'Model name: Xeon\nCPU(s): 4\nCPU(s) scaling MHz: 93%'}
        second = first | {'lscpu': 'Model name: Xeon\nCPU(s): 4\nCPU(s) scaling MHz: 44%'}
        self.assertEqual(platform_identity(first), platform_identity(second))
        self.assertNotEqual(platform_identity(first), platform_identity(second | {'lscpu': 'Model name: Other\nCPU(s): 4'}))
        self.assertNotEqual(platform_identity(first), platform_identity(first | {'sysctl hw.model': 'hw.model: Mac17,1'}))

    def test_same_labels_cannot_hide_missing_source_or_changed_dimensions(self):
        report = dict(protocol='multiplatform-v2', repetitions=15, warmups=3, seed=2026, threads=[1, 2, 4],
                      sources=[dict(original='kernel.c', snapshot_sha256='unchanged')],
                      inputs=[dict(kernel='dot', size=1024, dimensions={'N': 1024})])
        rows = [dict(kernel='dot', size=1024, variant='manual', threads=2, median_seconds=1)]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = [root / name for name in ('first', 'second')]
            for path in paths:
                path.mkdir()
                (path / 'environment.json').write_text('{}')
                (path / 'commands.jsonl').write_text(json.dumps({'command': ['gcc', '-O3', 'kernel.c', '-o', 'dot-1024-manual']}) + '\n')
            for mutation, message in [('source', 'source/header'), ('dimensions', 'dimensions'), ('input', 'input identity')]:
                other = copy.deepcopy(report)
                if mutation == 'source':
                    other['sources'] = []
                elif mutation == 'dimensions':
                    other['inputs'][0]['dimensions']['N'] = 2048
                else:
                    other['inputs'] = []
                with patch('scripts.compare_sessions.verify', side_effect=[(report, rows), (other, rows)]):
                    with self.assertRaisesRegex(ValueError, message):
                        compare(paths, root / ('out-' + mutation), no_plots=True)


if __name__ == '__main__':
    unittest.main()
