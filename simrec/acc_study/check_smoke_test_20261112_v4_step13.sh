#!/usr/bin/env bash
# Checks of the acceptance_v4_step13 smoke test (run_smoke_test_20261112_v4_step13.sh), host side.
#  1. Step 13 geometry identity (refplanes/step13/identity_check_step13.sh);
#  2. per task: sim file present, run_sim log ends with "Finished", 200 events, ACC_XML/steering
#     checksums in the log; counts of G4Exception / fatal / Traceback lines (gate: 0) and a list of
#     the distinct "error" lines (the known 'Wrong bounding box for volume envelope26' is benign);
#  3. collections: SVTDiskRefPlaneHits, TrackerEndcapHits, SiBarrelHits, VertexBarrelHits, MCParticles
#     present and non-empty;
#  4. the v3 Step 9e smoke checks (refplanes/step13/check_smoke_9e.py, Step 13 plane_map.csv) on a
#     flat directory of symlinks (sim_*.root + sim_*.log side by side, as that script expects);
#  5. v3 shard validation: extract_disk_particles_refplanes.py (vz = +100, Step 13 plane map) into
#     <smoke root>/extracted, then validate_refplanes_shards_20261106.py.
# Report: logs/check_smoke_test_20261112_v4_step13.txt
set -uo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/../.." && pwd)"
smoke_root="/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/smoke_20261112_v4_step13"
plane_map="$project_dir/refplanes/step13/plane_map.csv"
report="$script_dir/logs/check_smoke_test_20261112_v4_step13.txt"
[[ -d "$smoke_root" ]] || { echo "ERROR: no smoke output: $smoke_root" >&2; exit 2; }
[[ ! -e "$smoke_root/flat" && ! -e "$smoke_root/extracted" ]] || { echo "ERROR: flat/ or extracted/ exists in $smoke_root" >&2; exit 2; }

module load conda >/dev/null 2>&1
conda activate tracking

{
  echo "check_smoke_test_20261112_v4_step13: $(date -u --iso-8601=seconds)"
  "$project_dir/refplanes/step13/identity_check_step13.sh"
  cat "$smoke_root/smoke_commands.txt"
  echo "plane map: $(sha256sum "$plane_map")"

  echo; echo "== 2. logs =="
  mkdir -p "$smoke_root/flat"
  for log in "$smoke_root"/*/logs/sim_*.log; do
    tag="$(basename "$log" .log)"
    root_file="$(dirname "$(dirname "$log")")/rootfiles/$tag.root"
    echo "-- $tag"
    echo "  sim file: $(ls -la "$root_file" 2>&1)"
    grep -E "^(Started|Finished|Events|Vertex z|Eta|Seed|Compact XML|Steering file):" "$log" | sed 's/^/  /'
    grep -E "^[0-9a-f]{64}  " "$log" | sed 's/^/  sha256 /'
    grep -E "Finished run 0 after" "$log" | sed 's/^/  /'
    echo "  G4Exception lines: $(grep -c 'G4Exception' "$log")"
    echo "  fatal lines (case-insensitive): $(grep -ci 'fatal' "$log")"
    echo "  Traceback lines: $(grep -c 'Traceback' "$log")"
    echo "  distinct lines containing 'error' (case-insensitive):"
    grep -i "error" "$log" | sort | uniq -c | head -20 | sed 's/^/    /'
    ln -s "$root_file" "$smoke_root/flat/$tag.root"
    ln -s "$log" "$smoke_root/flat/$tag.log"
  done
  grep -h "Wall time" "$smoke_root/smoke_commands.txt"

  echo; echo "== 3. collections =="
  python3 - "$smoke_root" <<'EOF'
import sys
from pathlib import Path
import awkward as ak
import uproot
wanted = ["MCParticles", "SVTDiskRefPlaneHits", "TrackerEndcapHits", "SiBarrelHits", "VertexBarrelHits"]
bad = 0
for path in sorted(Path(sys.argv[1]).glob("*/rootfiles/sim_*.root")):
    with uproot.open(path) as f:
        tree = f["events"]
        keys = set(tree.keys(recursive=False))
        print(f"{path.name}: {tree.num_entries} events")
        bad += tree.num_entries != 200
        for name in wanted:
            if name not in keys:
                print(f"  [FAIL] {name} missing"); bad += 1; continue
            n = int(ak.sum(ak.num(tree[name][f"{name}.PDG" if name == "MCParticles" else f"{name}.cellID"].array())))
            print(f"  [{'ok' if n > 0 else 'FAIL'}] {name}: {n} entries")
            bad += n == 0
print("collections:", "PASS" if bad == 0 else f"FAIL ({bad})")
EOF

  echo; echo "== 4. Step 9e checks (refplanes/step13/check_smoke_9e.py) =="
  python3 "$project_dir/refplanes/step13/check_smoke_9e.py" "$smoke_root/flat"
  echo "check_smoke_9e exit status: $?"

  echo; echo "== 5. extraction + validate_refplanes_shards_20261106.py =="
  python3 "$script_dir/extract_disk_particles_refplanes.py" --campaign-root "$smoke_root" \
    --output-dir "$smoke_root/extracted" --vertices 100 --plane-map "$plane_map" --step-size 5000
  echo "extract exit status: $?"
  python3 "$script_dir/validate_refplanes_shards_20261106.py" "$smoke_root/extracted" "$plane_map"
  echo "validate_refplanes_shards exit status: $?"
  echo "Finished: $(date -u --iso-8601=seconds)"
} > "$report" 2>&1
cat "$report"
