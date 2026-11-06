# Contraprova funcional de limite numérico — protocolo anterior à execução

Esta verificação suplementar reutiliza a fonte positiva `vector_sum.c` e o
candidato efetivamente gerado no arquivo científico do corpus. Não acrescenta
um programa ao denominador de 28 fontes nem observações à campanha de tempo.
Executar depois de encerrar as inferências, sem sobreposição de carga.

O driver `adversarial_sum_driver.c` usa N=1.026, B=0 e A repetindo
`[+1e308, -1e308, -1e308, +1e308]`, seguido dos dois primeiros termos. Todos
os elementos são finitos e a ordem sequencial retorna zero sem overflow.
A partição estática em duas faixas de 513 elementos pode iniciar a segunda
faixa com duas parcelas negativas de grande magnitude. A hipótese é que essa
soma parcial transborde na implementação medida, embora o original permaneça
finito. O comportamento depende da ordem de soma efetiva do compilador/runtime;
não se exige esse desfecho de toda implementação OpenMP.

Compilar a fonte original e o candidato arquivado com o mesmo GCC 13.3.0 e
`-O3`/`-O3 -fopenmp`, por meio de `compile_correctness_gate.py`, threads 1/2.
Preservar logs, códigos de saída, binários, fontes e relatório, inclusive FAIL.
Não alterar a entrada ou repetir para obter o resultado esperado. Se houver
falha numérica no candidato, ela deve impedir admissão nessa entrada.

O driver é uma especificação adicional com resultado zero; não demonstra
estabilidade para outras magnitudes. Os valores dyádicos moderados do corpus
principal não exercitam esse regime adversarial. O contrato AST examina
independência e forma sintática, não garante equivalência IEEE 754 para todas
as ordens de soma. A checagem funcional continua necessária.
