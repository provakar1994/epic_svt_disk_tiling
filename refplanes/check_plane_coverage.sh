#!/usr/bin/env bash
# Plane coverage of the silicon on the 4 x 10k 9f samples and the 6 v2 smoke files (host). Report: check_plane_coverage.txt
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
module load conda >/dev/null 2>&1; conda activate tracking
d=/pscratch/sd/p/pdatta/svt_disk_tiling/refplanes/silicon_9f
{ echo "Started: $(date -u --iso-8601=seconds)"; python3 "$here/check_plane_coverage.py" $d/sim_installed_fwd.root $d/sim_installed_bwd.root $d/sim_overlay_fwd.root $d/sim_overlay_bwd.root /pscratch/sd/p/pdatta/svt_disk_tiling/refplanes/smoke/sim_*.root; echo "exit status: $?"; } > "$here/check_plane_coverage.txt" 2>&1
