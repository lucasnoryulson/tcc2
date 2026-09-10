void kernel_wavefront(
    int N,
    double A[N][N]
)
{
    for (int i = 1; i < N; ++i) {

        for (int j = 1; j < N; ++j) {

            A[i][j] =
                0.5 * (
                    A[i - 1][j]
                    +
                    A[i][j - 1]
                );
        }
    }
}
