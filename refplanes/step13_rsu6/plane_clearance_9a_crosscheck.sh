#!/usr/bin/env bash
# [Step 14b rsu6 copy (2026-11-13): rsu6 overlay geometry_overlays/step13/rsu6/, container via eic_exec_rsu6.sh (CWD step13_rsu6/), identity_check_step13_rsu6.sh. Of the Step 13 copy, 2026-11-12: runs the refplanes/step13_rsu6/ copies; reports in refplanes/step13_rsu6/; container via ../eic_exec.sh]
# Runs plane_clearance_9a_crosscheck.py in the container. Report: plane_clearance_9a_crosscheck.txt
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
{
  echo "Started: $(date -u --iso-8601=seconds)"
  "$here/eic_exec_rsu6.sh" "python3 $here/plane_clearance_9a_crosscheck.py"
  echo "exit status: $?"
  echo "Finished: $(date -u --iso-8601=seconds)"
} > "$here/plane_clearance_9a_crosscheck.txt" 2>&1
