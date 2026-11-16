#include <stdio.h>
#include <stdlib.h>
#include <time.h>


#define N 10000000
#define INNER_REPEATS 100


double kernel_dot(
    int n,
    const double *A,
    const double *B
);


static double elapsed_seconds(
    struct timespec start,
    struct timespec end
)
{
    double seconds =
        (double)(end.tv_sec - start.tv_sec);

    double nanoseconds =
        (double)(end.tv_nsec - start.tv_nsec)
        / 1000000000.0;

    return seconds + nanoseconds;
}


int main(void)
{
    double *A = malloc(
        (size_t)N * sizeof(double)
    );

    double *B = malloc(
        (size_t)N * sizeof(double)
    );

    if (A == NULL || B == NULL)
    {
        fprintf(
            stderr,
            "Memory allocation failed\n"
        );

        free(A);
        free(B);

        return 1;
    }

    for (int i = 0; i < N; i++)
    {
        A[i] = (
            (double)(i % 1000)
            / 1000.0
        );

        B[i] = (
            (double)((i * 7) % 1000)
            / 1000.0
        );
    }

    volatile double result = 0.0;

    struct timespec start;
    struct timespec end;

    clock_gettime(
        CLOCK_MONOTONIC,
        &start
    );

    for (
        int repeat = 0;
        repeat < INNER_REPEATS;
        repeat++
    )
    {
        result = kernel_dot(
            N,
            A,
            B
        );
    }

    clock_gettime(
        CLOCK_MONOTONIC,
        &end
    );

    double total_time =
        elapsed_seconds(
            start,
            end
        );

    double average_time =
        total_time
        / INNER_REPEATS;

    printf(
        "RESULT=%.17g\n",
        result
    );

    printf(
        "TOTAL_SECONDS=%.12f\n",
        total_time
    );

    printf(
        "AVERAGE_SECONDS=%.12f\n",
        average_time
    );

    free(A);
    free(B);

    return 0;
}
