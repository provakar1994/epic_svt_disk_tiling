#!/usr/bin/env python3
"""Step 9f: per-disk silicon efficiency with and without the reference-plane overlay
(host, conda env 'tracking').

For each run, per disk: fraction of generated primaries (generatorStatus == 1) with at least
one TrackerEndcapHits hit linked directly to that primary on that disk. Disk = (system, layer)
from simrec/acc_study/README.md. Forward runs (eta 0.6..3.8) are evaluated on HD0-HD4,
backward runs (eta -3.8..-0.6) on ED0-ED4. All primaries of the run form the denominator.

Comparison: z = (f_overlay - f_installed) / sqrt(f(1-f) (1/n1 + 1/n2)) with the pooled
fraction f (binomial, independent samples). Gate: |z| < 3 for every disk.
Usage: python3 analyze_silicon_unchanged_9f.py RUN_DIR
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent / "simrec" / "acc_study"))
from mc_tracking_hits import read_mc_tracking_hits  # noqa: E402

SILICON_DISKS = {(68, 1): "ED0", (69, 1): "ED1", (70, 2): "ED2", (70, 3): "ED3", (70, 4): "ED4",
                 (77, 1): "HD0", (78, 1): "HD1", (79, 2): "HD2", (79, 3): "HD3", (79, 4): "HD4"}


def disk_fractions(path, disks):
    data = read_mc_tracking_hits(path, collections=["TrackerEndcapHits"], primary_only=True, pdgs=211)
    parts, hits = data["particles"], data["hits"]
    n = len(parts)
    hits = hits.assign(disk=[SILICON_DISKS.get((int(s), int(l)), "?") for s, l in zip(hits.system, hits.layer)])
    out = {}
    for d in disks:
        k = hits[hits.disk == d][["event_entry", "mc_index"]].drop_duplicates().shape[0]
        out[d] = (k, n)
    return out, n, len(hits)


def main():
    run_dir = Path(sys.argv[1])
    rows = []
    for direction, disks in (("fwd", [f"HD{i}" for i in range(5)]), ("bwd", [f"ED{i}" for i in range(5)])):
        res = {}
        for geo in ("installed", "overlay"):
            path = run_dir / f"sim_{geo}_{direction}.root"
            res[geo], n, nh = disk_fractions(path, disks)
            print(f"{path.name}: {n} primaries, {nh} primary-linked TrackerEndcapHits")
        for d in disks:
            k1, n1 = res["installed"][d]
            k2, n2 = res["overlay"][d]
            f1, f2 = k1 / n1, k2 / n2
            fp = (k1 + k2) / (n1 + n2)
            sigma = np.sqrt(fp * (1 - fp) * (1 / n1 + 1 / n2))
            z = (f2 - f1) / sigma if sigma > 0 else 0.0
            rows.append(dict(disk=d, n_installed=n1, k_installed=k1, f_installed=f1, n_overlay=n2,
                             k_overlay=k2, f_overlay=f2, diff=f2 - f1, sigma=sigma, z=z, ok=abs(z) < 3))
    table = pd.DataFrame(rows)
    with pd.option_context("display.float_format", "{:.4f}".format, "display.width", 200):
        print(table.to_string(index=False))
    ok = bool(table.ok.all())
    print(f"\nmax |z| = {table.z.abs().max():.2f}")
    print(f"Step 9f silicon-unchanged gate (|z| < 3 on every disk): {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
