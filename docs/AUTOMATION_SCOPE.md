# Escopo comprovado da automação

Este documento delimita o que o checkout atual analisa, transforma e executa
automaticamente. Classificação, planejamento, transformação, variantes
experimentais e decisão por LLM são capacidades diferentes.

## Caminho integrado comprovado

O runner completo foi demonstrado no Mac para **Dot Product em C com redução
escalar direta**:

1. análise AST e dependências;
2. classificação `REDUCTION_CANDIDATE`;
3. planejamento de redução OpenMP;
4. inserção determinística de `parallel for reduction`;
5. compilação e corretude numérica;
6. benchmark e seleção de threads;
7. decisão do Coordinator com uma LLM;
8. promoção, revalidação e publicação auditável.

A execução de 03/11/2026 terminou `PROMOTED` com `llama3.1:8b`, LLVM 23.1.1
e 4 threads. Essa evidência comprova o encadeamento do caminho suportado, não
uma transformação universal de programas C.

## Cobertura por caso

| Caso | Análise/classificação | Transformação | Pipeline completo atual |
|---|---|---|---|
| Dot Product / REDUCTION | Sim | Redução escalar direta, determinística | Sim |
| GEMM / DOALL | Sim | Variante OpenMP manual nas campanhas | Não |
| Jacobi-2D / STENCIL | Sim | Variantes manual e tiled | Não |
| Covariance / MIXED | Sim | Variante OpenMP manual | Não |
| Nussinov / WAVEFRONT | Sim | Transformações adaptativas específicas sobre base OpenMP existente | Não pelo runner genérico |
| Wavefront sintético | Sim | Variantes manual/tiled e autotuning | Não pelo runner genérico |

`analysis/code_transformer.py` recusa estratégias não suportadas no despacho
genérico. As rotinas adaptativas específicas existentes não constituem um
transformador universal nem um loop autônomo de reparo.

## Papel da LLM

Há uma LLM no Coordinator. Análise, transformação suportada, gates, seleção e
promoção são determinísticos. O termo “multiagente” descreve a divisão de papéis
funcionais; não significa múltiplas LLMs negociando, LangGraph, motor BDI ou
blackboard concorrente.

A LLM interpreta evidências e propõe uma ação estruturada. Ela não autoriza
sozinha corretude, desempenho, configuração ou publicação, e não é responsável
pelo speedup medido do código transformado.

## Fora do recorte comprovado

- GPU/CUDA;
- geração geral de C/C++ ou de todos os padrões classificados;
- múltiplas LLMs conversando;
- busca autônoma por novos candidatos;
- reparo autônomo iterativo após `RETUNE`, `MODIFY` ou `REJECT`;
- prova formal de equivalência ou ausência de races para todas as entradas;
- superioridade sobre geração monolítica de código por LLM.

Esses limites devem permanecer na monografia, nos slides e na defesa. Novas
capacidades só podem ser acrescentadas a esta tabela após implementação e
evidência reproduzível correspondentes.
