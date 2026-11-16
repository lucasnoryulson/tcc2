void kernel_case(int n, const double *restrict A, const double *restrict B, double *restrict Y)
{
    for (int i = 0; i < n; i++)
    {
        Y[i] = 2.0 * A[i] + B[i];
    }
}
