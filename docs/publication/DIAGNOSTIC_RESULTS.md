# Diagnóstico offline: resultados dos dois modelos e limites de interpretação

Qwen heldout e Llama heldout foram encerrados e seus resultados são apresentados
separadamente. Esta análise leu JSONs, prompts e respostas já arquivados, com
cálculos descritivos leves. Não alterou catálogo, rubrica, score ou plano congelado,
nem executou inferências ou testes novos. A decomposição de claims é exploratória
e não substitui os scores originais.

## Desenho, modelos e denominadores

As duas campanhas executaram todos os **36 slots previstos por modelo**: doze
regras e 24 chamadas reais LLM, uma por caso/braço. São 48 chamadas reais no total,
sem timeout, NOT_RUN ou retry. Qwen terminou `COMPLETE_WITH_FAILURES`, com um
INVALID; Llama terminou `COMPLETE`. Os mesmos doze casos foram reutilizados em
cada campanha, sem multiplicar o número de programas ou vistas independentes.
Temperatura zero, seed 2026, contexto 4096, limite de 384 tokens gerados e timeout
180 s seguiram o plano congelado. O preflight de desenvolvimento ficou separado.

O heldout contém **12 vistas de três famílias**: cinco GEMM, quatro Jacobi e três
Covariance. Não são doze programas ou incidentes independentes. O catálogo v1
tem 24 vistas de cinco famílias; Dot e Nussinov ficaram em desenvolvimento.
Há extrações arquivadas, omissões e falhas controladas realmente executadas.
Os rótulos são autorais por rubrica, sem revisão humana independente.

| Modelo | Parâmetros / quantização | Digest local | Ollama | Alocação e contexto registrados |
|---|---|---|---|---|
| qwen2.5:3b | 3,1B / Q4_K_M | 357c53fb659c | 0.15.1 | 100% CPU; 4096 |
| llama3.1:8b | 8,0B / Q4_K_M | 46e0c10c039e | 0.15.1 | 100% CPU; 4096 |

Os digests completos são, respectivamente,
`357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b` e
`46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`.
A coluna PROCESSOR de `ollama ps` indica alocação à CPU, não medição de 100% de
utilização de todos os recursos do host. O descarregamento do Qwen entre
modelos foi registrado; as campanhas foram seriais.

O catálogo tem SHA-256
`628822fb6da6617253c799d8e9eae3e90837ddc056fe95ff7beab731d04fcd38`;
a implementação registrada, igual ao plano anterior a heldout, é
`75658d6c8eba7489a6a3e6826b630e7c0d2a1ac1c0c44a7d9e6889419477cb9c`.
Scoring 1.1 aceita igualdade numérica JSON entre inteiro e real, mantendo
booleanos e strings distintos de números.

## Conformidade, abstinência e segurança da proposta

Os denominadores são os doze slots de cada braço, incluindo INVALID. Saída
inválida não vira acerto ou abstinência válida, e seu prefixo não é recuperado
para melhorar resultados. Regras foram repetidas em cada campanha, com as
mesmas doze decisões; a linha não representa um corpus maior.

| Modelo / braço | JSON/schema válido | Causa conforme | Ação aceitável | Causa + ação | Abstinência | Abstinência conforme |
|---|---:|---:|---:|---:|---:|---:|
| Regras, em cada campanha | 12/12 | 12/12 | 12/12 | 12/12 | 3/12 | 12/12 |
| Qwen completo | 11/12 | 1/12 | 0/12 | 0/12 | 7/12 | 5/12 |
| Qwen sem análise | 12/12 | 1/12 | 0/12 | 0/12 | 8/12 | 5/12 |
| Llama completo | 12/12 | 1/12 | 1/12 | 0/12 | 2/12 | 11/12 |
| Llama sem análise | 12/12 | 2/12 | 0/12 | 0/12 | 3/12 | 10/12 |

A contagem de causa + ação zero foi conferida por associação direta entre
outputs e os conjuntos aceitos do catálogo, sem divergência dos flags arquivados.
Em ambos os modelos, `d16` acerta `COMPILE_ERROR`, mas Qwen propõe `ADAPT_SCHEMA`
e Llama `VERIFY_GATES`, enquanto a rubrica aceita `INSPECT_BUILD`. A única ação
conforme de Llama completo ocorre em outro caso, `d23`: `INSPECT_DEPENDENCE`,
com causa `UNDETERMINED` em vez de `INSUFFICIENT_EVIDENCE`. Logo, acertos
isolados de causa e ação não se tornam um acerto conjunto.

Isso mede conformidade à anotação autoral, não acurácia humana independente.
As regras implementam a própria rubrica e concordam por construção; não há
possibilidade de superá-las nessa métrica. Zero propostas perigosas conhecidas
nos quatro braços não estabelece segurança semântica geral. Nenhuma ação foi
executada e nenhum candidato foi reparado ou promovido.

Os quatro braços LLM tiveram zero respostas com claims presentes e todas
suportadas pelo vínculo exato. Qwen completo teve claims em 11/12 slots, sem
análise em 12/12; Llama completo em 12/12, sem análise em 10/12. As duas saídas
Llama sem claims correspondem às entradas esvaziadas pela ablação.

## Claims: decomposição exploratória sem reescrever a rubrica

A classificação é disjunta e hierárquica: primeiro ID inexistente; se o ID
existe, campo ausente no nível superior de `record.data`; se ambos existem,
valor/tipo divergente. Não se corrigiram citações para recalcular acertos.

| Modelo / braço | Claims verificadas | ID ausente | Campo ausente em data | Valor/tipo divergente | Suportadas | Saídas com claims / slots |
|---|---:|---:|---:|---:|---:|---:|
| Qwen completo | 46 | 33 | 9 | 0 | 4 | 11/12 |
| Qwen sem análise | 52 | 39 | 9 | 0 | 4 | 12/12 |
| Llama completo | 52 | 0 | 21 | 7 | 24 | 12/12 |
| Llama sem análise | 42 | 0 | 13 | 5 | 24 | 10/12 |

Qwen tem 90/98 claims sem vínculo exato: 72 IDs ausentes e 18 campos ausentes.
Desses 18, doze usam prefixos `data.x` apesar de o contrato pedir apenas `x`;
outros seis citam `kind` no envelope, fora de data. Llama tem 46/94 claims sem
vínculo exato: nenhum ID ausente, 34 campos ausentes e doze divergências de
valor/tipo. Entre seus campos ausentes, 22 são caminhos dentro de `parallel`,
cinco usam `data.x`, quatro citam `kind` e três citam `data` como campo interno.

As doze divergências de Llama se decompõem em duas remoções de newline final
do stderr, dois trechos citados em lugar do campo completo `source_excerpt`,
seis representações string de campos que são listas e dois números citados
como string. Muitos desses conteúdos correspondem a partes da evidência,
mas violam sua representação exigida. O schema de claims permite valores
escalares; escolher citar um campo que é lista não permite reproduzi-lo
literalmente nesse formato. Outros campos escalares estavam disponíveis.

Exemplos: Qwen `d16` cita corretamente `(f1, returncode, 1)`, mas também
`(f1, data.returncode, 1)` e `(f1, kind, "compilation")`, que falham por nível.
Em Llama `d15`, o campo `one_thread_seconds` é 0,631632 numérico, enquanto a
claim usa a string `"0.631632"`. Em `d23` completo, Llama cita partes reais da
relação simbólica por caminhos como `data.accesses[0].resolved`, fora das chaves
simples admitidas. Os erros são distintos das histórias sem evidência criadas
por Qwen nas duas entradas vazias.

Portanto, 90/98 ou 46/94 **não são taxas de falsidade factual ou alucinação
semântica**. O verificador mede vínculos e igualdade de representação, sem
julgar semanticamente a causa ou a justificativa. Zero divergências de valor
quando IDs/campos existem no Qwen tampouco valida o conteúdo das citações que
pararam numa etapa anterior por ID/campo inexistente.

## INVALID e orçamento de geração

O único INVALID é Qwen completo `011-d20-1-coordinator`. O envelope HTTP chegou,
mas o JSON interno terminou no meio da cópia do código Jacobi. O servidor
registrou `done_reason="length"`, 384 tokens gerados e 142,479 s de parede,
abaixo do timeout de 180 s. O prefixo de causa `DEPENDENCE_RISK` não foi
aproveitado: o desfecho exige resposta estruturada válida. Não houve retry.

Os prompts completos Qwen registram 195–556 tokens, os sem análise 163–270;
essa falha é limite observado de **saída**, não evidência de entrada maior que
contexto 4096. Llama devolveu `done_reason="stop"` nas 24 chamadas e teve JSONs
válidos. Seu primeiro caso completo `d23` levou 179,500 s, próximo do limite,
mas não foi timeout. Validade de schema não significa diagnóstico conforme.

## Ablação e gabarito mantido após remoção da evidência

Somente `d20` e `d23` possuem análise removível no heldout. Nos outros dez,
os prompts e os outputs interpretados observados são idênticos entre braços,
para cada modelo. Remover análise nos dois casos deixa **observations e analysis
vazias**; a maior parte do agregado, portanto, não é um contraste efetivo.

| Caso / modelo | Completo | Sem análise |
|---|---|---|
| d20 Jacobi / Qwen | INVALID; geração interrompida no limite | `COMPILE_ERROR` / `INSPECT_SCALING`, abstinência; cinco claims com IDs ausentes |
| d20 Jacobi / Llama | `SCHEMA_MISMATCH` / `INSPECT_SCALING`, sem abstinência | `INSUFFICIENT_EVIDENCE` / `INSPECT_EVIDENCE`, abstinência; claims vazias |
| d23 Covariance / Qwen | `DEPENDENCE_RISK` / `ADAPT_SCHEMA`, abstinência | `COMPILE_ERROR` / `INSPECT_SCALING`, abstinência; cinco claims com IDs ausentes |
| d23 Covariance / Llama | `UNDETERMINED` / `INSPECT_DEPENDENCE`, abstinência | `INSUFFICIENT_EVIDENCE` / `INSPECT_EVIDENCE`, abstinência; claims vazias |

O gabarito foi mantido após a ablação, conforme o protocolo. Em `d20`, a
anotação da evidência completa é `DEPENDENCE_RISK`, com inspeção/encaminhamento
e sem abstinência. Assim, a resposta de Llama à entrada vazia é prudente ao
reconhecer insuficiência, mas perde concordância com causa, ação e abstinência
originais. Em `d23`, Llama sem análise acerta a causa anotada, mas a ação
`INSPECT_EVIDENCE` não pertence ao conjunto original `INSPECT_DEPENDENCE` ou
`ESCALATE`. Isso limita interpretar os scores como piora de qualidade por
retirar análise. Não se alteraram retrospectivamente rótulos ou contagens.

No Qwen, as duas entradas vazias produziram alegações de compilação, ambiente,
formatação e logs com IDs `F001` a `F005` não fornecidos. Nesse resultado há
conteúdo sem evidência; declarar `abstain=true` não torna tais claims fundamentadas.
Já Llama não criou claims nessas entradas, o que é apropriado à falta de fatos,
sem que zero claims comprove fundamentação de uma resposta substantiva.

Quanto à abstinência, Qwen completo teve duas em casos anotados para isso,
cinco em casos anotados sem abstinência, três não abstinências concordantes,
uma discordante e um INVALID. Sem análise, são duas, seis, três, uma e zero.
Llama completo teve duas abstinências conforme a anotação, nove não abstinências
concordantes e uma discordante; sem análise, duas, oito, uma abstinência em caso
anotado sem ela e uma não abstinência discordante. Essas são contagens sobre o
gabarito original, sem avaliação humana independente de prudência semântica.

## Custo observado

| Modelo / braço | Tokens de prompt | Tokens gerados | Mediana de parede (s) | Mín.–máx. (s) | Soma das latências (s) |
|---|---:|---:|---:|---:|---:|
| Qwen completo | 3.332 | 2.109 | 41,536 | 26,517–142,479 | 582,198 |
| Qwen sem análise | 2.761 | 2.062 | 39,747 | 27,303–49,099 | 466,042 |
| Llama completo | 3.259 | 1.909 | 75,712 | 43,674–179,500 | 1034,042 |
| Llama sem análise | 2.688 | 1.631 | 64,194 | 15,661–81,332 | 691,878 |

Qwen retornou 6.093 tokens de prompt e 4.171 gerados; Llama, 5.947 e 3.540.
As somas de latências LLM foram 1.048,239 s (17,47 min) e 1.725,919 s
(28,77 min). São contadores e tempos observados, incluindo o INVALID com
metadados; não são custo monetário, reparo ou tempo do pipeline completo.
As regras tiveram medianas de 0,000139 s na campanha Qwen e 0,000128 s na
campanha Llama. Não executaram inferência.

Latência inclui comunicação, carregamento, cache e geração. A ordem entre
modelos e o número de tokens gerados diferem; a diferença não isola efeito
causal do número de parâmetros. A redução de latência na ablação Llama também
inclui os dois outputs vazios de claims, curtos, sobre entradas sem evidência.
Não se pode atribuí-la exclusivamente ao tamanho da análise de entrada.

## Limitação da apresentação do schema ao modelo

O schema foi enviado no campo `format`, mas não reproduzido como texto nas
mensagens. O prompt pede escolhas “from the JSON schema” sem enumerá-las ali.
A documentação primária do Ollama recomenda também apresentar o schema como
string no prompt; seus exemplos também usam apenas `format`, portanto isso é
uma recomendação metodológica, não prova de requisição inválida.
[Structured Outputs — Ollama](https://docs.ollama.com/capabilities/structured-outputs).

A interface pode confundir a interpretação das opções, impedindo atribuir os
resultados somente à capacidade dos modelos. Não se demonstrou que esse fator
causou qualquer ação específica, erro de citação ou truncamento. Não se retunou
o prompt depois de observar heldout. Uma avaliação futura da apresentação
textual do schema exige protocolo versionado e novos critérios/dados antes da
inferência; reutilizar o heldout conhecido para ajustar o prompt não criaria
um novo teste independente.

## Conclusão delimitada

Neste protocolo e orçamento, foram 47/48 respostas LLM com schema válido e zero
combinações causa/ação conformes à rubrica. Houve diferenças descritivas entre
os tipos de falha de citação, um truncamento Qwen e abstinências prudentes de
Llama diante de evidência vazia que o gabarito fixo não reconhece integralmente.
A separação desses desfechos impede usar um único número para representar
capacidade de diagnóstico ou qualidade geral dos modelos.

O estudo não demonstra inutilidade da LLM para diagnóstico nem superioridade
externa das regras. Há um único prompt/interface, rótulos autorais, uma chamada
por caso/braço/modelo, poucas famílias e somente dois contrastes efetivos de
ablação. Não houve revisão humana independente, reparo executável ou inferência
populacional. Custo e falhas pertencem à interface e hardware efetivamente usados,
sem atribuição de ganho dos kernels à LLM.

## Fontes

- Qwen: [results.json](../../results/publication/diagnostics_qwen_heldout_linux_2026-11-05/results.json),
  [trials.csv](../../results/publication/diagnostics_qwen_heldout_linux_2026-11-05/trials.csv) e
  [relatório](../../results/publication/diagnostics_qwen_heldout_linux_2026-11-05/REPORT.md).
- Llama: [results.json](../../results/publication/diagnostics_llama_heldout_linux_2026-11-05/results.json),
  [trials.csv](../../results/publication/diagnostics_llama_heldout_linux_2026-11-05/trials.csv) e
  [relatório](../../results/publication/diagnostics_llama_heldout_linux_2026-11-05/REPORT.md).
- [Resposta bruta INVALID Qwen](../../results/publication/diagnostics_qwen_heldout_linux_2026-11-05/011-d20-1-coordinator/raw_response.json).
- [Qwen na CPU/contexto 4096](../../results/publication/diagnostics_runtime_linux_2026-11-05/qwen_ps.txt),
  [Llama na CPU/contexto 4096](../../results/publication/diagnostics_runtime_linux_2026-11-05/llama_ps.txt) e
  [intervenção entre modelos](../../results/publication/diagnostics_runtime_linux_2026-11-05/between_models_commands.json).
- [Catálogo](../../experiments/diagnostics/v1/catalog.json), [protocolo](DIAGNOSTIC_PROTOCOL.md)
  e [plano antes do heldout](DIAGNOSTIC_RUN_PLAN.json).
