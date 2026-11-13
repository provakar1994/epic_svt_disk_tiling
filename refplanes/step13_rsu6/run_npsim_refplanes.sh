#!/usr/bin/env bash
# [Step 14b rsu6 copy (2026-11-13): rsu6 overlay geometry_overlays/step13/rsu6/, container via eic_exec_rsu6.sh (CWD step13_rsu6/), identity_check_step13_rsu6.sh. Of the Step 13 copy, 2026-11-12, refplanes/step13_rsu6/: overlay = step13/generated/, steering = step13 copy, container via ../eic_exec.sh]
# Run one npsim job for the reference-plane study (Steps 9e/9f), inside the container.
# Usage: run_npsim_refplanes.sh overlay|installed OUTPUT_DIR TAG EVENTS VERTEX_Z_MM ETA_MIN ETA_MAX SEED
#   overlay   : generated/epic_craterlake_tracking_only_rsu6_refplanes.xml + npsim_refplanes_steering.py
#   installed : install/share/epic/epic_craterlake_tracking_only.xml, default npsim steering
# Gun options copied from simrec/acc_study/run_sim.sh (pi+, 0.5-20 GeV, flat eta, full phi).
# Output: OUTPUT_DIR/sim_TAG.root and OUTPUT_DIR/sim_TAG.log
set -euo pipefail
[[ $# -eq 8 ]] || { echo "Usage: $0 overlay|installed OUTPUT_DIR TAG EVENTS VZ_MM ETA_MIN ETA_MAX SEED" >&2; exit 2; }
geometry="$1"; out_dir="$2"; tag="$3"; events="$4"; vz="$5"; eta_min="$6"; eta_max="$7"; seed="$8"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
epic=/global/cfs/cdirs/m3763/pdatta/epic
case "$geometry" in
  overlay)   xml="$here/generated/epic_craterlake_tracking_only_rsu6_refplanes.xml"
             steering="--steeringFile $here/npsim_refplanes_steering.py" ;;
  installed) xml="$here/../../geometry_overlays/step13/rsu6/epic_craterlake_tracking_only_rsu6.xml"; steering="" ;;  # Step 14b: rsu6 overlay without planes
  *) echo "bad geometry $geometry" >&2; exit 2 ;;
esac
mkdir -p "$out_dir"
sim_file="$out_dir/sim_${tag}.root"; log="$out_dir/sim_${tag}.log"
[[ ! -e "$sim_file" && ! -e "$log" ]] || { echo "ERROR: output exists for $tag" >&2; exit 2; }
cmd="npsim --compactFile $xml $steering --outputFile $sim_file \
  --numberOfEvents $events --random.seed $seed --enableGun \
  --gun.phiMin '0*degree' --gun.phiMax '360*degree' \
  --gun.distribution eta --gun.etaMin $eta_min --gun.etaMax $eta_max \
  --gun.particle pi+ --gun.position '0 0 ${vz}*mm' \
  --gun.momentumMin '0.5*GeV' --gun.momentumMax '20*GeV' \
  --gun.multiplicity 1 --output.part WARNING"
{
  echo "Started: $(date -u --iso-8601=seconds)"
  echo "Geometry: $geometry"; echo "Command: $cmd"
  sha256sum "$xml"; [[ -n "$steering" ]] && sha256sum "$here/npsim_refplanes_steering.py"
  "$here/eic_exec_rsu6.sh" "$cmd"
  echo "npsim exit status: $?"
  echo "Finished: $(date -u --iso-8601=seconds)"
} > "$log" 2>&1
grep -q "npsim exit status: 0" "$log" || { echo "ERROR: npsim failed, see $log" >&2; exit 1; }
echo "done $tag"
