#!/usr/bin/env bash
# Step 14a: frozen 20261110_ES/rsu6 overlay for the rsu6 material map and per-disk scan
# (shared with the parallel rsu6 campaign; reuse, do not regenerate, if it already exists).
#   1. make_svt_overlay.sh 20261110_ES rsu6 with OVERLAY_ROOT=geometry_overlays/step13
#      -> silicon_disks_modules_rsu6.xml, epic_craterlake_tracking_only_rsu6.xml, epic_craterlake_rsu6.xml
#   2. epic_craterlake_material_map_rsu6.xml: the installed epic_craterlake_material_map.xml with the
#      same substitution (SVT modules include -> overlay modules XML by absolute path); the diff
#      against the installed file must be exactly that one include line (checked for all 3 top-level XMLs).
#   3. provenance_step14a.txt: sha256 of every file in the directory + the diffs.
# Run on the host from the EPIC repo root (no container needed). Install is the Step 13 freeze.
set -euo pipefail
epic=/global/cfs/cdirs/m3763/pdatta/epic
proj="$epic/proj_svt_disk_tiling"
dp="$epic/install/share/epic"
overlay_root="$proj/geometry_overlays/step13"
out="$overlay_root/rsu6"
mods="$out/silicon_disks_modules_rsu6.xml"
prov="$out/provenance_step14a.txt"

if [[ -e "$out" ]]; then
  echo "$out already exists; reusing (check its provenance.txt / provenance_step14a.txt)"
else
  DETECTOR_PATH="$dp" OVERLAY_ROOT="$overlay_root" bash "$proj/logs/make_svt_overlay.sh" 20261110_ES rsu6
fi

mm="$out/epic_craterlake_material_map_rsu6.xml"
if [[ ! -e "$mm" ]]; then
  sed "s|\\\${DETECTOR_PATH}/compact/tracking/silicon_disks_modules.xml|$mods|" \
    "$dp/epic_craterlake_material_map.xml" > "$mm.tmp"
  grep -qF "\"$mods\"" "$mm.tmp" || { echo "ERROR: include not redirected in $mm" >&2; exit 1; }
  mv "$mm.tmp" "$mm"
fi

# Verify: each top-level overlay differs from its installed source by exactly one line (the include).
check_one() {  # $1 installed, $2 overlay
  local d n_minus n_plus
  d="$(diff "$1" "$2" || true)"
  n_minus=$(grep -c '^<' <<< "$d" || true); n_plus=$(grep -c '^>' <<< "$d" || true)
  echo "diff $1 $2"; echo "$d" | sed 's/^/    /'
  [[ $n_minus -eq 1 && $n_plus -eq 1 ]] && grep -q 'silicon_disks_modules' <<< "$d" \
    || { echo "ERROR: unexpected diff for $2" >&2; exit 1; }
}
{
  echo "Step 14a frozen rsu6 overlay, checked $(date -u --iso-8601=seconds) by $0"
  echo "EPIC HEAD=$(git -C "$epic" rev-parse HEAD)"
  check_one "$dp/epic_craterlake_tracking_only.xml" "$out/epic_craterlake_tracking_only_rsu6.xml"
  check_one "$dp/epic_craterlake.xml" "$out/epic_craterlake_rsu6.xml"
  check_one "$dp/epic_craterlake_material_map.xml" "$mm"
  echo "diff installed modules XML vs overlay modules XML (rsu_opt -> rsu6 path components only):"
  diff "$dp/compact/tracking/silicon_disks_modules.xml" "$mods" | sed 's/^/    /' || true
  echo "installed inputs sha256:"
  sha256sum "$dp/compact/tracking/silicon_disks_modules.xml" "$dp/epic_craterlake_tracking_only.xml" \
    "$dp/epic_craterlake.xml" "$dp/epic_craterlake_material_map.xml" "$epic/install/lib/libepic.so" | sed 's/^/  /'
  echo "rsu6 tiling directory (combined sha256 over sorted files):"
  echo "  $( (cd "$dp/compact/tracking/silicon_disks_tiling/20261110_ES/rsu6" && find . -maxdepth 1 -type f | sort | xargs sha256sum) | sha256sum | cut -d' ' -f1)"
  echo "overlay sha256:"
  sha256sum "$mods" "$out/epic_craterlake_tracking_only_rsu6.xml" "$out/epic_craterlake_rsu6.xml" "$mm" | sed 's/^/  /'
} > "$prov.tmp"
mv "$prov.tmp" "$prov"
cat "$prov"
