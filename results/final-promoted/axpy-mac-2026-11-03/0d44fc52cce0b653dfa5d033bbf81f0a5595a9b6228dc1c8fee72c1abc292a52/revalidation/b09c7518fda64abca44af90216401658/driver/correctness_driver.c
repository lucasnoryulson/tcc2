#include <stdio.h>
#include <stdlib.h>

void kernel_axpy(int n, double alpha, const double *X, const double *Y, double *output);

int main(void)
{
    const int n = 1000000;
    double *X = malloc((size_t)n * sizeof(double));
    double *Y = malloc((size_t)n * sizeof(double));
    double *output = malloc((size_t)n * sizeof(double));
    if (X == NULL || Y == NULL || output == NULL)
    {
        free(X); free(Y); free(output);
        return 1;
    }
    for (int i = 0; i < n; i++)
    {
        X[i] = (double)(i % 1000) / 1000.0;
        Y[i] = (double)((i * 7) % 1000) / 1000.0;
    }
    kernel_axpy(n, 1.75, X, Y, output);
    double checksum = 0.0;
    for (int i = 0; i < n; i++)
        checksum += output[i] * (double)((i % 13) + 1);
    printf("%.17g\n", checksum);
    free(X); free(Y); free(output);
    return 0;
}
