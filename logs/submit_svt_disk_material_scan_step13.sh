#!/usr/bin/env bash
# Batch job for the full Step 13 per-disk material scan (4 eta slices x 1000 x 1500 geantinos,
# 4 recording containers in parallel; Step 8q recording took 12-20 min per slice on a login node).
# Usage: sbatch proj_svt_disk_tiling/logs/submit_svt_disk_material_scan_step13.sh
#SBATCH --account=m3763
#SBATCH --qos=shared
#SBATCH --constraint=cpu
#SBATCH --job-name=svt-matscan-13
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=03:00:00
#SBATCH --output=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/logs/slurm_matscan_step13_%j.out
set -euo pipefail
proj=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling
bash "$proj/logs/run_svt_disk_material_scan_step13.sh" "$@"
