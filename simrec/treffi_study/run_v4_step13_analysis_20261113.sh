#!/usr/bin/env bash
# Endcap tracking analysis of acceptance_v4_step13 (Step 13 geometry, reconstructed with the Step 13
# tracking-only ACTS map), same settings as run_v3_step8q_analysis_20261106.sh (v3 script unchanged):
#   - fine eta binning   -> out/v4_fine_vz0_50files/
#   - PWG eta binning    -> out/v4_pwg_vz0_50files/ (incl. PWG dp/p and q/p plots)
#   - v3 vs v4 PWG plots -> out/v3_vs_v4_pwg_vz0_50files/pwg_resol_{dp,qop}_v3_vs_v4.png
#   - compare_v3_v4_20261113.py -> out/v3_vs_v4_pwg_vz0_50files/compare_v3_v4.txt
# vz = 0 only, 50 files per side (2 x 5M primaries). Environment: conda "tracking" (inside
# run_endcap_tracking_performance.sh and below), no container.
# Gate (check_rec_campaign_ready.sh): refuses to run unless all 100 vz = 0 rec files exist, no
# *.tmp.* file is present in those rootfiles/ directories, and every rec log shows the Step 13
# map sha256 given as argument. Also refuses if any output directory already exists.
# Usage: ./run_v4_step13_analysis_20261113.sh STEP13_MAP_SHA256 [--check-only]
#   --check-only: run the gate and the output-directory check, then stop (dry run).
# Runs sequentially: the first run fills the per-file cache reduced_acceptance_v4_step13/.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
usage() { echo "Usage: $0 STEP13_MAP_SHA256 [--check-only]" >&2; exit 2; }
[[ $# -ge 1 && $# -le 2 ]] || usage
map_sha="$1"
check_only=0
if [[ $# -eq 2 ]]; then [[ "$2" == --check-only ]] || usage; check_only=1; fi
[[ "$map_sha" =~ ^[0-9a-f]{64}$ ]] || { echo "ERROR: STEP13_MAP_SHA256 must be 64 lowercase hex digits" >&2; exit 2; }
# The v3 (Step 8q) map must not be passed by mistake.
[[ "$map_sha" != b5ce1f2ef05a20149c2c4153bb818abe2648ee6b0d95a638cd935b9153873843 ]] || {
  echo "ERROR: that is the Step 8q (v3) map sha256, not the Step 13 map" >&2; exit 2; }

export CAMPAIGN=acceptance_v4_step13
export CAMPAIGN_LABEL="acceptance_v4 (Step 13)"
campaign_dir=/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/$CAMPAIGN
tag_fine=v4_fine_vz0_50files
tag_pwg=v4_pwg_vz0_50files
cmp_dir="$here/out/v3_vs_v4_pwg_vz0_50files"
v3_pwg_csv="$here/out/v3_pwg_vz0_50files/summary_v3_pwg_vz0_50files.csv"

"$here/check_rec_campaign_ready.sh" "$campaign_dir" "$map_sha" 50 || { echo "ERROR: rec campaign not ready" >&2; exit 1; }
for d in "$here/out/$tag_fine" "$here/out/$tag_pwg" "$cmp_dir"; do
  [[ ! -e "$d" ]] || { echo "ERROR: output exists: $d (move it to tmp/retained first)" >&2; exit 1; }
done
[[ -f "$v3_pwg_csv" ]] || { echo "ERROR: missing v3 reference $v3_pwg_csv" >&2; exit 1; }
if [[ $check_only -eq 1 ]]; then echo "Check only: gate passed, outputs free. Nothing run."; exit 0; fi

echo "Started: $(date -Is)  map sha256 $map_sha"
"$here/run_endcap_tracking_performance.sh" "$tag_fine" 50
ETA_EDGES=pwg "$here/run_endcap_tracking_performance.sh" "$tag_pwg" 50

module load conda; conda activate tracking
export MPLCONFIGDIR="${MPLCONFIGDIR:-/pscratch/sd/p/pdatta/svt_disk_tiling/treffi_study/mplconfig}"
mkdir -p "$cmp_dir"
for q in resol_dp resol_qop; do
  python "$here/plot_pwg_resolution.py" --quantity "$q" --out "$cmp_dir/pwg_${q}_v3_vs_v4.png" \
    "acceptance_v3 (Step 8q)=$v3_pwg_csv" \
    "acceptance_v4 (Step 13)=$here/out/$tag_pwg/summary_${tag_pwg}.csv"
done
python "$here/compare_v3_v4_20261113.py" > "$cmp_dir/compare_v3_v4.txt"
echo "Wrote $cmp_dir/compare_v3_v4.txt"
echo "Finished: $(date -Is)"
