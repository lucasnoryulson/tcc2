# TCC2 — Transferência de contexto do ChatGPT para Codex

**Data desta transferência:** 3 de novembro de 2026  
**Repositório GitHub:** https://github.com/lucasnoryulson/tcc2  
**Branch consultada:** `main` (a situação pode mudar; sempre consulte o Git local)  
**Natureza:** síntese da conversa, não transcrição integral. Algumas pendências estão documentadas com base em relatórios e conversas anteriores; valide tudo no checkout atual.

## 1. Tema e objetivo

- **Título:** Sistemas multiagentes para reestruturação autônoma de códigos.
- **Subtítulo:** Análise de dependências, paralelização automática com OpenMP e otimização de desempenho.
- Objetivo de pesquisa: avaliar um sistema híbrido que analisa dependências no código, classifica padrões de paralelismo, planeja/gera transformações, compila, testa corretude, mede desempenho e seleciona uma configuração; um Coordinator baseado em LLM interpreta evidências estruturadas para decidir ações.
- O sistema **não** deve depender da LLM para inventar métricas, configurações ou alegar corretude. Gates determinísticos decidem a admissibilidade.

## 2. Arquitetura conhecida

Fluxo conceitual:

1. Static Analyzer (AST Clang): loops, iteradores, atualizações e acessos.
2. Dependence Analyzer: dependências e acessos deslocados.
3. Pattern Classifier: DOALL, REDUCTION, STENCIL, WAVEFRONT/DOACROSS, MIXED.
4. Strategy Planner / Code Transformer: estratégia e arquivo candidato OpenMP; o Transformer não suporta todos os padrões automaticamente.
5. Compile + Correctness Gate: compilação e avaliação numérica.
6. Performance Gate / Performance Selector / Autotuning: medição, comparação, near-tie, política de recursos.
7. Context Builder / Coordinator baseado em LLM: `ACCEPT`, `RETUNE`, `MODIFY`, `REJECT` e `next_action`.
8. **Candidate Promotion Executor**: pendência principal; transforma a decisão `ACCEPT → PROMOTE_CANDIDATE` em código paralelo final e manifesto auditável.

Arquivos observados no `main` durante a conversa:

- `agents/coordinator_agent.py`: Coordinator v0.2. O CLI lê contexto JSON, chama Ollama e grava JSON com `schema: tcc2-coordinator-decision`, `version: 0.2` e `decision` aninhado.
- `agents/context_builder.py`: cria contexto com `source.candidate_file`, `source.candidate_code` e `performance.selection`. Observado `validation.correctness_gate = "PASS"` codificado diretamente. Isso não é evidência suficiente para publicação.
- `analysis/performance_selector.py`: v0.2, seleciona configurações com `status`, `parallel_status`, `recommended`, `near_tie_candidates`, `next_action`, métricas separadas. Não traz necessariamente ID de candidato/identidade dos bytes medidos.
- `analysis/autotuning_selector.py`: seleção multidimensional.
- `analysis/code_transformer.py`: implementações de transformação; cobertura parcial.
- `scripts/compile_correctness_gate.py`: gate de compilação e corretude, usado via CLI com `--sequential`, `--candidate`, `--driver`, `--build-dir`, `--compiler`, `--threads`; retorna exit code 0 quando PASS, diferente de 0 quando FAIL. Verificar compatibilidade da toolchain local.
- `scripts/performance_gate.py`: produz CSV de medições; verifique sua semântica de FAIL e código de saída, não presuma que imprimir FAIL significa exit code != 0.
- `scripts/test_coordinator_v02_regression.py`, `scripts/test_performance_selector_v02_regression.py` e outros testes existentes.
- `generated/dot_product_openmp.c` e `analysis/fixtures/dot_driver.c` para integração inicial.
- `results/nussinov-auto/experiment_results.csv`: resultados experimentais, não é necessariamente saída de promoção.

**IMPORTANTE sobre implementação anterior:** o ChatGPT preparou um patch e arquivos de exemplo para Candidate Promotion Executor, mas não conseguiu gravar no GitHub (erro 403 de permissões da integração). **Não presuma que esses arquivos existem no repositório.** Os testes citados eram locais/de protótipo e não demonstram integração real do TCC. Confirme a implementação a partir do estado real do checkout.

## 3. Resultados científicos anteriores

- Casos cobertos estruturalmente: GEMM (DOALL), Dot Product (REDUCTION), Jacobi-2D (STENCIL), Nussinov (WAVEFRONT/DOACROSS), Covariance (MIXED).
- Nussinov, em uma campanha: melhor OpenMP 4 threads; mediana 0,209073 s; speedup **end-to-end** ~4,106× e redução de runtime ~75,65%. Documentação anterior distinguiu ganho da transformação e escalabilidade real; não trate 4,106/4 como eficiência paralela isolada.
- Wavefront sintético: houve caso de transformação correta porém sem escalabilidade, seguido de modificação tiled e autotuning com ganho multicore reportado em campanha específica.
- Resultados de Xeon e Apple M5 devem ser comparados preferencialmente por tendências e valores relativos, sob protocolos compatíveis. Não misture medições de campanhas diferentes como amostras pareadas.

## 4. Próxima tarefa aprovada — Candidate Promotion Executor

Implementar uma **etapa final determinística e auditável** de promoção, sem aumentar desnecessariamente a arquitetura.

### Comportamento desejado

- Receber um JSON de decisão do Coordinator, seleção/medição determinística, caminho do código candidato, caminho do original, driver de corretude, toolchain e destino.
- Autorizar apenas `decision.decision == "ACCEPT"` **e** `decision.next_action == "PROMOTE_CANDIDATE"`; recusar todos os outros estados.
- Confirmar que a seleção está em status admissível (`SELECTED`, `PARALLEL_SUCCESS` quando exigido), que há ganho medido apropriado e que o número de threads e demais dimensões correspondem à configuração medida — não aos palpites da LLM.
- Amarrar a decisão ao **candidato exato**. Ideal: `candidate_id`, SHA-256 do conteúdo validado, referência a artefatos de corretude e performance, ID da campanha e configuração. Uma nova execução do gate pode verificar corretude atual, mas **não comprova que o benchmark histórico foi feito com os mesmos bytes**. Resolva essa lacuna com proveniência verificável.
- Evitar path traversal, sobrescritas silenciosas, promoção duplicada indevida e inconsistências entre arquivo validado e arquivo copiado. Preferir cópia atômica ou staging + publish quando viável.
- Gerar `results/promoted/<identificador>/parallel.c`, `manifest.json` e logs relevantes, com versão, hashes, configuração, referências de validação/benchmark, origem e momento da promoção.
- Se falhar qualquer gate ou divergência, não deixar artefato final aparentemente aprovado.
- Integrar ao ponto final do pipeline **após validação**; não criar um fluxo paralelo que ignora Coordinator/Selector.
- Criar testes unitários e um teste de integração real com Dot Product usando `analysis/fixtures/dot_driver.c` (ou o driver correto após inspeção).
- Não incluir comandos `git push`, mudanças no `main` ou merge sem aprovação explícita.

### Questão adicional de consistência

No `coordinator_agent.py` v0.2, a função `enrich_deterministic_configuration` foi observada preenchendo `recommended_configuration` para mais de uma dimensão, mas retornando `None` no tuning unidimensional (`threads`). Isso é uma pendência anterior e pode impedir a promoção inequívoca. Corrija com cuidado e mantenha regressão.

### Critérios de aceite

1. Arquivo promovido corresponde byte a byte ao candidato autorizado.
2. Configuração final é uma configuração efetivamente medida.
3. Corretude e ganho de desempenho são comprovados por evidências vinculadas ao arquivo.
4. Um candidato incorreto/alterado ou uma decisão `RETUNE/MODIFY/REJECT` não promove.
5. Manifesto permite auditoria e reprodução do teste.
6. Integração real com pelo menos um kernel funciona e testes relevantes passam.
7. Diferenças entre resultados de teste local e validação em ambiente original estão explicitadas.

## 5. Sequência de trabalho recomendada

- Verificar Git status e a branch, e criar `feat/candidate-promotion-executor`.
- Ler os módulos originais e formatos JSON reais, principalmente `Coordinator`, `Selector`, `Context Builder`, gates e scripts de execução.
- Propor o menor contrato de evidência que identifica o candidato e liga corretude/performance às mesmas fontes.
- Implementar executor e integração incremental com testes.
- Executar regressões existentes, teste real de compilação/validação Dot Product e, se possível, reprodução do Nussinov.
- Resumir alterações, comandos e evidências; não declarar o TCC concluído apenas pela promoção.

## 6. Pendências seguintes (fora do escopo inicial)

- Correção da propagação de `recommended_configuration` em tuning unidimensional.
- Integrar regressões determinísticas ao CI/GitHub Actions.
- Congelar arquitetura, limpar snapshots/backups/outputs e documentar reprodutibilidade.
- Fechar matriz experimental e ablações essenciais contra baseline sem LLM.
- Gráficos finais, metodologia, resultados, discussão, limitações e apresentação acadêmica.

## 7. Como se comunicar com o usuário

Responder em português, ser analítico e direto, distinguir evidência de hipótese, e informar o que foi realmente alterado/testado. Se o código não corresponder ao resumo acima, explique as diferenças sem presumir que o resumo é mais recente.
