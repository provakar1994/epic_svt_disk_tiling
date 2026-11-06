#!/usr/bin/env bash
# Regenerate the ACTS map for the installed three-layer SVT endcap geometry.
# Run inside the EIC shell after installing this checkout; does not start by itself.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
material_dir="$repo_root/scripts/material_map"
project_tmp="$repo_root/proj_svt_disk_tiling/tmp"
run_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
prefix="step8m_${run_stamp}_"
run_log="$repo_root/proj_svt_disk_tiling/logs/material_map_step8m_${run_stamp}.txt"
archive_dir="$project_tmp/retained/$(date -u +%Y-%m-%d)/material_map_plots_before_${run_stamp}"
nevents="${1:-1000}"
nparticles="${2:-5000}"

if [[ $# -gt 2 || ! "$nevents" =~ ^[1-9][0-9]*$ || ! "$nparticles" =~ ^[1-9][0-9]*$ ]]; then
  printf 'Usage: bash %s [nevents [nparticles]]\n' "$0" >&2
  exit 2
fi
if [[ -z "${DETECTOR_PATH:-}" || ! -f "$DETECTOR_PATH/epic_craterlake_material_map.xml" ]]; then
  printf '%s\n' 'ERROR: enter the EIC shell and source install/bin/thisepic.sh first.' >&2
  exit 1
fi
installed_module="$DETECTOR_PATH/compact/tracking/silicon_disks_modules.xml"
source_module="$repo_root/compact/tracking/silicon_disks_modules.xml"
if [[ ! -f "$installed_module" ]]; then
  printf 'ERROR: installed SVT module XML is missing: %s\n' "$installed_module" >&2
  exit 1
fi
cmp "$source_module" "$installed_module" || {
  printf '%s\n' 'ERROR: installed SVT module XML differs from this checkout; rebuild/install first.' >&2
  exit 1
}
grep -Fq 'silicon_disks_modules.xml' "$DETECTOR_PATH/epic_craterlake_material_map.xml" || {
  printf '%s\n' 'ERROR: material-map XML does not include the SVT module builder.' >&2
  exit 1
}
grep -Fq '20261001_ES/rsu_opt' "$installed_module" || {
  printf '%s\n' 'ERROR: installed SVT placement is not rsu_opt.' >&2
  exit 1
}
grep -Eq 'name="SiEndcapTilingRSUCu_thickness"[[:space:]]+value="2\.5\*um"' "$installed_module" || {
  printf '%s\n' 'ERROR: installed SVT does not have the Step 8l copper thickness.' >&2
  exit 1
}
grep -Eq 'name="SiEndcapTilingInwardModule_z_clearance"[[:space:]]+value="0\.0325\*mm"' "$installed_module" || {
  printf '%s\n' 'ERROR: installed SVT does not have the Step 8l inward clearance.' >&2
  exit 1
}
if [[ ! -f "$material_dir/Examples/Scripts/Python/material_recording.py" ]]; then
  printf '%s\n' 'ERROR: cached ACTS material-map example scripts are missing.' >&2
  exit 1
fi
for program in python root; do
  if ! command -v "$program" >/dev/null; then
    printf 'ERROR: %s is not on PATH; enter the 26.09.0-stable EIC shell.\n' "$program" >&2
    exit 1
  fi
done

if [[ -e "$run_log" || -e "$archive_dir" ||
      -e "$material_dir/${prefix}geant4_material_tracks.root" ]]; then
  printf '%s\n' 'ERROR: a run with this timestamp already exists; retry after one second.' >&2
  exit 1
fi

# The upstream runner recreates these fixed-name plot directories. Retain them
# before invoking it; timestamp-prefixed ROOT/CBOR/JSON outputs stay in place.
mkdir -p "$archive_dir"
for output_dir in plots Validation Surfaces; do
  if [[ -e "$material_dir/$output_dir" ]]; then
    mv "$material_dir/$output_dir" "$archive_dir/$output_dir"
    printf '%s | scripts/material_map/%s/ | %s/%s/ | move | retain prior plots before Step 8m map\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$output_dir" \
      "${archive_dir#"$repo_root/"}" "$output_dir" >> "$project_tmp/file_actions.log"
  fi
done

cd "$material_dir"
exec > >(tee "$run_log") 2>&1
printf 'SVT Step 8m material-map regeneration: %s\n' "$run_stamp"
printf 'HEAD=%s\nDETECTOR_PATH=%s\nSamples=%s x %s\nPrefix=%s\n' \
  "$(git -C "$repo_root" rev-parse HEAD)" "$DETECTOR_PATH" "$nevents" "$nparticles" "$prefix"
printf 'Prior plots retained at %s\n' "$archive_dir"
sha256sum "$DETECTOR_PATH/epic_craterlake_material_map.xml" "$installed_module" \
  "$DETECTOR_PATH/compact/tracking/definitions_craterlake.xml" \
  "$material_dir/run_material_map_validation.sh"

# Validate the regenerated map, but skip the older calibration map: the current
# ACTS bindings reject its cylinder-axis binning (documented in the rerun guide).
bash ./run_material_map_validation.sh \
  --nevents "$nevents" --nparticles "$nparticles" --prefix "$prefix" \
  --skip-current-map-validation

map_file="$material_dir/${prefix}material-map_map.cbor"
test -s "$map_file" || {
  printf 'ERROR: missing/empty regenerated map: %s\n' "$map_file" >&2
  exit 1
}
printf 'Completed map: %s\n' "$map_file"
sha256sum "$map_file"
printf '%s\n' 'Review the validation plots and any envelope26 warning before reconstruction.'
