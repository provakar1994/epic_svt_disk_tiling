#!/usr/bin/env bash
# Recorded TEST of analyze_refplane_efficiency.py on SYNTHETIC refplanes shards
# (real silicon fields from old extractions + toy plane fields, see
# make_synthetic_refplane_shards_20261106.py). Mechanics test only: the
# numbers are not physics results. Uses a synthetic plane map (made-up ids,
# z_plane = z_disk -/+ 6 mm, rmin = layer-envelope rmin, rmax = disk rmax + 20).
# Closure expectations: hit_without_plane = 0; med|true - mean hit| ~ 0; for
# selection fid the true-point efficiency is close to the straight-line fid
# efficiency at high p (toy plane point = real hit for hit particles).
# Output: tmp/refplane_analysis_synthetic_20261106/ ; report logs/check_refplane_analysis_synthetic_20261106.txt
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
test_dir="$script_dir/tmp/refplane_analysis_synthetic_20261106"
report="$script_dir/logs/check_refplane_analysis_synthetic_20261106.txt"
[[ ! -e "$test_dir" ]] || { echo "ERROR: $test_dir exists" >&2; exit 2; }
mkdir -p "$test_dir"
cat > "$test_dir/synthetic_plane_map.csv" <<'CSV'
disk,side,z_disk_mm,z_plane_mm,rmin_mm,rmax_mm,system,barrel,layer
ED0,negative,-250,-244,37.0,250.0,250,2,1
ED1,negative,-450,-444,54.45,425.0,250,2,2
ED2,negative,-650,-644,47.0,450.0,250,2,3
ED3,negative,-850,-844,47.0,450.0,250,2,4
ED4,negative,-1020,-1014,47.0,450.0,250,2,5
HD0,positive,250,244,37.0,250.0,250,1,1
HD1,positive,450,444,54.45,425.0,250,1,2
HD2,positive,700,694,47.0,450.0,250,1,3
HD3,positive,950,944,47.0,450.0,250,1,4
HD4,positive,1200,1194,47.0,450.0,250,1,5
CSV

module load conda
conda activate tracking
{
  echo "check_refplane_analysis_synthetic_20261106: $(date --iso-8601=seconds)"
  echo "SYNTHETIC TOY INPUT - mechanics test only, not a physics result"
  python3 "$script_dir/make_synthetic_refplane_shards_20261106.py" \
    "$test_dir/synthetic_plane_map.csv" "$test_dir/extracted" 3 | tail -2
  start=$(date +%s)
  EXTRACTED_ROOT="$test_dir/extracted" OUTPUT_DIR="$test_dir/results" \
    PLANE_MAP="$test_dir/synthetic_plane_map.csv" \
    "$script_dir/run_refplane_efficiency.sh" 0 100 -100
  echo "analysis wall time: $(( $(date +%s) - start )) s for 3 vertices x 2 sides x 3 shards (1.8M primaries)"
  echo "--- output files (vz_000mm) ---"
  ls "$test_dir/results/vz_000mm" | head -50
  echo "number of PDF pages expected per vertex: 1 + 10 disks x 3 = 31"
} > "$report" 2>&1
cat "$report"
