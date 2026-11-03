# TCC2

Sistema híbrido de análise estática, transformação OpenMP e coordenação por LLM.

Para continuar este trabalho em outra sessão ou no Mac, leia o
[contexto atualizado do Codex](tcc2_contexto_para_codex/docs/TCC2_CONTEXT.md), o
[histórico da conversa](tcc2_contexto_para_codex/docs/CONVERSA_E_DECISOES.md) e o
[roteiro de retomada](tcc2_contexto_para_codex/RETOMAR_NO_MAC.md).
O `AGENTS.md` da raiz aponta para essas instruções automaticamente.

## Pipeline completo e promoção

Com Clang, um compilador com OpenMP e o Ollama/modelo disponíveis, execute:

```bash
python3 scripts/run_pipeline.py --compiler gcc --threads 1 2 \
  --model qwen2.5:3b --timeout 600
```

O exemplo usa Dot Product e seus drivers existentes. O comando executa análise,
transformação, gates, Selector, Context Builder, Coordinator e promoção. Cada
tentativa conserva comandos, logs, evidências e `summary.json` em uma pasta
exclusiva sob `build/pipeline/`. `--source`, `--driver` e `--benchmark-driver`
permitem fornecer outro caso dentro do mesmo contrato de fontes C independentes,
mas o transformador genérico atual só publica redução escalar direta autorizada
pelo Planner; estratégias não suportadas são recusadas.
O compilador precisa aceitar `-O3 -fopenmp`; selecione a toolchain adequada ao
ambiente, especialmente no Mac.

Somente `ACCEPT` com `PROMOTE_CANDIDATE` chega ao executor. Uma decisão de
`RETUNE`, `MODIFY` ou `REJECT` interrompe o fluxo sem publicar código; a ação
pendente fica registrada. Este comando não implementa um ciclo automático de
recuperação para estratégias ainda não suportadas.

O executor exige configuração selecionada e medida, ganho contra o sequencial
e contra OpenMP com uma thread, e sucesso paralelo. Reconfere a cadeia de hashes,
recompila o candidato e executa novamente a corretude na configuração escolhida.
Uma reprovação ou divergência não deixa uma pasta final aprovada.

O resultado é publicado de uma vez em `results/promoted/<identificador>/`:

- `parallel.c`: bytes exatos do candidato validado e medido.
- `manifest.json`: configuração, métricas separadas, hashes, campanha, toolchain,
  origem e comando para reproduzir a corretude.
- `evidence/`: fontes, drivers, executáveis e cópias dos relatórios/decisão usados.
- `revalidation.json`, `revalidation.log` e `revalidation/`: resultado e artefatos
  da nova compilação/execução.

O identificador deriva da campanha e do candidato; uma promoção duplicada é
recusada, sem sobrescrever a anterior. A publicação usa staging e uma reserva
exclusiva. Se um processo for morto sem executar a limpeza, pode restar uma
reserva oculta `.lock`; inspecione a execução antes de removê-la.

Também é possível terminar uma execução já medida:

```bash
python3 agents/coordinator_agent.py build/dot/context.json \
  --model qwen2.5:3b --output build/dot/decision.json \
  --promote-to results/promoted
```

Ou usar uma decisão já produzida pelo Coordinator, ainda vinculada às evidências:

```bash
python3 scripts/promote_candidate.py build/dot/decision.json \
  --output-dir results/promoted
```

Um artefato produzido em teste com resposta simulada da LLM verifica a integração,
mas não demonstra autonomia da LLM ou sua contribuição científica. Essa distinção
é mantida nos relatórios de validação.

O [escopo comprovado da automação](docs/AUTOMATION_SCOPE.md) separa classificação,
transformação, variantes históricas e execução integrada por kernel.

## Evidências de corretude e desempenho

Execute os comandos na raiz do repositório, com Python, Clang para análise
estática e GCC com OpenMP para os gates. Não há dependências Python externas
para estes testes.

O contrato de evidência cobre os três arquivos de entrada explícitos: original,
candidato e driver. Cada gate preserva cópias em um diretório exclusivo da
execução, compila essas cópias e registra SHA-256 de fontes e executáveis,
compilador identificado por caminho/hash/versão, flags, ambiente OpenMP, data UTC,
plataforma, ID da campanha e medições. Alterações posteriores nas entradas,
cópias ou executáveis invalidam a evidência.

A campanha é criada pelo gate de corretude. O gate de desempenho exige esse
relatório, usa a mesma identidade do candidato e do compilador, herda a campanha
e preserva uma cópia do relatório de corretude. Todos os números de threads do
benchmark precisam ter passado pela validação numérica.

## Exemplo com Dot Product

Gere análises e candidato novos para a execução:

```bash
python3 analysis/static_analyzer.py analysis/fixtures/dot_product.c
python3 analysis/dependence_analyzer.py analysis/output/dot_product_analysis.json
python3 analysis/pattern_classifier.py \
  analysis/output/dot_product_analysis.json \
  analysis/output/dot_product_dependences.json
python3 analysis/strategy_planner.py \
  analysis/output/dot_product_analysis.json \
  analysis/output/dot_product_patterns.json
python3 analysis/code_transformer.py \
  analysis/fixtures/dot_product.c \
  analysis/output/dot_product_analysis.json \
  analysis/output/dot_product_strategy.json \
  --output build/dot/dot_product_openmp.c
```

Valide o candidato com os números de threads que serão medidos:

```bash
python3 scripts/compile_correctness_gate.py \
  --sequential analysis/fixtures/dot_product.c \
  --candidate build/dot/dot_product_openmp.c \
  --driver analysis/fixtures/dot_driver.c \
  --compiler gcc --threads 1 2 \
  --build-dir build/dot/correctness \
  --output build/dot/correctness.json
```

O relatório de corretude tem schema `tcc2-correctness-gate`, versão `0.2`.
A saída do processo é `0` para PASS e diferente de zero para falha. Em Python,
`run_gate()` retorna o relatório. Este driver compara um resultado escalar com
tolerâncias relativas de `1e-9` e absolutas de `1e-12`.

Meça o desempenho com o driver específico de benchmark:

```bash
TCC2_THREAD_COUNTS=1,2 python3 scripts/performance_gate.py \
  --sequential analysis/fixtures/dot_product.c \
  --candidate build/dot/dot_product_openmp.c \
  --driver analysis/fixtures/dot_benchmark_driver.c \
  --compiler gcc --correctness build/dot/correctness.json \
  --build-dir build/dot/performance \
  --csv build/dot/performance.csv \
  --output build/dot/performance.report.json
```

O gate registra as cinco repetições externas de cada configuração. A mediana,
a média e os speedups do CSV precisam corresponder aos tempos brutos. O relatório
tem schema `tcc2-performance-gate`, versão `0.1`. Sem `--output`, seu nome deriva
do CSV com sufixo `.report.json`.

O processo retorna `0` quando há ganho contra o sequencial e `1` quando não há,
inclusive em empate. Uma execução completa sem ganho conserva medições válidas
para análise e rejeição pelo pipeline. Erros de compilação, execução e medição
não produzem evidência de benchmark completa. Nunca use um CSV antigo para
compensar um gate que falhou.

Selecione somente a partir do CSV vinculado ao relatório:

```bash
python3 analysis/performance_selector.py build/dot/performance.csv \
  --performance-report build/dot/performance.report.json \
  --output build/dot/selection.json
```

O Selector verifica os hashes e a consistência das medições e inclui a referência
ao relatório na seleção. O uso sem `--performance-report` continua disponível
para analisar campanhas históricas, mas produz uma seleção sem proveniência
aceitável pelo Context Builder.

```bash
python3 agents/context_builder.py \
  --source analysis/fixtures/dot_product.c \
  --candidate build/dot/dot_product_openmp.c \
  --static analysis/output/dot_product_analysis.json \
  --dependences analysis/output/dot_product_dependences.json \
  --patterns analysis/output/dot_product_patterns.json \
  --strategy analysis/output/dot_product_strategy.json \
  --selection build/dot/selection.json \
  --correctness build/dot/correctness.json \
  --output build/dot/context.json
```

O Context Builder v0.3 exige corretude e benchmark vinculados à mesma campanha.
Ele recalcula a seleção determinística, confere hashes e usa os bytes das cópias
validadas para preencher o código no contexto. A configuração final deve ser uma
configuração efetivamente medida. O Coordinator preserva os parâmetros também
quando a única dimensão é `threads`.

A saída do Coordinator também registra o hash do contexto recebido, o
`candidate_id` e a campanha. Esses valores vêm do contexto de entrada, sem
depender de a LLM copiá-los. Contextos históricos sem identidade continuam úteis
para diagnóstico, mas não fornecem essa vinculação para uma futura promoção.

## Limites e reprodução

Conserve os relatórios e seus diretórios de execução juntos. Os caminhos são
absolutos: ao trocar de checkout ou máquina, gere evidências novas. Relatórios e
contextos históricos sem proveniência não são migrados nem tratados como prova
da campanha atual.

Este caminho atende fontes e drivers independentes, como o Dot Product. Headers
de projeto, bibliotecas externas, toolchain completa e conjuntos de entradas não
são integralmente arquivados por este contrato; o hash do compilador não substitui
a descrição do ambiente. Suporte a dependências de projeto exige captura dessas
dependências antes de ampliar o escopo.

Os hashes verificam integridade de artefatos produzidos localmente; não são uma
assinatura de um produtor externo. O executor repete a corretude antes de publicar.
Um PASS declarado manualmente não constitui evidência suficiente para promoção.

## Avaliação dos agentes — item 4

```bash
python3 -B scripts/evaluate_coordinator.py \
  --compiler gcc --threads 1 2 --model qwen2.5:3b --repetitions 3 --timeout 600
```

Compara a política determinística, o Coordinator completo e uma ablação das
análises estruturadas, usando os mesmos candidatos/medições em dois tamanhos de
Dot Product. Gera JSON, CSV, prompts e relatório Markdown por campanha, com
falhas preservadas. No Mac, ajustar `--compiler` à toolchain OpenMP instalada.
`--baseline-only` executa a parte determinística sem chamar o modelo.

O estudo mede decisões e custo de inferência; `RETUNE/MODIFY` não executam uma
busca por novos candidatos. O protocolo, as métricas e os critérios de conclusão
estão em [docs/COORDINATOR_EVALUATION.md](docs/COORDINATOR_EVALUATION.md).

## Testes

```bash
python3 -B scripts/test_gate_contracts.py
python3 -B scripts/test_candidate_promotion.py
python3 -B scripts/test_pipeline_integration.py
python3 -B scripts/test_coordinator_evaluation.py
python3 -B scripts/test_experiment_consolidation.py
python3 -B scripts/test_coordinator_v02_regression.py
python3 -B scripts/test_performance_selector_v02_regression.py
python3 -B scripts/test_autotuning_selector_v01_regression.py
```

A suíte de contratos inclui compilação e validação reais com GCC/OpenMP, rejeição
de candidato incorreto, alterações de artefatos, mistura de campanhas, divergências
de CSV/configuração e threads não validadas. Os testes de saída do benchmark usam
tempos controlados, sem afirmar speedup real. As campanhas científicas devem ser
executadas no hardware alvo com os drivers de benchmark originais.

## Matriz experimental e reprodução — item 5

Os resultados disponíveis foram consolidados em
[results/consolidated/REPORT.md](results/consolidated/REPORT.md): 22 campanhas,
seis kernels, 173 configurações, 545 tempos recuperados e gráficos SVG/PDF/PNG. O relatório
separa ganho contra o sequencial de escalabilidade OpenMP e distingue medições
históricas de evidências verificadas pelos gates atuais.

Para regenerar as tabelas sem Mac, Ollama ou dependências Python externas:

```bash
python3 -B scripts/consolidate_experiments.py --no-plots
```

Para incluir os gráficos, usar um ambiente virtual com
`requirements-analysis.txt` e executar o mesmo script sem `--no-plots`.
O [guia de reprodução](docs/EXPERIMENT_REPRODUCTION.md) documenta instalação,
fontes escolhidas, fórmulas, inconsistências dos CSVs, lacunas e comandos para
novas campanhas. O catálogo explícito está em
[docs/experiment_catalog.json](docs/experiment_catalog.json).

Os harnesses legados `benchmark.py` e `autotune_wavefront.py` aceitam
`--results-dir` para coletar em diretórios novos. Não anexar novas medições aos
CSVs históricos: alguns acumulam campanhas e versões diferentes de cabeçalho.

O estado de conclusão do TCC, com a numeração dos seis itens originais, está em
[docs/STATUS_TCC.md](docs/STATUS_TCC.md).

## Redação e defesa — item 6

Os três documentos Word recebidos foram comparados ao código e às evidências.
O [guia de fechamento](docs/FECHAMENTO_TCC.md) reúne os arquivos preparados e
as pendências pelos seis itens originais:

- [Base Word da monografia](docs/monografia/BASE_MONOGRAFIA.docx) e
  [fonte Markdown](docs/monografia/BASE_MONOGRAFIA.md).
- [PowerPoint com 16 slides e notas](docs/defesa/DEFESA_RASCUNHO.pptx) e
  [roteiro de fala](docs/defesa/SLIDES.md).
- [Demonstração reproduzível](docs/defesa/DEMONSTRACAO.md).
- [Revisão dos documentos recebidos](docs/monografia/LEITURA_DOS_DOCUMENTOS.md).

O gerador `scripts/build_academic_material.py` usa as dependências opcionais de
`requirements-writing.txt`. Ele exporta os rascunhos a partir dos Markdown e
preserva os Word originais. A avaliação LLM permanece pendente, inclusive na
redação e nos slides; conferir o formato de entrega e o layout nos aplicativos.
