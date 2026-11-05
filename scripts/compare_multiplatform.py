"""Compare two new archives only when code, inputs and sampling protocol match."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analyze_scaling import verify
from scripts.benchmark_scaling import write_csv, write_json


def comparability(left, right):
    mismatches = [name for name in ('protocol', 'repetitions', 'warmups', 'seed') if left[name] != right[name]]
    if left['protocol'] != 'multiplatform-v2' or right['protocol'] != 'multiplatform-v2':
        mismatches.append('new protocol required')
    if not left.get('inputs') or not right.get('inputs'):
        mismatches.append('missing measured input identity')
    if sorted(left.get('inputs', []), key=lambda x: (x['kernel'], str(x['size']))) != sorted(right.get('inputs', []), key=lambda x: (x['kernel'], str(x['size']))):
        mismatches.append('inputs/dimensions')
    def code(report):
        return {r['original']: r['snapshot_sha256'] for r in report['sources']
                if Path(r['original']).suffix in ('.c', '.h', '.cpp') and not r['original'].endswith('openmp_probe.c')}
    if code(left) != code(right):
        mismatches.append('compiled source/header/driver bytes')
    return mismatches


def compile_flags(directory):
    flags = {}
    for line in (directory / 'commands.jsonl').read_text().splitlines():
        command = json.loads(line)['command']
        if '-o' in command:
            name = Path(command[command.index('-o') + 1]).name
            flags[name] = [arg for arg in command[1:] if arg.startswith('-') and not arg.startswith('-I') and arg != '-o']
    return flags


def compare(left_path, right_path, output):
    left, lrows = verify(left_path)
    right, rrows = verify(right_path)
    output.mkdir(parents=True, exist_ok=False)
    issues = comparability(left, right)
    if compile_flags(left_path) != compile_flags(right_path):
        issues.append('compile flags')
    threads = sorted(set(left['threads']) & set(right['threads']))
    write_json(output / 'comparability.json', dict(status='INCOMPARABLE' if issues else 'MATCHED_PROTOCOL',
               mismatches=issues, common_threads=threads, left=str(left_path), right=str(right_path),
               scope='Whole platforms including compiler/runtime; no isolated architectural causality'))
    if issues:
        raise ValueError('Cannot compare archives: ' + ', '.join(issues))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    curves = sorted({(r['kernel'], str(r['size']), r['variant']) for r in lrows if r['variant'] != 'sequential'})
    fig, axes = plt.subplots((len(curves)+1)//2, 2, figsize=(11, ((len(curves)+1)//2)*3.2), squeeze=False)
    table = []
    for ax, (kernel, size, variant) in zip(axes.flat, curves):
        for label, rows in [(left_path.name, lrows), (right_path.name, rrows)]:
            curve = sorted((r for r in rows if (r['kernel'], str(r['size']), r['variant']) == (kernel, size, variant)
                            and r['threads'] in threads), key=lambda r: r['threads'])
            ax.plot([r['threads'] for r in curve], [r['speedup_parallel'] for r in curve], 'o-', label=label)
            table.extend(dict(campaign=label, **r) for r in curve)
        ax.set(title=f'{kernel} / {size} / {variant}', xlabel='Threads comuns', ylabel='T₁/Tₚ', xticks=threads)
        ax.grid(alpha=.25)
        ax.legend(fontsize=7)
    for ax in list(axes.flat)[len(curves):]:
        ax.set_visible(False)
    fig.tight_layout()
    for extension in ('png', 'svg', 'pdf'):
        fig.savefig(output / f'platform_comparison.{extension}', dpi=160)
    plt.close(fig)
    write_csv(output / 'comparison.csv', table)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('left', type=Path)
    parser.add_argument('right', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    compare(args.left.resolve(), args.right.resolve(), args.output.resolve())
