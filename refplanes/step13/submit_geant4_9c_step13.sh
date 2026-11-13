#!/usr/bin/env bash
# Step 13: Geant4 overlap check (0.1 mm) of the Step 13 refplane overlay, as a Slurm shared job
# (pattern: logs/submit_svt_geant_step13.sh). Runs step13/check_refplanes_9c.sh geant4.
# Usage: sbatch proj_svt_disk_tiling/refplanes/step13/submit_geant4_9c_step13.sh
# Report: refplanes/step13/check_refplanes_9c_geant4.txt (raw log in step13/out_9c/).
#SBATCH --account=m3763
#SBATCH --qos=shared
#SBATCH --constraint=cpu
#SBATCH --job-name=svt-rp13-g4
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/refplanes/step13/slurm_geant4_9c_%j.out
set -euo pipefail
here=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/refplanes/step13
echo "Job ${SLURM_JOB_ID:-local} on $(hostname)"
"$here/check_refplanes_9c.sh" geant4
cat "$here/check_refplanes_9c_geant4.txt"
