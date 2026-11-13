#!/usr/bin/env bash
# [Step 14b rsu6 copy, 2026-11-13] same gates on refplanes/step13_rsu6/ (rsu6 overlay).
# Step 13: the two 10k-event overlay samples used by check_plane_coverage.sh, same settings and seeds as
# the v3 Step 9f overlay runs (refplanes/run_silicon_unchanged_9f_overlay.sh): pi+, vz = 0,
# eta 0.6..3.8 (seed 201) and -3.8..-0.6 (seed 202). The installed-geometry 9f runs are not repeated
# (the 9f silicon-unchanged comparison is not a v4 gate). Two single-core processes in parallel.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
out=/pscratch/sd/p/pdatta/svt_disk_tiling/refplanes_step13_rsu6/coverage_9f
"$here/run_npsim_refplanes.sh" overlay "$out" overlay_fwd 10000 0  0.6  3.8 201 &
"$here/run_npsim_refplanes.sh" overlay "$out" overlay_bwd 10000 0 -3.8 -0.6 202 &
wait
echo "coverage runs finished: $(date -u --iso-8601=seconds)"
