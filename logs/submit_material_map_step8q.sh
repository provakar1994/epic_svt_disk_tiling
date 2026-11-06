#!/usr/bin/env bash
# Batch job for the full Step 8q material map (1000 x 5000 geantinos, ~45 min in Step 8m).
# Usage: sbatch proj_svt_disk_tiling/logs/submit_material_map_step8q.sh
#SBATCH --account=m3763
#SBATCH --qos=shared
#SBATCH --constraint=cpu
#SBATCH --job-name=svt-matmap-8q
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=04:00:00
#SBATCH --output=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/logs/slurm_material_map_step8q_%j.out
set -euo pipefail
proj=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling
"$proj/refplanes/eic_exec.sh" "bash $proj/logs/regenerate_svt_material_map_step8q.sh 1000 5000"
