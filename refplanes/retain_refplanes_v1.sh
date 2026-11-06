#!/usr/bin/env bash
# Move the superseded v1 reference-plane artifacts (centred annuli, rmin = enclosing circle)
# to retention before building v2 (off-centre annuli following the beam-pipe openings).
# Reason: coordinator found HD3/HD4 silicon below the v1 plane rmin (2026-11-06).
# Nothing is deleted; every move is logged in proj_svt_disk_tiling/tmp/file_actions.log.
set -euo pipefail
proj=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling
dest="$proj/tmp/retained/2026-11-06/refplanes_v1"
log="$proj/tmp/file_actions.log"
mkdir -p "$dest"
move() {  # move SRC REASON
  local src="$1" reason="$2" name
  name="$(basename "$src")"
  [[ -e "$src" ]] || { echo "skip (absent): $src"; return; }
  [[ ! -e "$dest/$name" ]] || { echo "ERROR: $dest/$name exists" >&2; exit 1; }
  mv "$src" "$dest/$name"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | ${src#/global/cfs/cdirs/m3763/pdatta/epic/} | ${dest#/global/cfs/cdirs/m3763/pdatta/epic/}/$name | moved | $reason" >> "$log"
  echo "moved $src -> $dest/$name"
}
r="v1 reference-plane overlay (centred annuli) superseded by v2 opening-following planes"
cd "$proj/refplanes"
move "$proj/refplanes/silicon_disks_refplanes.xml" "$r; v1 plane feature XML"
move "$proj/refplanes/plane_map.csv" "$r; v1 plane table"
move "$proj/refplanes/generated" "$r; v1 generated overlay XML + provenance"
move "$proj/refplanes/validate_refplanes_9b.txt" "$r; v1 9b validator report (PASS)"
move "$proj/refplanes/validate_refplanes_9b_run1_validator_bugs.txt" "$r; v1 9b first run with validator bugs"
move "$proj/refplanes/check_refplanes_9c_root.txt" "$r; v1 9c ROOT report (PASS)"
move "$proj/refplanes/check_refplanes_9c_geant4.txt" "$r; v1 9c Geant4 report (PASS)"
move "$proj/refplanes/out_9c" "$r; v1 9c raw logs and dd_web_display export"
move "$proj/refplanes/out_9d" "$r; v1 9d material scans"
move "$proj/refplanes/compare_material_scan_9d.txt" "$r; v1 9d comparison (gate wording failed, see log)"
move "$proj/refplanes/material_scan_9d_installed.log" "$r; v1 9d runner log"
move "$proj/refplanes/material_scan_9d_overlay.log" "$r; v1 9d runner log"
move "$proj/refplanes/material_scan_9d_installed_all_failed.log" "$r; v1 9d runner log, --detectors all crash"
move "$proj/refplanes/material_scan_9d_overlay_all_failed.log" "$r; v1 9d runner log, --detectors all crash"
move "$proj/refplanes/check_smoke_9e.txt" "$r; v1 9e smoke check report"
move "$proj/refplanes/diagnose_smoke_secondaries_9e.txt" "$r; v1 9e secondaries diagnostic"
move "$proj/refplanes/run_smoke_9e.log" "$r; v1 9e runner log"
move "$proj/refplanes/plane_clearance_9a_crosscheck.txt" "$r; v1 9a point-sampling cross-check of the centred annuli"
move "$proj/refplanes/run_silicon_unchanged_9f.log" "$r; v1 9f runner log (overlay runs stopped)"
move /pscratch/sd/p/pdatta/svt_disk_tiling/refplanes/smoke "$r; v1 smoke-test ROOT files and logs (4 x 100 events)"
move /pscratch/sd/p/pdatta/svt_disk_tiling/refplanes/smoke_debug "$r; symlinks used to debug the 9e checker"
mkdir -p "$dest/silicon_9f_overlay_v1_partial"
for f in sim_overlay_fwd.root sim_overlay_fwd.log sim_overlay_bwd.root sim_overlay_bwd.log; do
  src=/pscratch/sd/p/pdatta/svt_disk_tiling/refplanes/silicon_9f/$f
  [[ -e "$src" ]] || continue
  mv "$src" "$dest/silicon_9f_overlay_v1_partial/$f"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | $src | ${dest#/global/cfs/cdirs/m3763/pdatta/epic/}/silicon_9f_overlay_v1_partial/$f | moved | $r; v1 9f overlay run stopped (kill) part-way, incomplete" >> "$log"
  echo "moved $src"
done
