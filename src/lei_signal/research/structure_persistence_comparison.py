"""Research-only, causal post-top persistence states; no archived runner imports.

Callers must hash-check the frozen detector and inputs before use. The detector
may be run once per qualified continuous segment: only first-published node
fields are consumed here. Future invalidated_date/is_valid are never read.
"""

from __future__ import annotations

import math
import random
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class Node:
    side: str
    confirmed_date: str
    reference_date: str
    reference_price: float
    trigger_price: float
    final_price: float

    @classmethod
    def published(cls, structure):
        """Read only fields frozen at the node's first confirmation."""
        return cls(structure.side, structure.confirmed_date.isoformat(),
                   structure.reference_date.isoformat(), float(structure.reference_price),
                   float(structure.trigger_price), float(structure.final_price))

    def identity(self, asset: str, segment: int):
        return (asset, segment, self.side, self.confirmed_date, self.reference_date,
                self.reference_price, self.trigger_price, self.final_price)


@dataclass(frozen=True)
class Group:
    high: float
    low: float
    first_date: str
    completed_date: str


def _finite_positive(value):
    return isinstance(value, (float, int)) and math.isfinite(value) and value > 0


def append_group(groups: list[Group], day: str, high: float, low: float) -> bool:
    """Append a noncontained group or extend only the mutable current tail."""
    if not _finite_positive(high) or not _finite_positive(low) or high < low:
        raise ValueError("invalid daily high/low")
    if groups:
        tail = groups[-1]
        contains = (high <= tail.high and low >= tail.low) or (high >= tail.high and low <= tail.low)
        if contains:
            groups[-1] = Group(max(high, tail.high), min(low, tail.low),
                               tail.first_date, day)
            return False
    groups.append(Group(high, low, day, day))
    return True


def validate_nodes(nodes: list[Node], asset: str, segment: int, dates: set[str]):
    by_date: dict[str, list[Node]] = {}
    identities = set()
    same_side_day = set()
    for node in nodes:
        if node.side not in ("top", "bottom") or node.confirmed_date not in dates:
            raise ValueError("node side or confirmation date outside segment")
        if node.reference_date > node.confirmed_date or not all(_finite_positive(x) for x in
                (node.reference_price, node.trigger_price, node.final_price)):
            raise ValueError("invalid frozen node fields")
        identity = node.identity(asset, segment)
        side_day = (node.side, node.confirmed_date)
        if identity in identities or side_day in same_side_day:
            raise ValueError("duplicate or conflicting same-side same-day node")
        identities.add(identity)
        same_side_day.add(side_day)
        by_date.setdefault(node.confirmed_date, []).append(node)
    return by_date


def build_segment_features(*, asset: str, segment: int, bars: list[dict], nodes: list[Node],
                           ema20: list[float | None], warmup: int = 252) -> list[dict]:
    """Evaluate both candidates on every qualified scheduled day in one segment.

    `bars` has no gaps/unknowns and is chronological. The caller must split at
    each missing or unqualified scheduled day and then begin a new segment.
    """
    if len(bars) != len(ema20) or warmup < 21:
        raise ValueError("EMA length or warmup")
    dates = [row["date"] for row in bars]
    if dates != sorted(set(dates)):
        raise ValueError("duplicate or unordered segment dates")
    by_date = validate_nodes(nodes, asset, segment, set(dates))
    groups: list[Group] = []
    closes: list[float] = []
    root = previous_top = None
    root_date = episode_id = None
    root_index = -1
    seed_index = -1
    bar_active, bar_comparisons = True, 0
    node_state, node_progress = "pending", 0
    output = []
    for index, bar in enumerate(bars):
        day = bar["date"]
        high, low, close, open_price = (float(bar[k]) for k in ("high", "low", "close", "open"))
        if not all(_finite_positive(v) for v in (open_price, close, high, low)) or high < max(close, open_price) or low > min(close, open_price):
            raise ValueError("invalid qualified OHLC")
        appended = append_group(groups, day, high, low)
        closes.append(close)
        today_nodes = by_date.get(day, [])
        tops = [node for node in today_nodes if node.side == "top"]
        bottoms = [node for node in today_nodes if node.side == "bottom"]
        prior_bar = bars[index - 1] if index else None
        raw_rebound = (prior_bar is not None and
                       (high > float(prior_bar["high"]) or low > float(prior_bar["low"])))
        sma_flag = (close > closes[index - 20]) if index >= 20 else None
        ema_now = ema20[index]
        ema_prior = ema20[index - 1] if index else None
        ema_flag = (ema_now > ema_prior) if (ema_now is not None and ema_prior is not None
                     and math.isfinite(ema_now) and math.isfinite(ema_prior)) else None
        row = {"asset": asset, "date": day, "close": close, "segment": segment, "qualified_bars": index + 1,
               "evaluation_eligible": index + 1 >= warmup,
               "sma20_rising": sma_flag, "ema20_rising": ema_flag,
               "top_confirmed": bool(tops), "bottom_confirmed": bool(bottoms),
               "new_effective_group": appended, "raw_rebound": raw_rebound,
               "episode_id": None, "root_date": None,
               "root_day": False, "episode_day": False, "terminal": False,
               "root_high_break": False, "new_bottom": False,
               "same_day_seed_conflict": False, "bar_state": None, "bar_comparison_count": None,
               "node_state": None, "node_progress_count": None, "node_value": None,
               "bar_value": None, "episode_age_bars": None}
        if row["evaluation_eligible"] and (sma_flag is None or ema_flag is None):
            raise ValueError("baseline directions unavailable after warmup")
        if root is not None:
            row["episode_id"], row["root_date"] = episode_id, root_date
            row["episode_day"] = True
            row["episode_age_bars"] = index - root_index
            row["root_high_break"] = high > root.reference_price
            row["new_bottom"] = bool(bottoms)
            if row["root_high_break"] or row["new_bottom"]:
                row.update(terminal=True, bar_value=0, node_value=0,
                           bar_state="terminal", node_state="terminal",
                           bar_comparison_count=bar_comparisons,
                           node_progress_count=node_progress)
                root = previous_top = None
            else:
                if len(groups) - 1 > seed_index:
                    if appended:
                        bar_comparisons += 1
                    previous_group, current_group = groups[-2], groups[-1]
                    if not (current_group.high < previous_group.high and current_group.low < previous_group.low):
                        bar_active = False
                if tops and node_state != "broken":
                    top = tops[0]
                    if not (top.reference_price < previous_top.reference_price and
                            top.final_price < previous_top.final_price):
                        node_state = "broken"
                    else:
                        node_progress += 1
                        previous_top = top
                        node_state = "active"
                row.update(bar_value=int(bar_active), bar_state="active" if bar_active else "broken",
                           bar_comparison_count=bar_comparisons,
                           node_value=int(node_state == "active"), node_state=node_state,
                           node_progress_count=node_progress)
        elif tops:
            if bottoms:
                row["same_day_seed_conflict"] = True
            else:
                root = previous_top = tops[0]
                root_date = day
                root_index = index
                episode_id = "|".join(map(str, root.identity(asset, segment)))
                seed_index = len(groups) - 1
                bar_active, bar_comparisons = True, 0
                node_state, node_progress = "pending", 0
                row.update(root_day=True, episode_id=episode_id, root_date=day,
                           bar_state="root", node_state="root",
                           bar_comparison_count=0, node_progress_count=0)
        output.append(row)
    return output


def target_downside20(rows: list[dict], index: int, phase_of_date: dict[str, str]) -> dict | None:
    """Matured target from next close through 21st future close, same segment/phase."""
    if index + 21 >= len(rows):
        return None
    current = rows[index]
    future = rows[index + 1:index + 22]
    phase = phase_of_date.get(current["date"])
    if phase is None or any(phase_of_date.get(r["date"]) != phase or
                            r["segment"] != current["segment"] for r in future):
        return None
    prices = [float(r["close"]) for r in future]
    if not all(_finite_positive(p) for p in prices):
        return None
    return {"downside_pct": 100 * max(0.0, 1 - min(prices) / prices[0]),
            "terminal_return_pct": 100 * (prices[-1] / prices[0] - 1),
            "matured_at": future[-1]["date"]}


def phase(day: str) -> str | None:
    if "2022-01-04" <= day <= "2024-12-31":
        return "early_context"
    if "2025-01-01" <= day <= "2025-12-31":
        return "eval_2025"
    if "2026-01-01" <= day <= "2026-06-30":
        return "eval_2026H1"
    return None


def mark_calendar_maturity(rows: list[dict]) -> None:
    """Feature-only endpoint eligibility; reads dates/segments, never future prices."""
    for i, row in enumerate(rows):
        row["phase"] = phase(row["date"])
        future = rows[i + 1:i + 22]
        row["calendar_mature"] = (len(future) == 21 and row["phase"] is not None
                                  and all(r["segment"] == row["segment"] and
                                          phase(r["date"]) == row["phase"] for r in future))
        if not row["evaluation_eligible"]:
            row["exclusion_reason"] = "warmup"
        elif not row["episode_day"]:
            row["exclusion_reason"] = "root_day" if row["root_day"] else "no_post_root_episode"
        elif not row["calendar_mature"]:
            row["exclusion_reason"] = "future_window_not_mature_in_phase_or_segment"
        elif row["sma20_rising"] is None or row["ema20_rising"] is None:
            row["exclusion_reason"] = "baseline_unavailable"
        else:
            row["exclusion_reason"] = None


def freeze_common_support(rows: list[dict]) -> dict:
    """Choose cells from feature/calendar maturity only, before any Y values."""
    cells: dict[tuple, dict] = {}
    for row in rows:
        if row.get("exclusion_reason") is not None or row.get("phase") not in ("eval_2025", "eval_2026H1"):
            continue
        key = (row["asset"], row["phase"], row["sma20_rising"], row["ema20_rising"])
        cell = cells.setdefault(key, {"rows": 0, "bar_0": 0, "bar_1": 0, "node_0": 0, "node_1": 0,
                                      "episode_ids": set(), "dates": set()})
        cell["rows"] += 1
        cell[f"bar_{row['bar_value']}"] += 1
        cell[f"node_{row['node_value']}"] += 1
        cell["episode_ids"].add(row["episode_id"])
        cell["dates"].add(row["date"])
    retained = {key for key, value in cells.items() if all(value[f"{candidate}_{state}"] > 0
                for candidate in ("bar", "node") for state in (0, 1))}
    serialized = []
    for key, value in sorted(cells.items()):
        serialized.append({"asset": key[0], "phase": key[1], "sma20_rising": key[2],
                           "ema20_rising": key[3], "rows": value["rows"],
                           "bar_0": value["bar_0"], "bar_1": value["bar_1"],
                           "node_0": value["node_0"], "node_1": value["node_1"],
                           "episodes": len(value["episode_ids"]), "unique_dates": len(value["dates"]),
                           "retained": key in retained})
    required = {(asset, phase_name) for asset in ("510300.SS", "510050.SS", "510500.SS", "588000.SS")
                for phase_name in ("eval_2025", "eval_2026H1")}
    supported = {(key[0], key[1]) for key in retained}
    return {"cells": serialized, "retained_keys": [list(key) for key in sorted(retained)],
            "required_asset_phases": len(required), "supported_asset_phases": len(supported),
            "full_panel_eligible": supported == required,
            "missing_asset_phases": [list(key) for key in sorted(required - supported)]}


def attach_matured_targets(rows: list[dict]) -> list[dict]:
    """One fixed 21-close lookup per eligible observation; no candidate filter."""
    out = []
    by_asset = defaultdict(list)
    for row in rows:
        by_asset[row["asset"]].append(row)
    for asset in sorted(by_asset):
        series = sorted(by_asset[asset], key=lambda r: r["date"])
        phases = {r["date"]: r["phase"] for r in series}
        for i, row in enumerate(series):
            result = target_downside20(series, i, phases) if row.get("exclusion_reason") is None else None
            if row.get("exclusion_reason") is None and result is None:
                raise ValueError("feature-only maturity disagrees with actual target endpoint")
            out.append({**row, "target": result})
    return out


def _summary(rows: list[dict]) -> dict:
    values = [r["target"]["downside_pct"] for r in rows]
    terminal = [r["target"]["terminal_return_pct"] for r in rows]
    return {"rows": len(rows), "unique_dates": len({r["date"] for r in rows}),
            "episodes": len({r["episode_id"] for r in rows}),
            "mean_downside_pct": statistics.fmean(values) if values else None,
            "median_downside_pct": statistics.median(values) if values else None,
            "positive_terminal_fraction": sum(v > 0 for v in terminal) / len(terminal) if terminal else None,
            "mean_terminal_return_pct": statistics.fmean(terminal) if terminal else None,
            "median_terminal_return_pct": statistics.median(terminal) if terminal else None}


def effect_table(target_rows: list[dict], frozen_support: dict) -> dict:
    """Fixed common cells and weights, using targets only after support is frozen."""
    retained = {tuple(key) for key in frozen_support["retained_keys"]}
    eligible = [r for r in target_rows if r.get("exclusion_reason") is None and
                r["phase"] in ("eval_2025", "eval_2026H1")]
    if any(r["target"] is None for r in eligible):
        raise ValueError("missing target on matured common population")
    cell_rows = defaultdict(list)
    for row in eligible:
        key = (row["asset"], row["phase"], row["sma20_rising"], row["ema20_rising"])
        cell_rows[key].append(row)
    expected = {(c["asset"], c["phase"], c["sma20_rising"], c["ema20_rising"]): c
                for c in frozen_support["cells"]}
    if set(cell_rows) != set(expected) or any(len(value) != expected[key]["rows"] for key, value in cell_rows.items()):
        raise ValueError("feature support/count drift after label attach")
    raw = []
    for asset in ("510300.SS", "510050.SS", "510500.SS", "588000.SS"):
        for phase_name in ("eval_2025", "eval_2026H1"):
            group = [r for r in eligible if r["asset"] == asset and r["phase"] == phase_name]
            entry = {"asset": asset, "phase": phase_name, "B0": _summary(group)}
            for candidate in ("bar", "node"):
                entry[candidate] = {str(state): _summary([r for r in group if r[f"{candidate}_value"] == state])
                                    for state in (0, 1)}
            raw.append(entry)
    raw_overall = {"B0": _summary(eligible)}
    for candidate in ("bar", "node"):
        raw_overall[candidate] = {str(state): _summary([r for r in eligible
            if r[f"{candidate}_value"] == state]) for state in (0, 1)}
    cell_effects = []
    for key in sorted(retained):
        rows = cell_rows[key]
        entry = {"asset": key[0], "phase": key[1], "sma20_rising": key[2],
                 "ema20_rising": key[3], "fixed_weight_numerator": len(rows)}
        for candidate in ("bar", "node"):
            one = [r["target"]["downside_pct"] for r in rows if r[f"{candidate}_value"] == 1]
            zero = [r["target"]["downside_pct"] for r in rows if r[f"{candidate}_value"] == 0]
            if not one or not zero:
                raise ValueError("frozen common cell lost a state")
            entry[candidate + "_delta"] = statistics.fmean(one) - statistics.fmean(zero)
        cell_effects.append(entry)
    asset_phase = []
    for asset in ("510300.SS", "510050.SS", "510500.SS", "588000.SS"):
        for phase_name in ("eval_2025", "eval_2026H1"):
            subset = [c for c in cell_effects if c["asset"] == asset and c["phase"] == phase_name]
            if not subset:
                asset_phase.append({"asset": asset, "phase": phase_name, "status": "insufficient"})
                continue
            denominator = sum(c["fixed_weight_numerator"] for c in subset)
            asset_phase.append({"asset": asset, "phase": phase_name, "status": "supported",
                                "retained_rows": denominator, "retained_cells": len(subset),
                                **{candidate + "_delta": sum(c[candidate + "_delta"] *
                                      c["fixed_weight_numerator"] for c in subset) / denominator
                                   for candidate in ("bar", "node")}})
    primary = {"status": "insufficient"}
    if frozen_support["full_panel_eligible"] and all(r["status"] == "supported" for r in asset_phase):
        primary = {"status": "supported", **{candidate + "_delta": statistics.fmean(
            r[candidate + "_delta"] for r in asset_phase) for candidate in ("bar", "node")}}
    values = [r["target"]["downside_pct"] for r in eligible]
    median = statistics.median(values) if values else None
    counterexamples = []
    compositions = []
    for candidate in ("bar", "node"):
        for asset in ("510300.SS", "510050.SS", "510500.SS", "588000.SS"):
            for phase_name in ("eval_2025", "eval_2026H1"):
                subset = sorted((r for r in eligible if r["asset"] == asset and r["phase"] == phase_name),
                                key=lambda r: r["date"])
                counterexamples.append({"candidate": candidate, "asset": asset, "phase": phase_name,
                    "state_1_no_downside": [{"date": r["date"], "episode_id": r["episode_id"]}
                        for r in subset if r[f"{candidate}_value"] == 1 and r["target"]["downside_pct"] == 0][:3],
                    "state_0_high_downside": [{"date": r["date"], "episode_id": r["episode_id"],
                                               "downside_pct": r["target"]["downside_pct"]}
                        for r in subset if r[f"{candidate}_value"] == 0 and median is not None and
                        r["target"]["downside_pct"] > median][:3]})
                compositions.append({"candidate": candidate, "asset": asset, "phase": phase_name,
                    "state_counts": dict(Counter(r[f"{candidate}_state"] for r in subset)),
                    "episode_age_bars": dict(sorted(Counter(r["episode_age_bars"] for r in subset).items())),
                    "progress_counts": dict(sorted(Counter(r["node_progress_count"] for r in subset).items()))})
    return {"raw": raw, "raw_overall": raw_overall, "cells": cell_effects, "asset_phase": asset_phase,
            "primary": primary, "counterexamples": counterexamples,
            "compositions": compositions,
            "descriptive_high_downside_median": median}


def moving_block_intervals(target_rows: list[dict], frozen_support: dict,
                           full_calendar: list[str], *, seed: int = 20261009,
                           draws: int = 1000, lengths: tuple[int, ...] = (60, 20)) -> dict:
    """Synchronous date blocks; same fixed cells/weights, invalid joint draws kept."""
    if not frozen_support["full_panel_eligible"]:
        return {str(length): {"status": "insufficient_original_support", "valid_draws": 0}
                for length in lengths}
    retained = {tuple(key) for key in frozen_support["retained_keys"]}
    weights = {key: cell["rows"] for cell in frozen_support["cells"]
               if (key := (cell["asset"], cell["phase"], cell["sma20_rising"], cell["ema20_rising"])) in retained}
    by_phase_date = defaultdict(list)
    for row in target_rows:
        key = (row["asset"], row["phase"], row["sma20_rising"], row["ema20_rising"])
        if row.get("exclusion_reason") is None and key in retained:
            by_phase_date[(row["phase"], row["date"])].append(row)
    phase_dates = {name: [day for day in full_calendar if phase(day) == name]
                   for name in ("eval_2025", "eval_2026H1")}
    result = {}
    for length in lengths:
        rng = random.Random(seed)
        if any(len(days) < length for days in phase_dates.values()):
            result[str(length)] = {"status": "insufficient_calendar", "valid_draws": 0}
            continue
        pairs = []
        for _ in range(draws):
            counts = Counter()
            for phase_name, days in phase_dates.items():
                sampled = []
                while len(sampled) < len(days):
                    start = rng.randrange(len(days) - length + 1)
                    sampled.extend(days[start:start + length])
                counts.update((phase_name, day) for day in sampled[:len(days)])
            aggregates = defaultdict(lambda: [0.0, 0, 0.0, 0])
            for phase_day, multiplicity in counts.items():
                for row in by_phase_date.get(phase_day, ()):
                    key = (row["asset"], row["phase"], row["sma20_rising"], row["ema20_rising"])
                    for candidate in ("bar", "node"):
                        state = row[candidate + "_value"]
                        entry = aggregates[(key, candidate)]
                        entry[state * 2] += multiplicity * row["target"]["downside_pct"]
                        entry[state * 2 + 1] += multiplicity
            if any(aggregates[(key, candidate)][1] == 0 or aggregates[(key, candidate)][3] == 0
                   for key in retained for candidate in ("bar", "node")):
                continue
            pair = {}
            for candidate in ("bar", "node"):
                ap_values = []
                for asset in ("510300.SS", "510050.SS", "510500.SS", "588000.SS"):
                    for phase_name in ("eval_2025", "eval_2026H1"):
                        keys = [key for key in retained if key[0] == asset and key[1] == phase_name]
                        denominator = sum(weights[key] for key in keys)
                        ap_values.append(sum(weights[key] *
                            (aggregates[(key, candidate)][2] / aggregates[(key, candidate)][3] -
                             aggregates[(key, candidate)][0] / aggregates[(key, candidate)][1])
                            for key in keys) / denominator)
                pair[candidate] = statistics.fmean(ap_values)
            pairs.append(pair)
        if len(pairs) < 900:
            result[str(length)] = {"status": "interval_insufficient", "valid_draws": len(pairs),
                                   "attempted_draws": draws}
        else:
            def percentile(sorted_values, pct):
                position = (len(sorted_values) - 1) * pct
                left = int(position)
                right = min(left + 1, len(sorted_values) - 1)
                return sorted_values[left] + (position - left) * (sorted_values[right] - sorted_values[left])
            result[str(length)] = {"status": "interval_available", "valid_draws": len(pairs),
                                   "attempted_draws": draws,
                                   **{candidate: {"lower_1_25": percentile(sorted(p[candidate] for p in pairs), 0.0125),
                                                  "upper_98_75": percentile(sorted(p[candidate] for p in pairs), 0.9875)}
                                      for candidate in ("bar", "node")}}
    return result
