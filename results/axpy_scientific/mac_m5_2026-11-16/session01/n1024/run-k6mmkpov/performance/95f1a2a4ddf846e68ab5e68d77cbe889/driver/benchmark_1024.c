#define _POSIX_C_SOURCE 200809L
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define N 1024
#define INNER_REPEATS 10000
void kernel_axpy(int, double, const double *, const double *, double *);

static double elapsed(struct timespec start, struct timespec end)
{
    return (double)(end.tv_sec - start.tv_sec) + (double)(end.tv_nsec - start.tv_nsec) / 1e9;
}

int main(void)
{
    double *x = malloc((size_t)N * sizeof(*x));
    double *y = malloc((size_t)N * sizeof(*y));
    double *out = malloc((size_t)N * sizeof(*out));
    int status = 0;
    if (!x || !y || !out) { status = 2; goto done; }
    for (int i = 0; i < N; ++i) {
        x[i] = (i % 1000) / 1000.0;
        y[i] = ((i * 7) % 1000) / 1000.0;
        out[i] = NAN;
    }
    struct timespec start, end;
    if (clock_gettime(CLOCK_MONOTONIC, &start)) { status = 2; goto done; }
    for (int repeat = 0; repeat < INNER_REPEATS; ++repeat)
        kernel_axpy(N, 1.75, x, y, out);
    if (clock_gettime(CLOCK_MONOTONIC, &end)) { status = 2; goto done; }
    /* Validate the full timed input outside the timing interval. */
    for (int i = 0; i < N; ++i) {
        double expected = (double)(1.75L * x[i] + y[i]);
        if (!isfinite(out[i]) || fabs(out[i] - expected) > fmax(1e-12, 1e-9 * fabs(expected))) {
            fprintf(stderr, "AXPY benchmark mismatch at %d\n", i);
            status = 3; goto done;
        }
    }
    double total = elapsed(start, end);
    printf("RESULT=%.17g\nTOTAL_SECONDS=%.12f\nAVERAGE_SECONDS=%.12f\n",
           out[N / 2] + out[N - 1], total, total / INNER_REPEATS);
done:
    free(x); free(y); free(out);
    return status;
}
