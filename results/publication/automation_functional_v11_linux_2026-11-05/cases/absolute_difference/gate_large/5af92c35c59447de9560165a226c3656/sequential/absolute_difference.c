void kernel_case(int n, const double *restrict A, const double *restrict B, double *restrict Y)
{
    for (int i = 0; i < n; i++)
    {
        Y[i] = A[i] > B[i] ? A[i] - B[i] : B[i] - A[i];
    }
}
