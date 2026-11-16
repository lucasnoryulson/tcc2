"""Build a new manuscript from the publication version and verified Mac experiments."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_multiplatform_material import format_word, pdf_export

BASE = ROOT / 'results/multiplatform'
A1 = BASE / 'analysis_mac_m5_2026-11-16_session01'
A2 = BASE / 'analysis_mac_m5_2026-11-16_session02'
AL = BASE / 'analysis_linux_xeon_2026-11-05_p15w3'
HOLD = BASE / 'selector_holdout_mac_2026-11-16'
PROFILE = ROOT / 'results/profiling/mac_m5_2026-11-16_auxiliary'
COST = ROOT / 'results/pipeline_cost/mac_m5_2026-11-16'
WRITING = ROOT / 'docs/monografia'


def csv_rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def image_link(parent, file, title):
    return f'![{title}]({Path(os.path.relpath(file, parent)).as_posix()})'


def small_sample_statistics(costs, workers):
    from scripts.analyze_scaling import percentile
    from scripts.benchmark_scaling import write_csv
    values = []
    for mode in ('deterministic', 'coordinator'):
        for metric in ('shared_prefix_seconds', 'decision_seconds', 'promotion_seconds', 'total_accounted_seconds'):
            group = [float(r[metric]) for r in costs if r['mode'] == mode]
            values.append(('cost', mode, metric, group))
    for kernel in ('nussinov', 'jacobi-2d', 'covariance'):
        for size in ('MEDIUM', 'LARGE'):
            for threads in (1, 4, 10):
                fractions = []
                for repeat in (1, 2, 3):
                    trial = [r for r in workers if r['kernel'] == kernel and r['size'] == size and int(r['threads']) == threads and int(r['repeat']) == repeat]
                    total = sum(float(r['compute_seconds']) + float(r['barrier_seconds']) for r in trial)
                    fractions.append(sum(float(r['barrier_seconds']) for r in trial) / total)
                values.append(('profile', f'{kernel}/{size}/{threads}T', 'worker_wait_fraction', fractions))
    rows = []
    for experiment, group, metric, xs in values:
        median = statistics.median(xs)
        rows.append(dict(experiment=experiment, group=group, metric=metric, samples=len(xs), median=median,
                         mean=statistics.mean(xs), sample_sd=statistics.stdev(xs),
                         mad=statistics.median(abs(x-median) for x in xs),
                         iqr=percentile(xs, .75)-percentile(xs, .25), minimum=min(xs), maximum=max(xs),
                         bootstrap_ci95_low=None, bootstrap_ci95_high=None,
                         ci_limitation='Three auxiliary observations; below the declared minimum of 15 for bootstrap intervals'))
    write_csv(ROOT / 'docs/experiments/MAC_AUXILIARY_STATISTICS_2026-11-16.csv', rows)


def plots(output, mac, linux):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    output.mkdir(parents=True, exist_ok=True)
    kernels = ('dot-auto', 'dot', 'gemm', 'nussinov', 'jacobi-2d', 'covariance')
    for size_group in ('small', 'large'):
        for comparison in (True, False):
            fig, axes = plt.subplots(2, 3, figsize=(12, 7.5), squeeze=False)
            for ax, kernel in zip(axes.flat, kernels):
                size = ('1024' if size_group == 'small' else '10000000') if kernel == 'dot-auto' else ('1000000' if size_group == 'small' else '10000000') if kernel == 'dot' else ('MEDIUM' if size_group == 'small' else 'LARGE')
                platforms = [('Linux', linux), ('M5', mac)] if comparison else [('M5', mac)]
                for platform, rows in platforms:
                    variants = sorted({r['variant'] for r in rows if r['kernel'] == kernel} - {'sequential'})
                    for variant in variants:
                        curve = sorted((r for r in rows if r['kernel'] == kernel and r['size'] == size and r['variant'] == variant
                                        and (not comparison or int(r['threads']) in (1, 2, 4))), key=lambda r: int(r['threads']))
                        x = [int(r['threads']) for r in curve]
                        line, = ax.plot(x, [float(r['speedup_parallel']) for r in curve], 'o--' if platform == 'Linux' else 's-',
                                        label=f'{platform} {variant}', markersize=4)
                        ax.vlines(x, [float(r['speedup_parallel_ci95_low']) for r in curve],
                                  [float(r['speedup_parallel_ci95_high']) for r in curve], color=line.get_color(), alpha=.55)
                ax.set(title=f'{kernel} / {size}', xlabel='Threads', ylabel='T1 / Tp', xticks=(1, 2, 4) if comparison else (1, 2, 4, 6, 8, 10))
                ax.grid(alpha=.25)
                ax.legend(fontsize=7)
            fig.suptitle('Plataformas completas; pontos comuns e IC95% condicional' if comparison else 'M5: extensão até 10T; workers sem identificação P/E')
            fig.tight_layout()
            name = ('comparison' if comparison else 'mac_scaling') + '_' + size_group
            for extension in ('png', 'svg', 'pdf'):
                fig.savefig(output / f'{name}.{extension}', dpi=180)
            plt.close(fig)


def sections(parent, figures, rows, linux, hold, costs, workers):
    choices = json.loads((A1 / 'selection.json').read_text())
    choices2 = json.loads((A2 / 'selection.json').read_text())
    later = {(r['kernel'], str(r['size']), r['variant']): r['selection'] for r in choices2}
    policies = csv_rows(HOLD / 'policies.csv')
    lines = ['### 5.8. Apple M5 e comparação multiplataforma', '',
        'Duas sessões completas foram realizadas em 16/11/2026. Cada sessão preserva 108 configurações, 1.620 observações externas, 324 aquecimentos e 108 validações aprovadas. As observações das duas sessões permanecem em arquivos separados. A primeira sessão determina as decisões; a segunda avalia sua reaplicação.', '',
        'O M5 possui 4 núcleos de desempenho e 6 de eficiência, com 16 GiB de memória e macOS 26.6.2. LLVM Homebrew 23.1.1 e o runtime registrado por otool compõem a plataforma experimental. A energia registrada no início da primeira sessão foi bateria. Não houve controle exclusivo de temperatura, frequência ou carga do sistema. O probe confirmou equipes de 1/2/4/6/8/10 workers; não identificou sua classe de núcleo.', '',
        'A comparação com Linux foi aprovada pelo verificador: bytes de fontes, headers e drivers, dimensões, flags, aquecimentos, repetições e seed coincidem. Linux usa Clang 18.1.3 e outro runtime. Os pontos comuns são 1T, 2T e 4T; diferenças observadas pertencem às plataformas completas.', '',
        '| Caso / entrada / variante | S1: recomendação | S total S1 [IC95%] | S paralelo S1 | S2: recomendação |',
        '|---|---:|---:|---:|---:|']
    for c in choices:
        k = c['kernel'], str(c['size']), c['variant']
        selected = c['selection'].get('recommended')
        p = selected['threads'] if selected else None
        r = next(r for r in rows if (r['kernel'], r['size'], r['variant'], int(r['threads'])) == (k[0], k[1], k[2] if p else 'sequential', p or 1))
        p2 = (later[k].get('recommended') or {}).get('threads')
        interval = f"{float(r['speedup_total']):.3f} [{float(r['speedup_total_ci95_low']):.3f}; {float(r['speedup_total_ci95_high']):.3f}]" if p else '1,000 (sequencial)'
        scale = f"{float(r['speedup_parallel']):.3f}" if p else '—'
        lines.append(f"| {' / '.join(k)} | {str(p)+'T' if p else 'seq.'} | {interval} | {scale} | {str(p2)+'T' if p2 else 'seq.'} |")
    lines += ['', image_link(parent, figures / 'comparison_large.png', 'Escalabilidade das entradas grandes nos pontos comuns Linux/M5'), '',
              image_link(parent, figures / 'mac_scaling_large.png', 'Escalabilidade M5 até dez threads nas entradas grandes'), '',
              'As entradas menores também possuem figuras próprias e os CSVs completos registram mediana, média, DP amostral, MAD, IQR e IC95% para todas as configurações. ICs usam 5.000 reamostragens pareadas por rodada; não se interpretam como causalidade arquitetural ou prova de independência temporal.', '',
              '### 5.9. Avaliação independente da recomendação', '',
              'As 16 decisões da primeira sessão foram congeladas com hashes antes do início da segunda. As quatro políticas utilizam somente configurações definidas na primeira coleta: sequencial, máximo de threads, recomendação do Selector e menor mediana OpenMP. O comparador posterior é a menor mediana da segunda sessão incluindo sequencial. O arrependimento é percentual de tempo excedente; inadequação operacional significa exceder 2%.', '',
              '| Política | Casos inadequados / 16 | Arrependimento médio (%) | Maior arrependimento (%) | Mais lentos que sequencial |',
              '|---|---:|---:|---:|---:|']
    for mode, r in hold['policies'].items():
        lines.append(f"| {mode} | {r['inadequate']}/16 | {r['mean_regret_percent']:.3f} | {r['maximum_regret_percent']:.3f} | {r['slower_than_sequential']} |")
    lines += ['', f"As recomendações coincidiram em {hold['stable_cases']}/{hold['cases']} casos entre sessões. O arquivo de sensibilidade aplica limiares de 0%, 1%, 2% e 5% somente aos dados de seleção; a política de produção conserva 2%. O mínimo posterior foi escolhido após observar a segunda sessão e é uma referência descritiva, não um ótimo populacional. A média de arrependimento dá o mesmo peso a cada caso; perdas muito grandes nas entradas pequenas podem dominá-la.", '',
              '| Caso / entrada / variante | Configuração congelada | S total na S2 | Excesso sobre melhor S2 (%) |',
              '|---|---:|---:|---:|']
    for r in policies:
        if r['policy'] == 'selector':
            label = 'seq.' if r['evaluated_variant'] == 'sequential' else r['threads']+'T'
            lines.append(f"| {r['kernel']} / {r['size']} / {r['variant']} | {label} | {float(r['speedup_total']):.3f} | {float(r['regret_percent']):.3f} |")
    sensitivity = csv_rows(HOLD / 'sensitivity.csv')
    production = {(r['kernel'], r['size'], r['variant']): (r['threads'], r['sequential'])
                  for r in sensitivity if float(r['near_tie_threshold']) == .02}
    lines += ['', '| Limiar de quase empate | Decisões diferentes de 2% | Inadequadas na S2 | Arrependimento médio (%) |',
              '|---|---:|---:|---:|']
    for threshold in (0, .01, .02, .05):
        group = [r for r in sensitivity if float(r['near_tie_threshold']) == threshold]
        changed = sum((r['threads'], r['sequential']) != production[r['kernel'], r['size'], r['variant']] for r in group)
        inadequate = sum(r['inadequate'] == 'True' for r in group)
        mean = statistics.mean(float(r['regret_percent']) for r in group)
        lines.append(f'| {100*threshold:.0f}% | {changed}/16 | {inadequate}/16 | {mean:.3f} |')
    lines += ['', '### 5.10. Investigação dos gargalos no Mac', '',
        'A instalação disponível contém somente Command Line Tools; xcrun informa que xctrace não está disponível. Não foram obtidos contadores de cache ou DRAM. A investigação auxiliar usa cópias instrumentadas e mede intervalos de computação e espera em barreiras por worker em 1T, 4T e 10T, com três observações por entrada. Cada saída instrumentada foi comparada exatamente ao dump sequencial da campanha principal. As esperas incluem desbalanceamento, escalonamento e sincronização; não isolam um custo puro do runtime.', '',
        '| Kernel / entrada | Workers | Espera / (computação + espera), mediana (%) | Máx./mín. de itens atribuídos |',
        '|---|---:|---:|---:|']
    for kernel in ('nussinov', 'jacobi-2d', 'covariance'):
        for p in (4, 10):
            group = [r for r in workers if r['kernel'] == kernel and r['size'] == 'LARGE' and int(r['threads']) == p]
            ratios, counts = [], []
            for repeat in (1, 2, 3):
                trial = [r for r in group if int(r['repeat']) == repeat]
                work = sum(float(r['compute_seconds']) for r in trial)
                wait = sum(float(r['barrier_seconds']) for r in trial)
                ratios.append(100 * wait / (work + wait))
                items = [int(r['assigned_items']) for r in trial]
                if items and min(items) > 0:
                    counts.append(max(items) / min(items))
            ratio = f'{statistics.median(ratios):.2f}'
            count = f'{statistics.median(counts):.3f}' if counts else 'não contado'
            lines.append(f'| {kernel} / LARGE | {p} | {ratio} | {count} |')
    lines += ['', 'Em Covariance, a contagem registra pares (i,j) da fase triangular e os intervalos abrangem somente essa fase. Em Nussinov, os itens são células das diagonais; igualdade de células não implica igualdade de trabalho, pois a redução interna muda de comprimento. Em Jacobi, os intervalos abrangem as duas varreduras por passo de tempo. A instrumentação adiciona relógios, contadores e barreiras explícitas equivalentes; seus tempos não substituem os da campanha principal.', '',
        'No Dot, a variação entre entradas e threads mede quando overhead domina, mas não isola fisicamente a banda. A taxa 16*N/T é derivada dos bytes lógicos de entrada; caches e reutilização das chamadas internas impedem tratá-la como tráfego DRAM. GEMM mantém reuso e laço contíguo, porém a localidade permanece hipótese sem contadores. Em Jacobi, pressão de memória e barreiras podem atuar juntas. A espera instrumentada confirma intervalos de espera no código medido, sem atribuir todo o efeito à memória ou às classes P/E.', '',
        'O experimento Linux preparado em scripts/profile_linux_followup.sh coleta ciclos, instruções, eventos genéricos de cache, trocas de contexto e migrações em novo diretório. Banda física exige eventos suportados do controlador de memória, que devem ser escolhidos após consultar perf list. Nenhuma medição desse roteiro Linux foi presumida.', '',
        '### 5.11. Custo do pipeline e ponto de equilíbrio', '',
        'O custo foi medido em uma campanha técnica separada, com três prefixos reais de Dot C. Cada prefixo executa análise, dependências, classificação, planejamento, transformação, corretude, benchmark, seleção e contexto. Compilações e execuções internas possuem telemetria própria. Cada prefixo é compartilhado pela política determinística e pelo Coordinator LLM; alterna-se a ordem das decisões. O benchmark original dos gates conserva cinco observações por configuração, sem somá-las às quinze da campanha principal.', '',
        '| Braço | Prefixo mediano (s) | Decisão mediana (s) | Promoção mediana (s) | Custo contabilizado mediano (s) | Equilíbrio mediano (execuções) |',
        '|---|---:|---:|---:|---:|---:|']
    for mode in ('deterministic', 'coordinator'):
        group = [r for r in costs if r['mode'] == mode]
        def med(field):
            return statistics.median(float(r[field]) for r in group)
        n = [int(r['break_even_executions']) for r in group if r['break_even_executions']]
        lines.append(f"| {mode} | {med('shared_prefix_seconds'):.3f} | {med('decision_seconds'):.6f} | {med('promotion_seconds'):.3f} | {med('total_accounted_seconds'):.3f} | {statistics.median(n):.0f} |" if n else f"| {mode} | {med('shared_prefix_seconds'):.3f} | {med('decision_seconds'):.6f} | {med('promotion_seconds'):.3f} | {med('total_accounted_seconds'):.3f} | sem economia positiva |")
    stage_rows = csv_rows(COST / 'stages.csv')
    lines += ['', '| Etapa medida | Mediana inclusiva (s) | Compilação interna mediana (s) | Execução interna mediana (s) |', '|---|---:|---:|---:|']
    for stage in dict.fromkeys(r['stage'] for r in stage_rows):
        group = [r for r in stage_rows if r['stage'] == stage]
        values = [statistics.median(float(r[f]) for r in group) for f in ('inclusive_seconds', 'compilation_seconds', 'execution_seconds')]
        lines.append(f"| {stage} | {values[0]:.6f} | {values[1]:.6f} | {values[2]:.6f} |")
    lines += ['', 'O equilíbrio é ceil(C/(Tseq−Topt)) quando a economia por chamada é positiva. C inclui o prefixo, decisão/validação da decisão e promoção. A promoção já inclui recompilação e corretude fresca; somar novamente esses tempos internos contaria o mesmo trabalho duas vezes. As medianas por etapa não são somadas para reconstruir a mediana do total. Os custos dos braços são comparações contabilizadas sobre prefixos comuns, não seis pipelines independentes.', '',
        'Falhas, recusas e timeouts permanecem nos arquivos de tentativa; ausência de economia recebe equilíbrio indefinido. O modelo é local e a inferência inclui estado de carregamento/cache observado. O ganho do kernel é produzido pela transformação, configuração e hardware, não pela LLM que decide sobre evidências já medidas. As três observações dos custos e perfis têm mediana, DP amostral, MAD e IQR em MAC_AUXILIARY_STATISTICS_2026-11-16.csv; seus ICs ficam ausentes por não atingir o mínimo pré-definido de quinze observações. Esses ensaios auxiliares não estimam distribuição populacional.', '']
    return '\n'.join(lines)


def build(no_export=False):
    for analysis in (A1, A2):
        if json.loads((analysis / 'verification.json').read_text())['status'] != 'VERIFIED_ARCHIVE':
            raise ValueError('Verified Mac analysis required')
    comparison = json.loads((BASE / 'comparison_linux_mac_2026-11-16/comparability.json').read_text())
    if comparison['status'] != 'MATCHED_PROTOCOL':
        raise ValueError('Compatible cross-platform data required')
    hold = json.loads((HOLD / 'report.json').read_text())
    if hold['status'] != 'VERIFIED_LATER_HOLDOUT':
        raise ValueError('Frozen later-session evaluation required')
    profile = json.loads((PROFILE / 'report.json').read_text())
    cost_report = json.loads((COST / 'report.json').read_text())
    if profile['status'] != 'COMPLETE' or cost_report['status'] not in ('COMPLETE', 'COMPLETE_WITH_FAILURES'):
        raise ValueError('Complete auxiliary measurements required')
    rows, linux = csv_rows(A1 / 'measurements.csv'), csv_rows(AL / 'measurements.csv')
    costs, workers = csv_rows(COST / 'costs.csv'), csv_rows(PROFILE / 'workers.csv')
    small_sample_statistics(costs, workers)
    figures = WRITING / 'figures_mac_2026-11-16'
    plots(figures, rows, linux)
    original = WRITING / 'REVISAO_PUBLICACAO.md'
    text = original.read_text()
    before = {str(original.relative_to(ROOT)): hashlib.sha256(original.read_bytes()).hexdigest()}
    for extension in ('docx', 'pdf'):
        p = original.with_suffix('.' + extension)
        before[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    # Keep the previous manuscript as a source artifact; write only new dated files.
    title_end = text.index('## Resumo')
    text = '# Paralelização OpenMP baseada em evidências\n\n## Pipeline verificável, avaliação multiplataforma e limites de um Coordinator LLM\n\nLucas Nory Ulson — Ciência da Computação, PUCRS\n\nPorto Alegre, 2026\n\n' + text[title_end:]
    text = text.replace('A coleta M5 equivalente permanece pendente.', 'Duas sessões equivalentes no M5 acrescentaram 3.240 observações externas em arquivos próprios; a recomendação foi avaliada em uma sessão posterior à seleção.')
    text = text.replace('The equivalent new M5 campaign remains pending.', 'Two equivalent M5 sessions added 3,240 external observations in separate archives, with recommendations evaluated in a session started after selection was frozen.')
    text = text.replace('Resultados da nova\ncampanha M5 só serão acrescentados após execução real.', 'As novas sessões M5 e a avaliação independente são descritas em 5.8–5.11.')
    text = text.replace('A nova coleta M5 e a conferência institucional final permanecem pendentes.', 'As duas sessões M5 completaram a comparação nos pontos comuns; a avaliação posterior do Selector e o custo de admissão qualificam a interpretação dos ganhos. Limitações de instrumentação e apresentação institucional permanecem explicitadas.')
    text = text.replace('## 5. Resultados disponíveis', '## 5. Resultados experimentais')
    text = text.replace('## 7. Conclusão compatível com as evidências atuais', '## 7. Conclusão')
    text = re.sub(r'### 3\.8\. Procedimento de apresentação institucional.*?(?=### 3\.9\.)', '', text, flags=re.S)
    text = text.replace('### 3.9. Contrato conservador', '### 3.8. Contrato conservador')
    text = text.replace('M5 do acervo histórico', 'Apple M5 das novas sessões')
    text = text.replace('16 GB registrados em 03/11', '16 GiB observados em 16/11')
    text = text.replace('LLVM Homebrew 23.1.1 registrado em 03/11', 'LLVM Homebrew 23.1.1 observado em 16/11')
    text = text.replace('Estado atual deve ser registrado na nova coleta', 'Bateria em descarga nos registros iniciais das sessões')
    text = text.replace('A coluna M5 descreve o acervo, não uma observação feita nesta execução Linux.\nO novo script registra novamente modelo, sistema, compilador, contagens de\nnúcleos e energia.', 'A caracterização M5 foi registrada novamente em 16/11/2026, incluindo modelo, sistema, compilador, contagens de núcleos e energia.')
    methodology = ('### 4.11. Avaliação posterior do Selector, perfis e custo no M5\n\n'
        'O protocolo M5 conserva três aquecimentos e quinze medições em 1/2/4/6/8/10T. As duas sessões contêm os mesmos códigos e entradas. As decisões do Selector e seus hashes foram congelados após a primeira sessão e antes do início da segunda. O avaliador exige essa ordem temporal, integridade dos arquivos e a mesma identidade de plataforma/compilador. A inadequação operacional é definida antes da segunda coleta como excesso de tempo maior que 2% sobre a menor mediana posterior, incluindo sequencial. São examinados também limiares de quase empate de 0%, 1%, 2% e 5%, sem alterar a produção.\n\n'
        'Os perfis auxiliares instrumentam cópias dos fontes e medem intervalos por worker, preservando as dependências com barreiras explícitas. Três execuções por entrada e configuração 1/4/10T são comparadas aos dumps sequenciais. Seus tempos não são amostras da campanha principal. A ausência de xctrace e de contadores é registrada; tempos de espera não se convertem em estimativas de misses ou tráfego físico.\n\n'
        'O custo é medido em três prefixos reais, cada qual compartilhado entre decisão determinística e LLM. A ordem dos braços alterna; cada inferência tem uma chamada, e timeout encerra a campanha. O estado do servidor, modelo e metadados observados são arquivados. Compilações e execuções dos gates possuem telemetria separada; promoção inclui nova compilação e corretude. O equilíbrio usa a economia por chamada e não inclui uma segunda contagem dos tempos internos.\n\n')
    text = text.replace('## 5. Resultados experimentais', methodology + '## 5. Resultados experimentais', 1)
    theory = (ROOT / 'docs/experiments/MAC_EVALUATION_THEORY.md').read_text()
    text = text.replace('## 3. Arquitetura e implementação', theory + '\n## 3. Arquitetura e implementação', 1)
    main_sections = sections(WRITING, figures, rows, linux, hold, costs, workers)
    text = text.replace('## 6. Discussão e ameaças à validade', main_sections + '\n## 6. Discussão e ameaças à validade', 1)
    extra = ('### 6.3. Síntese das questões de pesquisa após a avaliação Mac\n\n'
             'R1: o contrato e as verificações de identidade sustentam admissão rastreável no subconjunto implementado; os oráculos são empíricos. R2: as sessões M5 e Linux caracterizam plataformas completas, e a reaplicação do Selector mede o risco operacional da decisão em novos tempos. R3: o custo adicional da inferência é comparado com a mesma política e o mesmo prefixo; qualquer igualdade de código e configuração implica a mesma economia medida por chamada. R4: os diagnósticos heldout anteriores conservam sua rubrica, falhas e resultado negativo; os novos perfis de workers não são novas respostas de diagnóstico da LLM.\n\n'
             'A bateria estava em descarga no início das sessões; estado energético, serviços do host e duas sessões no mesmo dia limitam generalização. As esperas por worker foram medidas em código instrumentado. Banda DRAM, cache misses, afinidade P/E e causalidade térmica permanecem sem medição no Mac disponível. O roteiro Linux prepara esses exames, sem lhes atribuir resultados. O arrependimento usa um mínimo posterior sujeito a ruído, e seu limiar de 2% é operacional.\n\n')
    text = text.replace('## 7. Conclusão', extra + '## 7. Conclusão', 1)
    # Statements in older experiments describe their historical collection date.
    text = text.replace('A comparação com a nova campanha M5 permanece pendente.', 'A comparação desta campanha Linux com as sessões M5 está apresentada em 5.8.')
    text = text.replace('A nova coleta M5 continua pendente.', 'As sessões M5 posteriores e sua avaliação independente estão apresentadas em 5.8–5.9.')
    text = text.replace('A campanha nova equivalente no M5\nestá preparada, mas não foi medida nesta máquina Linux.', 'As sessões M5 equivalentes ao protocolo principal de quinze observações foram medidas em 16/11 e estão em 5.8; esta coleta exploratória mantém seu protocolo próprio.')
    text = text.replace('mas os novos pontos M5 ainda não foram coletados. O subconjunto\n1T/2T/4T servirá à comparação com códigos e entradas verificados; 6T/8T/10T\nserão analisados como extensão heterogênea.', 'e os novos pontos M5 são apresentados em 5.8. O subconjunto 1T/2T/4T foi comparado com códigos e entradas verificados; 6T/8T/10T constituem a extensão heterogênea medida.')
    text = text.replace('o trecho de comparação direta será 1T/2T/4T.', 'o trecho de comparação direta usa 1T/2T/4T.')
    text = text.replace('As novas curvas M5 nas mesmas entradas, fontes,\nrepetições e política de medição ainda são necessárias para fortalecer esta\ncomparação.', 'As sessões M5 equivalentes ao protocolo principal estão em 5.8, com conferência de fontes, entradas e protocolo. Este contraste exploratório permanece separado.')
    observed = (f"Na avaliação posterior, o Selector teve {hold['policies']['selector']['inadequate']}/16 recomendações inadequadas pelo limiar operacional de 2%, contra {hold['policies']['max_threads']['inadequate']}/16 ao usar dez threads; {hold['stable_cases']}/16 escolhas repetiram-se entre sessões. ")
    text = text.replace('Os resultados sustentam uma', observed + 'Os resultados sustentam uma', 1)
    text = text.replace('The findings support a restricted,',
        f"In the later-session evaluation, {hold['policies']['selector']['inadequate']}/16 Selector choices exceeded the operational 2% regret threshold, compared with {hold['policies']['max_threads']['inadequate']}/16 for ten threads; {hold['stable_cases']}/16 recommendations repeated across sessions. The findings support a restricted,", 1)
    text = text.replace('## Referências verificadas para esta revisão', '## Referências')
    if '## Apêndice de rastreabilidade e atualização' in text:
        text = text[:text.index('## Apêndice de rastreabilidade e atualização')] + (
            '## Apêndice B. Rastreabilidade e reprodução\n\n'
            'Os arquivos Linux anteriores permanecem em results/multiplatform/linux_xeon_2026-11-05_p15w3 e results/publication. As duas sessões Mac são mac_m5_2026-11-16_p15w3_session01 e session02, sob results/multiplatform. Cada sessão preserva comandos, stdout/stderr, snapshots, executáveis, hashes, amostras e resultados de corretude. Os arquivos de análise correspondentes registram o método estatístico e a conferência de integridade.\n\n'
            'A decisão congelada está em mac_m5_2026-11-16_selector_frozen.json; a avaliação posterior, em selector_holdout_mac_2026-11-16. Perfis de workers ficam em results/profiling/mac_m5_2026-11-16_auxiliary, e o custo em results/pipeline_cost/mac_m5_2026-11-16. Modelos, prompts, respostas, telemetria e promoções pertencem a esses arquivos próprios. Caminhos absolutos dos registros identificam o ambiente de execução e não devem ser reescritos para simular outra máquina.\n\n'
            'O código-base é 0d3b54733f4c04a699c5f4e1787b1a7f21ef6f1b; o experimento foi realizado em branch específica e worktree separado. A versão anterior REVISAO_PUBLICACAO.md/.docx/.pdf foi preservada por hash. O manifesto da versão datada registra os arquivos novos. O PDF é uma exportação de conteúdo por ReportLab; o layout nativo Word e os requisitos institucionais exigem conferência no aplicativo de entrega.\n')
    references = ('Amdahl, Gene M. Validity of the Single Processor Approach to Achieving Large Scale Computing Capabilities. Spring Joint Computer Conference, 1967, p. 483–485. [Artigo original](https://www.cs.cmu.edu/~18742/papers/Amdahl1967.pdf).\n\n'
                  'Whaley, R. Clint; Petitet, Antoine; Dongarra, Jack J. Automated Empirical Optimizations of Software and the ATLAS Project. Parallel Computing, 27(1–2), 3–35, 2001. DOI 10.1016/S0167-8191(00)00087-9. [Texto dos autores](https://netlib.org/utk/people/JackDongarra/PAPERS/2001_Automated-Empirical-Optimizations-of-Software-and-the-ATLAS-Project.pdf).\n\n')
    text = text.replace('Efron, Bradley. Bootstrap Methods:', references + 'Efron, Bradley. Bootstrap Methods:', 1)
    target = WRITING / 'REVISAO_EXPERIMENTAL_MAC_2026-11-16.md'
    target.write_text(text)
    report_file = ROOT / 'docs/experiments/MAC_EVALUATION_2026-11-16_REPORT.md'
    report_file.write_text('# Avaliação experimental Linux e Apple M5 — 16/11/2026\n\n' + sections(report_file.parent, figures, rows, linux, hold, costs, workers))
    manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(), previous_manuscript_sha256=before,
                    data=dict(mac_session01=str(A1.relative_to(ROOT)), mac_session02=str(A2.relative_to(ROOT)),
                              holdout=hold['status'], profile=profile['status'], costs=cost_report['status']),
                    renderer='ReportLab content PDF; Word layout and institutional template require native review')
    if not no_export:
        manifest['word_checks'] = format_word(target, target.with_suffix('.docx'), revision='Paralelização OpenMP baseada em evidências — 16/11/2026')
        pdf_export(target, target.with_suffix('.pdf'))
    files = [target, report_file, ROOT / 'docs/experiments/MAC_AUXILIARY_STATISTICS_2026-11-16.csv', *figures.glob('*')]
    if not no_export:
        files += [target.with_suffix('.docx'), target.with_suffix('.pdf')]
    manifest['files'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    for name, expected in before.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Previous manuscript was modified')
    (WRITING / 'MAC_EVALUATION_2026-11-16_MANIFEST.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-export', action='store_true')
    args = parser.parse_args()
    print(json.dumps(build(args.no_export).get('word_checks', {})))
