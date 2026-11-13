#!/usr/bin/env bash
# Step 13: handedness/orientation audit of the Step 12 exports against the provider's
# module convention (20261016 Module Definitions PDF + module_cad_export.py).
# Read-only. Run on the host: bash logs/check_svt_handedness_step13.sh
# Report: logs/check_svt_handedness_step13.txt
set -euo pipefail
proj=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling
run=$proj/tmp/svt_step12_20261112T155205Z
tiling=/global/cfs/cdirs/m3763/pdatta/epic/compact/tracking/silicon_disks_tiling
cmd=""
for geo in 20261110_ES/rsu_opt 20261110_ES/rsu6 20261110-r_ES/rsu_opt 20261110-r_ES/rsu6; do
  tag="${geo%/*}_${geo#*/}"
  cmd+="echo; echo '== $geo'; python3 $proj/logs/inspect_svt_handedness_step13.py $run/epic_craterlake_tracking_only_$tag.root $tiling/$geo 2>&1 | grep -v '^Info'; "
done
bash "$proj/refplanes/eic_exec.sh" "$cmd" 2>&1 | tee "$proj/logs/check_svt_handedness_step13.txt"
