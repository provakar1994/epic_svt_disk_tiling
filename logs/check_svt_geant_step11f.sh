#!/usr/bin/env bash
# Step 11f: generic Geant4 overlap check (CI tolerance 0.1 mm) on the tracking-only geometry
# for one <delivery> <scenario> (copy of check_svt_20261110_geant_step11e.sh). Run INSIDE
# eic-shell 26.09.0-stable after the geometry was built/installed, e.g.
#   sbatch proj_svt_disk_tiling/logs/submit_svt_geant_step11f.sh   (20261110-r_ES rsu_opt, rsu6)
#   proj_svt_disk_tiling/refplanes/eic_exec.sh "bash <this script> 20261110-r_ES rsu6"
# The installed production selection is used directly; anything else through
# make_svt_overlay.sh (regenerated here from the current install).
set -euo pipefail

[[ $# -eq 2 ]] || { echo "Usage: $0 <delivery> <scenario>" >&2; exit 2; }
delivery="$1"
scenario="$2"
label="${delivery}_$scenario"
# Step tag for output names (env GEANT_STEP; default step11f keeps the 11f file names).
step="${GEANT_STEP:-step11f}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
proj="$repo_root/proj_svt_disk_tiling"
log_file="$proj/logs/check_svt_geant_${step}_$label.txt"
raw_log="$proj/logs/check_svt_geant_raw_${step}_$label.txt"
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
printf 'SVT step 11f Geant4 overlap check (%s): %s\n' "$label" "$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
printf 'Repository: %s (commit %s + working tree)\n' "$repo_root" "$(git -C "$repo_root" rev-parse --short HEAD)"
set +u; source "$repo_root/install/bin/thisepic.sh"; set -u

if grep -q "silicon_disks_tiling/$delivery/$scenario\" format=\"tiling-directory\"" \
     "$DETECTOR_PATH/compact/tracking/silicon_disks_modules.xml"; then
  xml="$DETECTOR_PATH/epic_craterlake_tracking_only.xml"
else
  odir="$proj/tmp/geant_${step}_overlay"   # private overlay dir: no race with other scripts
  OVERLAY_ROOT="$odir" bash "$proj/logs/make_svt_overlay.sh" "$delivery" "$scenario"
  # make_svt_overlay.sh labels its output <scenario> for the installed delivery, else <delivery>_<scenario>.
  olabel="$scenario"; [[ "$delivery" == 20261110_ES ]] || olabel="$label"
  xml="$odir/$olabel/epic_craterlake_tracking_only_$olabel.xml"
  sed 's/^/  /' "$odir/$olabel/provenance.txt"
fi
test -f "$xml"
printf 'Detector configuration: %s\nRaw Geant4 log: %s\n' "$xml" "$raw_log"

# Run from a scratch dir so the relative module_placements path resolves via $DETECTOR_PATH
# (installed CSVs) and any files written by the check stay out of the repo root.
work_dir="$proj/tmp/geant_${step}_$label"
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
  printf 'RESULT: FAIL (%s: overlap check did not complete)\n' "$label"
  exit 1
fi
if (( geant_count > 0 || exception_count > 0 || geant_status != 0 )); then
  grep -A6 'GeomVol1002' "$raw_log" | head -80 || true
  printf 'RESULT: FAIL (%s)\n' "$label"
  exit 1
fi
printf 'RESULT: PASS (%s: no Geant4 overlaps at 0.1 mm)\n' "$label"
