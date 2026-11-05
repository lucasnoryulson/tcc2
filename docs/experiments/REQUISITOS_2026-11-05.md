Estamos continuando meu Trabalho de Conclusão de Curso (TCC2) em Ciência da Computação na PUCRS.

**Repositório:** `lucasnoryulson/tcc2`

**Objetivo:** fortalecer a avaliação experimental multiplataforma do sistema de paralelização automática com OpenMP e atualizar a monografia para atender às críticas do orientador.

O último estado mencionado do meu checkout é a branch `feat/mac-pipeline-validation`, commit `32ae80b`. Confira o HEAD atual antes de trabalhar. Preserve todas as alterações locais.

## 1. Contexto do projeto

O projeto implementa um pipeline híbrido de análise e otimização de código C:

1. Static Analyzer: extrai informações estruturais utilizando Clang/AST.
2. Dependence Analyzer: identifica dependências de dados.
3. Pattern Classifier: classifica DOALL, REDUCTION, STENCIL, WAVEFRONT e MIXED.
4. Strategy Planner: seleciona transformações suportadas.
5. Code Transformer: aplica transformações determinísticas.
6. Correctness Gate: compila e compara os resultados.
7. Performance Gate: mede diferentes configurações OpenMP.
8. Performance Selector: escolhe uma configuração medida.
9. Context Builder: reúne as evidências.
10. Coordinator: utiliza LLM para decidir ACCEPT, RETUNE, MODIFY ou REJECT.
11. Candidate Promotion Executor: revalida o candidato e publica código e evidências quando os requisitos são satisfeitos.

**Limitação científica importante:** o caminho integrado de geração automática está demonstrado principalmente para Dot Product/redução escalar. GEMM, Jacobi-2D e Covariance possuem variantes OpenMP manuais. Nussinov tem transformações adaptativas específicas que partem de uma base OpenMP manual.

Não confundir essas categorias.

O Coordinator não pode receber crédito pelos ganhos produzidos por transformações manuais ou determinísticas. A última avaliação documentada com `qwen2.5:3b` teve quatro inferências expiradas por timeout; verificar se a branch atual contém resultados posteriores.

## 2. Motivação dos experimentos

Executamos experimentos em dois ambientes porque queremos investigar como a arquitetura e a quantidade de núcleos influenciam a escalabilidade e a seleção de configurações paralelas.

Ambientes históricos:

**Linux**
- Intel Xeon E3-1225 V2.
- Arquitetura x86-64.
- Quatro núcleos.
- Compilador histórico Clang 18.

**Mac**
- Apple M5.
- Arquitetura ARM64.
- Dez núcleos registrados.
- Compilador histórico Homebrew Clang 23.

São arquiteturas diferentes; não podemos atribuir qualquer diferença exclusivamente à quantidade de núcleos.

## 3. Resultados históricos disponíveis

A matriz consolidada está em `results/consolidated/REPORT.md`.

Resultados existentes:

| Algoritmo | Linux | Mac |
|---|---|---|
| GEMM | 3,079×, 4 threads | 4,691×, 9 threads |
| Jacobi-2D | 1,189×, 2 threads | 2,533×, 7 threads |
| Covariance | 2,183×, 4 threads | 4,183×, 10 threads |
| Nussinov manual | 3,566×, 4 threads | 2,592×, 4 threads |
| Dot Product automático | 1,258×, 2 threads | 3,753×, 10 threads |

Outras campanhas:
- Nussinov SIMD manual: 4,037× com 4 threads.
- Nussinov com transformação adaptativa específica: 4,106× com 4 threads, mas hardware não registrado na campanha canônica.
- Wavefront tiled no Mac: 3,400×, bloco 64 e 4 threads.
- Dot Product local Linux, N=10.000.000: 1,191× com 2 threads.
- Dot Product local Linux, N=1.024: configuração paralela rejeitada por ausência de ganho.

A consolidação anterior reuniu 19 campanhas, 161 configurações e 515 tempos individuais recuperados.

**Não declare essas campanhas como equivalentes ou totalmente reproduzíveis:** várias não possuem vínculo histórico completo entre fonte, compilador, corretude e medição.

## 4. Sua tarefa principal: experimentos reproduzíveis

Primeiro, leia e examine estes arquivos:

- `AGENTS.md`
- `README.md`
- `docs/STATUS_TCC.md`
- `docs/EXPERIMENT_REPRODUCTION.md`
- `docs/experiment_catalog.json`
- `results/consolidated/REPORT.md`
- `scripts/benchmark.py`
- `scripts/consolidate_experiments.py`
- `analysis/performance_selector.py`
- `scripts/run_pipeline.py`
- `docs/monografia/BASE_MONOGRAFIA.md`

**Priorize os seguintes algoritmos:**

1. Dot Product — REDUCTION.
2. GEMM — DOALL.
3. Nussinov — WAVEFRONT.

Se possível, inclua Jacobi-2D e Covariance como avaliações complementares.

### 4.1. Preparar o Linux

Registre:

- Commit e branch.
- Estado do Git e submódulos.
- Modelo do processador.
- Quantidade de núcleos físicos, lógicos e CPUs disponíveis.
- Arquitetura e sistema operacional.
- Versões dos compiladores.
- Flags de compilação.
- Versão Python.
- Variáveis OpenMP.
- SHA-256 dos arquivos utilizados.
- Tamanhos exatos das entradas.

Verifique que o compilador escolhido suporta OpenMP.

### 4.2. Executar os benchmarks

Implemente ou adapte um harness reproduzível, sem sobrescrever os resultados antigos.

No Linux, teste o sequencial e OpenMP com 1, 2 e 4 threads, desde que essas configurações sejam compatíveis com o hardware disponível.

Utilize:

- Três execuções de aquecimento por configuração.
- Quinze medições externas por configuração.
- Ordem das configurações alternada de maneira reprodutível.
- Entradas idênticas para as variantes comparadas.
- Validação de corretude para cada configuração medida.
- Registro de tempos individuais, não apenas médias.
- Captura de stdout, stderr e erros.
- Diretórios exclusivos por campanha.

Para GEMM e Nussinov, utilize o mesmo conjunto de dados PolyBench e preserve o SHA do submódulo.

Para Dot Product, separe claramente o caso C com transformação automática do benchmark C++ manual.

O harness existente `scripts/benchmark.py` executa cinco repetições e utiliza uma ordem fixa. Considere-o ponto de partida, não protocolo final.

### 4.3. Calcular as métricas

Utilize:

`T_seq`: mediana do sequencial original.

`T_1`: mediana da mesma variante OpenMP com uma thread.

`T_p`: mediana da mesma variante OpenMP com p threads.

Calcule:

- Speedup total = `T_seq / T_p`.
- Speedup da transformação = `T_seq / T_1`.
- Escalabilidade paralela = `T_1 / T_p`.
- Eficiência paralela = `(T_1 / T_p) / p`.

Registre também mediana, média, desvio padrão, MAD, IQR e número de amostras.

Calcule intervalos de confiança por bootstrap somente quando houver amostras brutas suficientes e informe o método.

Distinga a configuração mais rápida daquela recomendada pelo Performance Selector, que considera quase empates de até 2%.

### 4.4. Gerar gráficos

Produza:

1. Speedup total × quantidade de threads.
2. Escalabilidade paralela × quantidade de threads.
3. Eficiência paralela × quantidade de threads.
4. Tempo de execução × configuração.
5. Configuração recomendada por algoritmo.
6. Comparações Linux × Mac, quando os dados forem realmente comparáveis.

Utilize gráficos SVG/PNG adequados para inserção na monografia.

Não coloque resultados de máquinas diferentes na mesma curva como se fossem uma única campanha.

## 5. Comparação com Mac

Neste momento estamos trabalhando no Linux.

Execute tudo o que for possível localmente e prepare um script reproduzível para executar no Apple M5 posteriormente.

O script do Mac deve usar os mesmos códigos, entradas e critérios de corretude. Sugestão de threads: 1, 2, 4, 6, 8 e 10.

O subconjunto de comparação direta com Linux será 1, 2 e 4 threads, condicionado à equivalência real das variantes e das entradas.

Não invente medições do Mac nem substitua resultados históricos por medições atuais.

## 6. Atualização da monografia

Meu orientador criticou a versão anterior porque:

- Parecia excessivamente produzida por IA.
- Não estava no formato institucional correto.
- Não apresentava algoritmos suficientes.
- Tinha poucas figuras.
- Explicava superficialmente a arquitetura.
- Concentrava os resultados em Dot Product.

Quero corrigir essas deficiências.

A base disponível no GitHub é `docs/monografia/BASE_MONOGRAFIA.md`.

Uma versão reescrita mais recente também foi produzida fora do repositório, mas não está disponível neste checkout. Portanto, **não bloqueie o trabalho esperando esse arquivo**. Utilize a base existente e amplie-a de maneira tecnicamente rigorosa. Preserve a versão original e produza a revisão em arquivos novos.

A nova versão precisa:

1. Detalhar entradas, saídas, algoritmos e contratos dos componentes.
2. Incluir pseudocódigos baseados nas funções reais.
3. Mostrar exemplos concretos de código C sequencial e OpenMP.
4. Apresentar a arquitetura e seu fluxo de decisão em figuras.
5. Criar uma seção específica sobre os ambientes Linux e Apple M5.
6. Detalhar o protocolo experimental.
7. Apresentar resultados de Dot Product, GEMM e Nussinov, além dos casos complementares.
8. Analisar por que as configurações recomendadas podem diferir entre plataformas.
9. Separar os resultados históricos das campanhas novas.
10. Discutir explicitamente limitações e ameaças à validade.

**Não tente esconder limitações nem inventar o papel dos agentes.**

O objetivo é produzir uma monografia defensável perante uma banca de Ciência da Computação, não somente melhorar a aparência do texto.

## 7. Arquivos de saída esperados

Organize o trabalho em novos caminhos, por exemplo:

- `scripts/benchmark_multiplatform.py`
- `scripts/run_multiplatform_linux.sh`
- `scripts/run_multiplatform_mac.sh`
- `results/multiplatform/<identificador-da-campanha>/`
- `docs/experiments/MULTIPLATFORM_REPORT.md`
- `docs/experiments/MULTIPLATFORM_METHODOLOGY.md`
- `docs/monografia/REVISAO_MULTIPLATAFORMA.md`

Se houver ferramentas para exportação, gere também Word e PDF de revisão.

Preserve a monografia original e não sobrescreva resultados históricos.

## 8. Critérios de conclusão

Não pare após escrever um planejamento.

Quero que você:

1. Examine o repositório e identifique os scripts existentes que podem ser reutilizados.
2. Implemente as alterações necessárias.
3. Execute os benchmarks reais no Linux.
4. Confira a corretude dos resultados.
5. Produza os gráficos e relatórios.
6. Atualize a monografia com os resultados obtidos.
7. Prepare a execução equivalente no Mac.
8. Execute os testes de regressão.
9. Apresente o resumo numérico da campanha.

Trabalhe em uma branch própria. Preserve alterações locais. Não faça push nem merge sem autorização.

Ao finalizar, informe exatamente:

- Quais testes foram executados.
- Quais configurações foram medidas.
- Tempos e speedups obtidos.
- Qual configuração foi selecionada.
- Quais arquivos foram criados ou modificados.
- Quais resultados dependem de execução posterior no Mac.
- Quais limitações científicas permanecem.

Não confunda implementação concluída com experimento validado.