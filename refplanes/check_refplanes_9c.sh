#!/usr/bin/env bash
# Step 9c: geometry export and overlap checks on the reference-plane overlay XML.
# Usage: check_refplanes_9c.sh root|geant4
#   root   : dd_web_display --export, then ROOT checkOverlaps --option m --tolerance 0.01
#            gate: 0 'ovlp' lines and 0 illegal overlaps
#   geant4 : python scripts/checkOverlaps.py -t 0.1 (Geant4, long)
#            gate: 0 GeomVol1002 and 0 G4Exception
# Raw logs: refplanes/out_9c/ ; summary reports: check_refplanes_9c_<mode>.txt
set -uo pipefail
mode="${1:?root|geant4}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
epic=/global/cfs/cdirs/m3763/pdatta/epic
xml="$here/generated/epic_craterlake_tracking_only_refplanes.xml"
out="$here/out_9c"
mkdir -p "$out"
report="$here/check_refplanes_9c_$mode.txt"
{
  echo "Started: $(date -u --iso-8601=seconds)"
  echo "Overlay XML: $xml"
  echo "sha256: $(sha256sum "$xml" | cut -d' ' -f1)"
  echo "Plane XML sha256: $(sha256sum "$here/silicon_disks_refplanes.xml" | cut -d' ' -f1)"
  echo "EPIC commit: $(git -C $epic rev-parse HEAD)"
  case "$mode" in
    root)
      "$here/eic_exec.sh" "cd $out && dd_web_display --export $xml" > "$out/dd_web_display.log" 2>&1
      echo "dd_web_display exit status: $?"
      echo "export files in $out:"; ls -la "$out"/*.root 2>/dev/null
      grep -i "error\|exception" "$out/dd_web_display.log" | grep -v "envelope26" | head -20
      "$here/eic_exec.sh" "checkOverlaps --option m --tolerance 0.01 -c $xml" > "$out/root_overlap.log" 2>&1
      echo "checkOverlaps exit status: $?"
      n_ovlp=$(grep -c 'ovlp' "$out/root_overlap.log" || true)
      echo "ROOT 'ovlp' lines: $n_ovlp"
      grep -E "illegal overlaps|Number of illegal" "$out/root_overlap.log" | tail -3
      [[ "$n_ovlp" -eq 0 ]] || grep 'ovlp' "$out/root_overlap.log" | head -40
      ;;
    geant4)
      "$here/eic_exec.sh" "cd $epic && python scripts/checkOverlaps.py -t 0.1 -c $xml" > "$out/geant4_overlap_raw.log" 2>&1
      echo "checkOverlaps.py exit status: $?"
      n_g=$(grep -c 'GeomVol1002' "$out/geant4_overlap_raw.log" || true)
      n_e=$(grep -c 'G4Exception' "$out/geant4_overlap_raw.log" || true)
      echo "Geant4 GeomVol1002 overlap warnings: $n_g"
      echo "G4Exception lines: $n_e"
      [[ "$n_g" -eq 0 && "$n_e" -eq 0 ]] || grep -A6 'GeomVol1002\|G4Exception' "$out/geant4_overlap_raw.log" | head -80
      echo "-- tail of raw log --"; tail -15 "$out/geant4_overlap_raw.log"
      ;;
  esac
  echo "Finished: $(date -u --iso-8601=seconds)"
} > "$report" 2>&1
