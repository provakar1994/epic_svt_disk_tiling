#!/usr/bin/env bash
# Recorded count-only scan using measured per-particle disk hit positions.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
extracted_root="$script_dir/extracted/acceptance_v1"
output_dir="$script_dir/results/hit_r_phi_counts_v1"

module load conda
conda activate tracking

python3 "$script_dir/plot_disk_hit_r_phi_counts.py" \
  --extracted-root "$extracted_root" \
  --output-dir "$output_dir" \
  --vertices 0 \
  --momentum-bin 0.5 1.5 \
  --momentum-bin 1.5 3.0 \
  --momentum-bin 3.0 5.0 \
  --momentum-bin 5.0 10.0 \
  --momentum-bin 10.0 20.01 \
  --r-max-mm 450 \
  --r-bin-width-mm 10
