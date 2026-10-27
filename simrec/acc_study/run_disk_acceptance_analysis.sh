#!/usr/bin/env bash
# Reproducible extraction -> reduction -> validation -> plotting workflow.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
campaign_root="${1:-/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v1}"
output_dir="${2:-$script_dir/results/acceptance_v1}"
extracted_dir="$output_dir/extracted"

module load conda
conda activate tracking

python3 "$script_dir/extract_disk_particles.py" \
  --campaign-root "$campaign_root" \
  --output-dir "$extracted_dir" \
  --vertices 0 -10 10 \
  --step-size 10000

python3 "$script_dir/reduce_disk_acceptance.py" \
  --extracted-root "$extracted_dir" \
  --output-dir "$output_dir/reduced" \
  --vertices 0 -10 10 \
  --bin-size-mm 10 \
  --xy-limit-mm 450

python3 "$script_dir/validate_disk_acceptance.py" \
  "$output_dir"/reduced/disk_acceptance_vz_*.npz \
  --expected-files-per-side 50 \
  --expected-events-per-side 5000000

python3 "$script_dir/plot_disk_acceptance.py" \
  "$output_dir"/reduced/disk_acceptance_vz_*.npz \
  --output-dir "$output_dir/plots" \
  --minimum-denominator 50
