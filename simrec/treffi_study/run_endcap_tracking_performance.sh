#!/usr/bin/env bash
# Run endcap_tracking_performance.py on an SVT disk acceptance campaign (default acceptance_v1),
# then plot_pwg_resolution.py when the PWG eta binning is used.
# Usage: ./run_endcap_tracking_performance.sh TAG [FILES_PER_CONFIG] [MAX_EVENTS_PER_FILE]
#   TAG                 output name, e.g. vz0_5files
#   FILES_PER_CONFIG    chunks used per (vz, eta-side) configuration (default 5 = 500k events/side;
#                       the campaign has 50)
#   MAX_EVENTS_PER_FILE optional, for quick tests
# Optional environment:
#   ETA_EDGES  |eta| bin edges (default "1.0 1.5 2.0 2.5 3.0 3.5"; "pwg" = "1.0 2.5 3.0 3.5")
#   P_EDGES    momentum bin edges in GeV (default: script default 0.5,1,2,3,...,20)
#   EFF_P_EDGES   p bin edges [GeV] of the efficiency-vs-eta curves (default "0.5 1 2 5 10 20")
#   EFF_ETA_WIDTH eta bin width of the efficiency-vs-eta plot (default 0.05)
#   CAMPAIGN   campaign directory name under /pscratch/sd/p/pdatta/svt_disk_tiling/acc_study
#              (default acceptance_v1; e.g. acceptance_v3_refplanes, reconstructed with the Step 8q map).
#              Per-file caches go to treffi_study/reduced_<CAMPAIGN>/.
#   CAMPAIGN_LABEL  legend label of the PWG plots (default: "acceptance_v1 (Step 8m)" for v1,
#              "acceptance_v3 (Step 8q)" for acceptance_v3_refplanes, else CAMPAIGN)
#   CONFIGS    space-separated configuration names (default: the two vz = 0 configurations)
#   EFF_ONLY=1    only redo the efficiency plots from the cached .npz tables (no fits/CSV);
#                 the log then goes to run_TAG_efficiency.log instead of run_TAG.log
# Extra configurations (e.g. vz_p010mm_...) can be added to CONFIGS below.
set -euo pipefail

tag="${1:?Usage: $0 TAG [FILES_PER_CONFIG] [MAX_EVENTS_PER_FILE]}"
files_per_config="${2:-5}"
max_events="${3:-}"
eta_edges="${ETA_EDGES:-1.0 1.5 2.0 2.5 3.0 3.5}"
if [[ "$eta_edges" == pwg ]]; then eta_edges="1.0 2.5 3.0 3.5"; fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
campaign="${CAMPAIGN:-acceptance_v1}"
case "$campaign" in
  acceptance_v1) default_label="acceptance_v1 (Step 8m)" ;;
  acceptance_v3_refplanes) default_label="acceptance_v3 (Step 8q)" ;;
  *) default_label="$campaign" ;;
esac
campaign_label="${CAMPAIGN_LABEL:-$default_label}"
campaign_dir=/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/$campaign
reduced_dir=/pscratch/sd/p/pdatta/svt_disk_tiling/treffi_study/reduced_$campaign
outdir="$script_dir/out/$tag"
read -r -a CONFIGS <<< "${CONFIGS:-vz_000mm_eta_m3p8_to_m0p6 vz_000mm_eta_p0p6_to_p3p8}"

module load conda
conda activate tracking
export MPLCONFIGDIR="${MPLCONFIGDIR:-/pscratch/sd/p/pdatta/svt_disk_tiling/treffi_study/mplconfig}"

extra=()
if [[ -n "$max_events" ]]; then extra+=(--max-events "$max_events"); fi
if [[ -n "${P_EDGES:-}" ]]; then read -r -a p_edges <<< "$P_EDGES"; extra+=(--p-edges "${p_edges[@]}"); fi
if [[ -n "${EFF_P_EDGES:-}" ]]; then read -r -a eff_p_edges <<< "$EFF_P_EDGES"; extra+=(--eff-p-edges "${eff_p_edges[@]}"); fi
if [[ -n "${EFF_ETA_WIDTH:-}" ]]; then extra+=(--eff-eta-width "$EFF_ETA_WIDTH"); fi
log_name="run_${tag}.log"
if [[ "${EFF_ONLY:-0}" == 1 ]]; then extra+=(--efficiency-only); log_name="run_${tag}_efficiency.log"; fi
read -r -a eta_array <<< "$eta_edges"

mkdir -p "$outdir"
{
  echo "# $(date -Is) $0 $*"
  echo "# CAMPAIGN=$campaign campaign_dir=$campaign_dir reduced_dir=$reduced_dir"
  echo "# ETA_EDGES=$eta_edges P_EDGES=${P_EDGES:-default} EFF_P_EDGES=${EFF_P_EDGES:-default} EFF_ETA_WIDTH=${EFF_ETA_WIDTH:-default} EFF_ONLY=${EFF_ONLY:-0} configs=${CONFIGS[*]}"
  python "$script_dir/endcap_tracking_performance.py" \
    --campaign-dir "$campaign_dir" --configs "${CONFIGS[@]}" \
    --files-per-config "$files_per_config" "${extra[@]}" \
    --eta-edges "${eta_array[@]}" \
    --reduced-dir "$reduced_dir" --outdir "$outdir" --tag "$tag"
  if [[ "$eta_edges" == "1.0 2.5 3.0 3.5" && "${EFF_ONLY:-0}" != 1 ]]; then
    python "$script_dir/plot_pwg_resolution.py" --out "$outdir/pwg_dp_vs_p_${tag}.png" \
      "$campaign_label=$outdir/summary_${tag}.csv"
    python "$script_dir/plot_pwg_resolution.py" --quantity resol_qop --out "$outdir/pwg_qop_vs_p_${tag}.png" \
      "$campaign_label=$outdir/summary_${tag}.csv"
  fi
} 2>&1 | tee "$outdir/$log_name"
