#!/usr/bin/env bash
# Step 13 driver (host): build + ROOT/handedness checks in the container, then the Geant4
# Slurm array, then the visualization exports (install/ is only read after the build).
set -euo pipefail
proj=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling
bash "$proj/refplanes/eic_exec.sh" "bash $proj/logs/check_svt_step13.sh"
sbatch "$proj/logs/submit_svt_geant_step13.sh"
for sel in "" rsu6 20261110-r_ES/rsu_opt 20261110-r_ES/rsu6; do
  bash "$proj/logs/make_svt_visualize.sh" step13 $sel
done
echo "Step 13 driver done"
