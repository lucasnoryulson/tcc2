#define _POSIX_C_SOURCE 200809L
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
void kernel_case(int, const double *restrict, const double *restrict, double *restrict);
static double input_a(int i) { return ((i % 23) - 11) / 16.0; }
static double input_b(int i) { return (((i * 7) % 19) - 9) / 32.0; }
static double expected_value(int i) {
    double a = input_a(i), b = input_b(i);
    return a * b;
}
static double seconds(struct timespec t) { return t.tv_sec + t.tv_nsec * 1e-9; }
int main(void) {
    const int n = 1024, repeats = 1;
    double *A = malloc((size_t)(n + 2) * sizeof(double));
    double *B = malloc((size_t)(n + 2) * sizeof(double));
    double *Y = malloc((size_t)(n + 2) * sizeof(double));
    if (!A || !B || !Y) { free(A); free(B); free(Y); return 2; }
    for (int i = 0; i < n + 2; i++) { A[i] = input_a(i); B[i] = input_b(i); Y[i] = NAN; }
    double result = 0.0;
    struct timespec begin, end;
    if (clock_gettime(CLOCK_MONOTONIC, &begin)) return 4;
    for (int repetition = 0; repetition < repeats; repetition++) { kernel_case(n, A, B, Y); }
    if (clock_gettime(CLOCK_MONOTONIC, &end)) return 4;
    
    long double total = 0.0L;
    for (int i = 0; i < n; i++) {
        double expected = expected_value(i);
        if (!isfinite(Y[i]) || fabs(Y[i] - expected) > 1e-12 + 1e-9 * fabs(expected)) return 3;
        total += Y[i];
    }
    result = (double)total;
    
    printf("%.17g\nAVERAGE_SECONDS=%.17g\n", result, (seconds(end) - seconds(begin)) / repeats);
    free(A); free(B); free(Y);
    return 0;
}
