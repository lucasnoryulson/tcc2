/* The caller must supply valid, non-overlapping buffers under C restrict. */
void kernel_axpy(int n, double alpha, const double *restrict X,
                 const double *restrict Y, double *restrict output)
{
    /* TCC2 AUTO-GENERATED: DOALL */
    #pragma omp parallel for schedule(static)
    for (int i = 0; i < n; i++)
    {
        output[i] = alpha * X[i] + Y[i];
    }
}
