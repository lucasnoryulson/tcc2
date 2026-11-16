# AXPY: campanha final com todas as equipes — 16/11/2026



## Protocolo e integridade



Protocolo fixado em `62f84f0`, sobre branch derivada da main `601b813`. As duas sessões usam os fixtures existentes, três tamanhos, sequencial e OpenMP 1–10T. São 33 configurações por sessão, quinze medições e três aquecimentos: 990 medições e 198 aquecimentos. O intervalo entre sessões foi 118.834 s. A escolha foi congelada por SHA-256 antes da S2. Os 66 pares configuração–sessão passaram pela corretude integral dos vetores. Os prefixos terminam PREPARED porque a coleta termina antes da LLM; a campanha científica COMPLETE é sustentada pelo protocolo, duas sessões, amostras e análise, não pelo status isolado do runner.



## Resultados e estabilidade



| N | Configuração congelada S1 | Mediana S1 (µs) | Média S1 (µs) | DP S1 (µs) | S total S1 [IC95%] | E paralela S1 |
|---|---:|---:|---:|---:|---:|---:|
| 1,024 | seq. | 0,3082 | 0,3169 | 0,1210 | 1,000 [1,000; 1,000] | — |
| 1,000,000 | 6T | 837,1400 | 1137,4353 | 826,0358 | 1,367 [1,124; 1,471] | 0,251 |
| 10,000,000 | 4T | 8180,2500 | 8734,2317 | 1086,0006 | 1,594 [1,231; 1,878] | 0,406 |



| N | Escolha S1 | Escolha S2 | S total da escolha congelada na S2 | Excesso sobre melhor S2 | Inadequada (>2%) |
|---|---:|---:|---:|---:|---|
| 1,024 | seq. | seq. | 1,000 | 0,000% | Não |
| 1,000,000 | 6T | 4T | 1,394 | 2,088% | Sim |
| 10,000,000 | 4T | 4T | 1,716 | 0,000% | Não |



A escolha mudou em um dos três tamanhos. A recomendação congelada de 6T para um milhão de elementos ficou 2,088% acima da menor mediana posterior (10T), cruzando ligeiramente o limite operacional de 2%. A recomendação da própria S2 foi 4T por quase empate; ela não foi usada para corrigir a escolha congelada. Inadequação operacional não significa erro de corretude nem diferença estatisticamente confirmada. Os IC95% são bootstrap percentil pareado de 5.000 rodadas, condicionais à sessão. Nenhum tempo foi excluído como outlier.



![AXPY N=1024, OpenMP 1–10T: ganhos e IC95% condicionais por sessão](../monografia/figures_banca_2026-11-16/axpy_all_threads_1024.png)

![AXPY N=1000000, OpenMP 1–10T: ganhos e IC95% condicionais por sessão](../monografia/figures_banca_2026-11-16/axpy_all_threads_1000000.png)

![AXPY N=10000000, OpenMP 1–10T: ganhos e IC95% condicionais por sessão](../monografia/figures_banca_2026-11-16/axpy_all_threads_10000000.png)



## Comparação contextual, sem agregar campanhas



| Campanha / N=10 milhões | Threads medidas | Medições por configuração | Tseq S1 (ms) | Escolha S1; Tp (ms) | Ganho total S1 |
|---|---|---:|---:|---:|---:|
| Seis equipes, anterior | 1/2/4/6/8/10 | 15 | 9,785 | 10T; 7,808 | 1,253 |
| Todas as equipes, atual | 1/2/3/4/5/6/7/8/9/10 | 15 | 13,038 | 4T; 8,180 | 1,594 |



O candidato gerado conserva SHA-256 `4877d57708a392900b11ca3e6cc90e3e1e4c2497ef5c2e58460268cdfc94d1d1`. O ganho maior da campanha atual não é uma otimização nova: o baseline sequencial ficou mais lento, o conjunto de threads mudou e as condições de sessão não foram isoladas. O histórico de 03/11 usa outro contrato; a execução de 105 medições foi apenas validação técnica. Nenhum desses tempos foi usado para completar as 990 observações.



## Custos reais e amortização



| Braço | Tentativas | Promoções | Decisão + validação mediana (s) | Promoção mediana (s) | Total contabilizado mediano (s) | Equilíbrio mediano na S2 (chamadas) |
|---|---:|---:|---:|---:|---:|---:|
| deterministic | 3/3 | 3 | 0,000024 | 0,931 | 110,593 | 17966 |
| coordinator | 3/3 | 3 | 59,041822 | 1,721 | 170,709 | 27731 |



Os braços reutilizam um único prefixo determinístico S1 de N=10 milhões. Há três novas decisões por braço; não são três novas medições do prefixo ou seis pipelines independentes. A promoção recompila e revalida; o mesmo candidato e a configuração 4T são impostos pelos gates. A amortização da tabela usa as latências da S2 e custo total por tentativa antes de resumir. Decisão isolada, preparo e promoção estão discriminados nos CSVs. Reuso, entrada, economia positiva e condições equivalentes são hipóteses do cálculo, não uma promessa de economia futura. O custo real da LLM não foi substituído pela latência histórica. Tempos de kernel somados foram reconstruídos multiplicando cada média por seu número fixo de chamadas internas; há arredondamento de até a resolução de impressão do driver. O custo de parede inclui inicialização e validação, e não deve ser confundido com esse somatório.



## Condições e limites



Apple M5, 10 núcleos (4 P/6 E), 16 GiB, macOS 26.6.2, LLVM Homebrew 23.1.1. O probe confirmou todos os tamanhos de equipe, não sua alocação P/E. Energia externa e bateria 3–4%, indicada como carregando; sem controle térmico, de frequência ou exclusividade do host. A inferência ocorreu depois das duas sessões, sem concorrência com benchmarks ou testes. Nenhum contador perf Linux foi coletado no macOS. Uma fonte e três tamanhos não estimam generalização entre programas ou máquinas; duas sessões no mesmo dia não são independência populacional.

