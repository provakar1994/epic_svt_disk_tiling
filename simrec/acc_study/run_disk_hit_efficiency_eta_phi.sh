#!/usr/bin/env bash
# Recorded per-disk hit-efficiency maps in generated (eta, phi), z=0 sample.
# One page per disk and momentum selection; the region is set from all momenta.
# v2: same definitions as v1, plus the rounded efficiency [%] printed in each bin.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
extracted_root="$script_dir/extracted/acceptance_v1"
output_dir="$script_dir/results/disk_hit_efficiency_v2"

module load conda
conda activate tracking

python3 "$script_dir/plot_disk_hit_efficiency_eta_phi.py" \
  --extracted-root "$extracted_root" \
  --output-dir "$output_dir" \
  --vertices 0 \
  --momentum-bin 0.5 1.5 \
  --momentum-bin 1.5 3.0 \
  --momentum-bin 3.0 5.0 \
  --momentum-bin 5.0 10.0 \
  --momentum-bin 10.0 20.01 \
  --eta-bin-width 0.1 \
  --phi-bin-width-deg 10 \
  --minimum-bin-denominator 20 \
  --region-min-row-efficiency 0.01
