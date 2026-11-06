#!/usr/bin/env bash
# Exercise the NERSC ACTS patch workaround on copies, without changing the cache.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
material_dir="$repo_root/scripts/material_map"
archive_dir="$repo_root/proj_svt_disk_tiling/tmp/retained/$(date -u '+%Y-%m-%d')/material_map_patch_tests"
action_log="$repo_root/proj_svt_disk_tiling/tmp/file_actions.log"
test_workdir="$(mktemp -d "${TMPDIR:-/tmp}/acts-material-map-patch-test.XXXXXX")"
printf 'Patch test scratch: %s\n' "$test_workdir"

for patch_name in 6010.diff 6012.diff; do
  case "$patch_name" in
    6010.diff) target='Examples/Scripts/MaterialMapping/materialPlotHelper.cpp' ;;
    6012.diff) target='Examples/Scripts/Python/material_mapping.py' ;;
  esac
  patch_dir="$test_workdir/${patch_name%.diff}"
  mkdir -p "$patch_dir/$(dirname "$target")"
  cp "$material_dir/$target" "$patch_dir/$target"
  (cd "$patch_dir" && patch --forward -p1 --input="$material_dir/$patch_name" </dev/null)
  (cd "$patch_dir" && patch --dry-run --reverse -p1 --input="$material_dir/$patch_name" </dev/null >/dev/null)
  printf 'PASS: %s applies and reverses on a local scratch copy\n' "$patch_name"
done

mkdir -p "$archive_dir"
mv "$test_workdir" "$archive_dir/"
printf '%s | %s | %s | move | retain local ACTS patch staging test copies\n' \
  "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$test_workdir" \
  "${archive_dir#"$repo_root/"}/$(basename "$test_workdir")" >> "$action_log"
printf 'Retained test copies: %s/%s\n' "$archive_dir" "$(basename "$test_workdir")"
