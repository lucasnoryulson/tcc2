# Nussinov: verificação do código compilado

Depois do encerramento das 900 medições, os quatro comandos de compilação de
Nussinov LARGE foram recuperados do arquivo `commands.jsonl`. Novos executáveis
foram produzidos em `results/multiplatform/diagnostics_linux_xeon_2026-11-05_p15w3/`,
acrescentando `-Rpass=loop-vectorize`, `-Rpass-missed=loop-vectorize` e
`-Rpass-analysis=loop-vectorize`. Todos compilaram com retorno zero. Esses novos
executáveis não foram executados como benchmarks e não substituíram os medidos.

O laço de partição das duas variantes SIMD apresentou largura de vetorização
quatro e interleaving dois. A base manual sem redução SIMD apresentou um
diagnóstico de dependência impeditiva no laço correspondente. A vetorização de
largura 16 também presente nos logs pertence à inicialização; não é a evidência
usada para o laço de partição do kernel.

`objcopy --only-section=.text -O binary` extraiu as seções dos binários medidos
e dos diagnósticos em arquivos novos. As duas seções **medidas** de SIMD manual
e SIMD adaptado têm SHA-256 idêntico:
`a76a92aae5bc91a1a7ad8c9b31bac9a4e38ef84e30fbb3845030ccc390ad2887`.
Isso comprova identidade desses bytes, sem afirmar identidade de todos os dados
ELF ou ausência de interferência do sistema. As pequenas diferenças temporais
entre essas variantes não demonstram superioridade de uma transformação.

Os comandos de diagnóstico usam outro caminho de saída. Suas seções .text
não coincidem em todos os casos com as originais; essa recompilação não é usada
como substituta da identidade dos binários medidos. O relatório JSON registra
as comparações separadamente, incluindo os resultados falsos.

No conjunto LARGE, o ganho total foi 3,195× na base manual, 2,974× no SIMD manual
e 2,959× no SIMD adaptado. No MEDIUM, as variantes SIMD foram mais rápidas.
Portanto, confirmar a vetorização não garante melhor desempenho em qualquer
entrada. Não foram medidos contadores para atribuir uma causa única.
