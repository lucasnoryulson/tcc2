#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define N 10000000
#define INNER_REPEATS 40

void kernel_axpy(int n, double alpha, const double *X, const double *Y, double *output);

static double elapsed_seconds(struct timespec start, struct timespec end)
{
    return (double)(end.tv_sec - start.tv_sec)
        + (double)(end.tv_nsec - start.tv_nsec) / 1000000000.0;
}

int main(void)
{
    double *X = malloc((size_t)N * sizeof(double));
    double *Y = malloc((size_t)N * sizeof(double));
    double *output = malloc((size_t)N * sizeof(double));
    if (X == NULL || Y == NULL || output == NULL)
    {
        free(X); free(Y); free(output);
        return 1;
    }
    for (int i = 0; i < N; i++)
    {
        X[i] = (double)(i % 1000) / 1000.0;
        Y[i] = (double)((i * 7) % 1000) / 1000.0;
    }
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    for (int repeat = 0; repeat < INNER_REPEATS; repeat++)
        kernel_axpy(N, 1.75, X, Y, output);
    clock_gettime(CLOCK_MONOTONIC, &end);
    volatile double result = output[N / 2] + output[N - 1];
    double total = elapsed_seconds(start, end);
    printf("RESULT=%.17g\n", result);
    printf("TOTAL_SECONDS=%.12f\n", total);
    printf("AVERAGE_SECONDS=%.12f\n", total / INNER_REPEATS);
    free(X); free(Y); free(output);
    return 0;
}
