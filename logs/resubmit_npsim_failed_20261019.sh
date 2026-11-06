#!/usr/bin/env bash
# Re-submit the 15 npsim jobs that failed before npsim started on 2026-10-17.
# The old job ID, output tag, and vertex-specific runner are recorded together.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
batch_script="$repo_root/proj_svt_disk_tiling/simrec/submit_premium_packed.sh"
runner_dir="$repo_root/proj_svt_disk_tiling/simrec"
output_dir="/pscratch/sd/p/pdatta/svt_disk_tiling/simout"
events=20000

jobs=(
  '59930767|vm10mm_job_0|run_sim.sh'
  '59930768|vm10mm_job_1|run_sim.sh'
  '59930771|vm10mm_job_2|run_sim.sh'
  '59930774|vm10mm_job_3|run_sim.sh'
  '59930776|vm10mm_job_4|run_sim.sh'
  '59930994|v0mm_job_0|run_sim_v0mm.sh'
  '59930996|v0mm_job_1|run_sim_v0mm.sh'
  '59931001|v0mm_job_2|run_sim_v0mm.sh'
  '59931004|v0mm_job_3|run_sim_v0mm.sh'
  '59931007|v0mm_job_4|run_sim_v0mm.sh'
  '59931019|v10mm_job_0|run_sim_v10mm.sh'
  '59931021|v10mm_job_1|run_sim_v10mm.sh'
  '59931026|v10mm_job_2|run_sim_v10mm.sh'
  '59931027|v10mm_job_3|run_sim_v10mm.sh'
  '59931029|v10mm_job_4|run_sim_v10mm.sh'
)

# Check the complete set before submitting any job.
for entry in "${jobs[@]}"; do
  IFS='|' read -r old_job tag runner_name <<< "$entry"
  runner="$runner_dir/$runner_name"
  if [[ ! -f "$runner" ]]; then
    echo "ERROR: missing runner for $tag: $runner" >&2
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

for entry in "${jobs[@]}"; do
  IFS='|' read -r old_job tag runner_name <<< "$entry"
  runner="$runner_dir/$runner_name"
  new_job="$(sbatch --parsable --job-name="svt_${tag}" \
    --chdir="$repo_root" --output="$output_dir/slurm-%x-%j.out" \
    "$batch_script" "$tag" "$events" "$runner")"
  echo "$old_job -> $new_job | $tag | $events events | $runner_name"
done
