# Estado do TCC — fortalecimento científico atualizado em 6 de novembro de 2026

Esta numeração corresponde à lista original de conclusão. O fechamento histórico
no M5 permanece registrado. Corpus, sessões Linux e inferências heldout foram
concluídos em 05/11, preservando falhas. A bateria final foi aprovada. Exportação e pendências externas têm estados
próprios; não são concluídas pela coleta ou pelos testes.

O estado operacional e a sequência de execução estão em
[publication/WORKLOG.md](publication/WORKLOG.md). Os novos estudos usam diretórios
próprios e preservam a campanha principal Linux p15w3 e o acervo histórico.

| Item | Estado atual | Evidência e pendência |
|---|---|---|
| **1. Fechar o pipeline até a geração do resultado final** | Dot/redução promovido historicamente; DOALL gerado/medido, sem promoção real | O corpus transformou/validou oito DOALL e seis reduções. A demonstração integrada DOALL real de 06/11 passou pelas etapas determinísticas, mas Qwen expirou em 180 s: FAILED, sem decisão ou promoção, execução única preservada. |
| **2. Resolver lacunas de validação e configuração** | Bateria final aprovada; limites semânticos explícitos | 123 testes sem skips, 23 casos em seis regressões, isolamento estático, três verificações bash e duas recusas de sobrescrita passaram. Auditoria preservou 4.416 arquivos históricos. A contraprova numérica foi recusada pelo gate; reconhecimento AST não prova equivalência universal. |
| **3. Delimitar exatamente o que o sistema automatiza** | Escopo revisado | Geração determinística de redução escalar e microkernels DOALL sob `standalone-ast-v2`. GEMM, Jacobi e Covariance das campanhas continuam manuais; Nussinov mantém adaptações específicas. Uma LLM no Coordinator; diagnóstico offline separado da admissão. Ver [AUTOMATION_SCOPE.md](AUTOMATION_SCOPE.md). |
| **4. Fechar a avaliação científica dos agentes** | Piloto diagnóstico heldout concluído, com falha preservada | Qwen/Llama executaram 48 chamadas em doze vistas e dois braços por modelo. Qwen teve um INVALID por limite de saída; Llama concluiu. Causa + ação conforme rubrica: 0/12 em cada braço LLM. Baseline autoral perfeito verifica consistência, sem medir utilidade externa ou reparo. Estudo histórico M5 preservado. |
| **5. Consolidar experimentos e reprodução** | Linux concluído nos estudos previstos; M5 equivalente pendente | p15w3: 900 medições; S2/S3: mais 1.470, em arquivos próprios; escolhas repetidas em 15/16 e 9/10 combinações. Corpus: 28 fontes, 196 configurações, 2.940 medições, 588 aquecimentos e 28 pares positivos PASS. Comparadores verificaram compatibilidade sem juntar amostras. |
| **6. Fechar monografia e defesa** | Fontes e exportações revisadas; validações externas pendentes | Auditoria, bibliografia dirigida, monografia, artigo e slides preservam versões anteriores. Monografia PDF com 70 páginas, artigo PDF com 23 e defesa com 20 slides/notas foram exportados; arquivos reabertos e revisão visual de gráficos/páginas representativas aprovada. M5, modelo institucional completo, Office nativo e aprovação acadêmica permanecem externos. |

## 1. Pipeline histórico e extensão atual

Em 03/11/2026 no M5, o preflight terminou `PREPARED`, e o pipeline completo
terminou `PROMOTED` com `llama3.1:8b` (ID local `46e0c10c039e`), LLVM Homebrew
23.1.1 e threads 1/2/4. O Coordinator recomendou 4T. A configuração promovida
teve ganho total de 2,46546× e escalabilidade contra OpenMP 1T de 2,46466×.

O bundle está em
`results/final-promoted/mac-2026-11-03/5eef401105cc51be73471cfbf836964f858d9453a381224490828123f54eb1d5/`.
O candidato tem SHA-256
`5ece8b7eb8416cbc3ad123aa137a81c639253a1d9a3f4565983e2a1c22f7978b`.
A revalidação terminou PASS. Esses resultados pertencem ao Dot/redução histórico.

O código atual acrescenta DOALL conservador, sem alterar o mecanismo de promoção.
Uma função `kernel_*`, um laço canônico e uma atribuição pura/injetiva são
pré-condições, com obrigações de `restrict` do chamador. Não se generaliza isso
ao GEMM aninhado nem às demais fontes PolyBench. O corpus novo executou essa
extensão separadamente, com 14 fontes aceitas e 14 recusadas conforme suporte,
zero falsos aceites/recusas no conjunto autoral. Ver
[AUTOMATION_CORPUS.md](publication/AUTOMATION_CORPUS.md) e
[arquivo de cobertura](../results/publication/automation_corpus_linux_2026-11-05/coverage.json).

A [demonstração integrada DOALL real de 06/11](../results/publication/doall_pipeline_linux_2026-11-06/run-jia507x_/summary.json)
gerou `affine_vector`, passou na corretude, mediu e construiu contexto. A chamada
Qwen expirou em 180 s; o runner terminou FAILED, sem decisão/promoção e sem retry.
Os cinco tempos por configuração pertencem à demonstração técnica, sem entrar
nas quinze amostras do corpus. Modelo descarregado e ausência de geração
posterior foram registrados.

## 2. Validação: registros anteriores e revisão nova

A suíte histórica Mac de 03/11 executou 82 testes unittest e 14 regressões,
sem skips. Na etapa p15w3 Linux, 91 testes e 23 casos de regressão, além do
isolamento estático, foram aprovados. São registros de versões e datas próprias.

Nesta etapa, novas checagens revalidam o corpo AST e a posição física da fonte,
recusam atributos/pré-processamento e exigem comparação por elemento no DOALL.
A bateria final passou com **123 testes em 23,130 s, sem skips**, 23 casos em
seis regressões, isolamento estático, três `bash -n` e duas recusas de sobrescrita.
Logs: `results/publication/validation_linux_2026-11-05/unittest_publication_final.log`
e demais arquivos finais desse diretório. A execução anterior de 121 testes é
um registro separado, não somado aos 123. A auditoria confirmou 4.416 arquivos
históricos inalterados.

Uma checagem shell inicial supôs retorno 2 nos dois wrappers; o diagnóstico
recusava corretamente uma saída existente por `FileExistsError`, com retorno 1.
A expectativa foi corrigida e o registro inicial preservado, sem alterar a
recusa. Testes técnicos não constituem inferências reais ou prova semântica.

Uma [contraprova numérica separada](../results/publication/numerical_limit_linux_2026-11-06/gate.json)
usou 1.026 valores finitos de magnitude até 1e308: sequencial e OpenMP 1T
retornaram zero, enquanto 2T produziu `-inf`. O gate retornou FAIL. Isso mostra
que reordenar a redução pode ultrapassar o intervalo finito mesmo quando o
sequencial não o faz; não há corretude universal por reconhecer `+=`.
O ensaio não foi somado às 28 fontes/2.940 medições do corpus.

## 3. Três eixos de cobertura

| Eixo | Unidade correta | Limite |
|---|---|---|
| Automação | Fonte C distinta, aceitação/recusa conforme suporte, compilação e corretude por entrada | Corpus autoral, sem generalização a C arbitrário; entrada adicional não vira programa adicional |
| Escalabilidade | Variante × entrada × configuração × sessão | Cinco algoritmos; variantes manuais identificadas; não multiplicar a cobertura automática pelo número de medições |
| LLM | Decisão ou diagnóstico por caso/braço/modelo | Admissão subordinada ao Selector e diagnóstico por rubrica são tarefas diferentes; sem reparo executado |

O detalhamento vigente é [AUTOMATION_SCOPE.md](AUTOMATION_SCOPE.md). Classificar
um padrão não basta para afirmar que sua transformação está implementada.

## 4. Avaliação da LLM e limite das conclusões

O estudo histórico de admissão no M5 preserva a campanha original `INCOMPLETE`
e a replicação após correção de schema. Na replicação, as 12 respostas LLM foram
válidas e concordaram com a política nos dois tamanhos de Dot. No ensaio
controlado do `llama3.1:8b`, ACCEPT, REJECT e RETUNE tiveram 6/6, e MODIFY 0/6.
Não foi demonstrado benefício adicional da LLM nem das análises nessa amostra.

A configuração aceitável já vem do Selector. Logo, aceitar o mesmo candidato
implica usar o mesmo tempo medido; esse desenho avalia concordância, vetos,
falhas e custo, sem permitir escolher um speedup admissível superior.

O novo estudo de [diagnóstico](publication/DIAGNOSTIC_PROTOCOL.md) remove o
rótulo esperado do prompt, mantém causas/ações anotadas previamente e separa
famílias de desenvolvimento/heldout. São 24 vistas sobre cinco famílias,
incluindo falhas executadas por injeção controlada; não são 24 programas
independentes. O baseline implementa a própria rubrica e concorda 24/24, sem
validação humana independente. O [plano final de inferência](publication/DIAGNOSTIC_RUN_PLAN.json)
fixou orçamento e modelos antes do heldout. As duas campanhas terminaram:

| Modelo / braço | JSON válido | Causa + ação conforme rubrica | Claims sem vínculo exato / verificadas | Latência mediana |
|---|---:|---:|---:|---:|
| Qwen completo | 11/12 | 0/12 | 42/46 | 41,536 s |
| Qwen sem análise | 12/12 | 0/12 | 48/52 | 39,747 s |
| Llama completo | 12/12 | 0/12 | 28/52 | 75,712 s |
| Llama sem análise | 12/12 | 0/12 | 18/42 | 64,194 s |

Cada modelo tentou 36 slots, incluindo doze regras e 24 chamadas LLM. Qwen
terminou `COMPLETE_WITH_FAILURES`, com um INVALID por truncamento no limite
de 384 tokens; Llama terminou `COMPLETE`. Não houve timeout, `NOT_RUN` ou retry.
As regras concordam 12/12 por braço/campanha com sua própria rubrica.

Claims sem vínculo não são uma taxa de falsidade factual. A ablação altera
somente dois prompts heldout, removendo toda sua evidência e preservando os
rótulos originais. O schema foi enviado em `format`, sem enumerar opções nas
mensagens; esse desenho e o orçamento limitam atribuir erros somente ao modelo.
Não há avaliação humana independente, reparo, estimativa populacional ou
comparação causal de tamanho de modelo. Fontes:
[Qwen](../results/publication/diagnostics_qwen_heldout_linux_2026-11-05/results.json),
[Llama](../results/publication/diagnostics_llama_heldout_linux_2026-11-05/results.json)
e [análise](publication/DIAGNOSTIC_RESULTS.md).

## 5. Resultados existentes e campanhas novas

A referência numérica já concluída é o
[relatório multiplataforma p15w3](experiments/MULTIPLATFORM_REPORT.md):

| Entrada maior / origem | Threads recomendadas | Ganho total | Escalabilidade |
|---|---:|---:|---:|
| Dot C automático | 2 | 1,254× | 1,276× |
| Dot C++ manual | 2 | 1,044× | 1,239× |
| GEMM manual | 4 | 2,845× | 2,854× |
| Nussinov manual | 4 | 3,195× | 3,204× |
| Jacobi-2D manual | 2 | 1,177× | 1,182× |
| Covariance manual | 4 | 2,193× | 2,183× |

Os Dot grandes têm menor mediana em 4T; a recomendação 2T decorre do quase
empate de 2%. O Dot C pequeno e o C++ menor não tiveram paralelo benéfico.
ICs bootstrap são condicionais à campanha. Divergências do Nussinov médio entre
a coleta exploratória e p15w3 motivam sessões adicionais, sem apagar dados.

As [sessões concluídas](publication/REPEATABILITY_RESULTS.md) usam código
congelado b9e252d e comparação sem juntar amostras. S2 acrescentou 900 medições
e S3, 570; há 60 configurações comuns às duas completas e 38 às três.
As escolhas repetiram-se em 15/16 e 9/10 combinações; Dot C++ grande mudou
2T→4T→2T ao cruzar o limiar de 2%. São sessões do mesmo host/dia, sem comprovar
independência ou controle térmico. LARGE PolyBench tem somente duas sessões.

O [corpus científico](../results/publication/automation_corpus_linux_2026-11-05/report.json)
usa GCC 13.3.0 comum nos braços original, OpenMP gerado e autopar. Nas oito
DOALL grandes, pipeline/GCC tiveram ganhos recomendados de 1,114–1,898× e
1,117–1,816×; reduções precisam de discussão separada pela reassociação.
GCC SELECTED em 13/14 inclui três recomendações de 1T, sem significar treze
programas paralelizados. O pipeline manteve sequencial em 12/14 entradas
pequenas; as duas seleções restantes têm ICs incluindo 1. Nada disso é ganho
da LLM. ICs são condicionais, e o corpus é autoral.

A [matriz histórica](../results/consolidated/REPORT.md), com 22 campanhas,
continua preservada. Suas lacunas de ambiente/contrato não são preenchidas
retroativamente. O [roteiro M5](publication/MAC_EXECUTION.md) prepara a nova
execução, sem substituir medições reais. Linux/M5 será comparação de plataformas
completas, sem efeito isolado da quantidade de núcleos.

## 6. Redação, defesa e pendências externas

A [auditoria editorial](publication/EDITORIAL_AUDIT.md) corrige a promessa do
título, a pergunta sobre o Coordinator e inconsistências entre protocolos.
A [revisão bibliográfica dirigida](publication/RELATED_WORK.md) posiciona
ParEval, OMPar, P4OMP e RepoOMP, sem alegar reprodução quantitativa desses sistemas.

A [nova monografia](monografia/REVISAO_PUBLICACAO.md), o
[rascunho de artigo](publication/ARTICLE_DRAFT.md) e o
[novo roteiro de defesa](defesa/SLIDES_PUBLICACAO.md) usam arquivos separados.
Os resultados Linux e heldout têm arquivos finais, e a bateria final passou.
As novas exportações foram reabertas e conferidas: monografia Word com 22 tabelas/19 imagens,
PDF com 70 páginas; artigo Word com nove tabelas/quatro imagens, PDF com 23
páginas; PPTX com vinte slides e vinte notas. Gráficos e páginas representativas
dos PDFs foram inspecionados. O manifesto de escrita confere 24 arquivos.
A revisão anterior
multiplataforma Word/PDF e a defesa histórica foram preservadas; o PDF anterior
tem 47 páginas, 13 tabelas e 15 imagens, sem inspeção nativa do layout Office.

A incorporação editorial e a exportação Linux estão concluídas. Detalhes e
comandos estão em [publication/VALIDATION.md](publication/VALIDATION.md).
Continuam externos à execução Linux: coleta equivalente M5, modelo institucional
completo autenticado, conferência nativa Word/PowerPoint, informações da banca,
revisão humana independente e aprovação editorial/acadêmica. O usuário autorizou
commit/push nesta sessão; a operação realizada deve ser registrada ao encerrar.
Essa autorização não é submissão de artigo, merge ou aprovação acadêmica.
