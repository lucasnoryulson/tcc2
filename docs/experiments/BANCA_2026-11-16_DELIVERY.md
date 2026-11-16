# Fechamento experimental e preparação para banca — 16/11/2026

## Base, preservação e estado dos seis itens

A etapa começou com `git fetch origin main`, confirmando `601b813` como a main
remota mais recente naquele momento. A branch de trabalho é
`feat/defense-readiness-2026-11-16`, criada a partir dessa referência. Os dois
commits locais AXPY ainda ausentes da main foram reaplicados por cherry-pick
(`48114f2`, `c364407`), sem criar merge. A main local permaneceu em `cc5406b`.
Nenhum push, merge ou publicação externa foi realizado.

| Item original | Entrega nesta etapa | Limite restante |
|---|---|---|
| 1. Pipeline até o resultado final | AXPY sob o novo contrato: três decisões reais LLM e três decisões determinísticas, com seis promoções locais e revalidações PASS | São tentativas sobre uma única evidência congelada, não seis pipelines independentes |
| 2. Validação e configuração | 161 testes sem falhas/skips, 23 casos de regressão, configuração 4T e candidato preservados por SHA-256 | Corretude empírica, sem prova formal ou detector geral de races |
| 3. Recorte da automação | Distinção revisada entre Dot/AXPY gerados, variantes manuais/específicas e decisão LLM | Sem geração universal, busca de candidatos ou reparo autônomo |
| 4. Avaliação científica dos agentes | Três inferências reais AXPY concordaram com a política, sem alterar o speedup; custo medido separadamente | Mesmo contexto, modelo e host; sem ablação adicional, julgamento humano ou generalização |
| 5. Experimentos e reprodução | Duas novas sessões AXPY, todos os números de threads 1–10, três entradas, 990 medições e 198 aquecimentos | Contadores perf Linux não coletados neste Mac; roteiro de seis kernels preparado |
| 6. Monografia e defesa | Revisão integral da fonte consolidada, Word/PDF de 94 páginas, 35 tabelas e 27 figuras; revisão anterior preservada | Modelo institucional completo, layout nativo Word, dados acadêmicos e aprovação/ensaio da defesa continuam externos |

## Experimentos efetivamente executados

O [protocolo novo](AXPY_ALL_THREADS_PROTOCOL_2026-11-16.json) foi fixado em
`62f84f0`, antes da coleta. Fonte e drivers são os fixtures existentes;
somente as constantes N e chamadas internas do benchmark foram especializadas.
Cada sessão contém 33 configurações: três entradas × (sequencial + OpenMP
1/2/3/4/5/6/7/8/9/10T). Cada configuração tem quinze medições e três aquecimentos,
em rodadas completas aleatórias com seed 2026. As escolhas da primeira sessão
foram congeladas antes da segunda; o intervalo entre sessões foi 118,834 s.

Todos os elementos de saída foram verificados, inclusive no tamanho temporizado,
fora do intervalo do kernel. Os 66 pares configuração–sessão passaram. As flags
continuam sequencial `-O3` e candidato `-O3 -fopenmp`; OpenMP usa
`OMP_DYNAMIC=FALSE`, `OMP_PROC_BIND=TRUE`, `OMP_PLACES=cores`. O probe confirmou
todos os tamanhos de equipe, sem comprovar alocação por classe de núcleo.

| Entrada | Escolha S1 congelada | Ganho na S2 | Excesso sobre menor mediana S2 | Escolha repetida na S2 |
|---|---:|---:|---:|---|
| 1.024 | Sequencial | 1,000× | 0% | Sim |
| 1.000.000 | 6T | 1,394× | 2,088% | Não: a S2 recomendou 4T |
| 10.000.000 | 4T | 1,716× | 0% | Sim |

A adequação operacional usa o limiar de 2%: houve uma inadequação em três
casos, preservada sem retuning. No tamanho intermediário, o ponto de menor
mediana posterior foi 10T; a recomendação S2 4T deriva do quase empate.
Isso não é falha funcional nem teste estatístico de diferença. Mediana, média,
DP amostral, MAD, IQR, IC95% condicional bootstrap, speedups e eficiência estão
nos CSVs por sessão. Somatórios do tempo de kernel reconstruído e custos de
parede estão em arquivos separados, sem dupla contagem.

O candidato tem SHA-256
`4877d57708a392900b11ca3e6cc90e3e1e4c2497ef5c2e58460268cdfc94d1d1`.
É idêntico ao da campanha anterior de seis equipes: o ganho maior não é uma
nova otimização. O baseline sequencial também ficou mais lento e a grade mudou.
O histórico de 03/11 usa outro contrato; a execução de 105 medições PREPARED
continua sendo validação técnica. As 630 medições da campanha anterior e as
990 desta campanha não foram juntadas.

Arquivos reais:

- [sessões e amostras brutas](../../results/axpy_scientific/mac_m5_all_threads_2026-11-16/);
- [estatísticas e gráficos por sessão](../../results/axpy_scientific/analysis_mac_m5_all_threads_2026-11-16/);
- [relatório derivado, tempos totais e amortização](../../results/defense_readiness/2026-11-16/REPORT.md).

## Inferência real, promoção e custo

O estudo de custo reutilizou a evidência da maior entrada S1. Após as duas
sessões de desempenho, executou três tentativas por braço, alternando a ordem
determinístico/LLM. São seis decisões e seis promoções com nova compilação e
corretude; o prefixo determinístico de 109,662 s foi medido uma única vez.
Não são seis execuções independentes ponta a ponta.

Ollama 0.34.0, `llama3.1:8b`, digest `46e0c10c039e`, Q4_K_M, contexto efetivo
4096. As três chamadas receberam 2.050 tokens e geraram 205 cada, com
`done_reason=stop`, sem erro ou timeout. A latência foi 59,042/54,950/61,731 s.
O servidor reportou `size_vram=5263327231`; não se inferiu utilização de GPU,
energia ou causa da latência a partir dessa alocação. O modelo carregado pelos
ensaios foi descarregado ao final; o servidor já existente não foi encerrado.

| Braço | Decisão + validação mediana | Total contabilizado mediano | Equilíbrio mediano usando S2 |
|---|---:|---:|---:|
| Determinístico | 0,000024 s | 110,593 s | 17.966 chamadas |
| Coordinator | 59,041822 s | 170,709 s | 27.731 chamadas |

Os custos totais foram calculados por tentativa antes de resumir, incluindo a
promoção, sem somar medianas de componentes para reconstruir o total. Ambos os
braços usaram o mesmo candidato 4T; nenhum ganho do kernel foi atribuído à LLM.
O equilíbrio pressupõe reutilização, entrada equivalente e economia positiva;
não garante manutenção do ganho em uso futuro. O CSV também separa amortização
somente da decisão, somente do prefixo e dos totais contabilizados. No pequeno,
sem ganho, não há ponto de amortização.

Fonte: [custos, prompts, decisões, metadados e bundles](../../results/pipeline_cost/axpy_mac_m5_all_threads_2026-11-16/).
Alguns imports da inferência foram recuperados do commit de invocação `22e5ed2`
na validação final; isso é distinguido dos hashes capturados dentro do harness.

## Testes e verificação

A bateria final executou duas vezes a suíte completa nesta etapa. A última
execução passou **161 testes em 61,318 s**, sem falhas ou skips. Os seis scripts
de regressão passaram em **23 casos**, além do isolamento estático e da sintaxe
do wrapper Linux. Os testes focados prévios passaram em 13 casos AXPY/contrato
e dez casos custo/profiling. Não se somam repetições da mesma suíte como testes
distintos. Avisos legados `ResourceWarning` de CSV não fechado foram mantidos
nos logs, sem alteração dos dados ou falsa conversão em falha.

A verificação final recompôs políticas, bootstrap e amortização; conferiu
quatro sessões científicas intactas (as duas antigas e as duas novas), seis
bundles, revisão anterior, referências locais, A4, margens, campos de sumário e
paginação e numeração completa de tabelas/figuras. O PDF tem 94 páginas sem
página vazia. A inspeção visual identificou e corrigiu legendas órfãs e quebras
de tabelas curtas. O PDF é exportação de conteúdo ReportLab, não renderização
nativa do Word. O sumário do Word tem campo atualizável, cuja paginação nativa
precisa ser conferida no aplicativo final.

Logs: [regressões finais](../../results/validation/defense_readiness_2026-11-16/regression_final/report.json).
Auditoria: [artefatos verificados com pendências externas explícitas](../../results/validation/defense_readiness_2026-11-16/artifacts/report.json).

## Revisão acadêmica e institucional

Foram lidos e revisados resumo/abstract, introdução/objetivos, fundamentação,
arquitetura/algoritmos, metodologia, resultados, discussão, ameaças, conclusão
e referências. As mudanças principais foram:

- Correção de trechos que ainda descreviam a coleta M5 como futura.
- Separação das duas campanhas científicas AXPY, do histórico e da validação técnica.
- Explicação dos limites entre estrutura estática, hipóteses de gargalo,
  instrumentação, contadores e seleção de desempenho.
- Síntese de seis kernels com evidência, hipótese e confirmação necessária.
- Custo real AXPY da LLM e publicação, com prefixo compartilhado e amortização posterior.
- Preservação do resultado negativo do holdout, sem afirmar causalidade ou superioridade.
- Referências reordenadas, complementadas com documentação Ollama/perf; 35 tabelas
  e 27 figuras numeradas de modo consistente entre fontes/exportações.

As fontes primárias de OpenMP, ParEval, AutoGen, PolyBench, OMPar, P4OMP,
RepoOMP, GCC e Ollama foram confrontadas com as alegações relevantes. Os
trabalhos relacionados não foram reproduzidos e a revisão não é sistemática.
As tentativas de reabrir Amdahl/ACM e o repositório Roofline encontraram bloqueio
ou timeout; os metadados já arquivados foram conservados, sem alegar releitura
integral desses dois artigos nesta etapa.

A capa pública PUCRS disponível no repositório foi conferida com a
[orientação institucional](https://biblioteca.pucrs.br/apoio-a-pesquisa/capas-padrao-pucrs/capa-para-tcc/).
O [modelo completo ABNT](https://biblioteca.pucrs.br/apoio-a-pesquisa/modelos-de-normas-tecnicas-de-documentacao/trabalhos-academicos-abnt/)
continua exigindo login individual. Não foram inventados orientador, integrantes
da banca, folha de aprovação ou confirmação institucional. A capa permanece em
arquivo separado, para composição conforme o modelo completo; esta entrega não
afirma que o PDF já contém todos os elementos pré-textuais institucionais.

Arquivos principais:

- [Markdown](../monografia/MONOGRAFIA_CONSOLIDADA.md), [Word](../monografia/MONOGRAFIA_CONSOLIDADA.docx) e [PDF](../monografia/MONOGRAFIA_CONSOLIDADA.pdf);
- [manifesto final](../monografia/BANCA_2026-11-16_MANIFEST.json) e [bibliografia](../monografia/referencias_consolidada.bib);
- revisão anterior de 82 páginas em `MONOGRAFIA_CONSOLIDADA_PRE_BANCA_2026-11-16.*`;
  a revisão de 78 páginas e demais manuscritos históricos também foram preservados.

## Pendências efetivas e reprodução

1. Executar o [roteiro Linux de contadores](LINUX_COUNTERS_FOLLOWUP_2026-11-16.md)
   em host Linux disponibilizado, com eventos/permissões realmente existentes.
   Nenhum contador foi inventado no Mac.
2. Aplicar o modelo institucional completo, preencher dados acadêmicos reais,
   compor os elementos pré-textuais e conferir o Word nativamente após atualizar
   os campos. Isso não foi certificado por inspeções de XML/PDF.
3. Revisão humana do conteúdo, aprovação acadêmica e preparação/ensaio da defesa.

Não é necessário ampliar kernels, agentes ou arquiteturas para resolver essas
pendências. A condição de energia (bateria 3–4%, indicada em carga), o mesmo
host/dia e a ausência de controle térmico permanecem ameaças declaradas.

Para repetir AXPY no Mac, use um nome **novo** em todos os diretórios:

```bash
export PATH=/opt/homebrew/opt/llvm/bin:$PATH
python3 -B scripts/evaluate_axpy_campaign.py prepare \
  --protocol docs/experiments/AXPY_ALL_THREADS_PROTOCOL_2026-11-16.json \
  --directory results/axpy_scientific/mac_repeat_NEW
python3 -B scripts/evaluate_axpy_campaign.py session01 --directory results/axpy_scientific/mac_repeat_NEW
python3 -B scripts/evaluate_axpy_campaign.py freeze --directory results/axpy_scientific/mac_repeat_NEW
sleep 30
python3 -B scripts/evaluate_axpy_campaign.py session02 --directory results/axpy_scientific/mac_repeat_NEW
python3 -B scripts/evaluate_axpy_campaign.py analyze \
  --directory results/axpy_scientific/mac_repeat_NEW --output results/axpy_scientific/analysis_mac_repeat_NEW
```

Não execute inferência ou testes junto aos benchmarks. O estudo de custo aceita
`--prepared-run CAMINHO_RUN` para decisões/promoções novas sobre evidência
íntegra, com saída nova e orçamento previamente declarado. O protocolo da
campanha científica não é alterado retroativamente.

Para testar e exportar, use um venv local com `requirements-experimental.txt`:

```bash
python3 -B scripts/validate_mac_evaluation.py --output results/validation/repeat_NEW/regression
python3 -B scripts/build_defense_material.py
python3 -B scripts/validate_defense_readiness.py \
  --output results/validation/repeat_NEW/artifacts \
  --regression results/validation/repeat_NEW/regression
```

O gerador final lê a fonte consolidada atual e preserva a revisão anterior.
Ele atualiza suas exportações: incorporar edições feitas apenas no Word ao
Markdown antes de executar. Os geradores históricos são específicos das suas
revisões; não os use para substituir o texto final. O manifesto antigo AXPY
continua descrevendo a revisão de 82 páginas, agora preservada em PRE_BANCA,
enquanto o manifesto BANCA descreve os arquivos principais atuais.

## Arquivos e commits

Novos scripts: `report_defense_readiness.py`, `build_defense_material.py`,
`validate_defense_readiness.py`, `profile_linux_followup.py` e seu teste.
Atualizados: harness AXPY/testes, medição de custo/testes, wrapper Linux,
exportador de tabelas/legendas, monografia/bibliografia, README e estado do TCC.
Novos protocolos, campanhas, análises, seis bundles e relatórios de validação
ficam nos diretórios próprios citados acima, acompanhados por hashes.

Commits de protocolo: `62f84f0` (AXPY 1–10T) e `22e5ed2` (custos/perf).
O commit de entrega é o que adiciona este relatório; consulte
`git log -1 --oneline -- docs/experiments/BANCA_2026-11-16_DELIVERY.md`.
Nenhuma operação de push ou merge é parte desta entrega.
