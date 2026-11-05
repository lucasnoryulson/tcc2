# Coleta complementar de escalabilidade — Linux e preparação M5

Este protocolo registra o trabalho de 05/11/2026 na branch
`feat/experimentos-multiplataforma-2026-11-05`, a partir de `32ae80b`.
O remoto foi atualizado antes da coleta. Os três documentos mencionados no
pedido (`CODEX_EXPERIMENTOS_MULTIPLATAFORMA.md`,
`RESULTADOS_HISTORICOS_VERIFICADOS.md` e a monografia reescrita de 05/11)
não estavam no checkout, nos ZIPs locais nem nas branches remotas consultadas.
Portanto, esta coleta atende ao objetivo explícito de medir os três kernels,
mas ainda não pode ser declarada execução integral conferida daquele plano.
A fonte de monografia disponível é `docs/monografia/BASE_MONOGRAFIA.md`.

## Recorte e autoria das variantes

| Kernel | Entradas | Variantes | Origem |
|---|---|---|---|
| Dot Product C++ | N=1.000.000 e 10.000.000; double | sequencial, manual | Código preexistente de `kernels/dot/` |
| GEMM | MEDIUM: 200×220×240; LARGE: 1000×1100×1200; double | sequencial, manual | PolyBench fixado e `kernels/gemm/` |
| Nussinov | MEDIUM: N=500; LARGE: N=2500; int | sequencial, manual, SIMD manual, SIMD automático preexistente | PolyBench e fontes em `kernels/nussinov/` e `analysis/output/generated/` |

Não houve geração de código pela LLM nem chamadas ao Coordinator nesta coleta.
Nussinov automático é uma transformação determinística específica sobre base
OpenMP existente; sua comparação com a versão manual não demonstra contribuição
decisória da LLM. Dot C++ manual não é o Dot C do pipeline com 100 chamadas.

## Procedimento Linux

```bash
git submodule update --init benchmarks/PolyBenchC-4.2.1
python3 -B scripts/benchmark_scaling.py \
  --output results/scaling/linux_xeon_2026-11-05 \
  --cc clang --cxx clang++ --threads 1 2 3 4
```

O runner recusa diretório existente. Usa sete processos de medição por
configuração, um processo de aquecimento, ordem embaralhada em blocos completos
com seed 2026 e timeout explícito. Cada processo mede uma chamada do kernel;
inicialização dos arrays e compilação ficam fora do tempo. No Dot C++, a primeira
inicialização do runtime OpenMP está dentro do tempo do kernel. O aquecimento
externo não mantém a equipe OpenMP viva entre processos: ele aquece arquivos e
caminhos de execução, não mede regime estacionário de uma equipe persistente.
No PolyBench, o flush padrão de cache ocorre antes da região temporizada.
Nesse utilitário, o flush da compilação OpenMP já usa `parallel for`, portanto
inicializa a equipe antes do cronômetro de GEMM/Nussinov. O timer PolyBench usa
`gettimeofday` e imprime seis casas decimais; não foi substituído por outro
relógio nesta reprodução. Dot usa o relógio de `std::chrono` do código existente.

Flags: `-O3`, C++14 no Dot, `-D{MEDIUM,LARGE}_DATASET` no PolyBench e
`-fopenmp` nas variantes paralelas; sem `-march=native` ou `-ffast-math`.
Ambiente: `OMP_DYNAMIC=FALSE`, `OMP_PROC_BIND=TRUE`, `OMP_PLACES=cores` e
`OMP_NUM_THREADS=p`; demais variáveis OMP/KMP/GOMP herdadas são removidas do
processo medido, e seus valores originais ficam registrados no ambiente.
Um probe confirma o tamanho efetivo de equipe para cada p. Isso não demonstra
a posição dos workers dos kernels nem, no M5, uso exclusivo dos núcleos P.

A corretude do Dot é verificada também em cada amostra contra a fórmula
esperada, com valores finitos e tolerâncias 1e-9/1e-12. PolyBench compara a saída
completa de cada variante/thread com o sequencial na mesma entrada e toolchain,
em executáveis separados de validação. O header **copiado** do GEMM muda apenas
o formato de dump de duas casas para `%.17g`; a fonte original é preservada.
Nussinov mantém inteiros exatos. Não se afirma prova geral de equivalência ou
ausência de races, nem corretude universal fora dessas entradas.

As fontes/header/utilitário, flags, versões, bibliotecas dinâmicas, executáveis,
Git, afinidade, governor, memória, carga inicial, comandos, códigos de retorno e
stdout/stderr são preservados. Dumps grandes usam gzip sem perda. Os hashes de
saída referem-se aos bytes descomprimidos. Há amostras incrementais em JSONL e
tabelas CSV finais. Em falha, `report.json` fica FAILED e mantém os registros.
Os artefatos desse runner são um arquivo experimental próprio, sem convertê-los
em relatórios do contrato de promoção do pipeline.

```bash
build/analysis-venv/bin/python -B scripts/analyze_scaling.py \
  results/scaling/linux_xeon_2026-11-05 \
  --output results/scaling/analysis_linux_xeon_2026-11-05
```

A análise recusa campanha incompleta, confere hashes, reconstrói cada tempo a
partir da saída registrada e recalcula os resumos. Figuras PNG/SVG/PDF apresentam
tempos, escalabilidade e eficiência, usando mediana e mínimo–máximo. As barras
não são intervalos de confiança. Não se agrupam amostras de variantes distintas.
O desvio padrão dos CSVs novos é amostral (`stdev`), ao contrário do `pstdev`
da consolidação histórica; as medianas não dependem dessa diferença.

## Execução equivalente no M5

Copiar o checkout desta branch com scripts e dados, sem transportar o venv Linux.
Confirmar caminhos e versões reais. Não executar campanhas simultaneamente,
inferência LLM ou testes durante a coleta; registrar modo de energia e carga.

```bash
git status --short --branch
git submodule update --init benchmarks/PolyBenchC-4.2.1
/opt/homebrew/opt/llvm/bin/clang --version
/opt/homebrew/opt/llvm/bin/clang++ --version
python3 -B scripts/benchmark_scaling.py \
  --output results/scaling/mac_m5_nova_coleta \
  --cc /opt/homebrew/opt/llvm/bin/clang \
  --cxx /opt/homebrew/opt/llvm/bin/clang++ \
  --threads 1 2 3 4 5 6 7 8 9 10
```

Manter entradas, fontes, repetições e seed. O script registra `sw_vers`, modelo,
memória, contagem dos níveis de desempenho e energia (`pmset`). Não fixa afinidade
em classes de núcleo no macOS nem mede frequência, temperatura ou largura de
banda física. Bibliotecas e compiladores distintos fazem parte da comparação de
plataformas; não atribuir diferenças somente à ISA ou ao número de núcleos.

Para a análise, criar um venv local com as dependências de gráficos disponíveis
e registrar as versões; o código também aceita `--no-plots` só com Python padrão:

```bash
python3 -B scripts/analyze_scaling.py results/scaling/mac_m5_nova_coleta \
  --output results/scaling/analysis_mac_m5_nova_coleta
```

A comparação principal deve usar pontos comuns 1T–4T, depois descrever 5T–10T
como extensão M5 heterogênea. As dez threads não equivalem a dez núcleos de
desempenho. Eficiência usa p como número de threads e deve ser interpretada com
esse limite. Mais threads não garantem menor tempo em wavefront.

## Métricas e interpretação

Para cada entrada/variante: `S_total=Tseq/Tp`, `S_transf=Tseq/T1`,
`S_par=T1/Tp`, `E_par=S_par/p`. Preservar a identidade
`S_total=S_transf×S_par`. Um ganho já presente em 1T pertence à transformação,
compilação ou localidade; não demonstra escalabilidade multicore.

Dot double realiza aproximadamente duas operações por par de entradas de
16 bytes: 0,125 operação/byte do acesso lógico aos vetores. Isso sugere pressão
de memória para entradas grandes, mas não constitui uma medição de tráfego
DRAM. O modelo Roofline distingue intensidade operacional, banda e teto de
computação; sem contadores e medição de banda, saturação é hipótese, não causa
comprovada. [Williams, Waterman e Patterson, 2009](https://escholarship.org/uc/item/5tz795vq).

GEMM distribui linhas independentes e mantém o laço j contíguo; isso permite
reuso de B e trabalho suficiente por thread. A versão avaliada não é BLAS
otimizada nem inclui blocagem nova. Seu desempenho depende também do conjunto
de trabalho, cache, vetorização e compilador. Escala de uma versão simples não
mede a eficiência frente a uma biblioteca de alto desempenho.

Nussinov mantém dependências entre diagonais. A versão OpenMP usa uma região
paralela persistente, um `omp for` por diagonal e barreira implícita, necessária
antes da próxima diagonal. À medida que d cresce, existem N−d células e o
paralelismo disponível diminui. Cada célula possui uma redução de máximo
no laço k; o acumulador e SIMD podem reduzir acessos ao destino e mudar
o código gerado, separadamente da distribuição de células entre threads.
As garantias de redução e sincronização são definidas pela
[especificação OpenMP](https://www.openmp.org/spec-html/5.2/openmp.html).
As diretivas SIMD não comprovam vetorização eficiente; os diagnósticos do
compilador precisam ser conferidos antes dessa alegação.

Resultados negativos de entradas médias podem ser dominados por inicialização,
barreiras, distribuição e interferência do sistema. Diferenças entre fontes
SIMD semanticamente equivalentes também podem ser ruído ou compilação, e não
superioridade da geração automática. Mantêm-se todas as observações, inclusive
perdas e outliers. Sem controle de temperatura/frequência e novas repetições
de campanha, não se afirma significância estatística nem causalidade arquitetural.

## Dependências ainda abertas

- Receber os três documentos de 05/11 para conferir o plano e incorporar a
  revisão na monografia reescrita correta; não reconstruir seus conteúdos.
- Coletar a campanha equivalente no M5 e confrontar os hashes das fontes.
- Separar comparação histórica contextual de comparação nova com protocolo comum.
- Adequar a monografia ao modelo institucional e conferir o PDF oficial.

## Fechamento Linux

A coleta principal concluiu 46 configurações e 322 amostras, todas com
validação aprovada. Mais dois casos reais do Dot C pelo pipeline terminaram
PREPARED, preservando 50 amostras adicionais e dispensando inferência/promoção.
Os resultados numéricos e a revisão estão em
[revisao_experimentos_2026-11-05/REVISAO.md](revisao_experimentos_2026-11-05/REVISAO.md).

A migração do catálogo Mac expôs caminhos indisponíveis: o carregador agora
aceita um resumo arquivado explicitamente configurado e fixado por hash,
rotulando ARCHIVED_SUMMARY_ONLY. Não há reescrita dos caminhos de evidências
nem conversão de hash divergente/contexto inválido em sucesso. O resumo de
03/11 foi copiado para `results/scaling/reference_consolidated_2026-11-03.json`;
a matriz original permanece intacta. Uma reanálise separada, sem gráficos,
está em `results/scaling/historical_reanalysis_linux_2026-11-05/`.

O teste de isolamento estático também dependia de caminhos arquivados do Mac.
Agora ele executa o analisador real em diretório temporário e verifica as duas
saídas novas, preservando os relatórios históricos. Passou no Linux com Clang
e PolyBench inicializado. A suíte final contém 87 testes unitários aprovados,
23 casos de regressão aprovados e esse teste de isolamento aprovado. Os logs
iniciais de falha também foram preservados.

Os diagnósticos novos confirmaram SIMD no laço k, com largura 4 e intercalação 2,
mas sem benefício no Nussinov grande. A seção `.text` dos executáveis SIMD
manual e automático LARGE é idêntica; os comandos e hashes estão em
`results/scaling/diagnostics_2026-11-05/`.

Para repetir o Dot C equivalente no Mac, em diretórios novos:

```bash
python3 -B scripts/run_pipeline.py --prepare-only \
  --compiler /opt/homebrew/opt/llvm/bin/clang --threads 1 2 3 4 \
  --work-dir results/scaling/mac_pipeline_dot_large_nova_coleta
python3 -B scripts/run_pipeline.py --prepare-only \
  --compiler /opt/homebrew/opt/llvm/bin/clang --threads 1 2 3 4 \
  --benchmark-driver analysis/fixtures/dot_small_benchmark_driver.c \
  --work-dir results/scaling/mac_pipeline_dot_small_nova_coleta
```
