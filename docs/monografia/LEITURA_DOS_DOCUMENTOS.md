# Revisão dos documentos recebidos — 3 de novembro de 2026

Foram lidos os três arquivos Word adicionados à raiz do workspace, incluindo
parágrafos, tabelas e referências textuais. Os originais foram preservados.

| Documento | Conteúdo encontrado | Uso na revisão |
|---|---|---|
| `tcc_proposta(1).docx` | Proposta com introdução, fundamentação, arquitetura planejada, cronograma e bibliografia; autor Lucas Nory Ulson | Base do problema e registro do escopo originalmente proposto |
| `Guia_TCC2_Paralelizacao_Automatica_atualizado_2026-09-02(1).docx` | Caderno de execução, checklists, baselines sugeridos e medições iniciais | Histórico e critérios de comparação; tarefas sugeridas não são funcionalidades implementadas |
| `Resumo_Executivo_TCC2_Lucas_Ulson_Atualizado_2026-10-08.docx` | Síntese da arquitetura, plataformas e resultados de setembro; executor ainda pendente | Comparação com o estado atual e identificação de afirmações desatualizadas |

Nenhum dos três é uma monografia final completa com capítulos definitivos de
método, resultados e conclusão. A base nova é uma redação substantiva para essa
integração, não uma revisão de um documento final que não foi recebido.

## Ajustes incorporados à nova redação

| Local no material original | Divergência | Redação adotada / evidência |
|---|---|---|
| Título da proposta | Inclui GPU, sem implementação GPU avaliada | Título de trabalho delimitado a OpenMP em CPU; GPU fica como possibilidade futura, sem promessa de adaptação imediata |
| Proposta §3.1 | Restringe-se a GEMM e Jacobi e chama GEMM de MapReduce | Separar DOALL, redução, stencil, wavefront e mixed; distinguir análises e variantes de geração automática. O runner completo suporta o caso Dot Product/redução escalar |
| Proposta §3.1 | Associa padrões de algoritmo diretamente a SIMD | Descrever padrões e modelo de execução separadamente; threads OpenMP e a transformação SIMD específica não são a mesma etapa |
| Proposta §3.2–3.3 | Declara LangGraph, blackboard e quatro agentes como implementação | Runner Python, artefatos JSON e componentes determinísticos, mais Coordinator LLM. Não foram encontradas importações LangGraph nem um motor BDI no caminho atual |
| Proposta §3.2.3 | Codificador LLM produz os programas avaliados | O Transformer suportado é determinístico. GEMM/Jacobi/Covariance e Wavefront tiled têm variantes manuais. Nussinov automático parte de uma base OpenMP manual |
| Proposta §3.2.4 | Loop de reparo até convergência / máximo de tentativas | `run_pipeline.py` interrompe em RETUNE/MODIFY/REJECT; não executa uma busca automática de reparo |
| Proposta §3.4 | Comparação com LLM monolítica e múltiplos tamanhos para todo o conjunto | Comparação prioritária atual é a decisão sobre o mesmo candidato, com/sem Coordinator e com ablação. Não equivale a medir geração one-shot versus geração multiagente |
| Proposta e guia | Testes provam preservação semântica geral / race gate previsto | Comparação empírica para entradas e threads testadas; detector de races não é uma etapa do runner atual |
| Resumo executivo §1–3, §7 e §10 | Candidate Promotion Executor pendente | Implementado com vínculo de evidências, configuração medida, revalidação e publicação em diretório final; inferência real concluída continua pendente na integração local |
| Resumo executivo §6.2 | Eficiência tiled de aproximadamente 0,850 | É `(T_seq/T_4)/4`. Para o mesmo bloco 64, a eficiência paralela é `(T_1/T_4)/4 ≈ 0,594`; ganho contra sequencial continua 3,400× |
| Resumo executivo §6.2 e §9 | Ciclo Wavefront atribuído à recuperação autônoma do sistema | Histórico de diagnóstico, alteração manual e autotuning; não demonstra que a LLM executou sozinha o ciclo |
| Resumo executivo §6.3 | Hardware Mac atribuído ao CSV Nussinov automático | O documento afirma Mac; a campanha canônica não contém captura própria. A matriz mantém o hardware como não registrado, até comprovar o vínculo |
| Resumo executivo §8 | Contagem antiga de regressões | Última bateria registrada: 75 testes unittest e 14 casos dos seletores/Coordinator. São verificação técnica, não amostras científicas |
| Guia §3 e §10–15 | Múltiplas suítes, one-shot, agente com reparo, Polly e várias ablações propostos | Backlog de pesquisa, sem declaração de execução. O estudo atual tem um kernel em dois tamanhos para avaliar a decisão da LLM |

## Questões de pesquisa reconciliadas com o recorte

A proposta pretendia demonstrar superioridade sobre uma geração monolítica sem
análise. O experimento implementado não produz esse contraste. A redação foi
reformulada para estudar: rastreabilidade e bloqueio de candidatos; desempenho
das configurações medidas; e efeito adicional do Coordinator na decisão de
admissão. A terceira questão permanece sem conclusão experimental.

Essa mudança deve aparecer na introdução, nos objetivos e na conclusão. Não
manter o objetivo original amplo e usar a ablação do Coordinator como se fosse
uma resposta equivalente sobre geração de código ou coordenação de vários LLMs.

## Bibliografia e formato

As referências novas usadas na base foram conferidas em fontes primárias e
estão em `referencias.bib`. A bibliografia extensa da proposta não foi tratada
como integralmente verificada; estatísticas de adoção de IA e tópicos sem papel
na implementação foram retirados da nova argumentação. A proposta original foi
preservada como registro dessas fontes e do planejamento.

A revisão não atesta normas institucionais, aprovação de mudança de título ou
prazo de entrega. O texto final ainda precisa ser colocado no modelo de entrega,
com os resultados LLM concluídos ou sua ausência explicitamente discutida.
