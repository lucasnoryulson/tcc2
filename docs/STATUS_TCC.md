# Estado do TCC — 3 de novembro de 2026

Esta numeração corresponde à lista original de conclusão do trabalho.

| Item | Estado | Evidência / pendência |
|---|---|---|
| **1. Fechar o pipeline até a geração do resultado final** | Implementado no caminho suportado | Runner único, Coordinator e executor determinístico; publicação atômica de código, manifesto, evidências e revalidação. A confirmação com LLM real permanece dependente de uma inferência concluída: o modelo local apresentou timeout em 120 e 300 segundos. |
| **2. Resolver as lacunas de validação e configuração** | Implementado e coberto por testes | PASS fixo removido; configuração unidimensional preservada; códigos de saída dos gates corrigidos; hashes, campanhas e configurações conferidos; testes de promoção válida e recusas, incluindo corretude fresca de candidato incorreto. |
| **3. Delimitar exatamente o que o sistema automatiza** | Incorporado à base revisada e aos slides | Caminho integrado para Dot Product/redução escalar independente. Demais padrões com análises/variantes e cobertura parcial; distinguir geração determinística, variantes manuais e decisão LLM. Manter esse recorte na versão adotada para entrega. |
| **4. Fechar a avaliação científica dos agentes** | Infraestrutura implementada; campanha LLM e discussão pendentes | Comparação pareada determinística/Coordinator/ablação, mesmos candidatos e medições, prompts, decisões, falhas, tokens, latência e tentativas. Baseline real em dois tamanhos de Dot Product; rodada real com quatro timeouts registrada. Ver `COORDINATOR_EVALUATION.md` e `COORDINATOR_EVALUATION_LOCAL.md`; testes simulados não substituem inferências concluídas. |
| **5. Consolidar os experimentos e a reprodução** | Dados disponíveis consolidados; fechamento experimental pendente | Matriz de 19 campanhas, inventário de 35 CSVs, amostras recuperadas, dispersão, gráficos SVG/PDF/PNG e guia de reprodução. Harnesses com saída separada e proteção dos históricos. Faltam confirmar metadados/vínculos históricos ou declarar suas limitações, e conservar a campanha final no hardware alvo. |
| **6. Fechar monografia e defesa** | Três Word revisados; base e defesa preparadas | Recebidos proposta, guia e resumo executivo. Produzidos base Word/Markdown com método, resultados disponíveis e conclusão delimitada; 16 slides PowerPoint com notas, bibliografia e roteiro de demonstração. Faltam resultados finais, integração ao modelo institucional, conferência no Office e ensaio. |

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
explicitamente. Somente as duas campanhas locais de Dot Product têm os gates
atuais verificáveis neste checkout. As demais são resultados históricos,
sem autorização de promoção pelo contrato atual.

## Critério para a próxima fase

O material de redação, a comparação com os Word recebidos e os passos finais
estão em [FECHAMENTO_TCC.md](FECHAMENTO_TCC.md). A base revisada não é declarada
monografia final: os três documentos recebidos eram proposta, guia e resumo,
sem um texto final completo de resultados e conclusão. Os originais foram preservados.

O fechamento técnico dos itens 1 e 2 permite concentrar a próxima campanha no
item 4. A redação deve usar o recorte do item 3 e as métricas separadas do item 5:
ganho da transformação, escalabilidade OpenMP e ganho contra o sequencial.

Nenhum teste local autoriza afirmar que o TCC ou a avaliação científica estão
concluídos. Ao retornar ao Mac, executar o comando do README com a toolchain e
o modelo locais e conservar a pasta da execução para auditoria.
