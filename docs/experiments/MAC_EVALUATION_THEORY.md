### 2.4. Dependências, custo serial e Lei de Amdahl

Uma dependência verdadeira exige que o valor produzido por uma operação esteja
disponível antes de outra consumi-lo. A ausência de escrita concorrente no
mesmo endereço é necessária, mas não substitui o exame das relações entre
iterações e dos contratos de alias. Uma redução permite combinar valores
parciais segundo a operação declarada; em ponto flutuante, a mudança de ordem
pode alterar arredondamento e valores intermediários. Uma sequência temporal
de stencils e uma sequência de diagonais possuem fronteiras de sincronização
que uma distribuição espacial precisa preservar.

Para trabalho fixo e p processadores homogêneos, uma fração serial s conduz ao
modelo `S(p)=1/[s+(1-s)/p]`. O limite quando p cresce é `1/s`. Esse modelo torna
explícito por que aumentar workers não elimina inicialização, regiões seriais e
sincronização. Aqui, uma descrição mais realista acrescenta overhead H(p,N):
`Tp = Ts + Tpar/p + H(p,N)`. Cache, distribuição de carga e classes distintas de
núcleo também podem alterar os termos. Não se estima uma fração serial causal
apenas ajustando essa expressão às seis medianas do M5. A hipótese de workers
homogêneos é especialmente limitada numa CPU com quatro núcleos de desempenho
e seis de eficiência. [Amdahl, 1967](https://www.cs.cmu.edu/~18742/papers/Amdahl1967.pdf).

### 2.5. Intensidade operacional e Roofline

Roofline relaciona desempenho atingível P, teto computacional Pmax, largura de
banda B e intensidade operacional I: `P <= min(Pmax, B*I)`. A intensidade precisa
usar o volume de tráfego do nível de memória examinado. Para Dot double, a
contagem lógica é aproximadamente duas operações por dezesseis bytes de entrada,
ou 0,125 operação/byte. Reuso em cache pode tornar essa contagem diferente do
tráfego físico. Em GEMM, o reuso de blocos aumenta operações por byte transferido;
ordem dos laços, tamanhos e hierarquia de cache influenciam esse reuso. Neste
estudo, taxas derivadas de bytes lógicos e tempo são indicadores operacionais.
Sem um teto de banda medido e contadores adequados, não constituem um Roofline
empírico da máquina nem demonstram saturação da DRAM.
[Williams, Waterman e Patterson, 2009](https://escholarship.org/uc/item/5tz795vq).

### 2.6. Autotuning e validação da configuração escolhida

Autotuning empírico explora alternativas executáveis e usa medições para decidir
parâmetros. ATLAS exemplifica a escolha de implementações ajustadas à máquina;
esse princípio não implica reproduzir sua busca, seus kernels ou seu desempenho.
O espaço deste trabalho é restrito às configurações de threads de cada variante
fixa. Uma recomendação depende da entrada, compilador, runtime e condições da
coleta. Por isso, reaplicar a escolha em novas observações é parte da avaliação,
e não apenas recalcular sua vantagem nos tempos usados para escolhê-la.
[Whaley, Petitet e Dongarra, 2001](https://netlib.org/utk/people/JackDongarra/PAPERS/2001_Automated-Empirical-Optimizations-of-Software-and-the-ATLAS-Project.pdf).

O mínimo de várias medianas pode refletir variação favorável da coleta. O limiar
operacional de 2% prefere menos threads em um quase empate; ele não funciona
como teste de significância ou intervalo de confiança. A avaliação separa a
configuração mais rápida na seleção, a recomendada pela política e o melhor
resultado observado posteriormente. O arrependimento é `100*(T_escolhida /
T_melhor_observada - 1)`. A referência posterior inclui o sequencial e pertence
somente àquela sessão. Uma frequência de recomendações inadequadas descreve
este conjunto finito de casos, sem estimar uma taxa populacional de erro.
