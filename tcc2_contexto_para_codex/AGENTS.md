# Orientações para Codex — TCC2

Este repositório contém o TCC2 de Ciência da Computação (PUCRS): sistema híbrido de análise estática, agentes e seleção de estratégias de paralelização automática em OpenMP.

## Contexto obrigatório

Antes de propor alterações, leia `docs/TCC2_CONTEXT.md`. Este arquivo registra o contexto transferido de uma conversa anterior com ChatGPT, as decisões já tomadas, a arquitetura conhecida, os resultados, as pendências e os critérios de aceite. Considere-o um ponto de partida, não um substituto para inspecionar a versão atual do código.

## Regras de trabalho

- Inspecione os arquivos e os contratos reais antes de editar. Se houver divergência entre a documentação e o repositório, priorize o código e relate a divergência.
- Trabalhe em uma branch de feature. Não altere diretamente `main`; não faça push/merge sem aprovação explícita.
- Preserve a separação entre evidências determinísticas (AST, dependências, corretude, benchmark e seleção) e decisões de LLM. A LLM nunca autoriza, por si só, a promoção de um artefato.
- Não aceite `correctness_gate: PASS` declarado manualmente como prova suficiente de corretude. Exija evidência vinculada ao candidato, incluindo integridade por SHA-256 e revalidação ou atestado verificável.
- Nunca confunda speedup end-to-end com escalabilidade paralela real. Preserve as métricas e os baselines usados.
- Acrescente testes que cubram rejeições, configurações inconsistentes, troca de artefato, falha de gate e promoção válida. Execute os testes relevantes e reporte exatamente o que foi executado.
- Evite expansão arquitetural (CUDA, novos agentes ou padrões) sem necessidade para fechar o TCC.
