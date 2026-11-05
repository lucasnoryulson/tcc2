#include <omp.h>
#include <stdio.h>
int main(void) {
#pragma omp parallel
{
#pragma omp single
printf("%d\n", omp_get_num_threads());
}
}
