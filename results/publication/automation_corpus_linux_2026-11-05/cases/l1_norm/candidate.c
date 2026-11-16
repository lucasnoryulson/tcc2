double kernel_case(int n, const double *A, const double *B)
{
    double sum = 0.0;
    /* TCC2 AUTO-GENERATED: REDUCTION */
    #pragma omp parallel for reduction(+:sum) schedule(static)
    for (int i = 0; i < n; i++)
    {
        sum += A[i] < 0.0 ? -A[i] : A[i];
    }
    return sum;
}
