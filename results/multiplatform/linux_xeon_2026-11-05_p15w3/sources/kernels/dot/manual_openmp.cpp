#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <vector>

#include <omp.h>

#if defined(__GNUC__) || defined(__clang__)
__attribute__((noinline))
#endif
double dot_product(
    const double* A,
    const double* B,
    long N
) {
    double sum = 0.0;

#pragma omp parallel for reduction(+ : sum) schedule(static)
    for (long i = 0; i < N; ++i) {
        sum += A[i] * B[i];
    }

    return sum;
}

int main(int argc, char** argv) {

    long N = 10000000;

    if (argc > 1) {
        N = std::stol(argv[1]);
    }

    std::vector<double> A(N);
    std::vector<double> B(N);

    const double a =
        1.0 * 1024.0 /
        static_cast<double>(N);

    const double b =
        2.0 * 1024.0 /
        static_cast<double>(N);

    for (long i = 0; i < N; ++i) {
        A[i] = a;
        B[i] = b;
    }

    auto start =
        std::chrono::high_resolution_clock::now();

    double result = dot_product(
        A.data(),
        B.data(),
        N
    );

    auto stop =
        std::chrono::high_resolution_clock::now();

    double elapsed_ms =
        std::chrono::duration<
            double,
            std::milli
        >(stop - start).count();

    const double expected =
        a * b *
        static_cast<double>(N);

    const double difference =
        std::abs(result - expected);

    std::cout << std::setprecision(17);

    std::cout
        << "threads="
        << omp_get_max_threads()
        << "\n";

    std::cout
        << "result="
        << result
        << "\n";

    std::cout
        << "expected="
        << expected
        << "\n";

    std::cout
        << "difference="
        << difference
        << "\n";

    std::cout
        << "run_ms="
        << elapsed_ms
        << "\n";

    return 0;
}