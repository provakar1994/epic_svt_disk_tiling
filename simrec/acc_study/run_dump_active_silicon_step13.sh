#!/usr/bin/env bash
# Step 13 copy (2026-11-13) of run_dump_active_silicon.sh for the acceptance_v4_step13 analysis.
# The "active" selection of analyze_refplane_efficiency.py needs the sensitive boxes of the SAME
# geometry that was simulated. geometry/active_silicon_rectangles.csv is from EPIC 311634084 (v3);
# Step 13 (EPIC 78ade4686, 20261110_ES/rsu_opt) moved the modules, so it is dumped again here.
# Changes vs run_dump_active_silicon.sh:
#   - refuses to run unless refplanes/step13/identity_check_step13.sh passes;
#   - writes geometry/active_silicon_rectangles_step13.csv and refuses to overwrite it;
#   - records the identity check and the output sha256 in the log.
# Runs dump_active_silicon_rectangles.py inside eic_xl:26.09.0-stable (refplanes/eic_exec.sh)
# on the installed epic_craterlake_tracking_only.xml (no reference planes; they are not sensitive
# silicon anyway).
# Log: logs/dump_active_silicon_step13_<UTC>.log
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/../.." && pwd)"
epic_root="$(cd "$script_dir/../../.." && pwd)"
xml="$epic_root/install/share/epic/epic_craterlake_tracking_only.xml"
out="$script_dir/geometry/active_silicon_rectangles_step13.csv"
[[ ! -e "$out" ]] || { echo "ERROR: $out exists; move it to tmp/retained first" >&2; exit 2; }
identity_text="$("$project_dir/refplanes/step13/identity_check_step13.sh")" || {
  echo "$identity_text" >&2; echo "ERROR: Step 13 geometry identity check failed" >&2; exit 2; }
mkdir -p "$script_dir/geometry" "$script_dir/logs"
log="$script_dir/logs/dump_active_silicon_step13_$(date -u +%Y%m%dT%H%M%SZ).log"
{
  echo "Started: $(date -u) ; xml: $xml ; EPIC commit: $(git -C "$epic_root" rev-parse --short HEAD)"
  echo "$identity_text"
  "$project_dir/refplanes/eic_exec.sh" \
    "python3 $script_dir/dump_active_silicon_rectangles.py $xml $out" 2>&1 \
    | grep -v ' INFO \|^Info in' || true
  [[ -s "$out" ]] && sha256sum "$out"
  echo "Finished: $(date -u)"
} > "$log" 2>&1
grep -E "SENSITIVE_BOXES|ERROR|Traceback|Error|$(basename "$out")" "$log" || true
[[ -s "$out" ]] || { echo "ERROR: no output written; see $log" >&2; exit 1; }
echo "log: $log"
