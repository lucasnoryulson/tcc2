# Validação do fechamento Linux — 6 de novembro de 2026

Os testes verificam software e integridade local. Não multiplicam o número
de programas, inferências ou observações científicas. Os logs estão em
[validation_linux_2026-11-05](../../results/publication/validation_linux_2026-11-05/).

| Verificação | Resultado observado |
|---|---|
| Unittest da árvore final | 123 aprovados em 23,130 s; zero falhas/skips |
| Seis scripts de regressão | 23 casos aprovados |
| Isolamento de análise estática | PASS; saídas distintas por variante |
| Sintaxe dos três wrappers Mac | PASS, `bash -n` |
| Colisão de diretório de saída | Dois wrappers recusaram antes de executar medições/inferências |
| Arquivo científico do corpus | VERIFIED; manifestos e estatísticas/seleção reconstruídos |
| Diagnósticos Qwen/Llama | Catálogo/harness congelados, agenda, prompts, respostas, metadados, scores e agregados conferidos |
| Análises S2/S3 e comparações | PASS; 60 configurações comuns em duas sessões e 38 em três, sem reunir amostras |
| Históricos preservados | 4.416 arquivos, zero hashes alterados |
| Word e PowerPoint novos | ZIPs sem corrupção e reabertura pelas bibliotecas aprovados |
| PDFs novos | Texto, números principais e ausência de marcadores conferidos; revisão visual representativa |

Comandos da bateria e relatório:

```bash
python3 -B -m unittest discover -s scripts -p 'test_*.py' -v
python3 -B scripts/test_static_analysis_variant_isolation.py
python3 -B scripts/evaluate_automation_corpus.py --verify \
  --output results/publication/automation_corpus_linux_2026-11-05
python3 -B scripts/report_publication.py \
  --corpus results/publication/automation_corpus_linux_2026-11-05 \
  --diagnostics results/publication/diagnostics_qwen_heldout_linux_2026-11-05 \
    results/publication/diagnostics_llama_heldout_linux_2026-11-05 \
  --sessions results/publication/session_comparison_linux_2026-11-05
```

Os seis scripts são `test_adaptive_strategy_planner_v01_regression.py`,
`test_autotuning_selector_v01_regression.py`,
`test_compiler_feedback_analyzer_v01_regression.py`,
`test_compiler_feedback_analyzer_v02_regression.py`,
`test_coordinator_v02_regression.py` e
`test_performance_selector_v02_regression.py`, em `scripts/`.
O [registro shell](../../results/publication/validation_linux_2026-11-05/regressions_shell_final.json)
identifica comandos, retornos e uma expectativa inicial corrigida, preservada.
As falhas de desenvolvimento anteriores têm [registro próprio](PREFLIGHTS.md).

## Exportações e conferência

```bash
MPLCONFIGDIR=/tmp/tcc2-mpl-cache build/analysis-venv/bin/python -B \
  scripts/build_publication_material.py \
  --corpus results/publication/automation_corpus_linux_2026-11-05 \
  --diagnostics results/publication/diagnostics_qwen_heldout_linux_2026-11-05 \
    results/publication/diagnostics_llama_heldout_linux_2026-11-05
```

A monografia Word tem 22 tabelas e 19 imagens; o PDF de revisão tem 70 páginas.
O artigo Word tem nove tabelas e quatro imagens; o PDF, 23 páginas. O PPTX
tem vinte slides e vinte notas. A capa pública oficial foi preenchida em
arquivo novo; sua conferência lê também os textboxes no XML. Os 24 arquivos
no [manifesto de escrita](../monografia/PUBLICATION_WRITING_MANIFEST.json)
conservaram seus hashes na reabertura. Links locais dos três Markdown foram
resolvidos. A dependência de exportação está em `requirements-publication.txt`.

Foram inspecionadas as cinco figuras novas e páginas representativas dos PDFs.
Os [resultados da conferência](../../results/publication/validation_linux_2026-11-05/academic_artifacts_final.json)
e renders da [monografia](../../results/publication/validation_linux_2026-11-05/visual_monograph_page47.png)
e do [artigo](../../results/publication/validation_linux_2026-11-05/visual_article_page10.png)
ficam arquivados. Os PDFs são produzidos por ReportLab para revisão de conteúdo;
não são renderizações nativas do Word. Não se verificou integralmente o layout
no Word/PowerPoint nem se aprovou o template institucional completo.

## Falhas experimentais preservadas

A tentativa integrada DOALL real terminou FAILED por timeout Qwen de 180 s,
sem decisão/promoção e sem retry. A contraprova numérica pré-declarada teve
sequencial/1T zero e 2T solicitado `-inf`, com gate FAIL. Esses desfechos são
resultados preservados, fora das 2.940 medições do corpus. Testes de promoção
com Coordinator/tempos simulados têm identificação explícita e não substituem
essa inferência. A entrada extrema não prova garantia numérica geral.

A nova matriz M5, revisão humana independente dos rótulos, conferência nativa
Office, dados da banca e aprovação acadêmica/editorial continuam externos.

A checagem de whitespace se aplica ao código atual e aos Markdown. Saídas brutas,
CSV/JSONL, dumps e arquivos PDF/SVG mantêm seus bytes, inclusive whitespace de
instrumentação, para conservar hashes; os avisos sobre esses dados não são
corrigidos reformatando evidências. O arquivo de corretude guarda snapshots
mesmo onde o nome build/ é ignorado por padrão pelo Git.
