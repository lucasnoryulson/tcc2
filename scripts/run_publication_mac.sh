#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$#" -lt 1 ] || [ "$#" -gt 3 ]; then
  echo 'Uso: bash scripts/run_publication_mac.sh <diretorio-novo> [gcc-real-ou-llvm] [modelo-ollama]' >&2
  exit 2
fi
output=$1
compiler=${2:-/opt/homebrew/opt/llvm/bin/clang}
model=${3:-qwen2.5:3b}
if [ -e "$output" ]; then
  echo 'O diretório precisa ser novo; evidências existentes são preservadas.' >&2
  exit 2
fi
export PATH="/opt/homebrew/opt/llvm/bin:$PATH"
compiler_version=$("$compiler" --version)
baseline=()
case "$compiler_version" in
  *gcc*|*GCC*) baseline=(--gcc-baseline "$compiler") ;;
esac
ollama show "$model" > /dev/null
mkdir -p "$output"
for session in 01 02; do
  bash scripts/run_multiplatform_mac.sh "$output/scaling-session$session"
done
bash scripts/run_multiplatform_mac.sh "$output/scaling-session03-medium" --datasets MEDIUM
python3 -B scripts/evaluate_automation_corpus.py --compiler "$compiler" "${baseline[@]}" \
  --threads 1 2 4 6 8 10 --measure --samples 15 --warmups 3 --seed 2026 \
  --output "$output/automation-corpus"
python3 -B scripts/evaluate_automation_corpus.py --verify --output "$output/automation-corpus"
# Run inference only after all timed kernel collections have finished.
python3 -B scripts/evaluate_diagnostics.py --model "$model" --split heldout \
  --repetitions 1 --num-ctx 4096 --num-predict 384 --timeout 180 \
  --output "$output/diagnostics"
echo 'Coletas encerradas. Confira os estados dos relatórios, inclusive TIMEOUT/NOT_RUN.'
