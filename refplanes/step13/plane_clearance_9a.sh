#!/usr/bin/env bash
# [Step 13 copy, 2026-11-12: runs the refplanes/step13/ copies; reports in refplanes/step13/; container via ../eic_exec.sh]
# Step 9a runner: confirm installed compact files match the EPIC checkout, then
# run plane_clearance_9a.py in the container. Report: plane_clearance_9a.txt
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
epic=/global/cfs/cdirs/m3763/pdatta/epic
{
  echo "Started: $(date -u --iso-8601=seconds)"
  "$here/identity_check_step13.sh"
  echo "-- repo vs installed compact files (sha256 must match) --"
  for f in tracking/definitions_craterlake.xml tracking/silicon_disks_modules.xml tracking/support_service_craterlake.xml; do
    a=$(sha256sum $epic/compact/$f | cut -c1-16); b=$(sha256sum $epic/install/share/epic/compact/$f | cut -c1-16)
    echo "  $f repo=$a installed=$b $([[ $a == $b ]] && echo same || echo DIFFERENT)"
  done
  "$here/../eic_exec.sh" "python3 $here/plane_clearance_9a.py"
  echo "exit status: $?"
  echo "Finished: $(date -u --iso-8601=seconds)"
} > "$here/plane_clearance_9a.txt" 2>&1
