# Avaliação pareada do Coordinator

Estado: **BASELINE_ONLY**.

Mesmos candidatos e medições em todos os modos. Concordância é com a política de promoção,
não um julgamento independente de qualidade. Falhas permanecem no denominador.

| Caso | Modo | Válidas/total | Concordância | Aceitação | Decisão (s, mediana) | Speedup vs seq. |
|---|---|---:|---:|---:|---:|---:|
| dot_large | deterministic | 3/3 | 100% | 100% | 0.000022 | 1.191 |
| dot_small | deterministic | 3/3 | 100% | 0% | 0.000009 | 1.000 |

O speedup usa medições compartilhadas; uma recusa/falha retorna ao sequencial (1×).
O tempo contabilizado soma o prefixo real compartilhado ao custo de cada decisão/validação;
não é uma nova execução independente do pipeline. Não inclui publicação/revalidação final.
Há um candidato por caso e nenhuma recuperação automática por RETUNE/MODIFY nesta avaliação.
Repetições da LLM reutilizam evidências e não são novas amostras de desempenho do kernel.
Dois tamanhos de Dot Product não permitem generalização para outros padrões.

Comparações da LLM só podem ser discutidas após concluir as inferências reais.
