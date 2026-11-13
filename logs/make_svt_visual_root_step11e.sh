#!/usr/bin/env bash
# Step 11e: visualization ROOT file (dd_web_display TGeo export, as in Steps 8j/8l) of the
# tracking-only geometry for one 20261110_ES scenario. Open it in the DD4hep/ROOT web
# display (or jsroot) to review the SVT endcap disks. Run INSIDE eic-shell 26.09.0-stable
# after check_svt_20261110_step11d.sh, e.g. from the host:
#   proj_svt_disk_tiling/refplanes/eic_exec.sh "bash <this script> rsu6"
# Scenarios: rsu_opt -> installed epic_craterlake_tracking_only.xml
#            other   -> overlay XML (regenerated here from the current install)
# Output: proj_svt_disk_tiling/tmp/visual_step11e/epic_craterlake_tracking_only_<scenario>_<stamp>.root
#         plus .log (export log) and .txt (report).
set -euo pipefail

[[ $# -eq 1 ]] || { echo "Usage: $0 <rsu_opt|rsu6>" >&2; exit 2; }
scenario="$1"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
proj="$repo_root/proj_svt_disk_tiling"
run_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out_dir="$proj/tmp/visual_step11e"
base="$out_dir/epic_craterlake_tracking_only_${scenario}_$run_stamp"
mkdir -p "$out_dir"
command -v dd_web_display >/dev/null || { echo "ERROR: run inside the 26.09.0-stable EIC shell." >&2; exit 2; }

exec > >(tee "$base.txt") 2>&1
printf 'SVT step 11e visualization export (%s): %s\n' "$scenario" "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
printf 'Repository: %s (commit %s + working tree)\n' "$repo_root" "$(git -C "$repo_root" rev-parse --short HEAD)"
set +u; source "$repo_root/install/bin/thisepic.sh"; set -u
if ! cmp -s "$repo_root/compact/tracking/silicon_disks_modules.xml" \
     "$DETECTOR_PATH/compact/tracking/silicon_disks_modules.xml"; then
  echo "WARNING: installed silicon_disks_modules.xml differs from source; rerun step 11d first." >&2
fi

case "$scenario" in
  rsu_opt) xml="$DETECTOR_PATH/epic_craterlake_tracking_only.xml" ;;
  *)
    bash "$proj/logs/make_svt_scenario_overlay_step11d.sh" "$scenario"
    xml="$proj/tmp/scenario_overlay/$scenario/epic_craterlake_tracking_only_$scenario.xml"
    ;;
esac
test -f "$xml"
printf 'Detector configuration: %s\n' "$xml"

# Export from the output dir so module_placements resolve via $DETECTOR_PATH (installed CSVs).
cd "$out_dir"
dd_web_display -o "$base.root" --export "$xml" > "$base.log" 2>&1
test -s "$base.root"
n_warn=$(grep 'SiEndcapModuleTracker' "$base.log" | grep -ci 'warn' || true)
printf 'SiEndcapModuleTracker warnings during export: %s\n' "$n_warn"
printf 'Wrote %s (%s)\n' "$base.root" "$(du -h "$base.root" | cut -f1)"
printf '%s\n' 'VISUAL CHECK: modules sit on the corrugation flats; no modules in the beam-pipe openings.'
printf '%s\n' 'VISUAL CHECK: inward modules carry the 30 um Al on the back (outer) side of the baseplate.'
printf 'RESULT: COMPLETE (%s)\n' "$scenario"
