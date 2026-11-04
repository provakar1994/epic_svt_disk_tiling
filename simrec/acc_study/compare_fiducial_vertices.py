#!/usr/bin/env python3
"""Print the all-momentum fiducial hit efficiency [%] per disk for every vertex
(columns vz = -100, -10, 0, +10, +100 mm) from the v8 fiducial_efficiency CSVs,
and the vertex-to-disk distance |z_disk - z_vtx| [mm] next to each value."""
import pandas as pd
from pathlib import Path

results = Path(__file__).resolve().parent / "results"
vertices = [(-100, "_vz_m100mm", "vz_m100mm"), (-10, "_vz_m010mm", "vz_m010mm"), (0, "", "vz_000mm"),
            (10, "_vz_p010mm", "vz_p010mm"), (100, "_vz_p100mm", "vz_p100mm")]
disk_z = {"ED4": -1020, "ED3": -850, "ED2": -650, "ED1": -450, "ED0": -250,
          "HD0": 250, "HD1": 450, "HD2": 700, "HD3": 950, "HD4": 1200}
rows = {}
for vz, suffix, tag in vertices:
    t = pd.read_csv(results / f"disk_hit_efficiency_v8{suffix}" / f"fiducial_efficiency_{tag}.csv")
    t = t[t.all_momenta]
    for disk, eff in zip(t.disk, t.fiducial_efficiency):
        rows.setdefault(disk, {})[vz] = f"{100*eff:5.2f} (L={abs(disk_z[disk]-vz):4d})"
table = pd.DataFrame(rows).T.loc[list(disk_z)]
table.columns = [f"vz={c:+d} mm" for c in table.columns]
print(table.to_string())
