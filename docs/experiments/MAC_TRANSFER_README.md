# Retomada no Apple M5 — protocolo 15/3

A branch Linux é `feat/multiplatform-protocol-2026-11-05`, baseada em
`32ae80b2bfb46d8819f099645864b1a2fc60ba3c`, com alterações locais preservadas.
Não houve push ou merge. O ZIP `tcc2_multiplataforma_p15w3_mac_2026-11-05.zip`
é um overlay dos arquivos novos/modificados sobre esse commit, com fontes,
resultados Linux e documentos. Não contém `.git`, venv ou o checkout completo
dos submódulos. Os executáveis Linux são evidências para integridade; não devem
ser executados no Mac. O ZIP anterior de sete amostras foi preservado.

Use um diretório novo para preservar o trabalho existente no Mac. Na raiz do
repositório que já contém o commit:

```bash
git status --short --branch
git worktree add -b feat/multiplatform-m5-p15w3 ../tcc2-m5-p15w3 32ae80b
cd ../tcc2-m5-p15w3
shasum -a 256 /caminho/tcc2_multiplataforma_p15w3_mac_2026-11-05.zip
unzip /caminho/tcc2_multiplataforma_p15w3_mac_2026-11-05.zip
git submodule update --init benchmarks/PolyBenchC-4.2.1
```

Confira o hash do ZIP contra o arquivo `.sha256` que o acompanha. Depois de
extrair, confira o inventário de bytes incluído:

```bash
python3 - <<'PY'
import hashlib, json
from pathlib import Path
items = json.loads(Path('TRANSFER_MANIFEST.json').read_text())['files']
bad = [name for name, digest in items.items()
       if not Path(name).is_file()
       or hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest]
assert not bad, bad
print(f'{len(items)} arquivos conferidos')
PY
```

O coletor usa apenas biblioteca padrão Python, compiladores e ferramentas do
sistema. Confirme o LLVM com OpenMP antes da campanha. Não rode testes,
inferência ou outras campanhas enquanto mede. O programa de probe do coletor
confere suporte OpenMP e equipes solicitadas. As quantidades físicas e classes
de núcleo são registradas; não se assume homogeneidade dos dez núcleos.

```bash
/opt/homebrew/opt/llvm/bin/clang --version
git submodule status
bash scripts/run_multiplatform_mac.sh results/multiplatform/mac_m5_nova_coleta_p15w3
```

Os padrões são quinze medições externas e três aquecimentos, seed 2026, duas
entradas por caso e threads 1/2/4/6/8/10. Com a matriz completa, esperam-se
108 configurações, 1.620 medições, 324 aquecimentos e 108 validações. O número
é planejamento, não resultado Mac. O diretório deve ser inexistente. Em caso
de falha, preserve-o e investigue o erro antes de iniciar outra campanha.

Crie dependências de análise no próprio Mac; não copie o venv Linux:

```bash
python3 -m venv build/analysis-venv
build/analysis-venv/bin/python -m pip install -r requirements-analysis.txt
build/analysis-venv/bin/python -B scripts/analyze_scaling.py \
  results/multiplatform/mac_m5_nova_coleta_p15w3 \
  --output results/multiplatform/analysis_mac_m5_nova_coleta_p15w3
build/analysis-venv/bin/python -B scripts/compare_multiplatform.py \
  results/multiplatform/linux_xeon_2026-11-05_p15w3 \
  results/multiplatform/mac_m5_nova_coleta_p15w3 \
  --output results/multiplatform/comparison_linux_mac_p15w3
```

Sem matplotlib, `analyze_scaling.py --no-plots` ainda verifica o arquivo e gera
tabelas; a comparação com figuras requer as dependências de análise. O
comparador recusa divergências de protocolo, fontes compiladas, dimensões ou
flags. Não editar hashes/caminhos históricos para contornar uma recusa.

As curvas comparadas conservam cada campanha separada nos pontos comuns
1/2/4T. As extensões 6/8/10T pertencem ao M5. O compilador e runtime mudam junto
com a arquitetura; os resultados não isolam quantidade de núcleos ou ISA.
Nenhuma inferência LLM participa desta coleta de desempenho.

Depois da coleta real, incorporar os dados e a discussão à monografia em novos
artefatos. `report_multiplatform.py` escreve o relatório Linux atual e a seção
5.8; não apontá-lo para o Mac usando os caminhos de saída padrão, pois isso
substituiria a revisão Linux. Os gráficos de comparação são gerados pelo
comparador, sem necessidade de reescrever o arquivo científico original.

Word/PDF de revisão e capa oficial estão em `docs/monografia/`. A capa é um
arquivo separado, preenchido a partir do modelo público; orientador e banca
não foram inventados. O sumário Word é um campo automático que precisa ser
atualizado no editor. O PDF foi produzido por ReportLab e não certifica o
layout nativo Word nem atendimento integral ao modelo institucional completo.
