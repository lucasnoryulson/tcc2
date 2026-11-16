# Continuidade — fechamento Linux em 6 de novembro de 2026

Branch `feat/publication-strengthening-2026-11-05`, base b9e252d. O usuário
pediu executar as melhorias de publicabilidade e corrigir o TCC. Depois
autorizou explicitamente commit e push desta branch. Merge, submissão e
mensagens a terceiros não foram solicitados. O checkpoint intermediário
foi preservado em `WORKLOG_CHECKPOINT_2026-11-05.md`; suas tarefas ativas
são históricas e os estados abaixo o substituem.

## 1. Pipeline e extensão

O contrato `standalone-ast-v2` aceita reduções escalares e DOALL restrito.
O Transformer reanalisa a fonte atual e verifica offsets/precondições, sem
confiar em um plano JSON editável. Preprocessamento, atributos, shadowing,
CRLF/VT/FF e campos desconhecidos receberam recusas/testes.

O corpus executou geração/gates reais; a promoção DOALL em unittest usa
Coordinator e tempos simulados, explicitamente. A tentativa integrada real
`results/publication/doall_pipeline_linux_2026-11-06/run-jia507x_/` passou por
transformação, corretude em 1/2/4T, tempos reais e seleção de 2T, mas Qwen
excedeu 180 s: FAILED em 182,749 s, sem decisão/promoção. Uma única tentativa,
sem retry. Os modelos foram descarregados e Ollama ps ficou vazio antes de
outras cargas. O Dot/redução promovido historicamente permanece preservado.

## 2. Validação

123 unittests em 23,130 s, zero falhas/skips. Seis scripts de regressão:
23 casos PASS; isolamento estático PASS; três bash-n e duas recusas de
sobrescrita PASS. O harness da primeira checagem shell esperava RC2 nos
dois wrappers, mas o diagnóstico recusa por FileExistsError/RC1; expectativa
corrigida, registro inicial preservado. Testes e logs anteriores não apagados.

O verificador de diagnósticos reconstrói agenda, campos derivados, prompts,
respostas brutas, metadados, scores e agregados. Não altera a implementação
congelada do estudo. A contraprova FP pré-declarada reutilizou vector_sum:
sequencial e 1T zero, 2T solicitado -inf, gate FAIL. É uma execução funcional
suplementar, fora de 28 fontes/2.940 observações e sem medição de workers.
Não retunar entrada para substituir essa falha.

Os 4.416 arquivos históricos acompanhados conservaram os hashes. Verificação
em `results/publication/validation_linux_2026-11-05/`; comandos e limites em
[VALIDATION.md](VALIDATION.md). Os cinco artefatos da contraprova sob build/
precisam ser versionados explicitamente apesar da regra geral de .gitignore.

## 3. Automação e corpus científico

`results/publication/automation_corpus_linux_2026-11-05/` está COMPLETE e
VERIFIED. GCC13.3.0 comum aos três braços: original O3, gerado O3/OpenMP e
original O3/ftree-parallelize-loops=p. Driver compilado uma vez e separado.
28 fontes autorais: oito DOALL/seis reduções aceitas e 14 recusas conforme
contrato; zero falsos aceites/recusas/erros; 28 pares fonte × entrada PASS.
196 configurações, 2.940 observações externas, 588 aquecimentos,15/3 seed2026.
Chamadas internas amortizam tempo, sem aumentar n. DOALL valida cada elemento.

Razões geométricas descritivas GCC/pipeline recomendado, entrada grande:
DOALL1,0005× (8fontes),RED2,0487×(6),conjunto1,3602×(14). Não são superioridade
geral: reassociação FP difere entre braços e o corpus é curado. Inspeção de
objetos/logs identificou parallelizing e bytes GOMP_parallel nos32objetos
DOALL GCCp2/p4, sem os dois indícios nos24RED; isso não mede workers.

## 4. LLM: diagnóstico encerrado

Qwen e Llama heldout encerrados: 24 chamadas reais/36 slots por modelo,
12 vistas sobre três famílias, uma repetição. Total48chamadas,47JSONválidos,
zero combinações causa+ação conforme rubrica em cada braço. Regras implementam
a própria rubrica e não são verdade humana independente. Qwen tem um INVALID
por length384; não houve timeout/NOT_RUN no heldout. Llama COMPLETE. Tempo
mediano Qwen41,536/39,747s; Llama75,712/64,194s, completo/sem análise.

Claims Qwen90/98 sem vínculo exato (IDs/campos); Llama46/94 (campos/formato).
Não chamar essas frações de falsidade factual. A ablação só muda dois casos,
remove toda evidência e mantém o gabarito original, penalizando respostas
prudentes de Llama. Schema via format sem explicitação no prompt é confound,
não causa comprovada nem autorização para retunar heldout conhecido.

Catálogo SHA628822fb6da6617253c799d8e9eae3e90837ddc056fe95ff7beab731d04fcd38;
harness SHA75658d6c8eba7489a6a3e6826b630e7c0d2a1ac1c0c44a7d9e6889419477cb9c.
Permanecem congelados. Preflight d01 separado. Detalhes: DIAGNOSTIC_RESULTS.md.

## 5. Sessões e M5

S2 completa acrescentou900observações/180aquecimentos/60corretudesPASS;
S3 predefinida MEDIUM+Dots acrescentou570/114/38PASS. Fonte congelada b9e252d,
PolyBench3e872547cef7e5c9909422ef1e6af03cf4e56072. Não são tempos da extensão
DOALL. Comparações verificadas:60cfgS1/S2,38cfgS1/S2/S3, sem juntar amostras.
Escolhas repetidas15/16 e9/10. DotC++grande2T→4T→2T atravessa quase empate2%.
São sessões do mesmo host/dia; não há frequência/temperatura controladas.

Matriz nova M5 NÃO executada. MAC_EXECUTION.md e wrappers preparam coleta
compatível, com diretórios novos e reconstrução de binários/venv. Não preencher
Mac com dados Linux ou acervo histórico. No Mac, usar GCC real se disponível
para braço GCC, senão registrar sua ausência; compilador/runtime são confounds.

## 6. Texto e exportações

Monografia nova em docs/monografia/REVISAO_PUBLICACAO.{md,docx,pdf};
artigo em ARTICLE_DRAFT.{md,docx,pdf}; defesa em
SLIDES_PUBLICACAO.md/DEFESA_PUBLICACAO.pptx. Originais preservados. Texto
revisa título, perguntas, trabalhos próximos, métodos, resultados, discussão
e conclusões; distingue geração determinística, variantes manuais e LLM.
Sem marcadores pendentes. Cinco figuras novas em PNG/SVG/PDF.

Monografia70p/22tabelas/19imagens; artigo23p/9tabelas/4imagens;
defesa20slides/20notas. Reabertura Office e checks PDF PASS; manifesto24arquivos
conferido. Figuras e páginas representativas inspecionadas; renders salvos.
ReportLab é revisão de conteúdo, sem aprovação de layout nativo/institucional.

Faltam externamente: execução M5 e comparação equivalente, revisão humana dos
rótulos/corpus, dados institucionais não fornecidos, Word/PowerPoint nativo,
orientação/veículo e aprovação acadêmica. O material está mais bem sustentado;
não há garantia de publicação. Fechar com commit/push autorizado e pacote novo
para Mac; conferir SHA do branch remoto e árvore limpa. Não fazer merge.
