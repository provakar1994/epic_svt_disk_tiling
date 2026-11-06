#!/usr/bin/env bash
# Step 9d comparison runner (host, conda env tracking). Report: compare_material_scan_9d.txt
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
module load conda >/dev/null 2>&1; conda activate tracking
{ echo "Started: $(date -u --iso-8601=seconds)"; grep -h "^detectors" "$here"/material_scan_9d_installed.log "$here"/material_scan_9d_overlay.log; python3 "$here/compare_material_scan_9d.py" "$here/out_9d"; echo "exit status: $?"; } > "$here/compare_material_scan_9d.txt" 2>&1
