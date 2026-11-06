#!/usr/bin/env bash
# Move per-disk material-scan outputs into proj_svt_disk_tiling/matscan/disk_material_map/
# (user request 2026-11-06). Non-destructive: mv only, each move logged to tmp/file_actions.log.
# Left in place on purpose: scripts/out/20260720/ (hit maps, not material scans) and the
# Step 8m geant4_material_tracks.root (part of the ACTS material-map product set).
set -euo pipefail
proj="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
epic="$(cd "$proj/.." && pwd)"
src="$epic/scripts/out/disk_material_map"
dst="$proj/matscan/disk_material_map"
stamp8q="step8q_20261106T153414Z"
log="$proj/tmp/file_actions.log"
mkdir -p "$dst"

move() {  # move <from> <to> <reason>
  local from="$1" to="$2" reason="$3"
  [[ -e "$to" ]] && { echo "ERROR: target exists: $to" >&2; exit 1; }
  mkdir -p "$(dirname "$to")"
  mv "$from" "$to"
  printf '%s | %s | %s | moved | %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "${from#"$epic/"}" "${to#"$epic/"}" "$reason" >> "$log"
  echo "moved ${from#"$epic/"} -> ${to#"$epic/"}"
}

# 1. disk_material_map.py outputs (directories and their run logs)
for name in step8m_full test_200k test_200k_mat "$stamp8q"; do
  move "$src/$name" "$dst/$name" "per-disk material scan output; consolidated under matscan/"
  move "$src/$name.log" "$dst/$name.log" "run log of the per-disk material scan"
done

# 2. Step 8q geantino recordings (made only for this scan) and their container logs
for k in 0 1 2 3; do
  move "$epic/scripts/material_map/${stamp8q}_slice${k}_geant4_material_tracks.root" \
       "$dst/$stamp8q/recording/${stamp8q}_slice${k}_geant4_material_tracks.root" \
       "Step 8q scan-only geantino recording (eta slice $k)"
  move "$proj/tmp/${stamp8q}_slice${k}_recording.log" \
       "$dst/$stamp8q/recording/${stamp8q}_slice${k}_recording.log" \
       "container log of the Step 8q recording slice $k"
done
echo "done; scripts/out/disk_material_map/ is now empty and left in place"
