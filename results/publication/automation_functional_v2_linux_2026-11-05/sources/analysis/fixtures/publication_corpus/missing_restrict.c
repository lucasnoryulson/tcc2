void kernel_case(int n, const double *A, const double *B, double *Y)
{
    for (int i = 0; i < n; i++)
    {
        Y[i] = A[i] + B[i];
    }
}
