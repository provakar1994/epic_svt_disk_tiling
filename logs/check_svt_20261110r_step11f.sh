#!/usr/bin/env bash
# Step 11f: build/install and ROOT checks for the "-r" package 20261110-r_ES (all module facings
# flipped; systematic studies). Production XML is NOT changed (still 20261110_ES/rsu_opt); both
# -r scenarios are loaded through overlays made by make_svt_overlay.sh.
# Run INSIDE eic-shell 26.09.0-stable (e.g. refplanes/eic_exec.sh "bash <this script>").
# Do not run while a Geant4 job is reading install/ (cmake --install rewrites it).
#   1. configure/build/install (same as step 8q/11d); check both -r scenarios got installed
#   2. overlays 20261110-r_ES/{rsu_opt,rsu6} (tracking-only + full craterlake)
#   3. per scenario: dd_web_display export, builder warnings, placed-module count and
#      prototype stacks (inspect_svt_export_step11d.py), ROOT checkOverlaps (option m, 0.01 mm)
#      on tracking-only AND full craterlake
# Report: logs/check_svt_20261110r_step11f.txt; run dir tmp/svt_20261110r_step11f_<stamp>/.
# Next: sbatch logs/submit_svt_geant_step11f.sh (Geant4, 0.1 mm), make_svt_visualize.sh.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
proj="$repo_root/proj_svt_disk_tiling"
log_file="$proj/logs/check_svt_20261110r_step11f.txt"
run_stamp="$(date -u '+%Y%m%dT%H%M%SZ')"
report_dir="$proj/tmp/svt_20261110r_step11f_$run_stamp"
mkdir -p "$report_dir"
delivery="20261110-r_ES"
declare -A expected_modules=([rsu_opt]=2164 [rsu6]=2150)

exec > >(tee "$log_file") 2>&1
printf 'SVT step 11f %s build + ROOT checks: %s\n' "$delivery" "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
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
for scen in rsu_opt rsu6; do
  n=$(find "$DETECTOR_PATH/compact/tracking/silicon_disks_tiling/$delivery/$scen" -maxdepth 1 -name '*_modules.csv' 2>/dev/null | wc -l)
  if (( n == 10 )); then record "installed $delivery/$scen" PASS "10 *_modules.csv"
  else record "installed $delivery/$scen" FAIL "$n *_modules.csv"; fi
done

# ---- 2. Overlays --------------------------------------------------------------------
for scen in rsu_opt rsu6; do
  if bash "$proj/logs/make_svt_overlay.sh" "$delivery" "$scen" > "$report_dir/overlay_$scen.log" 2>&1; then
    record "overlay $scen" PASS "$proj/tmp/scenario_overlay/${delivery}_$scen"
  else
    record "overlay $scen" FAIL "see $report_dir/overlay_$scen.log"
  fi
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

for scen in rsu_opt rsu6; do
  odir="$proj/tmp/scenario_overlay/${delivery}_$scen"
  xml="$odir/epic_craterlake_tracking_only_${delivery}_$scen.xml"
  full_xml="$odir/epic_craterlake_${delivery}_$scen.xml"
  printf '\n== %s/%s: %s\n' "$delivery" "$scen" "$xml"
  disp_log="$report_dir/dd_web_display_$scen.log"
  root_file="$report_dir/epic_craterlake_tracking_only_r_$scen.root"
  if dd_web_display -o "$root_file" --export "$xml" > "$disp_log" 2>&1 && [[ -s "$root_file" ]]; then
    record "export $scen" PASS "$root_file"
  else
    record "export $scen" FAIL "see $disp_log"; tail -20 "$disp_log"
  fi
  n_warn=$(grep 'SiEndcapModuleTracker' "$disp_log" | grep -ci 'warn' || true)
  n_skip=$(grep -ci 'skipping module' "$disp_log" || true)
  if (( n_warn == 0 && n_skip == 0 )); then record "builder warnings $scen" PASS "0 warnings, 0 skipping-module"
  else record "builder warnings $scen" FAIL "$n_warn warnings, $n_skip skipping-module"; fi
  if [[ -s "$root_file" ]]; then
    python3 "$proj/logs/inspect_svt_export_step11d.py" "$root_file" > "$report_dir/inspect_$scen.txt" 2>&1 || true
    placed="$(grep -o 'placed tiling modules: [0-9]*' "$report_dir/inspect_$scen.txt" | grep -o '[0-9]*$' || echo 0)"
    if [[ "$placed" == "${expected_modules[$scen]}" ]]; then
      record "placed modules $scen" PASS "$placed (= delivery)"
    else
      record "placed modules $scen" FAIL "$placed placed, delivery has ${expected_modules[$scen]}"
    fi
    grep 'placed tiling modules' "$report_dir/inspect_$scen.txt" || true
  fi
  root_overlaps "tracking_r_$scen" "$xml"
  root_overlaps "craterlake_r_$scen" "$full_xml"
done

# ---- Summary ------------------------------------------------------------------------
printf '\n===== Step 11f summary (%s) =====\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
printf '%-40s %-5s %s\n' "check" "status" "detail"
for line in "${results[@]}"; do
  IFS='|' read -r name status detail <<< "$line"
  printf '%-40s %-5s %s\n' "$name" "$status" "$detail"
done
printf 'Report directory: %s\n' "$report_dir"
if (( n_fail > 0 )); then printf 'RESULT: FAIL (%d failed checks)\n' "$n_fail"; exit 1; fi
printf '%s\n' 'RESULT: COMPLETE (next: sbatch logs/submit_svt_geant_step11f.sh)'
