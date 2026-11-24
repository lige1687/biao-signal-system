"""One fixed low-volatility opponent for the monthly reversal interpretation."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


def lowvol_weights(
    features: Sequence[Mapping], frozen_groups: Mapping[str, int]
) -> dict[str, float]:
    """Use original momentum groups and their mass; no outcome enters selection."""
    good = {r["code"]: r for r in features if r["eligible"]}
    if set(good) != set(frozen_groups):
        raise ValueError("features and frozen momentum groups must have identical membership")
    if len(good) < 30 or set(frozen_groups.values()) != {1, 2, 3, 4, 5}:
        raise ValueError("requires the original five qualified groups")
    if any(not math.isfinite(float(r["vol60"])) or float(r["vol60"]) < 0 for r in good.values()):
        raise ValueError("invalid volatility")
    weights = {}
    for group in range(1, 6):
        names = [c for c in good if frozen_groups[c] == group]
        k = len(names) // 2
        if not k:
            raise ValueError("sparse frozen group")
        chosen = sorted(names, key=lambda c: (float(good[c]["vol60"]), c))[:k]
        weights.update({c: len(names) / len(good) / k for c in chosen})
    return weights
