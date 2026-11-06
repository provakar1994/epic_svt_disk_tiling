#!/usr/bin/env bash
# Recorded one-time particle + reference-plane extraction for one vertex of the
# acceptance_v3_refplanes campaign (extract_disk_particles_refplanes.py).
# All vertices share one extraction root; each run writes its own manifest
# extraction_manifest_vz_<label>mm.csv, so vertices can run in parallel.
# Usage: ./run_extract_refplanes.sh <vz_mm: 0, 100 or -100> [CAMPAIGN_ROOT [OUTPUT_DIR]]
#   defaults: CAMPAIGN_ROOT=/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v3_refplanes
#             OUTPUT_DIR=extracted/acceptance_v3_refplanes
# Extra arguments for testing can be passed through EXTRACT_EXTRA_ARGS, e.g.
#   EXTRACT_EXTRA_ARGS="--max-files-per-side 1" ./run_extract_refplanes.sh 0 <smoke root> <test dir>
# Log: logs/extract_refplanes_vz_<label>mm_<UTC timestamp>.log
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/../.." && pwd)"
vertex="${1:?usage: $0 <vz_mm: 0, 100 or -100> [CAMPAIGN_ROOT [OUTPUT_DIR]]}"
case "$vertex" in
  0) label=000 ;; 100) label=p100 ;; -100) label=m100 ;;
  *) echo "ERROR: vertex must be 0, 100 or -100" >&2; exit 2 ;;
esac
campaign_root="${2:-/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v3_refplanes}"
output_dir="${3:-$script_dir/extracted/acceptance_v3_refplanes}"
plane_map="$project_dir/refplanes/plane_map.csv"
[[ -f "$plane_map" ]] || { echo "ERROR: plane map not found: $plane_map" >&2; exit 2; }
mkdir -p "$script_dir/logs"
log="$script_dir/logs/extract_refplanes_vz_${label}mm_$(date -u +%Y%m%dT%H%M%SZ).log"

module load conda
conda activate tracking

# shellcheck disable=SC2086  # EXTRACT_EXTRA_ARGS is intentionally word-split
{
  echo "Started: $(date --iso-8601=seconds)"
  echo "Campaign root: $campaign_root"
  echo "Output dir:    $output_dir"
  sha256sum "$plane_map" "$script_dir/extract_disk_particles_refplanes.py"
  python3 "$script_dir/extract_disk_particles_refplanes.py" \
    --campaign-root "$campaign_root" \
    --output-dir "$output_dir" \
    --vertices "$vertex" \
    --plane-map "$plane_map" \
    --step-size 5000 ${EXTRACT_EXTRA_ARGS:-}
  echo "Finished: $(date --iso-8601=seconds)"
} 2>&1 | tee "$log"
