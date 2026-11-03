# Histórico da conversa e decisões para continuidade

Atualizado em **03/11/2026**. Síntese do histórico disponível nesta sessão.
Não é transcrição integral: nem todas as respostas antigas estão disponíveis
literalmente. Os estados técnicos abaixo foram conferidos com a documentação
e os arquivos atuais, sem reconstruir falas que não temos.

## Pedidos do usuário e evolução do trabalho

1. **“leia o contexto que adicionei na pasta tcc2_contexto”** e
   **“o que falta eu fazer para concluir o tcc?”**: o trabalho começou pela
   transferência do contexto do ChatGPT e inspeção do projeto. O contexto
   inicial descrevia lacunas no executor de promoção e nos gates.
2. O usuário trouxe uma resposta anterior do ChatGPT e confirmou:
   **“sim queria publicar esse trabalho”**. Depois definiu a prioridade:
   **“nao tenho mais tempo para ver com o orientador nem ver veiculo, so
   implementar o melhor que conseguir”**. O foco passou a ser fechamento técnico
   e acadêmico. Não houve autorização para submeter artigo ou contatar terceiros.
3. **“faça o primeiro passo primeiro”**, seguido de **“vc testou tudo para ver
   se esta funcionando?”**: foram implementados os contratos de evidência,
   promoção e integração, com testes positivos e negativos. Foi mantida a
   distinção entre integração com LLM simulada e inferência real.
4. **“pode continuar pq nao estou no mac agora, quando estiver la eu vejo.
   Vamos seguir para o passo 2”**: a ausência do Mac passou a ser uma restrição.
   Foram feitas as correções possíveis no Linux e explicitada a validação
   pendente no ambiente alvo.
5. O usuário reapresentou uma lista com o fechamento do pipeline e mais cinco
   tópicos e perguntou se os primeiros estavam feitos. O acompanhamento adotou
   os **seis itens originais consolidados**:

   | Número | Item |
   |---|---|
   | **1** | Fechar o pipeline até o resultado final |
   | **2** | Resolver lacunas de validação e configuração |
   | **3** | Delimitar o que o sistema automatiza |
   | **4** | Fechar a avaliação científica dos agentes |
   | **5** | Consolidar experimentos e reprodução |
   | **6** | Fechar monografia e defesa |

6. **“termine isso e me diga aonde estamos, use a numeracao da tabela que te
   dei antes”** e **“o que falta fazer?”**: foi mantida essa numeração nos
   relatórios de estado. Não renumerar para acompanhar uma lista nova de comandos.
7. **“faça o passo 4 entao”**: foi criado o experimento pareado de decisão com
   política determinística, Coordinator completo e ablação das análises, usando
   os mesmos candidatos e medições. Dois tamanhos de Dot Product foram medidos
   no Linux; chamadas reais ao qwen expiraram. A infraestrutura está pronta,
   mas isso não concluiu a pergunta científica sobre a contribuição da LLM.
8. **“o que podemos fazer agora sem o mac?”**, **“faça isso”**: foram consolidados
   os dados disponíveis, as métricas e gráficos, o catálogo explícito, a
   reprodução e a proteção contra sobrescrever históricos. Não se fingiu uma
   nova coleta Mac nem se corrigiram silenciosamente CSVs históricos quebrados.
9. O usuário perguntou **“entao so falta eu rodar os passos 4 e 5 no mac?”**
   e pediu que continuássemos. A resposta foi delimitada: falta coleta alvo,
   análise e integração final; ainda era possível preparar redação/defesa.
10. Durante a redação foi perguntado onde estava a monografia. O usuário respondeu
    **“adicionei uns arquivos em word na raiz do diretorio”**. Foram encontrados
    na pasta pai do repo três Word: proposta, guia e resumo executivo. Eles não
    constituíam uma monografia final completa e foram preservados sem alteração.
11. Os Word foram lidos e comparados ao código. Foram preparados uma base de
    monografia com resultados disponíveis, bibliografia conferida, diagrama,
    16 slides com notas, demonstração e prévias PDF. A revisão retirou alegações
    de implementação não sustentadas: GPU, LangGraph, codificador LLM geral e
    reparo autônomo. Corrigiu também a interpretação de eficiência paralela.
12. À pergunta **“entao agora so falta eu fazer os testes no mac?”**, o estado
    foi explicado como **quase**, com ações pendentes nos itens 1, 4, 5 e 6.
    Testar não substitui analisar, atualizar o texto, formatar e ensaiar.
13. Pedido atual: **“adiciona tudo isso e nossa conversa no contexto do codex
    para eu usar o codex no mac”**. Esta atualização grava o estado real, esta
    síntese, a orientação de retomada e um ponto de entrada AGENTS.md na raiz.
    O contexto antigo foi preservado como histórico, sem continuar apresentando
    implementação pronta como pendência futura.

## Decisões técnicas que não devem ser desfeitas na retomada

- A LLM decide sobre evidências; gates determinísticos controlam a admissão.
  Um PASS declarado em JSON ou ACCEPT escrito à mão não é prova de corretude.
- Promoção liga decisão, configuração e medições aos mesmos bytes e campanha;
  faz nova compilação/corretude e publica atomicamente. Não relaxar isso para
  obter uma demonstração positiva.
- O novo caminho integrado gera redução escalar independente/Dot Product.
  Classificar vários padrões não equivale a gerar todos automaticamente.
- Há uma LLM no Coordinator, não uma equipe de LLMs que gera e repara código.
  O uso do termo multiagentes precisa explicar os papéis determinísticos.
- O experimento atual mede concordância da decisão, aceitação/veto e custo.
  Não testa superioridade sobre geração monolítica nem busca de novos candidatos.
- Manter separadas as razões contra sequencial e contra OpenMP 1T; em tiled,
  usar o mesmo bloco no baseline. Não atribuir a escala de um kernel à LLM.
- Manter os históricos intactos, declarar hardware desconhecido quando faltar
  evidência e conservar timeouts/recusas. Falha é dado, não deve virar PASS.
- Não é necessário repetir todas as 19 campanhas. Escolher um recorte que
  sustente as perguntas de pesquisa e declarar os limites dos demais resultados.
- Preservar os três Word originais. As novas bases são rascunhos separados;
  o layout nativo Office ainda não foi verificado.

## Preferências de colaboração

Responder em português, de maneira direta, usando os seis números. O usuário
quer execução e continuidade, não sucessivas propostas de trabalho ou pedidos
de confirmação para tarefas reversíveis já autorizadas. Quando perguntar pelo
estado, informar o que foi realmente feito/testado e a próxima pendência concreta.
Não encerrar a tarefa alegando que o TCC está pronto só porque testes passaram.

Não presumir autorização para push/merge, publicação, submissão ou mensagens
a orientador/terceiros. O interesse em publicação deve permanecer registrado
como intenção futura, sem impedir o fechamento atual.

## Onde conferir detalhes e números

- [Contexto técnico atualizado](TCC2_CONTEXT.md).
- [Roteiro no Mac e mensagem para colar](../RETOMAR_NO_MAC.md).
- [Estado dos seis itens](../../docs/STATUS_TCC.md).
- [Fechamento, documentos e comandos](../../docs/FECHAMENTO_TCC.md).
- [Avaliação científica](../../docs/COORDINATOR_EVALUATION.md).
- [Consolidação e reprodução](../../docs/EXPERIMENT_REPRODUCTION.md).

Ao retomar, atualizar estes registros com os resultados efetivos do Mac.
Não perpetuar como atual uma pendência que a nova campanha tenha resolvido.
