#!/usr/bin/env bash
# Step 14b (acceptance_v4_step13_rsu6, 2026-11-13): frozen rsu6 tracking-only geometry overlay.
# Shared with the Step 14 material-map agent: OVERLAY_ROOT=proj_svt_disk_tiling/geometry_overlays/step13
# -> geometry_overlays/step13/rsu6/{silicon_disks_modules_rsu6.xml, epic_craterlake_tracking_only_rsu6.xml,
#    epic_craterlake_rsu6.xml, provenance.txt}
# If the directory already exists it is NOT regenerated: its provenance.txt is printed and checked
# (EPIC commit 78ade4686, replacement 20261110_ES/rsu_opt -> 20261110_ES/rsu6, output sha256 still match).
# Generation runs from this directory (not the repo root) with DETECTOR_PATH = epic/install/share/epic,
# after the Step 13 identity check. The shared tmp/scenario_overlay/ is not used.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
proj="$(cd "$here/../.." && pwd)"
epic="$(cd "$proj/.." && pwd)"
overlay_root="$proj/geometry_overlays/step13"
out="$overlay_root/rsu6"
"$proj/refplanes/step13/identity_check_step13.sh" >/dev/null || { echo "ERROR: Step 13 identity check failed" >&2; exit 2; }
if [[ -d "$out" ]]; then
  echo "Overlay exists, reusing: $out"
else
  cd "$here"
  DETECTOR_PATH="$epic/install/share/epic" OVERLAY_ROOT="$overlay_root" "$proj/logs/make_svt_overlay.sh" 20261110_ES rsu6
fi
cat "$out/provenance.txt"
bad=0
grep -q "EPIC commit: 78ade46865d06250fe601c5b56189e37735f75b1" "$out/provenance.txt" || { echo "FAIL: EPIC commit"; bad=1; }
grep -q "Replacement: 20261110_ES/rsu_opt -> 20261110_ES/rsu6" "$out/provenance.txt" || { echo "FAIL: replacement"; bad=1; }
for f in silicon_disks_modules_rsu6.xml epic_craterlake_tracking_only_rsu6.xml epic_craterlake_rsu6.xml; do
  want=$(grep " $out/$f\$" "$out/provenance.txt" | awk '{print $1}')
  have=$(sha256sum "$out/$f" | cut -d' ' -f1)
  [[ -n "$want" && "$want" == "$have" ]] && echo "  [ok] $f $have" || { echo "  [FAIL] $f $have (provenance: $want)"; bad=1; }
done
[[ "$bad" -eq 0 ]] && echo "Overlay provenance: PASS" || echo "Overlay provenance: FAIL"
exit "$bad"
