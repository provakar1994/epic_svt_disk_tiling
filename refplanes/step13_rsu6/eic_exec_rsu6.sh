#!/usr/bin/env bash
# Step 14b copy of refplanes/eic_exec.sh: run one command string inside eic_xl:26.09.0-stable with the
# locally installed EPIC (DETECTOR_PATH -> epic/install/share/epic).
# Only change: the command starts in refplanes/step13_rsu6/ (this directory has no compact/ subdirectory),
# so the relative module_placements path compact/tracking/silicon_disks_tiling/20261110_ES/rsu6 cannot
# resolve against the CWD (e.g. the EPIC source tree) and resolves to $DETECTOR_PATH/... (the install).
# Usage: eic_exec_rsu6.sh "<command string>"
set -euo pipefail
[[ $# -eq 1 ]] || { echo "Usage: $0 '<command string>'" >&2; exit 2; }
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ ! -e "$here/compact" ]] || { echo "ERROR: $here/compact exists; it would shadow DETECTOR_PATH" >&2; exit 2; }
runtime=/cvmfs/oasis.opensciencegrid.org/mis/singularity/bin/singularity
image=/cvmfs/singularity.opensciencegrid.org/eicweb/eic_xl:26.09.0-stable
epic_root=/global/cfs/cdirs/m3763/pdatta/epic
inner="set +u; source $epic_root/install/bin/thisepic.sh; export DETECTOR_PATH=$epic_root/install/share/epic; export OMP_NUM_THREADS=1; set -u; cd $here; $1"
exec "$runtime" exec -B /global/cfs,/global/homes,/pscratch "$image" /opt/local/bin/eic-shell "$inner"
