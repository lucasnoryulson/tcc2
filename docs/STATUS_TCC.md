# Estado do TCC — atualização experimental em 5 de novembro de 2026

Esta numeração corresponde à lista original de conclusão do trabalho.

Os itens 1 a 4 preservam o fechamento de 03/11 no Mac. Foi aberta uma etapa
complementar dos itens **5 e 6** para comparar escalabilidade de Dot Product,
GEMM e Nussinov, incluindo Jacobi-2D e Covariance. O pedido detalhado recebido
em 05/11 está preservado em [REQUISITOS_2026-11-05.md](experiments/REQUISITOS_2026-11-05.md).
A campanha Linux de quinze amostras terminou; o
[protocolo](experiments/MULTIPLATFORM_METHODOLOGY.md) e o
[relatório numérico](experiments/MULTIPLATFORM_REPORT.md) são as referências
atuais. A campanha equivalente no M5 permanece pendente. A revisão usou a
base disponível, conforme autorizado, sem esperar o manuscrito externo.

| Item | Estado | Evidência / pendência |
|---|---|---|
| **1. Fechar o pipeline até a geração do resultado final** | Concluído no caminho suportado | No Mac, o pipeline completo executou com LLVM 23.1.1 e inferência real do `llama3.1:8b`: Coordinator `ACCEPT`, promoção, manifesto, evidências e revalidação íntegros. O resultado comprova o caminho Dot Product/redução, não generaliza a automação para os demais padrões. |
| **2. Resolver as lacunas de validação e configuração** | Concluído e verificado no Mac | PASS fixo removido; configuração unidimensional preservada; códigos de saída dos gates corrigidos; hashes, campanhas e configurações conferidos. No Mac, a suíte final de 82 testes unittest e 14 casos de regressão passou sem skips. |
| **3. Delimitar exatamente o que o sistema automatiza** | Concluído e auditado | Contrato consolidado em `docs/AUTOMATION_SCOPE.md`: caminho integrado para Dot Product/redução escalar; demais padrões separados entre análise, variantes manuais e transformações específicas. Uma LLM apenas no Coordinator; GPU, geração universal e reparo autônomo fora do recorte. |
| **4. Fechar a avaliação científica dos agentes** | Concluído no recorte e limitações preservadas | A campanha original `INCOMPLETE` revelou um defeito de schema. Após correção, a replicação com as mesmas evidências terminou `COMPLETE`: 12/12 respostas LLM válidas e concordância total nos dois casos. Ensaio controlado: ACCEPT, REJECT e RETUNE 6/6; MODIFY 0/6 no `llama3.1:8b`. Não foi demonstrado benefício adicional da LLM ou das análises nesta amostra. Ver `COORDINATOR_EVALUATION_MAC.md`. |
| **5. Consolidar os experimentos e a reprodução** | Nova campanha Linux validada; coleta equivalente M5 pendente | Matriz anterior de 22 campanhas, campanha exploratória de sete amostras e Dot C nativo anteriores preservados. Protocolo novo: 60 configurações, 900 medições externas, 180 aquecimentos e 60 validações de corretude; fontes, compiladores, executáveis, comandos e saídas arquivados. Estatística, bootstrap e cinco gráficos em SVG/PNG/PDF recalculados. No Linux: 91 testes unittest, 23 casos de regressão e isolamento de análise estática aprovados. |
| **6. Fechar monografia e defesa** | Nova revisão de conteúdo exportada; fechamento institucional e Mac pendentes | `REVISAO_MULTIPLATAFORMA.md`, Word e PDF separados incluem arquitetura, contratos, pseudocódigos, exemplos C, ambientes, resultados e ameaças à validade. Exportação Word reaberta: 13 tabelas e 15 imagens. Base original de HEAD e materiais anteriores preservados. Capa oficial pública preenchida em arquivo separado. PDF de revisão via ReportLab; modelo institucional completo autenticado, conferência no Word, banca e incorporação da coleta M5 ainda pendentes. |

## Escopo de automação

| Caso | Cobertura conhecida no repositório |
|---|---|
| Dot Product / REDUCTION | Análise, planejamento, transformação de redução escalar, compilação, validação numérica, benchmark, seleção, Coordinator e promoção integrados. |
| GEMM / DOALL | Análises e implementação OpenMP manual; não declarar transformação completa automática pelo novo runner. |
| Jacobi-2D / STENCIL | Análises e variantes manual/tiled; não declarar transformação completa automática pelo novo runner. |
| Nussinov / WAVEFRONT | Análises, variantes OpenMP e transformações adaptativas específicas por feedback de compilação; o novo contrato de gates independentes não cobre o projeto PolyBench completo. |
| Covariance / MIXED | Análises e implementação OpenMP manual; não declarar transformação completa automática pelo novo runner. |
| Wavefront sintético | Variantes manual/tiled e autotuning existentes; integrar ao contrato de promoção exige evidências novas compatíveis. |

Os gates atuais verificam arquivos independentes e um resultado numérico escalar
segundo o driver fornecido. Isso não constitui prova formal de equivalência,
ausência de races para todas as entradas, nem um transformador universal C/C++.

## Evidências do item 5

- [Matriz e gráficos](../results/consolidated/REPORT.md).
- [Protocolo de reprodução e limites](EXPERIMENT_REPRODUCTION.md).
- [Catálogo das campanhas e referências](experiment_catalog.json).

Os CSVs históricos permanecem intactos. Campanhas misturadas e cabeçalhos
incompatíveis estão no inventário; a consolidação usa fontes selecionadas
explicitamente. Três campanhas finais de Dot Product no Mac têm os gates atuais
verificáveis neste checkout; duas coletas Linux preservam apenas o resumo. As 17
restantes são resultados históricos, sem autorização de promoção pelo contrato atual.

## Critério para a próxima fase

O material de redação, a comparação com os Word recebidos e os passos finais
estão em [FECHAMENTO_TCC.md](FECHAMENTO_TCC.md). A base revisada não é declarada
monografia final: os três documentos recebidos eram proposta, guia e resumo,
sem um texto final completo de resultados e conclusão. Os originais foram preservados.

O fechamento técnico dos itens 1 a 4 permite concentrar a próxima etapa na
consolidação do item 5. A redação deve usar o recorte do item 3 e as métricas separadas do item 5:
ganho da transformação, escalabilidade OpenMP e ganho contra o sequencial.

## Execução final do item 1 no Mac

Em 3 de novembro de 2026, o preflight terminou `PREPARED` e a execução completa
terminou `PROMOTED` com `llama3.1:8b` (ID local `46e0c10c039e`), LLVM Homebrew
23.1.1 e configurações 1, 2 e 4 threads. O Coordinator retornou `ACCEPT` e
`PROMOTE_CANDIDATE`, recomendando 4 threads. A configuração promovida mediu
speedup end-to-end de 2,46546x e escalabilidade contra OpenMP 1T de 2,46466x.

- Runner: `build/final-pipeline-mac-2026-11-03/run-4whpshpr/`.
- Bundle: `results/final-promoted/mac-2026-11-03/5eef401105cc51be73471cfbf836964f858d9453a381224490828123f54eb1d5/`.
- Candidato/`parallel.c`: SHA-256 `5ece8b7eb8416cbc3ad123aa137a81c639253a1d9a3f4565983e2a1c22f7978b`.
- Revalidação: `PASS`; todos os hashes declarados no manifesto foram conferidos.

Essa execução conclui o item 1 no recorte suportado, mas não conclui a avaliação
científica do item 4 nem o TCC como um todo.

## Verificação final do item 2 no Mac

Em 3 de novembro de 2026, a suíte final registrada executou **82 testes unittest** e
os **14 casos de regressão** (Coordinator 7, Performance Selector 3 e
Autotuning Selector 4), todos aprovados e sem skips. A primeira execução expôs
que `gcc` no macOS era o Apple Clang sem `-fopenmp`; a infraestrutura de testes
passou a detectar e provar suporte OpenMP, usando LLVM Homebrew no Mac e
preservando `gcc` compatível no Linux. Também foi normalizada a equivalência
macOS entre `/var` e `/private/var` nas fixtures. Os contratos de produção não
foram relaxados.

## Fechamento do item 3

O recorte foi auditado contra o despacho real de `analysis/code_transformer.py`
e consolidado em `docs/AUTOMATION_SCOPE.md`. O caminho genérico transforma
redução escalar direta e recusa estratégias não suportadas; as transformações
adaptativas de Nussinov permanecem identificadas como rotinas específicas sobre
uma base OpenMP existente. Monografia, README e roteiro de demonstração foram
alinhados ao mesmo escopo. As regressões do Adaptive Strategy Planner, Compiler
Feedback v0.1/v0.2, isolamento de variantes e a recusa direta de `DOALL` pelo
transformador genérico passaram no Mac.
