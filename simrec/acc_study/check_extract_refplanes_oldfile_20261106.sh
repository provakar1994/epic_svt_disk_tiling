#!/usr/bin/env bash
# Recorded check of extract_disk_particles_refplanes.py on an OLD sim file
# (acceptance_v2_vz100mm, vz = +100 mm, chunk 001 of both eta sides; these
# files have no SVTDiskRefPlaneHits collection).
# Expected: plane fields empty (mask 0, crossings 0, NaN), metadata
# plane_collection_present = false, and every silicon/particle array
# identical to the original extractor's shard for the same file
# (extracted/acceptance_v2_vz_p100mm/...).
# A synthetic plane_map.csv (made-up ids, z = disk z -/+ 6 mm) is used because
# refplanes/plane_map.csv does not exist yet; ids do not matter for old files.
# Report: logs/check_extract_refplanes_oldfile_20261106.txt
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
test_dir="$script_dir/tmp/extract_refplanes_oldfile_check_20261106"
report="$script_dir/logs/check_extract_refplanes_oldfile_20261106.txt"
[[ ! -e "$test_dir" ]] || { echo "ERROR: $test_dir exists" >&2; exit 2; }
mkdir -p "$test_dir"

cat > "$test_dir/synthetic_plane_map.csv" <<'CSV'
disk,side,z_disk_mm,z_plane_mm,rmin_mm,rmax_mm,system,barrel,layer
ED0,negative,-250,-244,37.0,250.0,250,2,1
ED1,negative,-450,-444,54.45,425.0,250,2,2
ED2,negative,-650,-644,47.0,450.0,250,2,3
ED3,negative,-850,-844,47.0,450.0,250,2,4
ED4,negative,-1020,-1014,47.0,450.0,250,2,5
HD0,positive,250,244,37.0,250.0,250,1,1
HD1,positive,450,444,54.45,425.0,250,1,2
HD2,positive,700,694,47.0,450.0,250,1,3
HD3,positive,950,944,47.0,450.0,250,1,4
HD4,positive,1200,1194,47.0,450.0,250,1,5
CSV

module load conda
conda activate tracking

{
  echo "check_extract_refplanes_oldfile_20261106: $(date --iso-8601=seconds)"
  echo "extractor sha256: $(sha256sum "$script_dir/extract_disk_particles_refplanes.py" | cut -d' ' -f1)"
  start=$(date +%s)
  python3 "$script_dir/extract_disk_particles_refplanes.py" \
    --campaign-root /pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v2_vz100mm \
    --output-dir "$test_dir/extracted" --vertices 100 --max-files-per-side 1 \
    --plane-map "$test_dir/synthetic_plane_map.csv" --step-size 5000
  echo "extraction wall time: $(( $(date +%s) - start )) s for 2 files x 100k events"
  python3 - "$test_dir/extracted" "$script_dir/extracted/acceptance_v2_vz_p100mm" <<'PY'
import json, sys
from pathlib import Path
import numpy as np
new_root, old_root = Path(sys.argv[1]), Path(sys.argv[2])
plane_float = ["plane_x_mm", "plane_y_mm", "plane_z_mm", "plane_t_ns",
               "plane_px_GeV", "plane_py_GeV", "plane_pz_GeV"]
ok = True
for new in sorted(new_root.glob("*/particles_*.npz")):
    old = old_root / new.parent.name / new.name
    print(f"--- {new.parent.name}/{new.name}\n    reference: {old}")
    with np.load(new) as a, np.load(old) as b:
        for key in b.files:
            if key == "metadata_json":
                continue
            same = a[key].dtype == b[key].dtype and a[key].shape == b[key].shape and \
                np.array_equal(a[key], b[key], equal_nan=a[key].dtype.kind == "f")
            ok &= same
            print(f"    {key:16s} {str(a[key].shape):12s} {a[key].dtype}  identical: {same}")
        meta = json.loads(str(a["metadata_json"]))
        n = len(a["event_entry"])
        checks = {
            "plane_collection_present is false": meta["plane_collection_present"] is False,
            "plane_mask all 0": a["plane_mask"].shape == (n,) and not a["plane_mask"].any(),
            "plane_crossings all 0": a["plane_crossings"].shape == (n, 5) and not a["plane_crossings"].any(),
            "plane_secondary_flagged all 0": not a["plane_secondary_flagged"].any(),
            "plane float fields all NaN": all(a[k].shape == (n, 5) and np.isnan(a[k]).all() for k in plane_float),
            "plane hit counters 0": meta["plane_hits_total"] == 0 and meta["plane_hits_dropped_not_primary"] == 0,
        }
        for text, value in checks.items():
            ok &= value
            print(f"    {text}: {value}")
print("OVERALL:", "PASS" if ok else "FAIL")
PY
} > "$report" 2>&1
cat "$report"
