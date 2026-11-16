void kernel_case(int n, const double *restrict A, const double *restrict B, double *restrict Y)
{
    for (int i = 0; i < n; i++)
    {
        Y[i] = 1.0 / (1.0 + A[i] * A[i]);
    }
}
