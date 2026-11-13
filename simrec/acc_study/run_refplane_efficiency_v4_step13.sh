#!/usr/bin/env bash
# acceptance_v4_step13 copy (2026-11-13) of run_refplane_efficiency.sh (v3 script left unchanged).
# Reference-plane hit-efficiency analysis (analyze_refplane_efficiency.py, unchanged; it already
# has the refplane_efficiency_v4 presentation: nomargin computed and written but not plotted).
# Changes vs the v3 script:
#   - EXTRACTED_ROOT default extracted/acceptance_v4_step13; OUTPUT_DIR default
#     results/refplane_efficiency_v5;
#   - PLANE_MAP default refplanes/step13/plane_map.csv (byte-identical to v3);
#   - rows table: geometry/row_families_20261110_ES_rsu_opt.csv, made from the delivered
#     20261110_ES/rsu_opt/<disk>_rows.csv by make_row_families_20261110.py (family A = 36 mm pitch,
#     B = 33 mm), instead of the 20261001 table;
#   - active outline: geometry/active_silicon_rectangles_step13.csv (Step 13 install,
#     run_dump_active_silicon_step13.sh) instead of the EPIC 311634084 dump;
#   - gate: an extraction manifest per requested vertex and EXPECTED_SHARDS_PER_SIDE (default 50)
#     shards per eta side.
# Usage: ./run_refplane_efficiency_v4_step13.sh [vz_mm ...]        (default: 0 100 -100)
# Optional environment overrides: EXTRACTED_ROOT, OUTPUT_DIR, PLANE_MAP, ROWS_CSV, ACTIVE_CSV,
#   EXPECTED_SHARDS_PER_SIDE, ANALYSIS_EXTRA_ARGS (e.g. "--max-shards-per-side 2").
# An existing vertex subdirectory of OUTPUT_DIR is never overwritten (analysis script rule).
# Log: logs/refplane_efficiency_v4_step13_<UTC timestamp>.log
set -euo pipefail
shopt -s nullglob

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/../.." && pwd)"
vertices=("$@")
[[ ${#vertices[@]} -gt 0 ]] || vertices=(0 100 -100)
extracted_root="${EXTRACTED_ROOT:-$script_dir/extracted/acceptance_v4_step13}"
output_dir="${OUTPUT_DIR:-$script_dir/results/refplane_efficiency_v5}"
plane_map="${PLANE_MAP:-$project_dir/refplanes/step13/plane_map.csv}"
rows_csv="${ROWS_CSV:-$script_dir/geometry/row_families_20261110_ES_rsu_opt.csv}"
active_csv="${ACTIVE_CSV:-$script_dir/geometry/active_silicon_rectangles_step13.csv}"
expected_shards="${EXPECTED_SHARDS_PER_SIDE:-50}"
geometry_xml="$script_dir/../../../compact/tracking/definitions_craterlake.xml"
for f in "$plane_map" "$rows_csv" "$active_csv" "$geometry_xml"; do
  [[ -f "$f" ]] || { echo "ERROR: input not found: $f" >&2; exit 2; }
done
for vz in "${vertices[@]}"; do
  case "$vz" in 0) label=000 ;; 100) label=p100 ;; -100) label=m100 ;;
    *) echo "ERROR: bad vertex $vz" >&2; exit 2 ;; esac
  [[ -f "$extracted_root/extraction_manifest_vz_${label}mm.csv" ]] || {
    echo "ERROR: extraction of vz=$vz not finished (no manifest in $extracted_root)" >&2; exit 1; }
  for side in eta_m3p8_to_m0p6 eta_p0p6_to_p3p8; do
    shards=()
    for f in "$extracted_root/vz_${label}mm_${side}"/particles_*.npz; do [[ "$f" == *.tmp.* ]] || shards+=("$f"); done
    [[ ${#shards[@]} -eq "$expected_shards" ]] || {
      echo "ERROR: ${#shards[@]} shards in vz_${label}mm_${side} (expected $expected_shards)" >&2; exit 1; }
  done
done
mkdir -p "$script_dir/logs"
log="$script_dir/logs/refplane_efficiency_v4_step13_$(date -u +%Y%m%dT%H%M%SZ).log"

module load conda
conda activate tracking

# shellcheck disable=SC2086  # ANALYSIS_EXTRA_ARGS is intentionally word-split
{
  echo "Started: $(date --iso-8601=seconds)"
  echo "Extracted root: $extracted_root ; output: $output_dir ; vertices: ${vertices[*]}"
  sha256sum "$plane_map" "$geometry_xml" "$rows_csv" "$active_csv" "$script_dir/analyze_refplane_efficiency.py"
  python3 "$script_dir/analyze_refplane_efficiency.py" \
    --extracted-root "$extracted_root" \
    --output-dir "$output_dir" \
    --vertices "${vertices[@]}" \
    --plane-map "$plane_map" \
    --geometry-xml "$geometry_xml" \
    --rows-csv "$rows_csv" \
    --active-csv "$active_csv" \
    --xy-bin-mm 4 \
    --inner-margin-mm 30 --outer-margin-mm 40 \
    --inner-boundary openings \
    --min-denominator-2d 20 --min-denominator-1d 100 ${ANALYSIS_EXTRA_ARGS:-}
  echo "Finished: $(date --iso-8601=seconds)"
} 2>&1 | tee "$log"
