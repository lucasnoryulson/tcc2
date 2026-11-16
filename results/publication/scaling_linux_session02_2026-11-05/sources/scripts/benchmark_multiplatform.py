"""Execute the requested three-warmup, fifteen-sample protocol using the archive collector."""
from benchmark_scaling import main


if __name__ == '__main__':
    main(dict(repetitions=15, warmups=3,
              kernels=['dot-auto', 'dot', 'gemm', 'nussinov', 'jacobi-2d', 'covariance']))
