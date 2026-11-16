double kernel_case(int n, double *A, const double *B)
{
    double sum = 0.0;
    for (int i = 0; i < n; i++)
    {
        sum += A[i];
        A[i] = sum;
    }
    return sum;
}
