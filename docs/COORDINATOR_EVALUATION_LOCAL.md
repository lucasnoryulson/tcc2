# Item 4 — evidências locais de 3 de novembro de 2026

**Estado: avaliação LLM incompleta.** A infraestrutura e o baseline foram
executados; as inferências reais não terminaram no limite diagnóstico adotado.
Este registro não demonstra benefício ou ausência de benefício do Coordinator.

## Ambiente e protocolo

Linux x86_64, Intel Xeon E3-1225 V2 @ 3,20 GHz, quatro núcleos/threads lógicas,
GCC 13.3.0 e Python 3.12.3. Flags `-O3` para sequencial e `-O3 -fopenmp` para o
candidato. Threads 1 e 2; `OMP_DYNAMIC=FALSE`, `OMP_PROC_BIND=TRUE`, `OMP_PLACES=cores`.
As fontes e o compilador têm hashes nos relatórios originais.

Foram executados os gates reais, com cinco amostras de desempenho por configuração.
O baseline abaixo foi coletado depois de terminarem os testes, antes da rodada
LLM. Uma coleta preliminar concorrente com testes foi descartada desta análise.
Três repetições da decisão determinística reutilizam as mesmas medições.

| Caso | Mediana seq. (s) | OpenMP 1 thread (s) | OpenMP 2 threads (s) | Decisão determinística |
|---|---:|---:|---:|---|
| Dot Product N=10.000.000 | 0,010607341 | 0,010978541 | 0,008904885 | Admite 2 threads |
| Dot Product N=1.024 | 0,000001183 | 0,000001600 | 0,000001592 | Mantém sequencial |

No caso grande, o ganho contra o sequencial foi **1,191×**, enquanto a
escalabilidade contra OpenMP com uma thread foi aproximadamente **1,233×**.
No pequeno, o candidato paralelo foi mais lento que o sequencial e não foi
admitido. Esses resultados descrevem esta coleta local, sem extrapolação ao Mac.

## Inferências reais

Modelo instalado `qwen2.5:3b`, ID curto `357c53fb659c`, tamanho indicado pelo
Ollama de 1,9 GB. Uma repetição por caso, dois modos LLM, temperatura zero,
limite diagnóstico de **30 segundos por chamada**. Os quatro pedidos reais
expiraram; não houve decisão LLM válida para comparar. Falhas ficaram no
denominador e a campanha terminou com `INCOMPLETE`, saída 1.

Este limite foi usado para verificar integração e registro de falhas. Não é
um limite de desempenho justificado para a campanha final. Também já haviam
ocorrido timeouts de 120 e 300 segundos nas validações anteriores do Coordinator.
Não interpretar os timeouts como erro semântico da LLM ou como demonstração de
que ela sempre discorda da política. A concordância observada zero inclui
ausência de resposta, conforme o protocolo; não representa quatro respostas erradas.

As evidências completas permanecem em:

- `build/validation/step4/final/evaluation-k3nql7bl/`: baseline, fontes, binários,
  relatórios, amostras e logs dos dois casos.
- `build/validation/step4/live/evaluation-c7s6idmh/`: prompts, resultados de cada
  tentativa e relatório da rodada real; `case_1` é a entrada grande e `case_2`, a pequena.

Cópias dos resumos JSON e Markdown estão em
[`results/coordinator_evaluation/local_2026-11-03/`](../results/coordinator_evaluation/local_2026-11-03/).
São registros históricos desta máquina; não substituem a pasta completa com os
artefatos referenciados. Os caminhos absolutos não são portáveis: gerar campanhas
novas ao trocar de máquina.

## O que falta para concluir o item 4

A validação técnica terminou com **57 testes unittest aprovados**, mais os sete
casos de regressão do Coordinator e os três do Performance Selector, e
`git diff --check` sem erros:

```bash
python3 -B -m unittest scripts.test_coordinator_evaluation \
  scripts.test_pipeline_integration scripts.test_candidate_promotion scripts.test_gate_contracts
python3 -B scripts/test_coordinator_v02_regression.py
python3 -B scripts/test_performance_selector_v02_regression.py
git diff --check
```

Os testes de respostas usam simulação explícita e verificam a infraestrutura,
incluindo recusas, configurações não medidas, troca de artefatos, timeouts,
ablação sem efeito e persistência de falhas. Não entram nos resultados LLM acima.

Executar o comando do [protocolo](COORDINATOR_EVALUATION.md) no Mac, conservar as
inferências concluídas e discutir concordância, recusas, falhas, tokens e latência.
Se os modos admitirem a mesma configuração, o ganho do kernel será o mesmo e a
contribuição observada do Coordinator deverá ser discutida como decisão/custo.
O experimento atual não permite alegar que a LLM gerou código melhor ou reduziu
uma busca por candidatos, pois essas ações não são executadas neste recorte.
