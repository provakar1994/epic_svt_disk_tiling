#!/usr/bin/env bash
# Step 11f: Geant4 overlap checks (0.1 mm, tracking-only) for the 20261110-r_ES package.
# Usage: sbatch proj_svt_disk_tiling/logs/submit_svt_geant_step11f.sh            # array: rsu_opt, rsu6
#        sbatch --array=1 proj_svt_disk_tiling/logs/submit_svt_geant_step11f.sh  # rsu6 only
# Requires the install to contain 20261110-r_ES (check_svt_20261110r_step11f.sh).
#SBATCH --account=m3763
#SBATCH --qos=shared
#SBATCH --constraint=cpu
#SBATCH --job-name=svt-geant-11f
#SBATCH --array=0-1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/logs/slurm_svt_geant_step11f_%A_%a.out
set -euo pipefail
proj=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling
delivery=20261110-r_ES
scenarios=(rsu_opt rsu6)
scenario="${scenarios[${SLURM_ARRAY_TASK_ID:-0}]}"
echo "Job ${SLURM_JOB_ID:-local} task ${SLURM_ARRAY_TASK_ID:-0}: $delivery/$scenario on $(hostname)"
"$proj/refplanes/eic_exec.sh" "bash $proj/logs/check_svt_geant_step11f.sh $delivery $scenario"
