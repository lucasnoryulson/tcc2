# Versão final na pasta principal — 16/11/2026

A pedido do usuário, a pasta principal `tcc2` passou a conter a versão final
do projeto, anteriormente acessível somente na worktree experimental.

## Git e preservação

- Pasta ativa: `/Users/lucasulson/Desktop/PUCRS/Ultimo semestre/TCC2/tcc2`.
- Branch ativa: `feat/final-patch-primary-2026-11-16`, criada a partir de `b5213bf`.
- O commit `b5213bf` contém a integração final; suas dependências, os experimentos
  e as monografias de novembro também fazem parte do histórico desta branch.
- A branch anterior `feat/mac-pipeline-validation` continua em `4bace11`, sem
  reescrita do histórico. Suas versões específicas permanecem recuperáveis ali.
- A worktree experimental e sua branch `feat/final-patch-integration-2026-11-16`
  permanecem intactas em `b5213bf`.
- `main` continua em `cc5406b79a1fac9446c6e0a25920243f82662a6e`.
  Não foi feito merge nem push.

A árvore estava limpa antes da troca de branch. A inspeção também confirmou que
nenhum arquivo não rastreado ocupava os novos destinos; a troca utilizou
`--no-overwrite-ignore`. Os ambientes virtuais e resultados locais em `build/`
foram mantidos, assim como os dois submódulos nas revisões fixadas.

## Verificação na pasta principal

A execução técnica AXPY foi repetida a partir de `tcc2`, com análise, geração,
compilação, corretude, benchmark, seleção e contexto reais. O protocolo usa
1/2/4/6/8/10T, quinze medições e três aquecimentos por configuração, seed 2026.
O resultado é `PREPARED`, sem inferência LLM nem nova promoção. Esses tempos
não foram incorporados às campanhas científicas históricas.

A validação completa e os logs desta pasta estão em
[`results/validation/primary_final_patch_2026-11-16/report.json`](../../results/validation/primary_final_patch_2026-11-16/report.json).
Ela executa a suíte de testes, seis scripts de regressão, isolamento estático,
sintaxe do roteiro Linux, reanálise dos holdouts, hashes e conferência dos
documentos Word/PDF. A suíte mantém 143 testes e os scripts cobrem 23 casos.

O verificador de holdout admite a mudança do campo informativo
`evaluation_campaign` causada pela nova pasta, mas continua comparando todos
os hashes, decisões congeladas, métricas e demais campos. Os JSONs históricos
não foram editados para substituir caminhos absolutos. Alguns vínculos antigos
ainda apontam à worktree experimental preservada; mudar de pasta não constitui
uma nova coleta nem torna esses arquivos historicamente portáveis.

Para esta verificação dos documentos foram reutilizadas as dependências do
Python experimental já instalado na pasta irmã, sem copiar o venv nem instalar
pacotes globais. O novo smoke AXPY utilizou o `python3` local.

## Arquivos principais

- [Monografia consolidada Markdown](../monografia/MONOGRAFIA_CONSOLIDADA.md).
- [Monografia consolidada Word](../monografia/MONOGRAFIA_CONSOLIDADA.docx).
- [Monografia consolidada PDF](../monografia/MONOGRAFIA_CONSOLIDADA.pdf).
- [Auditoria da integração do patch](FINAL_PATCH_INTEGRATION_2026-11-16.md).

O layout nativo Word/ABNT, a campanha científica AXPY atualizada e os contadores
físicos de cache/DRAM não foram concluídos por esta transferência de pasta.
