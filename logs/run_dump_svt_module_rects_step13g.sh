#!/usr/bin/env bash
# Step 13g: dump module-box rectangles from the Step 8q and Step 13 geometry exports (read-only).
# Runs logs/dump_svt_module_rects_step13g.py inside the EIC container (refplanes/eic_exec.sh).
# Exports: out/visualize_8q.root (2026-11-09, no provenance file; Step 8q HEAD 311634084 era)
#          out/visualize_step13.root (provenance: c20bb1646 + uncommitted Step 13b src = 78ade4686).
# Output: matscan/disk_material_map/step13g_geometry_rects/{step8q,step13}_module_rects.csv + .log
set -euo pipefail
proj=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling
out=$proj/matscan/disk_material_map/step13g_geometry_rects
mkdir -p "$out"
sha256sum "$proj/out/visualize_8q.root" "$proj/out/visualize_step13.root" | tee "$out/inputs.sha256"
for pair in "step8q:visualize_8q.root" "step13:visualize_step13.root"; do
  tag=${pair%%:*}; file=${pair#*:}
  "$proj/refplanes/eic_exec.sh" "cd $out && python3 $proj/logs/dump_svt_module_rects_step13g.py $proj/out/$file $out/${tag}_module_rects.csv" \
    2>&1 | grep -v -E "^Info in|Fontconfig" | tee "$out/${tag}_dump.log"
done
