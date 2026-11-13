#!/usr/bin/env bash
# Export a visualization ROOT file of the SVT endcap disks for one step/scenario:
#   dd_web_display -o proj_svt_disk_tiling/out/visualize_<step>[_<scenario>].root \
#     --export $DETECTOR_PATH/epic_craterlake_tracking_only_disk_tiles_new.xml
# (beam pipe + MARCO + silicon_disks_modules only; light-weight for viewing).
#
# Usage (host or inside eic-shell; on the host it re-runs itself via refplanes/eic_exec.sh):
#   bash proj_svt_disk_tiling/logs/make_svt_visualize.sh <step> [scenario]
#   e.g.  make_svt_visualize.sh step11b            # installed selection (rsu_opt)
#         make_svt_visualize.sh step11b rsu6       # 20261110_ES/rsu6 through an overlay XML
#         make_svt_visualize.sh step11f 20261110-r_ES/rsu6   # other delivery -> visualize_step11f_20261110-r_ES_rsu6.root
# The geometry is whatever is INSTALLED now (install/share/epic); rebuild first if the
# source changed. The scenario overlay copies the installed silicon_disks_modules.xml with the
# scenario path component replaced; nothing in the repo or install is modified.
# Outputs: out/visualize_<tag>.root, .log (dd_web_display output), .provenance.txt
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
proj="$(cd "$here/.." && pwd)"
epic_root="$(cd "$proj/.." && pwd)"

[[ $# -ge 1 && $# -le 2 ]] || { sed -n 2,13p "${BASH_SOURCE[0]}"; exit 2; }
step="$1"
scenario="${2:-}"

# Re-run inside the container when called from the host.
if ! command -v dd_web_display >/dev/null 2>&1; then
  exec "$proj/refplanes/eic_exec.sh" "bash $here/make_svt_visualize.sh $*"
fi

detector_path="${DETECTOR_PATH:-$epic_root/install/share/epic}"
base_xml="$detector_path/epic_craterlake_tracking_only_disk_tiles_new.xml"
modules_xml="$detector_path/compact/tracking/silicon_disks_modules.xml"
[[ -f "$base_xml" ]] || { echo "ERROR: $base_xml not installed" >&2; exit 2; }

# Installed delivery/scenario, e.g. 20261110_ES/rsu_opt (taken from the module_placements paths).
installed_sel="$(grep -o 'silicon_disks_tiling/[^/"]*/[^/"]*" format="tiling-directory"' "$modules_xml" \
                 | sed 's#silicon_disks_tiling/##; s#" format.*##' | sort -u)"
[[ "$(wc -l <<<"$installed_sel")" -eq 1 ]] || { echo "ERROR: mixed scenarios installed: $installed_sel" >&2; exit 2; }
delivery="${installed_sel%/*}"
installed_scenario="${installed_sel#*/}"

tag="$step"
xml="$base_xml"
# Optional "<delivery>/<scenario>" selects another installed delivery.
target_delivery="$delivery"
scenario_label="$scenario"
if [[ "$scenario" == */* ]]; then
  target_delivery="${scenario%/*}"
  scenario="${scenario#*/}"
  scenario_label="${target_delivery}_$scenario"
fi
if [[ -n "$scenario" && "$target_delivery/$scenario" != "$delivery/$installed_scenario" ]]; then
  [[ -d "$detector_path/compact/tracking/silicon_disks_tiling/$target_delivery/$scenario" ]] \
    || { echo "ERROR: $target_delivery/$scenario not installed" >&2; exit 2; }
  overlay_dir="$proj/tmp/scenario_overlay/$scenario_label"
  mkdir -p "$overlay_dir"
  overlay_modules="$overlay_dir/silicon_disks_modules_${scenario_label}_visualize.xml"
  sed "s#silicon_disks_tiling/$delivery/$installed_scenario\"#silicon_disks_tiling/$target_delivery/$scenario\"#g" \
    "$modules_xml" > "$overlay_modules"
  n_switched="$(grep -c "silicon_disks_tiling/$target_delivery/$scenario\" format=\"tiling-directory\"" "$overlay_modules" || true)"
  [[ "$n_switched" -eq 6 ]] || { echo "ERROR: switched $n_switched/6 module_placements" >&2; exit 2; }
  xml="$overlay_dir/epic_craterlake_tracking_only_disk_tiles_new_${scenario_label}.xml"
  sed "s#\${DETECTOR_PATH}/compact/tracking/silicon_disks_modules.xml#$overlay_modules#" "$base_xml" > "$xml"
  grep -q "$overlay_modules" "$xml" || { echo "ERROR: include not redirected" >&2; exit 2; }
fi
[[ -n "$scenario" ]] && tag="${step}_${scenario_label}"

out_dir="$proj/out"
mkdir -p "$out_dir"
root_file="$out_dir/visualize_${tag}.root"
log_file="$out_dir/visualize_${tag}.log"

# Run from out/ so relative CSV paths resolve through $DETECTOR_PATH (installed copies),
# not through the source tree (resolve_input_file tries the CWD first).
cd "$out_dir"
dd_web_display -o "$root_file" --export "$xml" > "$log_file" 2>&1
[[ -s "$root_file" ]] || { echo "ERROR: no output; see $log_file" >&2; exit 1; }
n_warn="$(grep -ci 'SiEndcapModuleTracker.*WARN\|skipping module' "$log_file" || true)"

{
  echo "created_utc = $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "step = $step"
  echo "selection = $target_delivery/${scenario:-$installed_scenario} (installed: $installed_sel)"
  echo "epic_commit = $(git -C "$epic_root" rev-parse --short HEAD) (+ uncommitted: $(git -C "$epic_root" status --porcelain -- src compact | wc -l) files in src/compact)"
  echo "detector_xml = $xml"
  echo "detector_xml_sha256 = $(sha256sum "$xml" | cut -c1-16)"
  echo "silicon_disks_modules_sha256 = $(sha256sum "${overlay_modules:-$modules_xml}" | cut -c1-16)"
  echo "builder_warnings = $n_warn"
  echo "root_file = $root_file"
} > "$out_dir/visualize_${tag}.provenance.txt"
cat "$out_dir/visualize_${tag}.provenance.txt"
