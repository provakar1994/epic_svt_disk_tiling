#!/usr/bin/env bash
# Step 11f: stage the Ernst S. 2026-11-10 "-r" package (transition/{rsu_opt,rsu6}; all module
# facings flipped, for systematic studies)
# into the EPIC repo as a parallel delivery directory 20261110-r_ES/.
# Byte-for-byte copies (cp -p) of the geometry-loader inputs only:
#   catalog.csv, <disk>_modules.csv, <disk>_rows.csv, <disk>_metadata.txt, disk_geometry_used.csv
# Not copied: SVG plots, xlsx, text reports, cad/ exports (stay in ES_material/).
# 20261001_ES/ and 20261110_ES/ are left untouched.
# Usage: bash stage_svt_tiling_20261110r_step11f.sh > stage_svt_tiling_20261110r_step11f.txt
set -euo pipefail

EPIC=/global/cfs/cdirs/m3763/pdatta/epic
SRC=$EPIC/proj_svt_disk_tiling/ES_material/20261110-r/transition
DST=$EPIC/compact/tracking/silicon_disks_tiling/20261110-r_ES
SCENARIOS="rsu_opt rsu6"
DISKS="ED4 ED3 ED2 ED1 ED0 HD0 HD1 HD2 HD3 HD4"

echo "Step 11f staging  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "source: $SRC"
echo "dest:   $DST"

# Ownership guard (global rule): destination parent must be ours.
parent_owner=$(stat -c %U "$(readlink -f "$(dirname "$DST")")")
if [ "$parent_owner" != "pdatta" ]; then
  echo "ABORT: $(dirname "$DST") owned by $parent_owner"; exit 1
fi

for scen in $SCENARIOS; do
  if [ -e "$DST/$scen" ]; then
    echo "ABORT: $DST/$scen already exists; not overwriting"; exit 1
  fi
done

n_total=0
for scen in $SCENARIOS; do
  mkdir -p "$DST/$scen"
  files="catalog.csv disk_geometry_used.csv"
  for d in $DISKS; do
    files="$files ${d}_modules.csv ${d}_rows.csv ${d}_metadata.txt"
  done
  for f in $files; do
    if [ ! -f "$SRC/$scen/$f" ]; then
      echo "ABORT: missing $SRC/$scen/$f"; exit 1
    fi
    cp -p "$SRC/$scen/$f" "$DST/$scen/$f"
    n_total=$((n_total + 1))
  done
done
echo "copied $n_total files"

# Verify byte identity and summarise row counts.
echo
echo "sha256 check (source vs staged):"
n_bad=0
for scen in $SCENARIOS; do
  for f in "$DST/$scen"/*; do
    b=$(basename "$f")
    if cmp -s "$f" "$SRC/$scen/$b"; then
      printf '  OK   %s/%s  %s\n' "$scen" "$b" "$(sha256sum "$f" | cut -c1-12)"
    else
      printf '  DIFF %s/%s\n' "$scen" "$b"; n_bad=$((n_bad + 1))
    fi
  done
done
echo "mismatches: $n_bad"

echo
echo "data rows per disk (modules / rows), excluding header:"
for scen in $SCENARIOS; do
  echo "  $scen: catalog types $(($(wc -l < "$DST/$scen/catalog.csv") - 1))"
  total=0
  for d in $DISKS; do
    nm=$(($(wc -l < "$DST/$scen/${d}_modules.csv") - 1))
    nr=$(($(wc -l < "$DST/$scen/${d}_rows.csv") - 1))
    total=$((total + nm))
    printf '    %-4s %5d modules  %3d rows\n' "$d" "$nm" "$nr"
  done
  echo "    total modules: $total"
done
[ "$n_bad" -eq 0 ]
