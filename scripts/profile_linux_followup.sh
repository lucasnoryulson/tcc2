#!/usr/bin/env bash
# Collect counters into a NEW archive; existing Linux benchmark archives are read-only.
set -euo pipefail
if [ "$#" -lt 2 ] || [ "$(uname -s)" != Linux ]; then
  echo 'Uso no Linux: bash scripts/profile_linux_followup.sh <campanha-completa> <diretorio-novo> [--axpy-session <sessao-AXPY>] [--threads 1 2 4] [--memory-event <evento-suportado>]' >&2
  exit 2
fi
script_directory=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 -B "$script_directory/profile_linux_followup.py" "$@"
