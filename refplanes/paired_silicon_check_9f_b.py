#!/usr/bin/env python3
"""Step 9f-b: paired (per-primary) silicon comparison, installed vs overlay.

The 9f runs use identical seeds, so both geometries generate the same primaries
(checked below). A per-disk binomial z-test between the two runs is then the
wrong test: the samples are strongly correlated, so a ~1 sigma one-sided shift
on 8 of 10 disks may be significant. Here every primary is matched by
(event_entry, mc_index) and its disk-hit bit is compared directly
(McNemar test on the discordant pairs b = hit only in installed,
c = hit only in overlay; z = (c - b)/sqrt(b + c)).

Run (host, tracking env):  python refplanes/paired_silicon_check_9f_b.py
Output: shards in /pscratch/.../refplanes/silicon_9f/paired_shards/, report on stdout.
"""
import math
import sys
from pathlib import Path

import numpy as np

ACC = Path("/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/simrec/acc_study")
sys.path.insert(0, str(ACC))
import extract_disk_particles_refplanes as ex  # noqa: E402
from reduce_disk_acceptance import DISKS  # noqa: E402

RUN_DIR = Path("/pscratch/sd/p/pdatta/svt_disk_tiling/refplanes/silicon_9f")
SHARD_DIR = RUN_DIR / "paired_shards"
PLANE_MAP = Path("/global/cfs/cdirs/m3763/pdatta/epic/proj_svt_disk_tiling/refplanes/plane_map.csv")
SIDES = {"fwd": "positive", "bwd": "negative"}


def shard(kind, tag):
    source = RUN_DIR / f"sim_{kind}_{tag}.root"
    target = SHARD_DIR / f"{kind}_{tag}.npz"
    if not target.exists():
        SHARD_DIR.mkdir(parents=True, exist_ok=True)
        _, lookup = ex.read_plane_map(PLANE_MAP)
        info = {"path": str(PLANE_MAP), "sha256": "", "content": PLANE_MAP.read_text()}
        ex.extract_file(source, target, SIDES[tag], f"paired_9f_{tag}", 1000, None, lookup, info)
    return dict(np.load(target, allow_pickle=True))


worst = 0.0
for tag, side in SIDES.items():
    a, b = shard("installed", tag), shard("overlay", tag)
    key_a = a["event_entry"].astype(np.int64) * 100000 + a["mc_index"]
    key_b = b["event_entry"].astype(np.int64) * 100000 + b["mc_index"]
    assert np.array_equal(key_a, key_b), "primary lists differ"
    same_p = np.allclose(a["px_GeV"], b["px_GeV"]) and np.allclose(a["pz_GeV"], b["pz_GeV"])
    print(f"[{tag}] primaries={len(key_a)} identical generated momenta={same_p}")
    print(f"  disk  hit_inst  hit_over  only_inst(b)  only_over(c)  McNemar z")
    for i, (disk, *_rest) in enumerate(DISKS[side]):
        ha = (a["hit_mask"] >> i) & 1
        hb = (b["hit_mask"] >> i) & 1
        only_a = int(np.sum((ha == 1) & (hb == 0)))
        only_b = int(np.sum((ha == 0) & (hb == 1)))
        z = (only_b - only_a) / math.sqrt(only_a + only_b) if only_a + only_b else 0.0
        worst = max(worst, abs(z))
        print(f"  {disk:4s}  {int(ha.sum()):8d}  {int(hb.sum()):8d}  {only_a:12d}  {only_b:12d}  {z:+9.2f}")
print(f"max |McNemar z| = {worst:.2f}  ->  {'PASS' if worst < 3 else 'FAIL'} (|z| < 3)")
