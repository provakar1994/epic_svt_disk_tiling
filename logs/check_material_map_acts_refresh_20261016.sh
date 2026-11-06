#!/usr/bin/env bash
# Run a small material-map validation in the EIC shell without replacing prior outputs.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
material_dir="$repo_root/scripts/material_map"
project_tmp="$repo_root/proj_svt_disk_tiling/tmp"
action_log="$project_tmp/file_actions.log"
run_stamp="$(date -u '+%Y%m%dT%H%M%SZ')"
prefix="smoke_${run_stamp}_"
archive_dir="$project_tmp/retained/2026-10-16/material_map_plots_before_${run_stamp}"
run_log="$repo_root/proj_svt_disk_tiling/logs/check_material_map_acts_refresh_${run_stamp}.txt"

if [[ -z "${DETECTOR_PATH:-}" || ! -f "$DETECTOR_PATH/epic_craterlake_material_map.xml" ]]; then
  printf '%s\n' 'ERROR: source the local EPIC setup; DETECTOR_PATH must contain epic_craterlake_material_map.xml.' >&2
  exit 1
fi
if ! grep -Fq 'compact/tracking/silicon_disks_modules.xml' "$DETECTOR_PATH/epic_craterlake_material_map.xml"; then
  printf '%s\n' 'ERROR: the installed material-map XML does not include silicon_disks_modules.xml.' >&2
  exit 1
fi
if [[ -e "$archive_dir" || -e "$run_log" ]]; then
  printf '%s\n' 'ERROR: generated archive or log name already exists; rerun in a new second.' >&2
  exit 1
fi
if [[ ! -f "$material_dir/Examples/Scripts/Python/material_recording.py" ]]; then
  printf '%s\n' 'ERROR: the ACTS examples have not been refreshed.' >&2
  exit 1
fi

cd "$material_dir"
mkdir -p "$archive_dir"
for output_dir in plots Validation Surfaces; do
  if [[ -e "$output_dir" ]]; then
    mv "$output_dir" "$archive_dir/$output_dir"
    printf '%s | scripts/material_map/%s/ | %s/%s/ | move | preserve plots before material-map smoke test\n' \
      "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$output_dir" \
      "${archive_dir#"$repo_root/"}" "$output_dir" >> "$action_log"
  fi
done

printf 'EIC material-map smoke test: %s\n' "$run_stamp" | tee "$run_log"
printf 'DETECTOR_PATH=%s\n' "$DETECTOR_PATH" | tee -a "$run_log"
printf 'Output prefix=%s\n' "$prefix" | tee -a "$run_log"
printf 'Earlier plots retained at %s\n' "$archive_dir" | tee -a "$run_log"
printf '%s\n' 'Existing calibration-map validation is skipped; regenerated-map validation remains enabled.' | tee -a "$run_log"
./run_material_map_validation.sh --nevents 10 --nparticles 100 --prefix "$prefix" --skip-current-map-validation 2>&1 | tee -a "$run_log"
