# Orientações para Codex — TCC2

Este repositório contém o TCC2 de Ciência da Computação (PUCRS): sistema híbrido de análise estática, agentes e seleção de estratégias de paralelização automática em OpenMP.

## Contexto obrigatório

Antes de propor alterações, leia `tcc2_contexto_para_codex/docs/TCC2_CONTEXT.md`
(caminho relativo à raiz do repositório), depois `docs/CONVERSA_E_DECISOES.md`
relativo a esta pasta e `RETOMAR_NO_MAC.md`. O contexto foi atualizado após as
implementações de 03/11/2026. `CONTEXTO_INICIAL_CHATGPT.md` é histórico e contém
pendências já resolvidas. Confirme o estado atual no código e no Git.

## Regras de trabalho

- Inspecione os arquivos e os contratos reais antes de editar. Se houver divergência entre a documentação e o repositório, priorize o código e relate a divergência.
- Trabalhe em uma branch de feature. Não altere diretamente `main`; não faça push/merge sem aprovação explícita.
- Preserve a separação entre evidências determinísticas (AST, dependências, corretude, benchmark e seleção) e decisões de LLM. A LLM nunca autoriza, por si só, a promoção de um artefato.
- Não aceite `correctness_gate: PASS` declarado manualmente como prova suficiente de corretude. Exija evidência vinculada ao candidato, incluindo integridade por SHA-256 e revalidação ou atestado verificável.
- Nunca confunda speedup end-to-end com escalabilidade paralela real. Preserve as métricas e os baselines usados.
- Acrescente testes que cubram rejeições, configurações inconsistentes, troca de artefato, falha de gate e promoção válida. Execute os testes relevantes e reporte exatamente o que foi executado.
- Evite expansão arquitetural (CUDA, novos agentes ou padrões) sem necessidade para fechar o TCC.
- Mantenha a numeração consolidada dos seis itens: pipeline, validação,
  recorte, avaliação dos agentes, experimentos/reprodução, monografia/defesa.
- Não trate LLM simulada como inferência real, nem testes aprovados como
  conclusão científica. Os materiais de redação e defesa ainda são rascunhos.
