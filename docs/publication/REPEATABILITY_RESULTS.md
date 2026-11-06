# Repetibilidade Linux: resultados de sessões separadas

Esta análise descreve as comparações registradas pelo comparador como
`VERIFIED_SEPARATE_SESSIONS`.
Foram lidos os CSVs de medianas/recomendações e os resultados das análises de
cada campanha. Não se agruparam tempos brutos. Os protocolos e os arquivos
originais foram preservados; a repetibilidade desta seção pertence ao código
anterior à extensão conservadora DOALL, e não ao novo corpus de automação.

## Identidade e cobertura das sessões

| Sessão | Arquivo da coleta | Janela em 05/11/2026, UTC aproximada ao minuto | Configurações | Observações externas | Aquecimentos |
|---|---|---|---:|---:|---:|
| S1 | `results/multiplatform/linux_xeon_2026-11-05_p15w3/` | 15:26–16:24 | 60 | 900 | 180 |
| S2 | `results/publication/scaling_linux_session02_2026-11-05/` | 18:58–19:55 | 60 | 900 | 180 |
| S3 | `results/publication/scaling_linux_session03_medium_2026-11-05/` | 20:04–20:06 | 38 | 570 | 114 |

Cada configuração conserva quinze observações externas e três aquecimentos de
sua própria sessão. A unidade de comparação é a **mediana daquela configuração
naquela sessão**, não uma mediana sobre 30 ou 45 tempos misturados. S2 e S3
acrescentaram 1.470 observações externas, em arquivos separados.

A comparação das duas sessões completas tem **60 configurações comuns**.
A comparação das três tem **38 configurações comuns**: os dois tamanhos de
ambos os Dot e os conjuntos MEDIUM de PolyBench. Os conjuntos LARGE de
GEMM, Nussinov, Jacobi e Covariance têm somente S1 e S2. A ausência em S3
é parte do protocolo, não resultado perdido ou descarte posterior.

A máquina é o Xeon E3-1225 V2 com quatro núcleos e Clang 18.1.3, usando
sequencial e OpenMP 1/2/4T. S2 e S3 executaram a cópia congelada em `b9e252d`;
o comparador registrou identidade de fontes compiladas, dimensões, compilador,
flags e plataforma nos pontos comuns. As sessões foram iniciadas separadamente
e executadas em sequência, no mesmo host e dia, sem testes ou inferências
concorrentes às medições. Isso não estabelece independência, exclusividade
de todas as atividades do host ou controle de frequência/temperatura.

## Recomendações e ganhos por entrada

Cada célula mostra a recomendação do Selector da própria sessão e seu ganho
contra o sequencial **da mesma sessão**: `Stotal = Tseq/Tp`. O caso sem paralelo
admissível usa `seq. (1,000×)` para indicar fallback; não significa que a variante
OpenMP mediu ganho unitário. O resumo do Selector prefere menos threads no
quase empate de até 2% e pode recomendar 1T quando há benefício de transformação;
a admissão integrada de paralelo exige pelo menos 2T e ganho contra sequencial
e OpenMP 1T. Nos casos selecionados desta tabela, esses critérios coincidem.
A menor mediana e a
recomendação são desfechos diferentes.

| Caso / entrada | S1: recomendação (ganho total) | S2: recomendação (ganho total) | S3: recomendação (ganho total) |
|---|---:|---:|---:|
| Dot C automático / 1024 | seq. (1,000×) | seq. (1,000×) | seq. (1,000×) |
| Dot C automático / 10000000 | 2T (1,254×) | 2T (1,252×) | 2T (1,243×) |
| Dot C++ manual / 1000000 | seq. (1,000×) | seq. (1,000×) | seq. (1,000×) |
| Dot C++ manual / 10000000 | 2T (1,044×) | 4T (1,085×) | 2T (1,044×) |
| GEMM manual / MEDIUM | 4T (3,815×) | 4T (3,891×) | 4T (4,066×) |
| GEMM manual / LARGE | 4T (2,845×) | 4T (2,883×) | não coletado |
| Nussinov manual / MEDIUM | 4T (2,704×) | 4T (2,617×) | 4T (2,409×) |
| Nussinov simd_auto / MEDIUM | 4T (3,875×) | 4T (3,777×) | 4T (3,943×) |
| Nussinov simd_manual / MEDIUM | 4T (3,871×) | 4T (3,838×) | 4T (3,784×) |
| Nussinov manual / LARGE | 4T (3,195×) | 4T (3,089×) | não coletado |
| Nussinov simd_auto / LARGE | 4T (2,959×) | 4T (2,900×) | não coletado |
| Nussinov simd_manual / LARGE | 4T (2,974×) | 4T (2,951×) | não coletado |
| Jacobi-2D manual / MEDIUM | 4T (3,608×) | 4T (3,545×) | 4T (3,440×) |
| Jacobi-2D manual / LARGE | 2T (1,177×) | 2T (1,178×) | não coletado |
| Covariance manual / MEDIUM | 4T (2,171×) | 4T (2,197×) | 4T (2,191×) |
| Covariance manual / LARGE | 4T (2,193×) | 4T (2,173×) | não coletado |

As duas sessões completas mantiveram a recomendação em **15 das 16** combinações
entrada × variante. Entre as três sessões, **nove das dez** combinações comuns
mantiveram a escolha. Essas contagens incluem os dois casos que permaneceram
sequenciais e não constituem uma probabilidade de estabilidade em máquinas
ou dias diferentes.

A única mudança de threads recomendadas foi **Dot C++ manual N=10.000.000**:
2T → 4T → 2T. O menor tempo paralelo foi 4T nas três sessões, mas o excesso de
tempo de 2T em relação a 4T foi 1,926%, 3,867% e 1,588%, respectivamente.
Portanto, a mudança acompanha o limiar operacional de 2%, sem provar diferença
estatística entre essas configurações.

No **Dot C automático N=10.000.000**, a recomendação 2T permaneceu. Em S1 e S2,
4T teve menor mediana, com 2T apenas 0,127% e 0,073% mais lento. Em S3, 2T
passou a ter a menor mediana: 0,00874206 s contra 0,00941860 s de 4T.
A inversão do mais rápido, mesmo com recomendação idêntica, mostra por que
não basta relatar somente a configuração escolhida.

## Variação descritiva das medianas

O campo `cv_session_medians` dos CSVs é uma **fração**, calculada como desvio
padrão amostral das duas ou três medianas dividido por sua média. Nesta tabela
foi multiplicado por 100 e apresentado em **porcentagem**. Cada intervalo é o
mínimo e máximo desses CVs entre as configurações daquele caso, incluindo
sequencial e variantes presentes. Não é intervalo de confiança, CV dos quinze
tempos dentro de uma sessão ou estimativa populacional. As colunas máximo/mínimo
mostram a maior razão descritiva entre medianas de uma mesma configuração.

| Caso (todas as entradas/variantes presentes) | Configs S1–S2 | CV das medianas S1–S2 (%) | Maior máximo/mínimo S1–S2 | Configs S1–S2–S3 | CV das medianas S1–S2–S3 (%) | Maior máximo/mínimo S1–S2–S3 |
|---|---:|---:|---:|---:|---:|---:|
| Dot C automático | 8 | 0,0003–5,703 | 1,0840× | 8 | 0,163–4,779 | 1,0913× |
| Dot C++ manual | 8 | 0,368–4,181 | 1,0609× | 8 | 0,563–5,187 | 1,1086× |
| GEMM manual | 8 | 0,220–5,579 | 1,0821× | 4 | 4,373–7,483 | 1,1618× |
| Nussinov | 20 | 0,146–2,109 | 1,0303× | 10 | 0,292–5,715 | 1,1153× |
| Jacobi-2D manual | 8 | 0,033–1,336 | 1,0191× | 4 | 0,919–3,435 | 1,0664× |
| Covariance manual | 8 | 0,173–3,701 | 1,0537× | 4 | 0,536–2,948 | 1,0537× |

Os intervalos das duas comparações não devem ser lidos como antes/depois de um
tratamento: a comparação de três sessões exclui LARGE e contém outro número
de medianas e configurações. Nas duas sessões completas, a maior razão entre
medianas foi 1,0840× no Dot C pequeno automático em 4T. Entre as três, foi
1,1618× no GEMM MEDIUM sequencial. A configuração de maior razão é diferente;
não se trata de uma variação de 16,18% comum ao conjunto todo.

## Discrepâncias que afetam a interpretação

**GEMM: tempo absoluto e ganho relativo não se movem necessariamente juntos.**
No conjunto LARGE, o sequencial passou de 0,629662 s a 0,680011 s entre S1 e S2
(+7,996%), e OpenMP 4T de 0,221314 s a 0,235891 s (+6,587%). Ambos ficaram mais
lentos nas medianas, enquanto o ganho total aumentou de 2,845× a 2,883×. Já a
escalabilidade da variante caiu de 2,854× a 2,835×. Isso ilustra a dependência
dos dois baselines, sem identificar a causa da mudança de tempos.

No GEMM MEDIUM, a mediana sequencial foi 0,003689, 0,003992 e 0,004286 s,
e a mediana 4T foi 0,000967, 0,001026 e 0,001054 s. Assim, o ganho total subiu
até 4,066× em S3 mesmo com tempo 4T maior. Nessa sessão, `T1/T4 = 4,0816`
e a eficiência observada é 1,0204 (102,04%). O valor permanece registrado,
sem truncamento em 100%; seu IC95% bootstrap dentro de S3 é aproximadamente
[3,530; 4,350] para `T1/T4`, abrangendo quatro. Não demonstra escalabilidade
superlinear reprodutível nem uma causa arquitetural medida.

**Nussinov MEDIUM: a recomendação de threads se repetiu, os valores e a ordem
entre variantes SIMD variaram.** A versão manual em 4T teve medianas
0,007798, 0,008027 e 0,008697 s: razão máxima/mínima 1,1153× e CV das medianas
5,715%. Seu ganho total caiu de 2,704× a 2,409×. As variantes SIMD continuaram
mais rápidas que a manual nesse tamanho, mas `simd_auto`/`simd_manual` trocaram
posição: em S1, 0,005443/0,005448 s; em S2, 0,005561/0,005473 s; em S3,
0,005314/0,005537 s. O Selector seleciona threads dentro de cada variante;
essa comparação de variantes é descritiva, sem teste de superioridade entre elas.

No Nussinov LARGE, a manual continuou mais rápida que as duas SIMD nas duas
sessões completas: 5,449333/5,614330 s para a manual; 5,853742/5,876816 s para
`simd_manual`; 5,883270/5,980381 s para `simd_auto` (S1/S2). Portanto, a
vantagem SIMD observada em MEDIUM não se transfere automaticamente a LARGE.
A coleta exploratória anterior continua separada e não entrou nestes cálculos.
Estas duas novas sessões não apagam nem explicam causalmente a divergência
da exploração anterior.

**Jacobi e Covariance: escolhas repetidas não significam tempos invariáveis.**
Jacobi LARGE permaneceu em 2T, com ganho total 1,177× e 1,178×. Jacobi MEDIUM
permaneceu em 4T, mas seu tempo escolhido aumentou de 0,002830 a 0,003018 s
entre S1 e S3 (+6,643%), e o ganho caiu de 3,608× a 3,440×. Covariance manteve
4T nas entradas presentes; no LARGE, os ganhos foram 2,193× e 2,173×, enquanto
as escalabilidades foram praticamente iguais, 2,18317× e 2,18348×. A constância
aproximada de uma razão não garante constância de todos os seus componentes.

## Conclusão delimitada e fontes

As recomendações repetiram-se na maior parte deste conjunto, mas houve uma
mudança de escolha no Dot C++ e inversões da menor mediana que uma tabela
apenas de recomendações ocultaria. As sessões acrescentam evidência descritiva
de repetibilidade local, mantendo a variação de tempos e dos dois baselines.
Não estabelecem estabilidade geral, independência entre sessões, equivalência
entre dias ou causalidade de cache, banda, barreiras ou frequência.

Os ICs existentes são condicionais às quinze observações de cada campanha.
Não foram usados como teste entre sessões nem transformados em IC populacional
com duas ou três medianas. A matriz equivalente M5 continua pendente; estas
coletas Linux não substituem a execução em outra plataforma.

Fontes lidas para esta análise:

- [Comparação S1–S2: relatório](../../results/publication/session_comparison_two_full_linux_2026-11-05/report.json),
  [medianas](../../results/publication/session_comparison_two_full_linux_2026-11-05/session_medians.csv) e
  [escolhas](../../results/publication/session_comparison_two_full_linux_2026-11-05/session_selections.csv).
- [Comparação S1–S2–S3: relatório](../../results/publication/session_comparison_linux_2026-11-05/report.json),
  [medianas](../../results/publication/session_comparison_linux_2026-11-05/session_medians.csv) e
  [escolhas](../../results/publication/session_comparison_linux_2026-11-05/session_selections.csv).
- S1: [estatísticas por configuração](../../results/multiplatform/analysis_linux_xeon_2026-11-05_p15w3/measurements.csv) e
  [seleção](../../results/multiplatform/analysis_linux_xeon_2026-11-05_p15w3/selection.json).
- S2: [estatísticas por configuração](../../results/publication/analysis_scaling_linux_session02_2026-11-05/measurements.csv) e
  [seleção](../../results/publication/analysis_scaling_linux_session02_2026-11-05/selection.json).
- S3: [estatísticas por configuração](../../results/publication/analysis_scaling_linux_session03_medium_2026-11-05/measurements.csv) e
  [seleção](../../results/publication/analysis_scaling_linux_session03_medium_2026-11-05/selection.json).
- [Protocolo registrado](REPEATABILITY_PROTOCOL.md) e [identidade do código congelado](FROZEN_REPEAT_SOURCE.json).
