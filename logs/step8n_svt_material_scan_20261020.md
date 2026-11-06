# Step 8n: SVT endcap material scan

`run_svt_material_scan_step8n.sh` reproduces the detailed six-endcap X0 scan
from `proj_svt_disk_tiling/matscan/20260720/material_scan_stdio.txt` using the
installed `epic_craterlake_tracking_only_disk_tiles_new.xml` geometry. It is
prepared but has not been run. Enter the 26.09.0-stable EIC shell, install
this checkout, then run from the repository root:

```bash
bash proj_svt_disk_tiling/logs/run_svt_material_scan_step8n.sh
```

The optional arguments are starting vertex z in centimeters and fixed phi in
degrees. For example, use `...step8n.sh -10 20` and `...step8n.sh 10 20` to
compare vertices at -10 and +10 cm. Defaults are z=0 cm and phi=20 degrees.
The scan covers -4.2 <= eta <= 4.2 in 841 bins, stops at 200 cm transverse
radius, and records X0. This is a single-phi material slice, not an azimuthal
average or an ACTS material-map validation.

Each run writes its PDF, aggregate CSV, PNG, stdout/stderr transcript, and
input checksums to a unique timestamped directory under
`proj_svt_disk_tiling/matscan/`. Existing scans are never overwritten.
