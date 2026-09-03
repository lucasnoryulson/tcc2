#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <vector>

int main(int argc, char** argv)
{
    int N = 4000;

    if (argc > 1) {
        N = std::stoi(argv[1]);
    }

    std::vector<double> A(
        static_cast<size_t>(N) * N,
        0.0
    );

    // Inicializa primeira linha.
    // Primeira linha com valores diferentes.
    for (int j = 0; j < N; ++j) {
        A[j] =
            1.0 +
            0.001 * static_cast<double>(j);
    }

    // Primeira coluna com valores diferentes.
    for (int i = 0; i < N; ++i) {
        A[
            static_cast<size_t>(i) * N
        ] =
            1.0 +
            0.002 * static_cast<double>(i);
    }

    auto start =
        std::chrono::high_resolution_clock::now();

    for (int i = 1; i < N; ++i) {

        for (int j = 1; j < N; ++j) {

            A[
                static_cast<size_t>(i) * N + j
            ] =
                0.5 * (
                    A[
                        static_cast<size_t>(i - 1)
                        * N + j
                    ]
                    +
                    A[
                        static_cast<size_t>(i)
                        * N + j - 1
                    ]
                );
        }
    }

    auto stop =
        std::chrono::high_resolution_clock::now();

    double elapsed_ms =
        std::chrono::duration<
            double,
            std::milli
        >(stop - start).count();

    // Algumas posições são usadas como checksum.
    double checksum = 0.0;

    checksum +=
        A[
            static_cast<size_t>(N - 1)
            * N + (N - 1)
        ];

    checksum +=
        A[
            static_cast<size_t>(N / 2)
            * N + (N / 2)
        ];

    checksum +=
        A[
            static_cast<size_t>(N - 1)
            * N + (N / 2)
        ];

    checksum +=
        A[
            static_cast<size_t>(N / 2)
            * N + (N - 1)
        ];

    std::cout << std::setprecision(17);

    std::cout
        << "result="
        << checksum
        << "\n";

    std::cout
        << "run_ms="
        << elapsed_ms
        << "\n";

    return 0;
}
