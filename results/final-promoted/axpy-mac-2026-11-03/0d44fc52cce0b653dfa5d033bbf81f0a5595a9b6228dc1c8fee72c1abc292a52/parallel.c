void kernel_axpy(
    int n,
    double alpha,
    const double *X,
    const double *Y,
    double *output
)
{
    /* TCC2 AUTO-GENERATED: DOALL */
    #pragma omp parallel for schedule(static)
    for (int i = 0; i < n; i++)
    {
        output[i] = alpha * X[i] + Y[i];
    }
}
