#!/usr/bin/env bash
# Redo the endcap tracking analysis on acceptance_v3_refplanes (reconstructed with the Step 8q
# tracking-only map, Slurm job 60936753), same settings as the v1 outputs fine_vz0_50files and
# pwg_vz0_50files, then compare v1 and v3 in the PWG dp/p and q/p plots.
# Runs sequentially: the first run fills the shared per-file cache reduced_acceptance_v3_refplanes/.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CAMPAIGN=acceptance_v3_refplanes
"$here/run_endcap_tracking_performance.sh" v3_fine_vz0_50files 50
ETA_EDGES=pwg "$here/run_endcap_tracking_performance.sh" v3_pwg_vz0_50files 50

module load conda; conda activate tracking
out="$here/out/v1_vs_v3_pwg_vz0_50files"; mkdir -p "$out"
for q in resol_dp resol_qop; do
  python "$here/plot_pwg_resolution.py" --quantity "$q" --out "$out/pwg_${q}_v1_vs_v3.png" \
    "acceptance_v1 (Step 8m map)=$here/out/pwg_vz0_50files/summary_pwg_vz0_50files.csv" \
    "acceptance_v3 (Step 8q map)=$here/out/v3_pwg_vz0_50files/summary_v3_pwg_vz0_50files.csv"
done
