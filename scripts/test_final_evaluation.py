import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.analyze_pipeline_cost import break_even
from scripts import evaluate_selector_sessions as sessions
from scripts.evaluate_selector_sessions import evaluate_rows


def rows(times):
    return [dict(kernel='axpy', size='LARGE', variant=mode, threads=threads,
                 median_seconds=t, mean_seconds=t)
            for (mode, threads), t in zip([('sequential', 1), ('auto', 1), ('auto', 2), ('auto', 4)], times)]


class FinalEvaluation(unittest.TestCase):
    def test_frozen_choice_is_not_reselected_on_holdout(self):
        result = evaluate_rows(rows([10, 10, 5.05, 5]), rows([10, 10, 8, 4]))[0]
        self.assertEqual(result['selected'], '2T')
        self.assertEqual(result['holdout_oracle'], '4T')
        self.assertEqual(result['regret_percent'], 100)
        self.assertFalse(result['within_two_percent_of_oracle'])

    def test_no_gain_falls_back_to_sequential(self):
        result = evaluate_rows(rows([1, 2, 3, 4]), rows([2, 1, 1, 1]))[0]
        self.assertEqual(result['selected'], 'sequential')
        self.assertIsNone(result['parallel_speedup'])

    def test_incompatible_repetitions_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_rows(rows([1, 2, 3, 4]), rows([1, 2, 3, 4])[:-1])

    def test_amortization(self):
        self.assertEqual(break_even(10, 2, 1), 10)
        self.assertIsNone(break_even(10, 1, 1))
        with self.assertRaises(ValueError):
            break_even(10, float('nan'), 1)

    def test_duplicate_or_invalid_measurements_are_rejected(self):
        for invalid in (0, -1, float('nan'), float('inf')):
            with self.subTest(time=invalid), self.assertRaises(ValueError):
                evaluate_rows(rows([1, 2, 3, 4]), rows([1, 2, invalid, 4]))
        data = rows([1, 2, 3, 4])
        with self.assertRaises(ValueError):
            evaluate_rows(data + [data[0]], data + [data[0]])

    def test_chronology_uses_instants_not_lexical_timezone_order(self):
        # 09:00 -03:00 is later than 11:00 UTC, even though its text sorts first.
        with patch.object(sessions, 'verify', side_effect=[
                ({'finished_utc': '2026-11-16T09:00:00-03:00'}, []),
                ({'started_utc': '2026-11-16T11:00:00+00:00'}, [])]), \
                self.assertRaisesRegex(ValueError, 'after training finishes'):
            sessions.evaluate(Path('training'), Path('holdout'), Path('output'))

    def test_same_archive_cannot_be_its_own_holdout(self):
        with patch.object(sessions, 'verify') as verify, self.assertRaises(ValueError):
            sessions.evaluate(Path('training'), Path('training'), Path('output'))
        verify.assert_not_called()


if __name__ == '__main__':
    unittest.main()
