#!/usr/bin/env bash
# Step 8q: regenerate the ACTS material map from epic_craterlake_tracking_only.xml, the same
# XML used by the acceptance_v3_refplanes npsim campaign (without its zero-material,
# non-ACTS reference-plane overlay) and by the planned EICrecon reprocessing.
# Differs from the Step 8m wrapper only in the geometry checks and in exporting
# DETECTOR_CONFIG=epic_craterlake_tracking_only (Step 8m mapped epic_craterlake_material_map,
# which adds DIRC/pfRICH/dRICH and other beamline/far-backward includes).
#
# Run inside eic_xl:26.09.0-stable with install/bin/thisepic.sh sourced, e.g.
#   proj_svt_disk_tiling/refplanes/eic_exec.sh "bash proj_svt_disk_tiling/logs/regenerate_svt_material_map_step8q.sh 10 100"
# Usage: regenerate_svt_material_map_step8q.sh [nevents [nparticles]]   (default 1000 x 5000, as Step 8m)
set -euo pipefail

repo_root="/global/cfs/cdirs/m3763/pdatta/epic"
material_dir="$repo_root/scripts/material_map"
project_tmp="$repo_root/proj_svt_disk_tiling/tmp"
nevents="${1:-1000}"
nparticles="${2:-5000}"
if [[ $# -gt 2 || ! "$nevents" =~ ^[1-9][0-9]*$ || ! "$nparticles" =~ ^[1-9][0-9]*$ ]]; then
  printf 'Usage: bash %s [nevents [nparticles]]\n' "$0" >&2
  exit 2
fi
run_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
kind="step8q"; (( nevents * nparticles < 5000000 )) && kind="step8q_smoke"
prefix="${kind}_${run_stamp}_"
run_log="$repo_root/proj_svt_disk_tiling/logs/material_map_${kind}_${run_stamp}.txt"
archive_dir="$project_tmp/retained/$(date -u +%Y-%m-%d)/material_map_plots_before_${run_stamp}"

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
[[ ! -e "$run_log" && ! -e "$material_dir/${prefix}geant4_material_tracks.root" ]] \
  || { echo "ERROR: a run with this timestamp exists; retry" >&2; exit 1; }

# The runner recreates fixed-name plot directories; retain the previous ones first.
mkdir -p "$archive_dir"
for output_dir in plots Validation Surfaces; do
  if [[ -e "$material_dir/$output_dir" ]]; then
    mv "$material_dir/$output_dir" "$archive_dir/$output_dir"
    printf '%s | scripts/material_map/%s/ | %s/%s/ | move | retain prior plots before %s map\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$output_dir" "${archive_dir#"$repo_root/"}" "$output_dir" "$kind" \
      >> "$project_tmp/file_actions.log"
  fi
done

cd "$material_dir"
exec > >(tee "$run_log") 2>&1
printf 'SVT %s material-map regeneration: %s\n' "$kind" "$run_stamp"
printf 'Host=%s SLURM_JOB_ID=%s\n' "$(hostname)" "${SLURM_JOB_ID:-none}"
printf 'HEAD=%s\nDETECTOR_PATH=%s\nDETECTOR_CONFIG=%s\nACTS=%s\nSamples=%s x %s\nPrefix=%s\n' \
  "$(git -C "$repo_root" rev-parse HEAD)" "$DETECTOR_PATH" "$DETECTOR_CONFIG" "$acts_version" \
  "$nevents" "$nparticles" "$prefix"
printf 'Prior plots retained at %s\n' "$archive_dir"
sha256sum "$xml" "$DETECTOR_PATH/compact/tracking/silicon_disks_modules.xml" \
  "$DETECTOR_PATH/compact/tracking/definitions_craterlake.xml" "$material_dir/run_material_map_validation.sh"

# Skip validation with the old calibrations/materials-map: it belongs to a different geometry
# (and the ACTS bindings rejected its binning in Step 8m).
time bash ./run_material_map_validation.sh \
  --nevents "$nevents" --nparticles "$nparticles" --prefix "$prefix" \
  --skip-current-map-validation

map_file="$material_dir/${prefix}material-map_map.cbor"
test -s "$map_file" || { echo "ERROR: missing/empty map: $map_file" >&2; exit 1; }
printf 'Completed map: %s\n' "$map_file"
sha256sum "$map_file"
echo 'Review the validation plots (Validation/regenerated, Surfaces/) before reconstruction.'
