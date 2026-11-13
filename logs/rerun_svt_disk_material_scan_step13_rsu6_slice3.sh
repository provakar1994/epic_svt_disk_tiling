#!/usr/bin/env bash
# Step 14a recovery: the full rsu6 scan (Slurm 61226514, prefix step13_rsu6_20261113T143518Z) lost
# slice 3 (eta 2.575..4.25) to an out-of-memory kill at ~700/1000 events (4 parallel recordings in
# 64G); slices 0-2 completed. Rerun slice 3 alone with the identical command and seed 13104
# (geantinos: same seed -> identical sample), then steps 2-3 of run_svt_disk_material_scan_step13_rsu6.sh.
# The partial slice-3 file and log are moved to tmp/retained/2026-11-13/ (logged), not overwritten.
# Usage: sbatch --account=m3763 --qos=shared --constraint=cpu --cpus-per-task=4 --mem=64G --time=02:00:00 \
#          --output=<proj>/logs/slurm_matscan_step13_rsu6_slice3_%j.out <this script>
set -euo pipefail
proj=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling
epic=/global/cfs/cdirs/m3763/pdatta/epic
material_dir="$epic/scripts/material_map"
prefix=step13_rsu6_20261113T143518Z
outdir="$proj/matscan/disk_material_map/$prefix"
recdir="$outdir/recording"
xml="$proj/geometry_overlays/step13/rsu6/epic_craterlake_material_map_rsu6.xml"
reference_json="$proj/matscan/disk_material_map/step13_20261113T065150Z/disk_material_summary.json"
report="$proj/logs/svt_disk_material_scan_step13_rsu6_slice3_rerun.txt"
exec > >(tee "$report") 2>&1
echo "rsu6 scan slice-3 rerun: $(date -u +%FT%TZ) host=$(hostname) SLURM_JOB_ID=${SLURM_JOB_ID:-none}"
[[ "$(sha256sum "$xml" | cut -d' ' -f1)" == 80c74aae7c88c2786f99fbeb3035561a81021b652b941ab6f9d8d88b0fcc06de ]] \
  || { echo "ERROR: rsu6 material-map overlay changed"; exit 1; }
[[ "$(git -C "$epic" rev-parse HEAD)" == 78ade46865d06250fe601c5b56189e37735f75b1 ]] || { echo "ERROR: HEAD changed"; exit 1; }

# Retain the partial slice-3 outputs.
keep="$epic/tmp/retained/2026-11-13/proj_svt_disk_tiling_matscan_${prefix}_partial_slice3"
mkdir -p "$keep"
for f in "$recdir/${prefix}_slice3_geant4_material_tracks.root" "$recdir/${prefix}_slice3_recording.log"; do
  if [[ -e "$f" ]]; then
    mv "$f" "$keep/"
    printf '%s\t%s\t%s\tmove\tpartial output of OOM-killed slice 3 (Slurm 61226514); rerun\n' \
      "$(date -u +%FT%TZ)" "$f" "$keep/$(basename "$f")" >> "$epic/tmp/file_actions.log"
  fi
done

# 1. slice 3 only, identical arguments to the original run
bash "$proj/refplanes/eic_exec.sh" "cd $material_dir && python $proj/logs/record_svt_disk_material_step8q.py \
    -i $xml -n 1000 -t 1500 --eta-min=2.575 --eta-max=4.25 --seed 13104 \
    -o $recdir/${prefix}_slice3_geant4_material_tracks.root" > "$recdir/${prefix}_slice3_recording.log" 2>&1
grep -h 'Processed .* events' "$recdir/${prefix}_slice3_recording.log" | tail -1

# 2. per-disk maps on all four slices
bash "$epic/scripts/subdetector_tests/run_disk_material_map.sh" \
  "$recdir/${prefix}_slice*_geant4_material_tracks.root" "$outdir"

# 3. paired comparison with the rsu_opt Step 13 scan
module load conda >/dev/null 2>&1 || true
set +u; eval "$(conda shell.bash hook)" && conda activate tracking; set -u
python "$proj/logs/compare_disk_material_summaries.py" "$reference_json" "rsu_opt" \
  "$outdir/disk_material_summary.json" "rsu6"
echo "outputs: $outdir"
