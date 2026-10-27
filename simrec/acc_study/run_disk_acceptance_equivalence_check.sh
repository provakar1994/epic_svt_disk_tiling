#!/usr/bin/env bash
# Compare ROOT-direct and cached-particle reductions on the same small sample.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
extracted="$script_dir/tmp/acceptance_two_stage_smoke_20261027/extracted"
campaign_root="/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v1"
check_root="$script_dir/tmp/acceptance_two_stage_equivalence_20261027_v2"
direct_dir="$check_root/direct_root"
cached_dir="$check_root/cached_particles"

[[ -d "$extracted" ]] || { echo "ERROR: extracted smoke shards are missing" >&2; exit 2; }
[[ -d "$campaign_root" ]] || { echo "ERROR: campaign directory is missing" >&2; exit 2; }
[[ ! -e "$check_root" ]] || { echo "ERROR: check output exists: $check_root" >&2; exit 2; }

module load conda
conda activate tracking

python3 "$script_dir/reduce_disk_acceptance.py" \
  --campaign-root "$campaign_root" \
  --output-dir "$direct_dir" \
  --vertices 0 \
  --abs-eta-range 0.9 1.2 \
  --max-files-per-side 1 \
  --stop-events-per-file 5000 \
  --step-size 1000

python3 "$script_dir/reduce_disk_acceptance.py" \
  --extracted-root "$extracted" \
  --output-dir "$cached_dir" \
  --vertices 0 \
  --abs-eta-range 0.9 1.2

python3 "$script_dir/validate_reduction_equivalence.py" \
  "$direct_dir/disk_acceptance_vz_000mm.npz" \
  "$cached_dir/disk_acceptance_vz_000mm.npz"
