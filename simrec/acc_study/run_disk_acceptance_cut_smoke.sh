#!/usr/bin/env bash
# Recorded cut-enabled check: 1,000 input events per side at vertex z=0.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
output_dir="$script_dir/tmp/acceptance_cut_smoke_20261027"
[[ ! -e "$output_dir" ]] || { echo "ERROR: output exists: $output_dir" >&2; exit 2; }

module load conda
conda activate tracking

python3 "$script_dir/reduce_disk_acceptance.py" \
  --campaign-root /pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v1 \
  --output-dir "$output_dir/reduced" \
  --vertices 0 \
  --abs-eta-range 1.0 2.0 \
  --momentum-range-gev 1.0 10.0 \
  --max-files-per-side 1 \
  --stop-events-per-file 1000 \
  --step-size 500

python3 "$script_dir/validate_disk_acceptance.py" \
  "$output_dir/reduced/disk_acceptance_vz_000mm.npz" \
  --expected-files-per-side 1
