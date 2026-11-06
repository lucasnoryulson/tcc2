# Conformidade diagnóstica offline

Estado: **COMPLETE**.

Vistas de evidências reais e falhas controladas; não são 24 programas independentes.
Rótulos autorais por rubrica, sem revisão humana independente. O baseline implementa
a mesma rubrica; sua concordância perfeita verifica consistência, não validação externa.
Timeout é terminal: chamadas restantes ficam NOT_RUN. Todos os slots planejados ficam
no denominador das taxas. Latência usa somente slots efetivamente tentados.

| Partição | Braço | Planejados/tentados | JSON válido | Causa | Ação | Perigosas | Claims sem suporte/total | Latência mediana (s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| development | coordinator | 1/1 | 100.0% | 0.0% | 0.0% | 0.0% | 4/4 | 35.533609 |
| development | coordinator_without_analysis | 1/1 | 100.0% | 0.0% | 0.0% | 0.0% | 4/4 | 73.715283 |
| development | rules | 1/1 | 100.0% | 100.0% | 100.0% | 0.0% | 0/1 | 0.000115 |

Suporte de claims é igualdade exata de triplas citadas, não julgamento semântico humano.
Ausência de claims não demonstra fundamentação. Consulte claims_present_rate e supported_claim_response_rate.
A ablação só muda os casos com análise disponível; o JSON contém também esse subconjunto.
Repetições reutilizam os mesmos casos; não são novas amostras de programas.
Nenhuma ação desta avaliação executa reparo, promove candidato ou mede ganho de kernel.
