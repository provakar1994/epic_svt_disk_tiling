#!/usr/bin/env bash
# Step 14b (acceptance_v4_step13_rsu6, 2026-11-13) geometry identity check for the rsu6 scenario.
#   1. refplanes/step13/identity_check_step13.sh (EPIC HEAD 78ade4686, silicon_disks_modules.xml 6d04bd66...,
#      libepic.so 9ccf1a66...; the install itself is the production rsu_opt one)
#   2. frozen rsu6 overlay proj_svt_disk_tiling/geometry_overlays/step13/rsu6/ (make_geometry_overlay_rsu6.sh):
#      provenance.txt says EPIC 78ade4686 and 20261110_ES/rsu_opt -> 20261110_ES/rsu6; the three overlay
#      XMLs have the sha256 recorded in provenance.txt AND the values frozen below (a regenerated overlay
#      with a different content fails); the installed 20261110_ES/rsu6 CSV/metadata combined sha256
#      (same recipe as make_svt_overlay.sh) matches.
# Usage: identity_check_step13_rsu6.sh   -> exit 0 if all match, 1 otherwise.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
proj="$(cd "$here/../.." && pwd)"
epic="$(cd "$proj/.." && pwd)"
ov="$proj/geometry_overlays/step13/rsu6"
prov="$ov/provenance.txt"
expected_tracking=453fda16a335bb8735e8e6f616ba16f5f4970b573417818691bc0afa5ec19065
expected_modules=7bfe44276ceffc81989055f504f4f331c8970a99b99368f0a126a9e099c95567
expected_full=7c9e04c1c01506389f292ea042e57e09fdba8bec2e28683af27a95858911f7bb
expected_scenario=e4d6cc88b60290f24a44965a03f284f830c9b60052716ebbc3648bc8a6d389dd
bad=0
compare() {  # label actual expected
  if [[ "$2" == "$3" ]]; then echo "  [ok]   $1 = $2"; else echo "  [FAIL] $1 = $2 (expected $3)"; bad=1; fi
}
"$proj/refplanes/step13/identity_check_step13.sh" || bad=1
echo "rsu6 overlay check: $ov"
[[ -f "$prov" ]] || { echo "  [FAIL] missing $prov"; echo "Identity rsu6: FAIL"; exit 1; }
compare "provenance EPIC commit" "$(sed -n 's/^EPIC commit: \([0-9a-f]*\).*/\1/p' "$prov")" 78ade46865d06250fe601c5b56189e37735f75b1
compare "provenance replacement" "$(sed -n 's/^Replacement: //p' "$prov")" "20261110_ES/rsu_opt -> 20261110_ES/rsu6"
compare "provenance source silicon_disks_modules.xml" \
  "$(grep '/install/share/epic/compact/tracking/silicon_disks_modules.xml$' "$prov" | awk '{print $1}')" \
  6d04bd66e5524c9cbdfec34c0e15064463af2000501a925063dc577ccfd1b27b
for pair in "epic_craterlake_tracking_only_rsu6.xml:$expected_tracking" \
            "silicon_disks_modules_rsu6.xml:$expected_modules" "epic_craterlake_rsu6.xml:$expected_full"; do
  f="${pair%%:*}"; want="${pair#*:}"
  compare "provenance sha256 $f" "$(grep " $ov/$f\$" "$prov" | awk '{print $1}')" "$want"
  compare "actual sha256 $f" "$(sha256sum "$ov/$f" | cut -d' ' -f1)" "$want"
done
sdir="$epic/install/share/epic/compact/tracking/silicon_disks_tiling/20261110_ES/rsu6"
scen_sha="$( (cd "$sdir" && for f in *; do [[ -f "$f" ]] && echo "./$f"; done | sort | xargs sha256sum) | sha256sum | cut -d' ' -f1)"
compare "installed 20261110_ES/rsu6 combined sha256" "$scen_sha" "$expected_scenario"
echo "  provenance.txt sha256 = $(sha256sum "$prov" | cut -d' ' -f1)"
echo "  module_placements in overlay: $(grep -o 'silicon_disks_tiling/[^"]*' "$ov/silicon_disks_modules_rsu6.xml" | sort | uniq -c | tr -s ' ' | tr '\n' ' ')"
if [[ "$bad" -eq 0 ]]; then echo "Identity rsu6: PASS"; else echo "Identity rsu6: FAIL"; fi
exit "$bad"
