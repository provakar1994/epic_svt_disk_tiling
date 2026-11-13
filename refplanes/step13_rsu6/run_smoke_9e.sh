#!/usr/bin/env bash
# [Step 14b rsu6 copy (2026-11-13): rsu6 overlay geometry_overlays/step13/rsu6/, container via eic_exec_rsu6.sh (CWD step13_rsu6/), identity_check_step13_rsu6.sh. Of the Step 13 copy, 2026-11-12: Step 13 overlay (step13/generated/), output /pscratch/.../refplanes_step13_rsu6/smoke; same events, vertices and seeds as v3]
# Step 9e smoke test (v2 planes): 6 x 100 events pi+ on the overlay geometry with the plane steering.
# Configurations: vz = 0, +100 mm, -100 mm, each with eta 0.6..3.8 and eta -3.8..-0.6.
# Runs sequentially (one core). Then check_smoke_9e.sh. v1 smoke files (4 runs, v1 planes) are in
# tmp/retained/2026-11-06/refplanes_v1/smoke/.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
out=/pscratch/sd/p/pdatta/svt_disk_tiling/refplanes_step13_rsu6/smoke
"$here/run_npsim_refplanes.sh" overlay "$out" vz0_fwd     100    0  0.6  3.8 101
"$here/run_npsim_refplanes.sh" overlay "$out" vz0_bwd     100    0 -3.8 -0.6 102
"$here/run_npsim_refplanes.sh" overlay "$out" vz100_fwd   100  100  0.6  3.8 103
"$here/run_npsim_refplanes.sh" overlay "$out" vz100_bwd   100  100 -3.8 -0.6 104
"$here/run_npsim_refplanes.sh" overlay "$out" vzm100_fwd  100 -100  0.6  3.8 105
"$here/run_npsim_refplanes.sh" overlay "$out" vzm100_bwd  100 -100 -3.8 -0.6 106
