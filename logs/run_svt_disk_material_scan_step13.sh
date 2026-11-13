#!/usr/bin/env bash
# Step 13 (Step 13d) per-disk material scan: 20261110_ES/rsu_opt tiling, delivered-row
# corrugation, FPC split on all modules, bridge FPCs away from y = 0 (EPIC 78ade4686,
# install frozen in logs/freeze_install_step13.txt). Copy of run_svt_disk_material_scan_step8q.sh:
#   1. geantino material recording on the installed epic_craterlake_material_map.xml,
#      restricted to the SVT disk eta band 0.90 < |eta| < 4.25, as 4 equal-width eta
#      slices run in parallel with distinct seeds (uniform in eta over the band);
#      recorder: logs/record_svt_disk_material_step8q.py (reused unchanged; only adds --seed);
#   2. per-disk maps with scripts/subdetector_tests/run_disk_material_map.sh on all slices
#      (disk table checked against definitions_craterlake.xml at HEAD: logs/check_disk_table_step13.txt);
#   3. comparison of per-disk / per-material x/X0 with the Step 8q scan.
# Geometry identity: HEAD + sha256 of installed silicon_disks_modules.xml and libepic.so
# (the top-level XML only includes other files and does not identify the geometry), clean src/ compact/.
# Run outside eic-shell (login node, or the Slurm job logs/submit_svt_disk_material_scan_step13.sh);
# recording runs in eic_xl:26.09.0-stable via refplanes/eic_exec.sh.
# Usage: bash run_svt_disk_material_scan_step13.sh [events [tracks]]   (default 1000 x 1500 per slice)
set -euo pipefail

proj="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
epic="$(cd "$proj/.." && pwd)"
material_dir="$epic/scripts/material_map"
events="${1:-1000}"
tracks="${2:-1500}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
prefix="step13_${stamp}"
(( events * tracks < 1000000 )) && prefix="step13_smoke_${stamp}"
report="$proj/logs/svt_disk_material_scan_${prefix}.txt"
outdir="$proj/matscan/disk_material_map/${prefix}"
recdir="$outdir/recording"   # scan-only geantino recordings live next to the scan output
xml="$epic/install/share/epic/epic_craterlake_material_map.xml"
modules_xml="$epic/install/share/epic/compact/tracking/silicon_disks_modules.xml"
libepic="$epic/install/lib/libepic.so"
reference_json="$proj/matscan/disk_material_map/step8q_20261106T153414Z/disk_material_summary.json"

expected_head="78ade46865d06250fe601c5b56189e37735f75b1"
expected_modules_sha="6d04bd66e5524c9cbdfec34c0e15064463af2000501a925063dc577ccfd1b27b"
expected_libepic_sha="9ccf1a6690903c009fe167383d14eb81c170c2ed29d212d674a6c73886e5cc87"

# eta slices: [lo, hi] pairs; equal widths so the merged sample is uniform in eta per side
slices=("-4.25 -2.575" "-2.575 -0.90" "0.90 2.575" "2.575 4.25")
seeds=(13101 13102 13103 13104)

[[ ! -e "$outdir" && ! -e "$report" ]] || { echo "ERROR: $outdir exists; retry" >&2; exit 1; }
mkdir -p "$recdir"
exec > >(tee "$report") 2>&1
echo "Step 13 per-disk material scan: $prefix  host=$(hostname)  SLURM_JOB_ID=${SLURM_JOB_ID:-none}"
echo "EPIC HEAD=$(git -C "$epic" rev-parse HEAD)  dirty(src,compact)=$(git -C "$epic" status --short --untracked-files=no -- src compact | wc -l)"
echo "XML=$xml  events=$events tracks/event=$tracks per slice"

# geometry identity checks (abort on any mismatch)
[[ "$(git -C "$epic" rev-parse HEAD)" == "$expected_head" ]] || { echo "ERROR: EPIC HEAD is not $expected_head"; exit 1; }
[[ -z "$(git -C "$epic" status --short --untracked-files=no -- src compact)" ]] \
  || { echo "ERROR: uncommitted geometry changes in compact/ or src/"; exit 1; }
cmp "$epic/compact/tracking/silicon_disks_modules.xml" "$modules_xml"
[[ "$(sha256sum "$modules_xml" | cut -d' ' -f1)" == "$expected_modules_sha" ]] \
  || { echo "ERROR: installed silicon_disks_modules.xml is not the Step 13 freeze"; exit 1; }
[[ "$(sha256sum "$libepic" | cut -d' ' -f1)" == "$expected_libepic_sha" ]] \
  || { echo "ERROR: $libepic is not the Step 13 freeze"; exit 1; }
[[ -s "$reference_json" ]] || { echo "ERROR: Step 8q reference $reference_json missing"; exit 1; }
sha256sum "$xml" "$modules_xml" "$libepic" "$epic/install/share/epic/compact/tracking/definitions_craterlake.xml" \
  "$proj/logs/record_svt_disk_material_step8q.py" "$epic/scripts/subdetector_tests/disk_material_map.py" \
  "$proj/logs/run_svt_disk_material_scan_step13.sh"

# 1. recording, one background container per slice
pids=()
files=()
for k in "${!slices[@]}"; do
  read -r lo hi <<< "${slices[$k]}"
  out="$recdir/${prefix}_slice${k}_geant4_material_tracks.root"
  files+=("$out")
  log="$recdir/${prefix}_slice${k}_recording.log"
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

# 3. comparison with the Step 8q scan
module load conda >/dev/null 2>&1 || true
set +u; eval "$(conda shell.bash hook)" && conda activate tracking; set -u
python "$proj/logs/compare_disk_material_summaries.py" \
  "$reference_json" "Step8q" \
  "$outdir/disk_material_summary.json" "Step13"
echo "outputs: $outdir"
