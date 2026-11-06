#!/usr/bin/env bash
# Run inside eic-shell 26.09.0-stable from any directory.
# Step 8q: validate and build the rounded (R = 5 mm mid-surface) corrugation
# bends, export the tracking-only geometry for visual review, and run the
# deterministic ROOT overlap check (CI settings: option m, 0.01 mm) on the
# tracking-only and full craterlake configurations.
# Next, after visual review: check_svt_rounded_bends_geant_step8q.sh
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
log_file="$repo_root/proj_svt_disk_tiling/logs/check_svt_rounded_bends_step8q.txt"
run_stamp="$(date -u '+%Y%m%dT%H%M%SZ')"
report_dir="$repo_root/proj_svt_disk_tiling/tmp/rounded_bends_step8q_$run_stamp"
mkdir -p "$report_dir"

exec > >(tee "$log_file") 2>&1
trap 'status=$?; printf "Stopped at line %s (exit %s); inspect %s\n" "$LINENO" "$status" "$report_dir" >&2' ERR
printf 'SVT step 8q rounded corrugation bends: %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
printf 'Repository: %s (commit %s + working tree)\n' "$repo_root" "$(git -C "$repo_root" rev-parse --short HEAD)"
printf 'Report directory: %s\n' "$report_dir"
cd "$repo_root"

# Static checks: the new bend validator plus the earlier corrugation/placement validators.
python3 proj_svt_disk_tiling/logs/validate_svt_rounded_bends_step8q.py
python3 proj_svt_disk_tiling/logs/validate_svt_closed_corrugation_y_gaps_step8i.py
python3 proj_svt_disk_tiling/logs/validate_svt_central_corrugation_web_step8h.py
python3 proj_svt_disk_tiling/logs/validate_svt_restored_corrugation_step8g.py
python3 proj_svt_disk_tiling/logs/validate_svt_module_z_offsets_step8f.py
python3 proj_svt_disk_tiling/logs/validate_svt_explicit_corrugation_builder_step7c.py
python3 proj_svt_disk_tiling/logs/validate_svt_corrugation_lattice_step7b.py
python3 proj_svt_disk_tiling/logs/audit_svt_epoxy_facet_y_step8b.py
python3 proj_svt_disk_tiling/logs/validate_svt_placement_transform_step5b.py
git diff --check

printf 'Configure/build/install; logs in %s\n' "$report_dir"
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=install -DEPIC_ECCE_LEGACY_COMPAT=OFF > "$report_dir/configure.log" 2>&1
cmake --build build -j4 > "$report_dir/build.log" 2>&1
cmake --install build > "$report_dir/install.log" 2>&1
source "$repo_root/install/bin/thisepic.sh"

tracking_xml="$DETECTOR_PATH/epic_craterlake_tracking_only.xml"
full_xml="$DETECTOR_PATH/epic_craterlake.xml"
test -f "$tracking_xml"
test -f "$full_xml"
grep -q 'bend_radius="SiEndcapCorrugation_bend_radius"' \
  "$repo_root/install/share/epic/compact/tracking/silicon_disks_modules.xml"

# Export for visual review; geometry warnings from the frame builder must be absent.
dd_web_display --export "$tracking_xml" > "$report_dir/dd_web_display.log" 2>&1
if grep -E "corrugat|bend_radius" "$report_dir/dd_web_display.log" | grep -i "warn\|skipping"; then
  printf 'ERROR: corrugation builder warnings during export (see above)\n' >&2
  exit 1
fi
printf 'Exported files:\n'; ls -1t ./*.root 2>/dev/null | head -2 || true

for config in "$tracking_xml" "$full_xml"; do
  name="$(basename "$config" .xml)"
  checkOverlaps --option m --tolerance 0.01 -c "$config" > "$report_dir/root_overlap_$name.log" 2>&1
  count="$(grep -c 'ovlp' "$report_dir/root_overlap_$name.log" || true)"
  printf 'ROOT overlap lines (%s, 0.01 mm): %s\n' "$name" "$count"
  grep -E "illegal overlaps|Number of illegal" "$report_dir/root_overlap_$name.log" | tail -2 || true
  if (( count > 0 )); then
    grep 'ovlp' "$report_dir/root_overlap_$name.log" | head -40
    printf 'RESULT: FAIL (ROOT overlaps in %s)\n' "$name"
    exit 1
  fi
done

printf '%s\n' 'VISUAL CHECK: flats, bends and webs form one smooth profile on every disk (edge-on view).'
printf '%s\n' 'VISUAL CHECK: bends are clipped like the flats/webs at the disk edge and beam-pipe openings.'
printf '%s\n' 'RESULT: COMPLETE (review visualization, then run check_svt_rounded_bends_geant_step8q.sh)'
