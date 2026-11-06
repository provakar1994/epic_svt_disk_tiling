#!/usr/bin/env bash
# Step 8q per-disk material scan (rounded 5 mm corrugation bends, EPIC 311634084).
#   1. geantino material recording on the installed epic_craterlake_material_map.xml,
#      restricted to the SVT disk eta band 0.90 < |eta| < 4.25, as 4 equal-width eta
#      slices run in parallel with distinct seeds (uniform in eta over the band);
#   2. per-disk maps with scripts/subdetector_tests/run_disk_material_map.sh on all slices;
#   3. comparison of per-disk / per-material x/X0 with the Step 8m result.
# Run from a login node (outside eic-shell); recording runs in eic_xl:26.09.0-stable via
# refplanes/eic_exec.sh. Usage: bash run_svt_disk_material_scan_step8q.sh [events [tracks]]
set -euo pipefail

proj="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
epic="$(cd "$proj/.." && pwd)"
material_dir="$epic/scripts/material_map"
events="${1:-1000}"
tracks="${2:-1500}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
prefix="step8q_${stamp}"
report="$proj/logs/svt_disk_material_scan_step8q_${stamp}.txt"
outdir="$proj/matscan/disk_material_map/${prefix}"
recdir="$outdir/recording"   # scan-only geantino recordings live next to the scan output
xml="$epic/install/share/epic/epic_craterlake_material_map.xml"

# eta slices: [lo, hi] pairs; equal widths so the merged sample is uniform in eta per side
slices=("-4.25 -2.575" "-2.575 -0.90" "0.90 2.575" "2.575 4.25")
seeds=(8101 8102 8103 8104)

exec > >(tee "$report") 2>&1
echo "Step 8q per-disk material scan: $stamp"
echo "EPIC HEAD=$(git -C "$epic" rev-parse HEAD)  dirty(src,compact)=$(git -C "$epic" status --short -- src compact | wc -l)"
echo "XML=$xml  events=$events tracks/event=$tracks per slice"
cmp "$epic/compact/tracking/silicon_disks_modules.xml" "$epic/install/share/epic/compact/tracking/silicon_disks_modules.xml"
grep -q 'bend_radius="SiEndcapCorrugation_bend_radius"' "$epic/install/share/epic/compact/tracking/silicon_disks_modules.xml"
sha256sum "$xml" "$epic/install/share/epic/compact/tracking/silicon_disks_modules.xml" "$epic/install/lib/libepic.so"

# 1. recording, one background container per slice
pids=()
files=()
for k in "${!slices[@]}"; do
  read -r lo hi <<< "${slices[$k]}"
  out="$recdir/${prefix}_slice${k}_geant4_material_tracks.root"
  files+=("$out")
  log="$recdir/${prefix}_slice${k}_recording.log"
  mkdir -p "$recdir"
  echo "slice $k: eta [$lo, $hi] seed ${seeds[$k]} -> $out (log $log)"
  bash "$proj/refplanes/eic_exec.sh" "cd $material_dir && python $proj/logs/record_svt_disk_material_step8q.py \
      -i $xml -n $events -t $tracks --eta-min=$lo --eta-max=$hi --seed ${seeds[$k]} -o $out" > "$log" 2>&1 &
  pids+=($!)
done
fail=0
for k in "${!pids[@]}"; do
  if wait "${pids[$k]}"; then echo "slice $k: done ($(grep -h 'Processed .* events' "$recdir/${prefix}_slice${k}_recording.log" | tail -1))"
  else echo "slice $k: FAILED, see $recdir/${prefix}_slice${k}_recording.log"; fail=1; fi
done
[[ $fail -eq 0 ]] || exit 1
ls -la "${files[@]}"

# 2. per-disk maps on all slices (uproot glob)
bash "$epic/scripts/subdetector_tests/run_disk_material_map.sh" \
  "$recdir/${prefix}_slice*_geant4_material_tracks.root" "$outdir"

# 3. comparison with Step 8m
module load conda >/dev/null 2>&1 || true
set +u; eval "$(conda shell.bash hook)" && conda activate tracking; set -u
python "$proj/logs/compare_disk_material_summaries.py" \
  "$proj/matscan/disk_material_map/step8m_full/disk_material_summary.json" "Step8m" \
  "$outdir/disk_material_summary.json" "Step8q"
echo "outputs: $outdir"
