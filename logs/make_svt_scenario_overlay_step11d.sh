#!/usr/bin/env bash
# Step 11d: generate a scenario overlay so a second tiling scenario (e.g. rsu6)
# can be built without editing the EPIC repository.
#
# Inputs (INSTALLED geometry, $DETECTOR_PATH = epic/install/share/epic by default):
#   compact/tracking/silicon_disks_modules.xml   (production: <DELIVERY>/rsu_opt)
#   epic_craterlake_tracking_only.xml, epic_craterlake.xml
# Outputs in proj_svt_disk_tiling/tmp/scenario_overlay/<scenario>/:
#   silicon_disks_modules_<scenario>.xml          path component <DELIVERY>/rsu_opt -> <DELIVERY>/<scenario>
#   epic_craterlake_tracking_only_<scenario>.xml  includes the copy above by absolute path
#   epic_craterlake_<scenario>.xml                same for the full detector
#   provenance.txt                                EPIC commit, sha256 of inputs and outputs
#
# The module_placements paths stay relative ("compact/tracking/silicon_disks_tiling/...").
# SiEndcapModuleTracker_geo.cpp resolve_input_file() tries the path relative to the
# current directory first, then $DETECTOR_PATH/<path>. Load the overlay with
# DETECTOR_PATH pointing at the same install, and preferably from a directory other
# than the repo root so the installed copy (not the source tree) is used.
#
# Usage: make_svt_scenario_overlay_step11d.sh <scenario>     (e.g. rsu6; host or container)
# Optional env: DELIVERY (default 20261110_ES), SOURCE_SCENARIO (default rsu_opt),
#               DETECTOR_PATH, OVERLAY_ROOT (default proj_svt_disk_tiling/tmp/scenario_overlay)
set -euo pipefail

[[ $# -eq 1 ]] || { echo "Usage: $0 <scenario>   (e.g. rsu6)" >&2; exit 2; }
scenario="$1"
delivery="${DELIVERY:-20261110_ES}"
source_scenario="${SOURCE_SCENARIO:-rsu_opt}"
[[ "$scenario" != "$source_scenario" ]] || {
  echo "ERROR: $scenario is already the installed scenario; use the installed XML directly." >&2; exit 2; }

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
epic_root="$(cd "$here/../.." && pwd)"
detector_path="${DETECTOR_PATH:-$epic_root/install/share/epic}"
out_dir="${OVERLAY_ROOT:-$epic_root/proj_svt_disk_tiling/tmp/scenario_overlay}/$scenario"

src_modules="$detector_path/compact/tracking/silicon_disks_modules.xml"
src_tracking="$detector_path/epic_craterlake_tracking_only.xml"
src_full="$detector_path/epic_craterlake.xml"
scenario_dir="$detector_path/compact/tracking/silicon_disks_tiling/$delivery/$scenario"
out_modules="$out_dir/silicon_disks_modules_$scenario.xml"
out_tracking="$out_dir/epic_craterlake_tracking_only_$scenario.xml"
out_full="$out_dir/epic_craterlake_$scenario.xml"
sidecar="$out_dir/provenance.txt"

for f in "$src_modules" "$src_tracking" "$src_full"; do
  [[ -f "$f" ]] || { echo "ERROR: installed file not found: $f" >&2; exit 2; }
done
# The scenario directory must be installed (cmake --install copies *.csv and *_metadata.txt).
[[ -d "$scenario_dir" ]] || { echo "ERROR: scenario not installed: $scenario_dir" >&2; exit 2; }
n_csv=$(find "$scenario_dir" -maxdepth 1 -name '*_modules.csv' | wc -l)
(( n_csv > 0 )) || { echo "ERROR: no *_modules.csv in $scenario_dir" >&2; exit 2; }

old_component="$delivery/$source_scenario"
new_component="$delivery/$scenario"
n_src_placements=$(grep 'module_placements' "$src_modules" | grep -c "$old_component\"" || true)
(( n_src_placements > 0 )) || {
  echo "ERROR: installed $src_modules has no module_placements selecting $old_component" >&2; exit 2; }
(( n_src_placements == 6 )) || echo "WARNING: expected 6 module_placements with $old_component, found $n_src_placements" >&2

include_old='${DETECTOR_PATH}/compact/tracking/silicon_disks_modules.xml'
for f in "$src_tracking" "$src_full"; do
  n=$(grep -cF "$include_old" "$f" || true)
  [[ "$n" -eq 1 ]] || { echo "ERROR: expected 1 include of $include_old in $f, found $n" >&2; exit 2; }
done

mkdir -p "$out_dir"
# Replace the scenario path component only where it is a whole component
# (followed by '"' or '/'), so e.g. rsu_opt_old would not be touched.
sed -E "s#${old_component}([\"/])#${new_component}\\1#g" "$src_modules" > "$out_modules.tmp"
n_left=$(grep -c "$old_component[\"/]" "$out_modules.tmp" || true)
n_new_placements=$(grep 'module_placements' "$out_modules.tmp" | grep -c "$new_component\"" || true)
n_new_total=$(grep -c "$new_component[\"/]" "$out_modules.tmp" || true)
[[ "$n_left" -eq 0 && "$n_new_placements" -eq "$n_src_placements" ]] || {
  echo "ERROR: replacement incomplete (left=$n_left, new placements=$n_new_placements)" >&2; exit 1; }
mv "$out_modules.tmp" "$out_modules"

for pair in "$src_tracking:$out_tracking" "$src_full:$out_full"; do
  src="${pair%%:*}"; dst="${pair#*:}"
  # '|' delimiter (paths contain no '|'); the escaped '$' matches ${DETECTOR_PATH} literally.
  sed "s|\\\${DETECTOR_PATH}/compact/tracking/silicon_disks_modules.xml|$out_modules|" "$src" > "$dst.tmp"
  grep -qF "\"$out_modules\"" "$dst.tmp" || { echo "ERROR: include not redirected in $dst" >&2; exit 1; }
  mv "$dst.tmp" "$dst"
done

{
  echo "Generated: $(date -u --iso-8601=seconds) by $here/make_svt_scenario_overlay_step11d.sh $scenario"
  echo "EPIC checkout: $epic_root"
  echo "EPIC commit: $(git -C "$epic_root" rev-parse HEAD) ($(git -C "$epic_root" rev-parse --abbrev-ref HEAD))"
  echo "EPIC tracked changes (git status --short --untracked-files=no):"
  git -C "$epic_root" status --short --untracked-files=no | sed 's/^/  /'
  echo "DETECTOR_PATH: $detector_path   (load the overlay with this DETECTOR_PATH)"
  echo "Replacement: $old_component -> $new_component"
  echo "  module_placements replaced: $n_new_placements; all occurrences now pointing at $new_component: $n_new_total"
  echo "Scenario directory: $scenario_dir ($n_csv *_modules.csv files)"
  echo "source sha256:"
  sha256sum "$src_modules" "$src_tracking" "$src_full" | sed 's/^/  /'
  echo "scenario CSV/metadata sha256 (combined over sorted file list):"
  echo "  $( (cd "$scenario_dir" && find . -maxdepth 1 -type f | sort | xargs sha256sum) | sha256sum | cut -d' ' -f1)  $scenario_dir"
  echo "output sha256:"
  sha256sum "$out_modules" "$out_tracking" "$out_full" | sed 's/^/  /'
} > "$sidecar"

echo "Wrote $out_modules"
echo "Wrote $out_tracking"
echo "Wrote $out_full"
echo "Wrote $sidecar"
