#!/usr/bin/env bash
# Pre-campaign check (coordinator, 2026-11-06): one real 20-event task through
# run_sim.sh with the refplanes overrides, exactly as the campaign tasks call it.
set -euo pipefail
P=/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling
out=/pscratch/sd/p/pdatta/svt_disk_tiling/refplanes/precampaign_test_$(date -u +%Y%m%dT%H%M%SZ)
cmd="ACC_XML=$P/refplanes/generated/epic_craterlake_tracking_only_refplanes.xml ACC_STEERING=$P/refplanes/npsim_refplanes_steering.py $P/simrec/acc_study/run_sim.sh sim $out test_vzm100_bwd 20 -100 -3.8 -0.6 43999999"
echo "Output: $out"
/cvmfs/oasis.opensciencegrid.org/mis/singularity/bin/singularity exec -B /global,/pscratch \
  /cvmfs/singularity.opensciencegrid.org/eicweb/eic_xl:26.09.0-stable /opt/local/bin/eic-shell "$cmd"
grep -E "ACC_|steering|sha256|Finished|refplanes" "$out/logs/sim_test_vzm100_bwd.log" | head -12
ls -la "$out/rootfiles"
echo "$out" > "$P/refplanes/precampaign_runsim_test.last"
