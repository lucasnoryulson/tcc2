#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$#" -lt 1 ]; then
  echo 'Uso: bash scripts/run_multiplatform_linux.sh <diretorio-novo> [opcoes]' >&2
  exit 2
fi
output=$1
shift
exec python3 -B scripts/benchmark_multiplatform.py --output "$output" --cc clang --cxx clang++ --threads 1 2 4 "$@"
