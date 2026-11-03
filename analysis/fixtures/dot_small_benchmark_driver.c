#include <stdio.h>
#include <time.h>

/* Small inputs expose the cost of starting an OpenMP team. */
#define N 1024
#define INNER_REPEATS 10000

double kernel_dot(int n, const double *A, const double *B);

int main(void)
{
    double A[N], B[N];
    for (int i = 0; i < N; i++) {
        A[i] = (double)(i % 1000) / 1000.0;
        B[i] = (double)((i * 7) % 1000) / 1000.0;
    }
    volatile double result = 0.0;
    struct timespec start, end;
    if (clock_gettime(CLOCK_MONOTONIC, &start) != 0) return 1;
    for (int repeat = 0; repeat < INNER_REPEATS; repeat++)
        result = kernel_dot(N, A, B);
    if (clock_gettime(CLOCK_MONOTONIC, &end) != 0) return 1;
    double elapsed = (double)(end.tv_sec - start.tv_sec)
        + (double)(end.tv_nsec - start.tv_nsec) / 1e9;
    printf("RESULT=%.17g\nTOTAL_SECONDS=%.12f\nAVERAGE_SECONDS=%.12f\n",
           result, elapsed, elapsed / INNER_REPEATS);
    return 0;
}
