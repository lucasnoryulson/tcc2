"""Retrospective evaluation of training-session choices on a later campaign.

Unlike evaluate_selector_holdout.py, this mode does not attest that a decision
file was frozen before holdout collection. Both interfaces are kept separate.
"""
import argparse
from datetime import datetime
import json
import math
import statistics
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analyze_scaling import verify, selections
from scripts.benchmark_scaling import digest, write_csv, write_json
from scripts.compare_multiplatform import comparability, compile_flags
from scripts.compare_sessions import platform_identity


def evaluate_rows(training, holdout):
    def key(r):
        return r['kernel'], str(r['size']), r['variant'], int(r['threads'])
    train = {key(r): r['median_seconds'] for r in training}
    test = {key(r): r['median_seconds'] for r in holdout}
    if (len(train) != len(training) or len(test) != len(holdout)
        or not train or train.keys() != test.keys()
        or any(not math.isfinite(t) or t <= 0 for t in (*train.values(), *test.values()))):
        raise ValueError('Identical positive-time configuration sets required')
    rows = []
    for c in selections(training):
        kernel, size, variant = c['kernel'], str(c['size']), c['variant']
        seq = (kernel, size, 'sequential', 1)
        choices = sorted(k for k in train if k[:3] == (kernel, size, variant))
        recommendation = c['selection'].get('recommended')
        selected = (kernel, size, variant, recommendation['threads']) if recommendation else seq
        train_fastest = min([seq, *choices], key=lambda k: (train[k], k != seq, k[3]))
        test_fastest = min([seq, *choices], key=lambda k: (test[k], k != seq, k[3]))
        max_threads = max(choices, key=lambda k: k[3])
        one = (kernel, size, variant, 1)
        def label(k):
            return 'sequential' if k == seq else f'{k[3]}T'
        rows.append(dict(kernel=kernel, size=size, variant=variant,
            selected=label(selected), training_fastest=label(train_fastest),
            holdout_oracle=label(test_fastest), max_threads=label(max_threads),
            sequential_seconds=test[seq], selected_seconds=test[selected],
            training_fastest_seconds=test[train_fastest], max_threads_seconds=test[max_threads],
            holdout_oracle_seconds=test[test_fastest],
            total_speedup=test[seq]/test[selected],
            parallel_speedup=None if selected == seq else test[one]/test[selected],
            parallel_efficiency=None if selected == seq else test[one]/test[selected]/selected[3],
            regret_percent=100*(test[selected]/test[test_fastest]-1),
            slower_than_sequential=test[selected]>test[seq],
            within_two_percent_of_oracle=test[selected]<=1.02*test[test_fastest]))
    return rows


def evaluate(training, holdout, output):
    training, holdout = training.resolve(), holdout.resolve()
    if training == holdout:
        raise ValueError('Holdout must be a separate run')
    a, train = verify(training)
    b, test = verify(holdout)
    if datetime.fromisoformat(a['finished_utc']) > datetime.fromisoformat(b['started_utc']):
        raise ValueError('Holdout must start after training finishes')
    differences = [d for d in comparability(a, b) if d != 'seed']
    if a['threads'] != b['threads'] or differences or compile_flags(training) != compile_flags(holdout):
        raise ValueError(f'Incompatible campaigns: {differences}')
    env = lambda p: platform_identity(json.loads((p/'environment.json').read_text()))
    if env(training) != env(holdout):
        raise ValueError('Compiler and platform identities differ')
    rows = evaluate_rows(train, test)
    def metrics(field):
        regret = [100*(r[field]/r['holdout_oracle_seconds']-1) for r in rows]
        return dict(median_regret_percent=statistics.median(regret), max_regret_percent=max(regret),
                    slower_than_sequential=sum(r[field]>r['sequential_seconds'] for r in rows),
                    within_two_percent_of_oracle=sum(r[field]<=1.02*r['holdout_oracle_seconds'] for r in rows))
    output.mkdir(parents=True, exist_ok=False)
    write_csv(output/'holdout.csv', rows)
    result = dict(status='COMPLETE',
        training_report_sha256=digest((training/'report.json').read_bytes()),
        holdout_report_sha256=digest((holdout/'report.json').read_bytes()),
        training_samples_sha256=digest((training/'samples.jsonl').read_bytes()),
        holdout_samples_sha256=digest((holdout/'samples.jsonl').read_bytes()),
        cases=len(rows), slower_than_sequential=sum(r['slower_than_sequential'] for r in rows),
        within_two_percent_of_oracle=sum(r['within_two_percent_of_oracle'] for r in rows),
        policies={name: metrics(field) for name, field in [('selector', 'selected_seconds'),
            ('training_fastest', 'training_fastest_seconds'), ('max_threads', 'max_threads_seconds')]},
        limitation='Retrospective choices from separate sequential sessions; no attestation of a decision file frozen before holdout collection; oracle is not a global optimum', rows=rows)
    write_json(output/'report.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('training', type=Path)
    parser.add_argument('holdout', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    evaluate(args.training, args.holdout, args.output)
