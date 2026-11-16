void kernel_axpy(
    int n,
    double alpha,
    const double *X,
    const double *Y,
    double *output
)
{
    for (int i = 0; i < n; i++)
    {
        output[i] = alpha * X[i] + Y[i];
    }
}
