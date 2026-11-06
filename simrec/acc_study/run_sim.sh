#!/usr/bin/env bash
# Run one acceptance-study simulation, reconstruction, or both.
# Usage: run_sim.sh sim|recon|both OUTPUT_DIR TAG EVENTS VERTEX_Z_MM ETA_MIN ETA_MAX SEED
# Optional environment overrides (unset = the original behaviour):
#   ACC_XML       compact XML for npsim/eicrecon (default $DETECTOR_PATH/epic_craterlake_tracking_only.xml)
#   ACC_STEERING  npsim --steeringFile (default: none). Command-line options below
#                 still take precedence over values set in the steering file.
set -euo pipefail

show_usage() {
  echo "Usage: $0 sim|recon|both OUTPUT_DIR TAG EVENTS VERTEX_Z_MM ETA_MIN ETA_MAX SEED" >&2
}

if [[ ${1:-} == --help || ${1:-} == -h ]]; then show_usage; exit 0; fi
if [[ $# -ne 8 ]]; then show_usage; exit 2; fi

mode="$1"
output_dir="$2"
tag="$3"
events="$4"
vertex_z_mm="$5"
eta_min="$6"
eta_max="$7"
random_seed="$8"
case "$mode" in sim|recon|both) ;; *) show_usage; exit 2 ;; esac

number_pattern='^-?[0-9]+([.][0-9]+)?$'
[[ "$tag" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo 'ERROR: unsafe TAG.' >&2; exit 2; }
[[ "$events" =~ ^[1-9][0-9]*$ && "$random_seed" =~ ^[1-9][0-9]*$ ]] || {
  echo 'ERROR: EVENTS and SEED must be positive integers.' >&2; exit 2;
}
[[ "$vertex_z_mm" =~ $number_pattern && "$eta_min" =~ $number_pattern && "$eta_max" =~ $number_pattern ]] || {
  echo 'ERROR: vertex z and eta bounds must be plain decimal numbers.' >&2; exit 2;
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
output_dir="$(realpath -m -- "$output_dir")"
[[ -f "$repo_root/install/bin/thisepic.sh" ]] || { echo 'ERROR: install this EPIC checkout first.' >&2; exit 2; }
set +u
source "$repo_root/install/bin/thisepic.sh"
set -u
export DETECTOR_PATH="$repo_root/install/share/epic"
export OMP_NUM_THREADS=1

xml="${ACC_XML:-$DETECTOR_PATH/epic_craterlake_tracking_only.xml}"
steering_file="${ACC_STEERING:-}"
material_map="$repo_root/scripts/material_map/step8m_20261020T164956Z_material-map_map.cbor"
root_dir="$output_dir/rootfiles"
log_dir="$output_dir/logs"
sim_file="$root_dir/sim_${tag}.root"
recon_file="$root_dir/rec_${tag}.root"
sim_log="$log_dir/sim_${tag}.log"
recon_log="$log_dir/rec_${tag}.log"

[[ -f "$xml" ]] || { echo "ERROR: compact XML not found: $xml" >&2; exit 2; }
[[ -z "${ACC_XML:-}" ]] || xml="$(realpath -e -- "$xml")"
if [[ -n "$steering_file" ]]; then
  [[ -f "$steering_file" ]] || { echo "ERROR: steering file not found: $steering_file" >&2; exit 2; }
  steering_file="$(realpath -e -- "$steering_file")"
fi
if [[ "$mode" != sim && ! -s "$material_map" ]]; then
  echo "ERROR: material map not found: $material_map" >&2; exit 2
fi
if [[ "$mode" != recon ]]; then
  command -v npsim >/dev/null || { echo 'ERROR: npsim unavailable.' >&2; exit 2; }
  [[ ! -e "$sim_file" && ! -e "$sim_log" ]] || { echo "ERROR: simulation output/log exists for $tag" >&2; exit 2; }
fi
if [[ "$mode" != sim ]]; then
  command -v eicrecon >/dev/null || { echo 'ERROR: eicrecon unavailable.' >&2; exit 2; }
  if [[ "$mode" == recon && ! -s "$sim_file" ]]; then
    echo "ERROR: simulation input not found: $sim_file" >&2; exit 2
  fi
  [[ ! -e "$recon_file" && ! -e "$recon_log" ]] || { echo "ERROR: reconstruction output/log exists for $tag" >&2; exit 2; }
fi

mkdir -p "$root_dir" "$log_dir"
job_id="${SLURM_JOB_ID:-local}"
rank="${SLURM_PROCID:-0}"
temporary_sim_file="${sim_file%.root}.tmp.${job_id}.${rank}.root"
temporary_recon_file="${recon_file%.root}.tmp.${job_id}.${rank}.root"
[[ ! -e "$temporary_sim_file" && ! -e "$temporary_recon_file" ]] || {
  echo 'ERROR: temporary output exists; inspect the prior failed task.' >&2; exit 2;
}

npsim_command=(
  npsim
)
if [[ -n "$steering_file" ]]; then npsim_command+=(--steeringFile "$steering_file"); fi
npsim_command+=(
  --compactFile "$xml" --outputFile "$temporary_sim_file"
  --numberOfEvents "$events" --random.seed "$random_seed" --enableGun
  --gun.phiMin "0*degree" --gun.phiMax "360*degree"
  --gun.distribution eta --gun.etaMin "$eta_min" --gun.etaMax "$eta_max"
  --gun.particle pi+ --gun.position "0 0 ${vertex_z_mm}*mm"
  --gun.momentumMin "0.5*GeV" --gun.momentumMax "20*GeV"
  --gun.multiplicity 1 --output.part WARNING
)

output_collections=(
  EventHeader MCParticles
  SiBarrelRawHits SiBarrelVertexRawHits SiEndcapTrackerRawHits
  SiBarrelNoiseRawHits SiBarrelVertexNoiseRawHits SiEndcapTrackerNoiseRawHits
  SiBarrelRawHitsWithNoise SiBarrelVertexRawHitsWithNoise SiEndcapTrackerRawHitsWithNoise
  MPGDBarrelRawHits OuterMPGDBarrelRawHits BackwardMPGDEndcapRawHits ForwardMPGDEndcapRawHits
  SiBarrelTrackerRecHits SiBarrelVertexRecHits SiEndcapTrackerRecHits
  MPGDBarrelRecHits OuterMPGDBarrelRecHits BackwardMPGDEndcapRecHits ForwardMPGDEndcapRecHits
  TOFBarrelSharedRawHits TOFBarrelSharedRecHits TOFBarrelClusterHits
  TOFEndcapSharedRawHits TOFEndcapSharedRecHits TOFEndcapClusterHits
  CentralTrackingRecHits CentralWithoutTOFTrackerMeasurements CentralTrackerMeasurements
  CentralTrackSeeds CentralTrackSeedParameters CentralCKFTrajectories
  CentralCKFTrackParameters CentralCKFTracks CentralCKFTrackAssociations
  ReconstructedChargedWithoutPIDParticles CentralTrackVertices
)
output_collections_csv=$(IFS=,; echo "${output_collections[*]}")
eicrecon_command=(
  eicrecon -Pnthreads=1 -Pjana:nevents="$events"
  -Ppodio:output_file="$temporary_recon_file" -Pdd4hep:xml_files="$xml"
  -Pacts:MaterialMap="$material_map"
  -Pectrk:siendcaptrackernoiserawhits:addnoise=0
  -Pbvtx:sibarrelvertexnoiserawhits:addnoise=0
  -Pbtrk:sibarrelnoiserawhits:addnoise=0
  -Ppodio:output_collections="$output_collections_csv"
  -Ptracking:ChargedParticlesWithAssociations:InputTags=CentralCKFTracks,CentralCKFTrackAssociations
  -Ptracking:CentralTrackVertices:InputTags=CentralCKFActsTrackStates,CentralCKFActsTracks,ReconstructedChargedWithoutPIDParticles
  "$sim_file"
)

if [[ "$mode" != recon ]]; then
  {
    echo "Started: $(date --iso-8601=seconds)"
    printf 'Tag: %s\nEvents: %s\nVertex z: %s mm\nEta: [%s, %s]\nSeed: %s\n' \
      "$tag" "$events" "$vertex_z_mm" "$eta_min" "$eta_max" "$random_seed"
    printf 'Command:'; printf ' %q' "${npsim_command[@]}"; printf '\n'
    printf 'Compact XML: %s\nSteering file: %s\n' "$xml" "${steering_file:-none}"
    sha256sum "$xml"
    [[ -z "$steering_file" ]] || sha256sum "$steering_file"
    "${npsim_command[@]}"
    echo "Finished: $(date --iso-8601=seconds)"
  } > "$sim_log" 2>&1 || { status=$?; echo "ERROR: npsim failed; see $sim_log" >&2; exit "$status"; }
  mv "$temporary_sim_file" "$sim_file"
fi

if [[ "$mode" != sim ]]; then
  {
    echo "Started: $(date --iso-8601=seconds)"
    printf 'Tag: %s\nEvents: %s\nInput: %s\n' "$tag" "$events" "$sim_file"
    printf 'Command:'; printf ' %q' "${eicrecon_command[@]}"; printf '\n'
    sha256sum "$xml" "$material_map"
    "${eicrecon_command[@]}"
    echo "Finished: $(date --iso-8601=seconds)"
  } > "$recon_log" 2>&1 || { status=$?; echo "ERROR: eicrecon failed; see $recon_log" >&2; exit "$status"; }
  mv "$temporary_recon_file" "$recon_file"
fi

echo "Completed $mode task: $tag"
