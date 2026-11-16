# Preflights técnicos preservados

Estes arquivos registram desenvolvimento e validação técnica. Seus tempos,
quando presentes, não são somados à campanha científica do corpus nem às
sessões de escalabilidade. Falhas anteriores continuam visíveis.

| Arquivo | Resultado e interpretação |
|---|---|
| `results/publication/validation_linux_2026-11-05/unittest.log` | Bateria inicial: 108 testes aprovados antes das revisões adicionais |
| `results/publication/validation_linux_2026-11-05/unittest_postreview_failed117.log` | 117 testes, um erro: um token de comentário no fixture encerrava o comentário e tornava a fonte inválida antes da análise; fixture corrigido |
| `results/publication/validation_linux_2026-11-05/unittest_final.log` | 117 testes aprovados após corrigir o fixture e a decodificação de stderr; antecede a última revisão do coletor |
| `results/publication/automation_functional_v2_linux_2026-11-05/` | Preflight completo, `COVERAGE_MISMATCH`: 14 positivas e 28 entradas corretas, mas 14 recusas foram classificadas como erro. O CLI escreve a mensagem em stdout, enquanto o novo coletor procurava somente em stderr. Nenhum desses erros recebe crédito como recusa correta |
| `results/publication/validation_linux_2026-11-05/unittest_after_archive_review.log` | Bateria ampliada: 121 testes aprovados, incluindo atribuição de binário, reconstrução de estatísticas/seleção, resultado negativo completo, dimensões e mutação de clamp |
| `results/publication/automation_functional_v11_linux_2026-11-05/` | Preflight final do coletor 1.1: `COMPLETE`, 14 aceitações, 14 recusas conforme o contrato, zero erros e 28 pares positivos fonte × entrada validados; arquivo verificado por SHA-256 |

O coletor 1.1 considera stdout e stderr e exige retorno 1, contrato REFUSED
e mensagem explícita de recusa. Crash, timeout e arquivo ausente são erros.
Os valores de A passaram de divisor 16 para 8 antes da campanha científica,
pois o desenho anterior não exercitava o ramo superior de clamp. Os dois
preflights possuem snapshots que identificam as versões e os valores usados.

A inspeção adicional de código foi assistida por outro agente. Não equivale
a revisão humana independente, anotação cega ou prova formal.

O fechamento de 06/11 executou 123 unittests, todos aprovados em 23,130 s,
sem skips (`unittest_publication_final.log`). Os seis scripts de regressão
passaram nos 23 casos. A primeira checagem de colisão de saída esperava
retorno 2 para ambos os wrappers; `run_diagnostics_mac.sh` delega ao Python,
que recusa por `FileExistsError` com retorno 1 antes de qualquer inferência.
A expectativa de teste foi corrigida sem mudar o wrapper ou o harness
congelado. O registro inicial foi preservado como
`regressions_shell_initial_expectation_error.json`; o relatório final PASS
está em `regressions_shell_final.json`.

A demonstração integrada DOALL de 06/11, com compilação e tempos reais,
terminou `FAILED` por timeout Qwen de 180 s. Nenhuma decisão ou promoção
foi produzida e não houve retry. O suplemento numérico pré-declarado
registrou `FAIL` em 2T solicitado por saída `-inf`; essa falha é o resultado
a preservar, não defeito no teste a corrigir. Ambos têm arquivos próprios,
fora dos denominadores científicos do corpus e das sessões de escalabilidade.
