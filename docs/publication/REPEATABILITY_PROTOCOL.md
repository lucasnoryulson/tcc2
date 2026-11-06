# Coletas adicionais de repetibilidade

Protocolo registrado antes de executar novas medições nesta etapa de
fortalecimento. A campanha principal anterior é preservada em
`results/multiplatform/linux_xeon_2026-11-05_p15w3/`.

Executar uma nova sessão completa com os mesmos códigos, entradas, três
aquecimentos e quinze observações externas por configuração, 1/2/4T e seed
2026. Uma terceira sessão prioriza as entradas MEDIUM e os dois tamanhos de
ambos os Dot. Assim, o conjunto comum entre as três sessões não inclui LARGE
de PolyBench; os conjuntos grandes terão duas sessões nesta etapa. Não se
excluirá uma sessão por seus resultados serem desfavoráveis.

As repetições usam uma cópia congelada do código em b9e252d; a ampliação do
transformador é outro experimento e não muda os binários destas campanhas.
O arquivo de cada coleta preserva as fontes efetivamente compiladas e os
novos executáveis e logs, além da referência ao código congelado. O Git do
checkout de trabalho descreve a sessão atual e sua árvore dirty, não uma
suposta versão já publicada das alterações.

As sessões serão iniciadas separadamente e executadas em sequência, sem testes
ou inferência concorrentes. Não há isolamento exclusivo de todas as atividades
do host. São sessões na mesma máquina e no mesmo dia: não se alega
independência, frequência fixa ou repetição em dias distintos.

O analisador existente verifica cada arquivo e mantém estatísticas e ICs
condicionais por campanha. `scripts/compare_sessions.py` compara somente
configurações comuns, exige identidade de fonte/compilador/flags e descreve
a dispersão das medianas entre sessões. Não agrupa as observações brutas como
se fossem uma única campanha maior. Seus poucos pontos não estimam um IC
populacional entre sessões.

A coleta M5 continua dependendo daquela máquina; repetir o Linux não a
substitui. A comparação Linux/M5 exige códigos, entradas e protocolo compatíveis.

## Reprodução do código congelado

Na raiz do repositório, com o submódulo no SHA de
`FROZEN_REPEAT_SOURCE.json`, use um diretório de preparação novo. A extração
não altera o checkout de trabalho:

```bash
mkdir -p build/repeat-b9e252d/benchmarks
git archive b9e252d scripts analysis kernels | tar -x -C build/repeat-b9e252d
cp -R benchmarks/PolyBenchC-4.2.1 build/repeat-b9e252d/benchmarks/
python3 -B build/repeat-b9e252d/scripts/benchmark_multiplatform.py \
  --output results/publication/reproduction-linux-session02 \
  --cc clang --cxx clang++ --threads 1 2 4 \
  --repetitions 15 --warmups 3 --seed 2026
python3 -B build/repeat-b9e252d/scripts/benchmark_multiplatform.py \
  --output results/publication/reproduction-linux-session03-medium \
  --cc clang --cxx clang++ --threads 1 2 4 --datasets MEDIUM \
  --repetitions 15 --warmups 3 --seed 2026
```

As saídas também precisam ser novas. Compare hashes dos fontes efetivamente
compilados antes de reunir curvas de outra execução. Registrar novamente o
ambiente é necessário mesmo com o mesmo commit.
