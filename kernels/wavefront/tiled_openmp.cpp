#include <algorithm>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <vector>

#include <omp.h>


int main(int argc, char** argv)
{
    int N = 4000;
    int BLOCK_SIZE = 64;

    if (argc > 1) {
        N = std::stoi(argv[1]);
    }

    if (argc > 2) {
        BLOCK_SIZE = std::stoi(argv[2]);
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


    /*
     * A região realmente calculada vai
     * de 1 até N-1 em ambas dimensões.
     */
    int interior_size = N - 1;

    int num_tiles =
        (
            interior_size
            + BLOCK_SIZE
            - 1
        )
        / BLOCK_SIZE;


    auto start =
        std::chrono::high_resolution_clock::now();


#pragma omp parallel
    {

        /*
         * Agora a onda ocorre entre TILES,
         * e não entre células individuais.
         *
         * Todos os tiles da mesma
         * anti-diagonal podem executar
         * simultaneamente.
         */
        for (
            int tile_diag = 0;
            tile_diag <= 2 * (num_tiles - 1);
            ++tile_diag
        ) {

            int tile_row_start =
                std::max(
                    0,
                    tile_diag - (num_tiles - 1)
                );

            int tile_row_end =
                std::min(
                    num_tiles - 1,
                    tile_diag
                );


#pragma omp for schedule(static)
            for (
                int tile_row = tile_row_start;
                tile_row <= tile_row_end;
                ++tile_row
            ) {

                int tile_col =
                    tile_diag - tile_row;


                int i_start =
                    1
                    + tile_row
                    * BLOCK_SIZE;

                int j_start =
                    1
                    + tile_col
                    * BLOCK_SIZE;


                int i_end =
                    std::min(
                        N,
                        i_start + BLOCK_SIZE
                    );

                int j_end =
                    std::min(
                        N,
                        j_start + BLOCK_SIZE
                    );


                /*
                 * Dentro do tile mantemos
                 * a ordem sequencial.
                 *
                 * Assim preservamos as
                 * dependências:
                 *
                 * A[i-1][j]
                 * A[i][j-1]
                 */
                for (
                    int i = i_start;
                    i < i_end;
                    ++i
                ) {

                    for (
                        int j = j_start;
                        j < j_end;
                        ++j
                    ) {

                        A[
                            static_cast<size_t>(i)
                            * N + j
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
            }

            /*
             * Barreira implícita.
             *
             * Todos os tiles da diagonal
             * atual terminam antes da
             * próxima diagonal.
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
        << "block_size="
        << BLOCK_SIZE
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
