#!/usr/bin/env bash
# Recorded run of dump_active_silicon_rectangles.py inside eic_xl:26.09.0-stable,
# using the locally installed EPIC geometry (same install the campaign used).
# Output: geometry/active_silicon_rectangles.csv ; log: logs/dump_active_silicon_<UTC>.log
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
epic_root="$(cd "$script_dir/../../.." && pwd)"
xml="$epic_root/install/share/epic/epic_craterlake_tracking_only.xml"
out="$script_dir/geometry/active_silicon_rectangles.csv"
mkdir -p "$script_dir/geometry" "$script_dir/logs"
log="$script_dir/logs/dump_active_silicon_$(date -u +%Y%m%dT%H%M%SZ).log"
{
  echo "Started: $(date -u) ; xml: $xml ; EPIC commit: $(git -C "$epic_root" rev-parse --short HEAD)"
  "$epic_root/proj_svt_disk_tiling/refplanes/eic_exec.sh" \
    "python3 $script_dir/dump_active_silicon_rectangles.py $xml $out" 2>&1 \
    | grep -v ' INFO \|^Info in' || true
  echo "Finished: $(date -u)"
} > "$log" 2>&1
grep -E "SENSITIVE_BOXES|ERROR|Traceback|Error" "$log" || true
echo "log: $log"
