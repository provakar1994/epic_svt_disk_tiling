#!/usr/bin/env bash
# Recorded end-to-end test of the refplanes chain on the geometry agent's smoke
# files (/pscratch/sd/p/pdatta/svt_disk_tiling/refplanes/smoke/, 6 x 100 events:
# vz = 0, +100 and -100 mm, both eta signs; v2 plane geometry with off-centre
# annuli and 7 plane detectors. The v1 run of this script (4 files, no
# vz = -100) is retained in tmp/retained/2026-11-06/).
#  1. build a campaign-style directory of symlinks (configuration/rootfiles/sim_*.root);
#  2. run_extract_refplanes.sh for vz = 0, +100, -100 into a test extraction root;
#  3. per-plane validation of the shards (validate_refplanes_shards_20261106.py);
#  4. run_refplane_efficiency.sh for vz = 0, +100, -100 into a test results dir.
# Statistics are tiny (100 events per configuration): this tests the chain and
# the plane interface, not the efficiencies.
# Output: tmp/refplanes_smoke_chain_20261106/ ; report logs/check_refplanes_smoke_chain_20261106.txt
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
smoke_dir=/pscratch/sd/p/pdatta/svt_disk_tiling/refplanes/smoke
test_dir="$script_dir/tmp/refplanes_smoke_chain_20261106"
report="$script_dir/logs/check_refplanes_smoke_chain_20261106.txt"
[[ ! -e "$test_dir" ]] || { echo "ERROR: $test_dir exists" >&2; exit 2; }

link() {  # smoke name, configuration
  mkdir -p "$test_dir/campaign/$2/rootfiles"
  ln -s "$smoke_dir/sim_$1.root" "$test_dir/campaign/$2/rootfiles/sim_$1.root"
}
link vz0_fwd   vz_000mm_eta_p0p6_to_p3p8
link vz0_bwd   vz_000mm_eta_m3p8_to_m0p6
link vz100_fwd vz_p100mm_eta_p0p6_to_p3p8
link vz100_bwd vz_p100mm_eta_m3p8_to_m0p6
link vzm100_fwd vz_m100mm_eta_p0p6_to_p3p8
link vzm100_bwd vz_m100mm_eta_m3p8_to_m0p6

{
  echo "check_refplanes_smoke_chain_20261106: $(date --iso-8601=seconds)"
  echo "smoke files:"; sha256sum "$smoke_dir"/sim_*.root
  echo "plane map:"; sha256sum "$script_dir/../../refplanes/plane_map.csv"
  for vz in 0 100 -100; do
    "$script_dir/run_extract_refplanes.sh" "$vz" "$test_dir/campaign" "$test_dir/extracted"
  done
  module load conda
  conda activate tracking
  python3 "$script_dir/validate_refplanes_shards_20261106.py" "$test_dir/extracted" \
    "$script_dir/../../refplanes/plane_map.csv"
  EXTRACTED_ROOT="$test_dir/extracted" OUTPUT_DIR="$test_dir/results" \
    "$script_dir/run_refplane_efficiency.sh" 0 100 -100
} > "$report" 2>&1
cat "$report"
