double global_state = 0.0;
void kernel_case(int n, const double *restrict A, const double *restrict B, double *restrict Y)
{
    for (int i = 0; i < n; i++)
    {
        Y[i] = (global_state += A[i]);
    }
}
