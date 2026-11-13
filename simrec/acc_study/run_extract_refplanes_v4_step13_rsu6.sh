#!/usr/bin/env bash
# [Step 14b rsu6 copy, 2026-11-13: campaign root acceptance_v4_step13_rsu6, output extracted/acceptance_v4_step13_rsu6,
#  plane map refplanes/step13_rsu6/plane_map.csv (byte-identical to step13), log name *_v4_step13_rsu6_*.]
# acceptance_v4_step13 copy (2026-11-13) of run_extract_refplanes.sh (v3 script left unchanged).
# One-time particle + reference-plane extraction for one vertex (extract_disk_particles_refplanes.py).
# All vertices share one extraction root; each run writes extraction_manifest_vz_<label>mm.csv,
# so vertices can run in parallel.
# Changes vs the v3 script:
#   - defaults: v4 campaign root and extracted/acceptance_v4_step13;
#   - plane map refplanes/step13/plane_map.csv (byte-identical to the v3 map, Step 13e);
#   - completeness gate before extracting: EXPECTED_FILES_PER_SIDE (default 50) sim_*.root files in
#     each eta side of the vertex and no sim_*.tmp.* files (a running or failed sim task; rec
#     temporaries of a running recon job are allowed, the extractor reads only sim_*.root); set
#     EXPECTED_FILES_PER_SIDE=1 for the 200-event smoke files.
# Usage: ./run_extract_refplanes_v4_step13.sh <vz_mm: 0, 100 or -100> [CAMPAIGN_ROOT [OUTPUT_DIR]]
#   EXTRACT_EXTRA_ARGS is passed through, e.g. "--max-files-per-side 1".
# Log: logs/extract_refplanes_v4_step13_rsu6_vz_<label>mm_<UTC timestamp>.log
set -euo pipefail
shopt -s nullglob

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/../.." && pwd)"
vertex="${1:?usage: $0 <vz_mm: 0, 100 or -100> [CAMPAIGN_ROOT [OUTPUT_DIR]]}"
case "$vertex" in
  0) label=000 ;; 100) label=p100 ;; -100) label=m100 ;;
  *) echo "ERROR: vertex must be 0, 100 or -100" >&2; exit 2 ;;
esac
campaign_root="${2:-/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v4_step13_rsu6}"
output_dir="${3:-$script_dir/extracted/acceptance_v4_step13_rsu6}"
expected_files="${EXPECTED_FILES_PER_SIDE:-50}"
plane_map="$project_dir/refplanes/step13_rsu6/plane_map.csv"
[[ -f "$plane_map" ]] || { echo "ERROR: plane map not found: $plane_map" >&2; exit 2; }

# Completeness gate (both eta sides of this vertex).
for side in eta_m3p8_to_m0p6 eta_p0p6_to_p3p8; do
  dir="$campaign_root/vz_${label}mm_${side}/rootfiles"
  tmp_files=("$dir"/sim_*.tmp.*)
  sim_files=()
  for f in "$dir"/sim_*.root; do [[ "$f" == *.tmp.* ]] || sim_files+=("$f"); done
  [[ ${#sim_files[@]} -eq "$expected_files" && ${#tmp_files[@]} -eq 0 ]] || {
    echo "ERROR: $dir has ${#sim_files[@]} sim files (expected $expected_files) and ${#tmp_files[@]} sim_*.tmp.* files" >&2
    exit 1; }
done

mkdir -p "$script_dir/logs"
log="$script_dir/logs/extract_refplanes_v4_step13_rsu6_vz_${label}mm_$(date -u +%Y%m%dT%H%M%SZ).log"

module load conda
conda activate tracking

# shellcheck disable=SC2086  # EXTRACT_EXTRA_ARGS is intentionally word-split
{
  echo "Started: $(date --iso-8601=seconds)"
  echo "Campaign root: $campaign_root"
  echo "Output dir:    $output_dir"
  echo "Sim files per side: $expected_files (gate passed)"
  sha256sum "$plane_map" "$script_dir/extract_disk_particles_refplanes.py"
  python3 "$script_dir/extract_disk_particles_refplanes.py" \
    --campaign-root "$campaign_root" \
    --output-dir "$output_dir" \
    --vertices "$vertex" \
    --plane-map "$plane_map" \
    --step-size 5000 ${EXTRACT_EXTRA_ARGS:-}
  echo "Finished: $(date --iso-8601=seconds)"
} 2>&1 | tee "$log"
