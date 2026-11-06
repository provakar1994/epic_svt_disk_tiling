#!/usr/bin/env bash
# Step 9f: silicon-unchanged comparison. 4 npsim runs of 10k pi+ events at vz = 0:
#   installed geometry + default steering vs overlay geometry + plane steering,
#   eta 0.6..3.8 (seed 201) and eta -3.8..-0.6 (seed 202); same seed per eta range.
# The 4 runs go in parallel (4 single-core processes). Then analyze_silicon_unchanged_9f.py.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
out=/pscratch/sd/p/pdatta/svt_disk_tiling/refplanes/silicon_9f
"$here/run_npsim_refplanes.sh" installed "$out" installed_fwd 10000 0  0.6  3.8 201 &
"$here/run_npsim_refplanes.sh" overlay   "$out" overlay_fwd   10000 0  0.6  3.8 201 &
"$here/run_npsim_refplanes.sh" installed "$out" installed_bwd 10000 0 -3.8 -0.6 202 &
"$here/run_npsim_refplanes.sh" overlay   "$out" overlay_bwd   10000 0 -3.8 -0.6 202 &
wait
echo "all 9f runs finished: $(date -u --iso-8601=seconds)"
