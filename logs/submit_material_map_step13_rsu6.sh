#!/usr/bin/env bash
# Step 14a: batch job for the full rsu6 Step 13 material map (1000 x 5000 geantinos, frozen overlay
# geometry_overlays/step13/rsu6; copy of submit_material_map_step13.sh, the rsu_opt map took 67 min).
# Usage: sbatch proj_svt_disk_tiling/logs/submit_material_map_step13_rsu6.sh
#SBATCH --account=m3763
#SBATCH --qos=shared
#SBATCH --constraint=cpu
#SBATCH --job-name=svt-matmap-13-rsu6
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=05:00:00
#SBATCH --output=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/logs/slurm_material_map_step13_rsu6_%j.out
set -euo pipefail
proj=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling
"$proj/refplanes/eic_exec.sh" "bash $proj/logs/regenerate_svt_material_map_step13_rsu6.sh 1000 5000"
