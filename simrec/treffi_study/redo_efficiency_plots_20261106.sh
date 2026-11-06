#!/usr/bin/env bash
# Redo only the efficiency plots (efficiency vs eta in p bins, efficiency vs p) for the
# existing 50-chunk outputs, from the cached .npz tables (no ROOT reading, no fits).
# The previous efficiency PNGs are first moved to tmp/retained/2026-11-06/ and logged
# in tmp/file_actions.log, because the new plots reuse the same file names.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/../.." && pwd)"
# Usage: redo_efficiency_plots_20261106.sh [RETAIN_LABEL [REASON]]
#   first use (default): before_p_bins; 2nd use: before_no_zoom (zoom panel and all-p curve removed)
retain_label="${1:-before_p_bins}"
reason="${2:-superseded by efficiency-vs-eta in p bins (same file name)}"
retain_dir="$project_dir/tmp/retained/2026-11-06/simrec/treffi_study/out_efficiency_${retain_label}"
log="$project_dir/tmp/file_actions.log"

retain() {
  local src="$1" sub="$2"
  if [[ -e "$src" ]]; then
    mkdir -p "$retain_dir/$sub"
    mv -n "$src" "$retain_dir/$sub/"
    echo "$(date -Is) | ${src#$project_dir/} | ${retain_dir#$project_dir/}/$sub/$(basename "$src") | move | $reason" >> "$log"
  fi
}

for tag in pwg_vz0_50files fine_vz0_50files; do
  for f in efficiency_eta efficiency_p; do
    retain "$script_dir/out/$tag/${f}_${tag}.png" "$tag"
  done
done

ETA_EDGES=pwg EFF_ONLY=1 "$script_dir/run_endcap_tracking_performance.sh" pwg_vz0_50files 50
EFF_ONLY=1 "$script_dir/run_endcap_tracking_performance.sh" fine_vz0_50files 50
