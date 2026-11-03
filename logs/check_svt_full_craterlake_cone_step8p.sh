#!/usr/bin/env bash
# Run inside eic-shell 26.09.0-stable after editing the cone clearance.
# Build the full craterlake configuration, then reproduce its CI overlap checks.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
run_stamp="$(date -u '+%Y%m%dT%H%M%SZ')"
report_dir="$repo_root/proj_svt_disk_tiling/tmp/full_craterlake_overlap_$run_stamp"
mkdir -p "$report_dir"
cd "$repo_root"

printf 'Report directory: %s\n' "$report_dir"
printf 'Branch commit: %s\n' "$(git rev-parse --short HEAD)"
trap 'status=$?; printf "Stopped at line %s (exit %s); inspect %s\n" "$LINENO" "$status" "$report_dir" >&2' ERR
printf 'Checking git diff...\n'
git diff --check

printf 'Configuring CMake; log: %s/configure.log\n' "$report_dir"
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=install -DEPIC_ECCE_LEGACY_COMPAT=OFF \
    > "$report_dir/configure.log" 2>&1
printf 'Building; log: %s/build.log\n' "$report_dir"
cmake --build build -j4 > "$report_dir/build.log" 2>&1
printf 'Installing; log: %s/install.log\n' "$report_dir"
cmake --install build > "$report_dir/install.log" 2>&1
printf 'Loading installed detector environment...\n'
source "$repo_root/install/bin/thisepic.sh"

compact_file="$DETECTOR_PATH/epic_craterlake.xml"
test -f "$compact_file"
grep -Fq 'silicon_disks_modules.xml' "$compact_file"
grep -Fq 'support_service_craterlake.xml' "$compact_file"
printf 'Checking %s\n' "$compact_file"

# CI: check-overlap-tgeo, option m, tolerance 0.01 mm.
printf 'Running ROOT overlap check; log: %s/root_overlap.log\n' "$report_dir"
checkOverlaps --option m --tolerance 0.01 -c "$compact_file" \
    > "$report_dir/root_overlap.log" 2>&1
root_count="$(grep -c 'ovlp' "$report_dir/root_overlap.log" || true)"
printf 'ROOT overlap lines: %s\n' "$root_count"

# CI: check-overlap-geant4, tolerance 0.1 mm. This can take a long time.
printf 'Running Geant4 overlap check; log: %s/geant4_overlap.log\n' "$report_dir"
python scripts/checkOverlaps.py -t 0.1 -c "$compact_file" \
    > "$report_dir/geant4_overlap.log" 2>&1
geant_count="$(grep -c 'GeomVol1002' "$report_dir/geant4_overlap.log" || true)"
printf 'Geant4 overlap warnings: %s\n' "$geant_count"

if (( root_count > 0 || geant_count > 0 )); then
    printf 'Overlap check failed; inspect reports in %s\n' "$report_dir" >&2
    exit 1
fi
printf 'Full epic_craterlake overlap checks passed.\n'
