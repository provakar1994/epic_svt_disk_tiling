#!/usr/bin/env bash
# Run inside eic-shell 26.09.0-stable after check_svt_rounded_bends_step8q.sh
# passed and the visualization was reviewed. Reuses that installed geometry
# and runs the Geant4 overlap check with the CI tolerance (0.1 mm) on the full
# craterlake configuration. This can take a long time.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
log_file="$repo_root/proj_svt_disk_tiling/logs/check_svt_rounded_bends_geant_step8q.txt"
build_log="$repo_root/proj_svt_disk_tiling/logs/check_svt_rounded_bends_step8q.txt"
source_xml="$repo_root/compact/tracking/silicon_disks_modules.xml"
installed_xml="$repo_root/install/share/epic/compact/tracking/silicon_disks_modules.xml"

# Guard: the installed geometry must be the one built and checked by the first script.
if [[ ! -f "$build_log" ]] || ! grep -q '^RESULT: COMPLETE' "$build_log"; then
  printf '%s\n' 'ERROR: run check_svt_rounded_bends_step8q.sh to completion first.' >&2
  exit 1
fi
for geometry_source in "$source_xml" "$repo_root/src/SiEndcapModuleTracker_geo.cpp"; do
  if [[ "$geometry_source" -nt "$build_log" ]]; then
    printf 'ERROR: %s is newer than the Step 8q build; rerun the first script.\n' "$geometry_source" >&2
    exit 1
  fi
done
if [[ ! -f "$installed_xml" ]] || ! cmp -s "$source_xml" "$installed_xml"; then
  printf '%s\n' 'ERROR: installed silicon_disks_modules.xml does not match source.' >&2
  exit 1
fi

exec > >(tee "$log_file") 2>&1
printf 'SVT step 8q Geant4 continuation: %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
cd "$repo_root"
source "$repo_root/install/bin/thisepic.sh"

full_xml="$DETECTOR_PATH/epic_craterlake.xml"
raw_log="$repo_root/proj_svt_disk_tiling/logs/check_svt_rounded_bends_geant_raw_step8q.txt"
printf 'Detector configuration: %s\nRaw Geant4 log: %s\n' "$full_xml" "$raw_log"
python scripts/checkOverlaps.py -t 0.1 -c "$full_xml" > "$raw_log" 2>&1
geant_count="$(grep -c 'GeomVol1002' "$raw_log" || true)"
exception_count="$(grep -c 'G4Exception' "$raw_log" || true)"
printf 'Geant4 GeomVol1002 overlap warnings: %s\nG4Exception lines: %s\n' "$geant_count" "$exception_count"
if (( geant_count > 0 )); then
  grep -A6 'GeomVol1002' "$raw_log" | head -80
  printf 'RESULT: FAIL\n'
  exit 1
fi
printf 'RESULT: PASS (no Geant4 overlaps at 0.1 mm)\n'
