"""Compute amortization from an actual pipeline summary and verified selection."""
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.artifact_provenance import file_record, load_performance_report, load_selection_evidence


def break_even(cost, sequential, optimized):
    if not all(math.isfinite(x) and x >= 0 for x in (cost, sequential, optimized)):
        raise ValueError('Invalid times')
    return math.ceil(cost/(sequential-optimized)) if sequential > optimized else None


def analyze(run):
    summary = json.loads((run/'summary.json').read_text())
    if summary['status'] not in {'PREPARED', 'PROMOTED', 'NOT_PROMOTED'}:
        raise ValueError('Cost requires a complete preparation or decision')
    report, _, _ = load_performance_report(run/'performance.json', run/'performance.csv')
    inputs = report['provenance']['inputs']
    bundle = load_selection_evidence(run/'selection.json', run/'correctness.json',
        Path(inputs['sequential']['path']), Path(inputs['candidate']['path']))
    if bundle['references']['performance'] != file_record(run/'performance.json'):
        raise ValueError('Selection belongs to another performance report')
    calculated = {k: v for k, v in bundle['selection'].items() if k != 'evidence'}
    selected = calculated.get('recommended')
    sequential = calculated['sequential']['median_seconds']
    steps = {x['name']: x['wall_seconds'] for x in summary['steps']}
    if (len(steps) != len(summary['steps'])
        or not all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in steps.values())):
        raise ValueError('Invalid step times')
    elapsed = summary['elapsed_seconds']
    if (type(elapsed) not in (int, float) or not math.isfinite(elapsed)
        or elapsed < 0 or elapsed + 1e-9 < sum(steps.values())):
        raise ValueError('Invalid elapsed time')
    deterministic = sum(v for k, v in steps.items() if k not in {'coordinator', 'promotion'})
    inference = steps.get('coordinator')
    optimized = selected['median_seconds'] if selected else sequential
    return dict(status=summary['status'], steps_seconds=steps, elapsed_seconds=summary['elapsed_seconds'],
        sequential_seconds=sequential, selected_seconds=optimized,
        deterministic_prefix_seconds=deterministic, coordinator_step_seconds=inference,
        prefix_break_even=break_even(deterministic, sequential, optimized),
        inference_only_break_even=None if inference is None else break_even(inference, sequential, optimized),
        observed_pipeline_break_even=break_even(summary['elapsed_seconds'], sequential, optimized) if summary['status']=='PROMOTED' else None,
        limitation='Prefix estimate assumes reuse of the measured candidate; only PROMOTED has observed full admission cost')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(args.run), indent=2))
