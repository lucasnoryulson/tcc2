void kernel_case(int n, const double *restrict A, const double *restrict B, double *restrict Y)
{
    for (int i = 0; i < n; i++)
    {
        if (A[i] < 0.0) break;
        Y[i] = A[i];
    }
}
