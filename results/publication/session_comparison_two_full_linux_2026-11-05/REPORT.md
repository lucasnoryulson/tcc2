# Repetibilidade entre sessões Linux

2 coletas separadas; 60 configurações comuns. Cada mediana conserva as quinze observações da sua própria sessão.

Não se agrupam amostras nem se estima um IC populacional com apenas estas sessões. O CV abaixo descreve as medianas observadas; não identifica uma causa para sua mudança.

| Caso / entrada / variante / threads | Medianas por sessão (s) | Máximo/mínimo | CV das medianas |
|---|---|---:|---:|
| covariance / LARGE / manual / 1 | 12.2289; 12.2772 | 1.0039 | 0.0028 |
| covariance / LARGE / manual / 2 | 9.54098; 9.56434 | 1.0024 | 0.0017 |
| covariance / LARGE / manual / 4 | 5.60143; 5.62276 | 1.0038 | 0.0027 |
| covariance / LARGE / sequential / 1 | 12.2831; 12.2169 | 1.0054 | 0.0038 |
| covariance / MEDIUM / manual / 1 | 0.011136; 0.010568 | 1.0537 | 0.0370 |
| covariance / MEDIUM / manual / 2 | 0.008204; 0.008175 | 1.0035 | 0.0025 |
| covariance / MEDIUM / manual / 4 | 0.004922; 0.004817 | 1.0218 | 0.0152 |
| covariance / MEDIUM / sequential / 1 | 0.010688; 0.010584 | 1.0098 | 0.0069 |
| dot / 1000000 / manual / 1 | 0.00301228; 0.003028 | 1.0052 | 0.0037 |
| dot / 1000000 / manual / 2 | 0.00285288; 0.00293135 | 1.0275 | 0.0192 |
| dot / 1000000 / manual / 4 | 0.0029303; 0.00310884 | 1.0609 | 0.0418 |
| dot / 1000000 / sequential / 1 | 0.0013915; 0.00146009 | 1.0493 | 0.0340 |
| dot / 10000000 / manual / 1 | 0.0132696; 0.0129316 | 1.0261 | 0.0182 |
| dot / 10000000 / manual / 2 | 0.0107116; 0.0108316 | 1.0112 | 0.0079 |
| dot / 10000000 / manual / 4 | 0.0105092; 0.0104283 | 1.0078 | 0.0055 |
| dot / 10000000 / sequential / 1 | 0.0111782; 0.0113138 | 1.0121 | 0.0085 |
| dot-auto / 10000000 / automatic / 1 | 0.0110251; 0.0112542 | 1.0208 | 0.0145 |
| dot-auto / 10000000 / automatic / 2 | 0.00864162; 0.00874699 | 1.0122 | 0.0086 |
| dot-auto / 10000000 / automatic / 4 | 0.00863066; 0.00874064 | 1.0127 | 0.0090 |
| dot-auto / 10000000 / sequential / 1 | 0.0108333; 0.0109555 | 1.0113 | 0.0079 |
| dot-auto / 1024 / automatic / 1 | 1.75612e-06; 1.77456e-06 | 1.0105 | 0.0074 |
| dot-auto / 1024 / automatic / 2 | 1.98409e-06; 1.98408e-06 | 1.0000 | 0.0000 |
| dot-auto / 1024 / automatic / 4 | 2.05313e-06; 2.22568e-06 | 1.0840 | 0.0570 |
| dot-auto / 1024 / sequential / 1 | 8.78806e-07; 8.94594e-07 | 1.0180 | 0.0126 |
| gemm / LARGE / manual / 1 | 0.631632; 0.66871 | 1.0587 | 0.0403 |
| gemm / LARGE / manual / 2 | 0.346942; 0.371781 | 1.0716 | 0.0489 |
| gemm / LARGE / manual / 4 | 0.221314; 0.235891 | 1.0659 | 0.0451 |
| gemm / LARGE / sequential / 1 | 0.629662; 0.680011 | 1.0800 | 0.0544 |
| gemm / MEDIUM / manual / 1 | 0.003847; 0.003859 | 1.0031 | 0.0022 |
| gemm / MEDIUM / manual / 2 | 0.001909; 0.001976 | 1.0351 | 0.0244 |
| gemm / MEDIUM / manual / 4 | 0.000967; 0.001026 | 1.0610 | 0.0419 |
| gemm / MEDIUM / sequential / 1 | 0.003689; 0.003992 | 1.0821 | 0.0558 |
| jacobi-2d / LARGE / manual / 1 | 2.58814; 2.58692 | 1.0005 | 0.0003 |
| jacobi-2d / LARGE / manual / 2 | 2.19022; 2.1946 | 1.0020 | 0.0014 |
| jacobi-2d / LARGE / manual / 4 | 2.37098; 2.41319 | 1.0178 | 0.0125 |
| jacobi-2d / LARGE / sequential / 1 | 2.5773; 2.58507 | 1.0030 | 0.0021 |
| jacobi-2d / MEDIUM / manual / 1 | 0.010337; 0.010296 | 1.0040 | 0.0028 |
| jacobi-2d / MEDIUM / manual / 2 | 0.005255; 0.005279 | 1.0046 | 0.0032 |
| jacobi-2d / MEDIUM / manual / 4 | 0.00283; 0.002884 | 1.0191 | 0.0134 |
| jacobi-2d / MEDIUM / sequential / 1 | 0.010211; 0.010225 | 1.0014 | 0.0010 |
| nussinov / LARGE / manual / 1 | 17.4601; 17.3237 | 1.0079 | 0.0055 |
| nussinov / LARGE / manual / 2 | 8.79064; 8.75981 | 1.0035 | 0.0025 |
| nussinov / LARGE / manual / 4 | 5.44933; 5.61433 | 1.0303 | 0.0211 |
| nussinov / LARGE / sequential / 1 | 17.4104; 17.3444 | 1.0038 | 0.0027 |
| nussinov / LARGE / simd_auto / 1 | 18.1862; 18.1486 | 1.0021 | 0.0015 |
| nussinov / LARGE / simd_auto / 2 | 9.24518; 9.18703 | 1.0063 | 0.0045 |
| nussinov / LARGE / simd_auto / 4 | 5.88327; 5.98038 | 1.0165 | 0.0116 |
| nussinov / LARGE / simd_manual / 1 | 18.2057; 18.1438 | 1.0034 | 0.0024 |
| nussinov / LARGE / simd_manual / 2 | 9.18428; 9.20583 | 1.0023 | 0.0017 |
| nussinov / LARGE / simd_manual / 4 | 5.85374; 5.87682 | 1.0039 | 0.0028 |
| nussinov / MEDIUM / manual / 1 | 0.027121; 0.027286 | 1.0061 | 0.0043 |
| nussinov / MEDIUM / manual / 2 | 0.014095; 0.014125 | 1.0021 | 0.0015 |
| nussinov / MEDIUM / manual / 4 | 0.007798; 0.008027 | 1.0294 | 0.0205 |
| nussinov / MEDIUM / sequential / 1 | 0.021089; 0.021006 | 1.0040 | 0.0028 |
| nussinov / MEDIUM / simd_auto / 1 | 0.018571; 0.018531 | 1.0022 | 0.0015 |
| nussinov / MEDIUM / simd_auto / 2 | 0.009612; 0.009666 | 1.0056 | 0.0040 |
| nussinov / MEDIUM / simd_auto / 4 | 0.005443; 0.005561 | 1.0217 | 0.0152 |
| nussinov / MEDIUM / simd_manual / 1 | 0.018586; 0.018473 | 1.0061 | 0.0043 |
| nussinov / MEDIUM / simd_manual / 2 | 0.009673; 0.009749 | 1.0079 | 0.0055 |
| nussinov / MEDIUM / simd_manual / 4 | 0.005448; 0.005473 | 1.0046 | 0.0032 |

As recomendações de cada sessão estão em session_selections.csv. As curvas do M5 permanecem pendentes. Sessões do mesmo dia/host não são máquinas independentes e não tornam frequência ou temperatura controladas.
