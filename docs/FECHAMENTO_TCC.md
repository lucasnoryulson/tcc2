# Fechamento do TCC — itens 1 a 6

Os três Word recebidos foram lidos e preservados. Eles contêm proposta, guia e
resumo executivo; a revisão das divergências está em
[LEITURA_DOS_DOCUMENTOS.md](monografia/LEITURA_DOS_DOCUMENTOS.md).

## Material de redação e defesa preparado

| Material | Arquivo editável | Fonte para revisão |
|---|---|---|
| Monografia revisada | [MONOGRAFIA_REVISAO_FINAL.docx](monografia/MONOGRAFIA_REVISAO_FINAL.docx) | [Texto Markdown](monografia/BASE_MONOGRAFIA.md) |
| Apresentação revisada, 16 slides com notas | [DEFESA_REVISAO_FINAL.pptx](defesa/DEFESA_REVISAO_FINAL.pptx) | [Slides e falas](defesa/SLIDES.md) |
| Demonstração | [Roteiro executável](defesa/DEMONSTRACAO.md) | Preparo real e recusa por integridade |
| Referências conferidas | [referencias.bib](monografia/referencias.bib) | Quatro fontes primárias usadas na nova base |

Os PDFs `monografia/BASE_MONOGRAFIA_PREVIA.pdf` e `defesa/DEFESA_PREVIA.pdf`
são prévias antigas e não devem ser entregues como versão atual. Os editáveis
revisados foram reabertos e verificados com suas bibliotecas de formato,
incluindo tabelas, imagens e notas. O DOCX também foi renderizado pelo Quick Look;
o PPTX requer conferência final no PowerPoint ou Keynote antes da entrega.

A base inclui resumo, abstract, introdução, questões de pesquisa, arquitetura,
metodologia, resultados disponíveis, discussão, limitações e conclusão
compatível com as evidências. Não contém resultados LLM inventados. R3 foi
respondida com resultado negativo/limitado, e os materiais são identificados
como versão revisada com adequação institucional ainda pendente.

## Onde estamos, pela numeração original

| Item | Situação após a revisão |
|---|---|
| **1. Pipeline até o resultado final** | Concluído no caminho suportado no Mac: inferência real, `ACCEPT`, promoção, revalidação e auditoria do manifesto |
| **2. Validação e configuração** | Concluído e verificado no Mac: 82 testes unittest e 14 regressões aprovados, sem skips |
| **3. Delimitação da automação** | Concluída e auditada em código, monografia, slides e `AUTOMATION_SCOPE.md`; preservar na entrega |
| **4. Avaliação dos agentes** | Campanha original `INCOMPLETE` preservada; contrato corrigido e replicação final `COMPLETE`, sem benefício adicional demonstrado; MODIFY não reproduzido no ensaio controlado |
| **5. Experimentos e reprodução** | Concluído no acervo disponível: 22 campanhas consolidadas, lacunas históricas declaradas e três campanhas Mac verificadas pelos gates atuais |
| **6. Monografia e defesa** | Conteúdo revisado e sincronizado com os resultados finais; DOCX e PPTX regenerados e validados. Restam adequação ao modelo institucional, dados de orientação/banca, exportação oficial para PDF e ensaio, que dependem de informações externas. |

## 1 e 2 — confirmação final do pipeline no ambiente alvo

Conferir a toolchain OpenMP e o modelo efetivamente instalado. No Mac, o ambiente
histórico tinha LLVM em `/opt/homebrew/opt/llvm/bin/clang`; usar esse caminho
somente se corresponder à instalação atual. O exemplo usa qwen2.5:3b; substituir
pelo modelo instalado e registrar o nome/ID real.

```bash
ollama list
python3 -B scripts/run_pipeline.py \
  --compiler /opt/homebrew/opt/llvm/bin/clang --threads 1 2 4 \
  --model qwen2.5:3b --timeout 600 \
  --work-dir build/final-pipeline --output-dir results/final-promoted
```

PROMOTED exige decisão e gates compatíveis. Não editar uma decisão para forçar
esse estado. Conservar a pasta do runner e o bundle final. Se ocorrer recusa,
ausência de ganho ou timeout, conservar o desfecho e sua causa.

Execução efetiva de 03/11/2026: `llama3.1:8b` (ID local `46e0c10c039e`),
LLVM 23.1.1, `PROMOTED` com 4 threads, speedup end-to-end 2,46546x e
escalabilidade contra OpenMP 1T 2,46466x. Evidências em
`build/final-pipeline-mac-2026-11-03/run-4whpshpr/` e bundle em
`results/final-promoted/mac-2026-11-03/5eef401105cc51be73471cfbf836964f858d9453a381224490828123f54eb1d5/`.
Isso fecha o item 1 no recorte Dot Product/redução; não substitui a campanha
pareada e a discussão científica do item 4.

## 3 — recorte que deve permanecer no texto

Manter explícitas a transformação determinística, a geração integrada de redução
escalar e a origem manual/específica das demais variantes. Remover as afirmações
de implementação em LangGraph, GPU, codificador LLM geral e loop de reparo
autônomo. Não trocar classificação de cinco padrões por geração automática de
cinco padrões. A mudança em relação à proposta está justificada na revisão.

## 4 — campanha e discussão do Coordinator

```bash
python3 -B scripts/evaluate_coordinator.py \
  --compiler /opt/homebrew/opt/llvm/bin/clang --threads 1 2 4 \
  --model qwen2.5:3b --repetitions 3 --timeout 600
```

Seguir o [protocolo](COORDINATOR_EVALUATION.md): mesmo candidato e medições,
ablação efetiva, identidade do modelo, janela de contexto e falhas preservadas.
Depois preencher a discussão com números reais de concordância, aceitação,
falhas, latência e tokens. O arquivo de resultados pode estar completo sem
demonstrar benefício. Uma campanha com falhas continua tendo resultados a
discutir; ausência total de respostas não permite responder à qualidade semântica.

A campanha original do Mac está em
`results/coordinator_evaluation/mac_2026-11-03/evaluation-4vgn5q8n/`; suas seis
respostas inválidas foram preservadas. Após corrigir o contrato, a replicação
com as mesmas evidências terminou `COMPLETE` em
`results/coordinator_evaluation/mac-2026-11-03-final-v4-llama/evaluation-sl8k2oaz/`,
com 12/12 respostas LLM válidas. O ensaio controlado acertou ACCEPT, REJECT e
RETUNE em 6/6, mas não MODIFY. Ver
[COORDINATOR_EVALUATION_MAC.md](COORDINATOR_EVALUATION_MAC.md).

Atualizar conjuntamente resumo, abstract, metodologia, §5.4 de resultados,
discussão, conclusão e slide do Coordinator. Não manter na versão final uma
promessa de superioridade sobre geração monolítica se esse contraste não foi
executado. O estudo atual avalia decisão, sem gerar novos candidatos pela LLM.

## 5 — seleção de evidências e atualização dos gráficos

Os metadados das campanhas que entram no texto foram separados entre vinculados,
arquivados e históricos: hardware, compilador,
flags, entrada, origem da variante, corretude, configurações e tempos. Nem todas
as 22 campanhas precisam ser repetidas; escolher o recorte que sustenta as
questões de pesquisa e declarar os limites das demais.

Para incluir campanhas novas, registrar suas fontes e ambiente no
[catálogo](experiment_catalog.json) antes de regenerar a matriz. O consolidator
não importa automaticamente toda nova medição para a seleção principal.
Entradas de `evaluation_case` podem apontar ao novo `results.json` e aos casos
`dot_large`/`dot_small`. Não renomear as campanhas Linux antigas para Mac.

```bash
python3 -B scripts/consolidate_experiments.py --no-plots
```

Para gráficos, usar o ambiente com `requirements-analysis.txt` e retirar
`--no-plots`. Atualizar números e figuras da monografia e dos slides quando a
campanha selecionada mudar. Seguir o [guia de reprodução](EXPERIMENT_REPRODUCTION.md).

Conservar as pastas completas: `build/` é ignorado pelo Git, e versionar somente
um resumo não conserva as cópias, executáveis e relatórios referenciados por ele.
Os caminhos absolutos impedem simplesmente transplantar a evidência para outra
máquina como se tivesse sido produzida lá.

## 6 — entrega acadêmica

Adotar o arquivo Word revisado como base de conteúdo, adaptar ao modelo
institucional e conferir nome do autor, orientador, curso, ano, sumário,
paginação, referências, legendas e chamadas das figuras. Não foram inferidas
normas ou exigências de uma banca específica. As referências da proposta
original que forem mantidas precisam ser conferidas; a base nova utiliza as
fontes verificadas em `referencias.bib`.

Revisar os slides com os resultados finais, ajustar à duração exigida e ensaiar
a demonstração preparada. Levar uma versão sem execução ao vivo e identificar
qualquer resposta simulada usada para mostrar integração. Fazer a exportação
final para PDF a partir dos aplicativos de edição, após conferir que tabelas,
figuras e notas estão corretas. A leitura final deve verificar se objetivos e
conclusões respondem ao mesmo experimento efetivamente executado.

## Regenerar os arquivos editáveis

Os Markdown são as fontes da versão preparada. Editar os arquivos Office
diretamente é possível; nesse caso, não executar o gerador sobre essas alterações
sem antes incorporá-las às fontes. O gerador sobrescreve somente suas saídas
de rascunho, sem modificar os três Word recebidos.

```bash
python3 -m venv build/writing-venv
build/writing-venv/bin/python -m pip install -r requirements-writing.txt
build/writing-venv/bin/python -B scripts/build_academic_material.py
```

O script gera `MONOGRAFIA_REVISAO_FINAL.docx`, `DEFESA_REVISAO_FINAL.pptx`,
diagrama e manifesto de revisão.
Não regenera as prévias PDF. Exportá-las novamente após mudar o conteúdo. O
manifesto identifica os documentos de origem e as fontes da revisão, sem
significar aprovação acadêmica ou conformidade automática com o modelo da banca.
