#!/usr/bin/env bash
# Step 12: build/install and ROOT checks after (a) building the corrugation from the delivered
# <disk>_rows.csv and (b) applying the FPC split (Kapton front, Al on the baseplate back) to
# outward modules too. Four geometries: 20261110_ES/{rsu_opt (installed), rsu6} and
# 20261110-r_ES/{rsu_opt, rsu6}, non-installed ones through make_svt_overlay.sh.
# Run INSIDE eic-shell 26.09.0-stable (e.g. refplanes/eic_exec.sh "bash <this script>").
# Do not run while a Geant4 job is reading install/ (cmake --install rewrites it).
# Per geometry: dd_web_display export, builder warnings, placed modules + prototype stacks
# (inspect_svt_export_step11d.py), corrugation pieces vs rows.csv (inspect_svt_corrugation_step12.py),
# ROOT checkOverlaps (option m, 0.01 mm) on tracking-only AND full craterlake.
# Report: logs/check_svt_step12.txt; run dir tmp/svt_step12_<stamp>/.
# Next: sbatch logs/submit_svt_geant_step12.sh, make_svt_visualize.sh step12 ...
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
proj="$repo_root/proj_svt_disk_tiling"
log_file="$proj/logs/check_svt_step12.txt"
run_stamp="$(date -u '+%Y%m%dT%H%M%SZ')"
report_dir="$proj/tmp/svt_step12_$run_stamp"
mkdir -p "$report_dir"
declare -A expected_modules=([rsu_opt]=2164 [rsu6]=2150)

exec > >(tee "$log_file") 2>&1
printf 'SVT step 12 build + ROOT checks: %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
printf 'Repository: %s (commit %s + working tree)\n' "$repo_root" "$(git -C "$repo_root" rev-parse --short HEAD)"
printf 'Report directory: %s\n' "$report_dir"
command -v dd_web_display >/dev/null || { printf 'ERROR: run inside the 26.09.0-stable EIC shell.\n' >&2; exit 2; }
cd "$repo_root"

results=()
n_fail=0
record() {  # record <check> <PASS|FAIL|SKIP|INFO> <detail>
  results+=("$1|$2|$3")
  if [[ "$2" == FAIL ]]; then n_fail=$((n_fail + 1)); fi
  printf '[%s] %s: %s\n' "$2" "$1" "$3"
}

# ---- 1. Build/install ---------------------------------------------------------------
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=install -DEPIC_ECCE_LEGACY_COMPAT=OFF > "$report_dir/configure.log" 2>&1
cmake --build build -j8 > "$report_dir/build.log" 2>&1
cmake --install build > "$report_dir/install.log" 2>&1
set +u; source "$repo_root/install/bin/thisepic.sh"; set -u
record "build/install" PASS "DETECTOR_PATH=$DETECTOR_PATH"
if cmp -s compact/tracking/silicon_disks_modules.xml "$DETECTOR_PATH/compact/tracking/silicon_disks_modules.xml"; then
  record "installed == source XML" PASS "production selection unchanged"
else
  record "installed == source XML" FAIL "installed silicon_disks_modules.xml differs from source"
fi
if grep -qE '^[[:space:]]*rowwise_placement="' "$DETECTOR_PATH/compact/tracking/silicon_disks_modules.xml"; then
  record "no legacy rowwise_placement" FAIL "installed XML still has a rowwise_placement attribute"
else
  record "no legacy rowwise_placement" PASS "frames read <disk>_rows.csv"
fi
geometries=(20261110_ES/rsu_opt 20261110_ES/rsu6 20261110-r_ES/rsu_opt 20261110-r_ES/rsu6)
for geo in "${geometries[@]}"; do
  n=$(ls "$DETECTOR_PATH/compact/tracking/silicon_disks_tiling/$geo/"*_rows.csv 2>/dev/null | wc -l)
  if (( n == 10 )); then record "installed $geo" PASS "10 *_rows.csv"
  else record "installed $geo" FAIL "$n *_rows.csv"; fi
done

# ---- 2. Overlays (private dir; label <scenario> for the installed delivery, else <delivery>_<scenario>)
overlay_root="$report_dir/overlay"
declare -A tracking_xml full_xml
for geo in "${geometries[@]}"; do
  delivery="${geo%/*}"; scen="${geo#*/}"; tag="${delivery}_$scen"
  if [[ "$geo" == 20261110_ES/rsu_opt ]]; then
    tracking_xml[$tag]="$DETECTOR_PATH/epic_craterlake_tracking_only.xml"
    full_xml[$tag]="$DETECTOR_PATH/epic_craterlake.xml"
    continue
  fi
  olabel="$scen"; [[ "$delivery" == 20261110_ES ]] || olabel="$tag"
  if OVERLAY_ROOT="$overlay_root" bash "$proj/logs/make_svt_overlay.sh" "$delivery" "$scen" > "$report_dir/overlay_$tag.log" 2>&1; then
    record "overlay $tag" PASS "$overlay_root/$olabel"
  else
    record "overlay $tag" FAIL "see $report_dir/overlay_$tag.log"
  fi
  tracking_xml[$tag]="$overlay_root/$olabel/epic_craterlake_tracking_only_$olabel.xml"
  full_xml[$tag]="$overlay_root/$olabel/epic_craterlake_$olabel.xml"
done

# ---- 3. Export + ROOT overlaps (from the report dir: CSVs resolve via $DETECTOR_PATH) ---
cd "$report_dir"
root_overlaps() {  # root_overlaps <label> <xml>
  local label="$1" xml="$2" log="$report_dir/root_overlap_$1.log" count illegal
  if [[ ! -f "$xml" ]]; then record "ROOT overlaps $label" FAIL "missing $xml"; return; fi
  if ! checkOverlaps --option m --tolerance 0.01 -c "$xml" > "$log" 2>&1; then
    record "ROOT overlaps $label" FAIL "checkOverlaps exit nonzero; see $log"; tail -20 "$log"; return
  fi
  count="$(grep -c 'ovlp' "$log" || true)"
  illegal="$(grep -E 'Number of illegal overlaps/extrusions' "$log" | tail -1 | sed 's/.*: *//')"
  if (( count == 0 )); then record "ROOT overlaps $label" PASS "0 ovlp lines (illegal=${illegal:-?})"
  else record "ROOT overlaps $label" FAIL "$count ovlp lines (illegal=${illegal:-?}); see $log"; grep 'ovlp' "$log" | head -40; fi
}

for geo in "${geometries[@]}"; do
  delivery="${geo%/*}"; scen="${geo#*/}"; tag="${delivery}_$scen"
  xml="${tracking_xml[$tag]}"
  printf '\n== %s: %s\n' "$geo" "$xml"
  disp_log="$report_dir/dd_web_display_$tag.log"
  root_file="$report_dir/epic_craterlake_tracking_only_$tag.root"
  if dd_web_display -o "$root_file" --export "$xml" > "$disp_log" 2>&1 && [[ -s "$root_file" ]]; then
    record "export $tag" PASS "$root_file"
  else
    record "export $tag" FAIL "see $disp_log"; tail -20 "$disp_log"
  fi
  n_warn=$(grep 'SiEndcapModuleTracker' "$disp_log" | grep -ci 'warn' || true)
  n_skip=$(grep -ci 'skipping module' "$disp_log" || true)
  if (( n_warn == 0 && n_skip == 0 )); then record "builder warnings $tag" PASS "0 warnings, 0 skipping-module"
  else record "builder warnings $tag" FAIL "$n_warn warnings, $n_skip skipping-module"; fi
  if [[ -s "$root_file" ]]; then
    python3 "$proj/logs/inspect_svt_export_step11d.py" "$root_file" > "$report_dir/inspect_$tag.txt" 2>&1 || true
    placed="$(grep -o 'placed tiling modules: [0-9]*' "$report_dir/inspect_$tag.txt" | grep -o '[0-9]*$' || echo 0)"
    if [[ "$placed" == "${expected_modules[$scen]}" ]]; then
      record "placed modules $tag" PASS "$placed (= delivery)"
    else
      record "placed modules $tag" FAIL "$placed placed, delivery has ${expected_modules[$scen]}"
    fi
    grep 'placed tiling modules' "$report_dir/inspect_$tag.txt" || true
    if python3 "$proj/logs/inspect_svt_corrugation_step12.py" "$root_file" \
         "$DETECTOR_PATH/compact/tracking/silicon_disks_tiling/$geo" > "$report_dir/corrugation_$tag.txt" 2>&1; then
      record "corrugation vs rows $tag" PASS "$(tail -1 "$report_dir/corrugation_$tag.txt")"
    else
      record "corrugation vs rows $tag" FAIL "see $report_dir/corrugation_$tag.txt"
      tail -15 "$report_dir/corrugation_$tag.txt"
    fi
  fi
  root_overlaps "tracking_$tag" "$xml"
  root_overlaps "craterlake_$tag" "${full_xml[$tag]}"
done

# ---- Summary ------------------------------------------------------------------------
printf '\n===== Step 12 summary (%s) =====\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
printf '%-40s %-5s %s\n' "check" "status" "detail"
for line in "${results[@]}"; do
  IFS='|' read -r name status detail <<< "$line"
  printf '%-40s %-5s %s\n' "$name" "$status" "$detail"
done
printf 'Report directory: %s\n' "$report_dir"
if (( n_fail > 0 )); then printf 'RESULT: FAIL (%d failed checks)\n' "$n_fail"; exit 1; fi
printf '%s\n' 'RESULT: COMPLETE (next: sbatch logs/submit_svt_geant_step12.sh)'
