# Entrega da avaliação experimental no Mac — 16/11/2026

O trabalho foi executado na branch `feat/mac-experimental-evaluation-2026-11-16`,
base `0d3b54733f4c04a699c5f4e1787b1a7f21ef6f1b`, em worktree separado
`tcc2-experiments-mac-2026-11-16/`. O checkout original `tcc2/` conserva as
alterações anteriores. A primeira conclusão de ausência da branch foi corrigida
após a atualização remota se tornar disponível. Não houve push ou merge.

## Experimentos concluídos e achados

| Experimento | Execução efetiva | Resultado |
|---|---|---|
| Matriz M5 equivalente à Linux | Duas sessões completas; cada uma com 108 configurações, 1.620 observações, 324 aquecimentos e 108 validações PASS | Mesmos bytes de fontes/headers/drivers, dimensões, flags, seed e protocolo; comparação `MATCHED_PROTOCOL` em 1/2/4T e curvas M5 até 10T |
| Selector em novas medições | 16 decisões congeladas por hash antes da segunda sessão | 14/16 recomendações estáveis; 1/16 inadequada pelo critério operacional de excesso maior que 2% sobre o melhor tempo posterior, incluindo sequencial |
| Políticas alternativas | Mesma sessão posterior para todas as escolhas | Máximo de threads: 9/16 inadequadas; menor mediana OpenMP da seleção: 2/16; Selector: 1/16 |
| Sensibilidade ao quase empate | Selector real aplicado à S1 com 0%, 1%, 2% e 5% | 0–2%: 1/16 inadequada; 5%: 3/16. Produção mantém o limiar de 2% |
| Perfis por worker | 54 observações em cópias instrumentadas de Nussinov, Jacobi e Covariance; MEDIUM/LARGE e 1/4/10T | Saídas conferidas com dumps sequenciais. Em Nussinov LARGE, espera agregada mediana de 12,0% em 4T e 61,3% em 10T. Covariance LARGE/10T: razão de itens máximo/mínimo 18,85 |
| Custo e amortização | Três prefixos reais, três decisões determinísticas e três inferências `llama3.1:8b`, com seis promoções revalidadas | Mediana contabilizada: 11,865 s determinístico e 20,842 s LLM; equilíbrio mediano: 3.360 e 5.929 chamadas. Mesma configuração admitida por par; nenhum ganho adicional observado da LLM |

O caso inadequado do Selector foi Nussinov MEDIUM manual: 4T recomendado na
S1 levou 0,006819 s na S2, frente a 0,006101 s sequencial, excesso de 11,769%.
A outra mudança de recomendação entre sessões foi Dot C++ grande, de 10T para
6T. Os resultados desfavoráveis e todas as observações foram preservados.

Na S1, os ganhos totais recomendados nas entradas grandes foram 3,679× no
Dot C automático/10T; 2,677× no Dot C++ manual/10T; 4,976× em GEMM/10T;
2,703× em Nussinov manual/4T; 3,963× em SIMD adaptado/4T; 3,953× em SIMD
manual/4T; 2,525× em Jacobi/10T; e 4,295× em Covariance/10T. O Dot C pequeno
conservou o sequencial. Esses ganhos pertencem aos códigos e configurações,
não à LLM. Ganho total e escalabilidade têm denominadores distintos.

As tabelas completas, ICs e a discussão estão no
[relatório científico](MAC_EVALUATION_2026-11-16_REPORT.md). Custos e perfis têm
três observações por grupo; DP amostral, MAD e IQR estão no
[CSV auxiliar](MAC_AUXILIARY_STATISTICS_2026-11-16.csv), com ICs ausentes por não
atingir o mínimo declarado de quinze observações. As campanhas principais
possuem IC bootstrap pareado de 5.000 réplicas por sessão, além dos demais
resumos; as amostras de sessões diferentes não foram agrupadas.

## Arquivos e caminhos

- Coletas: `results/multiplatform/mac_m5_2026-11-16_p15w3_session01/` e `session02/`.
- Análises: `results/multiplatform/analysis_mac_m5_2026-11-16_session01/` e `session02/`.
- Comparação: `results/multiplatform/comparison_linux_mac_2026-11-16/`.
- Repetibilidade: `results/multiplatform/session_comparison_mac_2026-11-16/`.
- Decisões congeladas: `results/multiplatform/mac_m5_2026-11-16_selector_frozen.json`.
- Avaliação posterior: `results/multiplatform/selector_holdout_mac_2026-11-16/`.
- Perfis: `results/profiling/mac_m5_2026-11-16_auxiliary/`.
- Custos, prompts, modelo, telemetria e promoções: `results/pipeline_cost/mac_m5_2026-11-16/`.
- Hardware/ferramentas: `results/multiplatform/mac_m5_2026-11-16_host_tools/`.
- Validação: `results/validation/mac_experimental_2026-11-16/`.
- Monografia: [Markdown](../monografia/REVISAO_EXPERIMENTAL_MAC_2026-11-16.md),
  [Word](../monografia/REVISAO_EXPERIMENTAL_MAC_2026-11-16.docx) e
  [PDF de 78 páginas](../monografia/REVISAO_EXPERIMENTAL_MAC_2026-11-16.pdf).
- Integridade acadêmica: `docs/monografia/MAC_EVALUATION_2026-11-16_MANIFEST.json`.

Arquivos de implementação novos: `evaluate_selector_holdout.py`,
`measure_pipeline_cost.py`, `process_timing.py`, `profile_openmp_auxiliary.py`,
`profile_linux_followup.sh`, `record_mac_tools.py`,
`build_mac_evaluation_material.py`, `validate_mac_evaluation.py`,
`test_selector_holdout.py` e `test_experiment_cost.py`, todos em `scripts/`.
Foram ajustados `analyze_scaling.py` e `compare_sessions.py` para relatos sem
pendência M5 obsoleta; os dois gates receberam telemetria opcional e o runner
identifica a etapa na telemetria. `test_benchmark_scaling.py` passou a usar o
driver `clang++` ao testar C++. O README aponta à nova entrega e
`requirements-experimental.txt` permite recriar o ambiente isolado.

## Testes e verificações

129 unittests aprovados em 31,174 s, sem falhas ou skips; seis scripts de
regressão aprovados em 23 casos; isolamento estático PASS; sintaxe do roteiro
Linux PASS. Logs completos e comandos estão no
[relatório de validação](../../results/validation/mac_experimental_2026-11-16/report.json).
A execução inicial expôs uma expectativa de exceção incorreta em um teste novo;
ela foi corrigida e a suíte final passou. Avisos preexistentes `ResourceWarning`
de leituras CSV do corpus permanecem no log e não foram ocultados.

Os arquivos das duas sessões foram verificados por hash e tiveram resumos
reconstruídos do stdout/amostras. Todos os hashes dos seis manifestos de
promoção foram conferidos. Os resultados Linux e a monografia anterior
conservaram seus bytes. Word foi reaberto: 29 tabelas e 21 imagens. O PDF tem
78 páginas, sem páginas vazias; capítulos e resultados principais foram
conferidos no texto. Os gráficos principais foram inspecionados visualmente.

## Limitações e pendências Linux

O Mac disponível tem apenas Command Line Tools; `xcrun xctrace` falhou e a
saída foi arquivada. Não há contadores medidos de cache ou DRAM, identificação
P/E por worker, frequência/temperatura fixadas, detector de races ou medição
de energia. As duas sessões começaram na bateria e no mesmo dia/host; novas
observações não equivalem a máquinas ou sessões estatisticamente independentes.

Os perfis são de versões instrumentadas. Tempos de espera incluem
desbalanceamento, agendamento e sincronização; não medem um custo puro de
barreira. As contagens de pares de Covariance são efetivamente medidas.
Pressão de memória no Dot/Jacobi e localidade em GEMM permanecem hipóteses
estruturais sem contadores físicos. Os poucos custos/perfis auxiliares não
possuem os ICs da matriz principal. As médias de arrependimento entre casos
pesam igualmente programas de durações diferentes.

No Linux, executar `scripts/profile_linux_followup.sh` em diretório novo para
ciclos, instruções, eventos genéricos de cache, trocas de contexto e migrações.
Consultar `perf list` e as permissões antes de uma campanha separada de
controladores de memória; eventos genéricos de cache não dão banda DRAM.
Repetir os perfis auxiliares no Linux, idealmente em sessões/dias distintos e
com condições de energia registradas. Nada desse roteiro foi declarado executado.

O PDF é uma exportação de conteúdo por ReportLab. Conferência nativa do Word,
sumário, paginação, capa e exigências institucionais ainda requerem o aplicativo
e os dados acadêmicos de entrega. A versão anterior de 70 páginas permanece
intacta; esta entrega não substitui a aprovação do orientador ou da banca.

## Estado pela numeração original

1. Pipeline: seis promoções reais e revalidadas no ensaio de custo, com origens
   determinísticas ou LLM identificadas.
2. Validação: 129 testes, regressões, hashes e saídas numéricas verificados.
3. Recorte: preservado; os kernels manuais continuam identificados como manuais.
4. Agentes: três inferências reais adicionais de admissão; mesmo resultado
   admitido e custo maior. O resultado negativo heldout anterior foi preservado.
5. Experimentos: duas sessões M5 compatíveis com Linux, avaliação posterior do
   Selector, perfis auxiliares e custo concluídos no ambiente disponível.
6. Monografia: nova versão Markdown/Word/PDF com 78 páginas; acabamento
   institucional e contadores Linux permanecem com limites explícitos.

Os commits locais separam infraestrutura, arquivos experimentais e material
acadêmico. Sua identificação pode ser consultada com `git log -3 --oneline`
na branch de execução. Não foi configurado envio automático ao GitHub.
