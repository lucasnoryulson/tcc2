# Item 4 — avaliação do Coordinator

Pergunta avaliada: **com as mesmas evidências e o mesmo candidato, o Coordinator
altera a decisão de admitir uma variante paralela e a que custo?** O experimento
mede o valor adicional da decisão da LLM sobre o pipeline determinístico atual.
Não mede geração de código pela LLM nem recuperação autônoma de candidatos.

## Executar no hardware alvo

Com Clang disponível para análise, compilador OpenMP e Ollama com o modelo instalado:

```bash
python3 -B scripts/evaluate_coordinator.py \
  --compiler clang --threads 1 2 4 \
  --model qwen2.5:3b --repetitions 3 --timeout 600
```

No Linux com GCC/OpenMP, usar `--compiler gcc`. No Mac, usar o mesmo compilador
OpenMP funcional empregado nos gates do projeto. O nome `clang` precisa resolver
para essa toolchain; o Apple Clang sem suporte OpenMP não basta. O script não
instala dependências nem baixa modelos. Registrar a versão do Ollama e conservar
o ID do modelo mostrado por `ollama list`, além dos relatórios gerados.
Registrar também a janela de contexto efetiva do servidor e conferir que ela
comporta os prompts salvos. Se houver truncamento, corrigir a configuração e
repetir a campanha antes de interpretar a ablação; o cliente atual não fixa essa janela.

Para verificar o pipeline sem inferência:

```bash
python3 -B scripts/evaluate_coordinator.py --compiler gcc --baseline-only
```

Para comparar decisões sobre contextos já gerados, sem repetir o benchmark:

```bash
python3 -B scripts/evaluate_coordinator.py \
  --contexts build/pipeline/run-EXEMPLO/context.json \
  --model qwen2.5:3b --repetitions 3 --timeout 600
```

Os caminhos devem existir nesta máquina, com todos os artefatos referenciados
intactos. Nesse modo o custo do prefixo é desconhecido (`null`); não se inventa
tempo de preparação. Usar ambos os tamanhos de entrada na campanha final.

## Desenho experimental

| Modo | Evidência fornecida | Regra efetiva de admissão |
|---|---|---|
| `deterministic` | Gates e seleção verificados; nenhuma chamada à LLM | Mesma função usada pelo executor de promoção |
| `coordinator` | Contexto completo da implementação atual | Decisão validada e sujeita à mesma regra de admissão |
| `coordinator_without_analysis` | Código, corretude, desempenho e restrições; análises estruturadas removidas do prompt | Mesmos gates, contexto canônico e regra de admissão |

A ablação remove `static_analysis`, `dependence_analysis`, `pattern`, `strategy`
e `deterministic_evidence` de uma cópia para inferência. O script verifica se o
prompt efetivamente mudou. Campos que o compactador já omite não são anunciados
como informação retirada do prompt. Essa ablação também reduz seu tamanho;
qualquer diferença de latência tem esse fator de confusão.

Por padrão são preparados dois casos reais de Dot Product: N=10.000.000, com 100
chamadas por medição, e N=1.024, com 10.000 chamadas por medição. O segundo expõe
o custo de criação das equipes OpenMP. Não se força um resultado positivo ou
negativo: a decisão vem das medições da máquina. Cada configuração tem cinco
medições externas; cada uma contém as chamadas internas do driver. São usados
os flags e as variáveis OpenMP registrados no relatório de desempenho.

Cada caso passa uma vez por análise, transformação, compilação, validação,
benchmark, seleção e Context Builder. Os três modos reutilizam **esses mesmos
bytes e essas mesmas medições**, com hashes e campanha conferidos antes/depois.
A ordem dos modos é embaralhada por caso/repetição com semente registrada. Não
há retentativas silenciosas de inferência. A temperatura é zero; repetir chamadas
mede também estabilidade/latência, sem garantir respostas diferentes.

A admissão exige seleção paralela, configuração medida com pelo menos duas
threads e tempo menor que **ambos** os baselines, sequencial e OpenMP com uma
thread. A LLM não pode liberar uma configuração fora desse contrato. A decisão
bruta e a decisão enriquecida são guardadas separadamente: preencher a
configuração deterministicamente não conta como acerto de cópia da LLM.

## Resultados registrados

Cada diretório `results/coordinator_evaluation/evaluation-*` contém:

- `results.json`: configuração, identidades das evidências e da implementação,
  medições, decisões brutas/enriquecidas, erros, metadados do modelo e agregações.
- `trials.csv` e `report.md`: comparação por caso e modo, pronta para inspeção.
- `CASO-REPETICAO-MODO/prompt.json` e `trial.json`: entrada exata enviada e resultado
  de cada chamada; o modo determinístico não tem prompt.
- Diretórios dos pipelines preparados, com fontes, binários, logs, tempos brutos,
  toolchain, flags e relatórios vinculados. Conservar a pasta completa.

Concordância significa **concordância binária com a política de admissão**, não
uma verdade independente sobre a melhor ação `RETUNE/MODIFY/REJECT`. A taxa usa
todas as tentativas no denominador; erros/timeouts não viram respostas corretas.
São registrados propostas de aceitação inadmissíveis, oportunidades elegíveis
não aceitas, aceitação efetiva, respostas válidas, falhas e intervalos de latência.

O resultado final é a configuração paralela admissível quando aceita; nos demais
casos, o sequencial é o fallback explícito da avaliação. Seu speedup é 1×. O tempo
do kernel vem das medições compartilhadas, não de uma nova execução por decisão.
Se dois modos aceitam a mesma configuração, têm o mesmo speedup neste desenho.

O tempo contabilizado do pipeline soma o prefixo real compartilhado ao tempo
de decisão e validação da tentativa. O relatório guarda também o tempo real de
parede da campanha. Não inclui publicação/revalidação final: este é um estudo
da decisão, sem produzir artefatos promovidos. Latência da chamada inclui espera
e carregamento; os metadados do Ollama preservam durações em nanossegundos e
tokens quando disponíveis. Custo monetário fica desconhecido, sem preço inventado.

Há **um candidato por caso** e uma chamada por tentativa LLM. `RETUNE` e `MODIFY`
são ações observadas, sem gerar novas variantes neste experimento. O número de
tentativas até candidato paralelo admissível é 1 quando aceito, ou desconhecido
quando não aceito; não se afirma que o agente reduziu tentativas de busca.

## Critério de conclusão e limites

`BASELINE_ONLY` comprova execução determinística, deixando a avaliação LLM
pendente. `INCOMPLETE` conserva falhas, timeouts e ablações sem efeito. `FAILED`
indica falha de preparação ou integridade; resultados desse diretório não devem
ser usados como campanha válida. `COMPLETE` significa que as chamadas previstas
produziram decisões válidas com ablação efetiva, não que houve benefício da LLM.

Para fechar o item 4, executar os três modos no hardware alvo, inspecionar as
decisões e escrever a discussão com os números obtidos. Uma conclusão legítima
é que a LLM reproduziu a seleção determinística e adicionou latência, ou vetou
uma oportunidade medida. Não atribuir ganho do transformador à LLM.

Os dois casos são um kernel em dois tamanhos, sem generalização para todos os
padrões. Repetições da decisão não são amostras independentes de desempenho.
O benchmark atual mede sequencial e depois configurações OpenMP em ordem fixa,
sem controle de temperatura/frequência ou aquecimento dedicado; tratar esta
campanha como avaliação delimitada e registrar carga/energia/ambiente da máquina.
Não executar testes ou outros benchmarks concorrentes durante a coleta final.
Uma inferência expirada pode continuar no servidor; antes de repetir a campanha,
aguardar o servidor terminar ou reiniciá-lo e registrar isso. Falhas de corretude
são cobertas por testes dos gates, não enviadas como candidatos deste estudo.

Teste da infraestrutura: `python3 -B scripts/test_coordinator_evaluation.py`.
Respostas simuladas nesses testes não constituem resultados científicos da LLM.

A execução local e seus limites estão em
[COORDINATOR_EVALUATION_LOCAL.md](COORDINATOR_EVALUATION_LOCAL.md).
