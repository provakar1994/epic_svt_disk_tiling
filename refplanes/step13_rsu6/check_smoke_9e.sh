#!/usr/bin/env bash
# [Step 14b rsu6 copy (2026-11-13): rsu6 overlay geometry_overlays/step13/rsu6/, container via eic_exec_rsu6.sh (CWD step13_rsu6/), identity_check_step13_rsu6.sh. Of the Step 13 copy, 2026-11-12: runs the refplanes/step13_rsu6/ copies; reports in refplanes/step13_rsu6/; container via ../eic_exec.sh]
# Step 9e checks on the smoke outputs (host, conda env tracking). Report: check_smoke_9e.txt
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
module load conda >/dev/null 2>&1; conda activate tracking
{ echo "Started: $(date -u --iso-8601=seconds)"; python3 "$here/check_smoke_9e.py" /pscratch/sd/p/pdatta/svt_disk_tiling/refplanes_step13_rsu6/smoke; echo "exit status: $?"; } > "$here/check_smoke_9e.txt" 2>&1
