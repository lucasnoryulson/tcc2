# Avaliação multiplataforma — campanha de quinze medições

Campanha: `results/multiplatform/linux_xeon_2026-11-05_p15w3`. Estado COMPLETE; 60 configurações, 900 amostras, 180 aquecimentos e 60 validações.

As amostras anteriores e os históricos não foram combinados com esta campanha. Não houve inferência LLM.

## Recomendação por entrada e variante

| Caso | Entrada | Variante | Recomendação | Tp (s) | S total | S paralelo | E paralela |
|---|---|---|---:|---:|---:|---:|---:|
| dot-auto | 1024 | automatic | sequencial | 8.78806e-07 | 1 | — | — |
| dot-auto | 10000000 | automatic | 2T | 0.00864162 | 1.25361 | 1.27581 | 0.637905 |
| dot | 1000000 | manual | sequencial | 0.0013915 | 1 | — | — |
| dot | 10000000 | manual | 2T | 0.0107116 | 1.04356 | 1.23881 | 0.619404 |
| gemm | LARGE | manual | 4T | 0.221314 | 2.84511 | 2.85401 | 0.713502 |
| gemm | MEDIUM | manual | 4T | 0.000967 | 3.81489 | 3.97828 | 0.994571 |
| nussinov | LARGE | manual | 4T | 5.44933 | 3.19496 | 3.20409 | 0.801022 |
| nussinov | LARGE | simd_auto | 4T | 5.88327 | 2.95931 | 3.09117 | 0.772792 |
| nussinov | LARGE | simd_manual | 4T | 5.85374 | 2.97424 | 3.1101 | 0.777524 |
| nussinov | MEDIUM | manual | 4T | 0.007798 | 2.70441 | 3.47794 | 0.869486 |
| nussinov | MEDIUM | simd_auto | 4T | 0.005443 | 3.87452 | 3.41191 | 0.852976 |
| nussinov | MEDIUM | simd_manual | 4T | 0.005448 | 3.87096 | 3.41153 | 0.852882 |
| jacobi-2d | LARGE | manual | 2T | 2.19022 | 1.17673 | 1.18168 | 0.590838 |
| jacobi-2d | MEDIUM | manual | 4T | 0.00283 | 3.60813 | 3.65265 | 0.913163 |
| covariance | LARGE | manual | 4T | 5.60143 | 2.19285 | 2.18317 | 0.545792 |
| covariance | MEDIUM | manual | 4T | 0.004922 | 2.17148 | 2.26249 | 0.565624 |

S total=Tseq/Tp; S paralelo=T1/Tp; E paralela=(T1/Tp)/p. O CSV também contém Tseq/T1 e ICs das razões.

## Menor mediana e política de quase empate

| Caso / entrada / variante | Menor mediana OpenMP | Recomendação | Estado |
|---|---:|---:|---|
| dot-auto / 1024 / automatic | 1T; 1.75612e-06 s | sequencial | NO_BENEFICIAL_CONFIGURATION |
| dot-auto / 10000000 / automatic | 4T; 0.00863066 s | 2T | SELECTED |
| dot / 1000000 / manual | 2T; 0.00285288 s | sequencial | NO_BENEFICIAL_CONFIGURATION |
| dot / 10000000 / manual | 4T; 0.0105092 s | 2T | SELECTED |
| gemm / LARGE / manual | 4T; 0.221314 s | 4T | SELECTED |
| gemm / MEDIUM / manual | 4T; 0.000967 s | 4T | SELECTED |
| nussinov / LARGE / manual | 4T; 5.44933 s | 4T | SELECTED |
| nussinov / LARGE / simd_auto | 4T; 5.88327 s | 4T | SELECTED |
| nussinov / LARGE / simd_manual | 4T; 5.85374 s | 4T | SELECTED |
| nussinov / MEDIUM / manual | 4T; 0.007798 s | 4T | SELECTED |
| nussinov / MEDIUM / simd_auto | 4T; 0.005443 s | 4T | SELECTED |
| nussinov / MEDIUM / simd_manual | 4T; 0.005448 s | 4T | SELECTED |
| jacobi-2d / LARGE / manual | 2T; 2.19022 s | 2T | SELECTED |
| jacobi-2d / MEDIUM / manual | 4T; 0.00283 s | 4T | SELECTED |
| covariance / LARGE / manual | 4T; 5.60143 s | 4T | SELECTED |
| covariance / MEDIUM / manual | 4T; 0.004922 s | 4T | SELECTED |

A coluna de menor mediana considera somente OpenMP; ela não implica ganho contra o sequencial. A recomendação aplica o Selector real, com quase empate de 2%. Seleção analítica não promove código.

## Estatística por configuração

| Caso | Entrada | Variante | Threads | Mediana (s) | Média (s) | DP amostral | MAD | IQR | IC95% mediana |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| covariance | LARGE | manual | 1 | 12.2289 | 12.293 | 0.161408 | 0.022361 | 0.0397845 | [12.2184; 12.2397] |
| covariance | LARGE | manual | 2 | 9.54098 | 9.56354 | 0.08085 | 0.021323 | 0.037445 | [9.51813; 9.55616] |
| covariance | LARGE | manual | 4 | 5.60143 | 5.67337 | 0.146881 | 0.042544 | 0.198816 | [5.56363; 5.82276] |
| covariance | LARGE | sequential | 1 | 12.2831 | 12.3362 | 0.18455 | 0.088215 | 0.190914 | [12.2103; 12.2993] |
| covariance | MEDIUM | manual | 1 | 0.011136 | 0.0109957 | 0.000496333 | 0.000351 | 0.0005925 | [0.010637; 0.011264] |
| covariance | MEDIUM | manual | 2 | 0.008204 | 0.00816013 | 0.000217397 | 0.000163 | 0.000353 | [0.008004; 0.008349] |
| covariance | MEDIUM | manual | 4 | 0.004922 | 0.00530493 | 0.000692634 | 0.000167 | 0.000897 | [0.004795; 0.005842] |
| covariance | MEDIUM | sequential | 1 | 0.010688 | 0.0107213 | 0.000357274 | 0.000352 | 0.0006895 | [0.0104196; 0.011059] |
| dot | 1000000 | manual | 1 | 0.00301228 | 0.00339249 | 0.000796518 | 0.000270568 | 0.00081843 | [0.00283054; 0.0036807] |
| dot | 1000000 | manual | 2 | 0.00285288 | 0.00283523 | 0.000109685 | 9.5417e-05 | 0.00015739 | [0.00273685; 0.00290019] |
| dot | 1000000 | manual | 4 | 0.0029303 | 0.00298217 | 0.000269406 | 0.00010517 | 0.000204205 | [0.00281026; 0.00302246] |
| dot | 1000000 | sequential | 1 | 0.0013915 | 0.00139023 | 8.66732e-05 | 6.1872e-05 | 0.000121807 | [0.00132963; 0.00144104] |
| dot | 10000000 | manual | 1 | 0.0132696 | 0.0136226 | 0.00109187 | 0.000144212 | 0.000351319 | [0.0131693; 0.0135938] |
| dot | 10000000 | manual | 2 | 0.0107116 | 0.010951 | 0.000765027 | 0.000352666 | 0.000782626 | [0.0103754; 0.011165] |
| dot | 10000000 | manual | 4 | 0.0105092 | 0.0106484 | 0.000548793 | 0.000256853 | 0.000507163 | [0.0102961; 0.010766] |
| dot | 10000000 | sequential | 1 | 0.0111782 | 0.0112148 | 0.000469178 | 0.000185242 | 0.000322019 | [0.0109516; 0.0112783] |
| dot-auto | 1024 | automatic | 1 | 1.75612e-06 | 1.80964e-06 | 1.31163e-07 | 1.1947e-08 | 2.26755e-08 | [1.74573e-06; 1.76807e-06] |
| dot-auto | 1024 | automatic | 2 | 1.98409e-06 | 1.99044e-06 | 5.81927e-08 | 1.7798e-08 | 3.32225e-08 | [1.95644e-06; 1.98955e-06] |
| dot-auto | 1024 | automatic | 4 | 2.05313e-06 | 2.06898e-06 | 8.8235e-08 | 7.3032e-08 | 1.53539e-07 | [1.99044e-06; 2.15084e-06] |
| dot-auto | 1024 | sequential | 1 | 8.78806e-07 | 8.93638e-07 | 4.19238e-08 | 1.1689e-08 | 2.6511e-08 | [8.67117e-07; 8.82162e-07] |
| dot-auto | 10000000 | automatic | 1 | 0.0110251 | 0.011269 | 0.000533402 | 0.000206411 | 0.000644013 | [0.0109067; 0.0116732] |
| dot-auto | 10000000 | automatic | 2 | 0.00864162 | 0.0087187 | 0.000648743 | 0.000234929 | 0.000383386 | [0.00833375; 0.00872385] |
| dot-auto | 10000000 | automatic | 4 | 0.00863066 | 0.0092382 | 0.00184273 | 0.000291435 | 0.000563715 | [0.00821132; 0.0088133] |
| dot-auto | 10000000 | sequential | 1 | 0.0108333 | 0.0113144 | 0.000962499 | 0.000207091 | 0.000786601 | [0.0107685; 0.0116972] |
| gemm | LARGE | manual | 1 | 0.631632 | 0.632576 | 0.0118375 | 0.00581 | 0.0122585 | [0.628924; 0.637442] |
| gemm | LARGE | manual | 2 | 0.346942 | 0.345496 | 0.013099 | 0.009322 | 0.0176575 | [0.336214; 0.355923] |
| gemm | LARGE | manual | 4 | 0.221314 | 0.230508 | 0.048322 | 0.012207 | 0.0214125 | [0.207238; 0.227423] |
| gemm | LARGE | sequential | 1 | 0.629662 | 0.632965 | 0.0129525 | 0.009837 | 0.01914 | [0.621976; 0.640672] |
| gemm | MEDIUM | manual | 1 | 0.003847 | 0.00398253 | 0.00030265 | 0.000211 | 0.0005485 | [0.003739; 0.004288] |
| gemm | MEDIUM | manual | 2 | 0.001909 | 0.00195373 | 0.000110937 | 3.2e-05 | 7e-05 | [0.001877; 0.001925] |
| gemm | MEDIUM | manual | 4 | 0.000967 | 0.00102793 | 0.000163471 | 5e-06 | 2.75e-05 | [0.000962975; 0.00097] |
| gemm | MEDIUM | sequential | 1 | 0.003689 | 0.00388187 | 0.000328232 | 9.2e-05 | 0.000652 | [0.003643; 0.004299] |
| jacobi-2d | LARGE | manual | 1 | 2.58814 | 2.61916 | 0.0966973 | 0.015952 | 0.0457775 | [2.57219; 2.64796] |
| jacobi-2d | LARGE | manual | 2 | 2.19022 | 2.212 | 0.06043 | 0.012764 | 0.028034 | [2.18221; 2.21471] |
| jacobi-2d | LARGE | manual | 4 | 2.37098 | 2.40663 | 0.149923 | 0.04164 | 0.069916 | [2.36284; 2.41262] |
| jacobi-2d | LARGE | sequential | 1 | 2.5773 | 2.59312 | 0.0453023 | 0.017179 | 0.038788 | [2.57147; 2.59448] |
| jacobi-2d | MEDIUM | manual | 1 | 0.010337 | 0.0105042 | 0.000354868 | 9.3e-05 | 0.0003205 | [0.010312; 0.01052] |
| jacobi-2d | MEDIUM | manual | 2 | 0.005255 | 0.0053012 | 0.00026215 | 0.000182 | 0.0002975 | [0.005146; 0.005443] |
| jacobi-2d | MEDIUM | manual | 4 | 0.00283 | 0.00292533 | 0.000279518 | 7.6e-05 | 0.000181 | [0.002796; 0.00294282] |
| jacobi-2d | MEDIUM | sequential | 1 | 0.010211 | 0.0102355 | 0.000219025 | 0.000132 | 0.000237 | [0.010052; 0.010272] |
| nussinov | LARGE | manual | 1 | 17.4601 | 17.6231 | 0.612077 | 0.071415 | 0.121215 | [17.3887; 17.5139] |
| nussinov | LARGE | manual | 2 | 8.79064 | 8.87825 | 0.218783 | 0.071318 | 0.190383 | [8.73717; 9.00016] |
| nussinov | LARGE | manual | 4 | 5.44933 | 5.8737 | 1.43734 | 0.269731 | 0.490884 | [5.1796; 5.60436] |
| nussinov | LARGE | sequential | 1 | 17.4104 | 17.5111 | 0.278429 | 0.075658 | 0.149701 | [17.3605; 17.5244] |
| nussinov | LARGE | simd_auto | 1 | 18.1862 | 18.2937 | 0.28277 | 0.029666 | 0.05215 | [18.1555; 18.2147] |
| nussinov | LARGE | simd_auto | 2 | 9.24518 | 9.39226 | 0.356574 | 0.069573 | 0.251325 | [9.19085; 9.51043] |
| nussinov | LARGE | simd_auto | 4 | 5.88327 | 6.71126 | 2.84476 | 0.525235 | 1.09797 | [5.44457; 6.63493] |
| nussinov | LARGE | simd_manual | 1 | 18.2057 | 18.2265 | 0.224329 | 0.048193 | 0.0978135 | [18.1589; 18.2706] |
| nussinov | LARGE | simd_manual | 2 | 9.18428 | 9.20591 | 0.128136 | 0.03473 | 0.075397 | [9.14955; 9.2494] |
| nussinov | LARGE | simd_manual | 4 | 5.85374 | 6.5639 | 1.7911 | 0.238114 | 0.463529 | [5.70712; 6.13578] |
| nussinov | MEDIUM | manual | 1 | 0.027121 | 0.0274527 | 0.000932816 | 0.000121 | 0.000353 | [0.02708; 0.027254] |
| nussinov | MEDIUM | manual | 2 | 0.014095 | 0.0140974 | 0.000396013 | 0.000207 | 0.0002755 | [0.013888; 0.014161] |
| nussinov | MEDIUM | manual | 4 | 0.007798 | 0.0082452 | 0.000774328 | 0.000358 | 0.0013715 | [0.007581; 0.008801] |
| nussinov | MEDIUM | sequential | 1 | 0.021089 | 0.021509 | 0.00102597 | 0.000292 | 0.0006485 | [0.020939; 0.021381] |
| nussinov | MEDIUM | simd_auto | 1 | 0.018571 | 0.0185732 | 0.000252593 | 0.000239 | 0.0004315 | [0.018322; 0.018792] |
| nussinov | MEDIUM | simd_auto | 2 | 0.009612 | 0.0097112 | 0.000443199 | 6.8e-05 | 0.0001265 | [0.009518; 0.00968] |
| nussinov | MEDIUM | simd_auto | 4 | 0.005443 | 0.0065368 | 0.00268112 | 0.000195 | 0.000855 | [0.005426; 0.005781] |
| nussinov | MEDIUM | simd_manual | 1 | 0.018586 | 0.0196107 | 0.00335589 | 0.00012 | 0.0003325 | [0.018495; 0.018755] |
| nussinov | MEDIUM | simd_manual | 2 | 0.009673 | 0.00970587 | 0.000125952 | 9.6e-05 | 0.0002025 | [0.009602; 0.009815] |
| nussinov | MEDIUM | simd_manual | 4 | 0.005448 | 0.0060956 | 0.00141549 | 0.000191 | 0.0006955 | [0.005276; 0.006132] |

DP amostral usa n−1; MAD não é escalado; quartis usam interpolação linear inclusiva. ICs: bootstrap percentil pareado por blocos, 5.000 réplicas, seed 2026, 95%, somente com n≥15.

Esses ICs são condicionais aos blocos medidos. Não demonstram independência temporal, causalidade de arquitetura ou significância entre plataformas. Nenhum outlier foi removido.

## Artefatos e execução no M5

Fontes e entradas, logs e amostras estão no diretório da campanha. O diretório de análise contém `measurements.csv`, `selection.json`, `statistics_method.json`, `verification.json` e as figuras em PNG/SVG/PDF.

Usar `scripts/run_multiplatform_mac.sh` com um diretório novo e analisar as saídas com `scripts/analyze_scaling.py`. A comparação direta é feita com `scripts/compare_multiplatform.py`, que exige compatibilidade e mantém curvas distintas.

A coleta equivalente M5 está pendente. Não há novas medições Mac neste relatório. Os números históricos permanecem contextuais, com suas lacunas de proveniência.

## Limites

Máquina sem isolamento exclusivo ou frequência/temperatura fixadas. Não houve detector de races, contadores de hardware, medição de energia ou banda física. As variantes manuais e adaptações específicas não são ganhos da LLM.

