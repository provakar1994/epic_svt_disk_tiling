#!/usr/bin/env bash
# Step 14b (2026-11-13): geometry inputs of the acceptance_v4_step13_rsu6 refplane analysis.
#   1. active-silicon dump of the rsu6 geometry: dump_active_silicon_rectangles.py (unchanged) on the
#      frozen rsu6 tracking-only overlay geometry_overlays/step13/rsu6/epic_craterlake_tracking_only_rsu6.xml,
#      inside eic_xl:26.09.0-stable via refplanes/step13_rsu6/eic_exec_rsu6.sh (DETECTOR_PATH = install,
#      CWD step13_rsu6/ so the relative rsu6 tiling path resolves to the install)
#      -> geometry/active_silicon_rectangles_step13_rsu6.csv
#      (pattern: run_dump_active_silicon_step13.sh, which is unchanged)
#   2. row families: make_row_families_20261110.py (unchanged) with --tiling-dir = the INSTALLED
#      20261110_ES/rsu6 directory (the one the geometry reads) and --active-csv = the rsu6 dump
#      -> geometry/row_families_20261110_ES_rsu6.csv, report logs/make_row_families_20261110_rsu6.txt
#   3. comparison with the rsu_opt inputs: cmp of the delivered <disk>_rows.csv (rsu_opt vs rsu6) and of
#      the two converted tables; box counts per disk of the two active dumps.
# Refuses unless refplanes/step13_rsu6/identity_check_step13_rsu6.sh passes; never overwrites outputs.
# Log: logs/geometry_inputs_v4_step13_rsu6_<UTC>.log
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/../.." && pwd)"
epic_root="$(cd "$project_dir/.." && pwd)"
xml="$project_dir/geometry_overlays/step13/rsu6/epic_craterlake_tracking_only_rsu6.xml"
active_out="$script_dir/geometry/active_silicon_rectangles_step13_rsu6.csv"
rows_out="$script_dir/geometry/row_families_20261110_ES_rsu6.csv"
rows_report="$script_dir/logs/make_row_families_20261110_rsu6.txt"
tiling_installed="$epic_root/install/share/epic/compact/tracking/silicon_disks_tiling/20261110_ES"
for f in "$active_out" "$rows_out" "$rows_report"; do
  [[ ! -e "$f" ]] || { echo "ERROR: $f exists; move it to tmp/retained first" >&2; exit 2; }
done
identity_text="$("$project_dir/refplanes/step13_rsu6/identity_check_step13_rsu6.sh")" || {
  echo "$identity_text" >&2; echo "ERROR: rsu6 identity check failed" >&2; exit 2; }
mkdir -p "$script_dir/geometry" "$script_dir/logs"
log="$script_dir/logs/geometry_inputs_v4_step13_rsu6_$(date -u +%Y%m%dT%H%M%SZ).log"
{
  echo "Started: $(date -u) ; xml: $xml"
  echo "$identity_text"
  echo "== 1. active-silicon dump (container) =="
  "$project_dir/refplanes/step13_rsu6/eic_exec_rsu6.sh" \
    "python3 $script_dir/dump_active_silicon_rectangles.py $xml $active_out" 2>&1 | grep -v ' INFO \|^Info in' || true
  [[ -s "$active_out" ]] && sha256sum "$active_out"

  echo "== 2. row families (conda tracking) =="
  module load conda >/dev/null 2>&1; conda activate tracking
  python3 "$script_dir/make_row_families_20261110.py" "$rows_out" --tiling-dir "$tiling_installed/rsu6" \
    --active-csv "$active_out" > "$rows_report" 2>&1
  echo "make_row_families exit status: $?"; cat "$rows_report"
  sha256sum "$rows_out"

  echo "== 3. rsu6 vs rsu_opt inputs =="
  for d in ED4 ED3 ED2 ED1 ED0 HD0 HD1 HD2 HD3 HD4; do
    if cmp -s "$tiling_installed/rsu_opt/${d}_rows.csv" "$tiling_installed/rsu6/${d}_rows.csv"; then
      echo "  ${d}_rows.csv: rsu6 IDENTICAL to rsu_opt"; else echo "  ${d}_rows.csv: rsu6 DIFFERS from rsu_opt"; fi
  done
  if cmp -s "$rows_out" "$script_dir/geometry/row_families_20261110_ES_rsu_opt.csv"; then
    echo "  converted row-family table: IDENTICAL to row_families_20261110_ES_rsu_opt.csv"
  else
    echo "  converted row-family table differs from rsu_opt:"
    diff "$script_dir/geometry/row_families_20261110_ES_rsu_opt.csv" "$rows_out" | head -20
  fi
  python3 - "$script_dir/geometry/active_silicon_rectangles_step13.csv" "$active_out" <<'EOF'
import sys
import pandas as pd
a, b = pd.read_csv(sys.argv[1]), pd.read_csv(sys.argv[2])
col = "disk" if "disk" in a.columns else a.columns[0]
print(f"  active boxes per {col}: rsu_opt total {len(a)}, rsu6 total {len(b)}")
print(pd.DataFrame({"rsu_opt": a.groupby(col).size(), "rsu6": b.groupby(col).size()}).to_string())
EOF
  echo "Finished: $(date -u)"
} > "$log" 2>&1
cat "$log" | grep -v '^\s*\[ok\]'
[[ -s "$active_out" && -s "$rows_out" ]] || { echo "ERROR: outputs missing; see $log" >&2; exit 1; }
echo "log: $log"
