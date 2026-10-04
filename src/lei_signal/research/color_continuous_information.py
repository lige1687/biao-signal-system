"""Causal continuous expressions of qualified daily color history.

These are descriptive research features at the day's close, not trade signals.
Twenty-day shares require twenty consecutive qualified daily colors; a missing
quote or an unfinished 252-day warmup makes the share unknown.
"""
from __future__ import annotations

from collections import defaultdict, deque
import math

from .color_history_information import history_rows
from .technical_persistence_information import _segment_features
from .top_structure_information import _known


def _old_ema_direction_share(payload: dict) -> dict[tuple[str, str], float]:
    """Reuse the registered EMA-slope control's exact existing calculation."""
    calendar = payload.get("calendar", [])
    by_key = {(bar["asset"], bar["date"]): bar for bar in payload.get("bars", [])}
    assets = payload.get("assets") or sorted({asset for asset, _ in by_key})
    control: dict[tuple[str, str], float] = {}
    for asset in assets:
        segment: list[dict] = []
        def flush():
            for bar, item in zip(segment, _segment_features(segment)):
                if item is not None and item["features"] is not None:
                    control[(asset, bar["date"])] = item["features"]["ema20_up_share20"]
            segment.clear()
        for day in calendar:
            bar = by_key.get((asset, day))
            if bar is not None and _known(bar):
                segment.append(bar)
            elif segment:
                flush()
        if segment:
            flush()
    return control


def continuous_rows(payload: dict) -> list[dict]:
    """Add strict color/EMA shares and 19-pair switch frequency to history rows."""
    old_ema_share = _old_ema_direction_share(payload)
    result = []
    recent: deque[dict] = deque(maxlen=20)
    last_asset = None
    for row in history_rows(payload):
        if row["asset"] != last_asset:
            recent.clear()
            last_asset = row["asset"]
        # history_rows includes every calendar date. An unqualified date is a
        # hard break; its color is never interpreted as gray.
        if not row["ready_252"] or row["color20"] not in ("green", "gray", "black"):
            recent.clear()
        else:
            recent.append(row)
        complete = len(recent) == 20
        colors = [item["color20"] for item in recent] if complete else []
        above = [item["distance_to_ema20"] > 0 for item in recent] if complete else []
        output = dict(row)
        output.update(
            green_share20=sum(color == "green" for color in colors) / 20 if complete else None,
            switch_frequency20=sum(a != b for a, b in zip(colors, colors[1:])) / 19
            if complete else None,
            ema_above_share20=sum(above) / 20 if complete else None,
            ema20_up_share20=old_ema_share.get((row["asset"], row["date"])),
            color20_green=int(row["color20"] == "green") if row["ready_252"] else None,
            color20_black=int(row["color20"] == "black") if row["ready_252"] else None,
            color20_gray=int(row["color20"] == "gray") if row["ready_252"] else None,
            color60_green=int(row["color60"] == "green") if row["ready_252"] else None,
            color60_black=int(row["color60"] == "black") if row["ready_252"] else None,
            color60_gray=int(row["color60"] == "gray") if row["ready_252"] else None,
            asset_510050=int(row["asset"] == "510050.SS"),
            asset_510500=int(row["asset"] == "510500.SS"),
            asset_588000=int(row["asset"] == "588000.SS"),
        )
        result.append(output)
    return result


def same_day_ranks(rows: list[dict], field: str) -> list[dict]:
    """Return copies with ``{field}_rank``: average tied ascending rank 0..1.

    Only ready observations with finite numeric values participate. A date with
    fewer than two valid ETF values yields None. Equal values receive their
    average rank, so a constant field across >=2 ETFs yields 0.5 and carries
    no same-day discrimination.
    """
    if field in {"color20", "color60", "gray_origin", "group", "state20", "state60"}:
        raise ValueError("categorical states must not be ranked as numeric codes")
    grouped: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for i, row in enumerate(rows):
        value = row.get(field)
        if (row.get("ready_252") and isinstance(value, (int, float))
                and not isinstance(value, bool) and math.isfinite(value)):
            grouped[row["date"]].append((i, float(value)))
    ranks: dict[int, float] = {}
    for items in grouped.values():
        if len(items) < 2:
            continue
        ordered = sorted(items, key=lambda item: item[1])
        j = 0
        while j < len(ordered):
            k = j + 1
            while k < len(ordered) and ordered[k][1] == ordered[j][1]:
                k += 1
            rank = ((j + 1 + k) / 2 - 1) / (len(ordered) - 1)
            for index, _ in ordered[j:k]:
                ranks[index] = rank
            j = k
    key = f"{field}_rank"
    return [{**row, key: ranks.get(i)} for i, row in enumerate(rows)]
