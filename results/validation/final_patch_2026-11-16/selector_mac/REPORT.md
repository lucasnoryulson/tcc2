# Avaliação independente do Selector

As decisões foram congeladas antes do início da segunda sessão. Cada política usa as novas quinze observações da configuração escolhida. O comparador descritivo é a menor mediana da segunda sessão, incluindo sequencial.

| Caso / entrada / variante | Política | Configuração | Ganho total | Arrependimento (%) | Inadequada (>2%) |
|---|---|---|---:|---:|---|
| covariance / LARGE / manual | sequential | seq. | 1.0000 | 322.654 | True |
| covariance / LARGE / manual | max_threads | 10T | 4.2265 | 0.000 | False |
| covariance / LARGE / manual | selector | 10T | 4.2265 | 0.000 | False |
| covariance / LARGE / manual | fastest_selection | 10T | 4.2265 | 0.000 | False |
| covariance / MEDIUM / manual | sequential | seq. | 1.0000 | 296.631 | True |
| covariance / MEDIUM / manual | max_threads | 10T | 3.9663 | 0.000 | False |
| covariance / MEDIUM / manual | selector | 10T | 3.9663 | 0.000 | False |
| covariance / MEDIUM / manual | fastest_selection | 10T | 3.9663 | 0.000 | False |
| dot / 1000000 / manual | sequential | seq. | 1.0000 | 8.085 | True |
| dot / 1000000 / manual | max_threads | 10T | 0.9628 | 12.265 | True |
| dot / 1000000 / manual | selector | 4T | 1.0809 | 0.000 | False |
| dot / 1000000 / manual | fastest_selection | 4T | 1.0809 | 0.000 | False |
| dot / 10000000 / manual | sequential | seq. | 1.0000 | 178.551 | True |
| dot / 10000000 / manual | max_threads | 10T | 2.7855 | 0.000 | False |
| dot / 10000000 / manual | selector | 10T | 2.7855 | 0.000 | False |
| dot / 10000000 / manual | fastest_selection | 10T | 2.7855 | 0.000 | False |
| dot-auto / 1024 / automatic | sequential | seq. | 1.0000 | 0.000 | False |
| dot-auto / 1024 / automatic | max_threads | 10T | 0.0078 | 12767.655 | True |
| dot-auto / 1024 / automatic | selector | seq. | 1.0000 | 0.000 | False |
| dot-auto / 1024 / automatic | fastest_selection | 1T | 0.7645 | 30.796 | True |
| dot-auto / 10000000 / automatic | sequential | seq. | 1.0000 | 294.248 | True |
| dot-auto / 10000000 / automatic | max_threads | 10T | 3.9425 | 0.000 | False |
| dot-auto / 10000000 / automatic | selector | 10T | 3.9425 | 0.000 | False |
| dot-auto / 10000000 / automatic | fastest_selection | 10T | 3.9425 | 0.000 | False |
| gemm / LARGE / manual | sequential | seq. | 1.0000 | 390.737 | True |
| gemm / LARGE / manual | max_threads | 10T | 4.9074 | 0.000 | False |
| gemm / LARGE / manual | selector | 10T | 4.9074 | 0.000 | False |
| gemm / LARGE / manual | fastest_selection | 10T | 4.9074 | 0.000 | False |
| gemm / MEDIUM / manual | sequential | seq. | 1.0000 | 325.442 | True |
| gemm / MEDIUM / manual | max_threads | 10T | 4.2098 | 1.060 | False |
| gemm / MEDIUM / manual | selector | 8T | 4.2544 | 0.000 | False |
| gemm / MEDIUM / manual | fastest_selection | 8T | 4.2544 | 0.000 | False |
| jacobi-2d / LARGE / manual | sequential | seq. | 1.0000 | 151.064 | True |
| jacobi-2d / LARGE / manual | max_threads | 10T | 2.5106 | 0.000 | False |
| jacobi-2d / LARGE / manual | selector | 10T | 2.5106 | 0.000 | False |
| jacobi-2d / LARGE / manual | fastest_selection | 10T | 2.5106 | 0.000 | False |
| jacobi-2d / MEDIUM / manual | sequential | seq. | 1.0000 | 12.865 | True |
| jacobi-2d / MEDIUM / manual | max_threads | 10T | 0.4438 | 154.344 | True |
| jacobi-2d / MEDIUM / manual | selector | 4T | 1.1287 | 0.000 | False |
| jacobi-2d / MEDIUM / manual | fastest_selection | 4T | 1.1287 | 0.000 | False |
| nussinov / LARGE / manual | sequential | seq. | 1.0000 | 166.800 | True |
| nussinov / LARGE / manual | max_threads | 10T | 2.2945 | 16.280 | True |
| nussinov / LARGE / manual | selector | 4T | 2.6680 | 0.000 | False |
| nussinov / LARGE / manual | fastest_selection | 4T | 2.6680 | 0.000 | False |
| nussinov / LARGE / simd_auto | sequential | seq. | 1.0000 | 276.974 | True |
| nussinov / LARGE / simd_auto | max_threads | 10T | 3.2724 | 15.199 | True |
| nussinov / LARGE / simd_auto | selector | 4T | 3.7697 | 0.000 | False |
| nussinov / LARGE / simd_auto | fastest_selection | 4T | 3.7697 | 0.000 | False |
| nussinov / LARGE / simd_manual | sequential | seq. | 1.0000 | 276.755 | True |
| nussinov / LARGE / simd_manual | max_threads | 10T | 3.2710 | 15.181 | True |
| nussinov / LARGE / simd_manual | selector | 4T | 3.7676 | 0.000 | False |
| nussinov / LARGE / simd_manual | fastest_selection | 4T | 3.7676 | 0.000 | False |
| nussinov / MEDIUM / manual | sequential | seq. | 1.0000 | 0.000 | False |
| nussinov / MEDIUM / manual | max_threads | 10T | 0.3923 | 154.876 | True |
| nussinov / MEDIUM / manual | selector | 4T | 0.8947 | 11.769 | True |
| nussinov / MEDIUM / manual | fastest_selection | 4T | 0.8947 | 11.769 | True |
| nussinov / MEDIUM / simd_auto | sequential | seq. | 1.0000 | 24.105 | True |
| nussinov / MEDIUM / simd_auto | max_threads | 10T | 0.4060 | 205.655 | True |
| nussinov / MEDIUM / simd_auto | selector | 1T | 1.2410 | 0.000 | False |
| nussinov / MEDIUM / simd_auto | fastest_selection | 1T | 1.2410 | 0.000 | False |
| nussinov / MEDIUM / simd_manual | sequential | seq. | 1.0000 | 24.434 | True |
| nussinov / MEDIUM / simd_manual | max_threads | 10T | 0.4035 | 208.423 | True |
| nussinov / MEDIUM / simd_manual | selector | 1T | 1.2443 | 0.000 | False |
| nussinov / MEDIUM / simd_manual | fastest_selection | 1T | 1.2443 | 0.000 | False |

Recomendação estável em 14/16 casos. Frequências descritivas por política: `{"sequential": {"cases": 16, "inadequate": 14, "inadequate_rate": 0.875, "slower_than_sequential": 0, "mean_regret_percent": 171.83414550651543, "maximum_regret_percent": 390.7372400756144}, "max_threads": {"cases": 16, "inadequate": 9, "inadequate_rate": 0.5625, "slower_than_sequential": 6, "mean_regret_percent": 846.9337373566092, "maximum_regret_percent": 12767.654867256639}, "selector": {"cases": 16, "inadequate": 1, "inadequate_rate": 0.0625, "slower_than_sequential": 1, "mean_regret_percent": 0.7355351581707927, "maximum_regret_percent": 11.768562530732684}, "fastest_selection": {"cases": 16, "inadequate": 2, "inadequate_rate": 0.125, "slower_than_sequential": 2, "mean_regret_percent": 2.66031391923274, "maximum_regret_percent": 30.796460176991157}}`.

A sensibilidade aplica o Selector real com limiares de 0%, 1%, 2% e 5% somente à primeira sessão. O código de produção conserva 2%. Não há agrupamento de sessões ou teste de significância baseado no limiar operacional.
