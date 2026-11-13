#!/usr/bin/env bash
# Step 14b (2026-11-13) rsu6 copy of run_v4_step13_analysis_20261113.sh (unchanged). Endcap tracking
# analysis of acceptance_v4_step13_rsu6 (20261110_ES/rsu6 overlay, reconstructed with the rsu6 Step 13
# tracking-only ACTS map), same settings as v4:
#   - fine eta binning      -> out/v4_rsu6_fine_vz0_50files/
#   - PWG eta binning       -> out/v4_rsu6_pwg_vz0_50files/ (incl. PWG dp/p and q/p plots)
#   - rsu_opt vs rsu6 plots -> out/v4_rsu6_vs_rsuopt_pwg_vz0_50files/pwg_resol_{dp,qop}_rsuopt_vs_rsu6.png
#   - compare_tracking_scenarios_20261113.py (A = v4 rsu_opt, B = v4 rsu6)
#                           -> out/v4_rsu6_vs_rsuopt_pwg_vz0_50files/compare_rsuopt_vs_rsu6.txt
# Gates: check_rec_campaign_ready.sh with the rsu6 map sha256 (argument); in addition every vz = 0
# rec log must list the rsu6 tracking-only XML sha256 453fda16... (run_sim.sh writes sha256sum of
# ACC_XML and the map into the rec log), i.e. eicrecon used the rsu6 geometry. Refuses the v3 and the
# rsu_opt Step 13 map sha256, existing outputs, and a missing rsu_opt v4 PWG reference.
# Usage: ./run_v4_step13_rsu6_analysis_20261113.sh RSU6_MAP_SHA256 [--check-only]
set -euo pipefail
shopt -s nullglob
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
usage() { echo "Usage: $0 RSU6_MAP_SHA256 [--check-only]" >&2; exit 2; }
[[ $# -ge 1 && $# -le 2 ]] || usage
map_sha="$1"
check_only=0
if [[ $# -eq 2 ]]; then [[ "$2" == --check-only ]] || usage; check_only=1; fi
[[ "$map_sha" =~ ^[0-9a-f]{64}$ ]] || { echo "ERROR: RSU6_MAP_SHA256 must be 64 lowercase hex digits" >&2; exit 2; }
case "$map_sha" in
  b5ce1f2ef05a20149c2c4153bb818abe2648ee6b0d95a638cd935b9153873843) echo "ERROR: that is the Step 8q (v3) map" >&2; exit 2 ;;
  cba82219b990be0f2e6a85b707e25f95755095480c071859bd0c4eb00df45e66) echo "ERROR: that is the rsu_opt Step 13 map" >&2; exit 2 ;;
esac
rsu6_xml_sha=453fda16a335bb8735e8e6f616ba16f5f4970b573417818691bc0afa5ec19065

export CAMPAIGN=acceptance_v4_step13_rsu6
export CAMPAIGN_LABEL="acceptance_v4 rsu6 (Step 13)"
campaign_dir=/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/$CAMPAIGN
tag_fine=v4_rsu6_fine_vz0_50files
tag_pwg=v4_rsu6_pwg_vz0_50files
cmp_dir="$here/out/v4_rsu6_vs_rsuopt_pwg_vz0_50files"
ref_pwg_csv="$here/out/v4_pwg_vz0_50files/summary_v4_pwg_vz0_50files.csv"

"$here/check_rec_campaign_ready.sh" "$campaign_dir" "$map_sha" 50 || { echo "ERROR: rec campaign not ready" >&2; exit 1; }
n_logs=0; n_bad=0
for log in "$campaign_dir"/vz_000mm_eta_*/logs/rec_*.log; do
  n_logs=$((n_logs + 1))
  grep -Eq "^${rsu6_xml_sha}  .*/epic_craterlake_tracking_only_rsu6\.xml\$" "$log" || n_bad=$((n_bad + 1))
done
echo "rsu6 XML in rec logs: $((n_logs - n_bad))/$n_logs"
[[ "$n_logs" -eq 100 && "$n_bad" -eq 0 ]] || { echo "ERROR: rec logs not all on the rsu6 XML" >&2; exit 1; }
for d in "$here/out/$tag_fine" "$here/out/$tag_pwg" "$cmp_dir"; do
  [[ ! -e "$d" ]] || { echo "ERROR: output exists: $d (move it to tmp/retained first)" >&2; exit 1; }
done
[[ -f "$ref_pwg_csv" ]] || { echo "ERROR: missing rsu_opt v4 reference $ref_pwg_csv" >&2; exit 1; }
if [[ $check_only -eq 1 ]]; then echo "Check only: gate passed, outputs free. Nothing run."; exit 0; fi

echo "Started: $(date -Is)  map sha256 $map_sha"
"$here/run_endcap_tracking_performance.sh" "$tag_fine" 50
ETA_EDGES=pwg "$here/run_endcap_tracking_performance.sh" "$tag_pwg" 50

module load conda; conda activate tracking
export MPLCONFIGDIR="${MPLCONFIGDIR:-/pscratch/sd/p/pdatta/svt_disk_tiling/treffi_study/mplconfig}"
mkdir -p "$cmp_dir"
for q in resol_dp resol_qop; do
  python "$here/plot_pwg_resolution.py" --quantity "$q" --out "$cmp_dir/pwg_${q}_rsuopt_vs_rsu6.png" \
    "acceptance_v4 rsu_opt (Step 13)=$ref_pwg_csv" \
    "acceptance_v4 rsu6 (Step 13)=$here/out/$tag_pwg/summary_${tag_pwg}.csv"
done
python "$here/compare_tracking_scenarios_20261113.py" > "$cmp_dir/compare_rsuopt_vs_rsu6.txt"
echo "Wrote $cmp_dir/compare_rsuopt_vs_rsu6.txt"
echo "Finished: $(date -Is)"
