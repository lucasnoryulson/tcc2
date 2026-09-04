double kernel_dot(
    int n,
    const double *A,
    const double *B
)
{
    double sum = 0.0;

    /* TCC2 AUTO-GENERATED: REDUCTION */
    #pragma omp parallel for reduction(+:sum) schedule(static)
    for (int i = 0; i < n; i++)
    {
        sum += A[i] * B[i];
    }

    return sum;
}
