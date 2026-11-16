#include <math.h>
#include <stdio.h>
#include <stdlib.h>

void kernel_axpy(int, double, const double *, const double *, double *);

static int verify(int n, double alpha)
{
    double *x = malloc((size_t)n * sizeof(*x));
    double *y = malloc((size_t)n * sizeof(*y));
    double *out = malloc((size_t)n * sizeof(*out));
    int status = 0;
    if (!x || !y || !out) { status = 2; goto done; }
    for (int i = 0; i < n; ++i) {
        x[i] = ((i % 1000) - 500) / 1000.0;
        y[i] = (((i * 7) % 1000) - 500) / 1000.0;
        out[i] = NAN;
    }
    kernel_axpy(n, alpha, x, y, out);
    for (int i = 0; i < n; ++i) {
        double expected = (double)((long double)alpha * x[i] + y[i]);
        if (!isfinite(out[i]) || fabs(out[i] - expected) > fmax(1e-12, 1e-9 * fabs(expected))) {
            fprintf(stderr, "AXPY mismatch: n=%d index=%d expected=%.17g actual=%.17g\n", n, i, expected, out[i]);
            status = 3; break;
        }
    }
done:
    free(x); free(y); free(out);
    return status;
}

int main(void)
{
    const int sizes[] = {1024, 1000000, 10000000};
    for (int i = 0; i < 3; ++i) {
        int status = verify(sizes[i], 1.75);
        if (status) return status;
    }
    if (verify(1024, -2.0) || verify(1024, 0.0)) return 3;
    /* The scalar gate sees success only after all elements passed the oracle. */
    puts("0");
    return 0;
}
