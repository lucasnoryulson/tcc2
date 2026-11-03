# Demonstração reproduzível — item 6

Objetivo: demonstrar o encadeamento das evidências e uma recusa por integridade.
Não usar uma inferência sem prazo previsível como requisito de uma apresentação
curta. O roteiro sugere cerca de três minutos de exposição depois do preparo.

## 1. Preparar antes da apresentação

Na raiz `tcc2/`, com Python, Clang para o AST e GCC/OpenMP no Linux:

```bash
python3 -B scripts/run_pipeline.py --prepare-only \
  --compiler gcc --threads 1 2 --work-dir build/defense-demo
```

No Mac, substituir o compilador pela toolchain OpenMP funcional, por exemplo o
caminho registrado no ambiente de setembro, se ainda instalado:

```bash
python3 -B scripts/run_pipeline.py --prepare-only \
  --compiler /opt/homebrew/opt/llvm/bin/clang --threads 1 2 \
  --work-dir build/defense-demo
```

Cada execução cria um diretório novo `run-*`. O preparo mede o benchmark real
com cinco repetições por configuração e pode demorar mais que a demonstração.
Não executá-lo simultaneamente com testes ou outras medições.

## 2. Mostrar o resultado e conferir o vínculo

O comando abaixo escolhe a preparação mais recente da pasta reservada à
demonstração, exige estado PREPARED e verifica contexto/gates. O timestamp do
diretório é usado apenas para escolher a pasta; a validade vem dos relatórios.

```bash
python3 - <<'PY'
import json
from pathlib import Path
from analysis.artifact_provenance import load_context_evidence

runs = sorted(Path('build/defense-demo').glob('run-*'), key=lambda p: p.stat().st_mtime)
if not runs:
    raise SystemExit('Preparar o pipeline antes da demonstração.')
run = runs[-1]
summary = json.loads((run / 'summary.json').read_text())
if summary['status'] != 'PREPARED':
    raise SystemExit(f"Preparação incompleta: {summary['status']}; consultar {run}")
context, evidence, reference = load_context_evidence(run / 'context.json')
if reference != summary['context']:
    raise SystemExit('Contexto diferente da preparação registrada.')
print('Execução:', run)
print('Candidato:', context['source']['candidate_id'])
print('Corretude:', evidence['correctness']['status'])
print('Threads validadas:', evidence['correctness']['validated_threads'])
print('Seleção:', evidence['selection']['parallel_status'])
for row in evidence['measurements']:
    print(row['mode'], row['threads'], 'mediana (s):', row['median_seconds'])
PY
```

Fala sugerida: “O código do contexto corresponde às cópias validadas. As mesmas
configurações medidas constam da seleção. O resultado pode indicar sucesso ou
ausência de ganho, conforme esta coleta; não altero os dados para obter ACCEPT.”

## 3. Demonstrar uma recusa sem alterar os arquivos do projeto

```bash
python3 -B -m unittest \
  scripts.test_candidate_promotion.CandidatePromotion.test_changed_candidate_driver_or_original_never_promotes
```

Esse teste cria seus arquivos temporários, produz evidências controladas, altera
um artefato e verifica que o executor recusa antes de revalidar/publicar. Ele
não modifica os resultados históricos. Fala sugerida: “Este é um teste de
proteção do contrato, com evidência controlada; não é uma nova medição científica.”

## 4. Mostrar a publicação quando houver decisão real concluída

Uma execução completa para preparar fora da apresentação:

```bash
python3 -B scripts/run_pipeline.py --compiler gcc --threads 1 2 \
  --model qwen2.5:3b --timeout 600 --work-dir build/defense-full \
  --output-dir results/defense-promoted
```

Ajustar a toolchain no Mac. Só usar a publicação como caso real de decisão da
LLM se o modelo concluir a inferência e o runner terminar em PROMOTED. Conferir
o manifesto, os hashes, a configuração e a revalidação. RETUNE/MODIFY/REJECT,
ausência de ganho ou timeout são desfechos que devem ser apresentados como tais.

O bundle real do Mac está em
`results/final-promoted/mac-2026-11-03/5eef401105cc51be73471cfbf836964f858d9453a381224490828123f54eb1d5/`.
Ele registra `llama3.1:8b`, decisão `ACCEPT`, 4 threads, revalidação `PASS` e
os hashes das evidências. O bundle antigo em `build/validation/final/promoted/`
continua sendo integração com Coordinator simulado e não deve ser apresentado
como inferência real.

## Plano de apresentação sem execução ao vivo

Abrir o slide das curvas locais e os relatórios previamente gerados. Mostrar
arquivo do candidato, configuração, tempos e condição de recusa. Os dados são
da coleta registrada, sem afirmar que foram medidos durante a fala. Não editar
PASS, nomes de modelos, timestamps ou campos do manifesto para simular sucesso.
