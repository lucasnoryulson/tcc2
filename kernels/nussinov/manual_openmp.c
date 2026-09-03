/**
 * This version is stamped on May 10, 2016
 *
 * Contact:
 *   Louis-Noel Pouchet <pouchet.ohio-state.edu>
 *   Tomofumi Yuki <tomofumi.yuki.fr>
 *
 * Web address: http://polybench.sourceforge.net
 */

/* nussinov.c: this file is part of PolyBench/C */

#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <math.h>

/* Include polybench common header. */
#include <polybench.h>

/* Include benchmark-specific header. */
#include "nussinov.h"

/* RNA bases represented as chars, range is [0,3] */
typedef char base;

#define match(b1, b2) (((b1) + (b2)) == 3 ? 1 : 0)
#define max_score(s1, s2) ((s1) >= (s2) ? (s1) : (s2))


/* Array initialization. */
static
void init_array(
    int n,
    base POLYBENCH_1D(seq, N, n),
    DATA_TYPE POLYBENCH_2D(table, N, N, n, n))
{
    int i, j;

    /* base is AGCT / 0..3 */
    for (i = 0; i < n; i++) {
        seq[i] = (base)((i + 1) % 4);
    }

    for (i = 0; i < n; i++) {
        for (j = 0; j < n; j++) {
            table[i][j] = 0;
        }
    }
}


/*
 * DCE code.
 * Must scan the entire live-out data.
 * Can also be used to check correctness.
 */
static
void print_array(
    int n,
    DATA_TYPE POLYBENCH_2D(table, N, N, n, n))
{
    int i, j;
    int t = 0;

    POLYBENCH_DUMP_START;
    POLYBENCH_DUMP_BEGIN("table");

    for (i = 0; i < n; i++) {
        for (j = i; j < n; j++) {

            if (t % 20 == 0) {
                fprintf(POLYBENCH_DUMP_TARGET, "\n");
            }

            fprintf(
                POLYBENCH_DUMP_TARGET,
                DATA_PRINTF_MODIFIER,
                table[i][j]
            );

            t++;
        }
    }

    POLYBENCH_DUMP_END("table");
    POLYBENCH_DUMP_FINISH;
}


/*
 * Main computational kernel.
 *
 * Wavefront OpenMP implementation.
 *
 * Instead of traversing i from N-1 to 0 as in the original
 * implementation, the computation is organized by diagonals.
 *
 * d = j - i
 *
 * All dependencies needed to compute table[i][j] belong to
 * previous diagonals, allowing all elements belonging to the
 * same diagonal to be processed in parallel.
 */
static
void kernel_nussinov(
    int n,
    base POLYBENCH_1D(seq, N, n),
    DATA_TYPE POLYBENCH_2D(table, N, N, n, n))
{
    int i, j, k, d;

#pragma scop

#pragma omp parallel private(i, j, k, d)
    {
        /*
         * Each thread walks through the same sequence of
         * wavefronts.
         *
         * The implicit barrier at the end of omp for ensures
         * that diagonal d has been completely calculated
         * before diagonal d + 1 starts.
         */
        for (d = 1; d < _PB_N; d++) {

#pragma omp for schedule(static)
            for (i = 0; i < _PB_N - d; i++) {

                j = i + d;

                /*
                 * Dependency:
                 * table[i][j - 1]
                 *
                 * This belongs to diagonal d - 1.
                 */
                if (j - 1 >= 0) {
                    table[i][j] =
                        max_score(
                            table[i][j],
                            table[i][j - 1]
                        );
                }

                /*
                 * Dependency:
                 * table[i + 1][j]
                 *
                 * This also belongs to diagonal d - 1.
                 */
                if (i + 1 < _PB_N) {
                    table[i][j] =
                        max_score(
                            table[i][j],
                            table[i + 1][j]
                        );
                }

                /*
                 * Dependency:
                 * table[i + 1][j - 1]
                 *
                 * This belongs to diagonal d - 2.
                 */
                if (j - 1 >= 0 && i + 1 < _PB_N) {

                    /*
                     * Do not allow adjacent elements to bond.
                     */
                    if (i < j - 1) {

                        table[i][j] =
                            max_score(
                                table[i][j],
                                table[i + 1][j - 1]
                                    + match(seq[i], seq[j])
                            );

                    } else {

                        table[i][j] =
                            max_score(
                                table[i][j],
                                table[i + 1][j - 1]
                            );
                    }
                }

                /*
                 * Split the interval.
                 *
                 * Both table[i][k] and table[k + 1][j]
                 * belong to smaller diagonals and have
                 * therefore already been computed.
                 */
                for (k = i + 1; k < j; k++) {

                    table[i][j] =
                        max_score(
                            table[i][j],
                            table[i][k]
                                + table[k + 1][j]
                        );
                }
            }

            /*
             * IMPORTANT:
             *
             * There is an implicit OpenMP barrier here.
             *
             * Do NOT add "nowait" to the omp for.
             *
             * All cells of diagonal d must be finished
             * before diagonal d + 1 starts.
             */
        }
    }

#pragma endscop
}


int main(int argc, char **argv)
{
    /* Retrieve problem size. */
    int n = N;

    /* Variable declaration/allocation. */
    POLYBENCH_1D_ARRAY_DECL(
        seq,
        base,
        N,
        n
    );

    POLYBENCH_2D_ARRAY_DECL(
        table,
        DATA_TYPE,
        N,
        N,
        n,
        n
    );

    /* Initialize array(s). */
    init_array(
        n,
        POLYBENCH_ARRAY(seq),
        POLYBENCH_ARRAY(table)
    );

    /* Start timer. */
    polybench_start_instruments;

    /* Run kernel. */
    kernel_nussinov(
        n,
        POLYBENCH_ARRAY(seq),
        POLYBENCH_ARRAY(table)
    );

    /* Stop and print timer. */
    polybench_stop_instruments;
    polybench_print_instruments;

    /*
     * Prevent dead-code elimination.
     * All live-out data must be printed.
     */
    polybench_prevent_dce(
        print_array(
            n,
            POLYBENCH_ARRAY(table)
        )
    );

    /* Be clean. */
    POLYBENCH_FREE_ARRAY(seq);
    POLYBENCH_FREE_ARRAY(table);

    return 0;
}