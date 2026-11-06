#!/usr/bin/env bash
# Step 8q: regenerate the ACTS material map from epic_craterlake_tracking_only.xml, the same
# XML used by the acceptance_v3_refplanes npsim campaign (without its zero-material,
# non-ACTS reference-plane overlay) and by the planned EICrecon reprocessing.
# Differs from the Step 8m wrapper in the geometry checks, in exporting
# DETECTOR_CONFIG=epic_craterlake_tracking_only (Step 8m mapped epic_craterlake_material_map,
# which adds DIRC/pfRICH/dRICH and other beamline/far-backward includes), and in the
# output layout (below).
#
# Output layout (like matscan/): everything from one run goes to its own directory
#   proj_svt_disk_tiling/matmap/<tag>/        tag = step8q_<UTC stamp> or step8q_smoke_<UTC stamp>
#     material-map_map.cbor                   <- the map to give EICrecon (-Pacts:MaterialMap=...)
#     provenance.txt, run_log.txt             geometry/software identity, full transcript
#     *.root, *.json, plots/ Validation/ Surfaces/   intermediate products and validation plots
#     (symlinks)                              runner inputs from scripts/material_map/
# The upstream runner writes fixed file and directory names into its working directory, so it
# is run with the run directory as working directory; nothing is written into
# scripts/material_map/ and no earlier run is overwritten. The transcript is also copied to
# proj_svt_disk_tiling/logs/material_map_<tag>.txt (tracked in git).
#
# Run inside eic_xl:26.09.0-stable with install/bin/thisepic.sh sourced, e.g.
#   proj_svt_disk_tiling/refplanes/eic_exec.sh "bash proj_svt_disk_tiling/logs/regenerate_svt_material_map_step8q.sh 10 100"
# Usage: regenerate_svt_material_map_step8q.sh [nevents [nparticles]]   (default 1000 x 5000, as Step 8m)
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
kind="step8q"; (( nevents * nparticles < 5000000 )) && kind="step8q_smoke"
tag="${kind}_${run_stamp}"
run_dir="$proj/matmap/$tag"
git_log="$proj/logs/material_map_${tag}.txt"

# Geometry identity: the map must come from the exact XML/commit used for the v3 simulation.
export DETECTOR_CONFIG="epic_craterlake_tracking_only"
xml="${DETECTOR_PATH:-}/${DETECTOR_CONFIG}.xml"
expected_xml_sha="c0141309c5f618eafdeacb66b4d8174d05e2dab815ed5c07ba947f5570bfb4fd"  # refplanes/generated/*.provenance.txt
expected_head="311634084f0ff4229c25d6e8cadb6ff9c497c5d8"                             # Step 8q, v3 sim
[[ -f "$xml" ]] || { echo "ERROR: $xml missing; enter eic-shell and source install/bin/thisepic.sh" >&2; exit 1; }
[[ "$(sha256sum "$xml" | cut -d' ' -f1)" == "$expected_xml_sha" ]] || { echo "ERROR: installed $xml differs from the v3 simulation XML" >&2; exit 1; }
[[ "$(git -C "$repo_root" rev-parse HEAD)" == "$expected_head" ]] || { echo "ERROR: EPIC HEAD is not $expected_head" >&2; exit 1; }
cmp -s "$repo_root/compact/tracking/silicon_disks_modules.xml" "$DETECTOR_PATH/compact/tracking/silicon_disks_modules.xml" \
  || { echo "ERROR: installed SVT module XML differs from the checkout" >&2; exit 1; }
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
    "$DETECTOR_PATH/compact/tracking/definitions_craterlake.xml" "$material_dir/run_material_map_validation.sh" \
    "$proj/logs/regenerate_svt_material_map_step8q.sh"
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
