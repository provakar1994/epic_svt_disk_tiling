#!/usr/bin/env bash
# Step 14a: batch job for the full rsu6 Step 13 per-disk material scan (4 eta slices x 1000 x 1500
# geantinos, seeds 13101-13104 as the rsu_opt Step 13 scan; copy of submit_svt_disk_material_scan_step13.sh
# with --mem=64G, as the rsu_opt scan was actually submitted).
# Usage: sbatch proj_svt_disk_tiling/logs/submit_svt_disk_material_scan_step13_rsu6.sh [events [tracks]]
#SBATCH --account=m3763
#SBATCH --qos=shared
#SBATCH --constraint=cpu
#SBATCH --job-name=svt-matscan-13-rsu6
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=03:00:00
#SBATCH --output=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/logs/slurm_matscan_step13_rsu6_%j.out
set -euo pipefail
proj=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling
bash "$proj/logs/run_svt_disk_material_scan_step13_rsu6.sh" "$@"
