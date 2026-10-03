"""Shared fixed price-window state summaries; no fitting or policy return."""
from __future__ import annotations

import pandas as pd
import numpy as np

from .workflow_inputs import _label
from .workflow_evaluation import _weights


def _summary(frame):
    if frame.empty:
        return {"rows": 0, "dates": 0, "assets": 0, "values": None}
    w = _weights(frame, "equal_asset")
    columns = ["return", "up", "above5", "loss5", "loss10", "loss15", "mae", "mfe", "max_drawdown"]
    values = {c: float(w @ frame[c].to_numpy(float)) for c in columns}
    values["mfe_to_mae"] = values["mfe"] / values["mae"] if values["mae"] else None
    return {"rows": len(frame), "dates": int(frame.date.nunique()), "assets": int(frame.asset.nunique()),
            "by_asset_rows": frame.asset.value_counts().to_dict(), "values": values,
            "weighting": "equal_asset_inside_this_group; descriptive_not_same_population_increment"}


def summarize_price_groups(observations, payload, contract):
    """Use frozen state groups and shared labels on the actually bound price axis.

    Full-history descriptions can cross year ends. Earlier/later descriptions
    contain outcomes within the earlier period or the declared evaluation year;
    this deliberately differs from a hidden recut of the full-history table.
    Same asset/year comparisons require both sides >= the frozen minimum and
    preserve their common-background weights. They are not causal increments.
    """
    spec = contract["descriptive"]
    groups, horizons = spec["groups"], spec["horizons"]
    dates = payload["calendar"]
    position = {d: i for i, d in enumerate(dates)}
    keyed = {(b["asset"], b["date"]): b for b in payload["bars"]}
    by_asset = {a: [keyed[(a, d)] for d in dates] for a in contract["universe"]["assets"]}
    base = [r for r in observations if r.get("feature_reason") is None and r.get("distance_group") in groups]
    tables, comparisons, records = [], [], []
    for horizon in horizons:
        labelled = []
        for row in base:
            target = {**contract["target"], "kind": "forward_return", "unit": "percentage_point", "end_offset": 1 + horizon}
            i = position[row["date"]]
            ret, end, error = _label(by_asset[row["asset"]], i, target)
            if error:
                continue
            path = {}
            for name in ("mae", "mfe", "max_drawdown"):
                value, _, reason = _label(by_asset[row["asset"]], i, {**target, "kind": name})
                if reason:
                    raise ValueError("path-specific description unavailable: " + str(reason))
                path[name] = value
            item = {"id": row["id"], "asset": row["asset"], "date": row["date"], "stratum": row["stratum"],
                    "group": row["distance_group"], "horizon": horizon, "label_end": end, "return": ret,
                    "up": float(ret > 0), "above5": float(ret > 5), "loss5": float(ret <= -5),
                    "loss10": float(ret <= -10), "loss15": float(ret <= -15), **path}
            labelled.append(item)
            records.append(item)
        frame = pd.DataFrame(labelled)
        if frame.empty:
            continue
        earlier = frame[(frame.date < "2024-01-01") & (frame.label_end <= "2023-12-31")]
        later = frame.loc[[any(f["eval_start"] <= r.date <= f["eval_end"] and r.label_end <= f["eval_end"]
                              for f in contract["split"]["folds"]) for r in frame.itertuples()]]
        for phase, pool in [("all", frame), ("earlier", earlier), ("later", later)]:
            overall = _summary(pool)
            tables.append({"horizon": horizon, "phase": phase, "group": "all", "opportunity_share": 1., **overall})
            for group in groups:
                part = pool[pool.group == group]
                tables.append({"horizon": horizon, "phase": phase, "group": group,
                               "opportunity_share": len(part) / len(pool) if len(pool) else None, **_summary(part)})
            if pool.empty:
                continue
            origin_w = _weights(pool, "equal_asset")
            background = pool.assign(origin_w=origin_w).groupby("stratum").origin_w.sum().to_dict()
            for group in groups:
                supported = []
                for stratum, subset in pool.groupby("stratum"):
                    left, right = subset[subset.group == group], subset[subset.group != group]
                    if len(left) >= spec["minimum_each_background"] and len(right) >= spec["minimum_each_background"]:
                        supported.append((stratum, left, right))
                total = sum(background[s] for s, _, _ in supported)
                fields = ["return", "up", "mae", "mfe", "max_drawdown", "loss5", "loss10", "loss15"]
                left_values = {c: sum(background[s] * l[c].mean() for s, l, _ in supported) / total for c in fields} if total else None
                right_values = {c: sum(background[s] * r[c].mean() for s, _, r in supported) / total for c in fields} if total else None
                retained = sum(len(l) + len(r) for _, l, r in supported)
                comparisons.append({"horizon": horizon, "phase": phase, "group": group,
                    "left": left_values, "right": right_values,
                    "difference": {c: left_values[c] - right_values[c] for c in fields} if total else None,
                    "common_strata": [s for s, _, _ in supported], "retained_rows": retained,
                    "lost_rows": len(pool) - retained, "original_rows": len(pool),
                    "left_rows": sum(len(l) for _, l, _ in supported), "right_rows": sum(len(r) for _, _, r in supported),
                    "weighting": "same_asset_year_background_from_full_pool_normalized_on_common_support",
                    "interpretation": "conditional_description_not_causal_or_full_technical_increment"})
    return {"schema_version": "price-group-descriptions/1.0", "spec": spec,
            "tables": tables, "common_background_comparisons": comparisons, "labelled_records": records}
