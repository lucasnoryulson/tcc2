void kernel_case(int n, const double *restrict A, const double *restrict B, double *restrict Y)
{
    for (int i = 1; i < n; i++)
    {
        Y[i] = Y[i - 1] + A[i];
    }
}
