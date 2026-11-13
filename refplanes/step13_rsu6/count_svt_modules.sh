#!/usr/bin/env bash
# Step 14b: module-count proof of the loaded scenario (rsu6 2150, rsu_opt 2164), with the same
# container, DETECTOR_PATH and CWD (step13_rsu6/) as the gates. Report: count_svt_modules.txt
#   1. rsu6 refplane overlay (generated/epic_craterlake_tracking_only_rsu6_refplanes.xml)  -> 2150
#   2. rsu6 tracking-only overlay (geometry_overlays/step13/rsu6/)                          -> 2150
#   3. installed production XML (rsu_opt), contrast                                         -> 2164
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
epic=/global/cfs/cdirs/m3763/pdatta/epic
{
  echo "Started: $(date -u --iso-8601=seconds)"
  "$here/identity_check_step13_rsu6.sh" | tail -1
  for pair in "$here/generated/epic_craterlake_tracking_only_rsu6_refplanes.xml:2150" \
              "$epic/proj_svt_disk_tiling/geometry_overlays/step13/rsu6/epic_craterlake_tracking_only_rsu6.xml:2150" \
              "$epic/install/share/epic/epic_craterlake_tracking_only.xml:2164"; do
    "$here/eic_exec_rsu6.sh" "python3 $here/count_svt_modules.py ${pair%%:*} ${pair##*:}" 2>&1 | grep -E "modules|Geometry"
    echo "exit status: ${PIPESTATUS[0]}"
  done
  echo "Finished: $(date -u --iso-8601=seconds)"
} > "$here/count_svt_modules.txt" 2>&1
grep -E "total|exit" "$here/count_svt_modules.txt"
