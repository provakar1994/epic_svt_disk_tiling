#!/usr/bin/env bash
# Step 14b (2026-11-13): smoke test of the rsu6 acceptance analysis chain on the two 200-event vz = +100 smoke
# files (run_smoke_test_20261113_v4_step13_rsu6.sh). Same pattern as the Step 13f smoke test. Numbers are
# meaningless (N ~ 100); this only checks that the scripts run end to end with the rsu6 inputs.
#   1. run_extract_refplanes_v4_step13_rsu6.sh 100 <smoke root> <test>/extracted   (EXPECTED_FILES_PER_SIDE=1)
#   2. run_refplane_efficiency_v4_step13_rsu6.sh 100 (EXTRACTED_ROOT/OUTPUT_DIR = test dirs, EXPECTED_SHARDS_PER_SIDE=1)
#   3. compare_refplane_scenarios.py --vertices 100: A = rsu_opt results/refplane_efficiency_v5, B = test results
# Output: <smoke root>/analysis_test_20261113/ ; refuses if it exists.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
smoke_root=/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/smoke_20261113_v4_step13_rsu6
test_dir="$smoke_root/analysis_test_20261113"
[[ ! -e "$test_dir" ]] || { echo "ERROR: $test_dir exists" >&2; exit 2; }
mkdir -p "$test_dir"
EXPECTED_FILES_PER_SIDE=1 "$here/run_extract_refplanes_v4_step13_rsu6.sh" 100 "$smoke_root" "$test_dir/extracted" > "$test_dir/extract.out" 2>&1
echo "extraction exit status: $?"
EXTRACTED_ROOT="$test_dir/extracted" OUTPUT_DIR="$test_dir/results" EXPECTED_SHARDS_PER_SIDE=1 \
  "$here/run_refplane_efficiency_v4_step13_rsu6.sh" 100 > "$test_dir/efficiency.out" 2>&1
echo "efficiency exit status: $?"; echo "result files: $(ls -1 "$test_dir"/results/*/ | wc -l)"
module load conda >/dev/null 2>&1; conda activate tracking
cd "$here"
python3 compare_refplane_scenarios.py --b "$test_dir/results" --vertices 100 \
  --out-prefix "$test_dir/compare_rsu_opt_vs_rsu6_smoke" > "$test_dir/compare_rsu_opt_vs_rsu6_smoke.txt" 2>&1
echo "compare exit status: $?"
head -25 "$test_dir/compare_rsu_opt_vs_rsu6_smoke.txt"
