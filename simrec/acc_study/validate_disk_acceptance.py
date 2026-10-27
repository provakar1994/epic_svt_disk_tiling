#!/usr/bin/env python3
"""Check structural and counting invariants in disk-acceptance NPZ outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs="+")
    parser.add_argument("--expected-files-per-side", type=int)
    parser.add_argument("--expected-events-per-side", type=int)
    return parser.parse_args()


def validate(path: Path, expected_files: Optional[int], expected_events: Optional[int]) -> None:
    with np.load(path, allow_pickle=False) as data:
        metadata = json.loads(str(data["metadata_json"]))
        denominator = data["denominator_total"]
        numerator = data["numerator_total"]
        denominator_xy = data["denominator_xy"]
        numerator_xy = data["numerator_xy"]
        missing_xy = data["missing_xy"]
        assert len(data["disk_label"]) == 10
        assert denominator.shape == numerator.shape == (10,)
        assert denominator_xy.shape == numerator_xy.shape == missing_xy.shape
        assert np.all(numerator <= denominator)
        assert np.all(numerator_xy <= denominator_xy)
        np.testing.assert_array_equal(numerator_xy + missing_xy, denominator_xy)
        assert np.all(denominator_xy.sum(axis=(1, 2)) + data["outside_xy"]
                      + data["invalid_projection"] == denominator)
        assert np.all(data["raw_hits_total"] >= numerator)
        assert not np.any(np.asarray([record["processed_entries"] for record in metadata["input_files"]]) <= 0)

        for side in ("negative", "positive"):
            records = [record for record in metadata["input_files"] if record["side"] == side]
            disk_mask = data["side"] == side
            if expected_files is not None:
                assert len(records) == expected_files, (side, len(records), expected_files)
            if expected_events is not None:
                assert np.all(denominator[disk_mask] == expected_events), \
                    (side, denominator[disk_mask], expected_events)
            assert np.all(denominator[disk_mask] == denominator[disk_mask][0])

    print(f"PASS: {path}")


def main() -> None:
    args = parse_args()
    for path in args.inputs:
        validate(path, args.expected_files_per_side, args.expected_events_per_side)


if __name__ == "__main__":
    main()
