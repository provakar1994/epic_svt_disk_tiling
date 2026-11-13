#!/usr/bin/env bash
# Step 13: diagnose the clean primary plane hit(s) with |p_hit|/|p_gen| < 0.95 that failed the
# check_smoke_9e C sub-gate on the acceptance_v4_step13 campaign smoke file (forward, vz = +100).
# Same diagnosis as v3 (refplanes/diagnose_low_p_primary_9e.txt). Report: step13/diagnose_low_p_primary_smoke_v4.txt
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
module load conda >/dev/null 2>&1; conda activate tracking
f=/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/smoke_20261112_v4_step13/vz_p100mm_eta_p0p6_to_p3p8/rootfiles/sim_vz_p100mm_eta_p0p6_to_p3p8_chunk_001_smoke_n200.root
{ echo "Started: $(date -u --iso-8601=seconds)"; echo "File: $f"; python3 "$here/diagnose_low_p_primary_9e.py" "$f" 0.95; echo "exit status: $?"; } > "$here/diagnose_low_p_primary_smoke_v4.txt" 2>&1
cat "$here/diagnose_low_p_primary_smoke_v4.txt"
