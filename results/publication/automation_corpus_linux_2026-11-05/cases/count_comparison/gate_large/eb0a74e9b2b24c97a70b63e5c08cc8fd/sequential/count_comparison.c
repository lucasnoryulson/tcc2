double kernel_case(int n, const double *A, const double *B)
{
    double sum = 0.0;
    for (int i = 0; i < n; i++)
    {
        sum += A[i] > B[i] ? 1.0 : 0.0;
    }
    return sum;
}
