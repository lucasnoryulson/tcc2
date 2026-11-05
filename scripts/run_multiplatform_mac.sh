#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$#" -lt 1 ]; then
  echo 'Uso: bash scripts/run_multiplatform_mac.sh <diretorio-novo> [opcoes]' >&2
  exit 2
fi
output=$1
shift
export PATH="/opt/homebrew/opt/llvm/bin:$PATH"
exec python3 -B scripts/benchmark_multiplatform.py --output "$output" \
  --cc /opt/homebrew/opt/llvm/bin/clang --cxx /opt/homebrew/opt/llvm/bin/clang++ \
  --threads 1 2 4 6 8 10 "$@"
