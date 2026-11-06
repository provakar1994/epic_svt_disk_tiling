#!/usr/bin/env bash
# Preserve the 13 failed logs before retrying their original output tags.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source_dir="/pscratch/sd/p/pdatta/svt_disk_tiling/simout"
retained_dir="$repo_root/proj_svt_disk_tiling/tmp/retained/2026-10-19/oom_npsim_logs"
tags=(
  vm10mm_job_2 vm10mm_job_3 vm10mm_job_4
  v0mm_job_0 v0mm_job_1 v0mm_job_2 v0mm_job_3 v0mm_job_4
  v10mm_job_0 v10mm_job_1 v10mm_job_2 v10mm_job_3 v10mm_job_4
)

for tag in "${tags[@]}"; do
  if [[ ! -f "$source_dir/sim_${tag}.log" || -e "$source_dir/sim_${tag}.root" ||
        -e "$retained_dir/sim_${tag}.log" ]]; then
    echo "ERROR: unexpected source/output/retention state for $tag" >&2
    exit 1
  fi
done

mkdir -p "$retained_dir"
for tag in "${tags[@]}"; do
  mv "$source_dir/sim_${tag}.log" "$retained_dir/sim_${tag}.log"
  echo "retained sim_${tag}.log"
done
