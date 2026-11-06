#!/usr/bin/env bash
# Recorded reference-plane hit-efficiency analysis (analyze_refplane_efficiency.py).
# Usage: ./run_refplane_efficiency.sh [vz_mm ...]        (default: 0 100 -100)
# Optional environment overrides (for tests):
#   EXTRACTED_ROOT  (default extracted/acceptance_v3_refplanes)
#   OUTPUT_DIR      (default results/refplane_efficiency_v1; one vz_* subdir per vertex,
#                    an existing vertex subdir is never overwritten)
#   PLANE_MAP       (default ../../refplanes/plane_map.csv)
#   ANALYSIS_EXTRA_ARGS, e.g. "--max-shards-per-side 2"
# Log: logs/refplane_efficiency_<UTC timestamp>.log
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/../.." && pwd)"
vertices=("$@")
[[ ${#vertices[@]} -gt 0 ]] || vertices=(0 100 -100)
extracted_root="${EXTRACTED_ROOT:-$script_dir/extracted/acceptance_v3_refplanes}"
output_dir="${OUTPUT_DIR:-$script_dir/results/refplane_efficiency_v1}"
plane_map="${PLANE_MAP:-$project_dir/refplanes/plane_map.csv}"
geometry_xml="$script_dir/../../../compact/tracking/definitions_craterlake.xml"
rows_csv="$script_dir/../../../compact/tracking/silicon_disks_tiling/20261001_ES/SVT_endcap_corrugation_rows_33_36.csv"
[[ -f "$plane_map" ]] || { echo "ERROR: plane map not found: $plane_map" >&2; exit 2; }
mkdir -p "$script_dir/logs"
log="$script_dir/logs/refplane_efficiency_$(date -u +%Y%m%dT%H%M%SZ).log"

module load conda
conda activate tracking

# shellcheck disable=SC2086  # ANALYSIS_EXTRA_ARGS is intentionally word-split
{
  echo "Started: $(date --iso-8601=seconds)"
  sha256sum "$plane_map" "$geometry_xml" "$rows_csv" "$script_dir/analyze_refplane_efficiency.py"
  python3 "$script_dir/analyze_refplane_efficiency.py" \
    --extracted-root "$extracted_root" \
    --output-dir "$output_dir" \
    --vertices "${vertices[@]}" \
    --plane-map "$plane_map" \
    --geometry-xml "$geometry_xml" \
    --rows-csv "$rows_csv" \
    --xy-bin-mm 4 \
    --inner-margin-mm 30 --outer-margin-mm 40 \
    --inner-boundary openings \
    --min-denominator-2d 20 --min-denominator-1d 100 ${ANALYSIS_EXTRA_ARGS:-}
  echo "Finished: $(date --iso-8601=seconds)"
} 2>&1 | tee "$log"
