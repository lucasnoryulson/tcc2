# Continuidade da etapa de fortalecimento

Branch `feat/publication-strengthening-2026-11-05`, base b9e252d. O usuário
pediu executar as melhorias e corrigir o TCC, com continuidade autônoma. Não há
autorização de push, merge, submissão ou mensagens a terceiros.

## Preservação

O mapa `/tmp/tcc2-before-publication-strengthening.json` cobre 4.416 arquivos
anteriores de resultados, monografia e defesa. Conferir os hashes ao fim.
Não reexportar originais. A revisão atual é NOVA:
`docs/monografia/REVISAO_PUBLICACAO.md` e `docs/publication/ARTICLE_DRAFT.md`.
A capa/Office antigos e o pacote Mac p15w3 anterior permanecem preservados.

## Estudos realmente concluídos

- Sessão S2 completa, fonte congelada b9e252d: 60 configurações, 900 medições,
  180 aquecimentos, 60 validações. Diretório
  `results/publication/scaling_linux_session02_2026-11-05/`; log de execução
  `/tmp/tcc2-publication-session02.log`; janela 18:57:47–19:54:56 UTC.
- S3 MEDIUM e ambos os Dot: 38 configurações, 570 medições, 114 aquecimentos,
  38 validações. Diretório `results/publication/scaling_linux_session03_medium_2026-11-05/`;
  log `/tmp/tcc2-publication-session03.log`; 20:04:18–20:06:24 UTC.
- As duas novas análises e comparações S1/S2 (60 configurações) e S1/S2/S3
  (38) passaram. Diretórios de análise/comparação têm nomes próprios em
  `results/publication/`. Fontes/compilador/plataforma/dimensões/flags conferidos,
  sem juntar observações brutas. `REPEATABILITY_RESULTS.md` relata escolhas
  15/16 e 9/10 repetidas, Dot C++ grande 2T→4T→2T, variações de medianas e limites.
- Corpus científico `results/publication/automation_corpus_linux_2026-11-05/`:
  COMPLETE e verificado. GCC13.3.0 comum, 28 fontes autorais, 14 aceitações e
  14 recusas conforme contrato, zero falsos aceites/recusas/erros. 28 pares
  positivos fonte × entrada PASS, 196 configurações, 2.940 amostras e 588
  aquecimentos. Coletor1.1, A/8 para cobrir ramo superior de clamp. Log
  `/tmp/tcc2-automation-corpus-science.log`. O arquivo não deve ser modificado.
- Inspeção derivada dos objetos/logs em
  `results/publication/compiler_mechanisms_linux_2026-11-05/`: 32 DOALL GCC p2/p4
  com mensagem parallelizing e bytes GOMP_parallel; 24 reduções sem os dois
  indícios. Não é medida de workers. Comparar FP com cuidado por reassociação.
- Qwen heldout concluído: `diagnostics_qwen_heldout_linux_2026-11-05/`, 24 chamadas,
  36 slots, COMPLETE_WITH_FAILURES, um INVALID por length384 (não timeout).
  Full11/12JSON e ablação12/12; 0/12 causa+ação em ambos frente à rubrica autoral.
  90/98 claims sem vínculo exato =72 IDs ausentes+18 campos ausentes; não chamar
  isso de 91,8% falsidade factual. Documento `DIAGNOSTIC_RESULTS.md` tem análise.
  Qwen foi descarregado; ps confirmado vazio antes do modelo seguinte.

## Execução ATIVA neste checkpoint

Llama3.1:8b heldout está rodando na sessão exec **58594**, iniciado 20:30:42 UTC.
Log `/tmp/tcc2-diagnostics-llama-heldout.log` e resultados em
`results/publication/diagnostics_llama_heldout_linux_2026-11-05/`.
Na última consulta, posição11/36 OK; primeira chamada179,5s. Não interromper,
retunar, repetir seletivamente ou sobrepor testes, renderizações ou benchmarks.
Configuração congelada: 12 vistas heldout, 1 repetição, contexto4096,
num_predict384, timeout180, temp0, seed2026. O catálogo e
`scripts/evaluate_diagnostics.py` NÃO foram alterados depois do congelamento;
SHA do harness no plano é 75658d6c8eba7489a6a3e6826b630e7c0d2a1ac1c0c44a7d9e6889419477cb9c.

Timeout é terminal e deixa restantes NOT_RUN; conservar a falha. Ollama pode
continuar após desconexão: descarregar o modelo da tarefa e conferir ps vazio
antes de iniciar outra carga. Metadados PS100%CPU/context4096 estão em
`results/publication/diagnostics_runtime_linux_2026-11-05/`.

## Implementação e validação técnica

Contrato AST `standalone-ast-v2`: RED + DOALL conservadores; reanálise da fonte,
restrições de expressão pura/restrict, offsets CRLF, VT/FF, atributos, headers,
pré-processamento, shadowing e plano falso. Corpus tem gates por elemento e
baseline GCC com driver compilado uma vez. Verificador do corpus reconstrói
coverage/core summary/selection e vínculo amostra-binário. COVERAGE_MISMATCH
completo permanece analisável, sem premiar erro como recusa.

121 testes passaram após essas correções em22,669s:
`validation_linux_2026-11-05/unittest_after_archive_review.log`.
Depois foram acrescentados2 testes AINDA NÃO EXECUTADOS: integração DOALL com
compilação/revalidação reais e Coordinator/tempos simulados; verificação e
adulteração de resultados diagnósticos. Total esperado123, conferir resultado
real após inferências. Logs de falhas e preflights anteriores estão preservados
em `PREFLIGHTS.md`, inclusive a classificação incorreta de14 recusas quando o
CLI emitia mensagem em stdout e o coletor procurava só stderr.

O novo `verify_diagnostics` em `report_publication.py` confere fonte/catalog,
schedule, prompts, respostas, rescoring e agregados; não muda o harness congelado.
Ainda requer teste e execução real. `build_publication_material.py` o reutiliza.

## Redação e exportação

Corpus e sessões já foram incorporados na monografia/artigo. Resumo/abstract
foram reescritos, mas contêm marcadores INSERIR_SINTESE_DIAGNOSTICO_PT/EN/ARTIGO.
Blocos INSERIR_DIAGNOSTICO_RESULTADOS e INSERIR_VALIDACAO_EXTENSAO ainda precisam
ser preenchidos. Conclusões, quadro de ampliações do artigo, apêndice final,
README/STATUS e slides precisam da passada final para remover futuros já
concluídos. Os slides têm corpus/sessões atuais e diagnóstico ainda pendente.

Gerador novo preparado, SEM EXPORTAÇÃO AINDA: Word/PDF monografia, Word/PDF
artigo, nova capa pública e PPTX. Figuras planejadas em figures_publication:
coverage total, escolhas grandes com IC, curvas affine_vector/inner_product,
DOALL antes/depois, diagnóstico. `requirements-publication.txt` fixa os pacotes
já instalados. PDFs ReportLab são revisão de conteúdo, não layout Office nativo.

Limitação de interpretação: SCHEMA foi passado em format, sem enumerar opções
no texto das mensagens. A documentação Ollama recomenda também explicitá-lo no
prompt; não é prova da causa dos erros. Não alterar prompts após heldout.
A ablação só muda dois casos, esvazia sua evidência e mantém a anotação original;
concordância não equivale a adequação humana da abstenção.

## Restante, nesta ordem

1. Concluir Llama; preservar estados/falhas e descarregar/conferir ausência de
   geração antes de outras cargas. Completar DIAGNOSTIC_RESULTS.md.
2. Executar suplemento funcional pré-declarado NUMERICAL_LIMIT_PROTOCOL.md,
   reutilizando original/candidato vector_sum arquivados e o novo
   adversarial_sum_driver.c. N1026, valores ±1e308, threads1/2: hipótese de
   original finito e parcial paralelo não finito. Executar uma vez, conservar
   qualquer resultado e não somar à campanha científica.
3. Executar demonstração DOALL no run_pipeline com drivers reais fornecidos,
   Qwen, timeout180, diretórios novos. Não presumir PROMOTED nem retry de
   recusa/timeout. Seus5 tempos/config são demonstração técnica separada.
4. Rodar bateria final123, seis scripts de regressão, isolamento estático,
   shell e verificadores. Nada concorrente às inferências/medições.
5. Gerar RESULTS.md com report_publication.py (args corpus,2diagnostics,
   sessão3way). Preencher texto/abstract/conclusões/slides e estados1–6 com dados.
6. Exportar via build/analysis-venv/bin/python scripts/build_publication_material.py;
   usar MPLCONFIGDIR em /tmp para evitar cache fora da sandbox. Reabrir
   Office/PDF, conferir páginas e figuras visualmente. Não reexportar originais.
7. Auditar hashes4.416, git diff, manifestos finais e novo pacote Mac (nome
   diferente do anterior), sem push/merge. Congelar alterações em commit local
   conforme autorização anterior do usuário, se adequado.

Mac equivalente, revisão humana independente, campos institucionais não
fornecidos, inspeção Office nativa e aprovação acadêmica permanecem externos.
Não declarar essas etapas concluídas por haver scripts ou documentos de revisão.
