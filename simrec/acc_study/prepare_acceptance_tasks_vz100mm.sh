#!/usr/bin/env bash
# Generate the auditable 200-task +/-10 cm vertex campaign; do not submit it.
# Copy of prepare_acceptance_tasks.sh (acceptance_v1: 0, +/-10 mm) with only the
# vertex list, campaign name, task count and seed base changed. run_sim.sh takes
# the vertex in mm, so +/-10 cm is passed as +/-100.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
runner="$script_dir/run_sim.sh"
campaign="${1:-acceptance_v2_vz100mm}"
[[ "$campaign" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo 'ERROR: unsafe campaign name.' >&2; exit 2; }
[[ -x "$runner" ]] || { echo "ERROR: runner is not executable: $runner" >&2; exit 2; }

task_dir="$script_dir/task_lists/$campaign"
task_file="$task_dir/tasks.txt"
manifest="$task_dir/manifest.tsv"
storage_root="/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study"
output_root="$storage_root/$campaign"
[[ ! -e "$task_dir" ]] || { echo "ERROR: task directory exists: $task_dir" >&2; exit 2; }
mkdir -p "$task_dir" "$storage_root/slurm" "$output_root"

vertex_values=(100 100 -100 -100)
vertex_labels=(p100 p100 m100 m100)
eta_mins=(0.6 -3.8 0.6 -3.8)
eta_maxs=(3.8 -0.6 3.8 -0.6)
eta_labels=(p0p6_to_p3p8 m3p8_to_m0p6 p0p6_to_p3p8 m3p8_to_m0p6)
events=100000
chunks=50
seed_base=42000000  # acceptance_v1 used 41000000-41005050; no overlap

printf 'task\tconfiguration\tvertex_z_mm\teta_min\teta_max\tchunk\tevents\tseed\ttag\n' > "$manifest"
{
  echo "# Campaign: $campaign"
  echo '# 2 vertex positions (z = +/-100 mm) x 2 eta ranges x 50 chunks = 200 tasks'
  echo '# 100,000 events/task; 20,000,000 events total'
} > "$task_file"

task_number=0
for config_index in "${!vertex_values[@]}"; do
  configuration="vz_${vertex_labels[$config_index]}mm_eta_${eta_labels[$config_index]}"
  output_dir="$output_root/$configuration"
  for ((chunk = 1; chunk <= chunks; chunk++)); do
    task_number=$((task_number + 1))
    chunk_label="$(printf '%03d' "$chunk")"
    seed=$((seed_base + config_index * 1000 + chunk))
    tag="${configuration}_chunk_${chunk_label}_n${events}"
    printf '%d\t%s\t%s\t%s\t%s\t%d\t%d\t%d\t%s\n' \
      "$task_number" "$configuration" "${vertex_values[$config_index]}" \
      "${eta_mins[$config_index]}" "${eta_maxs[$config_index]}" "$chunk" \
      "$events" "$seed" "$tag" >> "$manifest"
    command=("$runner" both "$output_dir" "$tag" "$events" \
      "${vertex_values[$config_index]}" "${eta_mins[$config_index]}" \
      "${eta_maxs[$config_index]}" "$seed")
    printf '%q ' "${command[@]}" >> "$task_file"
    printf '\n' >> "$task_file"
  done
done

[[ "$task_number" -eq 200 ]] || { echo "ERROR: generated $task_number tasks, expected 200." >&2; exit 1; }
unique_seeds="$(awk 'NR > 1 {print $8}' "$manifest" | sort -u | wc -l)"
[[ "$unique_seeds" -eq 200 ]] || { echo "ERROR: generated $unique_seeds unique seeds, expected 200." >&2; exit 1; }

echo "Prepared: $task_file"
echo "Manifest: $manifest"
echo "Output:   $output_root"
echo "Submit:   sbatch $script_dir/submit_premium_packed.sh $task_file"
