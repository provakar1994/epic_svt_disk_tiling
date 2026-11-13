#!/usr/bin/env bash
# Step 13 geometry identity check (acceptance_v4_step13 preparation, 2026-11-12).
# The top-level epic_craterlake_tracking_only.xml only includes other files, so its
# checksum (c0141309..., same as v3) does NOT identify the geometry. Identity is:
#   EPIC HEAD, installed + checkout silicon_disks_modules.xml, installed libepic.so
# Values from proj_svt_disk_tiling/logs/freeze_install_step13.txt.
# Usage: identity_check_step13.sh   -> prints the values, exit 0 if all match, 1 otherwise.
set -uo pipefail
epic=/global/cfs/cdirs/m3763/pdatta/epic
expected_head=78ade46865d06250fe601c5b56189e37735f75b1
expected_modules=6d04bd66e5524c9cbdfec34c0e15064463af2000501a925063dc577ccfd1b27b
expected_libepic=9ccf1a6690903c009fe167383d14eb81c170c2ed29d212d674a6c73886e5cc87

bad=0
compare() {  # label actual expected
  if [[ "$2" == "$3" ]]; then echo "  [ok]   $1 = $2"; else echo "  [FAIL] $1 = $2 (expected $3)"; bad=1; fi
}
echo "Step 13 identity check: $(date -u --iso-8601=seconds)"
compare "EPIC HEAD" "$(git -C "$epic" rev-parse HEAD)" "$expected_head"
compare "checkout compact/tracking/silicon_disks_modules.xml sha256" \
  "$(sha256sum "$epic/compact/tracking/silicon_disks_modules.xml" | cut -d' ' -f1)" "$expected_modules"
compare "installed share/epic/compact/tracking/silicon_disks_modules.xml sha256" \
  "$(sha256sum "$epic/install/share/epic/compact/tracking/silicon_disks_modules.xml" | cut -d' ' -f1)" "$expected_modules"
compare "install/lib/libepic.so sha256" \
  "$(sha256sum "$epic/install/lib/libepic.so" | cut -d' ' -f1)" "$expected_libepic"
echo "  tiling in installed XML: $(grep -o 'silicon_disks_tiling/[^"]*' "$epic/install/share/epic/compact/tracking/silicon_disks_modules.xml" | sort -u | tr '\n' ' ')"
if [[ "$bad" -eq 0 ]]; then echo "Identity: PASS"; else echo "Identity: FAIL"; fi
exit "$bad"
