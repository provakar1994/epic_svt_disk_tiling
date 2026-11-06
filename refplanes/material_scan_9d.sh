#!/usr/bin/env bash
# Step 9d: zero-material check. Runs scripts/subdetector_tests/material_scan.py (unmodified)
# on the installed epic_craterlake_tracking_only.xml and on the overlay XML with identical
# settings (Running_NOTES.md invocation), for phi = 20 and 200 deg.
# No detector filter: '--detectors all' crashes in material_scan.py with this container's pandas
# (first attempt, logs material_scan_stdio_all_failed.txt), so the explicit list of ALL world
# children of each geometry is passed instead (list_world_detectors.py). Material outside the
# listed detectors would go to the script's 'Others' column, so the per-eta total is complete.
# Outputs: refplanes/out_9d/<geometry>/phi<phi>/material_scan_agg.csv (+ stdio, pdf, png)
# Usage: material_scan_9d.sh installed|overlay   (one single-threaded process)
set -uo pipefail
which="${1:?installed|overlay}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
epic=/global/cfs/cdirs/m3763/pdatta/epic
case "$which" in
  installed) xml="$epic/install/share/epic/epic_craterlake_tracking_only.xml" ;;
  overlay)   xml="$here/generated/epic_craterlake_tracking_only_refplanes.xml" ;;
esac
mkdir -p "$here/out_9d/$which"
mpl="/pscratch/sd/p/pdatta/svt_disk_tiling/refplanes/mplconfig_$which"; mkdir -p "$mpl"
"$here/eic_exec.sh" "python3 $here/list_world_detectors.py $xml" > "$here/out_9d/$which/world_detectors.txt" 2>&1
dets="$(grep '^DETECTORS=' "$here/out_9d/$which/world_detectors.txt" | tail -1 | cut -d= -f2)"
[[ -n "$dets" ]] || { echo "ERROR: no detector list"; exit 1; }
echo "detectors ($which): $dets"
for phi in 20 200; do
  out="$here/out_9d/$which/phi$phi"
  mkdir -p "$out"
  echo "[$(date -u --iso-8601=seconds)] $which phi=$phi xml=$xml"
  "$here/eic_exec.sh" "export MPLCONFIGDIR=$mpl; cd $out && python3 $epic/scripts/subdetector_tests/material_scan.py $xml \
    --path-r 200 --start-point 0,0,0 --eta-min -4.2 --eta-max 4.2 --eta-nbins 841 \
    --phi $phi --epsilon 1e-3 --value-type X0 --detectors $dets" > "$out/material_scan_stdio.txt" 2>&1
  echo "  exit status: $?"
done
