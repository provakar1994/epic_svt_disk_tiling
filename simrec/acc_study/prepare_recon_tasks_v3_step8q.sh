#!/usr/bin/env bash
# Generate (do not submit) the 300 reconstruction tasks for the acceptance_v3_refplanes npsim files,
# using the Step 8q ACTS material map made from epic_craterlake_tracking_only.xml.
# - Reads the v3 sim manifest (task_lists/acceptance_v3_refplanes/manifest.tsv) for tag, vertex,
#   eta range and seed (the seed is only recorded; eicrecon does not use it).
# - Each task: ACC_MATERIAL_MAP=<map> run_sim.sh recon <v3 config dir> <tag> 100000 ...
#   ACC_XML is NOT set, so eicrecon uses the plain installed epic_craterlake_tracking_only.xml
#   (the reference planes are not in the ACTS geometry; the extra plane-hit collections in the
#   sim files are ignored).
# - Output: rec_<tag>.root / rec_<tag>.log next to the sim files, as in acceptance_v1.
# Submit with: sbatch --time=01:00:00 --job-name=svt-v3-rec submit_premium_packed.sh task_lists/<name>/tasks.txt
# Usage: ./prepare_recon_tasks_v3_step8q.sh [TASK_LIST_NAME]
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/../.." && pwd)"
runner="$script_dir/run_sim.sh"
name="${1:-acceptance_v3_refplanes_rec_step8q}"
sim_manifest="$script_dir/task_lists/acceptance_v3_refplanes/manifest.tsv"
material_map="$project_dir/matmap/step8q_20261106T222257Z/material-map_map.cbor"
expected_map_sha="b5ce1f2ef05a20149c2c4153bb818abe2648ee6b0d95a638cd935b9153873843"
output_root="/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v3_refplanes"
task_dir="$script_dir/task_lists/$name"

[[ ! -e "$task_dir" ]] || { echo "ERROR: task directory exists: $task_dir" >&2; exit 2; }
[[ -f "$sim_manifest" ]] || { echo "ERROR: missing $sim_manifest" >&2; exit 2; }
[[ "$(sha256sum "$material_map" | cut -d' ' -f1)" == "$expected_map_sha" ]] || { echo "ERROR: map checksum mismatch" >&2; exit 2; }

mkdir -p "$task_dir"
task_file="$task_dir/tasks.txt"
manifest="$task_dir/manifest.tsv"
{
  echo "# Reconstruction of acceptance_v3_refplanes (300 x 100k events), mode recon"
  echo "# ACC_MATERIAL_MAP=$material_map (sha256 $expected_map_sha)"
  echo "# Compact XML: run_sim.sh default \$DETECTOR_PATH/epic_craterlake_tracking_only.xml"
} > "$task_file"
printf 'task\tconfiguration\tvertex_z_mm\teta_min\teta_max\tchunk\tevents\tseed\ttag\n' > "$manifest"

n=0
missing=0
while IFS=$'\t' read -r task configuration vz eta_min eta_max chunk events seed tag; do
  sim_file="$output_root/$configuration/rootfiles/sim_${tag}.root"
  [[ -s "$sim_file" ]] || { echo "MISSING sim file: $sim_file" >&2; missing=$((missing + 1)); continue; }
  [[ ! -e "$output_root/$configuration/rootfiles/rec_${tag}.root" ]] || { echo "ERROR: rec file exists for $tag" >&2; exit 1; }
  n=$((n + 1))
  printf '%d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$n" "$configuration" "$vz" "$eta_min" "$eta_max" "$chunk" "$events" "$seed" "$tag" >> "$manifest"
  printf 'ACC_MATERIAL_MAP=%q ' "$material_map" >> "$task_file"
  printf '%q ' "$runner" recon "$output_root/$configuration" "$tag" "$events" "$vz" "$eta_min" "$eta_max" "$seed" >> "$task_file"
  printf '\n' >> "$task_file"
done < <(tail -n +2 "$sim_manifest")

[[ "$missing" -eq 0 && "$n" -eq 300 ]] || { echo "ERROR: $n tasks, $missing missing sim files (expected 300, 0)" >&2; exit 1; }
echo "Wrote $n tasks to $task_file"
