#!/usr/bin/env python3
"""TEST ONLY: build SYNTHETIC refplanes shards from real old shards, so the
analysis chain (analyze_refplane_efficiency.py) can be exercised before real
reference-plane simulation exists. The silicon fields are real (old
extractions: z=0 acceptance_v1, +/-100 mm acceptance_v2); the plane fields are
a TOY MODEL and carry no physics:

  plane z     = z_plane from the given plane map;
  plane p     = generated momentum (no field, no scattering);
  plane (x,y) = for primaries with a silicon hit on the disk: the mean hit
                moved back along the generated direction to z_plane
                (so the propagated true point reproduces the mean hit);
                otherwise the straight-line projection from the vertex;
  reached     = silicon hit, OR (projection inside the plane annulus and a
                uniform random number < 0.97, mimicking upstream losses);
  time        = |z_plane| / c, crossings = 1.

Usage: make_synthetic_refplane_shards_20261106.py PLANE_MAP OUTPUT_ROOT N_SHARDS_PER_SIDE
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from reduce_disk_acceptance import DISKS, configuration_name

here = Path(__file__).resolve().parent
SOURCES = {0: "acceptance_v1", 100: "acceptance_v2_vz_p100mm", -100: "acceptance_v2_vz_m100mm"}
plane_map = pd.read_csv(sys.argv[1]).set_index("disk")
output_root = Path(sys.argv[2])
n_shards = int(sys.argv[3])
rng = np.random.default_rng(20261106)

for vz, source in SOURCES.items():
    for side in DISKS:
        configuration = configuration_name(vz, side)
        for path in sorted((here / "extracted" / source / configuration).glob("particles_*.npz"))[:n_shards]:
            with np.load(path) as stored:
                s = {k: stored[k] for k in stored.files}
            meta = json.loads(str(s.pop("metadata_json")))
            n = len(s["p_GeV"])
            px, py, pz = (s[k].astype(float) for k in ("px_GeV", "py_GeV", "pz_GeV"))
            vx, vy, vzz = (s[k].astype(float) for k in ("vertex_x_mm", "vertex_y_mm", "vertex_z_mm"))
            plane = {k: np.full((n, 5), np.nan, np.float32) for k in
                     ("plane_x_mm", "plane_y_mm", "plane_z_mm", "plane_t_ns", "plane_px_GeV", "plane_py_GeV", "plane_pz_GeV")}
            mask = np.zeros(n, np.uint8)
            crossings = np.zeros((n, 5), np.uint16)
            for i, (disk, *_rest) in enumerate(DISKS[side]):
                row = plane_map.loc[disk]
                zp = float(row.z_plane_mm)
                hit = (s["hit_mask"] & np.uint8(1 << i)) != 0
                with np.errstate(divide="ignore", invalid="ignore"):
                    x_line = vx + (zp - vzz) * px / pz
                    y_line = vy + (zp - vzz) * py / pz
                    hz = s["mean_hit_z_mm"][:, i].astype(float)
                    x_hit = s["mean_hit_x_mm"][:, i] + (zp - hz) * px / pz
                    y_hit = s["mean_hit_y_mm"][:, i] + (zp - hz) * py / pz
                x = np.where(hit, x_hit, x_line)
                y = np.where(hit, y_hit, y_line)
                # On-plane test about the plane centre (v2 map); centred fallback for 9-column maps.
                r = np.hypot(x - row.get("center_x_mm", 0.0), y - row.get("center_y_mm", 0.0))
                r_inner = row.get("r_inner_about_center_mm", row.rmin_mm)
                r_outer = row.get("r_outer_about_center_mm", row.rmax_mm)
                same_direction = np.sign(pz) == np.sign(zp)
                reached = hit | (same_direction & (r >= r_inner) & (r <= r_outer) & (rng.random(n) < 0.97))
                mask[reached] |= np.uint8(1 << i)
                crossings[reached, i] = 1
                for key, values in (("plane_x_mm", x), ("plane_y_mm", y), ("plane_z_mm", np.full(n, zp)),
                                    ("plane_t_ns", np.full(n, abs(zp) / 299.792458)),
                                    ("plane_px_GeV", px), ("plane_py_GeV", py), ("plane_pz_GeV", pz)):
                    plane[key][reached, i] = values[reached]
            meta.update({"format_version": "refplanes-1-SYNTHETIC-TOY", "plane_collection_present": True,
                         "plane_hits_total": int(crossings.sum()), "plane_hits_accepted": int(crossings.sum()),
                         "plane_hits_dropped_not_primary": 0, "plane_hits_secondary_flagged": 0,
                         "plane_hits_other_side": 0, "synthetic_source_shard": str(path)})
            out = output_root / configuration / path.name
            out.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(out, metadata_json=np.asarray(json.dumps(meta)), plane_mask=mask,
                                plane_crossings=crossings, plane_secondary_flagged=np.zeros((n, 5), np.uint16),
                                **s, **plane)
            print(f"wrote {out}")
