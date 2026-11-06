#!/usr/bin/env python3
"""Step 9e diagnostic (host, tracking env): composition of plane hits not linked to the primary,
and whether low-|p| primary-linked hits are the ones flagged producedBySecondary (quality bit 30,
set when the particle handler re-attributes an unsaved secondary's hit to its saved ancestor).
Usage: python3 diagnose_smoke_secondaries_9e.py SMOKE_DIR"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parent / "simrec" / "acc_study"))
from mc_tracking_hits import read_mc_tracking_hits  # noqa: E402

BIT = 1 << 30
for path in sorted(Path(sys.argv[1]).glob("sim_*.root")):
    d = read_mc_tracking_hits(path, collections=["SVTDiskRefPlaneHits"], primary_only=False)
    parts, ph = d["particles"], d["hits"]
    key = ["event_entry", "mc_index"]
    info = parts.set_index(key)[["generator_status", "pdg", "p_GeV"]]
    j = info.reindex(pd.MultiIndex.from_frame(ph[key])).reset_index(drop=True)
    ph = pd.concat([ph.reset_index(drop=True), j], axis=1)
    sec = ph[ph.generator_status != 1]
    print(f"\n=== {path.name}: {len(ph)} plane hits, {len(sec)} not on the primary ===")
    print("  non-primary hits by linked PDG:", sec.pdg.value_counts().head(8).to_dict())
    per_event = sec.groupby("event_entry").size().sort_values(ascending=False)
    print(f"  events with non-primary hits: {len(per_event)}/100; top events (event: hits):",
          per_event.head(5).to_dict())
    prim = ph[ph.generator_status == 1].copy()
    prim["p_hit"] = np.sqrt(prim.px_GeV ** 2 + prim.py_GeV ** 2 + prim.pz_GeV ** 2)
    prim["ratio"] = prim.p_hit / prim.p_GeV
    prim["by_secondary"] = (prim.quality.astype(np.int64) & BIT) != 0
    low = prim[prim.ratio < 0.9]
    print(f"  primary-linked hits with |p_hit|/|p_gen| < 0.9: {len(low)}; of these flagged producedBySecondary: "
          f"{int(low.by_secondary.sum())}")
    clean = prim[~prim.by_secondary]
    q = np.quantile(clean.ratio, [0, 0.01, 0.1, 0.5])
    print(f"  primary-linked, NOT producedBySecondary: {len(clean)} hits; ratio quantiles 0/1/10/50% = "
          + ", ".join(f"{v:.4f}" for v in q))
    print("  crossings per (primary, plane) for those:",
          clean.groupby(key + ["system", "layer"]).size().value_counts().sort_index().to_dict())
