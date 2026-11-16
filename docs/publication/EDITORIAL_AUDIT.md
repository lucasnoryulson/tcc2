# Auditoria editorial e de inferência científica

Fonte auditada: `docs/monografia/REVISAO_MULTIPLATAFORMA.md`, versão de 05/11/2026
de 1.284 linhas, antes das ampliações para publicação. Esta auditoria não altera
o manuscrito nem suas evidências. As recomendações devem entrar em uma revisão
separada, preservando a versão que acompanha a campanha p15w3.

## Correções prioritárias

| Local do manuscrito auditado | Problema e consequência | Mudança concreta recomendada |
|---|---|---|
| Título, linha 1 | “Sistemas Multiagentes” e “Reestruturação Autônoma” sugerem interação e autonomia superiores às demonstradas | Usar “Paralelização OpenMP baseada em evidências: pipeline verificável, escalabilidade e limites de um Coordinator LLM”. Explicar os papéis determinísticos no corpo |
| Nota inicial, linhas 7–12 | “campanha final do Mac” pode ser confundida com a matriz multiplataforma nova | Escrever “estudo histórico do Coordinator no M5; coleta equivalente p15w3 no M5 ainda pendente” |
| R3, §1.1; contribuições, §1.2 | A pergunta permite ler que o Coordinator pode encontrar configuração superior, embora o Selector seja autoritativo | R3 deve perguntar concordância, vetos, falhas e custo sob a mesma configuração admissível. Criar pergunta separada para diagnóstico, com verdade de referência oculta |
| Fundamentação, §2.3 | ParEval sozinho não posiciona paralelização LLM e combinação regras/LLM frente a trabalhos próximos | Incorporar comparação de OMPar, P4OMP e RepoOMP, com versão, corpus e limites; ligar a [RELATED_WORK.md](RELATED_WORK.md) |
| §4.3, linhas 585–588 | “gráficos ... sem intervalos de confiança” contradiz os ICs de §4.6/5.8 | Restringir a frase aos gráficos históricos/exploratórios. Explicar que apenas a campanha principal com amostras suficientes usa o bootstrap especificado |
| §4.5 versus §4.6 | Sete medições/um aquecimento e quinze/três convivem com a mesma data | Nomear sempre campanha exploratória e campanha principal; acrescentar tabela de identidade, protocolo e finalidade; nunca somar as amostras |
| §4.6, linhas 733–736 | “dumps completos” pode implicar todos os arrays internos | Escrever “dumps completos das saídas live-out instrumentadas; em Jacobi-2D, A”. Distinguir dump de validação de execução temporizada |
| Ameaças, linha 1056 | “sem cobertura de todas as entradas temporizadas” é genérico e conflita com validações da nova matriz | Delimitar o gate integrado antigo e a validação por entrada/configuração da campanha principal. Declarar o que a validação não cobre: todos os valores possíveis, races e memória interna não observada |
| Ameaças, linha 1060 | “ordem fixa” contradiz ordem aleatória reproduzível de §4.6 | Dizer que campanhas legadas possuem seus protocolos, enquanto p15w3 embaralha configurações em rodadas com seed 2026; a ausência de controle externo permanece |
| §5.7, tabela Linux/M5 | Usa Linux exploratório e Mac histórico, com fontes/protocolos diferentes | Rotular comparação contextual no título e na legenda; não usar como resultado da nova matriz equivalente. Mover para apêndice se o artigo ficar centrado na campanha principal |
| §5.8 e discussão | Boa separação entre menor mediana e recomendação; é preciso conservá-la no resumo/conclusão | Explicitar que 2T nos Dot grandes decorre do quase empate de 2%, não da menor mediana; política não é teste estatístico |
| §6.1–6.2 | Explicações de cache, banda e barreiras podem parecer causalidade medida | Manter como hipóteses ou modelos; não chamar contagem lógica de bytes de tráfego DRAM. Sem contadores, não estimar percentuais de custo por mecanismo |
| Conclusão, linhas 1216–1227 | 3,673× de Nussinov exploratório aparece antes de 3,195× principal; leitura rápida sugere resultado inconsistente | Liderar com a campanha principal, deixar o valor exploratório identificado em discussão de repetibilidade. Não escolher a coleta mais favorável |
| Fechamento do texto | Ampliação de padrões declarada extensão, mas pode mudar nesta tarefa | Atualizar cobertura somente após execução; separar novo corpus de transformação de cinco kernels de desempenho; não herdar números de testes como resultados científicos |

## Demonstração do limite de R3

Em `scripts/evaluate_coordinator.py`, `run_trial` chama `parallel_selection`
antes da inferência. `accepted` só é verdadeiro quando a proposta coincide com
a configuração já selecionada. `final_time` é `selected["median_seconds"]` se
aceita e o tempo sequencial em caso contrário. A promoção real confere novamente
essa igualdade em `scripts/promote_candidate.py`.

Logo, com candidato, medições e admissibilidade fixos, todos os braços que
aceitam usam o mesmo `Tp`. A LLM pode concordar, vetar ou falhar; não pode obter
outro `Tp` admissível. A igualdade de speedup não é uma descoberta sobre a
capacidade geral da LLM. O resultado empírico é a concordância e o custo no
conjunto observado. Não relaxar a promoção para criar diferença favorável.

Texto substituto sugerido para R3:

> Mantidas as evidências e a configuração admissível, com que frequência o
> Coordinator concorda com a política determinística, veta oportunidades ou
> produz propostas inválidas, e qual custo adicional introduz?

Uma nova pergunta sobre diagnóstico deve receber logs sem rótulo esperado nem
uma decisão determinística que entregue a resposta, ter gabarito rastreável e
manter desenvolvimento separado da avaliação. Comparar regras, contexto
completo e ablação com igual orçamento. Admissão e diagnóstico não devem ser
agregados numa única taxa de “inteligência”.

## Repetições e incerteza

As 900 medições da campanha principal são 15 observações por configuração,
distribuídas em 60 configurações. São cinco algoritmos, com variantes, entradas e
threads; não 900 programas independentes. Repetições de inferência reutilizando
um contexto também não multiplicam candidatos nem medições do kernel.

O bootstrap atual reamostra índices de rodadas completas, preservando o
pareamento entre sequencial, OpenMP 1T e p. Ele não trata blocos temporais
contíguos como um moving-block bootstrap. Os ICs são condicionais à campanha,
sem demonstração de estacionariedade ou independência entre rodadas. Não
interpretar sobreposição ou ausência de sobreposição de ICs como teste formal
entre plataformas. Comparações múltiplas e escolha posterior da melhor mediana
exigem cautela adicional.

Se CV for acrescentado, definir `100 × DP_amostral / média`, com unidades em
percentual. CV, MAD e IQR descrevem dispersão dentro da coleta; nenhum deles
substitui repetição entre sessões. Não chamar uma campanha de estável apenas
porque o CV é pequeno. Novas sessões devem manter diretórios e identificadores
próprios; relatar diferenças antes de considerar qualquer agregação.

## Escopo, completude e rastreabilidade

Separar três eixos no resumo, nos resultados e na conclusão:

1. Fontes transformadas automaticamente, classificadas por transformação
   implementada, aceitação/recusa, compilação e teste executável.
2. Variantes medidas para escalabilidade: Dot, GEMM, Nussinov, Jacobi e Covariance,
   com origem manual/automática identificada por caso.
3. Decisões ou diagnósticos da LLM, com modelo, prompts, rótulos, denominadores e
   falhas preservadas.

Nenhum desses eixos deve ampliar os demais implicitamente. Um novo corpus
curado localmente permite avaliar o recorte, mas não representa código industrial
nem uma amostra aleatória de C. Casos negativos são importantes para medir
recusas; suas categorias e seus motivos não devem aparecer como respostas no
prompt da avaliação final.

No Jacobi, o dump A cobre o estado de saída especificado pelo benchmark. Isso
não verifica separadamente B ou estados intermediários. SHA-256 liga bytes e
relatórios localmente; não é assinatura independente, prova de semântica nem
captura integral do sistema operacional e das bibliotecas.

O Mac histórico comprova execuções históricas e uma avaliação específica do
Coordinator. A matriz nova no M5 continua pendente enquanto não houver execução
e verificação reais. Receitas, smoke tests e comparação de um arquivo com ele
mesmo não constituem medições Mac.

## Estrutura recomendada para a próxima revisão

Liderar com pergunta delimitada e tabela de cobertura. Descrever primeiro o
contrato e o baseline determinístico, depois o papel subordinado do Coordinator.
Apresentar campanha principal, cobertura de transformação e decisões em seções
distintas. Manter históricos resumidos num apêndice, com motivo de preservação.
Discutir falhas e divergências entre sessões antes das hipóteses de arquitetura.
Concluir cada questão com evidência e limite correspondentes.

No artigo, priorizar uma contribuição: ligação verificável entre transformação,
evidências e admissão, e limites de coordenação no recorte. O estudo de
diagnóstico e a extensão de transformação só entram como resultados após
execução e análise. Não anunciar superioridade sobre ferramentas externas sem
comparação pareada compatível.

Não foi feita inspeção de layout nativo Word nem revisão de uma chamada
específica de publicação. Estas correções científicas/editoriais não substituem
aprovação do orientador, conferência institucional ou avaliação pelos revisores.

## Resolução executada em 06/11/2026

A fonte nova `REVISAO_PUBLICACAO.md` incorporou as correções acima, preservando
integralmente a revisão auditada. Título e perguntas refletem o recorte real;
componentes determinísticos, geração, variantes manuais, admissão histórica e
diagnóstico estão identificados. A campanha principal lidera os resultados;
exploratórios foram movidos ao apêndice. Live-out A de Jacobi, rodadas aleatórias,
quase empate operacional e hipóteses arquiteturais têm limites explícitos.

O corpus autoral e baseline GCC foram efetivamente executados; duas sessões
Linux adicionais medem repetibilidade sem fundir observações. Ambos os modelos
foram avaliados em heldout congelado. Resultados negativos, falhas de citação,
ablação vazia, schema/interface e o teto mecânico da rubrica estão discutidos.
A demonstração DOALL real encerrou por timeout, sem promoção; uma contraprova
FP foi rejeitada pelo gate. O texto não atribui speedups manuais à LLM.

Os [resultados](RESULTS.md), [diagnósticos](DIAGNOSTIC_RESULTS.md),
[repetibilidade](REPEATABILITY_RESULTS.md) e [validações](VALIDATION.md) fornecem
os números e logs. Monografia, artigo e defesa possuem novos Word/PDF/PPTX;
reabertura estrutural e revisão visual parcial não equivalem a layout nativo
Office aprovado. Permanecem externos a matriz M5, revisão humana independente,
modelo institucional completo, escolha do veículo e aprovação acadêmica.
