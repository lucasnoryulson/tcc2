# Automação conservadora e corpus controlado de programas

Esta extensão acrescenta geração automática DOALL ao caminho independente de
redução escalar. Não utiliza uma LLM, não transpõe implementações OpenMP manuais
e não modifica os resultados históricos. O Transformer insere a diretiva no
sequencial somente depois de reanalisar os bytes atuais com Clang.

## O que o sistema realmente transforma

O contrato `analysis/conservative_transform.py` admite uma função `kernel_*`,
um único laço externo canônico `for (int i = 0/1; i < n; i++)` e uma atribuição no
corpo. Os casos admitidos são:

- **DOALL:** `Y[i] = expressão`, retorno `void`, entradas `const double *restrict`,
  saída `double *restrict`, nenhuma leitura de `Y`, expressão pura, índices de
  entrada `i` ou `i +/- constante` de até 16 e escrita injetiva no índice `i`.
- **REDUCTION:** acumulador `double` local inicializado em zero, `sum += expressão`
  sem leitura do acumulador no lado direito e `return sum`. As entradas são
  ponteiros de leitura `const double *`; alias entre duas entradas somente lidas
  não cria escrita compartilhada.

`restrict` **é uma pré-condição do chamador conforme a linguagem C**, e não uma
prova dinâmica de que ponteiros são disjuntos. Os drivers alocam cada buffer
separadamente. O chamador deve fornecer extents válidos para todos os índices,
valores finitos e um programa sequencial sem comportamento indefinido. Não há
verificação geral de limites ou de overflow; o coletor restringe seus tamanhos
para evitar overflow na inicialização `i * 7` e aloca `n + 2` elementos. Testar
ponteiros sobrepostos seria uma violação do contrato, não um teste válido do
programa admitido.

São recusados chamadas, casts explícitos, acessos indiretos/scatter, in-place,
vizinhos do vetor de saída, passos não suportados, escrita escalar compartilhada,
múltiplas atribuições, laços aninhados, saídas antecipadas, pragmas existentes e
qualquer nó AST não reconhecido. Fontes independentes devem ser ASCII e o laço
deve começar na própria linha para a inserção por posição de fonte. Uma recusa
pode significar um programa paralelizável fora do subconjunto; isso não significa
que foi provada uma dependência.

O arquivo do kernel também exclui diretivas de pré-processamento e `_Pragma`:
uma condição em `_OPENMP` poderia selecionar outro corpo ao compilar o
candidato com `-fopenmp`. Definições em headers e atributos de função/iterador/
acumulador são recusados; por exemplo, `cleanup` pode introduzir uma chamada
invisível na expressão aritmética. Essas restrições aplicam-se ao arquivo
transformado, não aos drivers de teste separados.

O filtro é deliberadamente estrito: ocorrências de `#`, `%:`, `??`, `_Pragma`
ou barra invertida são recusadas mesmo em comentários/strings. Isso evita
digraphs, trigraphs, diretivas após comentários e continuações de linha sem
implementar um segundo pré-processador. É um limite de suporte, não uma
classificação de dependência. O contrato final desta revisão é
`standalone-ast-v2`; snapshots e hashes distinguem os testes técnicos anteriores.

A validação adicional também fecha uma lacuna anterior: reconhecer `sum += ...`
localmente não bastava para excluir efeitos laterais ou uma recorrência como
`sum += sum + A[i]`. O Transformer agora revalida o corpo completo. Metadados de
linha de um JSON antigo não comandam a inserção: as posições são reconstruídas
do AST atual. O contrato de promoção não foi relaxado.

Os leitores preservam CRLF ao decodificar os bytes, pois os offsets do Clang
se referem ao arquivo físico. Um teste com muitas linhas CRLF antes do laço
confere que a diretiva é inserida na posição correta, sem depender de metadados
de linha antigos.

## Corpus e denominadores

`analysis/fixtures/publication_corpus/catalog.json` declara **28 fontes C**:

| Grupo | Desenvolvimento | Teste controlado | Total |
|---|---:|---:|---:|
| Admitidas: DOALL ou redução | 4 | 10 | 14 |
| Recusas esperadas | 4 | 10 | 14 |
| Fontes | 8 | 20 | 28 |

As oito fontes DOALL cobrem transformação afim, produto elemento a elemento,
polinômio, diferença absoluta, filtro por limiar, saturação, stencil somente de
leitura com saída distinta e recíproco quadrático. As seis reduções cobrem soma,
soma de quadrados, produto interno, norma L1, distância quadrática e contagem.
As 14 recusas exercitam dependências, aliasing não resolvido, side effects e
limites deliberados do subconjunto. As recusas são avaliadas contra a
**especificação de suporte**, não contra a hipótese de que todo programa recusado
seria inerentemente sequencial.

O corpus foi escrito para este estudo. É uma seleção por conveniência de
microkernels controlados, não uma amostra representativa nem um benchmark externo
intocado. Desenvolvimento e teste têm arquivos distintos e rótulos explícitos,
mas o mesmo autor definiu ambos; os testes técnicos verificam ambos. Portanto,
esse split organiza a análise e não fornece uma estimativa cega de generalização.
Não foi ajustado um modelo nesses arquivos.

Cada fonte positiva usa **duas entradas, N=1.024 e N=1.000.000**. Entradas não são
contadas como novos programas. A avaliação funcional contém 28 pares fonte ×
entrada positivos, cada um executado no sequencial e no candidato com 1/2/4T.
Candidatos cuja recusa é esperada nunca são executados, mesmo que um erro do
transformador gere um arquivo. Todas as 28 fontes originais são compiladas para
verificar sua validade sintática.

Uma recusa contabilizada exige o contrato estático `REFUSED` e a mensagem
explícita `UNSUPPORTED_STANDALONE` do Transformer, com saída 1, em stdout ou
stderr. Crash, timeout, arquivo
ausente ou retorno inconsistente são erros inesperados e tornam a campanha
incompleta; não recebem crédito como recusas corretas.

## Corretude e evidências

O coletor reutiliza `compile_correctness_gate.py` sem alterar suas regras. O
oracle do driver determina os valores de entrada por fórmula e verifica **cada
elemento da saída DOALL**, antes de emitir um checksum escalar para o contrato do
gate. Reduções são comparadas à soma de termos em `long double`. As tolerâncias
são relativas `1e-9` e absolutas `1e-12`; valores não finitos ou uma posição errada
causam retorno não zero. Um teste usa dois erros que se cancelam no checksum para
confirmar que a checagem por elemento os rejeita.

Isso aumenta a observação sobre as entradas utilizadas; não é prova formal,
análise de races nem garantia para todas as entradas C. A fórmula do oracle é uma
especificação autoral da operação, não uma implementação externa independente.

A versão 1.1 do coletor usa A entre −1,375 e 1,375, com passo 0,125, e B entre
−0,28125 e 0,28125. Assim os dois tamanhos exercitam os ramos negativo, interno
e superior a um de `clamp`. Uma mutação sem saturação superior deve falhar no
driver. Um preflight técnico anterior usava A/16 e não cobria esse último
ramo; ele foi preservado, sem ser contado como campanha científica.

Cada execução conserva fontes e scripts, AST/dependências/padrões/planos,
candidatos gerados, drivers, comandos, stdout/stderr, gates e binários. Os
manifestos usam caminhos relativos e SHA-256. O verificador recusa adição/remoção,
bytes alterados, campanhas incompletas e amostras que divergem dos logs. As
estatísticas e figuras derivadas devem ficar em outro diretório, preservando o
arquivo completo da coleta.

## Desenho do desempenho

A opção `--measure` gera 15 processos medidos e 3 aquecimentos externos por
configuração. Cada rodada contém todas as configurações, com ordem embaralhada
por `random.Random(2026)`. O cronômetro `CLOCK_MONOTONIC` abrange apenas chamadas
do kernel: 1.000 chamadas internas na entrada pequena e 20 na grande. A média
interna é uma observação; o tamanho amostral externo continua 15. A primeira
inicialização do runtime OpenMP está dentro desse intervalo. Cada processo
verifica a saída depois do cronômetro, inclusive nos aquecimentos.

Com GCC, há três braços usando **o mesmo executável do compilador**:

| Braço | Fonte | Flags do objeto do kernel |
|---|---|---|
| Sequencial original | C original | `-O3` |
| Pipeline | C gerado automaticamente | `-O3 -fopenmp` |
| GCC autopar | C original | `-O3 -ftree-parallelize-loops=p -fopt-info-loop-optimized` |

O driver é compilado uma vez a `-O3`, sem autopar, e ligado aos objetos dos braços;
isso impede que a opção GCC paralelize a inicialização do driver e aqueça seus
workers antes do intervalo apenas nesse braço. Não há LTO ou `-ffast-math`.
A flag de autopar não prova que GCC paralelizou o laço: os diagnósticos reais são
arquivados. Não forçamos semântica de ponto flutuante para produzir um resultado
favorável ao baseline. A receita é apoiada pela
[documentação oficial GCC 13](https://gcc.gnu.org/onlinedocs/gcc-13.4.0/gcc/Optimize-Options.html).

No GCC 13, o número p integra a flag e cada configuração é compilada
separadamente. Portanto, T1/Tp desse braço compara configurações de compilação
da mesma família de fontes, não apenas a mudança de OMP_NUM_THREADS sobre um
único binário. O compilador pode conservar um laço sequencial se não o julgar
apto ou lucrativo; não se alega que todas as configurações ativaram p workers.

O contraste de desempenho é restrito às 14 fontes positivas do nosso contrato;
não mede a cobertura geral do GCC nas 14 recusas. As reduções OpenMP admitem
reordenação e são verificadas por tolerância. GCC sem reassociação pode
preservar a soma sequencial: não interpretar eventual vantagem nesses casos
como prova de uma análise de dependências superior. Relatar DOALL e redução
separadamente, além da tabela por fonte, evita ocultar esse fator.

Há uma configuração sequencial e 1/2/4T em cada um dos dois braços candidatos:
**14 fontes × 2 entradas × 7 configurações = 196 configurações**, 2.940 amostras
externas e 588 aquecimentos. Sem `--gcc-baseline`, são 112 configurações. O
parâmetro deve resolver para o mesmo executável que `--compiler`, para evitar
atribuir uma diferença Clang/GCC ao sistema de transformação.

São calculados média, mediana, desvio padrão amostral, MAD não escalado, quartis
lineares inclusivos, IQR, ganho total `Tseq/Tp`, transformação `Tseq/T1`,
escalabilidade `T1/Tp` e eficiência `(T1/Tp)/p`. O bootstrap percentil pareado
reamostra IDs das rodadas completas em 5.000 iterações, semente 2026, IC95% apenas
com pelo menos 15 amostras externas. Essa técnica não estabelece estacionariedade,
independência temporal ou repetibilidade entre sessões. O Selector existente é
reutilizado, incluindo o quase empate de 2%; uma variante mais rápida não implica
promoção automática ou benefício da LLM.

## Comandos de reprodução

Executar da raiz, sem outra campanha ou inferência concorrente:

```bash
python3 -B -m unittest scripts.test_automation_corpus scripts.test_pipeline_integration
python3 -B scripts/evaluate_automation_corpus.py \
  --compiler gcc --output results/publication/automation_functional_linux
python3 -B scripts/evaluate_automation_corpus.py \
  --compiler gcc --gcc-baseline gcc --threads 1 2 4 \
  --measure --samples 15 --warmups 3 --seed 2026 \
  --output results/publication/automation_corpus_linux_2026-11-05
python3 -B scripts/evaluate_automation_corpus.py \
  --verify --output results/publication/automation_corpus_linux_2026-11-05
```

Os caminhos de saída precisam ser novos. `--case` permite smoke técnico, sem
transformá-lo em campanha completa do corpus. O Mac deve usar um GCC de fato para
o baseline GCC, com o mesmo binário nos três braços; `/usr/bin/gcc` pode ser
Apple Clang. Se usar LLVM/OpenMP no Mac, omitir o braço GCC e declarar que esse
contraste de compilador não foi reproduzido. Não transportar binários Linux para
executá-los no Mac.

A nova classe funciona no runner integrado, sem passar pelo coletor do corpus:

```bash
python3 -B scripts/run_pipeline.py --prepare-only --compiler gcc --threads 1 2 4 \
  --source analysis/fixtures/publication_corpus/affine_vector.c \
  --driver analysis/fixtures/publication_corpus/affine_vector_driver.c \
  --benchmark-driver analysis/fixtures/publication_corpus/affine_vector_benchmark_driver.c \
  --work-dir build/publication-doall-preflight
```

Esse comando inclui medições reais do gate e termina antes da LLM. `PREPARED`
não é inferência, promoção ou demonstração de benefício da LLM.
