#!/usr/bin/env bash
# Validate two late selections from one reusable 10,000-particle extraction.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
smoke_root="$script_dir/tmp/acceptance_two_stage_smoke_20261027"
extracted_root="$smoke_root/extracted"
[[ ! -e "$smoke_root" ]] || { echo "ERROR: smoke output exists: $smoke_root" >&2; exit 2; }

module load conda
conda activate tracking

python3 "$script_dir/extract_disk_particles.py" \
  --campaign-root /pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v1 \
  --output-dir "$extracted_root" \
  --vertices 0 \
  --max-files-per-side 1 \
  --stop-events-per-file 5000 \
  --step-size 1000

# First reduction: every extracted primary.
python3 "$script_dir/reduce_disk_acceptance.py" \
  --extracted-root "$extracted_root" \
  --output-dir "$smoke_root/inclusive" \
  --vertices 0
python3 "$script_dir/validate_disk_acceptance.py" \
  "$smoke_root/inclusive/disk_acceptance_vz_000mm.npz" \
  --expected-files-per-side 1 \
  --expected-events-per-side 5000

# Second reduction: different physics cuts, with no ROOT reread.
python3 "$script_dir/reduce_disk_acceptance.py" \
  --extracted-root "$extracted_root" \
  --output-dir "$smoke_root/abseta1to2_p1to10" \
  --vertices 0 \
  --abs-eta-range 1.0 2.0 \
  --momentum-range-gev 1.0 10.0
python3 "$script_dir/validate_disk_acceptance.py" \
  "$smoke_root/abseta1to2_p1to10/disk_acceptance_vz_000mm.npz" \
  --expected-files-per-side 1
