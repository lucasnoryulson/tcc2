# Plano da avaliação no Apple M5 — 16 de novembro de 2026

## Diagnóstico e preservação

A base é `0d3b54733f4c04a699c5f4e1787b1a7f21ef6f1b`, ponta remota de
`feat/publication-strengthening-2026-11-05`. A branch de execução é
`feat/mac-experimental-evaluation-2026-11-16`, criada em worktree separado.
O checkout original `tcc2/`, na branch `feat/mac-pipeline-validation`, conserva
suas alterações locais, incluindo AXPY. A monografia de entrada é
`docs/monografia/REVISAO_PUBLICACAO.md`, acompanhada de Word e PDF de 70 páginas.
As três versões anteriores serão preservadas.

O primeiro diagnóstico consultou referências antes de a atualização remota se
tornar disponível e concluiu prematuramente que a base estava ausente. A nova
inspeção confirmou a base e eliminou o bloqueio sem exigir ação do autor.

O coletor existente implementa protocolo `multiplatform-v2`, entradas MEDIUM e
LARGE, dois tamanhos de cada Dot, três aquecimentos, quinze medições externas,
seed 2026 e validação por configuração. O comparador exige identidade dos
fontes/headers/drivers, dimensões, flags e protocolo. Os scripts de análise já
calculam DP amostral, MAD, IQR e bootstrap pareado por rodada (5.000 réplicas).

Preflight: Apple M5, modelo Mac17,2, ARM64, 16 GiB, dez núcleos físicos/lógicos,
quatro de desempenho e seis de eficiência; macOS 26.6.2; LLVM Homebrew 23.1.1.
Há somente Command Line Tools; `xcrun xctrace list templates` informa que a
ferramenta não está disponível. A bateria estava em 22% e descarregando.
Energia, carga e eventuais avisos térmicos serão registrados por sessão; não se
alega controle de frequência, afinidade dos kernels ou isolamento do host.

## Ordem de execução

1. Verificar PolyBench no SHA fixado, OpenMP real e testes relevantes. Confirmar
   os bytes usados na campanha Linux antes de adotar curvas conjuntas.
2. Executar `scripts/run_multiplatform_mac.sh` em diretório novo, com sequencial
   e OpenMP 1/2/4/6/8/10T para Dot C automático, Dot C++ manual, GEMM, Nussinov
   manual/SIMD manual/SIMD adaptado, Jacobi-2D e Covariance. Conservar stdout,
   stderr, comandos, fontes, binários, aquecimentos, tempos e falhas.
3. Congelar a decisão do Selector usando somente a primeira sessão. Executar
   nova sessão completa com protocolo idêntico, possibilitando avaliação
   independente da recomendação, do máximo de threads, da menor mediana da
   primeira sessão e do sequencial, com comparação à melhor configuração
   observada na segunda. Não reunir as amostras das sessões.
4. Antes de inspecionar a segunda sessão, definir recomendação inadequada como
   tempo mais de 2% acima do melhor resultado incluindo sequencial. Informar
   também o arrependimento percentual contínuo, casos que perdem para o
   sequencial, sensibilidade ao limiar e estabilidade entre sessões. O critério
   é descritivo; não equivale a significância estatística.
5. Investigar gargalos por instrumentação disponível e experimentos auxiliares
   separados. Tráfego estimado a partir do algoritmo e largura de banda efetiva
   não equivalem a contadores físicos de DRAM. Preparar comandos Linux para
   contadores que o Mac não disponibilize.
6. Medir custos por etapa em execuções reais e separadas da coleta principal.
   Distinguir compilação, execução de validação e benchmark dos processos que
   os agregam; evitar dupla contagem. Comparar política determinística e LLM
   sobre as mesmas evidências. Calcular `ceil(custo / (Tseq - Topt))` somente
   quando a economia por execução for positiva; preservar falhas e timeouts.
7. Verificar arquivos, gerar estatística por sessão e curvas Linux/Mac nos
   pontos comuns 1/2/4T; mostrar a extensão M5 até 10T separadamente.
8. Atualizar a monografia em novos Markdown/Word/PDF datados, acrescentando
   metodologia, resultados, interpretação, ameaças e respostas às questões.
   Preservar o resultado negativo anterior da avaliação LLM.
9. Executar testes proporcionais, conferir integridade dos históricos e gerar
   commits locais organizados. Não fazer push nem merge.

## Critérios de relato

Nenhum resultado será presumido pela existência do script. Serão distinguidos
sucesso de software, coleta completa, compatibilidade de plataformas e suporte
às hipóteses científicas. Amostras desfavoráveis não serão removidas. Os ganhos
de transformação, paralelismo e seleção terão seus próprios baselines. A LLM
receberá apenas o efeito de decisões que efetivamente tomou. Temperatura,
frequência, banda física, cache misses e migração entre núcleos só serão
apresentados como medidos quando houver instrumento e saída correspondentes.
