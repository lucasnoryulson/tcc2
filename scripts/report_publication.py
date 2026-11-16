"""Generate the new scientific review from verified, separately identified studies."""
import argparse
import csv
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evaluate_automation_corpus import verify_archive
from scripts.evaluate_diagnostics import DEFAULT_CATALOG, digest, model_view, prompt, score, summarize, verify_catalog


def n(value):
    return '—' if value is None else f'{float(value):.5g}'


def recommended(rows, choice):
    selected = choice['selection'].get('recommended')
    return next(r for r in rows if r['kernel'] == choice['kernel'] and r['size'] == choice['size']
                and r['variant'] == (choice['variant'] if selected else 'sequential')
                and int(r['threads']) == (selected['threads'] if selected else 1)), selected


def verify_diagnostics(directory):
    data = json.loads((directory / 'results.json').read_text())
    catalog = verify_catalog(DEFAULT_CATALOG)
    if (data['status'] not in ('BASELINE_ONLY', 'COMPLETE', 'COMPLETE_WITH_FAILURES', 'INCOMPLETE_TIMEOUT')
            or data['catalog_sha256'] != digest(DEFAULT_CATALOG)
            or digest(directory / 'catalog.json') != data['catalog_sha256']
            or data['implementation_sha256'] != digest(ROOT / 'scripts/evaluate_diagnostics.py')):
        raise ValueError('Diagnostic campaign is incomplete or uses different sources.')
    cases = {c['id']: c for c in catalog['cases']}
    settings = data['settings']
    selected = [c for c in catalog['cases'] if (settings['split'] == 'all' or c['split'] == settings['split'])
                and (not settings['case_ids'] or c['id'] in settings['case_ids'])]
    modes = ['rules'] if settings['baseline_only'] else ['rules', 'coordinator', 'coordinator_without_analysis']
    schedule = [(c['id'], mode, repetition) for c in selected
                for repetition in range(1, settings['repetitions'] + 1) for mode in modes]
    random.Random(settings['options']['seed']).shuffle(schedule)
    if schedule != [(t['case_id'], t['mode'], t['repetition']) for t in data['trials']]:
        raise ValueError('Diagnostic slots/order differ from the frozen schedule.')
    keys = {(t['case_id'], t['mode'], t['repetition']) for t in data['trials']}
    if len(keys) != len(data['trials']) or len(keys) != data['planned_slots']:
        raise ValueError('Missing or duplicate diagnostic slots.')
    timeout_halted = False
    for position, trial in enumerate(data['trials'], 1):
        work = directory / f"{position:03d}-{trial['case_id']}-{trial['repetition']}-{trial['mode']}"
        case = cases[trial['case_id']]
        ablated = trial['mode'] == 'coordinator_without_analysis'
        if (digest(work / 'prompt.json') != trial['prompt_sha256']
                or json.loads((work / 'prompt.json').read_text()) != prompt(case, ablated)
                or json.loads((work / 'trial.json').read_text()) != trial):
            raise ValueError('Diagnostic prompt/trial differs from its recorded case.')
        attempted = not (timeout_halted and trial['mode'] != 'rules')
        derived = {key: case[key] for key in ('family', 'split', 'origin')}
        derived.update(analysis_available=bool(case['evidence']['analysis']),
                       ablation_effective=(prompt(case)['user'] != prompt(case, True)['user']) if ablated else None,
                       attempted=attempted, llm_calls=int(attempted and trial['mode'] != 'rules'), retries=0)
        if any(trial[key] != value for key, value in derived.items()):
            raise ValueError('Diagnostic derived fields differ from the frozen case/schedule.')
        if (trial['status'] not in ('OK', 'INVALID', 'ERROR', 'TIMEOUT', 'NOT_RUN')
                or (trial['status'] == 'NOT_RUN') != (not attempted)
                or (trial['mode'] == 'rules' and trial['status'] != 'OK')
                or (trial['status'] in ('OK', 'INVALID') and
                    (trial['schema_valid'] != (trial['status'] == 'OK') or 'raw_response_sha256' not in trial))
                or (trial['status'] in ('ERROR', 'TIMEOUT', 'NOT_RUN') and
                    (trial['output'] is not None or trial['metadata'] != {}))):
            raise ValueError('Diagnostic state is inconsistent with its attempt/response.')
        timeout_halted |= trial['status'] == 'TIMEOUT'
        if 'raw_response_sha256' in trial:
            if digest(work / 'raw_response.json') != trial['raw_response_sha256']:
                raise ValueError('Raw diagnostic response changed.')
            if trial['status'] in ('OK', 'INVALID'):
                raw = json.loads((work / 'raw_response.json').read_text())
                if trial['mode'] == 'rules':
                    parsed = raw
                else:
                    try:
                        parsed = json.loads(raw.get('message', {}).get('content', ''))
                    except (ValueError, TypeError):
                        parsed = None
                metadata = {} if trial['mode'] == 'rules' else {key: value for key, value in raw.items() if key != 'message'}
                if metadata != trial['metadata']:
                    raise ValueError('Diagnostic metadata differs from the raw response.')
                if parsed != trial['output']:
                    raise ValueError('Parsed diagnosis differs from the raw response.')
        expected = score(case, model_view(case, ablated), trial['output'])
        if any(trial[key] != value for key, value in expected.items()):
            raise ValueError('Diagnostic score differs from the frozen rubric.')
    status = 'BASELINE_ONLY' if settings['baseline_only'] else ('INCOMPLETE_TIMEOUT' if timeout_halted else
             ('COMPLETE' if all(t['status'] == 'OK' for t in data['trials']) else 'COMPLETE_WITH_FAILURES'))
    if data['status'] != status:
        raise ValueError('Diagnostic campaign status differs from its trials.')
    if (data['groups'] != summarize(data['trials']) or data['analysis_available_groups'] !=
            summarize([t for t in data['trials'] if t['analysis_available']])):
        raise ValueError('Diagnostic aggregate differs from its trials.')
    return data


def generate(corpus, diagnostics, sessions, output):
    report = verify_archive(corpus)['report']
    assert report['measured'] and report['protocol']['samples'] == 15 and report['protocol']['warmups'] == 3
    if not report['protocol'].get('gcc_baseline'):
        raise ValueError('This report requires the measured same-compiler GCC baseline.')
    coverage = report['coverage']['all']
    patterns = {p['id']: p['pattern'] for p in json.loads((corpus / 'coverage.json').read_text())['programs']}
    rows = list(csv.DictReader((corpus / 'summary.csv').open()))
    choices = json.loads((corpus / 'selection.json').read_text())
    table = ['| Fonte / N=1.000.000 | Pipeline: threads / ganho total | GCC autopar: threads / ganho total | Tempo GCC / pipeline recomendado |',
             '|---|---:|---:|---:|']
    ratios, by_pattern = [], {}
    for kernel in sorted({r['kernel'] for r in rows}):
        pair = []
        for variant in ('pipeline_openmp', 'gcc_autopar'):
            choice = next(c for c in choices if c['kernel'] == kernel and c['size'] == 'large' and c['variant'] == variant)
            pair.append(recommended(rows, choice))
        (pipeline, p), (gcc, g) = pair
        ratio = float(gcc['median_seconds']) / float(pipeline['median_seconds'])
        ratios.append(ratio)
        by_pattern.setdefault(patterns[kernel], []).append(ratio)
        label = lambda selected: str(selected['threads']) + 'T' if selected else 'seq'
        table.append(f"| {kernel} | {label(p)} / {n(pipeline['speedup_total'])}× | {label(g)} / {n(gcc['speedup_total'])}× | {n(ratio)}× |")
    lines = ['# Fortalecimento científico — resultados executados no Linux', '',
             'Este relatório mantém separados corpus de transformação, conformidade diagnóstica, repetibilidade e as 900 medições anteriores. Não houve novas medições M5.', '',
             '## Corpus e comparação com uma ferramenta existente', '',
             f"Estado do arquivo: {report['status']}. Foram avaliadas {coverage['programs']} fontes autorais: {coverage['supported_expected']} no subconjunto suportado e {coverage['unsupported_expected']} recusas previstas. Houve {coverage['true_acceptances']} aceitações e {coverage['true_refusals']} recusas conforme a especificação, {coverage['false_acceptances']} aceitações indevidas, {coverage['false_refusals']} recusas indevidas e {coverage['unexpected_errors']} erros inesperados. Os {coverage['functional_inputs_passed']} pares positivos fonte × entrada passaram na validação funcional, com saída por elemento nos DOALL.", '',
             f"A campanha contém {report['configurations']} configurações, {report['sample_count']} observações externas e {report['warmup_count']} aquecimentos. As chamadas internas são amortização, não amostras independentes. Gates e cada processo medido verificam a saída observável.", '',
             'Original sequencial, fonte gerada e autoparalelização GCC usam o mesmo GCC, driver e entradas. O braço GCC usa -ftree-parallelize-loops=p; os objetos de kernel são compilados separadamente do driver. Ativar a flag não comprova uso efetivo de p workers. T1/Tp nesse braço compara configurações compiladas separadamente.', '',
             'O contraste de desempenho cobre somente as fontes positivas do nosso contrato. As recusas não constituem comparação de cobertura geral com GCC; alguns programas fora do nosso subconjunto podem ser paralelizáveis por outras técnicas.', '',
             *table, '',
             f"A média geométrica descritiva das {len(ratios)} razões de tempo GCC/pipeline recomendadas na entrada grande é {n(math.exp(sum(map(math.log, ratios)) / len(ratios)))}×. Valores acima de um favorecem o tempo do pipeline nessas fontes; não são estimativa sobre programas externos nem isolamento da qualidade de um compilador geral. A escolha por quase empate pode diferir da menor mediana.", '',
             'Por padrão: ' + '; '.join(f"{key}: {len(values)} fontes, razão geométrica {n(math.exp(sum(map(math.log, values)) / len(values)))}×" for key, values in sorted(by_pattern.items())) + '.', '',
             'Nas reduções, a diretiva OpenMP permite outra ordem de soma, avaliada com tolerância numérica. GCC sem flags de reassociação pode preservar a ordem sequencial e recusar a paralelização floating-point. Logo, uma vantagem nas reduções não demonstra superioridade geral da análise de dependências do pipeline. Os resultados DOALL são separados dessa diferença de semântica/contrato.', '',
             'As tabelas completas, ICs condicionais, tempos, escolhas e recusas estão no arquivo da campanha. O split autoral organiza a análise; não é teste cego externo. Não houve detector de races, prova formal ou teste dinâmico do contrato restrict.', '',
             '## Diagnóstico offline: rubrica oculta, não promoção', '',
             'O catálogo tem 24 vistas sobre cinco famílias, incluindo incidentes arquivados, extrações e injeções controladas realmente executadas. Os rótulos são autorais e derivados de rubrica mecânica; regras concordam por construção, sem validação humana independente. A avaliação final usa 12 vistas de três famílias heldout, uma chamada por caso/braço/modelo. O caso de desenvolvimento do preflight fica separado.', '',
             '| Modelo / braço heldout | Executados / planejados | JSON válido / executados | Causa + ação conforme / executados | Propostas perigosas | Claims sem suporte / verificados | Mediana da chamada (s) |',
             '|---|---:|---:|---:|---:|---:|---:|']
    verify_catalog(DEFAULT_CATALOG)
    seen_rules = False
    statuses = []
    ablation = ['| Modelo / caso com análise removível | Completo: estado / causa e ação | Sem análise: estado / causa e ação |',
                '|---|---|---|']
    costs = ['| Modelo / braço | Chamadas reais | Respostas com contagem de tokens | Prompt observado | Geração observada | Soma do tempo das tentativas (s) |',
             '|---|---:|---:|---:|---:|---:|']
    identities = []
    for directory in diagnostics:
        data = verify_diagnostics(directory)
        if data['catalog_sha256'] != digest(DEFAULT_CATALOG):
            raise ValueError('Diagnostics use another frozen annotation.')
        if data['status'] == 'RUNNING':
            raise ValueError('Diagnostic campaign is still running.')
        statuses.append(f"{data['settings']['model']}: {data['status']}")
        metadata = data.get('server_metadata', {})
        model = next((m for m in metadata.get('tags', {}).get('models', [])
                      if m.get('name') == data['settings']['model']), {})
        details = metadata.get('show', {}).get('details', {})
        identities.append(f"{data['settings']['model']}: digest {model.get('digest', 'ausente')[:12]}, "
                          f"{details.get('parameter_size', 'tamanho ausente')}, {details.get('quantization_level', 'quantização ausente')}, "
                          f"Ollama {metadata.get('version', {}).get('version', 'versão ausente')}")
        for group in data['groups']:
            if group['split'] != 'heldout':
                continue
            mode = group['mode']
            if mode == 'rules' and seen_rules:
                continue
            seen_rules |= mode == 'rules'
            trials = [t for t in data['trials'] if t['mode'] == mode and t['split'] == 'heldout']
            attempted = [t for t in trials if t['status'] != 'NOT_RUN']
            valid, correct = sum(t['schema_valid'] for t in attempted), sum(t['cause_action_correct'] for t in attempted)
            name = 'regras' if mode == 'rules' else data['settings']['model'] + ' / ' + mode
            lines.append(f"| {name} | {len(attempted)}/{len(trials)} | {valid}/{len(attempted)} | {correct}/{len(attempted)} | {sum(t['dangerous_proposal'] for t in attempted)} | {sum(t['unsupported_claims'] for t in attempted)}/{sum(t['claims_count'] for t in attempted)} | {n(group['median_wall_seconds'])} |")
            if mode != 'rules':
                observed = sum(all(type(t['metadata'].get(key)) is int for key in ('prompt_eval_count', 'eval_count')) for t in attempted)
                costs.append(f"| {name} | {sum(t['llm_calls'] for t in trials)} | {observed} | {n(group['prompt_eval_count_observed_sum'])} | {n(group['eval_count_observed_sum'])} | {n(sum(t['wall_seconds'] for t in attempted))} |")
        effective = [t for t in data['trials'] if t['split'] == 'heldout' and t['ablation_effective'] is True]
        for removed in effective:
            full = next(t for t in data['trials'] if t['case_id'] == removed['case_id']
                        and t['repetition'] == removed['repetition'] and t['mode'] == 'coordinator')
            def outcome(trial):
                return trial['status'] + ' / ' + (str(int(trial['cause_action_correct'])) if trial['attempted'] else 'não observado')
            ablation.append(f"| {data['settings']['model']} / {removed['case_id']} | {outcome(full)} | {outcome(removed)} |")
    lines += ['', 'Estados: ' + '; '.join(statuses) + '.', '',
              'Identidades observadas: ' + '; '.join(identities) + '. Os digests completos e metadados estão em results.json.', '',
              *costs, '',
              'As contagens de tokens são os campos efetivamente devolvidos pelo servidor. Uma resposta sem metadados não recebe estimativa; somas observadas não substituem latência e incluem os efeitos de cache/carregamento da execução.', '',
              'Slots ausentes não são respostas incorretas observadas; cobertura planejada e desempenho nas tentativas aparecem separados. Contagens 0/0 representam ausência de avaliação, não taxa de acerto ou ausência de erros.', '',
              'A ablação é efetiva somente em dois dos doze casos heldout; os outros prompts são idênticos. O pareamento e esse estrato estão registrados por tentativa. Claims são triplas checadas por igualdade exata contra fatos, não avaliação humana de justificativa livre. Respostas inválidas não são prova de ausência de afirmações falsas. Uma única repetição não caracteriza variância do modelo; não se estima acurácia populacional.', '',
              *ablation, '',
              'Timeout é terminal para chamadas de modelo na campanha. As demais ficam NOT_RUN, sem retry oculto. Latência inclui carregamento e cache do servidor; diferenças entre braços não isolam causalmente o tamanho do contexto.', '',
              '## Repetibilidade sem agrupar sessões', '']
    repeat = json.loads((sessions / 'report.json').read_text())
    if repeat['status'] != 'VERIFIED_SEPARATE_SESSIONS':
        raise ValueError('Verified separate sessions required.')
    lines += [f"Foram comparadas {len(repeat['sessions'])} sessões, com {repeat['common_configurations']} configurações comuns. A terceira coleta priorizou MEDIUM e os Dot; LARGE de PolyBench tem somente duas sessões. Cada mediana conserva suas quinze observações. O código desta repetição foi congelado em b9e252d, separadamente da nova extensão do transformador.", '',
              'São sessões do mesmo dia e host, executadas em sequência sem inferência ou testes concorrentes. Isso não demonstra independência, temperatura/frequência controladas ou repetição em dias diferentes. O relatório de sessões apresenta CV das medianas e mudanças de recomendação sem fundir tempos brutos.', '',
              '## Papel da LLM e limites', '',
              'No experimento histórico de admissão, o Selector já escolhe a configuração e o Executor exige a mesma escolha. Portanto, a LLM não pode superar o speedup do baseline nesse desenho; concordância, vetos e custo são os resultados empíricos. Diagnóstico offline é uma tarefa separada e não demonstra geração, reparo ou promoção.', '',
              'A comparação com trabalhos próximos é bibliográfica; a comparação executada com ferramenta externa é o braço GCC no corpus controlado. Não se reproduziram OMPar, P4OMP ou RepoOMP. Não se alega prioridade absoluta de pipelines híbridos baseados em evidências.', '',
              'Faltam a nova matriz no M5, revisão humana independente do corpus/rubrica, conferência institucional e layout nativo Office. Scripts e PDFs de revisão não equivalem a essas validações.', '']
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines))
    return dict(programs=coverage['programs'], observations=report['sample_count'], diagnostics=statuses,
                sessions=len(repeat['sessions']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--diagnostics', type=Path, nargs='+', required=True)
    parser.add_argument('--sessions', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/publication/RESULTS.md')
    args = parser.parse_args()
    print(json.dumps(generate(args.corpus, args.diagnostics, args.sessions, args.output)))
