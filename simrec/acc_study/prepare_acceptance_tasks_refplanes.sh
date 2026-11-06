#!/usr/bin/env bash
# Generate the auditable 300-task reference-plane campaign; do not submit it.
# Copy of prepare_acceptance_tasks_vz100mm.sh with:
#   - campaign acceptance_v3_refplanes;
#   - vertices z = 0, +100, -100 mm (run_sim.sh takes mm), each with
#     eta 0.6..3.8 and -3.8..-0.6: 6 configurations x 50 chunks x 100k = 30M events;
#   - seed base 43000000 (seeds 43000001-43005050; v1 used 41000001-41005050,
#     v2 42000001-42003050; checked against task_lists/*/manifest.tsv below);
#   - mode "sim" only (no eicrecon, no material map);
#   - every command prefixed with ACC_XML=<refplanes compact XML>
#     ACC_STEERING=<refplanes npsim steering file> (opt-in run_sim.sh overrides).
#
# Usage:
#   ./prepare_acceptance_tasks_refplanes.sh [CAMPAIGN]
#       real generation into task_lists/CAMPAIGN (refuses if it exists or if
#       the refplanes XML/steering file is missing).
#   DRY_RUN_TASK_ROOT=/some/dir ./prepare_acceptance_tasks_refplanes.sh [CAMPAIGN]
#       writes task_lists-style output under /some/dir/CAMPAIGN only; creates no
#       directory on /pscratch and only warns if the refplanes files are missing.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/../.." && pwd)"          # proj_svt_disk_tiling
runner="$script_dir/run_sim.sh"
campaign="${1:-acceptance_v3_refplanes}"
[[ "$campaign" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo 'ERROR: unsafe campaign name.' >&2; exit 2; }
[[ -x "$runner" ]] || { echo "ERROR: runner is not executable: $runner" >&2; exit 2; }

# Fixed interface with the geometry agent (proj_svt_disk_tiling/refplanes/).
refplanes_xml="$project_dir/refplanes/generated/epic_craterlake_tracking_only_refplanes.xml"
refplanes_steering="$project_dir/refplanes/npsim_refplanes_steering.py"

dry_run_root="${DRY_RUN_TASK_ROOT:-}"
if [[ -n "$dry_run_root" ]]; then
  task_dir="$dry_run_root/$campaign"
else
  task_dir="$script_dir/task_lists/$campaign"
fi
task_file="$task_dir/tasks.txt"
manifest="$task_dir/manifest.tsv"
storage_root="/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study"
output_root="$storage_root/$campaign"
[[ ! -e "$task_dir" ]] || { echo "ERROR: task directory exists: $task_dir" >&2; exit 2; }

for required in "$refplanes_xml" "$refplanes_steering"; do
  if [[ ! -f "$required" ]]; then
    if [[ -n "$dry_run_root" ]]; then
      echo "WARNING (dry run): refplanes file not found yet: $required" >&2
    else
      echo "ERROR: refplanes file not found: $required" >&2; exit 2
    fi
  fi
done

if [[ -n "$dry_run_root" ]]; then
  mkdir -p "$task_dir"
else
  mkdir -p "$task_dir" "$storage_root/slurm" "$output_root"
fi

vertex_values=(0 0 100 100 -100 -100)
vertex_labels=(000 000 p100 p100 m100 m100)
eta_mins=(0.6 -3.8 0.6 -3.8 0.6 -3.8)
eta_maxs=(3.8 -0.6 3.8 -0.6 3.8 -0.6)
eta_labels=(p0p6_to_p3p8 m3p8_to_m0p6 p0p6_to_p3p8 m3p8_to_m0p6 p0p6_to_p3p8 m3p8_to_m0p6)
events=100000
chunks=50
expected_tasks=$(( ${#vertex_values[@]} * chunks ))
seed_base=43000000  # v1: 41000001-41005050; v2: 42000001-42003050; no overlap

printf 'task\tconfiguration\tvertex_z_mm\teta_min\teta_max\tchunk\tevents\tseed\ttag\n' > "$manifest"
{
  echo "# Campaign: $campaign"
  echo '# 3 vertex positions (z = 0, +100, -100 mm) x 2 eta ranges x 50 chunks = 300 tasks'
  echo '# 100,000 events/task; 30,000,000 events total; mode sim (no reconstruction)'
  echo "# ACC_XML=$refplanes_xml"
  echo "# ACC_STEERING=$refplanes_steering"
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
    command=("$runner" sim "$output_dir" "$tag" "$events" \
      "${vertex_values[$config_index]}" "${eta_mins[$config_index]}" \
      "${eta_maxs[$config_index]}" "$seed")
    printf 'ACC_XML=%q ACC_STEERING=%q ' "$refplanes_xml" "$refplanes_steering" >> "$task_file"
    printf '%q ' "${command[@]}" >> "$task_file"
    printf '\n' >> "$task_file"
  done
done

[[ "$task_number" -eq "$expected_tasks" ]] || { echo "ERROR: generated $task_number tasks, expected $expected_tasks." >&2; exit 1; }
unique_seeds="$(awk 'NR > 1 {print $8}' "$manifest" | sort -u | wc -l)"
[[ "$unique_seeds" -eq "$expected_tasks" ]] || { echo "ERROR: generated $unique_seeds unique seeds, expected $expected_tasks." >&2; exit 1; }
unique_tags="$(awk 'NR > 1 {print $9}' "$manifest" | sort -u | wc -l)"
[[ "$unique_tags" -eq "$expected_tasks" ]] || { echo "ERROR: generated $unique_tags unique tags, expected $expected_tasks." >&2; exit 1; }

# No seed may repeat one used by an earlier campaign's manifest.
shopt -s nullglob
earlier_manifests=()
for other in "$script_dir"/task_lists/*/manifest.tsv; do
  [[ "$(realpath "$other")" == "$(realpath "$manifest")" ]] || earlier_manifests+=("$other")
done
if (( ${#earlier_manifests[@]} > 0 )); then
  overlap="$(comm -12 <(awk 'NR > 1 {print $8}' "$manifest" | sort -u) \
                     <(awk 'FNR > 1 {print $8}' "${earlier_manifests[@]}" | sort -u) | wc -l)"
  [[ "$overlap" -eq 0 ]] || { echo "ERROR: $overlap seeds overlap earlier campaigns." >&2; exit 1; }
  echo "Seed overlap with ${#earlier_manifests[@]} earlier manifest(s): none"
fi

echo "Prepared: $task_file ($task_number tasks, $unique_seeds unique seeds)"
echo "Manifest: $manifest"
echo "Output:   $output_root"
if [[ -n "$dry_run_root" ]]; then
  echo "DRY RUN: nothing created under task_lists/ or $storage_root"
else
  echo "Submit:   sbatch $script_dir/submit_premium_packed.sh $task_file"
fi
