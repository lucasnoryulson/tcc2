#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <vector>

#include <omp.h>


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


    // Primeira linha.
    for (int j = 0; j < N; ++j) {

        A[j] =
            1.0 +
            0.001 * static_cast<double>(j);
    }


    // Primeira coluna.
    for (int i = 0; i < N; ++i) {

        A[
            static_cast<size_t>(i) * N
        ] =
            1.0 +
            0.002 * static_cast<double>(i);
    }


    auto start =
        std::chrono::high_resolution_clock::now();


#pragma omp parallel
    {

        /*
         * d representa uma anti-diagonal.
         *
         * Para cada célula:
         *
         *     d = i + j
         *
         * A célula A[i][j] depende apenas
         * da diagonal anterior.
         */

        for (
            int d = 2;
            d <= 2 * (N - 1);
            ++d
        ) {

            int i_start =
                std::max(
                    1,
                    d - (N - 1)
                );

            int i_end =
                std::min(
                    N - 1,
                    d - 1
                );


#pragma omp for schedule(static)
            for (
                int i = i_start;
                i <= i_end;
                ++i
            ) {

                int j = d - i;

                A[
                    static_cast<size_t>(i) * N
                    + j
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

            /*
             * omp for possui uma barreira
             * implícita aqui.
             *
             * Portanto, toda a diagonal d
             * termina antes de d+1 começar.
             */
        }
    }


    auto stop =
        std::chrono::high_resolution_clock::now();


    double elapsed_ms =
        std::chrono::duration<
            double,
            std::milli
        >(stop - start).count();


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


    std::cout
        << std::setprecision(17);


    std::cout
        << "threads="
        << omp_get_max_threads()
        << "\n";


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
