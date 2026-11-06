# Conformidade diagnóstica offline

Estado: **COMPLETE_WITH_FAILURES**.

Vistas de evidências reais e falhas controladas; não são 24 programas independentes.
Rótulos autorais por rubrica, sem revisão humana independente. O baseline implementa
a mesma rubrica; sua concordância perfeita verifica consistência, não validação externa.
Timeout é terminal: chamadas restantes ficam NOT_RUN. Todos os slots planejados ficam
no denominador das taxas. Latência usa somente slots efetivamente tentados.

| Partição | Braço | Planejados/tentados | JSON válido | Causa | Ação | Perigosas | Claims sem suporte/total | Latência mediana (s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| heldout | coordinator | 12/12 | 91.7% | 8.3% | 0.0% | 0.0% | 42/46 | 41.535894 |
| heldout | coordinator_without_analysis | 12/12 | 100.0% | 8.3% | 0.0% | 0.0% | 48/52 | 39.746700 |
| heldout | rules | 12/12 | 100.0% | 100.0% | 100.0% | 0.0% | 0/12 | 0.000139 |

Suporte de claims é igualdade exata de triplas citadas, não julgamento semântico humano.
Ausência de claims não demonstra fundamentação. Consulte claims_present_rate e supported_claim_response_rate.
A ablação só muda os casos com análise disponível; o JSON contém também esse subconjunto.
Repetições reutilizam os mesmos casos; não são novas amostras de programas.
Nenhuma ação desta avaliação executa reparo, promove candidato ou mede ganho de kernel.
