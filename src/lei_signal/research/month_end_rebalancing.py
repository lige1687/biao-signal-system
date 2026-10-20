"""Bounded, synthetic-friendly monthly stock/bond drift research calculations.

This is an observational research mechanism, not a LEI technical signal or a
trade/account simulator. Prices are raw, dividends are ex-date cash amounts,
and the supplied rows are assumed to be an already qualified common calendar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


ASSETS = ("SPY", "IEF")
PANEL_COLUMNS = tuple(f"{asset}_{field}" for asset in ASSETS
                      for field in ("close", "open", "dividend"))


def total_return(close: pd.Series, dividend: pd.Series) -> pd.Series:
    """Close-to-close economic index, starting at one.

    Dividend on date t belongs to the holder from t-1 close through t close.
    Split events must already be absent; this function assumes zero splits.
    """
    if not isinstance(close, pd.Series) or not isinstance(dividend, pd.Series):
        raise TypeError("close and dividend must be Series")
    if not close.index.equals(dividend.index) or len(close) == 0:
        raise ValueError("close and dividend require identical nonempty indexes")
    if not close.index.is_unique or not close.index.is_monotonic_increasing:
        raise ValueError("dates must be unique and increasing")
    c = close.to_numpy(dtype=float)
    d = dividend.to_numpy(dtype=float)
    if not np.isfinite(c).all() or (c <= 0).any():
        raise ValueError("close must be finite and positive")
    if not np.isfinite(d).all() or (d < 0).any():
        raise ValueError("dividend must be finite and nonnegative")
    if (c[1:] + d[1:] <= 0).any():
        raise ValueError("total return factor must be positive")
    result = np.ones(len(c), dtype=float)
    result[1:] = np.cumprod((c[1:] + d[1:]) / c[:-1])
    if not np.isfinite(result).all():
        raise ValueError("economic index overflow")
    return pd.Series(result, index=close.index, name="total_return")


def calendar_drift(gs: float, gb: float, weight: float = 0.6) -> float:
    """Change from target stock weight after two positive gross returns."""
    values = np.asarray([gs, gb, weight], dtype=float)
    if not np.isfinite(values).all() or gs <= 0 or gb <= 0 or not 0 < weight < 1:
        raise ValueError("positive gross returns and interior weight required")
    return float(weight * gs / (weight * gs + (1 - weight) * gb) - weight)


def _open_to_close(panel: pd.DataFrame, index: pd.Series, asset: str,
                   entry: int, exit_: int) -> float:
    """Gross return from entry open; the entry-date dividend is excluded."""
    opening = float(panel[f"{asset}_open"].iloc[entry])
    closing = float(panel[f"{asset}_close"].iloc[entry])
    # Shares bought at the opening do not own the ex-date entitlement.
    return closing / opening * float(index.iloc[exit_] / index.iloc[entry])


def _features(panel: pd.DataFrame, indexes: dict[str, pd.Series],
              base: int, signal: int, label_end: int) -> dict:
    gs = float(indexes["SPY"].iloc[signal] / indexes["SPY"].iloc[base])
    gb = float(indexes["IEF"].iloc[signal] / indexes["IEF"].iloc[base])
    end = signal + 1
    stock_target = float(indexes["SPY"].iloc[label_end] / indexes["SPY"].iloc[signal])
    bond_target = float(indexes["IEF"].iloc[label_end] / indexes["IEF"].iloc[signal])
    return {
        "signal_date": panel.index[signal],
        "label_start": panel.index[end],
        "label_end": panel.index[label_end],
        "drift": calendar_drift(gs, gb),
        "relative_log": float(np.log(gs / gb)),
        "stock_log": float(np.log(gs)),
        "y": stock_target - bond_target,
        "y_open": (_open_to_close(panel, indexes["SPY"], "SPY", end, label_end)
                   - _open_to_close(panel, indexes["IEF"], "IEF", end, label_end)),
    }


def build_events(panel: pd.DataFrame, start, end) -> pd.DataFrame:
    """One event per complete common month, using the sixth-last close.

    The fifth subsequent common session is that month's last close. A month
    qualifies only if an input row in the next calendar month proves its end.
    The previous month's last common close is the feature baseline. A placebo
    signal is ten common sessions earlier, with the same past lookback length
    and a five-session forward target. Missing placebo history stays missing.
    """
    if not isinstance(panel, pd.DataFrame) or not isinstance(panel.index, pd.DatetimeIndex):
        raise TypeError("panel requires a DatetimeIndex DataFrame")
    if not panel.index.is_unique or not panel.index.is_monotonic_increasing:
        raise ValueError("panel dates must be unique and increasing")
    if panel.index.hasnans or not (panel.index == panel.index.normalize()).all():
        raise ValueError("panel dates must be normalized and nonmissing")
    if any(name not in panel.columns for name in PANEL_COLUMNS):
        raise ValueError(f"panel requires {PANEL_COLUMNS}")
    numbers = panel.loc[:, list(PANEL_COLUMNS)].to_numpy(dtype=float)
    if not np.isfinite(numbers).all():
        raise ValueError("missing or nonfinite quote/dividend; no calendar inner join")
    for asset in ASSETS:
        if (panel[f"{asset}_close"].to_numpy(dtype=float) <= 0).any() or (panel[f"{asset}_open"].to_numpy(dtype=float) <= 0).any():
            raise ValueError("open and close must be positive")
        if (panel[f"{asset}_dividend"].to_numpy(dtype=float) < 0).any():
            raise ValueError("dividend must be nonnegative")
    start, end = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    if start > end:
        raise ValueError("start must be no later than end")
    indexes = {asset: total_return(panel[f"{asset}_close"],
                                   panel[f"{asset}_dividend"])
               for asset in ASSETS}
    periods = panel.index.to_period("M")
    positions = {period: np.flatnonzero(periods == period) for period in periods.unique()}
    rows = []
    for month, loc in positions.items():
        if month.end_time.normalize() < start or month.end_time.normalize() > end:
            continue
        previous = positions.get(month - 1)
        # Presence of the following month is required even when end itself is
        # a calendar month-end; a truncated input cannot certify a last quote.
        if previous is None or month + 1 not in positions or len(loc) < 6:
            continue
        base = int(previous[-1])
        signal = int(loc[-6])
        last = int(loc[-1])
        event = {"month": str(month), "baseline_date": panel.index[base]}
        event.update(_features(panel, indexes, base, signal, last))
        placebo_signal = signal - 10
        placebo_base = placebo_signal - (signal - base)
        if placebo_base >= 0 and placebo_signal >= 0 and placebo_signal + 5 < len(panel):
            placebo = _features(panel, indexes, placebo_base,
                                placebo_signal, placebo_signal + 5)
            event.update({f"placebo_{key}": value for key, value in placebo.items()})
            event["placebo_baseline_date"] = panel.index[placebo_base]
        else:
            for key in ("signal_date", "label_start", "label_end", "drift",
                        "relative_log", "stock_log", "y", "y_open", "baseline_date"):
                event[f"placebo_{key}"] = pd.NaT if "date" in key or key == "label_start" or key == "label_end" else np.nan
        rows.append(event)
    return pd.DataFrame(rows)


def expanding_predictions(events: pd.DataFrame, min_train: int = 60) -> pd.DataFrame:
    """Past-matured expanding OLS predictions for four fixed feature sets.

    Evaluation rows with insufficient past labels are omitted. All four models
    use the same complete training rows, and each is fitted anew at each date.
    """
    if min_train < 1:
        raise ValueError("min_train must be positive")
    needed = ("signal_date", "label_end", "y", "stock_log", "relative_log", "drift")
    if any(column not in events.columns for column in needed):
        raise ValueError(f"events require {needed}")
    ordered = events.sort_values("signal_date").reset_index(drop=True)
    if ordered.signal_date.isna().any() or not ordered.signal_date.is_unique:
        raise ValueError("signal dates must be unique and present")
    rows = []
    predictors = ("stock_log", "relative_log", "drift")
    for _, current in ordered.iterrows():
        if current[list(predictors) + ["y"]].isna().any():
            continue
        history = ordered.loc[(ordered.label_end < current.signal_date)
                              & (ordered.signal_date < current.signal_date)]
        history = history.dropna(subset=["y", *predictors])
        if len(history) < min_train:
            continue
        y = history.y.to_numpy(dtype=float)
        if not np.isfinite(y).all():
            raise ValueError("nonfinite training labels")
        row = {"signal_date": current.signal_date, "label_end": current.label_end,
               "y": float(current.y), "train_n": len(history),
               "pred_mean": float(y.mean())}
        for feature in predictors:
            x = history[feature].to_numpy(dtype=float)
            current_x = float(current[feature])
            if not np.isfinite(x).all() or not np.isfinite(current_x):
                raise ValueError("nonfinite features")
            beta = np.linalg.lstsq(np.column_stack([np.ones(len(x)), x]), y,
                                   rcond=None)[0]
            row[f"pred_{feature}"] = float(beta[0] + beta[1] * current_x)
        rows.append(row)
    return pd.DataFrame(rows)


def circular_block_mean_interval(values, block_length: int = 12,
                                 seed: int = 20261020, reps: int = 5000) -> tuple[float, float]:
    """Descriptive 95% interval for a mean using circular month blocks.

    Ordered input must represent consecutive monthly observations. This does
    not identify causation or turn overlapping monthly targets into independent
    observations.
    """
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or len(array) == 0 or not np.isfinite(array).all():
        raise ValueError("finite nonempty one-dimensional values required")
    if block_length < 1 or reps < 1:
        raise ValueError("positive block_length and reps required")
    rng = np.random.default_rng(seed)
    n = len(array)
    draws = np.empty(reps)
    blocks = (n + block_length - 1) // block_length
    offsets = np.arange(block_length)
    for i in range(reps):
        starts = rng.integers(0, n, size=blocks)
        indices = ((starts[:, None] + offsets) % n).ravel()[:n]
        draws[i] = array[indices].mean()
    low, high = np.quantile(draws, [0.025, 0.975])
    return float(low), float(high)
