#!/usr/bin/env bash
# Runs plane_clearance_9a_crosscheck.py in the container. Report: plane_clearance_9a_crosscheck.txt
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
{
  echo "Started: $(date -u --iso-8601=seconds)"
  "$here/eic_exec.sh" "python3 $here/plane_clearance_9a_crosscheck.py"
  echo "exit status: $?"
  echo "Finished: $(date -u --iso-8601=seconds)"
} > "$here/plane_clearance_9a_crosscheck.txt" 2>&1
