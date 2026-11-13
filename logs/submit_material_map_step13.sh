#!/usr/bin/env bash
# Batch job for the full Step 13 material map (1000 x 5000 geantinos; Step 8q took 81 min on 4 cpus).
# Usage: sbatch proj_svt_disk_tiling/logs/submit_material_map_step13.sh
#SBATCH --account=m3763
#SBATCH --qos=shared
#SBATCH --constraint=cpu
#SBATCH --job-name=svt-matmap-13
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=05:00:00
#SBATCH --output=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/logs/slurm_material_map_step13_%j.out
set -euo pipefail
proj=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling
"$proj/refplanes/eic_exec.sh" "bash $proj/logs/regenerate_svt_material_map_step13.sh 1000 5000"
