#!/usr/bin/env bash
# Generate (do not submit) the 300 reconstruction tasks for the acceptance_v4_step13_rsu6 npsim files.
# Step 14b copy (2026-11-13) of prepare_recon_tasks_v4_step13.sh. Changes:
#   - reads task_lists/acceptance_v4_step13_rsu6/manifest.tsv and the rsu6 output root;
#   - every task sets ACC_XML = the frozen rsu6 TRACKING-ONLY overlay (no reference planes)
#     proj_svt_disk_tiling/geometry_overlays/step13/rsu6/epic_craterlake_tracking_only_rsu6.xml.
#     In recon mode run_sim.sh passes ACC_XML to eicrecon as -Pdd4hep:xml_files (realpath'ed), so
#     the ACTS geometry is rsu6. (v4 left ACC_XML unset = installed rsu_opt XML; that is wrong here.)
#   - every task line starts with "cd <simrec/acc_study> &&" (no compact/ there), as in the sim tasks,
#     so the overlay's relative tiling path resolves to $DETECTOR_PATH;
#   - the map must be the rsu6 map (made by the Step 14a material agent under
#     proj_svt_disk_tiling/matmap/step13_rsu6_<stamp>/material-map_map.cbor): its sha256 must equal the
#     argument, and the provenance.txt next to it must list the rsu6 tracking-only XML sha256
#     (453fda16...), i.e. the map was made from the same XML used here (CLAUDE.md rule);
#   - refuses unless refplanes/step13_rsu6/identity_check_step13_rsu6.sh passes;
#   - default task-list name acceptance_v4_step13_rsu6_rec_step13.
# As in v4: refuses before writing anything if any of the 300 sim files is missing or a rec file exists.
# Submit with (from simrec/acc_study):
#   sbatch --time=01:00:00 --job-name=svt-v4r6-rec submit_premium_packed.sh task_lists/<name>/tasks.txt
# Usage: ./prepare_recon_tasks_v4_step13_rsu6.sh MATERIAL_MAP_CBOR EXPECTED_SHA256 [TASK_LIST_NAME]
set -euo pipefail

usage() { echo "Usage: $0 MATERIAL_MAP_CBOR EXPECTED_SHA256 [TASK_LIST_NAME]" >&2; }
[[ $# -ge 2 && $# -le 3 ]] || { usage; exit 2; }

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/../.." && pwd)"
runner="$script_dir/run_sim.sh"
material_map="$(realpath -e -- "$1")" || { echo "ERROR: material map not found: $1" >&2; exit 2; }
expected_map_sha="$2"
name="${3:-acceptance_v4_step13_rsu6_rec_step13}"
[[ "$expected_map_sha" =~ ^[0-9a-f]{64}$ ]] || { echo "ERROR: EXPECTED_SHA256 must be 64 hex digits" >&2; exit 2; }
[[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo 'ERROR: unsafe task-list name.' >&2; exit 2; }
[[ ! -e "$script_dir/compact" ]] || { echo "ERROR: $script_dir/compact exists; it would shadow DETECTOR_PATH" >&2; exit 2; }
sim_manifest="$script_dir/task_lists/acceptance_v4_step13_rsu6/manifest.tsv"
output_root="/pscratch/sd/p/pdatta/svt_disk_tiling/acc_study/acceptance_v4_step13_rsu6"
task_dir="$script_dir/task_lists/$name"
identity_check="$project_dir/refplanes/step13_rsu6/identity_check_step13_rsu6.sh"
rsu6_xml="$project_dir/geometry_overlays/step13/rsu6/epic_craterlake_tracking_only_rsu6.xml"
rsu6_xml_sha=453fda16a335bb8735e8e6f616ba16f5f4970b573417818691bc0afa5ec19065
map_provenance="$(dirname "$material_map")/provenance.txt"

[[ ! -e "$task_dir" ]] || { echo "ERROR: task directory exists: $task_dir" >&2; exit 2; }
[[ -f "$sim_manifest" ]] || { echo "ERROR: missing $sim_manifest" >&2; exit 2; }
[[ "$(sha256sum "$material_map" | cut -d' ' -f1)" == "$expected_map_sha" ]] || { echo "ERROR: map checksum mismatch" >&2; exit 2; }
[[ "$(sha256sum "$rsu6_xml" | cut -d' ' -f1)" == "$rsu6_xml_sha" ]] || { echo "ERROR: rsu6 XML checksum mismatch" >&2; exit 2; }
[[ -f "$map_provenance" ]] || { echo "ERROR: no provenance.txt next to the map: $map_provenance" >&2; exit 2; }
grep -q "^$rsu6_xml_sha " "$map_provenance" || {
  echo "ERROR: $map_provenance does not list the rsu6 XML sha256 $rsu6_xml_sha (map not made from rsu6?)" >&2; exit 2; }
grep -q "^$expected_map_sha " "$map_provenance" || echo "WARNING: map sha256 not listed in $map_provenance" >&2
identity_text="$("$identity_check")" || { echo "$identity_text" >&2; echo "ERROR: rsu6 geometry identity check failed." >&2; exit 2; }
n_missing=0
while IFS=$'\t' read -r _ configuration _ _ _ _ _ _ tag; do
  [[ -s "$output_root/$configuration/rootfiles/sim_${tag}.root" ]] || n_missing=$((n_missing + 1))
done < <(tail -n +2 "$sim_manifest")
[[ "$n_missing" -eq 0 ]] || { echo "ERROR: $n_missing of 300 sim files missing under $output_root; nothing written" >&2; exit 1; }

mkdir -p "$task_dir"
task_file="$task_dir/tasks.txt"
manifest="$task_dir/manifest.tsv"
echo "$identity_text" > "$task_dir/identity_check.txt"
{
  echo "# Reconstruction of acceptance_v4_step13_rsu6 (300 x 100k events), mode recon"
  echo "# ACC_MATERIAL_MAP=$material_map (sha256 $expected_map_sha)"
  echo "# Map provenance: $map_provenance (lists rsu6 XML sha256 $rsu6_xml_sha)"
  echo "# ACC_XML=$rsu6_xml (sha256 $rsu6_xml_sha)"
  echo "# Task CWD: $script_dir"
  echo "# Geometry identity (refplanes/step13_rsu6/identity_check_step13_rsu6.sh):"
  echo "$identity_text" | sed 's/^/#   /'
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
  printf 'cd %q && ' "$script_dir" >> "$task_file"
  printf 'ACC_XML=%q ACC_MATERIAL_MAP=%q ' "$rsu6_xml" "$material_map" >> "$task_file"
  printf '%q ' "$runner" recon "$output_root/$configuration" "$tag" "$events" "$vz" "$eta_min" "$eta_max" "$seed" >> "$task_file"
  printf '\n' >> "$task_file"
done < <(tail -n +2 "$sim_manifest")

[[ "$missing" -eq 0 && "$n" -eq 300 ]] || { echo "ERROR: $n tasks, $missing missing sim files (expected 300, 0)" >&2; exit 1; }
echo "Wrote $n tasks to $task_file"
echo "Submit (from $script_dir): sbatch --time=01:00:00 --job-name=svt-v4r6-rec submit_premium_packed.sh task_lists/$name/tasks.txt"
