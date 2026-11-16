# Integração do patch final — 16/11/2026

## Origem e destino

- Pacote: `tcc2-final-2026-11-16.zip`, contendo somente
  `tcc2-final-2026-11-16.patch`, com conteúdo idêntico ao patch avulso.
- SHA-256 do patch: `484cb43293bf5631a398a3049785b619dfb0add9efd30a90894b22c72aacfb75`.
- Commit de origem informado pelo patch: `1df4e10d463a62a8d9b566a9d59b3da7bfc72eac`.
- Base da integração: `a1e4a6e`, que já contém as campanhas Mac e seus documentos.
- Branch: `feat/final-patch-integration-2026-11-16`.
- Worktree: pasta irmã `tcc2-experiments-mac-2026-11-16`.
  O checkout `tcc2`, em `feat/mac-pipeline-validation`/`4bace11`, foi preservado.
- Não houve merge, push ou alteração da referência `main`.

O patch aplica sobre a base experimental, exceto pelo arquivo de holdout que
já existia com outro contrato. Não foi necessário extrair arquivos em pastas
genéricas: fontes foram para `analysis/`, ferramentas e testes para `scripts/`,
documentos para `docs/` e evidências recebidas para `results/`.

## Resolução das diferenças

1. O `evaluate_selector_holdout.py` existente continua com a interface de
   congelamento prévio, verificação de cronologia, sensibilidade e estabilidade.
   A versão retrospectiva recebida foi incorporada como
   `scripts/evaluate_selector_sessions.py`, com testes e roteiro ajustados.
   As duas formas de avaliação não são apresentadas como equivalentes.
2. Foram mantidas a telemetria real por subprocesso e a coleta anterior de custos.
   O analisador novo valida os vínculos completos de seleção/corretude/desempenho,
   além dos tempos e da configuração; não aceita troca de campanha ou elapsed inválido.
3. O benchmark integrado aceita repetições, aquecimentos e seed. Sua agenda
   embaralhada, amostras e metadados são verificados; metadados incompletos,
   booleanos indevidos, duplicações e reordenações são recusados. Relatórios
   legados sem os três novos campos continuam legíveis, sem inventar aquecimentos.
4. AXPY passa a exigir três buffers com `restrict` e verifica cada elemento
   contra o oráculo, também na entrada temporizada. Os testes recusam índices
   não injetivos, aliasing não certificado, leitura da saída e erros que se
   cancelariam em um checksum.
5. A promoção AXPY de 03/11 recebida foi preservada byte a byte, inclusive
   caminhos absolutos e hashes. Ela pertence ao contrato anterior, não valida
   retrospectivamente o novo fixture. É idêntica à cópia no checkout original.
6. `MONOGRAFIA_CONSOLIDADA.md` recebeu os resultados Mac já existentes, corrigindo
   as alegações desatualizadas de coleta pendente. O holdout Linux é denominado
   retrospectivo. Word, PDF e capa foram exportados em arquivos próprios;
   revisões anteriores, figuras e campanhas não foram sobrescritas.

## Verificações executadas

- Suíte inicial após aplicar o patch: 136 testes aprovados.
- Suíte final ampliada: **143 testes**, sem falhas ou skips.
- Seis scripts de regressão: **23 casos**, todos aprovados.
- Isolamento estático das variantes e sintaxe do roteiro Linux: PASS.
- Execução técnica AXPY real: análise, transformação, compilação, corretude,
  desempenho, seleção e contexto; threads 1/2/4/6/8/10, 15 medições e 3
  aquecimentos por configuração, seed 2026. Total: 105 medições e 21 aquecimentos.
  Estado `PREPARED`, sem LLM nem nova promoção.
- Teste integrado de promoção com 15 medições/3 aquecimentos e decisão simulada:
  candidato revalidado e configuração preservada. Não é inferência real.
- Holdout Linux recalculado a partir das duas campanhas originais: CSV e todas
  as métricas reproduziram os arquivos recebidos, 16 casos.
- Holdout Mac com decisões previamente congeladas: resultado integral preservado,
  16 casos, estabilidade 14/16, uma recomendação inadequada.
- Hashes dos documentos e resultados anteriores: preservados.
- Novos Word e capa: ZIPs reabertos; PDF: texto e páginas conferidos, sem páginas
  vazias. Exportação consolidada com 78 páginas, 27 tabelas e 21 imagens no Word.

O [relatório estruturado](../../results/validation/final_patch_2026-11-16/report.json)
contém hashes, comandos, logs, protocolo e verificações. Os resultados do smoke
AXPY ficam em `build/final-patch-integration/axpy/run-6zbgh0n9`, ignorado pelo Git;
o resumo de custo é arquivado com a validação. Não se somam esses tempos às
campanhas científicas anteriores.

## Reprodução

Na raiz desta worktree, use Python com `requirements-experimental.txt` instalado
e LLVM/OpenMP no PATH. As saídas de validação devem ter nomes novos:

```bash
export PATH="/opt/homebrew/opt/llvm/bin:$PATH"
build/experimental-venv/bin/python -B scripts/run_pipeline.py \
  --source analysis/fixtures/axpy.c \
  --driver analysis/fixtures/axpy_driver.c \
  --benchmark-driver analysis/fixtures/axpy_benchmark_driver.c \
  --compiler /opt/homebrew/opt/llvm/bin/clang \
  --threads 1 2 4 6 8 10 --repetitions 15 --warmups 3 --seed 2026 \
  --work-dir build/final-patch-repeat/axpy --prepare-only

build/experimental-venv/bin/python -B scripts/build_final_monograph.py

build/experimental-venv/bin/python -B scripts/validate_final_patch.py \
  --output results/validation/final_patch_repeat \
  --axpy-run build/final-patch-repeat/axpy/run-IDENTIFICADOR \
  --patch ../tcc2-final-2026-11-16.patch
```

O gerador reexporta somente os novos arquivos consolidados; preserve qualquer
edição manual neles antes de regenerar. O validador exige o ZIP junto ao patch
e conserva o protocolo específico desta integração de 16/11.

## Limites restantes

Esta tarefa não executou nova inferência LLM, não promoveu o AXPY atual e não
transforma o smoke test em campanha científica controlada. A coleta científica
AXPY sob o novo contrato, os contadores físicos de cache/DRAM e a revisão nativa
do layout Word/ABNT continuam pendentes. Os avisos `ResourceWarning` de CSVs
abertos na rotina legada do corpus não causaram falhas e não foram ocultados.
Os caminhos históricos absolutos foram mantidos por integridade, não portabilizados
por edição dos JSONs. Testes aprovados não equivalem a aprovação acadêmica do TCC.
