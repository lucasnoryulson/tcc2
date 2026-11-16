#include <math.h>
#include <stdio.h>

double kernel_case(int n, const double *A, const double *B);

int main(void)
{
    const int n = 1026;
    double A[1026], B[1026] = {0};
    for (int i = 0; i < n; i++)
    {
        int phase = i % 4;
        A[i] = (phase == 0 || phase == 3) ? 1e308 : -1e308;
    }
    double result = kernel_case(n, A, B);
    printf("%.17g\n", result);
    if (!isfinite(result) || result != 0.0)
    {
        fprintf(stderr, "Expected finite zero for the sequential summation order.\n");
        return 3;
    }
    return 0;
}
