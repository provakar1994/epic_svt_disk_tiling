#!/usr/bin/env bash
# Step 13 (acceptance_v4_step13) master for the fast refplane gates, in this order:
#   1. plane_clearance_9a.sh      (installed geometry, no planes)  -> plane_clearance_9a.txt
#   2. validate_refplanes_9b.sh   (overlay XML, plane_map.csv, validator, cross-check)
#                                 -> validate_refplanes_9b.txt, plane_clearance_9a_crosscheck.txt
#   3. check_refplanes_9c.sh root (dd_web_display export + ROOT checkOverlaps) -> check_refplanes_9c_root.txt
# The Geant4 overlap check goes to Slurm: sbatch submit_geant4_9c_step13.sh
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$here/identity_check_step13.sh" || exit 2
"$here/plane_clearance_9a.sh"
"$here/validate_refplanes_9b.sh"
"$here/check_refplanes_9c.sh" root
for r in plane_clearance_9a validate_refplanes_9b plane_clearance_9a_crosscheck check_refplanes_9c_root; do
  echo "== $r.txt"; grep -E "overall|validator|Cross-check:|ovlp|IDENTICAL|DIFFERS|Identity:|exit status" "$here/$r.txt"
done
