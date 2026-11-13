#!/usr/bin/env bash
# [Step 13 copy, 2026-11-12, of refplanes/validate_refplanes_9b.sh] Generate the Step 13 overlay XML
# (make_refplanes_xml_step13.sh -> step13/generated/), write step13/plane_map.csv from the evaluated
# geometry (container), compare it with the v3 refplanes/plane_map.csv, run the static validator and
# the point-sampling clearance cross-check (container).
# Reports: step13/validate_refplanes_9b.txt, step13/plane_clearance_9a_crosscheck.txt
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
{
  echo "Started: $(date -u --iso-8601=seconds)"
  "$here/identity_check_step13.sh"; echo "identity exit status: $?"
  echo "== make_refplanes_xml_step13.sh =="
  DETECTOR_PATH=/global/cfs/cdirs/m3763/pdatta/epic/install/share/epic "$here/make_refplanes_xml_step13.sh"; echo "exit status: $?"
  cat "$here/generated/epic_craterlake_tracking_only_refplanes.provenance.txt"
  echo "== make_plane_map.py (container) =="
  "$here/../eic_exec.sh" "python3 $here/make_plane_map.py" 2>&1 | grep -v "Info in\|INFO\|envelope26"; echo "exit status: ${PIPESTATUS[0]}"
  echo "== plane_map.csv: Step 13 vs v3 (refplanes/plane_map.csv) =="
  if cmp -s "$here/plane_map.csv" "$here/../plane_map.csv"; then
    echo "plane_map.csv IDENTICAL to v3 (sha256 $(sha256sum "$here/plane_map.csv" | cut -d' ' -f1))"
  else
    echo "plane_map.csv DIFFERS from v3:"; diff "$here/../plane_map.csv" "$here/plane_map.csv"
  fi
  echo "== validate_refplanes_9b.py (container) =="
  "$here/../eic_exec.sh" "python3 $here/validate_refplanes_9b.py" 2>&1 | grep -v "Info in\|INFO\|envelope26"; echo "exit status: ${PIPESTATUS[0]}"
  echo "Finished: $(date -u --iso-8601=seconds)"
} > "$here/validate_refplanes_9b.txt" 2>&1
"$here/plane_clearance_9a_crosscheck.sh"
