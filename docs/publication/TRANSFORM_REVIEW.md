# Revisão do limite da transformação

Esta revisão cobre o contrato AST adicionado nesta etapa. Não é uma prova
formal de corretude de C/OpenMP. O nome `certify_kernel` identifica uma
verificação conservadora de pré-condições locais, não uma certificação externa.

A revisão do código confrontou a classificação e o plano JSON com o caminho
real do Transformer. O Transformer consulta novamente o AST da fonte atual,
exige uma única função de kernel compatível, reconstrói as posições e confere
a redução. Não basta editar um JSON para declarar um laço seguro.

Foram identificados e tratados estes limites adicionais:

| Limite | Consequência possível | Tratamento e caso de regressão |
|---|---|---|
| Normalização CRLF antes de usar offset físico do Clang | Inserção da diretiva em linha errada | Decodificar bytes preservando CRLF; teste com 80 linhas antes do laço |
| Definição de kernel originada de um header | Offset referente a outro arquivo | Recusar definições incluídas e conferir que o offset identifica `for` na fonte atual |
| Atributo `cleanup` e atributos não interpretados | Efeito lateral não observado na expressão aritmética | Recusar atributos de função, iterador e acumulador; teste de redução com cleanup |
| Corpo condicionado por `_OPENMP` | AST sequencial e candidato podem representar corpos diferentes | Recusar diretivas de pré-processamento e `_Pragma` no arquivo transformado; teste com recorrência somente no braço OpenMP |
| Diretivas com comentário/digraph, tokens com continuação e whitespace ASCII | Bypass de filtro textual ou índice de linha divergente | Filtro deliberadamente estrito de tokens; linhas de inserção divididas somente por LF, com testes de CRLF, VT/FF e digraph |
| Contrato/posição de laço alterados no JSON | Plano falsamente seguro ou metadados obsoletos | Reanalisar fonte atual; testes de plano forjado e linha 9999 |
| Dois erros em um vetor com checksum igual | Falso PASS se somente a soma fosse comparada | Driver DOALL compara cada elemento antes de emitir o checksum; teste de cancelamento |

As restrições positivas permanecem pequenas: uma atribuição injetiva a Y[i]
com entradas somente lidas, ou uma redução escalar de soma sem recorrência no
lado direito. Chamadas, escritas aninhadas, scatter, in-place, passos e bounds
fora do formato, múltiplas instruções e nós desconhecidos são recusados.

`restrict` é obrigação do chamador, e não uma análise dinâmica de alias.
Bounds válidos, ausência de comportamento indefinido e aritmética definida
continuam sendo pré-condições. As entradas do corpus são controladas e os
drivers alocam buffers distintos; eles não demonstram equivalência para todos
os valores ou ausência de races em qualquer programa.

A bateria final é registrada no diretório de validação desta etapa. Os
experimentos de repetibilidade usam fontes congeladas em b9e252d e, portanto,
não são medições dessa nova extensão de transformação. O corpus de automação
tem campanha própria, com snapshots do código efetivamente usado.

A revisão editorial e uma inspeção estática adicional foram feitas por outro
agente. Os achados de digraph/comentários, `splitlines()` e bound sombreado
foram incorporados; nenhuma compilação ou medição foi feita por ele durante a
coleta de desempenho. Isso é revisão técnica assistida, não validação humana
independente do corpus ou prova formal.
