# Posicionamento bibliográfico para publicação

Consulta em 05/11/2026. Comparação dirigida de fontes primárias, não revisão
sistemática. Os trabalhos foram escolhidos pela proximidade com geração
OpenMP, avaliação de código paralelo e integração entre regras e LLM.
Resultados dos autores são identificados como tais: nenhum desses sistemas
foi reproduzido aqui. Não há ranking quantitativo entre máquinas, modelos,
entradas ou protocolos diferentes.

## Fontes e estado de verificação

| Trabalho | Fonte primária efetivamente lida | Estado da publicação e do artefato nesta revisão |
|---|---|---|
| ParEval | [Artigo v3](https://arxiv.org/html/2401.12554v3), [registro bibliográfico](https://arxiv.org/abs/2401.12554v3), [README dos autores](https://github.com/parallelcodefoundry/ParEval/blob/develop/README.md) | Registro informa HPDC 2024, DOI 10.1145/3625549.3658689; README consultado, blob Git `d59630a76c4bdba168597a90b7305c24ea655108` |
| OMPar | [Artigo v1](https://arxiv.org/html/2409.14771v1), [versão do workshop](https://mlforsystems.org/assets/papers/neurips2024/paper12.pdf), [README dos autores](https://github.com/Scientific-Computing-Lab/OMPar/blob/master/README.md) | Preprint e versão hospedada pelo Machine Learning for Systems Workshop, NeurIPS 2024; README consultado, blob `f364ad999ee74ee8a70b235311c720d3f4bc9171` |
| P4OMP | [Artigo v1](https://arxiv.org/html/2506.22703v1), [cópia no site do autor](https://waliabdullah.github.io/papers/hpec_2025_p4omp_abdullah.pdf) | Comparação baseada no preprint v1; não inferir aceite pelo nome do PDF. O [artefato indicado no artigo](https://anonymous.4open.science/r/p4omp/) não pôde ser aberto pela ferramenta de consulta |
| RepoOMP | [Artigo v1](https://arxiv.org/html/2608.05855v1), [registro](https://arxiv.org/abs/2608.05855v1), [README dos autores](https://github.com/Qlalq/RepoOMP_Simplified/blob/main/README.md) | Preprint de 06/08/2026; README do protótipo consultado, blob `f72f8ba4cc7589187ba45a86241d2950b3bce5fb`; há diferenças declaradas entre artigo e protótipo |

Os hashes identificam bytes do README retornados pelo GitHub; não são commits
completos, atestados de correção ou provas de reprodução dos resultados.
O estado editorial indicado nas fontes não constitui avaliação independente
das alegações técnicas. Ausência de informação na documentação lida aparece
como **não verificado**, nunca como prova de ausência do recurso.

## Matriz de tarefas e automação

| Sistema | Problema e unidade de tarefa | Automação e corpus descritos pelos autores | Baselines descritos |
|---|---|---|---|
| ParEval | Gerar funções paralelas e traduzir entre modelos | Benchmark com 420 tarefas; 12 tipos de problema; sequencial e seis modelos paralelos | Modelos de linguagem comparados por tarefa e modelo de execução |
| OMPar | Detectar oportunidade em laços e produzir diretivas | OMPify + MonoCoder-OMP; 770 laços de 175 programas HeCBench; avaliação adicional em ParEval | AutoPar e ICPC; distinguir classificação de laços de transformação de programas completos |
| P4OMP | Transformar C/C++ sequencial usando contexto recuperado | RAG de tutoriais + GPT-3.5-Turbo; 108 programas, dos quais seis excluídos do conjunto considerado paralelizável | Mesmo GPT-3.5-Turbo sem recuperação |
| RepoOMP | Paralelizar hotspots em repositórios com dependências não locais | Grafo MAP, roteamento regras/LLM e contexto STC; artigo descreve 951 hotspots de NPB, BOTS, FFmpeg, NCNN e GROMACS | AutoPar/Polly nas suítes; agente sem contexto estruturado em comparações pareadas; ablações |
| Este TCC, evidência consolidada anterior à ampliação | Admitir uma transformação suportada a partir de evidências verificadas; estudar escalabilidade separadamente | Geração integrada de redução escalar; cinco algoritmos de desempenho, com variantes manuais identificadas; uma LLM decisora | Política determinística e ablação do contexto no estudo de decisão; sequencial e OpenMP 1T nos kernels |

## Matriz de validação e limites

| Sistema | Corretude e desempenho documentados | Artefatos, proveniência e limite relevante |
|---|---|---|
| ParEval | Drivers de compilação/execução e métricas de corretude, desempenho e eficiência | Repositório com prompts, geração, drivers e análise. Não é avaliação do nosso contrato de promoção |
| OMPar | Compila, compara saídas e varia threads; o artigo distingue rótulo original de laço e teste executável | Repositório descreve reprodução; README informa pesos OMPify externos ao repositório. Não se reproduziram instalação nem resultados |
| P4OMP | Autores relatam compilação, comparação manual de saídas em 102 transformações e desempenho em sete benchmarks | Artigo declara publicar código, corpus e logs. Compilação geral de 102/108 e sucesso entre 102 casos considerados paralelizáveis têm denominadores diferentes; não são prova formal |
| RepoOMP | Artigo exige compilação, checks por carga e ganho positivo; inclui avaliação de custo e ablações | README declara protótipo simplificado: NPB/BOTS, verificação parcial, diferenças de threads/agregação e lacunas em relação ao método do artigo. Não assumir equivalência entre ambos |
| Este TCC, evidência já arquivada | Gates e revalidação de promoção; 60 configurações Linux com 15 medições e três aquecimentos, dumps live-out/números; seleção por quase empate | Fontes, binários, comandos, amostras e SHA-256 locais; corretude empírica, bibliotecas não integralmente congeladas, sem prova formal ou detector de races integrado; nova matriz Mac pendente |

Cada célula sobre um trabalho externo resume a fonte primária da primeira
tabela. Os números externos dimensionam o corpus de cada estudo; não são
resultados obtidos neste repositório nem comparação experimental conosco.

## Consequências para a contribuição

ParEval fornece um modelo de avaliação por tarefas diversas. Mais repetições de
um mesmo Dot melhoram a caracterização da execução, mas não acrescentam tarefas
de transformação independentes. [ParEval](https://arxiv.org/html/2401.12554v3).

OMPar e P4OMP impedem apresentar geração OpenMP por modelos ou validação
executável como novidades isoladas. O recorte do TCC usa geração determinística
e uma LLM posterior às medições; isso muda a pergunta avaliada, sem estabelecer
superioridade. [OMPar](https://arxiv.org/html/2409.14771v1),
[P4OMP](https://arxiv.org/html/2506.22703v1).

RepoOMP é especialmente próximo da motivação híbrida baseada em evidências.
Seu artigo exige posicionamento explícito; o protótipo público também mostra
a necessidade de separar especificação publicada e comportamento reproduzido.
Não afirmar que somos o primeiro pipeline híbrido verificável.
[Artigo](https://arxiv.org/html/2608.05855v1),
[escopo do protótipo](https://github.com/Qlalq/RepoOMP_Simplified/blob/main/README.md).

A contribuição defensável do TCC é uma implementação delimitada e auditável,
com ligação entre evidência e promoção, avaliação da escalabilidade das variantes
e estudo crítico do custo/limites de um decisor subordinado a regras. Um estudo
novo de diagnóstico deve ter gabarito e partição de avaliação próprios. Seu
resultado não pode ser antecipado como ganho, nem convertido em reparo autônomo.

## Comparação experimental justa que pode ser executada

O baseline mínimo local usa a mesma entrada, compilador, driver e orçamento,
variando somente o método investigado. Na admissão, comparar regras, Coordinator
e ablação. No diagnóstico, comparar diagnósticos/ações sob gabarito oculto e
contar falhas. Na transformação, reportar cobertura por fonte e motivo de
recusa, preservando programas suportados e negativos no denominador. No
desempenho, manter separados `Tseq/Tp` e `T1/Tp`.

Uma comparação executável com OMPar/P4OMP/RepoOMP exige instalação comprovada,
disponibilidade de pesos/serviço, adaptação validada e entradas compartilhadas.
Não foi realizada aqui. Os resultados publicados em seus hardwares não suprem
esse experimento; a matriz é uma comparação de desenho e escopo.

## Critérios de fechamento bibliográfico

Antes de submeter: escolher veículo, conferir sua chamada e limite de páginas,
atualizar versões consultadas e verificar novas publicações. Registrar consulta,
versão e identidade do artefato utilizado. Reproduzir uma ferramenta externa
só quando couber na pergunta e nos recursos; declarar baseline indisponível
em vez de substituir resultados por estimativa.
