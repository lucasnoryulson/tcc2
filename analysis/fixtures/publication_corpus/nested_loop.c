void kernel_case(int n, const double *restrict A, const double *restrict B, double *restrict Y)
{
    for (int i = 0; i < n; i++)
    {
        for (int j = 0; j < 2; j++) Y[i] += A[i];
    }
}
