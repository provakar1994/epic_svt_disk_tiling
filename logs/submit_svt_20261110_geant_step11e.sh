#!/usr/bin/env bash
# Step 11e Slurm wrapper: one Geant4 overlap job (0.1 mm, tracking-only) per scenario.
# Usage (host, after check_svt_20261110_step11d.sh):
#   sbatch proj_svt_disk_tiling/logs/submit_svt_20261110_geant_step11e.sh            # array: rsu_opt, rsu6
#   sbatch --array=1 proj_svt_disk_tiling/logs/submit_svt_20261110_geant_step11e.sh  # rsu6 only
# Time: full craterlake took ~78 min in Step 8q, the tracking-only disk-tiles config ~5 min
# in Step 8l; 2 h leaves margin for the full tracking-only config.
#SBATCH --account=m3763
#SBATCH --qos=shared
#SBATCH --constraint=cpu
#SBATCH --job-name=svt-geant-11e
#SBATCH --array=0-1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/logs/slurm_svt_geant_step11e_%A_%a.out
set -euo pipefail
proj=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling
scenarios=(rsu_opt rsu6)
scenario="${scenarios[${SLURM_ARRAY_TASK_ID:-0}]}"
echo "Job ${SLURM_JOB_ID:-local} task ${SLURM_ARRAY_TASK_ID:-0}: scenario $scenario on $(hostname)"
"$proj/refplanes/eic_exec.sh" "bash $proj/logs/check_svt_20261110_geant_step11e.sh $scenario"
