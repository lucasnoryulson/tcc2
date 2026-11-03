# TCC2 — contexto atualizado para continuidade no Codex

**Atualização: 03/11/2026, após implementação, avaliação local e preparação da redação.**
Autor: **Lucas Nory Ulson**. Projeto: TCC2 de Ciência da Computação, PUCRS.
Título: *Sistemas Multiagentes para Reestruturação Autônoma de Códigos*.
Subtítulo: análise de dependências, paralelização com OpenMP e otimização de desempenho.
Repositório informado: https://github.com/lucasnoryulson/tcc2.

Este documento **substitui o estado de implementação do contexto inicial**.
A versão antiga foi preservada em [CONTEXTO_INICIAL_CHATGPT.md](CONTEXTO_INICIAL_CHATGPT.md).
Ela dizia que faltava o executor de promoção: essa pendência foi implementada.
Esta transferência é uma síntese verificável, não uma transcrição integral.
Leia também [CONVERSA_E_DECISOES.md](CONVERSA_E_DECISOES.md) e
[RETOMAR_NO_MAC.md](../RETOMAR_NO_MAC.md).

## Situação do checkout na transferência

- Linux: `/home/liswsz220-01/Desktop/tcc/tcc2`; a pasta pai não é o repositório.
- Branch observada: `feat/gate-contracts`; commit `c42b16d` (`saving`).
- A árvore estava limpa antes desta atualização de contexto. As novas alterações
  de documentação não foram commitadas nem enviadas ao remoto nesta tarefa.
- Não presumir sincronização com GitHub. Conferir Git no Mac e preservar trabalho local.
- O usuário estava sem acesso ao Mac. Quer concluir o TCC e tem interesse em publicar,
  mas não tem tempo agora para discutir orientador/veículo. A prioridade autorizada
  é finalizar implementação, evidências e material acadêmico, sem ampliar a arquitetura.

## Estado pelos seis itens originais

**Manter esta numeração em respostas futuras.** O bloco inicialmente citado tinha
um primeiro tópico sem número; o acompanhamento consolidou os seis itens abaixo.

| Item | Feito | Falta |
|---|---|---|
| **1. Pipeline até o resultado final** | Runner integrado e executor de promoção com proveniência, revalidação e publicação atômica; integração técnica testada | Confirmar uma execução completa com inferência real concluída no ambiente alvo; eventual promoção depende dos gates e da decisão |
| **2. Lacunas de validação e configuração** | PASS fixo removido, configuração somente threads corrigida, FAIL do desempenho tratado, cadeia de evidências e recusas testadas | Verificar compatibilidade da toolchain no Mac sem relaxar o contrato |
| **3. Delimitação da automação** | Recorte documentado e incorporado à base da monografia/slides | Preservá-lo na versão final de entrega |
| **4. Avaliação científica dos agentes** | Harness determinístico/Coordinator/ablação, baseline real e diagnóstico de timeout | Rodar a campanha LLM, analisar decisões/custo/falhas e escrever a discussão |
| **5. Experimentos e reprodução** | Catálogo, matriz, amostras, gráficos, documentação e proteção dos históricos | Selecionar/conservar campanhas finais, confirmar ou declarar lacunas de metadados e atualizar a consolidação |
| **6. Monografia e defesa** | Três Word lidos, base Word/Markdown, PowerPoint de 16 slides com notas, bibliografia e demonstração | Integrar resultados finais, adaptar ao modelo institucional, conferir Office/PDF e ensaiar |

**Não responder que só falta apertar os comandos no Mac.** A coleta no hardware
alvo é a próxima ação; ainda há análise, incorporação ao texto e fechamento da defesa.
A base preparada é rascunho, não uma monografia final aprovada.

## Arquitetura implementada e contratos

Fluxo: Static Analyzer (AST Clang) → Dependence Analyzer → Pattern Classifier →
Strategy Planner → Code Transformer → Compile/Correctness Gate → Performance
Gate/Selector → Context Builder → Coordinator via Ollama → Promotion Executor.
O runner é Python/subprocess/JSON. Há papéis funcionais chamados agentes, em sua
maioria determinísticos, com **uma LLM no Coordinator**. Não há LangGraph, motor
BDI, múltiplas LLMs conversando, geração geral de código pela LLM, GPU ou loop de
reparo autônomo no caminho avaliado. RETUNE/MODIFY/REJECT interrompem o runner.

Arquivos centrais:

- `analysis/artifact_provenance.py`: snapshots, SHA-256, IDs de candidato/campanha,
  identificação do compilador, validação dos relatórios, recomputação das
  medições/seleção e `parallel_selection`, regra compartilhada de admissão.
- `scripts/compile_correctness_gate.py`: relatório v0.2, entradas congeladas,
  compilação real, resultado numérico finito por configuração, exit code de falha.
- `scripts/performance_gate.py`: relatório v0.1 vinculado à corretude, cinco
  amostras externas/configuração, CSV verificável. Ausência de ganho conserva
  medições mas retorna 1; não usar esse FAIL como sucesso de promoção.
- `analysis/performance_selector.py`: política de quase empate de 2%, vinculação
  ao relatório de desempenho; CSV histórico sem vínculo serve só para análise.
- `agents/context_builder.py`: v0.3, consome evidências reais e bytes congelados;
  não preenche PASS sem validação.
- `agents/coordinator_agent.py`: decisões v0.2 vinculadas ao contexto/campanha;
  enriquecimento de configuração funciona com somente threads. A LLM interpreta
  evidências; não pode inventar uma configuração admissível.
- `scripts/promote_candidate.py`: só ACCEPT + PROMOTE_CANDIDATE; exige seleção
  paralela admissível, ganho contra sequencial **e** OpenMP 1T, configuração
  medida com pelo menos 2T, hashes íntegros. Recompila e repete a corretude;
  staging/rename atômico, reserva exclusiva, sem sobrescrever promoção duplicada.
- `scripts/run_pipeline.py`: CLI integrado, diretório exclusivo, logs/tempos/
  summary.json. `--prepare-only` termina PREPARED antes da LLM e da promoção.
- Bundle: `parallel.c`, `manifest.json`, `evidence/` e revalidação. Uma reserva
  `.lock` pode sobrar após encerramento abrupto; inspecionar antes de remover.

Flags: sequencial `-O3`; candidato `-O3 -fopenmp`. Ambiente OpenMP:
`OMP_DYNAMIC=FALSE`, `OMP_PROC_BIND=TRUE`, `OMP_PLACES=cores`.
Corretude do exemplo: resultado escalar, tolerâncias relativas 1e-9/absolutas
1e-12, driver N=1.000.000. Não é prova formal, teste universal de entradas nem
verificação de ausência de races. Headers/bibliotecas/toolchain completa não
são integralmente capturados. Hash é integridade local, não assinatura externa.

## Recorte real da automação — item 3

| Caso | Cobertura |
|---|---|
| Dot Product / REDUCTION | Geração determinística de redução escalar independente e pipeline integrado |
| GEMM / DOALL | Análises e variante OpenMP manual |
| Jacobi-2D / STENCIL | Análises e variantes manual/tiled |
| Covariance / MIXED | Análises e variante manual |
| Nussinov / WAVEFRONT | Variantes manuais e transformações determinísticas adaptativas específicas sobre uma base OpenMP existente; não geração universal a partir do sequencial pelo novo runner |
| Wavefront sintético | Variantes manual/tiled e autotuning; sem loop autônomo de recuperação no runner atual |

Classificação de vários padrões não significa geração automática completa de
cada um. Não atribuir ganhos das variantes manuais ou do transformador à LLM.

## Avaliação do Coordinator — item 4

`scripts/evaluate_coordinator.py` prepara dois tamanhos reais de Dot Product:
N=10.000.000/100 chamadas internas e N=1.024/10.000 chamadas internas. Cinco
medições externas/configuração. Três braços reutilizam **o mesmo candidato e
as mesmas medições**: `deterministic`, `coordinator` e
`coordinator_without_analysis`. A ablação remove análises estruturadas do prompt,
não os gates; verifica-se que o prompt mudou. Ordem embaralhada, seed 2026,
três repetições por padrão, temperatura zero, uma chamada por tentativa LLM.

Conserva prompts exatos, schema, hashes, decisões brutas/enriquecidas, tokens,
latência, falhas, metadados Ollama e resultados JSON/CSV/Markdown. Mede concordância
com a política, aceitação/veto, custo e oportunidades perdidas; não há verdade
independente para qualidade semântica, busca de novos candidatos ou comparação
com geração monolítica. Se dois braços aceitam a mesma configuração, seu speedup
é igual neste desenho. Timeouts entram no denominador, sem tentativas silenciosas.
Falha/recusa usa sequencial como fallback na avaliação. Não inclui promoção no
custo desse estudo. `COMPLETE` não significa benefício; BASELINE_ONLY e INCOMPLETE
mantêm os seus limites. Dois tamanhos de um kernel não generalizam para cinco padrões.

Evidência Linux:

- Baseline real: `build/validation/step4/final/evaluation-k3nql7bl/`.
  Dot grande: sequencial 0,01060734094 s, OpenMP1 0,01097854059 s,
  OpenMP2 0,00890488488 s. Ganho total 1,19118×; escalabilidade 1,23287×.
  Dot pequeno: sequencial 1,183359e-6 s, OpenMP1 1,600409e-6 s,
  OpenMP2 1,592121e-6 s; nenhuma configuração paralela admitida.
- Diagnóstico LLM real: `build/validation/step4/live/evaluation-c7s6idmh/`.
  Quatro chamadas qwen2.5:3b, timeout de 30 s cada, todas expiradas; INCOMPLETE.
  Outras tentativas do pipeline expiraram em 120 e 300 s.
  Isso não mede a qualidade das decisões nem prova inutilidade do modelo.
- Cópias versionadas dos resumos: `results/coordinator_evaluation/local_2026-11-03/`.
  Os artefatos completos estão no build ignorado pelo Git.
- Integração antiga em `build/validation/final/` usou Coordinator **simulado**;
  promoção/revalidação técnica não demonstram sucesso de uma inferência real.
- Modelo observado: qwen2.5:3b ID `357c53fb659c`; havia também llama3.1:8b e
  phi3:mini. Conferir o instalado no Mac; não assumir IDs idênticos.
- Cliente não fixa janela de contexto. Conferir configuração efetiva e truncamento.
  Geração pode continuar no servidor após timeout; evitar campanhas sobrepostas.

Detalhes: [protocolo](../../docs/COORDINATOR_EVALUATION.md) e
[registro local](../../docs/COORDINATOR_EVALUATION_LOCAL.md).

## Consolidação — item 5

`scripts/consolidate_experiments.py` + `docs/experiment_catalog.json` selecionam
explicitamente 19 campanhas: 17 históricas e 2 medições locais verificadas.
Inventário inicial de 35 CSVs, 161 configurações, 515 tempos individuais,
12 figuras (4 grupos de ambiente em SVG/PDF/PNG). Saídas em `results/consolidated/`.
O inventário encontrou oito CSVs com cabeçalho incompatível; fontes históricas
foram preservadas, não reescritas para aparentar dados limpos.

O catálogo separa receitas de flags/entrada de metadados efetivamente registrados.
`sha256_now` não prova identidade histórica do binário. Somente os gates locais
com artefatos intactos têm VERIFIED_LOCAL_GATES; em outra máquina, resumos sem
originais caem para ARCHIVED_SUMMARY_ONLY. Não editar caminhos para contornar isso.
Novas campanhas não entram automaticamente na matriz: atualizar o catálogo.

Métricas da mesma campanha/variante (e **mesmo bloco** em tiled):
`total=T_seq/T_p`; `transformação=T_seq/T_1`; `escala=T_1/T_p`;
`eficiência=(T_1/T_p)/p`. Resultados corrigidos:

- Wavefront tiled Mac, bloco64/4T: total 3,39956×, escala 2,37732×,
  eficiência 0,59433. O resumo antigo chamava 0,850 de eficiência indevidamente.
- Nussinov automático: total 4,10632×, escala 3,00529×, eficiência 0,75132.
  O hardware não está comprovado no CSV canônico: mantido desconhecido,
  apesar de o Word antigo atribuí-lo ao Mac.
- Nussinov SIMD manual: total 4,03660×, escala 3,01473×.
- Jacobi Mac: política de quase empate recomenda 7T; mais rápido era 10T.

`benchmark.py` e `autotune_wavefront.py` aceitam `--results-dir` novo; recusam
colisões de CSV. Não executar campanhas legadas simultâneas: binários continuam
compartilhados. Não é necessário repetir todas as 19 campanhas por padrão.
Submódulos estavam sem inicialização: PolyBenchC
`3e872547cef7e5c9909422ef1e6af03cf4e56072`, everythingsreduced
`fb1c1cca72eaaa660fbfdf8623e79ad2ababbc29`. Dot independente não depende deles.
Instalação/receitas/limites: [guia de reprodução](../../docs/EXPERIMENT_REPRODUCTION.md).

## Documentos e defesa — item 6

Três originais foram adicionados à pasta pai do repo e preservados:

1. `tcc_proposta(1).docx` — proposta, não texto final.
2. `Guia_TCC2_Paralelizacao_Automatica_atualizado_2026-09-02(1).docx` — guia/caderno.
3. `Resumo_Executivo_TCC2_Lucas_Ulson_Atualizado_2026-10-08.docx` — resumo executivo.

Foram confrontados com a implementação; promessas de GPU, LangGraph, codificador
LLM geral e reparo autônomo não são descritas como implementadas na revisão.
A pergunta original de superioridade sobre geração monolítica não foi respondida
pela comparação atual de decisões. Registrar a mudança de objetivo/escopo.

Materiais preparados:

- `docs/monografia/BASE_MONOGRAFIA.md` e `.docx`: resumo/abstract, introdução,
  questões R1/R2/R3, arquitetura, metodologia, resultados disponíveis, ameaças,
  discussão e conclusão delimitada; R3 explicitamente aberta.
- `docs/monografia/LEITURA_DOS_DOCUMENTOS.md`: divergências e revisões por documento.
- `docs/monografia/referencias.bib`: quatro fontes primárias conferidas
  (OpenMP5.2, AutoGen, ParEval, PolyBench). Não implica revisão sistemática ou
  conferência de toda a bibliografia antiga.
- `docs/monografia/ARQUITETURA.png`/`.svg` e `REVIEW_MANIFEST.json` com hashes.
- `docs/defesa/SLIDES.md` e `DEFESA_RASCUNHO.pptx`: 16 slides com notas, rascunho,
  previsão ajustável de 15 min, avaliação LLM pendente.
- `docs/defesa/DEMONSTRACAO.md`: preparo real, conferência de evidências, recusa
  por adulteração e caminho para execução LLM real, distinguindo simulações.
- PDFs `BASE_MONOGRAFIA_PREVIA.pdf` (12 páginas) e `DEFESA_PREVIA.pdf` (16):
  prévias de conteúdo via ReportLab, **não renderização nativa Office**.
- `scripts/build_academic_material.py`: gera Word/PPTX/diagrama/manifesto a partir
  dos Markdown, com autochecks; não gera PDFs e sobrescreve seus rascunhos.
  Incorporar edições Office às fontes antes de regenerar.

Os pacotes Office foram reabertos, imagens/tabelas/notas checadas e páginas
selecionadas das prévias inspecionadas. LibreOffice Linux só tinha Calc, sem
filtros Writer/Impress; layout nativo Word/PowerPoint **não foi verificado**.
Ambiente Python opcional instalado apenas em venv; recriar no Mac com
`requirements-analysis.txt`/`requirements-writing.txt` conforme a tarefa.

Demonstração efetivamente executada: `build/defense-demo/run-towc_fik/`, PREPARED,
PASS 1T/2T e PARALLEL_SUCCESS. Não foi incorporada como nova campanha científica.
Teste de recusa por alteração do candidato/driver/original passou. Verificações
registradas em `build/validation/step6/verification.json`.

## Verificação técnica registrada, não reexecutada nesta transferência

Última bateria técnica: **75 testes unittest + 14 casos de regressão aprovados**.
Arquivos: `test_gate_contracts.py` (26), `test_candidate_promotion.py` (14),
`test_pipeline_integration.py` (5), `test_coordinator_evaluation.py` (12),
`test_experiment_consolidation.py` (18); regressões Coordinator7,
PerformanceSelector3, Autotuning4. Usam GCC/OpenMP e Clang no Linux; parte dos
benchmarks/LLM é controlada ou simulada nos testes, claramente identificada.
No Mac, não supor que `gcc` seja GNU GCC; observar falhas e skips reais.

Havia uma falha histórica de isolamento estático ligada a caminho absoluto
`/Users/lucasulson/...` de Nussinov no Linux, não corrigida/mascarada como PASS.
Esta atualização só altera documentação/contexto; não é uma nova execução da suíte.

## Próxima ação e limites de autorização

Seguir [RETOMAR_NO_MAC.md](../RETOMAR_NO_MAC.md) e
[FECHAMENTO_TCC.md](../../docs/FECHAMENTO_TCC.md): conferir toolchain, realizar
preparo sem LLM, executar pipeline real e comparação dos três braços, conservar
artefatos/falhas, selecionar dados, atualizar texto/slides, formatar e ensaiar.
O usuário já autorizou continuar esse fechamento; não ficar pedindo confirmações
para inspeções, testes e correções reversíveis dentro desse escopo.

Não fazer push/merge/publicação nem enviar mensagens a terceiros sem instrução.
Interesse em publicação não é autorização para submeter a um veículo. Preservar
os originais e evidências. Não adicionar GPU/novos agentes/transformador universal
para preencher promessas antigas. Relatar resultados negativos honestamente.
