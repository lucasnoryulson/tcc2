# Item 5 — experimentos e reprodução

A coleta complementar Linux de **05/11/2026** tem protocolo próprio, arquivos
novos em `results/scaling/` e comandos para a execução equivalente no M5 em
[ESCALABILIDADE_MULTIPLATAFORMA_2026-11-05.md](ESCALABILIDADE_MULTIPLATAFORMA_2026-11-05.md).
Ela não sobrescreve os resultados ou a matriz histórica descritos abaixo.

A consolidação disponível em [results/consolidated/REPORT.md](../results/consolidated/REPORT.md)
reúne **22 campanhas**, seis kernels, variantes manuais/automáticas e resultados
positivos/negativos. O inventário cobre os 35 CSVs históricos disponíveis no
checkout inicial e nove CSVs gerados pelas campanhas finais. Não foram executados
novos benchmarks apenas para produzir a consolidação: as medições vieram das
campanhas já preservadas. Foram organizadas 173 configurações e recuperados 545
tempos individuais.

## Regerar a matriz sem Mac, Ollama ou submódulos

Na raiz `tcc2/`, com Python 3.12 (versão testada):

```bash
python3 -B scripts/consolidate_experiments.py --no-plots
python3 -B scripts/test_experiment_consolidation.py
```

As tabelas usam apenas a biblioteca padrão. Para regenerar também os gráficos,
instalar as dependências opcionais em um ambiente isolado:

```bash
python3 -m venv build/analysis-venv
build/analysis-venv/bin/python -m pip install -r requirements-analysis.txt
build/analysis-venv/bin/python -B scripts/consolidate_experiments.py
```

Nesta máquina o ambiente foi criado com `uv venv --system-site-packages` e os
pacotes instalados somente nele. Os gráficos foram efetivamente gerados com
Matplotlib 3.11.2 e NumPy 2.5.4. O script não exige essas bibliotecas com
`--no-plots`; não altera resultados históricos. Reexecutar sobrescreve apenas
os arquivos gerados em `results/consolidated/`. Usar `--output-dir` para outro
diretório reservado a relatórios. Não usar diretórios que contêm evidências.

| Arquivo gerado | Conteúdo |
|---|---|
| `matrix.csv` | Uma linha por campanha: origem, hardware, compilador, receita de flags/entrada, corretude registrada, contagem disponível, configuração selecionada e métricas separadas |
| `measurements.csv` | Uma linha por configuração: mediana, média, número de amostras e dispersão quando disponíveis |
| `samples.csv` | Tempos individuais recuperados dos logs, CSV bruto ou gates locais, sem agrupar campanhas |
| `report.json` | Evidências referenciadas, hashes atuais, lacunas, seleção recalculada, inventário e versão da biblioteca de gráficos |
| `REPORT.md` | Tabela de leitura, lacunas por campanha, inconsistências dos CSVs e gráficos |
| `scaling_*.svg/.pdf/.png` | Figuras separadas por ambiente, com um painel por campanha; SVG/PDF para monografia e PNG para inspeção |

## Como as campanhas foram escolhidas

O [catálogo](experiment_catalog.json) declara cada fonte, variante, ambiente,
receita e limitações. Nos casos de GEMM, Jacobi, Covariance e Nussinov do Xeon,
os logs de `repro_2026-09-04/performance/` são as fontes canônicas: seus tempos
individuais são legíveis e não dependem dos cabeçalhos quebrados dos CSVs.

No Mac são usados os CSVs normalizados e os logs correspondentes, conferindo
média/mediana com os tempos individuais. A tolerância absoluta dessa conferência
é 0,51 microssegundo, pois alguns logs imprimem somente seis casas decimais em
segundos; não é uma tolerância de corretude do código. Para Nussinov SIMD há CSV
bruto; para Nussinov automático há seleção explícita do timestamp de 11/09.
Para Wavefront tiled, a campanha `full` é distinta da `preliminary` e todas as
configurações da campanha escolhida permanecem na tabela de medições.

A seleção é recalculada pelas funções existentes do Performance Selector e do
Autotuning Selector, incluindo a política de quase empate de 2%. Logo, a
configuração recomendada pode usar menos threads que a configuração mais rápida:
Jacobi no Mac recomenda 7T, embora 10T tenha a menor mediana. O relatório JSON
preserva ambas. Essa é seleção analítica; não publica código nem converte um
resultado histórico em evidência aceita pelos gates atuais.

Os dados da avaliação LLM local não entram como repetições do kernel: somente
as duas medições determinísticas originais, grande/pequena, são consolidadas.
Prompts, respostas simuladas, latências de inferência e falhas LLM pertencem ao
[item 4](COORDINATOR_EVALUATION.md).

## Métricas e estatística

Para a mesma campanha e variante:

- Ganho contra o sequencial: `T_seq / T_p`.
- Ganho da transformação: `T_seq / T_1`.
- Escalabilidade paralela: `T_1 / T_p`.
- Eficiência paralela: `(T_1 / T_p) / p`.

Em autotuning, `T_1` usa **o mesmo bloco** da configuração avaliada. Comparar um
bloco em 1T com outro em várias threads mistura transformação e paralelismo.
Por exemplo, no Wavefront tiled do Mac, o bloco 64 com 4T tem ganho contra o
sequencial de aproximadamente 3,400× e escalabilidade do mesmo bloco de 2,377×.

Nussinov automático apresenta 4,106× contra o sequencial, mas aproximadamente
3,005× contra a sua variante OpenMP em 1T; eficiência paralela de 0,751 com 4T.
Não interpretar `4,106 / 4` como eficiência paralela. O hardware desse CSV não
está registrado na própria campanha, e foi mantido como desconhecido.

As amostras recuperadas permitem recalcular média, mediana, mínimo, máximo e
desvio padrão populacional (`pstdev`, como os harnesses históricos). Contagens
de amostras ausentes ficam desconhecidas: a receita atual usar cinco repetições
não prova que o resultado histórico tenha cinco amostras. Não foram inventados
intervalos de confiança a partir de medianas ou amostras independentes a partir
de execuções de LLM. As curvas exibem somente razões de medianas. Não há teste
de significância ou comparação estatística conjunta entre plataformas.

## Integridade, lacunas e inconsistências

`HISTORICAL_UNBOUND` significa que a medição foi recuperada, mas não possui o
contrato atual ligando fontes, compilador, corretude e benchmark. `sha256_now`
identifica o arquivo disponível hoje, sem demonstrar que esses eram os bytes
compilados historicamente. Os PASS/dumps históricos também não autorizam promoção.

`VERIFIED_LOCAL_GATES` requer que os artefatos originais da campanha local ainda
existam e passem pelas verificações atuais. Ao copiar somente o resumo para outra
máquina, o estado cai para `ARCHIVED_SUMMARY_ONLY`. Alteração detectada em um
artefato existente provoca falha; não é convertida silenciosamente em histórico.

O inventário lista linhas com número de campos incompatível, múltiplos baselines
e arquivos idênticos. Foram encontrados oito CSVs com cabeçalho incompatível e
arquivos acumulando campanhas distintas. Esses arquivos foram preservados como
histórico; não são lidos integralmente como uma única campanha. Novos arquivos
que aparecerem em `results/` também serão inventariados, sem inclusão automática
na matriz selecionada.

Flags e tamanhos apresentados como **receita** vêm dos scripts atuais. Versões
de compilador e hardware de uma captura de ambiente posterior/anterior não são
tratadas como medições específicas de cada execução. Faltam, em particular,
capturas próprias para parte das campanhas de setembro, vínculo de corretude
para todas as configurações e amostras individuais de Nussinov automático e dos
CSVs de autotuning tiled.

## Nova coleta com o pipeline suportado

O Dot Product C independente tem captura de fontes, compilador, flags, threads,
gates e amostras vinculadas. Para produzir evidências novas sem esperar pela LLM:

```bash
python3 -B scripts/run_pipeline.py --prepare-only --compiler gcc --threads 1 2
```

Para a comparação com agentes, executar a campanha do [item 4](COORDINATOR_EVALUATION.md).
No Mac, escolher a toolchain OpenMP instalada. O ambiente histórico registrou
`/opt/homebrew/opt/llvm/bin/clang`; confirmar a instalação atual. Apple Clang
sem OpenMP não satisfaz os gates. Não comparar hardware trocando apenas o nome
da máquina no catálogo: coletar evidências novas.

## Repetir casos legados sem alterar os históricos

PolyBench depende do submódulo. Neste checkout ele está **sem inicialização**:

```bash
git submodule update --init --recursive
git submodule status
```

Gitlinks registrados: PolyBenchC `3e872547cef7e5c9909422ef1e6af03cf4e56072`;
everythingsreduced `fb1c1cca72eaaa660fbfdf8623e79ad2ababbc29`. A segunda dependência
pertence aos benchmarks externos; os fixtures C independentes não precisam dela.

Os harnesses legados usam `clang`/`clang++` encontrados no PATH. Disponibilizar
a toolchain com OpenMP antes da execução. Exemplos com diretórios novos:

```bash
TCC2_THREAD_COUNTS=1,2,4 python3 -B scripts/benchmark.py gemm \
  --results-dir build/reproduction/campaign-01/gemm
TCC2_THREAD_COUNTS=1,2,4 python3 -B scripts/autotune_wavefront.py \
  --results-dir build/reproduction/campaign-01/wavefront-tiled
```

O primeiro aceita também `jacobi-2d`, `covariance`, `nussinov`, `nussinov-auto`,
`dot` e `wavefront`, com as variantes mapeadas no próprio script. Essa enumeração
não significa que todas as variantes sejam geradas automaticamente. O exemplo
de Nussinov SIMD manual possui fonte separada e não é selecionado automaticamente
por `benchmark.py nussinov`; preservar o candidato efetivamente compilado.

Usar um diretório novo para cada coleta. `--results-dir` recusa CSV existente;
o benchmark também recusa cabeçalhos incompatíveis no caminho legado. O autotuning
passou a recusar sobrescrita mesmo sem essa opção. Não executar campanhas em
paralelo: os diretórios de binários legados continuam compartilhados por kernel.

Conservar stdout/stderr completos, versões e caminhos dos compiladores, flags,
entrada, variáveis OpenMP, revisão Git e alterações locais, fontes/headers,
validação e tempos individuais. Esses harnesses legados ainda não produzem o
manifesto de proveniência dos novos gates; não apresentá-los como equivalentes.
O modo de corretude exato do PolyBench compara dumps da compilação de validação,
enquanto o benchmark usa `POLYBENCH_TIME`; o teste não cobre todas as entradas.

## Estado de fechamento

Verificação final executada nesta etapa: **82 testes unittest aprovados**, incluindo
19 testes da consolidação e dos comandos legados alterados, mais 14 casos de
regressão dos seletores e Coordinator. `git diff --check` passou. As 15 figuras
(cinco conjuntos em SVG/PDF/PNG) foram geradas; o novo PNG do Mac verificável
foram inspecionados visualmente. Os hashes dos 35 CSVs originais permaneceram
iguais antes/depois da geração.

```bash
python3 -B -m unittest scripts.test_experiment_consolidation \
  scripts.test_coordinator_evaluation scripts.test_pipeline_integration \
  scripts.test_candidate_promotion scripts.test_gate_contracts
python3 -B scripts/test_performance_selector_v02_regression.py
python3 -B scripts/test_autotuning_selector_v01_regression.py
python3 -B scripts/test_coordinator_v02_regression.py
```

A organização, o recálculo das métricas, os gráficos e os comandos estão prontos
para os dados disponíveis. As lacunas das 17 campanhas históricas foram declaradas,
as duas coletas Linux sem seus contextos originais foram reclassificadas como
`ARCHIVED_SUMMARY_ONLY` e três campanhas finais do Mac foram verificadas pelos
gates atuais. Isso conclui o item 5 dentro do acervo disponível, sem transformar
resultados históricos em evidência vinculada.
