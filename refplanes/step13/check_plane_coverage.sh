#!/usr/bin/env bash
# [Step 13 copy, 2026-11-12, of refplanes/check_plane_coverage.sh] Plane coverage of the silicon on the
# 2 x 10k Step 13 overlay samples (run_coverage_samples_step13.sh) and the 6 Step 13 smoke files (host).
# Report: step13/check_plane_coverage.txt
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
module load conda >/dev/null 2>&1; conda activate tracking
d=/pscratch/sd/p/pdatta/svt_disk_tiling/refplanes_step13
{ echo "Started: $(date -u --iso-8601=seconds)"; python3 "$here/check_plane_coverage.py" $d/coverage_9f/sim_overlay_fwd.root $d/coverage_9f/sim_overlay_bwd.root $d/smoke/sim_*.root; echo "exit status: $?"; } > "$here/check_plane_coverage.txt" 2>&1
