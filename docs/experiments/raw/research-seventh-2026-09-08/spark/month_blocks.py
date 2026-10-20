"""Block-based month index generator for shared experiment draws."""

from __future__ import annotations

import math
from typing import Any

import numpy as np


def draw_indices(months: int, block_length: int, repetitions: int, seed: int) -> np.ndarray:
    """Draw shared block-based month indices.

    Returns:
        np.ndarray: shape (repetitions, months), dtype int
    """

    for name, value in {
        "months": months,
        "block_length": block_length,
        "repetitions": repetitions,
        "seed": seed,
    }.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")

    if months < 1:
        raise ValueError("months must be >= 1")
    if block_length < 1:
        raise ValueError("block_length must be >= 1")
    if block_length > months:
        raise ValueError("block_length must be <= months")
    if repetitions < 1:
        raise ValueError("repetitions must be >= 1")

    rng = np.random.default_rng(seed)
    blocks_per_row = math.ceil(months / block_length)
    starts = rng.integers(
        low=0,
        high=months - block_length + 1,
        size=(repetitions, blocks_per_row),
    )

    block_offsets = np.arange(block_length)
    rows = []
    for rep_starts in starts:
        rep_blocks = [start + block_offsets for start in rep_starts]
        indices = np.concatenate(rep_blocks)[:months]
        rows.append(indices)

    return np.vstack(rows).astype(int)
