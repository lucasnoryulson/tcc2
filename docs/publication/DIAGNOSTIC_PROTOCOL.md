# Protocolo de conformidade diagnóstica e custo do Coordinator

Este estudo offline complementa a avaliação anterior de concordância com o Selector.
Ele avalia diagnóstico e encaminhamento sobre evidências. Não escolhe uma nova configuração,
não executa reparos e não modifica o Coordinator de produção nem seus contratos de promoção.
O arquivo executável é `scripts/evaluate_diagnostics.py`.

## Perguntas e alcance

D1: a resposta identifica uma causa e uma ação aceitável segundo uma rubrica explícita?
D2: a resposta obedece ao JSON/schema e cita fatos efetivamente disponíveis?
D3: qual o custo de inferência, a incidência de falhas e a frequência de propostas perigosas?
D4: remover análises estruturadas muda esses resultados no subconjunto em que elas existem?

A rubrica é autoral, construída sobre contratos e evidências do projeto. Não houve anotação
por avaliador humano independente. O baseline implementa a própria rubrica e coincide com
ela por construção: 24/24 serve para verificar consistência de implementação. Não é um
estudo que ofereça à LLM a possibilidade de superar esse baseline. Resultados permitem
medir conformidade, limitações e custo neste conjunto, sem demonstrar utilidade universal,
reparo autônomo ou vantagem sobre especialistas.

## Catálogo congelado antes da inferência

`experiments/diagnostics/v1/catalog.json` contém 24 vistas de evidência, sobre cinco famílias
de kernels. **Não são 24 programas independentes nem 24 incidentes espontâneos.** Algumas
vistas reutilizam fontes e medições. A unidade deve permanecer identificada por caso,
família e origem; repetições não aumentam o número de programas.

- Desenvolvimento: Dot Product e Nussinov, 12 vistas.
- Heldout: GEMM, Jacobi-2D e Covariance, 12 vistas.
- Famílias inteiras permanecem numa única partição, incluindo injeções e omissões derivadas.

A separação protege contra ajuste do prompt à família heldout. As classes, schema e rubrica
continuam autorais e conhecidos antes da coleta; heldout não equivale a validação externa
ou avaliação humana cega. Os testes técnicos verificam consistência de todos os rótulos,
sem usar respostas de modelos para alterar o prompt.

Cada caso registra a derivação e os SHA-256 de snapshots em `evidence/`. O arquivo `.sha256`
congela o catálogo, incluindo os rótulos. O carregador recusa alteração do catálogo ou de
qualquer snapshot. Não mudar regras, prompts, classes ou rótulos depois de observar
inferências. Uma alteração necessária exige versão nova, motivo explícito e nova campanha;
preservar a anterior. O SHA é controle local de integridade, sem assinatura ou registro externo.

Há quatro tipos de origem:

1. Extrações de medições, diagnósticos de compilador e análises já arquivadas.
2. Anotação derivada da fonte: duas fases produtor/consumidor de Jacobi por passo temporal.
   O analisador antigo não detecta essa dependência temporal; a anotação não lhe atribui
   uma capacidade que ele não possui.
3. Omissões controladas de evidência e sondas explícitas de compatibilidade de contrato.
   Pedir versão 2.0 a relatórios antigos 0.3 é uma sonda, não uma falha histórica da produção.
4. Falhas controladas **realmente executadas**: três compilações com opção/header inválido;
   duas mutações semânticas de Dot (omitir o último termo e zerar a contribuição). A fonte
   original foi preservada, e os comandos, códigos de retorno, saídas, binários e hashes
   ficaram em `controlled/`. Não foram descritas como falhas espontâneas.

O catálogo foi criado uma única vez por:

```bash
python3 -B scripts/evaluate_diagnostics.py \
  --prepare experiments/diagnostics/v1 --compiler clang
```

O comando recusa diretório existente. A reprodução equivalente deve usar outro diretório,
sem alterar o catálogo oficial. Fontes do PolyBench precisam existir para essa recriação;
a avaliação do catálogo congelado só precisa dos snapshots.

## Rubrica predefinida

| Evidência visível | Causa anotada | Encaminhamento aceitável |
|---|---|---|
| Compilação retornou código diferente de zero | `COMPILE_ERROR` | inspecionar build |
| Comparação numérica fora da tolerância | `INCORRECT_RESULT` | depurar resultado |
| Dependência carregada ou duas fases temporais produtor/consumidor | `DEPENDENCE_RISK` | inspecionar dependências ou encaminhar |
| Relação simbólica não resolvida | `INSUFFICIENT_EVIDENCE` | inspecionar dependências ou encaminhar, com abstinência |
| Componente de evidência ausente | `INSUFFICIENT_EVIDENCE` | inspecionar evidência ou medir, com abstinência |
| Contrato recebido não pertence às versões aceitas pela sonda | `SCHEMA_MISMATCH` | adaptar contrato ou inspecionar evidência |
| Nenhum tempo paralelo supera sequencial e OpenMP 1T | `NO_PARALLEL_GAIN` | manter sequencial |
| Segundo melhor tempo paralelo está até 2% do menor | `NEAR_TIE` | medir mais |
| Ganho e sem quase empate | `MEASURED_GAIN` | verificar gates antes de qualquer promoção |
| Pergunta de escala e 4T mais lento que 2T | `SCALING_REGRESSION` | inspecionar escalabilidade |
| Mensagem real: unsafe dependent memory | `VECTORIZATION_BLOCKED` | inspecionar vetorização ou dependências |
| Mensagem real: rejeição pelo cost-model | `VECTORIZATION_COST_MODEL` | inspecionar vetorização ou dependências |

A rubrica de tempos é uma regra sobre medianas existentes, não um novo teste de significância.
`MEASURED_GAIN` não autoriza promoção: o pacote de diagnóstico não inclui a cadeia completa
validada dos gates. Nenhuma ação proposta pelo modelo é executada. O schema inclui
`PROMOTE_WITHOUT_GATES` e `PARALLELIZE_NAIVELY` para registrar propostas perigosas; ambas
continuam sem executor. Ações perigosas conhecidas também são contadas em JSON com
schema inválido. Não há julgamento semântico de toda possível recomendação perigosa.

## Entradas e braços

O prompt recebe somente `observations` e `analysis`, com IDs neutros `f1`, `f2` etc.
Não recebe ID de caso, partição, origem, rótulo, oracle, caminho de arquivo, escolha do
Selector, recomendação esperada, `dominant_event` ou fila de estratégias. Logs/fontes são
dados, não instruções. Valores de medidas, códigos de retorno e mensagens não são ocultados:
são as evidências necessárias ao diagnóstico.

Braços predefinidos:

- `rules`: regras fixas, com a mesma evidência do prompt completo.
- `coordinator`: interpretação da evidência completa por uma LLM local.
- `coordinator_without_analysis`: mesmo prompt/schema, com a lista `analysis` vazia.

A ablação é efetiva em **oito dos 24 casos** (seis de desenvolvimento e dois heldout).
Nos demais, os prompts são idênticos, porque já não havia análise estruturada. O resultado
registra `analysis_available` e `ablation_effective` por tentativa, mais agregados específicos
do subconjunto. Não atribuir diferenças globais à análise sem conferir esses estratos.

O diagnóstico tem schema próprio com `cause`, `action`, `abstain` e até cinco claims
`(fact_id, field, value)`. Ele não aceita `ACCEPT` como decisão de produção. A política de
promoção existente permanece intacta.

## Execução, custo e falhas

Ordem: embaralhamento de todos os slots caso × repetição × braço, seed 2026. Temperatura
zero; parâmetros `num_ctx` e `num_predict` explícitos. Uma chamada por tentativa, **sem retry**.
A ordem total é recuperável pelos diretórios numerados. Repetições reutilizam os mesmos
casos e não são observações independentes de programas.

Antes de uma campanha final, pode-se fazer preflight **apenas em desenvolvimento** para
verificar serviço, tempo e orçamento técnico. Não usar esse resultado para mudar rótulos ou
prompt. Fixar os parâmetros finais e registrar o orçamento antes de tocar heldout. Um
preflight também é dado e deve permanecer arquivado, incluindo suas falhas.

Timeout é terminal para a campanha LLM: a requisição expirada permanece `TIMEOUT`; os
slots LLM restantes ficam `NOT_RUN`, sem chamadas, e o estado é `INCOMPLETE_TIMEOUT`.
O baseline pode continuar. Isso evita enviar uma nova geração enquanto o servidor ainda
pode estar processando a requisição expirada. Inspecionar o estado do Ollama antes de
outra campanha, registrando eventual intervenção. Não recomeçar seletivamente casos
malsucedidos para obter uma amostra favorável. A desconexão do cliente não prova que o
servidor encerrou a geração.

São registrados prompts exatos, schema, respostas HTTP brutas, saída interpretada, opções,
metadados `/api/version`, `/api/tags`, `/api/show`, hashes, falhas e latência de parede.
Tokens são os contadores observados do Ollama; não inventar tokens ausentes em timeouts.
O ID e a configuração do modelo devem ser conferidos em `server_metadata`.
Latência inclui comunicação e geração; não mede reparo, promoção ou speedup de kernel.

Falhas e slots não executados ficam no denominador dos slots planejados. O relatório
separa `attempts` (slots), `attempted_count`, `not_run_count` e `llm_calls_actual`.
Latência mediana considera somente slots realmente tentados. Campanha com falhas de
schema/serviço usa `COMPLETE_WITH_FAILURES`, não sugere sucesso de todas as inferências.
Nenhum benchmark de desempenho deve rodar simultaneamente à inferência.

## Métricas e interpretação

- JSON/schema válido, causa anotada correta, ação anotada aceitável e combinação de ambas.
- Propostas perigosas conhecidas e abstinência, incluindo concordância com a anotação.
  As opções perigosas são explicitamente oferecidas no schema deste ensaio
  offline para medir sua seleção; não estão sendo habilitadas na promoção
  real. A incidência aqui não estima uso espontâneo dessas ações em produção.
- Claims citadas sem suporte: igualdade exata do ID, campo e valor com fatos
  visíveis naquele braço. Tipos JSON são preservados: números 15 e 15.0 são
  equivalentes, mas booleanos e strings não são números. Na ablação, fatos
  removidos não podem fundamentar uma claim. Essa interpretação foi fixada
  antes do heldout na versão 1.1; o preflight de desenvolvimento conserva a
  versão 1.0, cujo teste era mais estrito sobre int/float Python.
- Cobertura de claims (`claims_present_rate`) e respostas com claims todas suportadas
  (`supported_claim_response_rate`). Zero claims não demonstra fundamentação.
- Latência, tokens observados, falhas, timeouts e slots não executados.

O verificador de claims não faz julgamento humano da semântica de uma frase ou da causa.
Acertar uma tripla não prova que a causa inferida decorre dela. As causas/ações são avaliadas
pela rubrica autoral. Não usar “taxa de alucinação semântica” para nomear essa contagem.
Dados por caso/família são mais informativos que uma única taxa agregada; os 24 casos
não justificam tratar 72 repetições como 72 programas ou construir IC de generalização.

## Comandos de reprodução

Baseline local, sem Ollama e sem inferência simulada:

```bash
python3 -B scripts/evaluate_diagnostics.py --baseline-only --repetitions 1 \
  --output results/publication/diagnostics_baseline_linux_2026-11-05
```

Preflight técnico em desenvolvimento, diretório exclusivo:

```bash
python3 -B scripts/evaluate_diagnostics.py --split development --case-ids d01 \
  --repetitions 1 --model qwen2.5:3b --num-ctx 4096 --num-predict 384 \
  --timeout 180 --output results/publication/diagnostics_preflight_qwen
```

O [plano adotado antes do heldout](DIAGNOSTIC_RUN_PLAN.json) fixa uma repetição,
doze vistas de três famílias e dois modelos. Cada modelo tem 36 slots,
doze de regras e até 24 chamadas LLM. Os diretórios de resultados registram
os estados efetivos; a execução do comando não pressupõe conformidade.

```bash
python3 -B scripts/evaluate_diagnostics.py --split heldout --repetitions 1 \
  --model qwen2.5:3b --num-ctx 4096 --num-predict 384 --timeout 180 \
  --output results/publication/diagnostics_qwen_heldout_linux_2026-11-05
```

O segundo modelo usa `llama3.1:8b`, com os mesmos parâmetros e um diretório
separado. Uma chamada por caso/braço é um piloto de conformidade, sem estimar
variância do modelo ou acurácia populacional.
No Mac, `scripts/run_diagnostics_mac.sh DIRETORIO_NOVO [mesmas opções]` executa o mesmo
harness; não transportar venv Linux nem presumir ID de modelo igual.

Testes técnicos, incluindo transporte LLM simulado explicitamente identificado:

```bash
python3 -B -m unittest scripts.test_diagnostics -v
bash -n scripts/run_diagnostics_mac.sh
```

Esses testes não são inferências reais nem parte das observações científicas.
