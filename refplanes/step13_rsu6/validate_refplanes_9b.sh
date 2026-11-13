#!/usr/bin/env bash
# [Step 14b rsu6 copy (2026-11-13): rsu6 overlay geometry_overlays/step13/rsu6/, container via eic_exec_rsu6.sh (CWD step13_rsu6/), identity_check_step13_rsu6.sh. Of the Step 13 copy, 2026-11-12, of refplanes/validate_refplanes_9b.sh] Generate the Step 13 overlay XML
# (make_refplanes_xml_step13_rsu6.sh -> step13/generated/), write step13/plane_map.csv from the evaluated
# geometry (container), compare it with the v3 refplanes/plane_map.csv, run the static validator and
# the point-sampling clearance cross-check (container).
# Reports: step13/validate_refplanes_9b.txt, step13/plane_clearance_9a_crosscheck.txt
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
{
  echo "Started: $(date -u --iso-8601=seconds)"
  "$here/identity_check_step13_rsu6.sh"; echo "identity exit status: $?"
  echo "== make_refplanes_xml_step13_rsu6.sh =="
  DETECTOR_PATH=/global/cfs/cdirs/m3763/pdatta/epic/install/share/epic "$here/make_refplanes_xml_step13_rsu6.sh"; echo "exit status: $?"
  cat "$here/generated/epic_craterlake_tracking_only_rsu6_refplanes.provenance.txt"
  echo "== make_plane_map.py (container) =="
  "$here/eic_exec_rsu6.sh" "python3 $here/make_plane_map.py" 2>&1 | grep -v "Info in\|INFO\|envelope26"; echo "exit status: ${PIPESTATUS[0]}"
  echo "== plane_map.csv: rsu6 vs Step 13 rsu_opt (refplanes/step13/plane_map.csv) =="
  if cmp -s "$here/plane_map.csv" "$here/../step13/plane_map.csv"; then
    echo "plane_map.csv IDENTICAL to step13 (rsu_opt) (sha256 $(sha256sum "$here/plane_map.csv" | cut -d' ' -f1))"
  else
    echo "plane_map.csv DIFFERS from step13 (rsu_opt):"; diff "$here/../step13/plane_map.csv" "$here/plane_map.csv"
  fi
  echo "== validate_refplanes_9b.py (container) =="
  "$here/eic_exec_rsu6.sh" "python3 $here/validate_refplanes_9b.py" 2>&1 | grep -v "Info in\|INFO\|envelope26"; echo "exit status: ${PIPESTATUS[0]}"
  echo "Finished: $(date -u --iso-8601=seconds)"
} > "$here/validate_refplanes_9b.txt" 2>&1
"$here/plane_clearance_9a_crosscheck.sh"
