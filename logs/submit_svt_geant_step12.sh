#!/usr/bin/env bash
# Step 12: Geant4 overlap checks (0.1 mm, tracking-only) after building the corrugation from
# <disk>_rows.csv and splitting the FPC on all modules. Four geometries as a Slurm array:
#   0 20261110_ES/rsu_opt (installed)  1 20261110_ES/rsu6  2 20261110-r_ES/rsu_opt  3 20261110-r_ES/rsu6
# Usage: sbatch proj_svt_disk_tiling/logs/submit_svt_geant_step12.sh   (after check_svt_step12.sh)
# Reports: logs/check_svt_geant_step12_<delivery>_<scenario>.txt (+ _raw_).
#SBATCH --account=m3763
#SBATCH --qos=shared
#SBATCH --constraint=cpu
#SBATCH --job-name=svt-geant-12
#SBATCH --array=0-3
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/logs/slurm_svt_geant_step12_%A_%a.out
set -euo pipefail
proj=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling
geometries=(20261110_ES/rsu_opt 20261110_ES/rsu6 20261110-r_ES/rsu_opt 20261110-r_ES/rsu6)
geo="${geometries[${SLURM_ARRAY_TASK_ID:-0}]}"
echo "Job ${SLURM_JOB_ID:-local} task ${SLURM_ARRAY_TASK_ID:-0}: $geo on $(hostname)"
"$proj/refplanes/eic_exec.sh" "GEANT_STEP=step12 bash $proj/logs/check_svt_geant_step11f.sh ${geo%/*} ${geo#*/}"
