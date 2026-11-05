# Avaliação pareada do Coordinator

Estado: **COMPLETE**.

Mesmos candidatos e medições em todos os modos. Concordância é com a política de promoção,
não um julgamento independente de qualidade. Falhas permanecem no denominador.

| Caso | Modo | Válidas/total | Concordância | Aceitação | Decisão (s, mediana) | Speedup vs seq. |
|---|---|---:|---:|---:|---:|---:|
| case_1 | coordinator | 3/3 | 100% | 100% | 4.985423 | 1.673 |
| case_1 | coordinator_without_analysis | 3/3 | 100% | 100% | 5.138635 | 1.673 |
| case_1 | deterministic | 3/3 | 100% | 100% | 0.000015 | 1.673 |
| case_2 | coordinator | 3/3 | 100% | 0% | 3.545473 | 1.000 |
| case_2 | coordinator_without_analysis | 3/3 | 100% | 0% | 3.559586 | 1.000 |
| case_2 | deterministic | 3/3 | 100% | 0% | 0.000007 | 1.000 |

O speedup usa medições compartilhadas; uma recusa/falha retorna ao sequencial (1×).
O tempo contabilizado soma o prefixo real compartilhado ao custo de cada decisão/validação;
não é uma nova execução independente do pipeline. Não inclui publicação/revalidação final.
Há um candidato por caso e nenhuma recuperação automática por RETUNE/MODIFY nesta avaliação.
Repetições da LLM reutilizam evidências e não são novas amostras de desempenho do kernel.
Dois tamanhos de Dot Product não permitem generalização para outros padrões.

Comparações da LLM só podem ser discutidas após concluir as inferências reais.
