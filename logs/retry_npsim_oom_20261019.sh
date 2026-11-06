#!/usr/bin/env bash
# Retry the 14 jobs killed by the default shared-QOS memory limit.
# Run 'pilot' first; run 'remaining' only after the pilot finishes successfully.
set -euo pipefail

if [[ $# -ne 1 || ( "$1" != pilot && "$1" != remaining ) ]]; then
  echo "Usage: $0 pilot|remaining" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
batch_script="$repo_root/proj_svt_disk_tiling/simrec/submit_premium_packed.sh"
runner_dir="$repo_root/proj_svt_disk_tiling/simrec"
output_dir="/pscratch/sd/p/pdatta/svt_disk_tiling/simout"
events=20000

jobs=(
  '59997188|vm10mm_job_1|run_sim.sh'
  '59997189|vm10mm_job_2|run_sim.sh'
  '59997190|vm10mm_job_3|run_sim.sh'
  '59997191|vm10mm_job_4|run_sim.sh'
  '59997192|v0mm_job_0|run_sim_v0mm.sh'
  '59997193|v0mm_job_1|run_sim_v0mm.sh'
  '59997195|v0mm_job_2|run_sim_v0mm.sh'
  '59997196|v0mm_job_3|run_sim_v0mm.sh'
  '59997197|v0mm_job_4|run_sim_v0mm.sh'
  '59997198|v10mm_job_0|run_sim_v10mm.sh'
  '59997199|v10mm_job_1|run_sim_v10mm.sh'
  '59997200|v10mm_job_2|run_sim_v10mm.sh'
  '59997201|v10mm_job_3|run_sim_v10mm.sh'
  '59997202|v10mm_job_4|run_sim_v10mm.sh'
)

if [[ "$1" == pilot ]]; then
  selected=("${jobs[0]}")
  dependency_args=()
else
  selected=("${jobs[@]:1}")
  # The bulk retry may start only after the full 20,000-event pilot succeeds.
  dependency_args=(--dependency=afterok:59999427)
fi

for entry in "${selected[@]}"; do
  IFS='|' read -r failed_job tag runner_name <<< "$entry"
  if [[ ! -f "$runner_dir/$runner_name" ]]; then
    echo "ERROR: missing runner for $tag" >&2
    exit 1
  fi
  if [[ -e "$output_dir/sim_${tag}.root" || -e "$output_dir/sim_${tag}.log" ]]; then
    echo "ERROR: output or log still exists for $tag" >&2
    exit 1
  fi
  if squeue -h -u "$USER" -o '%j' | rg -Fxq "svt_${tag}"; then
    echo "ERROR: a job is already queued for $tag" >&2
    exit 1
  fi
done

for entry in "${selected[@]}"; do
  IFS='|' read -r failed_job tag runner_name <<< "$entry"
  new_job="$(sbatch --parsable "${dependency_args[@]}" --job-name="svt_${tag}" \
    --chdir="$repo_root" --output="$output_dir/slurm-%x-%j.out" \
    "$batch_script" "$tag" "$events" "$runner_dir/$runner_name")"
  echo "$failed_job -> $new_job | $tag | $events events | $runner_name"
done
