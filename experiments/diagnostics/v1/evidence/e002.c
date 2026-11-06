double kernel_dot(
    int n,
    const double *A,
    const double *B
)
{
    double sum = 0.0;

    for (int i = 0; i < n; i++)
    {
        sum += A[i] * B[i];
    }

    return sum;
}
