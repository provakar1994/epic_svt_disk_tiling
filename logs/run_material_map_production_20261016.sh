#!/usr/bin/env bash
# Generate a production-size material map using the installed rsu_opt geometry.
# Run inside the EIC shell after sourcing this EPIC checkout's setup_local.sh.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
material_dir="$repo_root/scripts/material_map"
project_tmp="$repo_root/proj_svt_disk_tiling/tmp"
run_stamp="$(date -u '+%Y%m%dT%H%M%SZ')"
prefix="production_${run_stamp}_"
archive_dir="$project_tmp/retained/$(date -u '+%Y-%m-%d')/material_map_plots_before_${run_stamp}"
run_log="$repo_root/proj_svt_disk_tiling/logs/material_map_production_${run_stamp}.txt"
detector_xml="${DETECTOR_PATH:-}/epic_craterlake_material_map.xml"
module_xml="${DETECTOR_PATH:-}/compact/tracking/silicon_disks_modules.xml"
definitions_xml="${DETECTOR_PATH:-}/compact/tracking/definitions_craterlake.xml"
tiling_dir="${DETECTOR_PATH:-}/compact/tracking/silicon_disks_tiling/20261001_ES"

if [[ -z "${DETECTOR_PATH:-}" || ! -f "$detector_xml" || ! -f "$module_xml" ]]; then
  echo 'ERROR: source setup_local.sh; DETECTOR_PATH must point to the installed EPIC geometry.' >&2
  exit 1
fi
if ! grep -Fq 'compact/tracking/silicon_disks_modules.xml' "$detector_xml"; then
  echo 'ERROR: the installed material-map geometry does not include silicon_disks_modules.xml.' >&2
  exit 1
fi
if ! grep -Fq 'compact/tracking/silicon_disks_tiling/20261001_ES/rsu_opt' "$module_xml"; then
  echo 'ERROR: the installed silicon-disk geometry does not select rsu_opt.' >&2
  exit 1
fi
if [[ ! -f "$definitions_xml" || ! -f "$tiling_dir/SVT_endcap_corrugation_rows_33_36.csv" ||
      ! -f "$tiling_dir/rsu_opt/catalog.csv" ]]; then
  echo 'ERROR: installed tracking definitions or rsu_opt tiling data are missing.' >&2
  exit 1
fi
if [[ ! -f "$material_dir/Examples/Scripts/Python/material_recording.py" ]]; then
  echo 'ERROR: the refreshed ACTS example scripts are missing.' >&2
  exit 1
fi
if [[ -e "$archive_dir" || -e "$run_log" || -e "$material_dir/${prefix}geant4_material_tracks.root" ]]; then
  echo 'ERROR: a run with this timestamp already exists; retry after one second.' >&2
  exit 1
fi

cd "$material_dir"
mkdir -p "$archive_dir"
for output_dir in plots Validation Surfaces; do
  if [[ -e "$output_dir" ]]; then
    mv "$output_dir" "$archive_dir/$output_dir"
    printf '%s | scripts/material_map/%s/ | %s/%s/ | move | preserve plots before production material-map run\n' \
      "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$output_dir" \
      "${archive_dir#"$repo_root/"}" "$output_dir" >> "$project_tmp/file_actions.log"
  fi
done

{
  printf 'Production material-map run: %s\n' "$run_stamp"
  printf 'Repository HEAD: %s\n' "$(git -C "$repo_root" rev-parse HEAD)"
  printf 'DETECTOR_PATH=%s\n' "$DETECTOR_PATH"
  printf 'Sampling: 1000 events x 5000 geantinos per event\n'
  printf 'Output prefix: %s\n' "$prefix"
  printf 'Previous plots retained at: %s\n' "$archive_dir"
  printf 'Existing calibration-map validation: skipped (known ACTS cylinder-axis mismatch)\n'
  printf 'Installed geometry checksums:\n'
  sha256sum "$detector_xml" "$module_xml" "$definitions_xml" \
    "$tiling_dir/SVT_endcap_corrugation_rows_33_36.csv" "$tiling_dir/rsu_opt/"*
  printf 'Runner checksum:\n'
  sha256sum "$material_dir/run_material_map_validation.sh"
  printf 'Uncommitted source changes at run start:\n'
  git -C "$repo_root" diff --name-only
  printf 'Caution: review the known envelope26 bounding-box warning before accepting this map.\n'
} | tee "$run_log"

if ./run_material_map_validation.sh \
    --nevents 1000 --nparticles 5000 --prefix "$prefix" \
    --skip-current-map-validation 2>&1 | tee -a "$run_log"; then
  map_file="${prefix}material-map_map.cbor"
  if [[ ! -s "$map_file" ]]; then
    printf 'ERROR: expected map is missing or empty: %s\n' "$map_file" | tee -a "$run_log" >&2
    exit 1
  fi
  printf 'Completed map: %s\n' "$material_dir/$map_file" | tee -a "$run_log"
  sha256sum "$map_file" | tee -a "$run_log"
  printf 'Review plots and the full transcript before using this map.\n' | tee -a "$run_log"
else
  run_status=$?
  printf 'ERROR: material-map runner exited with status %s; inspect %s\n' "$run_status" "$run_log" >&2
  exit "$run_status"
fi
