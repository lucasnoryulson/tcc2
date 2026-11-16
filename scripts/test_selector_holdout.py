"""A later session can overturn a first-session near tie or its apparent gain."""
import unittest

import analysis.performance_selector as selector
from scripts.analyze_scaling import selections
from scripts.benchmark_scaling import summarize
from scripts.evaluate_selector_holdout import evaluate_rows, select_at_threshold


def summary(values):
    return summarize([dict(kernel='example', size=100, variant=v, threads=p, seconds=t)
                      for v, p, t in values])


class SelectorHoldoutTests(unittest.TestCase):
    def test_new_observations_can_make_resource_aware_choice_inadequate(self):
        first = summary([('sequential', 1, 12), ('manual', 1, 8), ('manual', 2, 2.01), ('manual', 4, 2)])
        second = summary([('sequential', 1, 12), ('manual', 1, 8), ('manual', 2, 5), ('manual', 4, 2)])
        rows, sensitivity, stable = evaluate_rows(first, second, selections(first))
        chosen = next(r for r in rows if r['policy'] == 'selector')
        self.assertEqual(chosen['threads'], 2)
        self.assertEqual(chosen['regret_percent'], 150)
        self.assertTrue(chosen['inadequate'])
        self.assertEqual(chosen['speedup_parallel'], 8 / 5)
        self.assertFalse(stable[0]['unchanged'])
        strict = next(r for r in sensitivity if r['near_tie_threshold'] == 0)
        self.assertEqual(strict['threads'], 4)
        self.assertEqual(strict['regret_percent'], 0)

    def test_evaluation_oracle_includes_sequential_and_two_percent_is_inclusive(self):
        first = summary([('sequential', 1, 2), ('manual', 1, 3), ('manual', 2, 1)])
        second = summary([('sequential', 1, 1), ('manual', 1, 3), ('manual', 2, 1.02)])
        rows, _, _ = evaluate_rows(first, second, selections(first))
        chosen = next(r for r in rows if r['policy'] == 'selector')
        self.assertEqual(chosen['oracle_variant'], 'sequential')
        self.assertFalse(chosen['inadequate'])
        self.assertTrue(chosen['slower_than_sequential'])

    def test_no_benefit_falls_back_to_sequential_and_constant_is_restored(self):
        first = summary([('sequential', 1, 1), ('manual', 1, 2), ('manual', 2, 3)])
        rows, _, stable = evaluate_rows(first, first, selections(first))
        chosen = next(r for r in rows if r['policy'] == 'selector')
        self.assertEqual(chosen['evaluated_variant'], 'sequential')
        self.assertIsNone(chosen['speedup_parallel'])
        self.assertTrue(stable[0]['unchanged'])
        previous = selector.NEAR_TIE_THRESHOLD
        with self.assertRaises(ValueError):
            select_at_threshold([], .05)
        self.assertEqual(selector.NEAR_TIE_THRESHOLD, previous)
