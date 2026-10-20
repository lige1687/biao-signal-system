"""Frozen research helpers. This module is not imported by production code."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import pandas as pd


def _valid_quote_sma(series: pd.Series, window: int, index: pd.Index) -> pd.Series:
    valid = series.dropna().astype(float)
    return valid.rolling(window, min_periods=window).mean().reindex(index)


def breadth_from_close_panel(
    close: pd.DataFrame,
    membership_by_date: Mapping[pd.Timestamp, Sequence[str]],
    minimum_coverage: float = 0.90,
) -> pd.DataFrame:
    """Compute B50/B200 with exactly the same eligible names on each date."""
    close = close.sort_index().copy()
    close.columns = [str(c).zfill(6) for c in close.columns]
    sma50 = pd.DataFrame(
        {c: _valid_quote_sma(close[c], 50, close.index) for c in close.columns},
        index=close.index,
    )
    sma200 = pd.DataFrame(
        {c: _valid_quote_sma(close[c], 200, close.index) for c in close.columns},
        index=close.index,
    )
    rows = []
    for raw_day in close.index:
        day = pd.Timestamp(raw_day)
        members = [str(c).zfill(6) for c in membership_by_date.get(day, ())]
        members = list(dict.fromkeys(members))
        total = len(members)
        quote = close.loc[day].reindex(members) if members else pd.Series(dtype=float)
        quoted = int(quote.notna().sum())
        eligible_mask = quote.notna() & sma200.loc[day].reindex(members).notna() if members else pd.Series(dtype=bool)
        eligible_names = list(eligible_mask[eligible_mask].index)
        eligible = len(eligible_names)
        coverage = eligible / total if total else np.nan
        valid = bool(total and coverage >= minimum_coverage)
        b50 = float((close.loc[day].reindex(eligible_names) > sma50.loc[day].reindex(eligible_names)).mean() * 100) if eligible else np.nan
        b200 = float((close.loc[day].reindex(eligible_names) > sma200.loc[day].reindex(eligible_names)).mean() * 100) if eligible else np.nan
        rows.append(
            {
                "date": day,
                "pool_total": total,
                "quoted": quoted,
                "eligible": eligible,
                "missing_quote": total - quoted,
                "insufficient_history": quoted - eligible,
                "missing": total - eligible,
                "coverage": coverage,
                "valid": valid,
                "b50": b50 if valid else np.nan,
                "b200": b200 if valid else np.nan,
            }
        )
    return pd.DataFrame(rows).set_index("date")


def breadth_target(value: float) -> float:
    if value < 43.3:
        return 1.0
    if value < 56.7:
        return 0.5
    return 0.0


def target_action(actual: float, target: float, band: float = 0.0) -> str:
    delta = target - actual
    if abs(delta) < band - 1e-12:
        return "none"
    if delta > 0:
        return "buy"
    if delta < 0:
        return "sell"
    return "none"


@dataclass
class BuyConfirmationState:
    """Small state machine for a raw target whose increases need confirmation."""

    current_target: float
    raw_target: float | None = None
    pending_target: float | None = None
    opportunity_start: str | None = None
    confirmed_order: dict | None = None

    def on_raw_target(self, day: str, target: float, confirmed: bool):
        self.raw_target = float(target)
        if target <= self.current_target:
            self.pending_target = None
            self.opportunity_start = None
            self.confirmed_order = None
            return {"signal_date": day, "target": float(target), "kind": "reduction"}
        if self.pending_target != float(target):
            self.pending_target = float(target)
            self.opportunity_start = day
            self.confirmed_order = None
        return self.on_confirmation(day, confirmed)

    def on_confirmation(self, day: str, confirmed: bool):
        if self.pending_target is None or self.confirmed_order is not None or not confirmed:
            return None
        self.confirmed_order = {
            "signal_date": day,
            "target": self.pending_target,
            "kind": "confirmed_increase",
            "opportunity_start": self.opportunity_start,
        }
        return dict(self.confirmed_order)

    def on_fill(self, target: float):
        self.current_target = float(target)
        self.pending_target = None
        self.opportunity_start = None
        self.confirmed_order = None


def price_trend_targets(close: pd.Series, window: int) -> pd.Series:
    valid = close.dropna().astype(float)
    sma = valid.rolling(window, min_periods=window).mean()
    out = (valid > sma).astype(float)
    out[sma.isna()] = np.nan
    return out.reindex(close.index)


def month_end_signal_dates(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    s = pd.Series(index, index=index)
    return list(s.groupby(index.to_period("M")).max())
