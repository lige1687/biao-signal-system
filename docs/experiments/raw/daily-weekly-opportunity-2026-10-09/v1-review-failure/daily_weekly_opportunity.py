"""Research-only daily state at a completed natural week; no trading decision."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math

import pandas as pd

from lei_signal.data.calendar import CoveredCalendar
from lei_signal.data.point_in_time import aggregate_weekly
from lei_signal.features.indicators import seeded_ema
from lei_signal.rules.trend_stage import trend_stage_series

ASSETS = ("510300.SS", "510050.SS", "510500.SS", "588000.SS")
PHASES = {"eval_2025": ("2025-01-01", "2025-12-31"),
          "eval_2026H1": ("2026-01-01", "2026-06-30")}
PERIODS = (20, 60, 120)


def _date(value) -> pd.Timestamp:
    t = pd.Timestamp(value)
    if pd.isna(t) or t.tz is not None or t != t.normalize():
        raise ValueError(f"invalid natural date: {value}")
    return t


@dataclass(frozen=True)
class FlagCalendar:
    """Exact saved date flags; never infer a weekday or an uncovered date."""
    flags: dict[pd.Timestamp, bool]

    def is_trading_day(self, day) -> bool:
        d = _date(day)
        if d not in self.flags:
            raise ValueError(f"unknown calendar date {d.date()}")
        return self.flags[d]

    def last_trading_day_in_range(self, start, end):
        days = pd.date_range(_date(start), _date(end))
        opened = [d for d in days if self.is_trading_day(d)]
        return opened[-1] if opened else None

    def next_trading_day(self, day):
        d = _date(day)
        later = sorted(x for x, open_ in self.flags.items() if x > d and open_)
        if not later:
            raise ValueError("no covered next session")
        return later[0]


def covered_calendar(raw_days: dict) -> CoveredCalendar:
    if not raw_days:
        raise ValueError("empty calendar")
    flags = {}
    for key, value in raw_days.items():
        d = _date(key)
        if d in flags or not isinstance(value, dict) or type(value.get("is_trading_day")) is not bool:
            raise ValueError(f"invalid calendar flag {key}")
        flags[d] = value["is_trading_day"]
    bounds = sorted(flags)
    if len(flags) != len(pd.date_range(bounds[0], bounds[-1])):
        raise ValueError("calendar natural-day coverage gap")
    return CoveredCalendar(FlagCalendar(flags), bounds[0], bounds[-1])


def _week_periods(start, end):
    return pd.period_range(_date(start).to_period("W-SUN"),
                           _date(end).to_period("W-SUN"), freq="W-SUN")


def qualify_dates(raw_bars: list[dict], calendar: CoveredCalendar,
                  start="2020-12-21", end="2026-06-30") -> dict:
    """Stage 0 reads dates and OHLCV validity only. No actual feature or target values."""
    start, end = _date(start), _date(end)
    if not calendar.covers(start, end):
        raise ValueError("calendar does not cover input span")
    seen = {asset: set() for asset in ASSETS}
    issues = {asset: [] for asset in ASSETS}
    for row in raw_bars:
        asset = row.get("asset")
        if asset not in seen:
            continue
        d = _date(row.get("date"))
        if d < start or d > end:
            issues[asset].append(f"outside input: {d.date()}")
            continue
        if d in seen[asset]:
            issues[asset].append(f"duplicate: {d.date()}")
        seen[asset].add(d)
        if not calendar.is_trading_day(d):
            issues[asset].append(f"closed-day quote: {d.date()}")
        if row.get("status") != "quoted":
            issues[asset].append(f"unquoted: {d.date()}")
        for field in ("open", "high", "low", "close", "volume"):
            v = row.get(field)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                issues[asset].append(f"invalid {field}: {d.date()}")
    weeks = []
    closed_weeks = []
    for period in _week_periods(start, end):
        monday, sunday = period.start_time.normalize(), period.end_time.normalize()
        if monday < start or sunday > end:
            continue
        expected = {d for d in pd.date_range(monday, sunday) if calendar.is_trading_day(d)}
        if not expected:
            closed_weeks.append(str(sunday.date()))
            continue
        weeks.append((sunday, expected))
    result = {"status": "passed", "input_start": str(start.date()),
              "input_end": str(end.date()), "complete_open_weeks": len(weeks),
              "all_closed_weeks": closed_weeks, "assets": {}}
    for asset in ASSETS:
        details = issues[asset]
        chain = 0
        first_121 = None
        phase_weeks = {phase: 0 for phase in PHASES}
        for sunday, expected in weeks:
            actual = seen[asset] & {d for d in pd.date_range(sunday - pd.Timedelta(days=6), sunday)}
            for d in sorted(expected - actual):
                details.append(f"missing declared session: {d.date()}")
            for d in sorted(actual - expected):
                details.append(f"unexpected session: {d.date()}")
            chain = chain + 1 if actual == expected else 0
            if chain == 121 and first_121 is None:
                first_121 = str(sunday.date())
            for phase, (lo, hi) in PHASES.items():
                if lo <= str(sunday.date()) <= hi and chain >= 121:
                    phase_weeks[phase] += 1
        result["assets"][asset] = {"quoted_days": len(seen[asset]),
                                   "first_121_week_sunday": first_121,
                                   "qualified_review_weeks_by_phase": phase_weeks,
                                   "issues": sorted(set(details))}
        if details or first_121 is None:
            result["status"] = "failed"
    return result


def _features(frame: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({"close": frame["close"].astype(float)}, index=frame.index)
    for p in PERIODS:
        out[f"sma{p}"] = out.close.rolling(p, min_periods=p).mean()
        out[f"ema{p}"] = seeded_ema(out.close, p)
    out["close_lag20"] = out.close.shift(20)
    out["ema20_slope"] = out.ema20.diff()
    out["sma120_change"] = out.sma120.diff()
    out["ema120_change"] = out.ema120.diff()
    out["stage"] = trend_stage_series(out)
    return out


def feature_rows(daily: pd.DataFrame, calendar: CoveredCalendar) -> list[dict]:
    """Stage 1 only. Caller must have a passing date receipt and explicit release."""
    daily = daily.sort_index()
    if not daily.index.is_unique:
        raise ValueError("duplicate daily date")
    daily_features = _features(daily)
    complete_end = daily.index[-1].to_period("W-SUN").end_time.normalize()
    week_start = complete_end - pd.Timedelta(days=6)
    if (not calendar.covers(week_start, complete_end) or
            calendar.last_trading_day_in_range(week_start, complete_end) > daily.index[-1]):
        complete_end -= pd.Timedelta(days=7)
    weekly = aggregate_weekly(daily.loc[:complete_end], calendar=calendar,
                              as_of=complete_end, complete_bar=True)
    week_features = _features(weekly)
    week_positions = {pd.Timestamp(row.week_end).normalize(): i
                      for i, (_, row) in enumerate(weekly.iterrows())}
    rows = []
    for period in _week_periods(daily.index[0], daily.index[-1]):
        monday, sunday = period.start_time.normalize(), period.end_time.normalize()
        if sunday > calendar.coverage_end or monday < calendar.coverage_start:
            continue
        sessions = [d for d in pd.date_range(monday, sunday) if calendar.is_trading_day(d)]
        if not sessions:
            continue
        if sunday not in week_positions:
            raise ValueError(f"missing completed week {sunday.date()}")
        week_number = week_positions[sunday]
        last = sessions[-1]
        d = daily_features.loc[last]
        w = week_features.iloc[week_number]
        ready = (daily.index.searchsorted(last, side="right") >= 121 and week_number + 1 >= 121
                 and d[[f"sma{p}" for p in PERIODS] + [f"ema{p}" for p in PERIODS]].notna().all()
                 and w[[f"sma{p}" for p in PERIODS] + [f"ema{p}" for p in PERIODS]
                       + ["sma120_change", "ema120_change"]].notna().all())
        phase = next((name for name, (lo, hi) in PHASES.items()
                      if lo <= str(sunday.date()) <= hi), None)
        rows.append({"observation_at": str(sunday.date()) + "T23:59:59+08:00",
                     "price_session_date": str(last.date()), "phase": phase,
                     "qualified": bool(ready), "reason": None if ready else "121_bar_warmup",
                     "X": int(d.stage >= 3) if ready else None,
                     "B1": min(int(w.stage), 4) if ready else None,
                     "daily_stage": int(d.stage) if ready else None,
                     "weekly_stage": int(w.stage) if ready else None,
                     "daily_steps": {f"step{i}": bool(d.stage >= i) for i in range(1, 6)} if ready else None,
                     "weekly_steps": {f"step{i}": bool(w.stage >= i) for i in range(1, 6)} if ready else None,
                     "daily": {k: float(d[k]) if pd.notna(d[k]) else None for k in
                               [f"sma{p}" for p in PERIODS] + [f"ema{p}" for p in PERIODS]},
                     "weekly": {k: float(w[k]) if pd.notna(w[k]) else None for k in
                                [f"sma{p}" for p in PERIODS] + [f"ema{p}" for p in PERIODS]},
                     "weekly_sma120_direction": int(math.copysign(1, w.sma120_change)) if ready and w.sma120_change != 0 else 0 if ready else None,
                     "weekly_ema120_direction": int(math.copysign(1, w.ema120_change)) if ready and w.ema120_change != 0 else 0 if ready else None})
    return rows


def label_dates(observation_at: str, calendar: CoveredCalendar) -> tuple[str, str] | None:
    """Date-only maturity, no price access."""
    obs = _date(observation_at[:10])
    later = [d for d in pd.date_range(obs + pd.Timedelta(days=1), calendar.coverage_end)
             if calendar.is_trading_day(d)]
    if len(later) < 21:
        return None
    s1, s21 = later[0], later[20]
    phase = next((p for p, (lo, hi) in PHASES.items() if lo <= str(obs.date()) <= hi), None)
    if phase is None or not (PHASES[phase][0] <= str(s1.date()) <= str(s21.date()) <= PHASES[phase][1]):
        return None
    return str(s1.date()), str(s21.date())


def label_values(closes: list[float]) -> dict:
    """Only for a separately released target pass: exactly 21 saved economic closes."""
    if len(closes) != 21 or any(not isinstance(v, (int, float)) or
                                 isinstance(v, bool) or not math.isfinite(v) or v <= 0
                                 for v in closes):
        raise ValueError("target requires 21 finite positive closes")
    r20 = 100 * (closes[-1] / closes[0] - 1)
    mae = 100 * max(0, 1 - min(closes) / closes[0])
    return {"R20_pct": r20, "MAE20_pct": mae, "positive20": r20 > 0}


def effect_cells(rows: list[dict]) -> dict:
    """Fixed full-population denominator; unsupported nonempty category blocks full delta."""
    groups = {}
    for row in rows:
        key = (row["asset"], row["phase"])
        groups.setdefault(key, []).append(row)
    result = {}
    for key, group in groups.items():
        n = len(group)
        cells = []
        missing = []
        total = 0.0
        for stage in range(5):
            category = [r for r in group if r["B1"] == stage]
            by_x = {x: [r for r in category if r["X"] == x] for x in (0, 1)}
            dates = {x: len({r["observation_at"] for r in by_x[x]}) for x in (0, 1)}
            supported = not category or all(dates[x] >= 2 for x in (0, 1))
            means = {x: sum(r["R20_pct"] for r in by_x[x]) / len(by_x[x]) if by_x[x] else None
                     for x in (0, 1)}
            delta = means[1] - means[0] if category and supported else None
            weight = len(category) / n
            cells.append({"B1": stage, "N": len(category), "weight": weight,
                          "N_X0": len(by_x[0]), "N_X1": len(by_x[1]),
                          "distinct_dates_X0": dates[0], "distinct_dates_X1": dates[1],
                          "mean_R20_X0_pct": means[0], "mean_R20_X1_pct": means[1],
                          "delta_pct_points": delta})
            if category and not supported:
                missing.append(stage)
            if delta is not None:
                total += weight * delta
        result["|".join(key)] = {"N": n, "cells": cells,
                                 "unsupported_stages": missing,
                                 "full_delta_pct_points": None if missing else total}
    return result


def support_cells(rows: list[dict]) -> dict:
    """Feature-only support uses dates, states and fixed future session dates, never prices."""
    admitted = [r for r in rows if r["qualified"] and r["phase"] is not None
                and r.get("label_dates") is not None]
    groups = {}
    for row in admitted:
        groups.setdefault((row["asset"], row["phase"]), []).append(row)
    result = {}
    for (asset, phase), group in groups.items():
        cells = []
        missing = []
        for stage in range(5):
            category = [r for r in group if r["B1"] == stage]
            by_x = {x: [r for r in category if r["X"] == x] for x in (0, 1)}
            dates = {x: len({r["observation_at"] for r in by_x[x]}) for x in (0, 1)}
            if category and any(dates[x] < 2 for x in (0, 1)):
                missing.append(stage)
            cells.append({"B1": stage, "N": len(category), "weight": len(category) / len(group),
                          "N_X0": len(by_x[0]), "N_X1": len(by_x[1]),
                          "distinct_dates_X0": dates[0], "distinct_dates_X1": dates[1]})
        result[f"{asset}|{phase}"] = {"N": len(group), "cells": cells,
                                     "unsupported_stages": missing,
                                     "full_comparison_admissible": not missing}
    return result


def describe_effect(rows: list[dict]) -> dict:
    """Descriptive output; no fitted model, interval, or independent-N claim."""
    import statistics

    def summary(group):
        if not group:
            return {"N": 0, "distinct_review_dates": 0, "state_runs": 0,
                    "mean_R20_pct": None, "median_R20_pct": None,
                    "positive_rate": None, "mean_MAE20_pct": None, "median_MAE20_pct": None}
        ordered = sorted(group, key=lambda r: r["observation_at"])
        return {"N": len(group),
                "distinct_review_dates": len({r["observation_at"] for r in group}),
                "state_runs": 1 + sum(ordered[i]["X"] != ordered[i - 1]["X"]
                                      for i in range(1, len(ordered))),
                "mean_R20_pct": statistics.mean(r["R20_pct"] for r in group),
                "median_R20_pct": statistics.median(r["R20_pct"] for r in group),
                "positive_rate": sum(r["positive20"] for r in group) / len(group),
                "mean_MAE20_pct": statistics.mean(r["MAE20_pct"] for r in group),
                "median_MAE20_pct": statistics.median(r["MAE20_pct"] for r in group)}

    groups = {}
    for row in rows:
        groups.setdefault((row["asset"], row["phase"]), []).append(row)
    b1 = effect_cells(rows)
    result = {}
    for (asset, phase), group in groups.items():
        key = f"{asset}|{phase}"
        ordered = sorted(group, key=lambda r: r["observation_at"])
        runs_by_x = {0: 0, 1: 0}
        for i, row in enumerate(ordered):
            if i == 0 or row["X"] != ordered[i - 1]["X"]:
                runs_by_x[row["X"]] += 1
        b0 = {"all": summary(group), "X0": summary([r for r in group if r["X"] == 0]),
              "X1": summary([r for r in group if r["X"] == 1])}
        b0["X0"]["state_runs"] = runs_by_x[0]
        b0["X1"]["state_runs"] = runs_by_x[1]
        wrong_true = sorted((r for r in group if r["X"] == 1 and r["R20_pct"] <= 0),
                            key=lambda r: r["observation_at"])
        missed = sorted((r for r in group if r["X"] == 0 and r["R20_pct"] > 0),
                        key=lambda r: r["observation_at"])
        direction = {}
        for row in group:
            dkey = f"{row['weekly_sma120_direction']}/{row['weekly_ema120_direction']}"
            direction.setdefault(dkey, []).append(row)
        result[key] = {"B0": b0,
                       "B1": b1[key],
                       "weekly_long_direction": {k: summary(v) for k, v in direction.items()},
                       "counterexamples": {"true_nonpositive_count": len(wrong_true),
                                           "true_nonpositive_first5": wrong_true[:5],
                                           "false_positive_count": len(missed),
                                           "false_positive_first5": missed[:5]}}
    phase_equal_asset = {}
    for phase in PHASES:
        vals = [b1[f"{asset}|{phase}"]["full_delta_pct_points"]
                for asset in ASSETS if f"{asset}|{phase}" in b1]
        phase_equal_asset[phase] = statistics.mean(vals) if len(vals) == 4 and all(v is not None for v in vals) else None
    return {"asset_phase": result, "equal_four_asset_by_phase_pct_points": phase_equal_asset,
            "shared_dates_and_overlapping_windows_are_not_independent": True}
