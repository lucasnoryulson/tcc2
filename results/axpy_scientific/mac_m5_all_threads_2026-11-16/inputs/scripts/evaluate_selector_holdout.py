"""Freeze Selector decisions before a new session and evaluate them out of sample."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import analysis.performance_selector as selector
from scripts.analyze_scaling import selections, verify
from scripts.benchmark_scaling import digest, write_csv, write_json
from scripts.compare_multiplatform import comparability, compile_flags
from scripts.compare_sessions import platform_identity
from scripts.consolidate_experiments import normalize


def select_at_threshold(rows, threshold):
    """Sensitivity uses the real Selector; restore its production constant."""
    previous = selector.NEAR_TIE_THRESHOLD
    try:
        selector.NEAR_TIE_THRESHOLD = threshold
        return selector.select_configuration(normalize(rows))
    finally:
        selector.NEAR_TIE_THRESHOLD = previous


def chosen_configuration(selection):
    recommended = selection.get('recommended')
    return (recommended['threads'], False) if recommended else (1, True)


def freeze(campaign, path):
    campaign = campaign.resolve()
    report, summary = verify(campaign)
    choices = selections(summary)
    record = dict(schema='tcc2-selector-holdout-v1', frozen_at_utc=datetime.now(timezone.utc).isoformat(),
                  selection_campaign=str(campaign), report_sha256=digest((campaign / 'report.json').read_bytes()),
                  samples_sha256=digest((campaign / 'samples.jsonl').read_bytes()),
                  selector_sha256=digest(Path(selector.__file__).read_bytes()),
                  near_tie_threshold=selector.NEAR_TIE_THRESHOLD,
                  inadequacy_threshold=.02, sensitivity_thresholds=[0, .01, .02, .05],
                  oracle='Smallest holdout median including sequential; descriptive post-hoc comparator',
                  choices=choices, selection_started_utc=report['started_utc'])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    return record


def evaluate_rows(selection_summary, evaluation_summary, frozen_choices, threshold=.02):
    output, sensitivity, stability = [], [], []
    holdout_choices = {(c['kernel'], str(c['size']), c['variant']): c['selection']
                       for c in selections(evaluation_summary)}
    for choice in frozen_choices:
        kernel, size, variant = choice['kernel'], str(choice['size']), choice['variant']
        key = kernel, size, variant
        def belongs(row):
            return (row['kernel'], str(row['size'])) == key[:2] and row['variant'] in ('sequential', variant)
        first = [r for r in selection_summary if belongs(r)]
        second = [r for r in evaluation_summary if belongs(r)]
        if {(r['variant'], r['threads']) for r in first} != {(r['variant'], r['threads']) for r in second}:
            raise ValueError('Holdout must contain the same configuration grid')
        seq = next(r for r in second if r['variant'] == 'sequential')
        one = next(r for r in second if r['variant'] == variant and r['threads'] == 1)
        oracle = min(second, key=lambda r: r['median_seconds'])
        parallel = [r for r in first if r['variant'] == variant]
        fastest = min(parallel, key=lambda r: r['median_seconds'])
        p, use_seq = chosen_configuration(choice['selection'])
        policies = [('sequential', 'sequential', 1),
                    ('max_threads', variant, max(r['threads'] for r in parallel)),
                    ('selector', 'sequential' if use_seq else variant, p),
                    ('fastest_selection', variant, fastest['threads'])]
        for policy, chosen_variant, threads in policies:
            observed = next(r for r in second if (r['variant'], r['threads']) == (chosen_variant, threads))
            seconds = observed['median_seconds']
            regret = seconds / oracle['median_seconds'] - 1
            output.append(dict(kernel=kernel, size=size, variant=variant, policy=policy,
                               evaluated_variant=chosen_variant, threads=threads, median_seconds=seconds,
                               speedup_total=seq['median_seconds'] / seconds,
                               speedup_parallel=one['median_seconds'] / seconds if chosen_variant != 'sequential' else None,
                               efficiency_parallel=one['median_seconds'] / seconds / threads if chosen_variant != 'sequential' else None,
                               regret_percent=100 * regret, inadequate=regret > threshold + 1e-12,
                               slower_than_sequential=seconds > seq['median_seconds'],
                               oracle_variant=oracle['variant'], oracle_threads=oracle['threads'],
                               oracle_median_seconds=oracle['median_seconds']))
        hp, hseq = chosen_configuration(holdout_choices[key])
        stability.append(dict(kernel=kernel, size=size, variant=variant,
                              selection_threads=p, selection_sequential=use_seq,
                              holdout_threads=hp, holdout_sequential=hseq,
                              unchanged=(p, use_seq) == (hp, hseq)))
        inputs = [dict(mode='sequential' if r['variant'] == 'sequential' else 'openmp',
                       threads=r['threads'], median_seconds=r['median_seconds'], mean_seconds=r['mean_seconds']) for r in first]
        for near_tie in (0, .01, .02, .05):
            sp, sseq = chosen_configuration(select_at_threshold(inputs, near_tie))
            observed = next(r for r in second if (r['variant'], r['threads']) == ('sequential' if sseq else variant, sp))
            regret = observed['median_seconds'] / oracle['median_seconds'] - 1
            sensitivity.append(dict(kernel=kernel, size=size, variant=variant, near_tie_threshold=near_tie,
                                    threads=sp, sequential=sseq, regret_percent=100 * regret,
                                    inadequate=regret > threshold + 1e-12))
    return output, sensitivity, stability


def evaluate(frozen_path, evaluation, output):
    frozen = json.loads(frozen_path.read_text())
    first = Path(frozen['selection_campaign'])
    evaluation = evaluation.resolve()
    if first.resolve() == evaluation:
        raise ValueError('Evaluation must use a distinct later session')
    for filename, key in [('report.json', 'report_sha256'), ('samples.jsonl', 'samples_sha256')]:
        if digest((first / filename).read_bytes()) != frozen[key]:
            raise ValueError('Selection archive changed after freezing')
    if digest(Path(selector.__file__).read_bytes()) != frozen['selector_sha256']:
        raise ValueError('Selector changed after freezing')
    a, first_rows = verify(first)
    b, second_rows = verify(evaluation)
    if datetime.fromisoformat(b['started_utc']) <= datetime.fromisoformat(frozen['frozen_at_utc']):
        raise ValueError('Evaluation session must start after decisions were frozen')
    if selections(first_rows) != frozen['choices']:
        raise ValueError('Frozen decisions do not match the selection archive')
    if comparability(a, b) or compile_flags(first) != compile_flags(evaluation) or a['threads'] != b['threads']:
        raise ValueError('Incompatible session protocol, code, inputs or compilation flags')
    env_a = json.loads((first / 'environment.json').read_text())
    env_b = json.loads((evaluation / 'environment.json').read_text())
    if platform_identity(env_a) != platform_identity(env_b):
        raise ValueError('Different compiler/platform identity')
    rows, sensitivity, stability = evaluate_rows(first_rows, second_rows, frozen['choices'], frozen['inadequacy_threshold'])
    output.mkdir(parents=True, exist_ok=False)
    write_csv(output / 'policies.csv', rows)
    write_csv(output / 'sensitivity.csv', sensitivity)
    write_csv(output / 'stability.csv', stability)
    aggregates = {}
    for policy in ('sequential', 'max_threads', 'selector', 'fastest_selection'):
        values = [r for r in rows if r['policy'] == policy]
        aggregates[policy] = dict(cases=len(values), inadequate=sum(r['inadequate'] for r in values),
                                  inadequate_rate=sum(r['inadequate'] for r in values) / len(values),
                                  slower_than_sequential=sum(r['slower_than_sequential'] for r in values),
                                  mean_regret_percent=sum(r['regret_percent'] for r in values) / len(values),
                                  maximum_regret_percent=max(r['regret_percent'] for r in values))
    result = dict(status='VERIFIED_LATER_HOLDOUT', frozen=frozen,
                  frozen_file_sha256=digest(frozen_path.read_bytes()),
                  evaluation_campaign=str(evaluation), evaluation_report_sha256=digest((evaluation / 'report.json').read_bytes()),
                  evaluation_samples_sha256=digest((evaluation / 'samples.jsonl').read_bytes()),
                  policies=aggregates, stable_cases=sum(r['unchanged'] for r in stability), cases=len(stability),
                  limitations='Two sequential sessions on the same host/day; independent new observations, not independent machines or population estimates; oracle selected post hoc')
    write_json(output / 'report.json', result)
    lines = ['# Avaliação independente do Selector', '',
             'As decisões foram congeladas antes do início da segunda sessão. Cada política usa as novas quinze observações da configuração escolhida. O comparador descritivo é a menor mediana da segunda sessão, incluindo sequencial.', '',
             '| Caso / entrada / variante | Política | Configuração | Ganho total | Arrependimento (%) | Inadequada (>2%) |',
             '|---|---|---|---:|---:|---|']
    for r in rows:
        config = 'seq.' if r['evaluated_variant'] == 'sequential' else str(r['threads']) + 'T'
        lines.append(f"| {r['kernel']} / {r['size']} / {r['variant']} | {r['policy']} | {config} | {r['speedup_total']:.4f} | {r['regret_percent']:.3f} | {r['inadequate']} |")
    lines += ['', f"Recomendação estável em {result['stable_cases']}/{result['cases']} casos. Frequências descritivas por política: `{json.dumps(aggregates, ensure_ascii=False)}`.", '',
              'A sensibilidade aplica o Selector real com limiares de 0%, 1%, 2% e 5% somente à primeira sessão. O código de produção conserva 2%. Não há agrupamento de sessões ou teste de significância baseado no limiar operacional.', '']
    (output / 'REPORT.md').write_text('\n'.join(lines))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--evaluation', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.selection and not args.evaluation:
        print(json.dumps({'frozen_cases': len(freeze(args.selection, args.freeze)['choices'])}))
    elif args.evaluation and args.output and not args.selection:
        result = evaluate(args.freeze, args.evaluation, args.output)
        print(json.dumps({k: result[k] for k in ('status', 'cases', 'stable_cases', 'policies')}))
    else:
        parser.error('Use --selection to freeze, or --evaluation and --output to evaluate')
