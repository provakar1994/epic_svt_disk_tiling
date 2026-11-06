#!/usr/bin/env python3
"""Unit check of the plane-hit logic in extract_disk_particles_refplanes.py on a
hand-made event block (no ROOT file). It exercises the code path that old sim
files cannot reach, until real refplanes smoke files exist:

  particle 0: two accepted hits on HD1 (t = 3.0 and 1.5 ns) -> reached, 2
              crossings, first crossing = the t = 1.5 ns hit;
  particle 1: one HD0 hit with quality bit 30 (producedBySecondary) set ->
              not reached, plane_secondary_flagged = 1;
  particle 2: one hit on an ED2 plane while the shard is the positive side ->
              ignored, counted as plane_hits_other_side;
  particle 3: no plane hits; one HD4 hit at t = 7 ns plus a silicon hit row
              (other collection) that must be ignored by the plane code;
  an unmapped (system, barrel, layer) must raise ValueError.
Run via: python3 check_extract_refplanes_synthetic_20261106.py > logs/check_extract_refplanes_synthetic_20261106.txt
"""
import numpy as np
import pandas as pd

from extract_disk_particles_refplanes import PLANE_COLLECTION, append_plane_block

lookup = {(250, 1, k + 1): ("positive", k) for k in range(5)}
lookup.update({(250, 2, k + 1): ("negative", k) for k in range(5)})
file_id = "synthetic"
particles = pd.DataFrame({"file_id": pd.Categorical([file_id] * 4, categories=[file_id]),
                          "event_entry": [0, 1, 2, 3], "mc_index": [0, 0, 0, 0]})
collections = ["TrackerEndcapHits", PLANE_COLLECTION]


def hit_table(rows):
    frame = pd.DataFrame(rows, columns=["event_entry", "collection", "system", "barrel", "layer", "quality",
                                        "time_ns", "x_mm", "y_mm", "z_mm", "px_GeV", "py_GeV", "pz_GeV"])
    frame["file_id"] = pd.Categorical([file_id] * len(frame), categories=[file_id])
    frame["mc_index"] = 0
    frame["hit_index"] = np.arange(len(frame))
    frame["hit_collection"] = pd.Categorical(frame.pop("collection"), categories=collections)
    frame["cell_barrel"] = pd.array(frame.pop("barrel"), dtype="UInt64")
    frame["system"] = pd.array(frame.system, dtype="UInt64")
    frame["layer"] = pd.array(frame.layer, dtype="UInt64")
    return frame


rows = [
    (0, PLANE_COLLECTION, 250, 1, 2, 0, 3.0, 30.0, 40.0, 444.0, 0.1, 0.2, 1.0),
    (0, PLANE_COLLECTION, 250, 1, 2, 0, 1.5, 10.0, 20.0, 444.0, 0.3, 0.4, 2.0),
    (1, PLANE_COLLECTION, 250, 1, 1, 1 << 30, 0.8, 5.0, 6.0, 244.0, 0.0, 0.0, 1.0),
    (2, PLANE_COLLECTION, 250, 2, 3, 0, 2.2, 1.0, 1.0, -644.0, 0.0, 0.0, -1.0),
    (3, PLANE_COLLECTION, 250, 1, 5, 0, 7.0, -50.0, 60.0, 1194.0, -0.1, 0.1, 5.0),
    (3, "TrackerEndcapHits", 79, 0, 4, 0, 4.0, -50.0, 60.0, 1200.0, -0.1, 0.1, 5.0),
]
storage = {name: [] for name in ("plane_mask", "plane_crossings", "plane_secondary_flagged", "plane_x_mm",
                                 "plane_y_mm", "plane_z_mm", "plane_t_ns", "plane_px_GeV", "plane_py_GeV",
                                 "plane_pz_GeV")}
counters = {"plane_hits_linked_to_primary": 0, "plane_hits_accepted": 0,
            "plane_hits_secondary_flagged": 0, "plane_hits_other_side": 0}
append_plane_block(storage, {"particles": particles, "hits": hit_table(rows)}, "positive", lookup, counters)
out = {k: v[0] for k, v in storage.items()}

checks = {
    "p0 reached HD1 only (mask 0b00010)": out["plane_mask"][0] == 0b00010,
    "p0 crossings on HD1 = 2": out["plane_crossings"][0, 1] == 2,
    "p0 first crossing is t=1.5 hit (x=10, y=20, pz=2)":
        (out["plane_t_ns"][0, 1], out["plane_x_mm"][0, 1], out["plane_y_mm"][0, 1], out["plane_pz_GeV"][0, 1])
        == (1.5, 10.0, 20.0, 2.0),
    "p1 not reached, secondary_flagged HD0 = 1":
        out["plane_mask"][1] == 0 and out["plane_secondary_flagged"][1, 0] == 1 and np.isnan(out["plane_x_mm"][1, 0]),
    "p2 not reached (other-side plane ignored)": out["plane_mask"][2] == 0,
    "p3 reached HD4 only, z=1194": out["plane_mask"][3] == 0b10000 and out["plane_z_mm"][3, 4] == 1194.0,
    "unreached entries are NaN": np.isnan(out["plane_x_mm"][0, [0, 2, 3, 4]]).all(),
    "counters": counters == {"plane_hits_linked_to_primary": 5, "plane_hits_accepted": 3,
                             "plane_hits_secondary_flagged": 1, "plane_hits_other_side": 1},
}
try:
    bad = rows + [(3, PLANE_COLLECTION, 251, 1, 1, 0, 1.0, 0, 0, 244.0, 0, 0, 1.0)]
    append_plane_block({k: [] for k in storage}, {"particles": particles, "hits": hit_table(bad)},
                       "positive", lookup, dict.fromkeys(counters, 0))
    checks["unmapped ids raise ValueError"] = False
except ValueError as error:
    checks["unmapped ids raise ValueError"] = True
    print(f"(expected error: {error})")

print("counters:", counters)
for text, value in checks.items():
    print(f"{text}: {bool(value)}")
print("OVERALL:", "PASS" if all(checks.values()) else "FAIL")
