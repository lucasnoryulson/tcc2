# Execução equivalente e limites que dependem do M5

A etapa Linux não tem acesso ao Apple M5. Este arquivo prepara a execução;
não constitui evidência de que a nova matriz tenha sido medida no Mac.

Use um checkout separado desta branch e mantenha as evidências Linux juntas.
Inicialize PolyBench no SHA registrado, confira LLVM/OpenMP e recrie o venv
Python local. Não copie o venv ou execute os binários Linux no Mac.

```bash
git status --short --branch
git submodule update --init benchmarks/PolyBenchC-4.2.1
/opt/homebrew/opt/llvm/bin/clang --version
ollama list
bash scripts/run_publication_mac.sh results/publication/mac_m5_nova_coleta
```

O wrapper executa duas sessões completas e uma terceira com PolyBench MEDIUM,
usando 1/2/4/6/8/10T, quinze medições e três aquecimentos; depois executa o corpus
de automação e finalmente uma campanha diagnóstica heldout. Cada diretório é
novo. A terceira sessão não replica LARGE. O wrapper não instala ferramentas,
baixa modelos ou encerra trabalhos alheios; deve ser iniciado com o servidor
Ollama sem gerações concorrentes e sem outros benchmarks/testes ativos.

O compilador padrão do corpus é LLVM: nesse caso, o baseline GCC é omitido.
Se houver um GCC real com OpenMP, forneça o caminho como segundo argumento:

```bash
bash scripts/run_publication_mac.sh results/publication/mac_m5_gcc_nova_coleta \
  /caminho/verificado/gcc-13 qwen2.5:3b
```

O mesmo GCC compila os três braços do corpus. Não interpretar `/usr/bin/gcc`
como GNU GCC sem conferir a versão. A versão do compilador e runtime compõe
a identidade da plataforma; um contraste Linux GCC/Mac LLVM não isola CPU.
O diagnóstico usa o catálogo congelado da versão especificada pelo harness;
falhas e timeouts não devem ser substituídos por novas chamadas seletivas.

Para gráficos, instale `requirements-analysis.txt` num venv criado no Mac.
Para reexportar Word/PDF/PPTX, `requirements-publication.txt` registra as
dependências já usadas no Linux. Não transportar o venv:

```bash
python3 -m venv build/analysis-venv
build/analysis-venv/bin/python -m pip install -r requirements-publication.txt
```

Execute `scripts/analyze_scaling.py` separadamente em cada arquivo de coleta.
Use `scripts/compare_sessions.py` para sessões do mesmo ambiente e
`scripts/compare_multiplatform.py` para o contraste Linux/M5. Este último exige
compatibilidade real e mantém curvas distintas nos pontos comuns 1/2/4T.
Os pontos 6/8/10T são extensão do M5, que tem classes distintas de núcleo.

```bash
build/analysis-venv/bin/python -B scripts/analyze_scaling.py \
  results/publication/mac_m5_nova_coleta/scaling-session01 \
  --output results/publication/mac_m5_analysis_session01
build/analysis-venv/bin/python -B scripts/compare_multiplatform.py \
  results/multiplatform/linux_xeon_2026-11-05_p15w3 \
  results/publication/mac_m5_nova_coleta/scaling-session01 \
  --output results/publication/comparison_linux_m5_nova_coleta
```

O wrapper não declara inferência aprovada pelo simples código de saída: leia
`results.json` para COMPLETE, COMPLETE_WITH_FAILURES ou INCOMPLETE_TIMEOUT.
Ollama pode continuar após timeout; o harness interrompe novas chamadas LLM
e marca as restantes NOT_RUN. Investigue e encerre a geração antes de outra
campanha, preservando o arquivo parcial.

Para reproduzir também o segundo modelo previsto no Linux, confira que a
primeira campanha terminou e que não ficou geração ativa no servidor. Depois,
sem repetir seletivamente respostas, use um diretório novo:

```bash
python3 -B scripts/evaluate_diagnostics.py --model llama3.1:8b --split heldout \
  --repetitions 1 --num-ctx 4096 --num-predict 384 --timeout 180 \
  --output results/publication/mac_m5_nova_coleta/diagnostics-llama
```

Uma comparação de latência inclui hardware, aceleração efetiva, runtime,
carregamento e cache. Não atribuir diferenças entre Linux/M5 apenas ao modelo.

Ajustar a monografia e o artigo somente com dados reais depois dessa execução.
A conferência nativa no Word/PowerPoint, atualização do sumário, orientador,
banca e modelo institucional completo ainda requerem o ambiente e as informações
correspondentes. Os PDFs Linux são revisões de conteúdo, não atestados de layout
institucional. A capa pública oficial é preservada separadamente.

## Pacote de transferência desta revisão

O fechamento gera `tcc2_publicacao_linux_2026-11-06.zip` na pasta que contém o
checkout, acompanhado de `.zip.sha256`. O arquivo é novo e não substitui o
pacote p15w3 anterior. A raiz extraída contém fontes e evidências versionadas,
incluindo o submódulo PolyBench, mais `TRANSFER_MANIFEST.json` com commit, branch,
SHA do submódulo e hashes por arquivo. `.git`, venv, builds de desenvolvimento
e o ZIP legado aninhado são excluídos; snapshots/binários de evidência Linux
permanecem para auditoria e precisam ser recompilados para executar no Mac.

Confira o SHA-256 do ZIP antes de extrair. O pacote não é um clone Git; para
acompanhar commits, prefira clonar o repositório e selecionar a branch
`feat/publication-strengthening-2026-11-05`. No pacote, a fonte atual do
submódulo já está incluída; `git submodule update` só se aplica ao clone.
