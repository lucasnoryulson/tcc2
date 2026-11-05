# Protocolo multiplataforma — versão de quinze medições

Este protocolo implementa o pedido detalhado recebido em 05/11/2026 e preservado
em [REQUISITOS_2026-11-05.md](REQUISITOS_2026-11-05.md). O trabalho está na branch
`feat/multiplatform-protocol-2026-11-05`, a partir de HEAD `32ae80b`, mantendo as
alterações locais anteriores. Não houve push ou merge. A coleta anterior de sete
amostras, suas figuras e as campanhas históricas permanecem intactas.

## Questões e unidades experimentais

O objetivo é caracterizar a escalabilidade de códigos OpenMP e a configuração
recomendada em cada plataforma. Esse desenho não isola causalmente ISA,
quantidade de núcleos, compilador, cache e memória: essas características variam
juntas entre Linux e Apple M5. Tampouco estima contribuição da LLM para os
ganhos dos kernels. O Coordinator não é chamado nesta campanha.

Uma observação é o tempo por chamada reportado por um processo externo. Um
bloco contém uma observação de cada configuração da mesma entrada/algoritmo.
Quinze blocos não são quinze máquinas ou campanhas independentes. Dot C agrupa
chamadas internas em cada processo, e a média interna é a observação externa.
Nenhuma chamada interna é tratada como nova amostra estatística independente.

## Casos, entradas e fontes

| Caso | Entrada menor | Entrada maior | Tipo e variante |
|---|---|---|---|
| Dot C automático | N=1024, 10.000 chamadas internas | N=10.000.000, 100 chamadas internas | double; original e candidato gerado pelo transformador determinístico real |
| Dot C++ manual | N=1.000.000 | N=10.000.000 | double; uma chamada por processo, fontes em `kernels/dot/` |
| GEMM | NI=200, NJ=220, NK=240 | NI=1000, NJ=1100, NK=1200 | double; original PolyBench e OpenMP manual |
| Nussinov | N=500 | N=2500 | int; original, OpenMP manual, SIMD manual e SIMD adaptado preexistente |
| Jacobi-2D | N=250, TSTEPS=100 | N=1300, TSTEPS=500 | double; original e OpenMP manual |
| Covariance | N=260, M=240 | N=1400, M=1200 | double; original e OpenMP manual |

O submódulo PolyBench é fixado em
`3e872547cef7e5c9909422ef1e6af03cf4e56072`. As macros efetivas e tipos também
são extraídos com o pré-processador e registrados em `report.json`; não se
infere o tamanho apenas pelo nome MEDIUM/LARGE. Os snapshots incluem fontes,
headers e o utilitário `polybench.c` efetivamente compilados.

Dot C usa A[i]=(i mod 1000)/1000 e B[i]=((7i) mod 1000)/1000. Dot C++ usa
constantes a=1024/N e b=2048/N. Portanto, nem os drivers nem as distribuições
dos valores são idênticos entre os dois casos. Comparações C versus C++ são
descritivas e não isolam uma diferença do transformador ou da linguagem.

O Dot C é gerado chamando os analisadores, Planner e Code Transformer reais em
diretórios exclusivos. Não se reutiliza um candidato editado manualmente para
alegar geração automática. As três variantes OpenMP de Nussinov pertencem ao
acervo preexistente; SIMD automático é adaptação determinística sobre base manual.

## Compilação, ambiente e cobertura de corretude

Flags: `-O3`, `-std=c++14` no C++, macro de dataset no PolyBench e `-fopenmp`
somente nas variantes OpenMP. Não se usa `-march=native` ou `-ffast-math`.
O ambiente define `OMP_DYNAMIC=FALSE`, `OMP_PROC_BIND=TRUE`, `OMP_PLACES=cores`
e `OMP_NUM_THREADS=p`; remove demais variáveis OMP/KMP/GOMP herdadas dos
processos medidos, registrando seus valores iniciais. A identidade do compilador
inclui caminho resolvido, SHA-256 e versão. As dependências dinâmicas são
registradas por `ldd` no Linux e `otool -L` no Mac.

O registro inclui branch, commit, Git dirty, submódulos, Python, sistema,
arquitetura, CPU, núcleos físicos/lógicos, afinidade disponível, memória, carga
inicial e governor quando expostos no Linux. No Mac também registra modelo,
contagens dos níveis de desempenho e alimentação/energia via `pmset`.
Um programa OpenMP compilado com a mesma toolchain confirma o tamanho efetivo
das equipes solicitadas. Ele não comprova a localização dos workers dos kernels.

Antes das medições, toda entrada/variante/thread é validada. Dot C e C++ exigem
valores finitos e concordância com o resultado esperado, usando rtol=1e-9 e
atol=1e-12; essa conferência também ocorre em cada amostra temporal de Dot.
No C, o valor esperado é calculado a partir do período de 1000 elementos e do
resto da entrada. No C++, a fórmula está na fonte e sua saída é conferida.

PolyBench usa executáveis de dump separados, com a mesma otimização e entrada,
comparando os arrays impressos com a referência sequencial. Nussinov mantém
inteiros exatos. Os headers **copiados** de GEMM, Jacobi e Covariance mudam o
formato floating-point de duas casas para 17 dígitos significativos; isso evita
aceitar diferenças escondidas pela formatação histórica. Os headers originais
não são editados. A igualdade desses dumps não prova ausência de races ou
equivalência para qualquer entrada; não se afirma validação dos elementos que
o `print_array` do benchmark não imprime.

## Aquecimento e ordem

Para cada entrada, são executados três blocos de aquecimento, contendo todas as
configurações, seguidos de quinze blocos de medição. A ordem dentro de cada bloco
é embaralhada por `random.Random(2026)` e fica reprodutível pelos comandos e
identificadores de repetição. A sequência de aquecimento consome o mesmo gerador
antes da sequência medida. Nenhuma amostra é excluída por ser lenta.

Cada aquecimento é um processo externo novo. Ele não conserva workers entre
processos. No Dot C++, o primeiro fork/join OpenMP pode integrar o tempo medido.
Dot C amortiza custos entre suas chamadas internas. No PolyBench, o flush de
cache padrão antes do timer já executa uma região OpenMP no candidato,
inicializando a equipe. Esses regimes são mantidos iguais entre plataformas
para cada caso, não igualados artificialmente entre kernels diferentes.

Os relógios preexistentes são mantidos: CLOCK_MONOTONIC no driver Dot C,
`std::chrono::high_resolution_clock` no Dot C++ e `gettimeofday` no PolyBench.
PolyBench imprime seis casas decimais em segundos. Tempos positivos e finitos
são exigidos; não há correção posterior para aparentar maior resolução.

Linux mede sequencial e OpenMP 1T, 2T e 4T. M5 acrescenta 6T, 8T e 10T. O ponto
sequencial não é confundido com OpenMP 1T. No Linux, a matriz solicitada contém
60 configurações, 180 aquecimentos externos e 900 amostras externas; Nussinov
compartilha um baseline sequencial entre suas variantes, sem duplicar amostras.

## Estatística e seleção

Para uma mesma entrada e variante:

- Tseq: mediana do original sequencial.
- T1: mediana dessa variante OpenMP com uma thread.
- Tp: mediana dessa variante com p threads.
- Speedup total: Tseq/Tp.
- Speedup de transformação: Tseq/T1.
- Escalabilidade: T1/Tp.
- Eficiência: (T1/Tp)/p.

O CSV derivado inclui média, mediana, desvio padrão amostral (n−1), mínimo,
máximo, MAD sem fator de escala, quartis e IQR. MAD é a mediana dos desvios
absolutos em relação à mediana; IQR=Q3−Q1. Os quartis usam interpolação linear
inclusiva, nas posições (n−1)q. A consolidação histórica usa `pstdev`; os
desvios desses dois protocolos não devem ser confundidos.

Com pelo menos quinze observações por configuração, calculam-se intervalos
percentis bootstrap de 95%, com 5.000 reamostragens e seed 2026. Cada réplica
reamostra identificadores de blocos completos, usando os mesmos índices para
sequencial, OpenMP 1T e OpenMP p; recalcula medianas e razões. Os limites são os
percentis 2,5% e 97,5%, com interpolação linear. Em amostras menores, os limites
ficam ausentes, em vez de serem inventados.
O bloco aqui é uma rodada completa do desenho pareado, não uma sequência de
rodadas contíguas usada em moving-block bootstrap para séries temporais. A
reamostragem da distribuição empírica segue a ideia geral de
[Efron (1979)](https://sites.stat.washington.edu/courses/stat527/s13/readings/ann_stat1979.pdf);
o pareamento por rodada é a escolha específica deste protocolo.

Esses intervalos são condicionais aos blocos observados e pressupõem que sua
reamostragem represente adequadamente a variabilidade. Não se comprovou
estacionariedade ou independência temporal, nem se corrigiram múltiplas
comparações. Os intervalos não são uma prova de causalidade arquitetural, de
ausência de ruído ou de significância entre duas máquinas. Não se agrupam
tempos de plataformas ou variantes diferentes para aumentar n.

O Performance Selector real é reutilizado para cada entrada/variante. São
registrados a menor mediana OpenMP, o estado da seleção, a recomendação e o
conjunto a até 2% da menor mediana benéfica. A configuração de menos threads
desse conjunto pode ser recomendada. Seleção analítica não é promoção; gates
e Executor do pipeline mantêm condições adicionais de admissão.

## Arquivo experimental e figuras

Cada campanha exige um diretório inexistente. O coletor preserva comandos,
retornos, stdout, stderr, fontes, executáveis e hashes. Dumps usam gzip sem
perda; seus hashes se referem aos bytes descomprimidos. Amostras são gravadas
incrementalmente em JSONL e, no sucesso, também em CSV. Falhas/timeout conservam
os registros e terminam com estado FAILED; não há tentativas silenciosas.

O analisador verifica os hashes, reconstrói tempos a partir do stdout, confere
contagens de amostras/aquecimentos e recalcula os resumos. Produz PNG/SVG/PDF de
tempo, speedup total, escalabilidade, eficiência e configuração recomendada.
As barras dos gráficos novos representam IC bootstrap; as figuras da campanha
exploratória anterior continuam representando sua dispersão original.

## Comandos Linux e M5

Na raiz do checkout, com PolyBench inicializado e sem campanhas concorrentes:

```bash
git submodule update --init benchmarks/PolyBenchC-4.2.1
bash scripts/run_multiplatform_linux.sh results/multiplatform/linux_xeon_2026-11-05_p15w3
```

O arquivo contém o protocolo aplicado. Para gráficos, usar o ambiente Python
de análise já adotado pelo projeto; tabelas e verificação também funcionam com
`--no-plots` apenas com a biblioteca padrão:

```bash
build/analysis-venv/bin/python -B scripts/analyze_scaling.py \
  results/multiplatform/linux_xeon_2026-11-05_p15w3 \
  --output results/multiplatform/analysis_linux_xeon_2026-11-05_p15w3
```

No M5, copiar fontes/scripts, confirmar a toolchain e recriar o venv local:
O wrapper coloca o LLVM Homebrew no PATH para que a análise AST que chama
`clang` também use essa instalação. Ao escolher caminhos diferentes, conferir
explicitamente `command -v clang` e sua versão, além de `--cc`/`--cxx`.

```bash
git status --short --branch
git submodule update --init benchmarks/PolyBenchC-4.2.1
/opt/homebrew/opt/llvm/bin/clang --version
bash scripts/run_multiplatform_mac.sh results/multiplatform/mac_m5_nova_coleta_p15w3
python3 -B scripts/analyze_scaling.py \
  results/multiplatform/mac_m5_nova_coleta_p15w3 \
  --output results/multiplatform/analysis_mac_m5_nova_coleta_p15w3
```

Os wrappers aceitam opções adicionais depois do diretório para ajustar os
caminhos reais dos compiladores; mudanças de entradas/protocolo precisam ser
declaradas e podem impedir comparação direta. Não executar binários Linux no Mac
nem reescrever caminhos de relatórios para simular nova medição.

Depois da coleta Mac real:

```bash
python3 -B scripts/compare_multiplatform.py \
  results/multiplatform/linux_xeon_2026-11-05_p15w3 \
  results/multiplatform/mac_m5_nova_coleta_p15w3 \
  --output results/multiplatform/comparison_linux_mac_p15w3
```

O comparador exige protocolos, entradas, bytes de fontes/headers/drivers e flags
compatíveis, produzindo curvas distintas por campanha no subconjunto comum.
Se houver divergência, registra INCOMPARABLE e recusa o gráfico conjunto. O
subconjunto planejado é 1T/2T/4T; 6T–10T são extensão específica M5, sem tratar
seus núcleos P/E como homogêneos. Compiladores e runtimes distintos permanecem
fatores da comparação de plataformas.

## Limites de execução

Não houve controle dedicado de temperatura/frequência, isolamento exclusivo do
sistema, teste de races, medição de energia ou contadores de memória/cache.
O governor e a carga inicial são registro de contexto, não prova de constância.
Os resultados históricos do M5 permanecem contextuais; a campanha equivalente
de quinze amostras ainda depende daquela máquina. O modelo institucional
completo da PUCRS exige autenticação; a capa oficial pública foi preservada e
a revisão de conteúdo não é declarada monografia final aprovada.
