# Revisão experimental — 05/11/2026

Execução Linux na branch `feat/experimentos-multiplataforma-2026-11-05`, baseada
no remoto mais recente disponível, `origin/feat/mac-pipeline-validation` em `32ae80b`.
Não foi feito push, merge de publicação ou inferência LLM nesta avaliação.

**Limite documental:** os três arquivos de 05/11 citados no pedido não foram
encontrados no checkout, nos ZIPs ou nas branches remotas após `git fetch`.
Por isso não é possível atestar a execução integral daquele plano específico.
Foi revisada a monografia mais recente disponível em Markdown (`BASE_MONOGRAFIA.md`),
com novo DOCX separado. A monografia reescrita citada permanece pendente de recebimento.

## 1. Pipeline

Além da campanha C++/PolyBench, o pipeline suportado executou duas vezes em
modo `--prepare-only`, com transformação determinística real de Dot C.
Os casos grande e pequeno terminaram PREPARED e passaram pela corretude em
1T–4T. Foram preservadas 50 amostras (cinco por configuração), candidato,
contextos e gates. Não se chamou o Coordinator nem se promoveu código.

## 2. Validação e testes

- 87 testes unittest aprovados, sem skips, em `unittest_final.log`.
- 23 casos das seis suítes de regressão aprovados.
- Teste adicional de isolamento de variantes aprovado, com análise Clang nova.
- 46 validações da campanha principal aprovadas: todas as entradas/variantes/threads.
- Arquivo principal conferido por hashes e tempos reconstruídos das saídas.
- Os 624 arquivos históricos de resultados mantiveram seus SHA-256.
- DOCX reaberto e conferido quanto a tabelas, imagens e presença dos novos resultados.
- `git diff --check` executado sem erros.

A primeira bateria expôs duas falhas de consolidação decorrentes de evidência Mac
indisponível no Linux. Corrigiu-se a leitura de resumo arquivado explícito, fixado
por hash e com estado ARCHIVED_SUMMARY_ONLY, mantendo erro em adulteração/contexto
inválido. A exceção MissingArtifactError continua derivada de ValueError; os gates
continuam recusando artefatos ausentes. O catálogo aponta para uma cópia intacta do
resumo anterior em vez de reescrever os caminhos absolutos dos relatórios.

O teste estático original também comparava caminhos históricos de outro host.
Agora ele executa o analisador e testa arquivos temporários novos. Os logs das
falhas iniciais foram mantidos, e as evidências históricas não foram corrigidas
para parecerem produzidas nesta máquina.

```bash
python3 -B -m unittest scripts.test_experiment_consolidation \
  scripts.test_coordinator_evaluation scripts.test_pipeline_integration \
  scripts.test_candidate_promotion scripts.test_gate_contracts \
  scripts.test_coordinator_scenarios scripts.test_benchmark_scaling
python3 -B scripts/test_coordinator_v02_regression.py
python3 -B scripts/test_performance_selector_v02_regression.py
python3 -B scripts/test_autotuning_selector_v01_regression.py
python3 -B scripts/test_adaptive_strategy_planner_v01_regression.py
python3 -B scripts/test_compiler_feedback_analyzer_v01_regression.py
python3 -B scripts/test_compiler_feedback_analyzer_v02_regression.py
python3 -B scripts/test_static_analysis_variant_isolation.py
```

## 3. Recorte da automação

Dot C automático pertence ao transformador determinístico do pipeline.
Dot C++, GEMM e Nussinov manual/SIMD manual são implementações preexistentes.
Nussinov SIMD automático é adaptação determinística específica sobre base
OpenMP, reutilizada sem nova geração nesta coleta. Nenhum ganho foi atribuído
à LLM. Não houve ampliação para GPU, geração universal ou reparo autônomo.

## 4. Avaliação dos agentes

A avaliação LLM real de 03/11 no M5 foi preservada. Esta coleta amplia a
avaliação de escalabilidade de kernels, sem ampliar os casos LLM nem repetir
inferências. As 12 respostas válidas do experimento anterior não são novas
amostras dos kernels de hoje. Os testes com respostas simuladas são técnicos.

## 5. Experimentos e resultados

Ambiente: Xeon E3-1225 V2, quatro núcleos físicos sem SMT, Linux x86_64,
Clang 18.1.3, governor schedutil, 8 MiB de LLC. O registro completo inclui
memória, carga inicial, afinidade disponível, comandos, bibliotecas e variáveis.
Não houve controle térmico/frequência dedicado nem coleta de contadores.

A campanha principal tem 46 configurações e 322 amostras externas, sete por
configuração, em ordem embaralhada por bloco (seed 2026). Um processo anterior
faz aquecimento. No Dot C++, a inicialização OpenMP pode integrar o tempo da
primeira chamada; o PolyBench inicializa workers no flush antes do timer.
As barras dos gráficos são mínimo–máximo, sem teste de significância.

| Caso | Variante | Menor mediana em | Tseq (s) | Tp (s) | S total | S paralelo | E paralela |
|---|---|---:|---:|---:|---:|---:|---:|
| dot 1000000 | manual | 2T | 0.001473456 | 0.002911023 | 0.5062 | 1.2208 | 0.6104 |
| dot 10000000 | manual | 3T | 0.010942113 | 0.010432664 | 1.0488 | 1.2375 | 0.4125 |
| gemm MEDIUM | manual | 4T | 0.004129000 | 0.001245000 | 3.3165 | 3.3671 | 0.8418 |
| gemm LARGE | manual | 3T | 0.644089000 | 0.284560000 | 2.2635 | 2.2476 | 0.7492 |
| nussinov MEDIUM | manual | 2T | 0.021994000 | 0.015356000 | 1.4323 | 1.8554 | 0.9277 |
| nussinov MEDIUM | simd_auto | 3T | 0.021994000 | 0.008536000 | 2.5766 | 2.2608 | 0.7536 |
| nussinov MEDIUM | simd_manual | 3T | 0.021994000 | 0.008553000 | 2.5715 | 2.2576 | 0.7525 |
| nussinov LARGE | manual | 4T | 16.885718000 | 4.596830000 | 3.6733 | 3.6165 | 0.9041 |
| nussinov LARGE | simd_auto | 4T | 16.885718000 | 4.820323000 | 3.5030 | 3.6430 | 0.9107 |
| nussinov LARGE | simd_manual | 4T | 16.885718000 | 4.898844000 | 3.4469 | 3.5846 | 0.8961 |

Esta tabela descreve a menor mediana, incluindo perdas. Não é uma seleção
automática de admissão: Dot C++ N=1 milhão não supera o sequencial em nenhuma
configuração. No Dot C do pipeline, a política de 2% recomendou 3T, embora a
menor mediana fosse em 4T; ganho total recomendado 1,263903×, escalabilidade
1,322175× e eficiência 0,440725. Dot C pequeno não admitiu paralelo.

Os diagnósticos confirmaram vetorização no laço k das versões SIMD, largura 4
e intercalação 2, mas Nussinov grande manual permaneceu mais rápido. A seção
`.text` dos executáveis SIMD manual/automático LARGE tem o mesmo SHA-256:
`0fd76d20837083583f782fbe35cf71b884c6724b7d024653d6881964abe283de`.
Diferenças de tempo entre esses executáveis não provam melhoria do código
computacional automático. Não se descartou o outlier de 8,119998 s da variante
SIMD manual em 4T.

O texto inclui comparação contextual 4T com GEMM/Nussinov históricos do M5 e
Dot C da promoção de 03/11, sem tratá-la como campanha nova pareada. Nussinov
automático histórico continua com hardware desconhecido. A nova coleta M5 é
necessária para comparar as duas entradas e curvas completas sob protocolo comum.

## 6. Monografia, arquivos e execução no Mac

- [Monografia Markdown atualizada](../monografia/BASE_MONOGRAFIA.md).
- [Novo DOCX](../monografia/MONOGRAFIA_ESCALABILIDADE_2026-11-05.docx).
- [Protocolo e comandos Linux/M5](../ESCALABILIDADE_MULTIPLATAFORMA_2026-11-05.md).
- [Relatório numérico e figuras](../../results/scaling/analysis_linux_xeon_2026-11-05/REPORT.md).
- [Amostras brutas](../../results/scaling/linux_xeon_2026-11-05/samples.csv).
- [Ambiente](../../results/scaling/linux_xeon_2026-11-05/environment.json).
- [Resumo do Dot C nativo](../../results/scaling/native_dot_summary_2026-11-05.json).
- [Logs e integridade histórica](../../results/scaling/validation_2026-11-05/).

Foram criados `scripts/benchmark_scaling.py`, `scripts/analyze_scaling.py` e
`scripts/test_benchmark_scaling.py`. Foram ajustados o carregador de proveniência,
a consolidação, seu catálogo/testes, o teste de isolamento e o exportador Word.
Os documentos de status/reprodução, a base da monografia e a bibliografia foram
atualizados. O manifesto enumera todos os arquivos novos/modificados e hashes.

A discussão foi ampliada nas seções 4.5, 5.5–5.7 e 6.1, com memória/cache,
sincronização por diagonais, SIMD, primeira chamada, banda lógica, quase empate,
heterogeneidade M5 e ameaças à validade. Resumo, abstract e conclusão foram
sincronizados. Os arquivos Office anteriores e os slides foram preservados.

**Pendências:** executar a coleta equivalente no M5; receber/conferir os três
documentos de 05/11; reconciliar esta revisão com a monografia reescrita correta;
revisar layout nativo Office e PDF institucional. Não foram feitos testes de
race ou medições de temperatura, banda física, energia ou contadores de cache.

O pacote de transferência contém as alterações sobre `32ae80b` e os resultados
Linux, sem `.git` nem venv. Aplicá-lo em cópia limpa dessa base, preservando
edições locais; inicializar PolyBench e recriar o ambiente Python no Mac.
Os artefatos Linux são para auditoria: não executar os binários no Mac nem
reescrever seus caminhos para aparentar nova medição.

