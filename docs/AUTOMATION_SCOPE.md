# Escopo implementado e evidências da automação

Classificação, transformação, variante medida, diagnóstico e promoção são
capacidades distintas. A extensão atual acrescenta uma classe conservadora
DOALL ao subconjunto de redução escalar; as novas campanhas têm protocolos e
artefatos próprios e não reclassificam retroativamente resultados manuais.

## Contrato de transformação atual

`analysis/conservative_transform.py`, versão `standalone-ast-v2`, verifica o AST
obtido da fonte atual. `analysis/code_transformer.py` reanalisa esses bytes antes
de inserir a diretiva. O nome interno `certify_kernel` é uma checagem local de
pré-condições, sem certificação externa ou prova formal.

- **REDUCTION:** um acumulador `double` local, inicializado em zero; um laço
  canônico com `sum += expressão` pura, sem recorrência do acumulador no lado
  direito; retorno do acumulador e entradas somente lidas.
- **DOALL:** um laço canônico com atribuição `Y[i] = expressão` pura, escrita
  injetiva, sem leitura da saída e ponteiros `restrict` no formato admitido.
  Entradas são `const double *restrict`, e a saída é `double *restrict`.

`restrict` é obrigação do chamador, não análise dinâmica de alias. Extensões de
buffers válidas, aritmética definida e ausência de comportamento indefinido são
pré-condições. Os drivers controlados usam buffers separados. Índices de entrada
são limitados a `i` e `i +/- constante` no intervalo admitido; não há análise
geral de limites. Fontes independentes devem ter uma função `kernel_*` compatível,
um único laço externo e formato de fonte reconhecido.

Chamadas, atributos, pré-processamento, `_Pragma`, escritas aninhadas, scatter,
in-place, efeitos laterais, corpos com múltiplas atribuições, laços aninhados e
nós não reconhecidos são recusados. Algumas recusas são programas paralelizáveis
fora do suporte, não provas de dependência. A
[especificação do corpus](publication/AUTOMATION_CORPUS.md) e a
[revisão do contrato](publication/TRANSFORM_REVIEW.md) detalham as restrições.

## Execução integrada e grau de evidência

O runner encadeia análise AST, dependências reconhecidas, classificação,
planejamento, transformação, gates, seleção, contexto, Coordinator e promoção.
A execução histórica de 03/11/2026 no M5 terminou `PROMOTED` para Dot Product,
com `llama3.1:8b`, LLVM 23.1.1 e 4 threads. Ela demonstra o caminho redução/Dot.

A extensão DOALL está implementada no despacho do runner e tem corpus próprio
concluído: 28 fontes, 14 aceites e 14 recusas conforme o suporte, sem falso
aceite/recusa no conjunto autoral. Os 28 pares positivos fonte × entrada
passaram, e a campanha coletou 196 configurações e 2.940 medições com GCC 13.3.0
comum aos três braços. Isso demonstra transformação e execução no corpus;
não herda a promoção histórica de Dot nem comprova promoção DOALL com inferência
real. A [demonstração integrada de 06/11](../results/publication/doall_pipeline_linux_2026-11-06/run-jia507x_/summary.json)
gerou o candidato, passou na corretude e mediu configurações, mas a chamada
Qwen expirou em 180 s: FAILED, sem decisão/promoção e sem retry. Ela não
integra as quinze amostras do corpus.

| Caso | Análise/classificação | Origem da transformação ou variante | Evidência de execução integrada |
|---|---|---|---|
| Dot Product / REDUCTION | Sim | Redução escalar determinística | Pipeline histórico com inferência e promoção no M5; seis fontes de redução aceitas e validadas no corpus novo |
| Microkernels independentes DOALL | Contrato AST conservador | Geração determinística de `parallel for`, dentro das pré-condições | Oito fontes autorais aceitas, duas entradas cada e candidatos 1/2/4T validados; promoção real não é consequência desses benchmarks |
| GEMM PolyBench / DOALL | Sim | Variante OpenMP manual nas campanhas de escalabilidade | A extensão para microkernels não transforma automaticamente o GEMM aninhado |
| Jacobi-2D / STENCIL | Sim, com limitações na dependência temporal | Variantes manual/tiled | Fora da geração integrada genérica atual |
| Covariance / MIXED | Sim, incluindo relações não resolvidas | Variante OpenMP manual | Fora da geração integrada genérica atual |
| Nussinov / WAVEFRONT | Sim | Variantes manuais e adaptações determinísticas específicas sobre base OpenMP existente | Não demonstrado pelo runner genérico |
| Wavefront sintético | Sim | Variantes manual/tiled e autotuning | Não demonstrado pelo runner genérico |

O corpus novo contém 28 fontes autorais: 14 positivas e 14 recusas esperadas,
organizadas em oito arquivos de desenvolvimento e vinte de teste controlado.
Duas entradas por fonte positiva não contam como programas adicionais. Os
rótulos refletem a especificação do subconjunto; não são anotação externa ou
estimativa representativa de programas C. A campanha concluída conserva
[cobertura](../results/publication/automation_corpus_linux_2026-11-05/coverage.json),
[resumos](../results/publication/automation_corpus_linux_2026-11-05/summary.csv)
e [seleções](../results/publication/automation_corpus_linux_2026-11-05/selection.json),
separados das 900 medições p15w3 e das sessões adicionais congeladas em b9e252d.

Os dois candidatos usam o mesmo GCC e driver: OpenMP gerado e autopar a partir
do original. Nos DOALL grandes, os ganhos recomendados do pipeline vão de
1,114× a 1,898×, e do GCC de 1,117× a 1,816×. Nas reduções, OpenMP permite
reassociação que o GCC sem fast-math pode recusar; isso impede atribuir seus
ganhos a melhor análise de dependências. O Selector pode recomendar 1T por
transformação/quase empate; `artifact_provenance.parallel_selection` exige
≥2T e ganho contra sequencial e 1T para admissão. SELECTED no corpus não
significa promoção ou ativação comprovada de p workers.

## Papel da LLM e duas tarefas diferentes

Há uma LLM no Coordinator de produção. Análise, transformação, gates, Selector
e promoção são determinísticos. O termo multiagente descreve papéis funcionais,
sem implicar várias LLMs conversando, LangGraph, BDI ou geração pela LLM.

Na **admissão**, a configuração aceitável já é determinada pelo Selector. A LLM
pode concordar, vetar ou falhar. Uma configuração diferente não se torna
admissível pela resposta textual. `RETUNE`, `MODIFY` e `REJECT` interrompem a
tentativa: não executam um ciclo de recuperação. O ganho do kernel não é ganho
da LLM, e igualdade de speedup entre braços que aceitam é consequência do desenho.

No **diagnóstico offline**, um harness separado compara regras, LLM completa e
ablação sobre evidências sem gabarito exposto. Causa e ação são avaliadas contra
rubrica autoral congelada; claims são verificadas mecanicamente. Esse estudo
não executa reparos nem alcança o executor de promoção. O baseline perfeito
confirma sua consistência com a rubrica, sem demonstrar validação humana
independente. Catálogo, limites e falhas estão em
[DIAGNOSTIC_PROTOCOL.md](publication/DIAGNOSTIC_PROTOCOL.md).

O heldout executou 48 chamadas reais: Qwen e Llama, completo/ablação, uma chamada
em cada uma das doze vistas GEMM/Jacobi/Covariance. Qwen teve um JSON truncado
por limite de saída; Llama concluiu com JSON válido nos dois braços. Causa e
ação conformes simultaneamente foram 0/12 por braço em ambos os modelos. A
ablação só altera dois prompts e remove toda a evidência desses casos; o
baseline mecânico não é validação humana independente. Esses resultados
caracterizam interface, orçamento e rubrica testados, sem demonstrar reparo,
benefício geral da LLM ou um ranking de modelos.

## Limites mantidos

GPU/CUDA, geração universal de C/C++, múltiplas LLMs negociando, busca autônoma,
reparo iterativo e superioridade sobre geração monolítica não foram demonstrados.
Também não há prova formal, ausência geral de races, análise de alias universal
ou corretude para todas as entradas. Gates e drivers observam casos concretos;
DOALL usa checagem por elemento nas entradas do corpus antes de emitir checksum.
Na [contraprova numérica executada](../results/publication/numerical_limit_linux_2026-11-06/gate.json),
sequencial e redução 1T deram zero e 2T gerou `-inf`; o gate recusou. Entradas
finitas e resultado sequencial finito não garantem parciais paralelos finitos.
O ensaio é suplementar, fora das 28 fontes/2.940 medições, e delimita a afirmação
de corretude às entradas testadas.

As campanhas de escalabilidade usam cinco algoritmos e variantes explicitamente
identificadas. Elas não aumentam implicitamente a amostra de geração automática
ou de decisões da LLM. O M5 histórico não substitui a nova matriz equivalente,
que continua dependente da execução naquela máquina.
