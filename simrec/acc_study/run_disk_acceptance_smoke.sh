#!/usr/bin/env bash
# Recorded 2,000-event reduction/validation/plot smoke test (1,000 per eta side).
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
campaign_root="/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v1"
output_dir="$script_dir/tmp/acceptance_smoke_20261027_v2"

[[ ! -e "$output_dir" ]] || {
  echo "ERROR: smoke output already exists: $output_dir" >&2
  exit 2
}

module load conda
conda activate tracking

python3 "$script_dir/reduce_disk_acceptance.py" \
  --campaign-root "$campaign_root" \
  --output-dir "$output_dir/reduced" \
  --vertices 0 \
  --max-files-per-side 1 \
  --stop-events-per-file 1000 \
  --step-size 500

python3 "$script_dir/validate_disk_acceptance.py" \
  "$output_dir/reduced/disk_acceptance_vz_000mm.npz" \
  --expected-files-per-side 1 \
  --expected-events-per-side 1000

python3 "$script_dir/plot_disk_acceptance.py" \
  "$output_dir/reduced/disk_acceptance_vz_000mm.npz" \
  --output-dir "$output_dir/plots" \
  --minimum-denominator 1
