#!/usr/bin/env bash
# Recorded one-time particle extraction for one vertex sample.
# Each non-zero vertex gets its own extraction root, because
# extract_disk_particles.py rewrites extraction_manifest.csv in its output
# directory with only the rows of the current run; sharing
# extracted/acceptance_v1/ would overwrite the z=0 manifest.
# Usage: ./run_extract_vertex.sh <vz_mm>   (-10, 10, -100 or 100)
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
vertex="${1:?usage: $0 <vertex_mm: -10 or 10>}"
case "$vertex" in
  -10)  output_dir="$script_dir/extracted/acceptance_v1_vz_m010mm"; campaign="acceptance_v1" ;;
  10)   output_dir="$script_dir/extracted/acceptance_v1_vz_p010mm"; campaign="acceptance_v1" ;;
  -100) output_dir="$script_dir/extracted/acceptance_v2_vz_m100mm"; campaign="acceptance_v2_vz100mm" ;;
  100)  output_dir="$script_dir/extracted/acceptance_v2_vz_p100mm"; campaign="acceptance_v2_vz100mm" ;;
  *)    echo "ERROR: vertex must be -10, 10, -100 or 100 (z=0 is in extracted/acceptance_v1)" >&2; exit 2 ;;
esac
campaign_root="/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/$campaign"

module load conda
conda activate tracking

python3 "$script_dir/extract_disk_particles.py" \
  --campaign-root "$campaign_root" \
  --output-dir "$output_dir" \
  --vertices "$vertex" \
  --step-size 5000
