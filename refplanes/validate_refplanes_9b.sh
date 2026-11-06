#!/usr/bin/env bash
# Step 9b runner (v2): generate the overlay XML, write plane_map.csv from the evaluated
# geometry (container), run the static validator and the point-sampling clearance check
# (container). Reports: validate_refplanes_9b.txt, plane_clearance_9a_crosscheck.txt
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
{
  echo "Started: $(date -u --iso-8601=seconds)"
  echo "== make_refplanes_xml.sh =="
  DETECTOR_PATH=/global/cfs/cdirs/m3763/pdatta/epic/install/share/epic "$here/make_refplanes_xml.sh"; echo "exit status: $?"
  cat "$here/generated/epic_craterlake_tracking_only_refplanes.provenance.txt"
  echo "== make_plane_map.py (container) =="
  "$here/eic_exec.sh" "python3 $here/make_plane_map.py" 2>&1 | grep -v "Info in\|INFO\|envelope26"; echo "exit status: ${PIPESTATUS[0]}"
  echo "== validate_refplanes_9b.py (container) =="
  "$here/eic_exec.sh" "python3 $here/validate_refplanes_9b.py" 2>&1 | grep -v "Info in\|INFO\|envelope26"; echo "exit status: ${PIPESTATUS[0]}"
  echo "Finished: $(date -u --iso-8601=seconds)"
} > "$here/validate_refplanes_9b.txt" 2>&1
"$here/plane_clearance_9a_crosscheck.sh"
