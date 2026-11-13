#!/usr/bin/env bash
# Step 14a: ACTS material map for the Step 13 geometry with the 20261110_ES/rsu6 tiling (2150 modules),
# for comparison with the rsu_opt Step 13 map (matmap/step13_20261113T054800Z). Copy of
# regenerate_svt_material_map_step13.sh (unchanged); differences:
#   - geometry = frozen overlay geometry_overlays/step13/rsu6/epic_craterlake_tracking_only_rsu6.xml
#     (the installed epic_craterlake_tracking_only.xml with only the SVT modules include redirected to
#     silicon_disks_modules_rsu6.xml; logs/make_svt_overlay_step14a_rsu6.sh, provenance_step14a.txt);
#     sha256 of both overlay files checked, plus the Step 13 freeze checks (HEAD, installed module XML, libepic).
#   - the upstream runner always uses ${DETECTOR_PATH}/${DETECTOR_CONFIG}.xml, so DETECTOR_PATH stays the
#     install (the overlay's other includes and the rsu6 CSVs resolve there) and DETECTOR_CONFIG is the
#     overlay path RELATIVE to DETECTOR_PATH (../../../proj_svt_disk_tiling/...). No upstream file edited.
#   - before the runner, logs/count_svt_modules_step14a.py loads the same XML from the run directory and
#     requires 2150 SVT endcap modules (rsu_opt would give 2164); the line SVT_MODULE_COUNT is in run_log.txt.
#   - tags step13_rsu6_<stamp> / step13_rsu6_smoke_<stamp>.
#
# Output: proj_svt_disk_tiling/matmap/<tag>/ (material-map_map.cbor, provenance.txt, run_log.txt, plots),
# transcript copy logs/material_map_<tag>.txt.
# Run inside eic_xl:26.09.0-stable with install/bin/thisepic.sh sourced, e.g.
#   proj_svt_disk_tiling/refplanes/eic_exec.sh "bash proj_svt_disk_tiling/logs/regenerate_svt_material_map_step13_rsu6.sh 10 100"
# Usage: regenerate_svt_material_map_step13_rsu6.sh [nevents [nparticles]]   (default 1000 x 5000)
set -euo pipefail

repo_root="/global/cfs/cdirs/m3763/pdatta/epic"
proj="$repo_root/proj_svt_disk_tiling"
material_dir="$repo_root/scripts/material_map"
nevents="${1:-1000}"
nparticles="${2:-5000}"
if [[ $# -gt 2 || ! "$nevents" =~ ^[1-9][0-9]*$ || ! "$nparticles" =~ ^[1-9][0-9]*$ ]]; then
  printf 'Usage: bash %s [nevents [nparticles]]\n' "$0" >&2
  exit 2
fi
run_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
kind="step13_rsu6"; (( nevents * nparticles < 5000000 )) && kind="step13_rsu6_smoke"
tag="${kind}_${run_stamp}"
run_dir="$proj/matmap/$tag"
git_log="$proj/logs/material_map_${tag}.txt"

# Geometry identity: frozen rsu6 overlay on top of the Step 13 install.
overlay_dir="$proj/geometry_overlays/step13/rsu6"
overlay_xml="$overlay_dir/epic_craterlake_tracking_only_rsu6.xml"
overlay_modules="$overlay_dir/silicon_disks_modules_rsu6.xml"
export DETECTOR_CONFIG="../../../proj_svt_disk_tiling/geometry_overlays/step13/rsu6/epic_craterlake_tracking_only_rsu6"
xml="${DETECTOR_PATH:-}/${DETECTOR_CONFIG}.xml"
expected_overlay_xml_sha="453fda16a335bb8735e8e6f616ba16f5f4970b573417818691bc0afa5ec19065"      # provenance_step14a.txt
expected_overlay_modules_sha="7bfe44276ceffc81989055f504f4f331c8970a99b99368f0a126a9e099c95567"  # provenance_step14a.txt
expected_module_count=2150                                                                       # 20261110_ES/rsu6
expected_head="78ade46865d06250fe601c5b56189e37735f75b1"                             # Step 13 freeze
expected_modules_sha="6d04bd66e5524c9cbdfec34c0e15064463af2000501a925063dc577ccfd1b27b"  # freeze_install_step13.txt
expected_libepic_sha="9ccf1a6690903c009fe167383d14eb81c170c2ed29d212d674a6c73886e5cc87"  # freeze_install_step13.txt
[[ "$DETECTOR_PATH" == "$repo_root/install/share/epic" ]] || { echo "ERROR: DETECTOR_PATH must be $repo_root/install/share/epic" >&2; exit 1; }
[[ -f "$xml" ]] || { echo "ERROR: $xml missing; enter eic-shell and source install/bin/thisepic.sh" >&2; exit 1; }
[[ "$(readlink -f "$xml")" == "$overlay_xml" ]] || { echo "ERROR: $xml does not resolve to $overlay_xml" >&2; exit 1; }
[[ "$(sha256sum "$overlay_xml" | cut -d' ' -f1)" == "$expected_overlay_xml_sha" ]] || { echo "ERROR: $overlay_xml is not the frozen Step 14a overlay" >&2; exit 1; }
[[ "$(sha256sum "$overlay_modules" | cut -d' ' -f1)" == "$expected_overlay_modules_sha" ]] || { echo "ERROR: $overlay_modules is not the frozen Step 14a overlay" >&2; exit 1; }
[[ "$(git -C "$repo_root" rev-parse HEAD)" == "$expected_head" ]] || { echo "ERROR: EPIC HEAD is not $expected_head" >&2; exit 1; }
cmp -s "$repo_root/compact/tracking/silicon_disks_modules.xml" "$DETECTOR_PATH/compact/tracking/silicon_disks_modules.xml" \
  || { echo "ERROR: installed SVT module XML differs from the checkout" >&2; exit 1; }
[[ "$(sha256sum "$DETECTOR_PATH/compact/tracking/silicon_disks_modules.xml" | cut -d' ' -f1)" == "$expected_modules_sha" ]] \
  || { echo "ERROR: installed silicon_disks_modules.xml is not the Step 13 freeze" >&2; exit 1; }
libepic="$repo_root/install/lib/libepic.so"
[[ "$(sha256sum "$libepic" | cut -d' ' -f1)" == "$expected_libepic_sha" ]] \
  || { echo "ERROR: $libepic is not the Step 13 freeze" >&2; exit 1; }
[[ -z "$(git -C "$repo_root" status --short --untracked-files=no -- compact src)" ]] \
  || { echo "ERROR: uncommitted geometry changes in compact/ or src/" >&2; exit 1; }
acts_version="$(python -c 'import acts; v = acts.version; print(f"{v.major}.{v.minor}.{v.patch}")')"
[[ "$acts_version" == "46.8.1" ]] || { echo "ERROR: ACTS $acts_version, expected 46.8.1 (26.09.0-stable)" >&2; exit 1; }
[[ ! -e "$run_dir" && ! -e "$git_log" ]] || { echo "ERROR: $run_dir exists; retry" >&2; exit 1; }

# Run directory: link the runner's inputs (python drivers, cached and already patched ACTS
# example scripts, ACTS patch files so the runner does not re-download/re-apply them,
# DD4hep calibration/fieldmap caches). Outputs are then written here only.
mkdir -p "$run_dir"
for input in Examples epic.py geometry_epic.py material_mapping_epic.py material_recording_epic.py \
             material_validation_epic.py materialmap_config.py 6010.diff 6012.diff calibrations fieldmaps; do
  [[ -e "$material_dir/$input" ]] || { echo "ERROR: runner input $material_dir/$input missing" >&2; exit 1; }
  ln -s "$material_dir/$input" "$run_dir/$input"
done
cd "$run_dir"

{
  printf 'tag=%s\nhost=%s\nSLURM_JOB_ID=%s\n' "$tag" "$(hostname)" "${SLURM_JOB_ID:-none}"
  printf 'EPIC HEAD=%s\nDETECTOR_PATH=%s\nDETECTOR_CONFIG=%s\nACTS=%s\nsamples=%s events x %s geantinos\n' \
    "$(git -C "$repo_root" rev-parse HEAD)" "$DETECTOR_PATH" "$DETECTOR_CONFIG" "$acts_version" "$nevents" "$nparticles"
  printf 'container=%s\n' "${EIC_SHELL_PREFIX:-eic_xl:26.09.0-stable (refplanes/eic_exec.sh)}"
  sha256sum "$xml" "$DETECTOR_PATH/compact/tracking/silicon_disks_modules.xml" \
    "$DETECTOR_PATH/compact/tracking/definitions_craterlake.xml" "$libepic" \
    "$overlay_xml" "$overlay_modules" "$overlay_dir/provenance_step14a.txt" \
    "$material_dir/run_material_map_validation.sh" "$proj/logs/regenerate_svt_material_map_step13_rsu6.sh" \
    "$proj/logs/count_svt_modules_step14a.py"
} > provenance.txt

exec > >(tee run_log.txt) 2>&1
printf 'SVT %s material-map regeneration in %s\n' "$kind" "$run_dir"
cat provenance.txt

# Prove the geometry: load the same XML from the same working directory and count the modules.
python "$proj/logs/count_svt_modules_step14a.py" "$xml" "$expected_module_count" 2>&1 | grep -A1 'SVT_MODULE_COUNT\|ERROR: expected'
[[ "${PIPESTATUS[0]}" -eq 0 ]] || { echo "ERROR: SVT module count check failed" >&2; exit 1; }

# Skip validation with the old calibrations/materials-map: it belongs to a different geometry
# (and the ACTS bindings rejected its binning in Step 8m).
time bash "$material_dir/run_material_map_validation.sh" \
  --nevents "$nevents" --nparticles "$nparticles" --skip-current-map-validation

map_file="$run_dir/material-map_map.cbor"
test -s "$map_file" || { echo "ERROR: missing/empty map: $map_file" >&2; exit 1; }
printf 'Completed map: %s\n' "$map_file"
sha256sum "$map_file" | tee -a provenance.txt
echo 'Review the validation plots (Validation/regenerated, Surfaces/) before reconstruction.'
cp run_log.txt "$git_log"
