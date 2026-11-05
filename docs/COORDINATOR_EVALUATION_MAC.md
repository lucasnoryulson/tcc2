# Item 4 — campanha pareada no Mac

Executada em **3 de novembro de 2026**. O diretório canônico é
`results/coordinator_evaluation/mac_2026-11-03/evaluation-4vgn5q8n/`.
A campanha terminou `INCOMPLETE` porque seis respostas concluídas violaram o
schema operacional; não houve timeout nem repetição silenciosa.

## Ambiente e protocolo

- MacBook Pro `Mac17,2`, Apple M5, 10 núcleos (4 de desempenho e 6 de eficiência), 16 GB;
- macOS 26.6.2, arm64; Python 3.15.2;
- LLVM Homebrew 23.1.1 com OpenMP;
- Ollama 0.34.0;
- `llama3.1:8b`, ID local `46e0c10c039e`, Q4_K_M, limite de contexto informado de 131.072 tokens;
- threads 1, 2 e 4; cinco medições externas por configuração;
- três repetições por caso/modo, temperatura zero, seed 2026 e timeout de 600 s;
- dois tamanhos de Dot Product e três modos: determinístico, Coordinator completo e ablação sem análises estruturadas.

Os prompts observados consumiram 2.050 tokens, abaixo do limite informado. Os
três modos reutilizaram os mesmos bytes, medições e gates em cada caso. As
repetições da decisão não são novas amostras do tempo do kernel.

## Resultados

| Caso | Modo | Respostas válidas | Concordância | Aceitação efetiva | Mediana da decisão |
|---|---|---:|---:|---:|---:|
| Grande | Determinístico | 3/3 | 100% | 100% | 0,000026 s |
| Grande | Coordinator | 3/3 | 100% | 100% | 3,681 s |
| Grande | Sem análises | 3/3 | 100% | 100% | 9,010 s |
| Pequeno | Determinístico | 3/3 | 100% | 0% | 0,000011 s |
| Pequeno | Coordinator | 0/3 | 0% | 0% | 8,918 s |
| Pequeno | Sem análises | 0/3 | 0% | 0% | 6,097 s |

No caso grande, a configuração de 4 threads apresentou speedup de 1,67272x
contra o sequencial e escalabilidade de 1,67266x contra OpenMP 1T. Os dois
braços LLM repetiram a admissão determinística em 3/3 tentativas e produziram o
mesmo resultado final. Não houve ganho de desempenho atribuível à decisão LLM.

No caso pequeno, nenhuma configuração paralela era admissível. Em todas as seis
chamadas, o modelo escolheu semanticamente `REJECT`, mas combinou
`recommended_threads: 1` com `next_action: SEND_TO_CODER`. O contrato rejeitou
as respostas porque a thread não pertencia às configurações medidas admissíveis
e `REJECT` exige `REJECT_CANDIDATE`. Os gates mantiveram o fallback sequencial;
nenhum candidato inadmissível foi promovido.

Cada braço LLM realizou seis chamadas, observou 12.300 tokens de prompt e gerou
399 tokens. Considerando os dois casos, a mediana da decisão foi 6,299 s no
Coordinator completo e 7,553 s na ablação. A inversão de latência entre braços
e casos não deve ser interpretada causalmente: ordem, carregamento e variabilidade
do servidor confundem a comparação, e há apenas três repetições.

## Interpretação de R3

Nesta amostra, retirar as análises estruturadas não alterou aceitação, validade
ou resultado final: os dois braços LLM tiveram comportamento idêntico em cada
caso. Para o candidato elegível, a LLM reproduziu uma política determinística já
suficiente e adicionou latência. Para o caso não elegível, a intenção de rejeitar
foi conservadora, mas o formato operacional foi consistentemente inválido.

Assim, **não foi demonstrado benefício adicional do Coordinator nem das análises
estruturadas para a decisão de admissão neste desenho**. O resultado também não
prova inutilidade geral de LLMs: são dois tamanhos de um kernel, um modelo e uma
política binária sobre candidato já gerado. O estudo não avalia geração de código,
busca por candidatos, reparo autônomo ou superioridade sobre geração monolítica.

`INCOMPLETE` é mantido como dado científico e de engenharia: as doze inferências
terminaram, mas somente seis respostas LLM foram admissíveis. A conclusão não
substitui respostas inválidas por decisões corrigidas nem repete chamadas para
obter uma campanha positiva.

## Melhoria do contrato e replicação v4

O diagnóstico da campanha original identificou um defeito real no contrato: o
schema exigia `recommended_configuration`, mas não declarava a propriedade e
simultaneamente proibia propriedades extras. O contrato foi corrigido e
reforçado em três níveis:

- schema completo, com descrições operacionais compatíveis com o modo
  estruturado do Ollama;
- tabela explícita entre decisão, ação e campos nulos no prompt;
- validação determinística que proíbe configuração operacional em RETUNE,
  MODIFY e REJECT, e proíbe ACCEPT sem `selection.status == SELECTED` e uma
  recomendação realmente medida.

Uma tentativa intermediária com `oneOf` foi preservada em
`results/coordinator_evaluation/mac_2026-11-03_v2_llama/`. A versão local do
Ollama tratou os ramos como objetos completos e omitiu campos comuns obrigatórios;
as doze respostas LLM foram bloqueadas. O recurso foi removido por
incompatibilidade observada, mantendo as mesmas regras no prompt e no validador.

A replicação final está em
`results/coordinator_evaluation/mac-2026-11-03-final-v4-llama/evaluation-sl8k2oaz/`.
Ela reutiliza exatamente os dois contextos e medições vinculados por hash da
campanha original, com três repetições por caso e modo. Terminou `COMPLETE`:

| Caso | Modo | Válidas | Concordância | Aceitação efetiva | Mediana da decisão |
|---|---|---:|---:|---:|---:|
| Grande | Determinístico | 3/3 | 100% | 100% | 0,000015 s |
| Grande | Coordinator | 3/3 | 100% | 100% | 4,985 s |
| Grande | Sem análises | 3/3 | 100% | 100% | 5,139 s |
| Pequeno | Determinístico | 3/3 | 100% | 0% | 0,000007 s |
| Pequeno | Coordinator | 3/3 | 100% | 0% | 3,545 s |
| Pequeno | Sem análises | 3/3 | 100% | 0% | 3,560 s |

Portanto, a correção eliminou as seis respostas operacionalmente inválidas do
caso pequeno sem alterar admissões, medições ou resultados finais. Ela melhora
confiabilidade de interface, mas continua sem demonstrar ganho decisório sobre
a política determinística nessa amostra.

## Cobertura controlada das quatro decisões

O ensaio separado
`results/coordinator_scenarios/mac-2026-11-03-llama-v4/scenarios-yo32yuxo/`
usa quatro cenários sintéticos explícitos e dois modos, com três repetições. Ele
não é benchmark de kernel e não entra como evidência de desempenho. As 24/24
respostas foram estruturalmente válidas; 18/24 corresponderam ao oráculo:

| Decisão esperada | Correspondências |
|---|---:|
| ACCEPT | 6/6 |
| REJECT | 6/6 |
| RETUNE | 6/6 |
| MODIFY/SEND_TO_DEBUGGER | 0/6 |

O `llama3.1:8b` converteu todas as falhas de corretude explicitamente reparáveis
em REJECT. Como a decisão é conservadora e não promove código incorreto, a
segurança foi preservada, mas o fluxo de recuperação não foi demonstrado. Uma
comparação opcional com `qwen3:14b` foi interrompida após oito registros porque
a mediana parcial era 46,3 s e algumas inferências se aproximavam de três
minutos. O diretório parcial permanece marcado `RUNNING` e não é usado para
conclusões entre modelos.
