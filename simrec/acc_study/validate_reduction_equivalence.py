#!/usr/bin/env python3
"""Require physics counters/maps from two reduction NPZ files to agree exactly."""

import argparse
from pathlib import Path

import numpy as np


ARRAYS = (
    "system", "layer", "nominal_z_mm", "x_edges_mm", "y_edges_mm",
    "denominator_total", "numerator_total", "raw_hits_total",
    "denominator_xy", "numerator_xy", "missing_xy", "outside_xy",
    "invalid_projection", "residual_count",
)
FLOAT_ACCUMULATORS = ("residual_sum_x_mm", "residual_sum_y_mm", "residual_sum_r2_mm2")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    with np.load(args.reference, allow_pickle=False) as reference, \
         np.load(args.candidate, allow_pickle=False) as candidate:
        for name in ARRAYS:
            np.testing.assert_array_equal(candidate[name], reference[name], err_msg=name)
        # Extracted shards store coordinates as float32, while direct reduction
        # accumulates pandas float64 values. Only roundoff-level differences are
        # permitted in diagnostic residual sums; acceptance counters stay exact.
        for name in FLOAT_ACCUMULATORS:
            np.testing.assert_allclose(candidate[name], reference[name], rtol=2e-6, atol=2e-3,
                                       err_msg=name)
    print(f"PASS: {args.candidate} reproduces {args.reference}")


if __name__ == "__main__":
    main()
