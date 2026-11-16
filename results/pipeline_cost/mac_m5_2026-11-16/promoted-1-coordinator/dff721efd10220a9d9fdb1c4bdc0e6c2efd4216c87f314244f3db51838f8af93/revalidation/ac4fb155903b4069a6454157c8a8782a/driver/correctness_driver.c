#include <stdio.h>
#include <stdlib.h>


double kernel_dot(
    int n,
    const double *A,
    const double *B
);


int main(void)
{
    const int n = 1000000;

    double *A = malloc(
        (size_t)n * sizeof(double)
    );

    double *B = malloc(
        (size_t)n * sizeof(double)
    );

    if (A == NULL || B == NULL)
    {
        fprintf(
            stderr,
            "Memory allocation failed\n"
        );

        free(A);
        free(B);

        return 1;
    }

    /*
     * Deterministic input.
     *
     * Values are intentionally simple so that the
     * sequential and OpenMP versions receive exactly
     * the same data.
     */
    for (int i = 0; i < n; i++)
    {
        A[i] = (
            (double)(i % 1000)
            / 1000.0
        );

        B[i] = (
            (double)((i * 7) % 1000)
            / 1000.0
        );
    }

    double result = kernel_dot(
        n,
        A,
        B
    );

    /*
     * Print enough precision for numeric validation.
     */
    printf(
        "%.17g\n",
        result
    );

    free(A);
    free(B);

    return 0;
}
