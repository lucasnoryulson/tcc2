# Repetibilidade entre sessões Linux

3 coletas separadas; 38 configurações comuns. Cada mediana conserva as quinze observações da sua própria sessão.

Não se agrupam amostras nem se estima um IC populacional com apenas estas sessões. O CV abaixo descreve as medianas observadas; não identifica uma causa para sua mudança.

| Caso / entrada / variante / threads | Medianas por sessão (s) | Máximo/mínimo | CV das medianas |
|---|---|---:|---:|
| covariance / MEDIUM / manual / 1 | 0.011136; 0.010568; 0.010606 | 1.0537 | 0.0295 |
| covariance / MEDIUM / manual / 2 | 0.008204; 0.008175; 0.008118 | 1.0106 | 0.0054 |
| covariance / MEDIUM / manual / 4 | 0.004922; 0.004817; 0.004799 | 1.0256 | 0.0137 |
| covariance / MEDIUM / sequential / 1 | 0.010688; 0.010584; 0.010514 | 1.0165 | 0.0083 |
| dot / 1000000 / manual / 1 | 0.00301228; 0.003028; 0.00329952 | 1.0954 | 0.0519 |
| dot / 1000000 / manual / 2 | 0.00285288; 0.00293135; 0.00297695 | 1.0435 | 0.0215 |
| dot / 1000000 / manual / 4 | 0.0029303; 0.00310884; 0.00324862 | 1.1086 | 0.0515 |
| dot / 1000000 / sequential / 1 | 0.0013915; 0.00146009; 0.00139308 | 1.0493 | 0.0277 |
| dot / 10000000 / manual / 1 | 0.0132696; 0.0129316; 0.0132292 | 1.0261 | 0.0140 |
| dot / 10000000 / manual / 2 | 0.0107116; 0.0108316; 0.0107106 | 1.0113 | 0.0065 |
| dot / 10000000 / manual / 4 | 0.0105092; 0.0104283; 0.0105432 | 1.0110 | 0.0056 |
| dot / 10000000 / sequential / 1 | 0.0111782; 0.0113138; 0.011177 | 1.0122 | 0.0070 |
| dot-auto / 10000000 / automatic / 1 | 0.0110251; 0.0112542; 0.0112058 | 1.0208 | 0.0108 |
| dot-auto / 10000000 / automatic / 2 | 0.00864162; 0.00874699; 0.00874206 | 1.0122 | 0.0068 |
| dot-auto / 10000000 / automatic / 4 | 0.00863066; 0.00874064; 0.0094186 | 1.0913 | 0.0478 |
| dot-auto / 10000000 / sequential / 1 | 0.0108333; 0.0109555; 0.0108663 | 1.0113 | 0.0058 |
| dot-auto / 1024 / automatic / 1 | 1.75612e-06; 1.77456e-06; 1.76692e-06 | 1.0105 | 0.0052 |
| dot-auto / 1024 / automatic / 2 | 1.98409e-06; 1.98408e-06; 1.97848e-06 | 1.0028 | 0.0016 |
| dot-auto / 1024 / automatic / 4 | 2.05313e-06; 2.22568e-06; 2.22184e-06 | 1.0840 | 0.0455 |
| dot-auto / 1024 / sequential / 1 | 8.78806e-07; 8.94594e-07; 8.91946e-07 | 1.0180 | 0.0095 |
| gemm / MEDIUM / manual / 1 | 0.003847; 0.003859; 0.004302 | 1.1183 | 0.0648 |
| gemm / MEDIUM / manual / 2 | 0.001909; 0.001976; 0.00215 | 1.1262 | 0.0618 |
| gemm / MEDIUM / manual / 4 | 0.000967; 0.001026; 0.001054 | 1.0900 | 0.0437 |
| gemm / MEDIUM / sequential / 1 | 0.003689; 0.003992; 0.004286 | 1.1618 | 0.0748 |
| jacobi-2d / MEDIUM / manual / 1 | 0.010337; 0.010296; 0.01072 | 1.0412 | 0.0224 |
| jacobi-2d / MEDIUM / manual / 2 | 0.005255; 0.005279; 0.005586 | 1.0630 | 0.0343 |
| jacobi-2d / MEDIUM / manual / 4 | 0.00283; 0.002884; 0.003018 | 1.0664 | 0.0333 |
| jacobi-2d / MEDIUM / sequential / 1 | 0.010211; 0.010225; 0.010381 | 1.0166 | 0.0092 |
| nussinov / MEDIUM / manual / 1 | 0.027121; 0.027286; 0.027254 | 1.0061 | 0.0032 |
| nussinov / MEDIUM / manual / 2 | 0.014095; 0.014125; 0.013983 | 1.0102 | 0.0053 |
| nussinov / MEDIUM / manual / 4 | 0.007798; 0.008027; 0.008697 | 1.1153 | 0.0572 |
| nussinov / MEDIUM / sequential / 1 | 0.021089; 0.021006; 0.020954 | 1.0064 | 0.0032 |
| nussinov / MEDIUM / simd_auto / 1 | 0.018571; 0.018531; 0.018449 | 1.0066 | 0.0034 |
| nussinov / MEDIUM / simd_auto / 2 | 0.009612; 0.009666; 0.009653 | 1.0056 | 0.0029 |
| nussinov / MEDIUM / simd_auto / 4 | 0.005443; 0.005561; 0.005314 | 1.0465 | 0.0227 |
| nussinov / MEDIUM / simd_manual / 1 | 0.018586; 0.018473; 0.018449 | 1.0074 | 0.0040 |
| nussinov / MEDIUM / simd_manual / 2 | 0.009673; 0.009749; 0.009635 | 1.0118 | 0.0060 |
| nussinov / MEDIUM / simd_manual / 4 | 0.005448; 0.005473; 0.005537 | 1.0163 | 0.0084 |

As recomendações de cada sessão estão em session_selections.csv. As curvas do M5 permanecem pendentes. Sessões do mesmo dia/host não são máquinas independentes e não tornam frequência ou temperatura controladas.
