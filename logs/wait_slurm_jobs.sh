#!/usr/bin/env bash
# Block until none of the given Slurm job IDs is in the queue, then print their final sacct state.
# Usage: bash wait_slurm_jobs.sh JOBID [JOBID ...]   (poll every 5 min)
set -u
ids=$(IFS=,; echo "$*")
while [[ -n "$(squeue -h -j "$ids" 2>/dev/null)" ]]; do sleep 300; done
sacct -X -j "$ids" -o JobID,JobName%20,State,Elapsed,ExitCode
