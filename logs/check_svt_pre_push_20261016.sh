#!/usr/bin/env bash
# Run inside ./eic-shell --version 26.09.0-stable before pushing si_disk_hole.
# Build the active rsu_opt geometry, export it, and check ROOT and Geant4 overlaps.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
run_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
log_file="$repo_root/proj_svt_disk_tiling/logs/check_svt_pre_push_${run_stamp}.txt"
root_log="$repo_root/proj_svt_disk_tiling/logs/check_svt_pre_push_root_${run_stamp}.txt"
geant_log="$repo_root/proj_svt_disk_tiling/logs/check_svt_pre_push_geant_${run_stamp}.txt"
display_file="$repo_root/proj_svt_disk_tiling/out/visualize_pre_push_${run_stamp}.root"
cd "$repo_root"
mkdir -p proj_svt_disk_tiling/out
exec > >(tee "$log_file") 2>&1

printf 'SVT pre-push check: %s\n' "$run_stamp"
printf 'Commit: %s\n' "$(git rev-parse HEAD)"
printf 'Transcript: %s\n' "$log_file"
printf 'ROOT report: %s\n' "$root_log"
printf 'Geant4 report: %s\n' "$geant_log"
printf 'Visualization: %s\n' "$display_file"

git diff --check
git diff --cached --check

for validator in \
  validate_svt_module_params_step4a.py \
  validate_svt_module_builder_step4b.py \
  validate_svt_placement_transform_step5b.py \
  validate_svt_corrugation_lattice_step7b.py \
  validate_svt_explicit_corrugation_builder_step7c.py \
  validate_svt_scenario_activation_step7d.py \
  validate_svt_engineer_to_epic_step7v.py \
  validate_svt_xml_radius_authority_step7w.py \
  validate_svt_tiling_delivery_layout_step7x.py \
  validate_svt_physical_openings_step7z.py \
  validate_svt_fpc_registration_step8d.py \
  validate_svt_module_z_offsets_step8f.py \
  validate_svt_restored_corrugation_step8g.py \
  validate_svt_central_corrugation_web_step8h.py \
  validate_svt_closed_corrugation_y_gaps_step8i.py; do
  printf '\n=== %s ===\n' "$validator"
  python3 -B "proj_svt_disk_tiling/logs/$validator"
done

printf '\n=== Configure, build, and install ===\n'
cmake -B build -S . -DCMAKE_INSTALL_PREFIX=install -DEPIC_ECCE_LEGACY_COMPAT=OFF
cmake --build build -j4
cmake --install build
source "$repo_root/install/bin/thisepic.sh"

detector_config="$DETECTOR_PATH/epic_craterlake_tracking_only_disk_modules.xml"
relative_lattice="compact/tracking/silicon_disks_tiling/20261001_ES/SVT_endcap_corrugation_rows_33_36.csv"
test -f "$detector_config"
cmp "$repo_root/compact/tracking/silicon_disks_modules.xml" \
    "$DETECTOR_PATH/compact/tracking/silicon_disks_modules.xml"
cmp "$repo_root/$relative_lattice" "$DETECTOR_PATH/$relative_lattice"

printf '\n=== Export geometry for visual review ===\n'
dd_web_display -o "$display_file" --export "$detector_config"

printf '\n=== ROOT overlap check, 0.01 mm tolerance ===\n'
checkOverlaps --option m --t 0.01 -c "$detector_config" 2>&1 | tee "$root_log"

printf '\n=== Geant4 overlap check, established defaults ===\n'
python scripts/checkOverlaps.py -c "$detector_config" 2>&1 | tee "$geant_log"

if ! grep -Fq 'Number of illegal overlaps/extrusions : 0' "$root_log"; then
  printf '%s\n' 'FAIL: ROOT did not report zero illegal overlaps/extrusions.' >&2
  exit 1
fi
if ! grep -Fq 'Geometry overlaps check completed !' "$geant_log"; then
  printf '%s\n' 'FAIL: Geant4 did not report a completed overlap check.' >&2
  exit 1
fi
if grep -Eq 'G4Exception|Overlap is detected|^[[:space:]]*Overlap ov[0-9]+' "$geant_log"; then
  printf '%s\n' 'REVIEW: an overlap warning appears in the transcript.' >&2
  exit 1
fi

printf '\nPASS: static checks, build/install, ROOT, and Geant4 overlap scan.\n'
printf 'Visual review remains: %s\n' "$display_file"
printf 'Transcript: %s\n' "$log_file"
