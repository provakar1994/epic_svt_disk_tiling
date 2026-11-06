#!/usr/bin/env bash
# Run endcap_tracking_performance.py on the SVT disk acceptance campaign (acceptance_v1),
# then plot_pwg_resolution.py when the PWG eta binning is used.
# Usage: ./run_endcap_tracking_performance.sh TAG [FILES_PER_CONFIG] [MAX_EVENTS_PER_FILE]
#   TAG                 output name, e.g. vz0_5files
#   FILES_PER_CONFIG    chunks used per (vz, eta-side) configuration (default 5 = 500k events/side;
#                       the campaign has 50)
#   MAX_EVENTS_PER_FILE optional, for quick tests
# Optional environment:
#   ETA_EDGES  |eta| bin edges (default "1.0 1.5 2.0 2.5 3.0 3.5"; "pwg" = "1.0 2.5 3.0 3.5")
#   P_EDGES    momentum bin edges in GeV (default: script default 0.5,1,2,3,...,20)
# Extra configurations (e.g. vz_p010mm_...) can be added to CONFIGS below.
set -euo pipefail

tag="${1:?Usage: $0 TAG [FILES_PER_CONFIG] [MAX_EVENTS_PER_FILE]}"
files_per_config="${2:-5}"
max_events="${3:-}"
eta_edges="${ETA_EDGES:-1.0 1.5 2.0 2.5 3.0 3.5}"
if [[ "$eta_edges" == pwg ]]; then eta_edges="1.0 2.5 3.0 3.5"; fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
campaign_dir=/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v1
reduced_dir=/pscratch/sd/p/pdatta/svt_disk_tiling/treffi_study/reduced_acceptance_v1
outdir="$script_dir/out/$tag"
CONFIGS=(vz_000mm_eta_m3p8_to_m0p6 vz_000mm_eta_p0p6_to_p3p8)

module load conda
conda activate tracking
export MPLCONFIGDIR="${MPLCONFIGDIR:-/pscratch/sd/p/pdatta/svt_disk_tiling/treffi_study/mplconfig}"

extra=()
if [[ -n "$max_events" ]]; then extra+=(--max-events "$max_events"); fi
if [[ -n "${P_EDGES:-}" ]]; then read -r -a p_edges <<< "$P_EDGES"; extra+=(--p-edges "${p_edges[@]}"); fi
read -r -a eta_array <<< "$eta_edges"

mkdir -p "$outdir"
{
  echo "# $(date -Is) $0 $*"
  echo "# ETA_EDGES=$eta_edges P_EDGES=${P_EDGES:-default} configs=${CONFIGS[*]}"
  python "$script_dir/endcap_tracking_performance.py" \
    --campaign-dir "$campaign_dir" --configs "${CONFIGS[@]}" \
    --files-per-config "$files_per_config" "${extra[@]}" \
    --eta-edges "${eta_array[@]}" \
    --reduced-dir "$reduced_dir" --outdir "$outdir" --tag "$tag"
  if [[ "$eta_edges" == "1.0 2.5 3.0 3.5" ]]; then
    python "$script_dir/plot_pwg_resolution.py" --out "$outdir/pwg_dp_vs_p_${tag}.png" \
      "acceptance_v1 (Step 8m)=$outdir/summary_${tag}.csv"
    python "$script_dir/plot_pwg_resolution.py" --quantity resol_qop --out "$outdir/pwg_qop_vs_p_${tag}.png" \
      "acceptance_v1 (Step 8m)=$outdir/summary_${tag}.csv"
  fi
} 2>&1 | tee "$outdir/run_${tag}.log"
