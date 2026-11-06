#!/bin/bash

# Diagnose where eic-shell startup time is spent without modifying the image.
set -u

launcher=/global/cfs/projectdirs/m3763/pdatta/eic-shell
version=26.09.0-stable
image=/cvmfs/singularity.opensciencegrid.org/eicweb/eic_xl:${version}
runtime=/cvmfs/oasis.opensciencegrid.org/mis/singularity/bin/singularity

echo "host=$(hostname)"
echo "date=$(date --iso-8601=seconds)"

echo "== path metadata latency =="
/usr/bin/time -f 'launcher_stat_seconds=%e' stat "$launcher" >/dev/null
/usr/bin/time -f 'runtime_stat_seconds=%e' stat "$runtime" >/dev/null
/usr/bin/time -f 'image_stat_seconds=%e' stat "$image" >/dev/null

echo "== CVMFS mount status =="
findmnt -T "$image" || true
findmnt -T "$runtime" || true

echo "== direct minimal container command =="
/usr/bin/time -f 'direct_exec_seconds=%e' \
  "$runtime" exec \
  --bind /global,/gpfs,/scratch \
  "$image" /bin/true

echo "== launcher minimal command =="
cd /global/cfs/projectdirs/m3763/pdatta
/usr/bin/time -f 'launcher_exec_seconds=%e' \
  "$launcher" --version "$version" -- /bin/true

echo "== repeated launcher timings =="
for attempt in 1 2 3; do
  /usr/bin/time -f "launcher_attempt_${attempt}_seconds=%e" \
    "$launcher" --version "$version" -- /bin/true
done

echo "== interactive prompt git lookup =="
cd /global/cfs/projectdirs/m3763/pdatta/epic
/usr/bin/time -f 'git_branch_seconds=%e' git branch >/dev/null

echo "== shell initialization =="
/usr/bin/time -f 'interactive_bash_start_seconds=%e' \
  bash --noprofile --rcfile /global/homes/p/pdatta/.bashrc -i -c exit
