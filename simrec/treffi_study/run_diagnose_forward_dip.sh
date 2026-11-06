#!/usr/bin/env bash
# Run diagnose_forward_dip.py (forward efficiency dip near eta ~ 1.7); report in out/diagnose_forward_dip/.
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
module load conda
conda activate tracking
export MPLCONFIGDIR="${MPLCONFIGDIR:-/pscratch/sd/p/pdatta/svt_disk_tiling/treffi_study/mplconfig}"
cd "$script_dir"
python diagnose_forward_dip.py --outdir "$script_dir/out/diagnose_forward_dip" "$@" 2>&1 | grep -v Warning
