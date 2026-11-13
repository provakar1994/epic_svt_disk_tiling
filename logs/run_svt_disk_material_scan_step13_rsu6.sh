#!/usr/bin/env bash
# Step 14a per-disk material scan for the Step 13 geometry with the 20261110_ES/rsu6 tiling (2150 modules).
# Copy of run_svt_disk_material_scan_step13.sh (unchanged); differences:
#   - recording XML = frozen overlay geometry_overlays/step13/rsu6/epic_craterlake_material_map_rsu6.xml
#     (installed epic_craterlake_material_map.xml with only the SVT modules include redirected to
#     silicon_disks_modules_rsu6.xml; logs/make_svt_overlay_step14a_rsu6.sh, provenance_step14a.txt);
#     DETECTOR_PATH stays the install (eic_exec.sh), so the rsu6 CSVs resolve there;
#   - overlay sha256 checks + Step 13 freeze checks (HEAD, installed module XML, libepic, clean src/compact);
#   - logs/count_svt_modules_step14a.py loads the same XML from the recording cwd (scripts/material_map)
#     and requires 2150 SVT endcap modules before recording (rsu_opt: 2164);
#   - SAME eta slices and seeds 13101-13104 as the rsu_opt Step 13 scan -> identical geantino samples
#     (paired comparison);
#   - comparison against matscan/disk_material_map/step13_20261113T065150Z (labels rsu_opt vs rsu6);
#   - prefix step13_rsu6_<stamp> (step13_rsu6_smoke_<stamp> when events x tracks < 1e6).
# Run outside eic-shell (login node, or the Slurm job logs/submit_svt_disk_material_scan_step13_rsu6.sh);
# recording runs in eic_xl:26.09.0-stable via refplanes/eic_exec.sh.
# Usage: bash run_svt_disk_material_scan_step13_rsu6.sh [events [tracks]]   (default 1000 x 1500 per slice)
set -euo pipefail

proj="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
epic="$(cd "$proj/.." && pwd)"
material_dir="$epic/scripts/material_map"
events="${1:-1000}"
tracks="${2:-1500}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
prefix="step13_rsu6_${stamp}"
(( events * tracks < 1000000 )) && prefix="step13_rsu6_smoke_${stamp}"
report="$proj/logs/svt_disk_material_scan_${prefix}.txt"
outdir="$proj/matscan/disk_material_map/${prefix}"
recdir="$outdir/recording"   # scan-only geantino recordings live next to the scan output
overlay_dir="$proj/geometry_overlays/step13/rsu6"
xml="$overlay_dir/epic_craterlake_material_map_rsu6.xml"
overlay_modules="$overlay_dir/silicon_disks_modules_rsu6.xml"
modules_xml="$epic/install/share/epic/compact/tracking/silicon_disks_modules.xml"
libepic="$epic/install/lib/libepic.so"
reference_json="$proj/matscan/disk_material_map/step13_20261113T065150Z/disk_material_summary.json"  # rsu_opt Step 13

expected_head="78ade46865d06250fe601c5b56189e37735f75b1"
expected_modules_sha="6d04bd66e5524c9cbdfec34c0e15064463af2000501a925063dc577ccfd1b27b"
expected_libepic_sha="9ccf1a6690903c009fe167383d14eb81c170c2ed29d212d674a6c73886e5cc87"
expected_overlay_xml_sha="80c74aae7c88c2786f99fbeb3035561a81021b652b941ab6f9d8d88b0fcc06de"      # provenance_step14a.txt
expected_overlay_modules_sha="7bfe44276ceffc81989055f504f4f331c8970a99b99368f0a126a9e099c95567"  # provenance_step14a.txt
expected_module_count=2150                                                                       # 20261110_ES/rsu6

# eta slices: [lo, hi] pairs; equal widths so the merged sample is uniform in eta per side
slices=("-4.25 -2.575" "-2.575 -0.90" "0.90 2.575" "2.575 4.25")
seeds=(13101 13102 13103 13104)

[[ ! -e "$outdir" && ! -e "$report" ]] || { echo "ERROR: $outdir exists; retry" >&2; exit 1; }
mkdir -p "$recdir"
exec > >(tee "$report") 2>&1
echo "Step 14a (Step 13 geometry, rsu6) per-disk material scan: $prefix  host=$(hostname)  SLURM_JOB_ID=${SLURM_JOB_ID:-none}"
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
[[ "$(sha256sum "$xml" | cut -d' ' -f1)" == "$expected_overlay_xml_sha" ]] || { echo "ERROR: $xml is not the frozen Step 14a overlay"; exit 1; }
[[ "$(sha256sum "$overlay_modules" | cut -d' ' -f1)" == "$expected_overlay_modules_sha" ]] || { echo "ERROR: $overlay_modules is not the frozen Step 14a overlay"; exit 1; }
[[ -s "$reference_json" ]] || { echo "ERROR: rsu_opt Step 13 reference $reference_json missing"; exit 1; }
sha256sum "$xml" "$modules_xml" "$libepic" "$epic/install/share/epic/compact/tracking/definitions_craterlake.xml" \
  "$proj/logs/record_svt_disk_material_step8q.py" "$epic/scripts/subdetector_tests/disk_material_map.py" \
  "$proj/logs/run_svt_disk_material_scan_step13_rsu6.sh" \
  "$overlay_modules" "$overlay_dir/provenance_step14a.txt" "$proj/logs/count_svt_modules_step14a.py"

# 0. prove the geometry: load the recording XML from the recording cwd and count the SVT modules
bash "$proj/refplanes/eic_exec.sh" "cd $material_dir && python $proj/logs/count_svt_modules_step14a.py $xml $expected_module_count" \
  > "$recdir/${prefix}_module_count.log" 2>&1 || { tail -5 "$recdir/${prefix}_module_count.log"; echo "ERROR: SVT module count check failed"; exit 1; }
grep -A1 SVT_MODULE_COUNT "$recdir/${prefix}_module_count.log"

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

# 3. paired comparison with the rsu_opt Step 13 scan (same seeds -> same geantinos)
module load conda >/dev/null 2>&1 || true
set +u; eval "$(conda shell.bash hook)" && conda activate tracking; set -u
python "$proj/logs/compare_disk_material_summaries.py" \
  "$reference_json" "rsu_opt" \
  "$outdir/disk_material_summary.json" "rsu6"
echo "outputs: $outdir"
