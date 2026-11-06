#!/usr/bin/env bash
# Run one command string inside eic_xl:26.09.0-stable with the locally
# installed EPIC geometry (DETECTOR_PATH -> epic/install/share/epic).
# Usage: eic_exec.sh "<command string>"
# Same launch pattern as simrec/acc_study/submit_premium_packed.sh.
set -euo pipefail
[[ $# -eq 1 ]] || { echo "Usage: $0 '<command string>'" >&2; exit 2; }
runtime=/cvmfs/oasis.opensciencegrid.org/mis/singularity/bin/singularity
image=/cvmfs/singularity.opensciencegrid.org/eicweb/eic_xl:26.09.0-stable
epic_root=/global/cfs/cdirs/m3763/pdatta/epic
inner="set +u; source $epic_root/install/bin/thisepic.sh; export DETECTOR_PATH=$epic_root/install/share/epic; export OMP_NUM_THREADS=1; set -u; $1"
exec "$runtime" exec -B /global/cfs,/global/homes,/pscratch "$image" /opt/local/bin/eic-shell "$inner"
