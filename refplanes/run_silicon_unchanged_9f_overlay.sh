#!/usr/bin/env bash
# Step 9f (v2): the two overlay runs (v2 planes + steering), same seeds as the installed runs
# made by run_silicon_unchanged_9f.sh (installed_fwd seed 201, installed_bwd seed 202; those are
# unaffected by the plane change). The v1 overlay runs were stopped part-way and retained.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
out=/pscratch/sd/p/pdatta/svt_disk_tiling/refplanes/silicon_9f
"$here/run_npsim_refplanes.sh" overlay "$out" overlay_fwd 10000 0  0.6  3.8 201 &
"$here/run_npsim_refplanes.sh" overlay "$out" overlay_bwd 10000 0 -3.8 -0.6 202 &
wait
echo "overlay 9f runs finished: $(date -u --iso-8601=seconds)"
