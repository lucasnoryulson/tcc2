# Revisão da entrega Linux e retomada M5

Branch: `feat/multiplatform-protocol-2026-11-05`. HEAD de base:
`32ae80b2bfb46d8819f099645864b1a2fc60ba3c`. Alterações locais anteriores foram
preservadas. Não houve push, merge ou nova inferência LLM nesta campanha.
O pedido completo recebido está em `REQUISITOS_2026-11-05.md`.

## Estado dos seis itens originais

1. **Pipeline:** fechamento anterior no Mac preservado, com promoção real do
   Dot Product; a campanha atual mede escalabilidade e não constitui promoção.
2. **Validação:** 91 testes unittest sem skips; 23 casos de regressão, análise
   estática isolada e verificações shell aprovados no Linux.
3. **Escopo:** geração automática C de redução escalar separada do C++ manual,
   GEMM/Jacobi/Covariance manuais e adaptações específicas de Nussinov.
4. **Agentes:** evidências anteriores com `llama3.1:8b` preservadas; a campanha
   atual não avalia decisões LLM nem demonstra contribuição da LLM ao ganho.
5. **Experimentos:** Linux completo e verificado, 60 configurações, 900 tempos,
   180 aquecimentos e 60 validações. Coleta equivalente Mac pendente.
6. **Monografia:** revisão nova em Markdown, Word e PDF; capa oficial pública
   preenchida separadamente. Conferência institucional e Mac ainda pendentes.

## Resultados principais

Máquina Linux Intel Xeon E3-1225 V2, x86-64, quatro núcleos físicos/lógicos e
CPUs disponíveis 0–3; LLC 8 MiB, memória registrada 19,47 GiB; Clang 18.1.3,
Python 3.12. Ambiente, versões, hash do compilador, submódulos, flags e macros
efetivas constam em `environment.json`, `report.json` e `commands.jsonl` da
campanha. Governor schedutil, sem frequência ou temperatura fixadas.

Medianas da entrada maior, na configuração recomendada:

| Caso | Tseq (s) | Threads | Tp (s) | Tseq/Tp | T1/Tp | Eficiência |
|---|---:|---:|---:|---:|---:|---:|
| Dot C automático, N=10.000.000 | 0,010833251 | 2 | 0,008641622 | 1,254 | 1,276 | 0,638 |
| Dot C++ manual, N=10.000.000 | 0,011178234 | 2 | 0,010711598 | 1,044 | 1,239 | 0,619 |
| GEMM LARGE | 0,629662 | 4 | 0,221314 | 2,845 | 2,854 | 0,714 |
| Nussinov LARGE manual | 17,410415 | 4 | 5,449333 | 3,195 | 3,204 | 0,801 |
| Nussinov LARGE SIMD manual | 17,410415 | 4 | 5,853742 | 2,974 | 3,110 | 0,778 |
| Nussinov LARGE SIMD adaptado | 17,410415 | 4 | 5,883270 | 2,959 | 3,091 | 0,773 |
| Jacobi-2D LARGE | 2,577300 | 2 | 2,190225 | 1,177 | 1,182 | 0,591 |
| Covariance LARGE | 12,283083 | 4 | 5,601431 | 2,193 | 2,183 | 0,546 |

Dot C e C++ grandes tiveram menor mediana OpenMP em 4T, mas 2T foi recomendado
pelo quase empate de até 2%. Os dois casos menores de Dot foram mantidos
sequenciais. Todos os demais casos médios foram recomendados em 4T. As 60
linhas completas, média, desvio amostral, MAD, IQR, transformação Tseq/T1 e
intervalos estão no CSV derivado e no relatório numérico.

Os intervalos percentis bootstrap usam 5.000 reamostragens de rodadas completas,
seed 2026, com pareamento entre baselines e variante. Exigem pelo menos quinze
amostras externas; não há inferência baseada nas chamadas internas do Dot C
como se fossem observações independentes. Não houve exclusão de outliers.

Corretude: resultado esperado finito para Dot, com tolerância explícita; dumps
PolyBench inteiros ou floating-point em 17 dígitos, nas saídas imprimíveis.
Isso não comprova ausência de races ou equivalência para qualquer entrada.

## Artefatos novos e arquivos alterados

- **Coleta:** `scripts/benchmark_scaling.py`, `benchmark_multiplatform.py`,
  `run_multiplatform_linux.sh` e `run_multiplatform_mac.sh`.
- **Análise:** `scripts/analyze_scaling.py`, `compare_multiplatform.py`,
  `report_multiplatform.py`, `test_benchmark_scaling.py`.
- **Exportação:** `scripts/build_multiplatform_material.py`, extensão de
  `build_academic_material.py` para blocos de código e contagem de imagens;
  `requirements-multiplatform-writing.txt`.
- **Dados e logs:** `results/multiplatform/linux_xeon_2026-11-05_p15w3/`;
  análise em `analysis_linux_xeon_2026-11-05_p15w3/`; diagnósticos compilados
  e logs de testes em diretórios irmãos, identificados separadamente.
- **Documentação:** protocolo, relatório completo, requisitos preservados,
  revisão dos diagnósticos de Nussinov, este documento e retomada Mac em
  `docs/experiments/`. README e `docs/STATUS_TCC.md` atualizados.
- **Redação:** `docs/monografia/REVISAO_MULTIPLATAFORMA.{md,docx,pdf}`,
  `ARQUITETURA_E_ALGORITMOS_MULTIPLATAFORMA.md`, figuras próprias, referências
  bibliográficas novas e `MULTIPLATFORM_WRITING_MANIFEST.json`.
- **Preservação:** `BASE_MONOGRAFIA_ORIGINAL_32ae80b.md`, modelo oficial de
  capa e sua origem/hash; capa preenchida `CAPA_PUCRS_MULTIPLATAFORMA.docx`.

O inventário `files_changed_from_HEAD.tsv`, no diretório de validação, lista os
caminhos e hashes de todos os arquivos novos/modificados desde HEAD, incluindo
as alterações locais da etapa exploratória anterior. Os logs científicos são
numerosos; o inventário evita omiti-los. `historical_integrity.json` verifica
**1.737 arquivos anteriores sem alteração**, com mapa de hashes preservado ao
lado. A base já modificada na etapa anterior e seus resultados não foram
reescritos nesta etapa de quinze amostras.

## Verificação executada

Comando unittest completo:

```bash
python3 -B -m unittest scripts.test_experiment_consolidation \
  scripts.test_coordinator_evaluation scripts.test_pipeline_integration \
  scripts.test_candidate_promotion scripts.test_gate_contracts \
  scripts.test_coordinator_scenarios scripts.test_benchmark_scaling
```

Resultado: **91 testes, 19,470 s, OK, sem skips**. As respostas LLM de testes
de integração são simuladas, não novas inferências científicas.

Regressões separadas, todas com saída zero:

| Script em scripts/ | Casos |
|---|---:|
| test_coordinator_v02_regression.py | 7 |
| test_performance_selector_v02_regression.py | 3 |
| test_autotuning_selector_v01_regression.py | 4 |
| test_adaptive_strategy_planner_v01_regression.py | 3 |
| test_compiler_feedback_analyzer_v01_regression.py | 3 |
| test_compiler_feedback_analyzer_v02_regression.py | 3 |

Também passaram `test_static_analysis_variant_isolation.py`, `bash -n` nos dois
wrappers e os testes sem argumentos (saída 2 esperada). O CLI de comparação foi
exercitado comparando o mesmo arquivo real MINI consigo próprio; esse teste
não é uma coleta Mac. A suíte verifica também a recusa de arquivos divergentes.

O analisador científico verificou hashes e reconstruiu os tempos a partir das
saídas. Os geradores de relatório e redação têm asserts de vínculo/contagem e
reabertura dos arquivos. O Word contém 13 tabelas, 15 imagens, código em fonte
monoespaçada e campo de sumário automático; o PDF tem 47 páginas, sumário
preenchido e texto sem caractere de substituição. Páginas de arquitetura,
exemplos C/pseudocódigo, tabelas e gráficos foram renderizadas e inspecionadas.
`git diff --check` passou. Logs e `final_checks.json` estão no diretório de
validação da campanha.

## O que depende do Mac ou de fechamento editorial

A matriz equivalente Mac ainda precisa ser medida com os mesmos códigos e
entradas. O wrapper inclui 1/2/4/6/8/10T; somente 1/2/4T serão comuns ao Linux.
O comparador exige compatibilidade e mantém curvas separadas. As diferenças
continuarão envolvendo CPU, ISA, cache, memória, compilador e runtime juntos.
O pacote de transferência e seus passos estão em `MAC_TRANSFER_README.md`.

A capa pública oficial foi preservada e preenchida; o modelo institucional
completo depende de autenticação. Não foi validado layout nativo no Microsoft
Word nem gerado PDF pelo Word. O sumário Word deve ser atualizado no editor.
O PDF ReportLab é uma revisão de conteúdo, com limites declarados. Orientador,
banca e integração da capa ao modelo final exigem conferência institucional.

Sem controle exclusivo de frequência/temperatura, contadores de hardware,
detector de races ou campanhas independentes adicionais, hipóteses sobre
memória/cache permanecem hipóteses. A divergência de Nussinov entre a coleta
exploratória e a atual foi preservada e discutida. Resultados antigos e novos
não foram agrupados para aumentar o número de amostras. Nada nesta coleta
demonstra ganho decisório adicional da LLM.
