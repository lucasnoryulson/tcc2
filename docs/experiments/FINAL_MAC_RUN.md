# Coleta adicional no Apple M5

A campanha científica AXPY também foi concluída; consulte
`AXPY_SCIENTIFIC_2026-11-16_REPORT.md` e o protocolo próprio. Os comandos abaixo
continuam como receitas opcionais, não como indicação de coleta pendente.

As duas campanhas equivalentes de 16/11 já foram coletadas e estão descritas em
`MAC_EVALUATION_2026-11-16_DELIVERY.md`. Este roteiro recebido no patch é opcional:
use nomes de saída novos caso precise repetir a coleta. Não substitua as sessões
existentes nem o holdout Mac cujas escolhas foram congeladas antes da coleta.

Não misture estes arquivos com os resultados históricos de novembro. Execute na
raiz do repositório, mantenha o mesmo commit entre sessões, conecte o Mac à
energia, feche aplicações de carga intensa e deixe esfriar entre sessões. Registre
qualquer interrupção e não descarte uma configuração apenas por ser lenta.

## 1. Testes antes das medições

```bash
export PATH="/opt/homebrew/opt/llvm/bin:$PATH"
clang --version
python3 -m unittest scripts.test_axpy_contract scripts.test_final_evaluation \
  scripts.test_gate_contracts scripts.test_pipeline_integration scripts.test_automation_corpus
```

Um teste AST pulado não comprova a aceitação de AXPY. Garanta que o LLVM e o
runtime OpenMP estejam disponíveis. Inicialize os submódulos já fixados no
repositório, se necessário (`git submodule update --init --recursive`).

## 2. AXPY com novo contrato e custo

```bash
python3 scripts/run_pipeline.py \
  --source analysis/fixtures/axpy.c \
  --driver analysis/fixtures/axpy_driver.c \
  --benchmark-driver analysis/fixtures/axpy_benchmark_driver.c \
  --compiler /opt/homebrew/opt/llvm/bin/clang \
  --threads 1 2 4 6 8 10 --repetitions 15 --warmups 3 --seed 2026 \
  --work-dir results/axpy_mac_2026-11-16 --prepare-only
```

Use o diretório `run-*` exibido/gerado para o relatório de custo (não mova o
diretório antes da análise: a proveniência usa caminhos absolutos).

```bash
python3 scripts/analyze_pipeline_cost.py results/axpy_mac_2026-11-16/run-IDENTIFICADOR
```

Com Ollama disponível, repita sem `--prepare-only`, com `--model llama3.1:8b`
e `--output-dir results/axpy_mac_promoted_2026-11-16`. A tentativa é uma nova
sessão, não uma reutilização silenciosa dos tempos anteriores. `NOT_PROMOTED`
é um resultado válido. Registre o custo de cada etapa, o resultado da decisão,
os arquivos de evidência e a configuração recomendada.

## 3. Campanha multiplataforma e sessão posterior

```bash
bash scripts/run_multiplatform_mac.sh results/multiplatform/mac_m5_2026-11-16_p15w3 --seed 2026
bash scripts/run_multiplatform_mac.sh results/multiplatform/mac_m5_2026-11-16_holdout_p15w3 --seed 2027
python3 scripts/evaluate_selector_sessions.py \
  results/multiplatform/mac_m5_2026-11-16_p15w3 \
  results/multiplatform/mac_m5_2026-11-16_holdout_p15w3 \
  --output results/publication/selector_holdout_mac_2026-11-16
python3 scripts/compare_multiplatform.py \
  results/multiplatform/linux_xeon_2026-11-05_p15w3 \
  results/multiplatform/mac_m5_2026-11-16_p15w3 \
  --output results/multiplatform/comparison_linux_mac_2026-11-16
```

Se a comparação retornar `INCOMPARABLE`, examine `comparability.json`. Não
force a comparação; confirme a identidade de fontes e flags. Os resultados do
Mac com 6/8/10T não têm pares correspondentes no Linux histórico. Mantenha-os
como extensão Mac. A primeira sessão fixa as recomendações; o holdout apenas
mede o custo da escolha derivada da primeira sessão. Este modo é retrospectivo
e não comprova congelamento prévio de um arquivo de decisões. Para congelamento
verificável antes da coleta, use `evaluate_selector_holdout.py --selection ...
--freeze ...` e, somente após uma nova sessão, `--freeze ... --evaluation ...
--output ...`. Não ajuste o limiar usando o holdout.

## 4. Perfil e teste de hipótese de gargalo (complementar)

Registre contadores quando houver acesso: ciclos, instruções, misses de cache,
throughput de memória e tempo bloqueado em sincronizações. No Mac, confira os
templates disponíveis com `xcrun xctrace list templates`; utilize Time Profiler
ou CPU Counters no Instruments, se disponíveis. Registre o template e a versão.
No Linux, utilize `perf stat` com eventos suportados pelo host, sem elevar
privilégios ou assumir que eventos genéricos equivalem à banda DRAM.

Para AXPY, compare tamanhos em regimes de cache e memória principal; para
Covariance, compare duas variantes que diferem somente no schedule; para
Jacobi, avalie a localidade e sincronização. Valide integralmente cada variante
antes de medir e preserve as flags. Registre os contadores separadamente das
medições de latência: a instrumentação altera a execução. Se o dispositivo não
expor contadores, declare a hipótese como não confirmada por contadores, em vez
de inferir causalidade da curva de speedup.

## 5. Atualizar monografia

Atualize §5.8 (AXPY), §5.9 (holdout), a comparação multiplataforma, resumo,
abstract, discussão e conclusão usando os arquivos reais. Preserve as fontes,
logs e metadados; não copie o ganho de um candidato histórico para outro.
`docs/monografia/MONOGRAFIA_CONSOLIDADA.md` é a fonte nova. As versões anteriores
continuam arquivadas e o documento institucional deve ser conferido antes do envio.

Para exportar a fonte, com `python-docx`, `reportlab`, `Pillow` e `matplotlib`
disponíveis no ambiente, execute `python3 scripts/build_final_monograph.py`.
O script preserva os documentos anteriores; confira o sumário e a paginação
no Word e preencha os campos institucionais antes da versão de entrega.
