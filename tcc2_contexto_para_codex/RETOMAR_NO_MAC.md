# Retomar no Mac

Atualizado em **03/11/2026**. Este pacote registra o estado e a conversa em forma
de síntese. Não é uma exportação literal de todas as mensagens.

## Transferência

Copie o checkout atualizado de `tcc2/`, inclusive os arquivos de contexto ainda
não commitados. O estado inspecionado nesta atualização era a branch
`feat/gate-contracts`, commit `c42b16d` (`saving`), com a árvore limpa antes desta
edição de documentação. Isso não confirma que o commit esteja no remoto. Não
executamos push nem merge nesta tarefa.

O ZIP `tcc2_contexto_codex_mac_2026-11-03.zip`, criado ao lado de `tcc2/`, contém
contexto e documentos de apoio com os caminhos do repositório. **Não contém a
implementação inteira:** use-o junto ao checkout atualizado. O ZIP antigo
`tcc2_contexto_para_codex.zip` foi preservado e está desatualizado.

Se precisar auditar a execução Linux, copie também `build/validation/` e
`build/defense-demo/`, ignorados pelo Git. Eles não estão no ZIP de contexto.
Os relatórios usam caminhos absolutos Linux: conservar a pasta serve para
auditoria; não os reescreva para simular uma execução no Mac. Gere evidência nova.

Os três Word recebidos estão na pasta **pai** de `tcc2/`. Copie-os separadamente
se quiser consultar os originais no Mac. Os rascunhos revisados estão em
`docs/monografia/` e `docs/defesa/` e estão incluídos no pacote de contexto.

## Mensagem para colar no Codex

> Continue o TCC2 a partir do estado atual, sem refazer as etapas implementadas.
> Leia AGENTS.md, tcc2_contexto_para_codex/docs/TCC2_CONTEXT.md,
> tcc2_contexto_para_codex/docs/CONVERSA_E_DECISOES.md e
> docs/FECHAMENTO_TCC.md. Estou no Mac. Confira o Git e a toolchain OpenMP,
> execute a validação real do pipeline e a avaliação do Coordinator, conserve
> todos os resultados e falhas e depois atualize a consolidação, a monografia
> e os slides com os números obtidos. Use a numeração original dos itens 1 a 6.
> Não force ACCEPT/PASS, não trate respostas simuladas como ciência e não
> faça push/merge. Informe o que realmente foi executado e o que ainda falta.

## Sequência de retomada

Execute os comandos a partir da raiz `tcc2/`. Antes de medir, inspecione Git,
Python, `clang`, a instalação OpenMP, Ollama e modelo disponível:

```bash
git status --short
git branch --show-current
git log -1 --oneline
python3 --version
command -v clang
clang --version
ollama --version
ollama list
```

O caminho histórico `/opt/homebrew/opt/llvm/bin/clang` é uma referência, não uma
garantia da instalação atual. `--compiler` controla os gates, mas a análise
estática chama `clang` pelo PATH. Verifique ambos. Não suponha que `gcc` do macOS
seja GNU GCC/OpenMP: vários testes locais usam literalmente `gcc` e podem exigir
adaptação da toolchain de teste; não conte skips como testes aprovados.

Primeiro faça a preparação real sem inferência:

```bash
python3 -B scripts/run_pipeline.py --prepare-only \
  --compiler /opt/homebrew/opt/llvm/bin/clang --threads 1 2 4 \
  --work-dir build/mac-preflight
```

Depois confirme o item **1** com o modelo real, substituindo o caminho/modelo
se necessário. Não colete benchmarks simultaneamente com testes ou outra campanha:

```bash
python3 -B scripts/run_pipeline.py \
  --compiler /opt/homebrew/opt/llvm/bin/clang --threads 1 2 4 \
  --model qwen2.5:3b --timeout 600 \
  --work-dir build/final-pipeline --output-dir results/final-promoted
```

Conserve `summary.json`, logs, evidências e eventual bundle promovido.
`PREPARED` não chamou a LLM. `PROMOTED` depende de uma decisão admissível e dos
gates. Recusa, ausência de ganho e timeout devem continuar visíveis.

Para o item **4**, execute a comparação dos três modos:

```bash
python3 -B scripts/evaluate_coordinator.py \
  --compiler /opt/homebrew/opt/llvm/bin/clang --threads 1 2 4 \
  --model qwen2.5:3b --repetitions 3 --timeout 600
```

Registre o ID do modelo, janela de contexto efetiva, versão do Ollama e condições
da máquina. Confira os prompts e decisões. Um timeout pode deixar uma geração
ativa no servidor: espere terminar ou reinicie-o antes de nova campanha,
registrando a intervenção. O cliente atual não fixa a janela de contexto.

Para os itens **5 e 6**, selecione as campanhas necessárias, acrescente as novas
fontes ao catálogo e atualize tabelas, gráficos, texto e slides. O comando abaixo
não importa automaticamente toda campanha nova:

```bash
python3 -B scripts/consolidate_experiments.py --no-plots
```

Use `requirements-analysis.txt` para gráficos e `requirements-writing.txt`
para o gerador de Word/PowerPoint. Não transporte um venv Linux para macOS;
crie um ambiente local. Não rode o gerador sobre edições feitas apenas no Word
ou PowerPoint sem antes incorporá-las às fontes Markdown. Ele não regenera PDFs.

O roteiro completo e os critérios de conclusão estão em
[FECHAMENTO_TCC.md](../docs/FECHAMENTO_TCC.md), no
[protocolo do Coordinator](../docs/COORDINATOR_EVALUATION.md) e no
[guia de reprodução](../docs/EXPERIMENT_REPRODUCTION.md).
