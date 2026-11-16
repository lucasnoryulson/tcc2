# Fortalecimento científico — resultados executados no Linux

Este relatório mantém separados corpus de transformação, conformidade diagnóstica, repetibilidade e as 900 medições anteriores. Não houve novas medições M5.

## Corpus e comparação com uma ferramenta existente

Estado do arquivo: COMPLETE. Foram avaliadas 28 fontes autorais: 14 no subconjunto suportado e 14 recusas previstas. Houve 14 aceitações e 14 recusas conforme a especificação, 0 aceitações indevidas, 0 recusas indevidas e 0 erros inesperados. Os 28 pares positivos fonte × entrada passaram na validação funcional, com saída por elemento nos DOALL.

A campanha contém 196 configurações, 2940 observações externas e 588 aquecimentos. As chamadas internas são amortização, não amostras independentes. Gates e cada processo medido verificam a saída observável.

Original sequencial, fonte gerada e autoparalelização GCC usam o mesmo GCC, driver e entradas. O braço GCC usa -ftree-parallelize-loops=p; os objetos de kernel são compilados separadamente do driver. Ativar a flag não comprova uso efetivo de p workers. T1/Tp nesse braço compara configurações compiladas separadamente.

O contraste de desempenho cobre somente as fontes positivas do nosso contrato. As recusas não constituem comparação de cobertura geral com GCC; alguns programas fora do nosso subconjunto podem ser paralelizáveis por outras técnicas.

| Fonte / N=1.000.000 | Pipeline: threads / ganho total | GCC autopar: threads / ganho total | Tempo GCC / pipeline recomendado |
|---|---:|---:|---:|
| absolute_difference | 2T / 1.1421× | 2T / 1.1427× | 0.99948× |
| affine_vector | 2T / 1.1318× | 2T / 1.138× | 0.99456× |
| clamp | 2T / 1.1141× | 2T / 1.1174× | 0.99706× |
| count_comparison | 2T / 1.3509× | 2T / 1.0227× | 1.321× |
| inner_product | 2T / 1.3335× | 1T / 1.0011× | 1.332× |
| l1_norm | 4T / 3.2311× | seq / 1× | 3.2311× |
| polynomial | 2T / 1.1418× | 2T / 1.1497× | 0.99319× |
| readonly_stencil | 4T / 1.8984× | 4T / 1.8164× | 1.0452× |
| reciprocal_quadratic | 4T / 1.7928× | 2T / 1.8128× | 0.98898× |
| squared_distance | 2T / 1.3717× | 1T / 1.0352× | 1.3251× |
| sum_squares | 4T / 3.2114× | 2T / 1.003× | 3.2018× |
| threshold_filter | 2T / 1.1665× | 4T / 1.219× | 0.95697× |
| vector_product | 2T / 1.1804× | 2T / 1.1449× | 1.031× |
| vector_sum | 4T / 3.0791× | 1T / 1.0044× | 3.0655× |

A média geométrica descritiva das 14 razões de tempo GCC/pipeline recomendadas na entrada grande é 1.3602×. Valores acima de um favorecem o tempo do pipeline nessas fontes; não são estimativa sobre programas externos nem isolamento da qualidade de um compilador geral. A escolha por quase empate pode diferir da menor mediana.

Por padrão: DOALL: 8 fontes, razão geométrica 1.0005×; REDUCTION: 6 fontes, razão geométrica 2.0487×.

Nas reduções, a diretiva OpenMP permite outra ordem de soma, avaliada com tolerância numérica. GCC sem flags de reassociação pode preservar a ordem sequencial e recusar a paralelização floating-point. Logo, uma vantagem nas reduções não demonstra superioridade geral da análise de dependências do pipeline. Os resultados DOALL são separados dessa diferença de semântica/contrato.

As tabelas completas, ICs condicionais, tempos, escolhas e recusas estão no arquivo da campanha. O split autoral organiza a análise; não é teste cego externo. Não houve detector de races, prova formal ou teste dinâmico do contrato restrict.

## Diagnóstico offline: rubrica oculta, não promoção

O catálogo tem 24 vistas sobre cinco famílias, incluindo incidentes arquivados, extrações e injeções controladas realmente executadas. Os rótulos são autorais e derivados de rubrica mecânica; regras concordam por construção, sem validação humana independente. A avaliação final usa 12 vistas de três famílias heldout, uma chamada por caso/braço/modelo. O caso de desenvolvimento do preflight fica separado.

| Modelo / braço heldout | Executados / planejados | JSON válido / executados | Causa + ação conforme / executados | Propostas perigosas | Claims sem suporte / verificados | Mediana da chamada (s) |
|---|---:|---:|---:|---:|---:|---:|
| qwen2.5:3b / coordinator | 12/12 | 11/12 | 0/12 | 0 | 42/46 | 41.536 |
| qwen2.5:3b / coordinator_without_analysis | 12/12 | 12/12 | 0/12 | 0 | 48/52 | 39.747 |
| regras | 12/12 | 12/12 | 12/12 | 0 | 0/12 | 0.000139 |
| llama3.1:8b / coordinator | 12/12 | 12/12 | 0/12 | 0 | 28/52 | 75.712 |
| llama3.1:8b / coordinator_without_analysis | 12/12 | 12/12 | 0/12 | 0 | 18/42 | 64.194 |

Estados: qwen2.5:3b: COMPLETE_WITH_FAILURES; llama3.1:8b: COMPLETE.

Identidades observadas: qwen2.5:3b: digest 357c53fb659c, 3.1B, Q4_K_M, Ollama 0.15.1; llama3.1:8b: digest 46e0c10c039e, 8.0B, Q4_K_M, Ollama 0.15.1. Os digests completos e metadados estão em results.json.

| Modelo / braço | Chamadas reais | Respostas com contagem de tokens | Prompt observado | Geração observada | Soma do tempo das tentativas (s) |
|---|---:|---:|---:|---:|---:|
| qwen2.5:3b / coordinator | 12 | 12 | 3332 | 2109 | 582.2 |
| qwen2.5:3b / coordinator_without_analysis | 12 | 12 | 2761 | 2062 | 466.04 |
| llama3.1:8b / coordinator | 12 | 12 | 3259 | 1909 | 1034 |
| llama3.1:8b / coordinator_without_analysis | 12 | 12 | 2688 | 1631 | 691.88 |

As contagens de tokens são os campos efetivamente devolvidos pelo servidor. Uma resposta sem metadados não recebe estimativa; somas observadas não substituem latência e incluem os efeitos de cache/carregamento da execução.

Slots ausentes não são respostas incorretas observadas; cobertura planejada e desempenho nas tentativas aparecem separados. Contagens 0/0 representam ausência de avaliação, não taxa de acerto ou ausência de erros.

A ablação é efetiva somente em dois dos doze casos heldout; os outros prompts são idênticos. O pareamento e esse estrato estão registrados por tentativa. Claims são triplas checadas por igualdade exata contra fatos, não avaliação humana de justificativa livre. Respostas inválidas não são prova de ausência de afirmações falsas. Uma única repetição não caracteriza variância do modelo; não se estima acurácia populacional.

| Modelo / caso com análise removível | Completo: estado / causa e ação | Sem análise: estado / causa e ação |
|---|---|---|
| qwen2.5:3b / d20 | INVALID / 0 | OK / 0 |
| qwen2.5:3b / d23 | OK / 0 | OK / 0 |
| llama3.1:8b / d20 | OK / 0 | OK / 0 |
| llama3.1:8b / d23 | OK / 0 | OK / 0 |

Timeout é terminal para chamadas de modelo na campanha. As demais ficam NOT_RUN, sem retry oculto. Latência inclui carregamento e cache do servidor; diferenças entre braços não isolam causalmente o tamanho do contexto.

## Repetibilidade sem agrupar sessões

Foram comparadas 3 sessões, com 38 configurações comuns. A terceira coleta priorizou MEDIUM e os Dot; LARGE de PolyBench tem somente duas sessões. Cada mediana conserva suas quinze observações. O código desta repetição foi congelado em b9e252d, separadamente da nova extensão do transformador.

São sessões do mesmo dia e host, executadas em sequência sem inferência ou testes concorrentes. Isso não demonstra independência, temperatura/frequência controladas ou repetição em dias diferentes. O relatório de sessões apresenta CV das medianas e mudanças de recomendação sem fundir tempos brutos.

## Papel da LLM e limites

No experimento histórico de admissão, o Selector já escolhe a configuração e o Executor exige a mesma escolha. Portanto, a LLM não pode superar o speedup do baseline nesse desenho; concordância, vetos e custo são os resultados empíricos. Diagnóstico offline é uma tarefa separada e não demonstra geração, reparo ou promoção.

A comparação com trabalhos próximos é bibliográfica; a comparação executada com ferramenta externa é o braço GCC no corpus controlado. Não se reproduziram OMPar, P4OMP ou RepoOMP. Não se alega prioridade absoluta de pipelines híbridos baseados em evidências.

Faltam a nova matriz no M5, revisão humana independente do corpus/rubrica, conferência institucional e layout nativo Office. Scripts e PDFs de revisão não equivalem a essas validações.
