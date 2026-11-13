#!/usr/bin/env bash
# Step 13 (Step 13d): regenerate the ACTS material map for the Step 13 SVT endcap geometry
# (20261110_ES/rsu_opt tiling, delivered-row corrugation, FPC split on all modules, every bridge
# FPC pointing away from y = 0; EPIC 78ade4686, install frozen in logs/freeze_install_step13.txt).
# Copy of regenerate_svt_material_map_step8q.sh; differences: step13 tags, expected HEAD, and
# sha256 checks of the installed silicon_disks_modules.xml and libepic.so. The top-level
# epic_craterlake_tracking_only.xml sha is unchanged from Step 8q (it only includes other files),
# so it does not identify the geometry by itself; HEAD + module XML + libepic + clean src/compact do.
# DETECTOR_CONFIG=epic_craterlake_tracking_only, as Step 8q (the XML used by the v3 npsim campaign
# without its non-ACTS reference-plane overlay, and by the EICrecon reprocessing).
#
# Output layout (like matscan/): everything from one run goes to its own directory
#   proj_svt_disk_tiling/matmap/<tag>/        tag = step13_<UTC stamp> or step13_smoke_<UTC stamp>
#     material-map_map.cbor                   <- the map to give EICrecon (-Pacts:MaterialMap=...)
#     provenance.txt, run_log.txt             geometry/software identity, full transcript
#     *.root, *.json, plots/ Validation/ Surfaces/   intermediate products and validation plots
#     (symlinks)                              runner inputs from scripts/material_map/
# The upstream runner writes fixed file and directory names into its working directory, so it
# is run with the run directory as working directory; nothing is written into
# scripts/material_map/ and no earlier run is overwritten. The transcript is also copied to
# proj_svt_disk_tiling/logs/material_map_<tag>.txt (tracked in git).
# scripts/material_map/run_material_map_validation.sh carries an uncommitted local modification
# (same file as Step 8q, sha 99f36d28...); its sha is recorded in provenance.txt.
#
# Run inside eic_xl:26.09.0-stable with install/bin/thisepic.sh sourced, e.g.
#   proj_svt_disk_tiling/refplanes/eic_exec.sh "bash proj_svt_disk_tiling/logs/regenerate_svt_material_map_step13.sh 10 100"
# Usage: regenerate_svt_material_map_step13.sh [nevents [nparticles]]   (default 1000 x 5000, as Step 8q)
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
kind="step13"; (( nevents * nparticles < 5000000 )) && kind="step13_smoke"
tag="${kind}_${run_stamp}"
run_dir="$proj/matmap/$tag"
git_log="$proj/logs/material_map_${tag}.txt"

# Geometry identity: the map must come from the exact XML/commit used for the v3 simulation.
export DETECTOR_CONFIG="epic_craterlake_tracking_only"
xml="${DETECTOR_PATH:-}/${DETECTOR_CONFIG}.xml"
expected_xml_sha="c0141309c5f618eafdeacb66b4d8174d05e2dab815ed5c07ba947f5570bfb4fd"  # refplanes/generated/*.provenance.txt
expected_head="78ade46865d06250fe601c5b56189e37735f75b1"                             # Step 13 freeze
expected_modules_sha="6d04bd66e5524c9cbdfec34c0e15064463af2000501a925063dc577ccfd1b27b"  # freeze_install_step13.txt
expected_libepic_sha="9ccf1a6690903c009fe167383d14eb81c170c2ed29d212d674a6c73886e5cc87"  # freeze_install_step13.txt
[[ -f "$xml" ]] || { echo "ERROR: $xml missing; enter eic-shell and source install/bin/thisepic.sh" >&2; exit 1; }
[[ "$(sha256sum "$xml" | cut -d' ' -f1)" == "$expected_xml_sha" ]] || { echo "ERROR: installed $xml differs from the v3 simulation XML" >&2; exit 1; }
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
    "$material_dir/run_material_map_validation.sh" "$proj/logs/regenerate_svt_material_map_step13.sh"
} > provenance.txt

exec > >(tee run_log.txt) 2>&1
printf 'SVT %s material-map regeneration in %s\n' "$kind" "$run_dir"
cat provenance.txt

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
