#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 1 ]]; then
  echo 'Uso: scripts/run_diagnostics_mac.sh DIRETORIO_NOVO [opções evaluate_diagnostics.py]' >&2
  exit 2
fi
root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="$1"
shift
cd "$root_dir"
# Execute after timing campaigns; this consumes CPU and does not measure kernel speed.
python3 -B scripts/evaluate_diagnostics.py --output "$output_dir" "$@"
