#!/usr/bin/env bash
# Re-submit the 15 jobs that failed at the compute-node /gpfs bind.
# Run with 'first', verify npsim starts, then run with 'remaining'.
set -euo pipefail

if [[ $# -ne 1 || ( "$1" != first && "$1" != remaining ) ]]; then
  echo "Usage: $0 first|remaining" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
batch_script="$repo_root/proj_svt_disk_tiling/simrec/submit_premium_packed.sh"
runner_dir="$repo_root/proj_svt_disk_tiling/simrec"
output_dir="/pscratch/sd/p/pdatta/svt_disk_tiling/simout"
events=20000

jobs=(
  '59997034|vm10mm_job_0|run_sim.sh'
  '59997035|vm10mm_job_1|run_sim.sh'
  '59997036|vm10mm_job_2|run_sim.sh'
  '59997037|vm10mm_job_3|run_sim.sh'
  '59997038|vm10mm_job_4|run_sim.sh'
  '59997039|v0mm_job_0|run_sim_v0mm.sh'
  '59997040|v0mm_job_1|run_sim_v0mm.sh'
  '59997041|v0mm_job_2|run_sim_v0mm.sh'
  '59997042|v0mm_job_3|run_sim_v0mm.sh'
  '59997043|v0mm_job_4|run_sim_v0mm.sh'
  '59997044|v10mm_job_0|run_sim_v10mm.sh'
  '59997045|v10mm_job_1|run_sim_v10mm.sh'
  '59997046|v10mm_job_2|run_sim_v10mm.sh'
  '59997047|v10mm_job_3|run_sim_v10mm.sh'
  '59997048|v10mm_job_4|run_sim_v10mm.sh'
)

if [[ "$1" == first ]]; then
  selected=("${jobs[0]}")
else
  selected=("${jobs[@]:1}")
fi

for entry in "${selected[@]}"; do
  IFS='|' read -r failed_job tag runner_name <<< "$entry"
  if [[ ! -f "$runner_dir/$runner_name" ]]; then
    echo "ERROR: missing runner for $tag" >&2
    exit 1
  fi
  if [[ -e "$output_dir/sim_${tag}.root" || -e "$output_dir/sim_${tag}.log" ]]; then
    echo "ERROR: output already exists for $tag" >&2
    exit 1
  fi
  if squeue -h -u "$USER" -o '%j' | rg -Fxq "svt_${tag}"; then
    echo "ERROR: a job is already queued for $tag" >&2
    exit 1
  fi
done

for entry in "${selected[@]}"; do
  IFS='|' read -r failed_job tag runner_name <<< "$entry"
  new_job="$(sbatch --parsable --job-name="svt_${tag}" \
    --chdir="$repo_root" --output="$output_dir/slurm-%x-%j.out" \
    "$batch_script" "$tag" "$events" "$runner_dir/$runner_name")"
  echo "$failed_job -> $new_job | $tag | $events events | $runner_name"
done
