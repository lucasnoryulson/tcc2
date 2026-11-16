# Contadores Linux: protocolo preparado, ainda não executado

O fechamento de 16/11 ocorreu no macOS. Não existe nova medição de ciclos,
instruções, IPC, misses, trocas de contexto, migrações ou tráfego DRAM nesta
etapa. Os testes do parser usam entradas sintéticas identificadas como testes.
O perfil auxiliar Mac já arquivado mede espera e trabalho instrumentados,
não esses contadores. Esta pendência não é marcada como concluída.

## Execução no host Linux

Use um checkout desta feature, os submódulos fixados e a toolchain OpenMP Linux.
Não execute binários Mach-O do Mac. Primeiro confira `lscpu`, `perf --version`,
`perf list`, afinidade/cotas e o compilador; não suponha o mesmo hardware do
acervo Xeon. Os comandos abaixo são receitas para o host histórico de quatro
núcleos. Adapte a grade **antes** de congelar um novo protocolo, caso necessário.

Os binários Linux preservados podem ser usados como entrada somente se seus
hashes ainda coincidirem. O coletor verifica isso e exige saída inexistente.
O AXPY precisa de evidência gerada no Linux; não transporte caminhos de gates
Mac para aparentar validação local. Para uma nova coleta AXPY completa:

```bash
export PATH=/usr/lib/llvm-18/bin:$PATH
python3 -B scripts/evaluate_axpy_campaign.py prepare \
  --protocol docs/experiments/AXPY_LINUX_FOLLOWUP_PROTOCOL_2026-11-16.json \
  --directory results/axpy_scientific/linux_counter_followup_NEW
python3 -B scripts/evaluate_axpy_campaign.py session01 \
  --compiler clang --directory results/axpy_scientific/linux_counter_followup_NEW
python3 -B scripts/evaluate_axpy_campaign.py freeze \
  --directory results/axpy_scientific/linux_counter_followup_NEW
sleep 30
python3 -B scripts/evaluate_axpy_campaign.py session02 \
  --compiler clang --directory results/axpy_scientific/linux_counter_followup_NEW
python3 -B scripts/evaluate_axpy_campaign.py analyze \
  --directory results/axpy_scientific/linux_counter_followup_NEW \
  --output results/axpy_scientific/analysis_linux_counter_followup_NEW
```

Depois de encerrar benchmarks, testes e inferências, colete em arquivo separado:

```bash
bash scripts/profile_linux_followup.sh \
  results/multiplatform/linux_xeon_2026-11-05_p15w3 \
  results/profiling/linux_counters_NEW \
  --axpy-session results/axpy_scientific/linux_counter_followup_NEW/session01 \
  --threads 1 2 3 4 --compiler clang --repetitions 5
```

O alvo compreende sequencial e variantes de Dot Product, AXPY, GEMM, Nussinov,
Jacobi-2D e Covariance. As quatro últimas são implementações manuais ou
adaptações específicas, não geração geral da LLM. AXPY/Dot gerados são
identificados separadamente. Se os binários antigos estiverem ausentes, faça
uma nova campanha multiplataforma com `scripts/run_multiplatform_linux.sh`,
em diretório novo, antes de usá-la como entrada. Não reconstrua sobre o arquivo
histórico para que os hashes pareçam coincidir.

## Interpretação e eventos indisponíveis

Ciclos e instruções são solicitados juntos, assim como referências/misses de
cache. IPC é razão dos contadores médios pareados pelo perf. Os eventos de
software têm chamada separada, preservando sua coleta mesmo se a PMU recusar
eventos de hardware. `NOT_SUPPORTED`, `NOT_COUNTED`, retorno não zero e timeout
ficam nos logs/JSON; valor ausente não vira zero. Não alterar `perf_event_paranoid`
ou executar com privilégios elevados automaticamente. Resultado `PARTIAL` ou
recusa de acesso é uma limitação real, não motivo para criar dados substitutos.

Os contadores abrangem o processo completo, incluindo alocação, inicialização,
runtime e validação, e não somente o trecho temporizado do kernel. Uma mudança
de IPC não comprova causa única; taxas de misses dependem do significado dos
eventos e da PMU. A ferramenta retém colunas brutas, inclusive multiplexação,
em vez de produzir precisão sem suporte. Compare instruções e ciclos do mesmo
escopo e não junte contagens coletadas em grupos/processos distintos para IPC.

Para memória, escolha primeiro um evento realmente suportado em `perf list` e
registre a documentação da PMU. A opção `--memory-event EVENTO` permite uma
coleta separada; nenhum nome genérico é fornecido como se fosse universal.
Eventos uncore podem exigir outro escopo/permissão e incluir outros processos:
nesse caso, a coleta deve ser declarada separadamente, não atribuída ao kernel.
Sem bytes transferidos e intervalo correspondente não se calcula banda DRAM.

As hipóteses e a confirmação necessária por kernel estão em §6.3 da
monografia. A implementação/teste do roteiro não confirma essas hipóteses.
