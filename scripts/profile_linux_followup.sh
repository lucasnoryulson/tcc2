#!/usr/bin/env bash
# Collect counters into a NEW archive; existing Linux benchmark archives are read-only.
set -uo pipefail
if [ "$#" -ne 2 ] || [ "$(uname -s)" != Linux ]; then
  echo 'Uso no Linux: bash scripts/profile_linux_followup.sh <campanha-completa> <diretorio-novo>' >&2
  exit 2
fi
campaign=$1
output=$2
if [ -e "$output" ] || [ ! -f "$campaign/report.json" ]; then
  echo 'Exige campanha existente e diretório de saída novo.' >&2
  exit 2
fi
mkdir -p "$output"
perf --version > "$output/perf-version.txt" 2>&1
perf list > "$output/perf-list.txt" 2>&1
lscpu > "$output/lscpu.txt" 2>&1
uname -a > "$output/uname.txt" 2>&1
printf 'case,threads,status\n' > "$output/status.csv"
for name in dot-auto-10000000-automatic gemm-LARGE-manual nussinov-LARGE-manual jacobi-2d-LARGE-manual covariance-LARGE-manual; do
  binary="$campaign/bin/$name"
  if [ ! -x "$binary" ]; then
    printf '%s,0,MISSING_BINARY\n' "$name" >> "$output/status.csv"
    continue
  fi
  for threads in 1 2 4; do
    command=(env OMP_DYNAMIC=FALSE OMP_PROC_BIND=TRUE OMP_PLACES=cores OMP_NUM_THREADS="$threads"
      perf stat --no-big-num -x, -r 5
      -e cycles,instructions,cache-references,cache-misses,context-switches,cpu-migrations
      -o "$output/$name-${threads}T-perf.csv" -- "$binary")
    printf '%q ' "${command[@]}" >> "$output/commands.txt"
    printf '\n' >> "$output/commands.txt"
    if "${command[@]}" > "$output/$name-${threads}T.stdout" 2> "$output/$name-${threads}T.stderr"; then
      status=0
    else
      status=$?
    fi
    printf '%s,%s,%s\n' "$name" "$threads" "$status" >> "$output/status.csv"
  done
done
# Generic cache events do not establish DRAM bandwidth. Choose supported memory
# controller events from perf-list.txt before a separately declared uncore run.
