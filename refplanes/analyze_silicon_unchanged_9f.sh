#!/usr/bin/env bash
# Step 9f comparison runner (host, conda env tracking). Report: analyze_silicon_unchanged_9f.txt
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
module load conda >/dev/null 2>&1; conda activate tracking
d=/pscratch/sd/p/pdatta/svt_disk_tiling/refplanes/silicon_9f
{ echo "Started: $(date -u --iso-8601=seconds)"; grep -h "npsim exit status" $d/*.log | sort | uniq -c; for f in $d/*.log; do echo "$(basename $f): $(grep -m1 -o 'random.seed [0-9]*' $f) $(grep -m1 -o 'compactFile [^ ]*' $f | awk '{print $2}')"; done
  python3 "$here/analyze_silicon_unchanged_9f.py" $d; echo "exit status: $?"; } > "$here/analyze_silicon_unchanged_9f.txt" 2>&1
