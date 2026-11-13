#!/usr/bin/env bash
# Step 11e: Geant4 overlap check (CI tolerance 0.1 mm) on the tracking-only geometry
# for one 20261110_ES scenario. Run INSIDE eic-shell 26.09.0-stable after
# check_svt_20261110_step11d.sh built/installed the geometry, e.g.
#   sbatch proj_svt_disk_tiling/logs/submit_svt_20261110_geant_step11e.sh        (both scenarios)
#   proj_svt_disk_tiling/refplanes/eic_exec.sh "bash <this script> rsu6"           (interactive)
# Scenarios: rsu_opt -> installed epic_craterlake_tracking_only.xml
#            rsu6    -> overlay XML (regenerated here from the current install)
set -euo pipefail

[[ $# -eq 1 ]] || { echo "Usage: $0 <rsu_opt|rsu6>" >&2; exit 2; }
scenario="$1"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
proj="$repo_root/proj_svt_disk_tiling"
log_file="$proj/logs/check_svt_20261110_geant_step11e_$scenario.txt"
raw_log="$proj/logs/check_svt_20261110_geant_raw_step11e_$scenario.txt"
source_xml="$repo_root/compact/tracking/silicon_disks_modules.xml"
installed_xml="$repo_root/install/share/epic/compact/tracking/silicon_disks_modules.xml"
installed_lib="$repo_root/install/lib/libepic.so"

# Guard: the install must match the current source (built by check_svt_20261110_step11d.sh).
if [[ ! -f "$installed_xml" ]] || ! cmp -s "$source_xml" "$installed_xml"; then
  echo "ERROR: installed silicon_disks_modules.xml does not match source; rerun step 11d." >&2; exit 1
fi
if [[ "$repo_root/src/SiEndcapModuleTracker_geo.cpp" -nt "$installed_lib" ]]; then
  echo "ERROR: SiEndcapModuleTracker_geo.cpp is newer than $installed_lib; rerun step 11d." >&2; exit 1
fi

exec > >(tee "$log_file") 2>&1
printf 'SVT step 11e Geant4 overlap check (%s): %s\n' "$scenario" "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
printf 'Repository: %s (commit %s + working tree)\n' "$repo_root" "$(git -C "$repo_root" rev-parse --short HEAD)"
set +u; source "$repo_root/install/bin/thisepic.sh"; set -u

case "$scenario" in
  rsu_opt) xml="$DETECTOR_PATH/epic_craterlake_tracking_only.xml" ;;
  *)
    bash "$proj/logs/make_svt_scenario_overlay_step11d.sh" "$scenario"
    xml="$proj/tmp/scenario_overlay/$scenario/epic_craterlake_tracking_only_$scenario.xml"
    sed 's/^/  /' "$proj/tmp/scenario_overlay/$scenario/provenance.txt"
    ;;
esac
test -f "$xml"
printf 'Detector configuration: %s\nRaw Geant4 log: %s\n' "$xml" "$raw_log"

# Run from a scratch dir so the relative module_placements path resolves via $DETECTOR_PATH
# (installed CSVs) and any files written by the check stay out of the repo root.
work_dir="$proj/tmp/geant_step11e_$scenario"
mkdir -p "$work_dir"
cd "$work_dir"
start_s=$(date +%s)
geant_status=0
python "$repo_root/scripts/checkOverlaps.py" -t 0.1 -c "$xml" > "$raw_log" 2>&1 || geant_status=$?
printf 'checkOverlaps.py exit status: %s, wall time: %d min\n' "$geant_status" $(( ($(date +%s) - start_s) / 60 ))

geant_count="$(grep -c 'GeomVol1002' "$raw_log" || true)"
exception_count="$(grep -c 'G4Exception' "$raw_log" || true)"
skip_count="$(grep -ci 'skipping module' "$raw_log" || true)"
printf 'Geant4 GeomVol1002 overlap warnings: %s\nG4Exception lines: %s\nskipping-module lines: %s\n' \
  "$geant_count" "$exception_count" "$skip_count"
if ! grep -q 'Geometry overlaps check completed' "$raw_log"; then
  tail -30 "$raw_log"
  printf 'RESULT: FAIL (%s: overlap check did not complete)\n' "$scenario"
  exit 1
fi
if (( geant_count > 0 || exception_count > 0 || geant_status != 0 )); then
  grep -A6 'GeomVol1002' "$raw_log" | head -80 || true
  printf 'RESULT: FAIL (%s)\n' "$scenario"
  exit 1
fi
printf 'RESULT: PASS (%s: no Geant4 overlaps at 0.1 mm)\n' "$scenario"
