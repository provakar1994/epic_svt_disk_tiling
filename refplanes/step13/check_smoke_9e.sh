#!/usr/bin/env bash
# [Step 13 copy, 2026-11-12: runs the refplanes/step13/ copies; reports in refplanes/step13/; container via ../eic_exec.sh]
# Step 9e checks on the smoke outputs (host, conda env tracking). Report: check_smoke_9e.txt
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
module load conda >/dev/null 2>&1; conda activate tracking
{ echo "Started: $(date -u --iso-8601=seconds)"; python3 "$here/check_smoke_9e.py" /pscratch/sd/p/pdatta/svt_disk_tiling/refplanes_step13/smoke; echo "exit status: $?"; } > "$here/check_smoke_9e.txt" 2>&1
