#!/usr/bin/env bash
# Step 11d: build/install the 20261110_ES delivery and run the ROOT checks for both scenarios.
# Run INSIDE eic-shell 26.09.0-stable, e.g. from the host:
#   proj_svt_disk_tiling/refplanes/eic_exec.sh "bash /global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/logs/check_svt_20261110_step11d.sh"
#
# 1. Static validators (validate_svt_delivery_20261110_step11c.py, git diff --check).
# 2. Configure/build/install like Step 8q.
# 3. Installed silicon_disks_modules.xml must select 20261110_ES/rsu_opt and have
#    SiEndcapTilingRSUInactiveSi_thickness = 33.5*um.
# 4. Generate the rsu6 overlay (make_svt_scenario_overlay_step11d.sh rsu6).
# 5. Per scenario (rsu_opt: installed tracking-only XML; rsu6: overlay tracking-only XML):
#    dd_web_display export (ROOT file kept in the report dir), SiEndcapModuleTracker
#    warning / 'skipping module' counts, ROOT checkOverlaps (option m, 0.01 mm).
#    Plus ROOT checkOverlaps on the full epic_craterlake.xml for rsu_opt.
# A failing check is recorded and the script continues; exit status is nonzero if
# anything failed. Only a failed build/install stops the script early.
# Next: submit_svt_20261110_geant_step11e.sh and make_svt_visual_root_step11e.sh.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
proj="$repo_root/proj_svt_disk_tiling"
log_file="$proj/logs/check_svt_20261110_step11d.txt"
run_stamp="$(date -u '+%Y%m%dT%H%M%SZ')"
report_dir="$proj/tmp/svt_20261110_step11d_$run_stamp"
mkdir -p "$report_dir"

exec > >(tee "$log_file") 2>&1
trap 'status=$?; printf "Stopped at line %s (exit %s); inspect %s\n" "$LINENO" "$status" "$report_dir" >&2' ERR
printf 'SVT step 11d 20261110_ES delivery build + ROOT checks: %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
printf 'Repository: %s (commit %s + working tree)\n' "$repo_root" "$(git -C "$repo_root" rev-parse --short HEAD)"
printf 'Report directory: %s\n' "$report_dir"
command -v dd_web_display >/dev/null || { printf 'ERROR: run inside the 26.09.0-stable EIC shell.\n' >&2; exit 2; }
cd "$repo_root"

# Results: one "name|status|detail" line per check, printed as a table at the end.
results=()
n_fail=0
record() {  # record <check> <PASS|FAIL|SKIP|INFO> <detail>
  results+=("$1|$2|$3")
  if [[ "$2" == FAIL ]]; then n_fail=$((n_fail + 1)); fi
  printf '[%s] %s: %s\n' "$2" "$1" "$3"
}

# ---- 1. Static checks -------------------------------------------------------------
validator="$proj/logs/validate_svt_delivery_20261110_step11c.py"
if [[ -f "$validator" ]]; then
  if python3 -B "$validator" > "$report_dir/validate_step11c.log" 2>&1; then
    record "validator step11c" PASS "$(tail -1 "$report_dir/validate_step11c.log")"
  else
    record "validator step11c" FAIL "see $report_dir/validate_step11c.log"
    tail -20 "$report_dir/validate_step11c.log"
  fi
else
  record "validator step11c" SKIP "not found: $validator"
fi
if git diff --check > "$report_dir/git_diff_check.log" 2>&1; then
  record "git diff --check" PASS "clean"
else
  record "git diff --check" FAIL "see $report_dir/git_diff_check.log"
  head -20 "$report_dir/git_diff_check.log"
fi

# ---- 2. Configure/build/install (abort on failure) ---------------------------------
printf 'Configure/build/install; logs in %s\n' "$report_dir"
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=install -DEPIC_ECCE_LEGACY_COMPAT=OFF > "$report_dir/configure.log" 2>&1
cmake --build build -j8 > "$report_dir/build.log" 2>&1
cmake --install build > "$report_dir/install.log" 2>&1
set +u; source "$repo_root/install/bin/thisepic.sh"; set -u
record "build/install" PASS "DETECTOR_PATH=$DETECTOR_PATH"

# ---- 3. Installed production XML ---------------------------------------------------
installed_modules="$DETECTOR_PATH/compact/tracking/silicon_disks_modules.xml"
n_sel=$(grep 'module_placements' "$installed_modules" | grep -c '20261110_ES/rsu_opt"' || true)
n_mp=$(grep -c '<module_placements' "$installed_modules" || true)
if (( n_sel == 6 && n_sel == n_mp )); then
  record "installed selects 20261110_ES/rsu_opt" PASS "$n_sel/$n_mp module_placements"
else
  record "installed selects 20261110_ES/rsu_opt" FAIL "$n_sel of $n_mp module_placements (expected 6/6)"
fi
if grep -Eq 'name="SiEndcapTilingRSUInactiveSi_thickness"[[:space:]]+value="33\.5\*um"' "$installed_modules"; then
  record "inactive Si 33.5*um" PASS "installed constant found"
else
  record "inactive Si 33.5*um" FAIL "$(grep 'SiEndcapTilingRSUInactiveSi_thickness' "$installed_modules" | head -1 | sed 's/^ *//')"
fi
if cmp -s "$repo_root/compact/tracking/silicon_disks_modules.xml" "$installed_modules"; then
  record "installed == source XML" PASS "cmp identical"
else
  record "installed == source XML" FAIL "installed silicon_disks_modules.xml differs from source"
fi
for scen in rsu_opt rsu6; do
  d="$DETECTOR_PATH/compact/tracking/silicon_disks_tiling/20261110_ES/$scen"
  n=$(find "$d" -maxdepth 1 -name '*_modules.csv' 2>/dev/null | wc -l)
  if (( n == 10 )); then record "installed $scen CSVs" PASS "$n *_modules.csv"
  else record "installed $scen CSVs" FAIL "$n *_modules.csv in $d (expected 10)"; fi
done

# ---- 4. rsu6 overlay -------------------------------------------------------------
overlay_dir="$proj/tmp/scenario_overlay/rsu6"
if bash "$proj/logs/make_svt_scenario_overlay_step11d.sh" rsu6 > "$report_dir/overlay_rsu6.log" 2>&1; then
  cp "$overlay_dir/provenance.txt" "$report_dir/overlay_rsu6_provenance.txt"
  record "rsu6 overlay" PASS "$overlay_dir"
else
  record "rsu6 overlay" FAIL "see $report_dir/overlay_rsu6.log"
  cat "$report_dir/overlay_rsu6.log"
fi

# ---- 5. Per-scenario export + ROOT overlaps ----------------------------------------
# Run from the report dir, not the repo root: resolve_input_file() tries the relative
# module_placements path against the current directory before $DETECTOR_PATH, so this
# makes the checks read the INSTALLED CSVs.
cd "$report_dir"

root_overlaps() {  # root_overlaps <label> <xml>; checkOverlaps option m, 0.01 mm
  local label="$1" xml="$2" log="$report_dir/root_overlap_$1.log" count illegal
  if [[ ! -f "$xml" ]]; then record "ROOT overlaps $label" FAIL "missing $xml"; return; fi
  if ! checkOverlaps --option m --tolerance 0.01 -c "$xml" > "$log" 2>&1; then
    record "ROOT overlaps $label" FAIL "checkOverlaps exit nonzero; see $log"
    tail -20 "$log"; return
  fi
  count="$(grep -c 'ovlp' "$log" || true)"
  illegal="$(grep -E 'Number of illegal overlaps/extrusions' "$log" | tail -1 | sed 's/.*: *//')"
  if (( count == 0 )); then
    record "ROOT overlaps $label" PASS "0 ovlp lines (illegal=${illegal:-?})"
  else
    record "ROOT overlaps $label" FAIL "$count ovlp lines (illegal=${illegal:-?}); see $log"
    grep 'ovlp' "$log" | head -40
  fi
}

declare -A scenario_xml=(
  [rsu_opt]="$DETECTOR_PATH/epic_craterlake_tracking_only.xml"
  [rsu6]="$overlay_dir/epic_craterlake_tracking_only_rsu6.xml"
)
for scen in rsu_opt rsu6; do
  xml="${scenario_xml[$scen]}"
  printf '\n== Scenario %s: %s\n' "$scen" "$xml"
  if [[ ! -f "$xml" ]]; then
    record "export $scen" FAIL "missing $xml"
    record "ROOT overlaps tracking_$scen" FAIL "missing $xml"
    continue
  fi
  disp_log="$report_dir/dd_web_display_$scen.log"
  root_file="$report_dir/epic_craterlake_tracking_only_$scen.root"
  if dd_web_display -o "$root_file" --export "$xml" > "$disp_log" 2>&1 && [[ -s "$root_file" ]]; then
    record "export $scen" PASS "$root_file"
  else
    record "export $scen" FAIL "see $disp_log"
    tail -20 "$disp_log"
  fi
  # Builder diagnostics. A module rejected by the disk boundary throws for tiling
  # coordinates (export fails); the layer-z check only warns with 'skipping module'.
  n_warn=$(grep 'SiEndcapModuleTracker' "$disp_log" | grep -ci 'warn' || true)
  n_skip=$(grep -ci 'skipping module' "$disp_log" || true)
  placed=$(grep -iE 'placed [0-9]+ modules|[0-9]+ modules placed' "$disp_log" | sed 's/^ *//' | head -12 || true)
  if (( n_warn == 0 && n_skip == 0 )); then
    record "builder warnings $scen" PASS "0 SiEndcapModuleTracker warnings, 0 skipping-module"
  else
    record "builder warnings $scen" FAIL "$n_warn SiEndcapModuleTracker warnings, $n_skip skipping-module"
    grep 'SiEndcapModuleTracker' "$disp_log" | grep -i 'warn' | head -30
  fi
  if [[ -n "$placed" ]]; then
    printf 'Placed-module printout (%s):\n%s\n' "$scen" "$placed"
    record "placed modules $scen" INFO "$(printf '%s\n' "$placed" | wc -l) printout lines; see $disp_log"
  else
    record "placed modules $scen" INFO "not printed by the builder"
  fi
  root_overlaps "tracking_$scen" "$xml"
done

printf '\n== Full craterlake (rsu_opt)\n'
root_overlaps "craterlake_rsu_opt" "$DETECTOR_PATH/epic_craterlake.xml"

# ---- Summary -----------------------------------------------------------------------
printf '\n===== Step 11d summary (%s) =====\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
printf '%-40s %-5s %s\n' "check" "status" "detail"
for line in "${results[@]}"; do
  IFS='|' read -r name status detail <<< "$line"
  printf '%-40s %-5s %s\n' "$name" "$status" "$detail"
done
printf 'Report directory: %s\n' "$report_dir"
if (( n_fail > 0 )); then
  printf 'RESULT: FAIL (%d failed checks)\n' "$n_fail"
  exit 1
fi
printf '%s\n' 'RESULT: COMPLETE (review exports, then sbatch submit_svt_20261110_geant_step11e.sh)'
