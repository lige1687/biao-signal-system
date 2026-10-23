#!/usr/bin/env python3
"""Frozen sequential SPY account scenarios; synthetic checks only unless authorized."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_CONTRACT = Path(__file__).with_name("contract.json")
STRATEGIES = ("sma10", "hold", "fixed50")
FEE_RATES = (0.0, 0.001, 0.0025)
PERIODS = {
    "early": ("1994-01", "2014-12", 252),
    "primary": ("2015-01", "2024-12", 120),
    "recent": ("2025-01", "2026-08", 20),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _json_write(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _clean_number(value: Any) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _period_str(value: Any) -> str:
    return pd.Period(value, freq="M").strftime("%Y-%m")


def _month_range(first: str, last: str) -> list[str]:
    return [str(x) for x in pd.period_range(first, last, freq="M")]


def _normal_col(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _date_series(frame: pd.DataFrame, source: str) -> pd.Series:
    work = frame.reset_index() if isinstance(frame.index, pd.DatetimeIndex) else frame.copy()
    candidates = {_normal_col(c): c for c in work.columns}
    date_col = next((candidates[x] for x in ("date", "datetime", "timestamp", "index") if x in candidates), None)
    if date_col is None:
        raise ValueError(f"{source}: no date column or DatetimeIndex")
    values = pd.to_datetime(work[date_col], errors="raise", utc=True).dt.tz_convert(None).dt.normalize()
    if values.isna().any():
        raise ValueError(f"{source}: null dates")
    if values.duplicated().any():
        raise ValueError(f"{source}: duplicate daily dates")
    return values


def _price_column(frame: pd.DataFrame, aliases: tuple[str, ...], field: str) -> pd.Series:
    columns = {_normal_col(c): c for c in frame.columns}
    for alias in aliases:
        key = _normal_col(alias)
        if key in columns:
            s = pd.to_numeric(frame[columns[key]], errors="raise").astype(float)
            if not np.isfinite(s.to_numpy()).all() or (s <= 0).any():
                raise ValueError(f"invalid/nonpositive {field} values")
            return s
    raise ValueError(f"missing {field}; expected one of {aliases}")


def load_ohlc_parquet(path: Path, *, need_ohlc: bool, label: str) -> tuple[pd.DataFrame, str]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} input does not exist: {path}")
    digest = sha256_file(path)
    raw = pd.read_parquet(path)
    dates = _date_series(raw, label)
    frame = raw.reset_index() if isinstance(raw.index, pd.DatetimeIndex) else raw.copy()
    frame = frame.loc[:, ~frame.columns.duplicated()]
    frame["date"] = dates.to_numpy()
    if not frame["date"].is_monotonic_increasing:
        raise ValueError(f"{label}: source dates are not in ascending order")
    if frame["date"].duplicated().any():
        raise ValueError(f"{label}: duplicate dates before sorting")
    if need_ohlc:
        # Validate available volume/amount fields when present; zeros are invalid
        # because this input is expected to contain traded sessions only.
        normalized = {_normal_col(c): c for c in frame.columns}
        for name in ("volume", "amount", "turnover"):
            col = normalized.get(name)
            if col is not None:
                values = pd.to_numeric(frame[col], errors="raise").astype(float)
                if not np.isfinite(values.to_numpy()).all() or (values <= 0).any():
                    raise ValueError(f"{label}: {name} must be finite and positive")
    frame = frame.sort_values("date", kind="mergesort").reset_index(drop=True)
    if frame["date"].duplicated().any():
        raise ValueError(f"{label}: duplicate dates after normalization")
    if need_ohlc:
        # Contracted source is Yahoo adjusted OHLC. Prefer explicit adjusted columns
        # when supplied; otherwise use the source's contracted auto-adjusted OHLC.
        frame["open"] = _price_column(frame, ("adjusted_open", "adj_open", "open_adjusted", "open"), "adjusted open")
        frame["close"] = _price_column(frame, ("adjusted_close", "adj_close", "close_adjusted", "close"), "adjusted close")
    return frame, digest


def _validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("schema") != "bounded-account-scenario/1":
        raise ValueError("unsupported contract schema")
    account = contract["account"]
    if account.get("start") != "1994-01-01" or account.get("end") != "2026-08-31":
        raise ValueError("contract start/end differ from the frozen scenario")
    if account.get("continuous") is not True or account.get("cash_interest") != 0:
        raise ValueError("continuous zero-interest account required")
    if account.get("fees_each_side") != [0.0, 0.001, 0.0025]:
        raise ValueError("fee schedule differs from frozen contract")
    if account.get("position_targets") != {
        "sma10": "100% strong; 0% weak",
        "hold": "100% first opening only, then fixed adjusted units",
        "fixed50": "50% post-fee NAV at each month first open",
    }:
        raise ValueError("position target definition differs from frozen contract")
    for key, (first, last, count) in PERIODS.items():
        p = contract["periods"][key]
        if (p["first"], p["last"], p["months"]) != (first, last, count):
            raise ValueError(f"period definition mismatch: {key}")
    if contract["signal"].get("window_months") != 10:
        raise ValueError("signal window must remain ten completed months")


def build_signals(monthly_close: pd.Series, first_formation: str, last_formation: str,
                  month_last_dates: dict[str, str] | None = None,
                  month_first_dates: dict[str, str] | None = None) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    closes = {_period_str(k): float(v) for k, v in monthly_close.items()}
    formations = _month_range(first_formation, last_formation)
    records: list[dict[str, Any]] = []
    by_hold_month: dict[str, dict[str, Any]] = {}
    for formation in formations:
        last10 = _month_range(str(pd.Period(formation, freq="M") - 9), formation)
        missing = [month for month in last10 if month not in closes]
        if missing:
            raise ValueError(f"missing monthly close(s) for signal formed {formation}: {missing}")
        vals = [closes[month] for month in last10]
        mean10 = math.fsum(vals) / 10.0
        signal = "strong" if closes[formation] > mean10 else "weak"
        hold_month = str(pd.Period(formation, freq="M") + 1)
        if month_last_dates is None or month_first_dates is None:
            formation_date = str(pd.Period(formation, freq="M").end_time.date())
            action_date = str(pd.Period(hold_month, freq="M").start_time.date())
            window_dates = [str(pd.Period(m, freq="M").end_time.date()) for m in last10]
        else:
            missing_dates = [m for m in last10 if m not in month_last_dates]
            if missing_dates or hold_month not in month_first_dates:
                raise ValueError(f"missing observed formation/action date for {formation}: {missing_dates}")
            formation_date = month_last_dates[formation]
            action_date = month_first_dates[hold_month]
            window_dates = [month_last_dates[m] for m in last10]
        row = {
            "formation_month": formation,
            "formation_date": formation_date,
            "action_date": action_date,
            "hold_month": hold_month,
            "state": signal,
            "formation_close": closes[formation],
            "sma10": mean10,
            "window_months": last10,
            "window_dates": window_dates,
            "window_closes": vals,
        }
        by_hold_month[hold_month] = row
        records.append(row)
    return by_hold_month, records


@dataclass
class TradeResult:
    cash: float
    units: float
    notional: float
    fee: float
    side: str | None
    nav_before: float
    nav_after: float


def rebalance(cash: float, units: float, price: float, target_weight: float, fee_rate: float) -> TradeResult:
    if not all(math.isfinite(x) for x in (cash, units, price, target_weight, fee_rate)):
        raise ValueError("non-finite rebalance input")
    if cash < -1e-8 or units < -1e-10 or price <= 0 or not 0 <= target_weight <= 1 or fee_rate < 0:
        raise ValueError("invalid rebalance input")
    nav_before = cash + units * price
    position = units * price
    target_gap = target_weight * nav_before - position
    tol = max(1e-9, nav_before * 1e-13)
    if abs(target_gap) <= tol:
        return TradeResult(cash, units, 0.0, 0.0, None, nav_before, nav_before)
    if target_gap > 0:
        notional = target_gap / (1.0 + target_weight * fee_rate)
        fee = notional * fee_rate
        new_cash = cash - notional - fee
        new_units = units + notional / price
        side = "buy"
    else:
        denominator = 1.0 - target_weight * fee_rate
        if denominator <= 0:
            raise ValueError("invalid fee/target combination")
        notional = -target_gap / denominator
        if notional > position + tol:
            raise ArithmeticError("sell notional exceeds current position")
        notional = min(notional, position)
        fee = notional * fee_rate
        new_cash = cash + notional - fee
        new_units = units - notional / price
        side = "sell"
    nav_after = new_cash + new_units * price
    if new_cash < -tol or new_units < -1e-10:
        raise ArithmeticError("rebalance created negative cash or units")
    new_cash = max(0.0, new_cash)
    if abs((nav_before - fee) - nav_after) > max(1e-7, nav_before * 1e-11):
        raise ArithmeticError("cash-plus-units NAV identity failed")
    actual_weight = (new_units * price / nav_after) if nav_after else 0.0
    if abs(actual_weight - target_weight) > 1e-9:
        raise ArithmeticError("post-fee target weight failed")
    return TradeResult(new_cash, new_units, notional, fee, side, nav_before, nav_after)


def simulate_account(daily: pd.DataFrame, signal_by_hold_month: dict[str, dict[str, Any]], strategy: str, fee_rate: float, initial_cash: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy: {strategy}")
    cash = float(initial_cash)
    units = 0.0
    previous_close_nav: float | None = None
    previous_month: str | None = None
    first_opened = False
    daily_rows: list[dict[str, Any]] = []
    trade_rows: list[dict[str, Any]] = []
    data = daily.sort_values("date", kind="mergesort").reset_index(drop=True)
    for item in data.itertuples(index=False):
        date = pd.Timestamp(item.date)
        month = date.strftime("%Y-%m")
        is_month_open = month != previous_month
        cash_before = cash
        units_before = units
        nav_before = cash + units * float(item.open)
        overnight_return = 0.0 if previous_close_nav is None else nav_before / previous_close_nav - 1.0
        signal = signal_by_hold_month.get(month)
        if strategy == "sma10":
            if signal is None:
                raise ValueError(f"missing SMA10 signal for holding month {month}")
            target = 1.0 if signal["state"] == "strong" else 0.0
            decision = is_month_open
        elif strategy == "fixed50":
            target = 0.5
            decision = is_month_open
        else:
            target = 1.0 if not first_opened else 1.0
            decision = not first_opened
        notional = fee = 0.0
        side = None
        nav_after = nav_before
        if decision:
            result = rebalance(cash, units, float(item.open), target, fee_rate)
            cash, units = result.cash, result.units
            notional, fee, side = result.notional, result.fee, result.side
            nav_before, nav_after = result.nav_before, result.nav_after
            first_opened = True
            if side is not None:
                trade_rows.append({
                    "date": date.strftime("%Y-%m-%d"), "month": month,
                    "strategy": strategy, "fee_rate": fee_rate, "fee_bps_per_side": fee_rate * 10000,
                    "side": side, "target_weight": target,
                    "adjusted_unit_price": float(item.open), "notional": notional, "fee": fee,
                    "nav_before_trade": nav_before, "nav_after_trade": nav_after,
                    "cash_before": cash_before, "cash_after": cash,
                    "units_before": units_before, "units_after": units,
                })
        nav_close = cash + units * float(item.close)
        if not math.isfinite(nav_close) or nav_close <= 0:
            raise ArithmeticError(f"invalid close NAV at {date.date()}")
        close_return = nav_close / (previous_close_nav if previous_close_nav is not None else initial_cash) - 1.0
        signal_state = signal["state"] if signal else None
        daily_rows.append({
            "date": date.strftime("%Y-%m-%d"), "month": month,
            "strategy": strategy, "fee_rate": fee_rate, "fee_bps_per_side": fee_rate * 10000,
            "signal_state": signal_state, "decision_at_month_open": bool(decision),
            "target_weight": target, "adjusted_open": float(item.open), "adjusted_close": float(item.close),
            "overnight_return": overnight_return, "close_to_close_return": close_return,
            "nav_before_trade": nav_before, "nav_after_trade": nav_after,
            "cash_before": cash_before, "cash_after_trade": cash,
            "units_before": units_before, "units_after_trade": units,
            "trade_side": side, "trade_notional": notional, "trade_fee": fee,
            "nav_close": nav_close, "cash_close": cash,
            "position_value_close": units * float(item.close),
            "exposure_close": units * float(item.close) / nav_close,
        })
        previous_close_nav = nav_close
        previous_month = month
    return pd.DataFrame(daily_rows), pd.DataFrame(trade_rows)


def make_monthly_table(daily: pd.DataFrame, market: pd.DataFrame, signal_by_hold_month: dict[str, dict[str, Any]], initial_cash: float) -> pd.DataFrame:
    market_month_open = market.sort_values("date").groupby("month", sort=True).first()[["date", "open"]]
    market_month_open = market_month_open.rename(columns={"date": "first_date", "open": "first_open"})
    next_open = market_month_open.shift(-1)
    month_end = daily.groupby("month", sort=True).tail(1).set_index("month")
    rows = []
    prev_nav = initial_cash
    for month, endrow in month_end.iterrows():
        startrow = market_month_open.loc[month]
        nxt = next_open.loc[month]
        market_ret = None if pd.isna(nxt["first_open"]) else float(nxt["first_open"] / startrow["first_open"] - 1.0)
        sig = signal_by_hold_month.get(month)
        start_daily = daily[daily["month"] == month].iloc[0]
        rows.append({
            "month": month, "strategy": str(daily["strategy"].iloc[0]),
            "fee_rate": float(daily["fee_rate"].iloc[0]), "fee_bps_per_side": float(daily["fee_bps_per_side"].iloc[0]),
            "first_date": pd.Timestamp(startrow["first_date"]).strftime("%Y-%m-%d"),
            "month_end_date": str(endrow["date"]), "signal_state": sig["state"] if sig else None,
            "target_weight": float(start_daily["target_weight"]),
            "nav_start": prev_nav, "nav_end": float(endrow["nav_close"]),
            "monthly_return": float(endrow["nav_close"] / prev_nav - 1.0),
            "average_exposure": float(daily.loc[daily["month"] == month, "exposure_close"].mean()),
            "open_to_next_open_market_return": market_ret,
        })
        prev_nav = float(endrow["nav_close"])
    return pd.DataFrame(rows)


def _nw_interval(values: list[float], lags: int = 3) -> tuple[float | None, float | None, float | None]:
    x = np.asarray(values, dtype=float)
    n = x.size
    if n == 0:
        return None, None, None
    mean = float(x.mean())
    if n <= lags + 1:
        return mean, None, None
    u = x - mean
    long_run = float(np.dot(u, u) / n)
    for lag in range(1, min(lags, n - 1) + 1):
        gamma = float(np.dot(u[lag:], u[:-lag]) / n)
        long_run += 2.0 * (1.0 - lag / (lags + 1.0)) * gamma
    se = math.sqrt(max(0.0, long_run) / n)
    return mean, mean - 1.96 * se, mean + 1.96 * se


def _period_summary(account_daily: pd.DataFrame, account_monthly: pd.DataFrame, account_trades: pd.DataFrame,
                    hold_monthly: pd.DataFrame, period_name: str, first: str, last: str,
                    initial_cash: float, *, all_first: str = "1994-01") -> dict[str, Any]:
    months = _month_range(first, last)
    monthly = account_monthly[account_monthly["month"].isin(months)].copy()
    hold = hold_monthly[hold_monthly["month"].isin(months)].copy()
    if list(monthly["month"]) != months or list(hold["month"]) != months:
        raise ValueError(f"period month coverage mismatch: {period_name}")
    daily = account_daily[account_daily["month"].isin(months)].copy()
    if first == all_first:
        start_nav = initial_cash
    else:
        prior = str(pd.Period(first, freq="M") - 1)
        prior_rows = account_daily[account_daily["month"] == prior]
        if prior_rows.empty:
            raise ValueError(f"missing continuous-account anchor for {period_name}")
        start_nav = float(prior_rows.iloc[-1]["nav_close"])
    end_nav = float(monthly.iloc[-1]["nav_end"])
    total = end_nav / start_nav - 1.0
    n_months = len(months)
    cagr = (end_nav / start_nav) ** (12.0 / n_months) - 1.0 if end_nav > 0 else None
    nav_path = [start_nav] + [float(x) for x in daily["nav_close"].tolist()]
    peak = nav_path[0]
    max_dd = 0.0
    underwater = longest_underwater = 0
    for nav in nav_path[1:]:
        peak = max(peak, nav)
        max_dd = min(max_dd, nav / peak - 1.0)
        if nav < peak:
            underwater += 1
            longest_underwater = max(longest_underwater, underwater)
        else:
            underwater = 0
    end_recovered = bool(nav_path[-1] >= max(nav_path[:-1])) if len(nav_path) > 1 else True
    strategy = str(account_daily["strategy"].iloc[0])
    fee_rate = float(account_daily["fee_rate"].iloc[0])
    trades = account_trades[account_trades["date"].str.slice(0, 7).isin(months)] if not account_trades.empty else account_trades
    returns = [float(x) for x in monthly["monthly_return"]]
    hold_returns = [float(x) for x in hold["monthly_return"]]
    diff = [a - b for a, b in zip(returns, hold_returns)]
    paired_mean, paired_low, paired_high = _nw_interval(diff, lags=3)
    target = monthly["target_weight"].to_numpy(dtype=float)
    market_returns = monthly["open_to_next_open_market_return"].to_numpy(dtype=object)
    missed = avoided = 0.0
    missed_count = avoided_count = 0
    decomp_rows = []
    for month, w, r in zip(months, target, market_returns):
        if r is None or pd.isna(r):
            continue
        r = float(r)
        gap = 1.0 - float(w)
        miss = gap * max(r, 0.0)
        avoid = gap * max(-r, 0.0)
        missed += miss
        avoided += avoid
        missed_count += int(miss > 0)
        avoided_count += int(avoid > 0)
        decomp_rows.append((month, r, gap, miss, avoid))
    largest_missed = max((x for x in decomp_rows if x[3] > 0), key=lambda x: x[3], default=None)
    largest_avoided = max((x for x in decomp_rows if x[4] > 0), key=lambda x: x[4], default=None)
    hold_start = initial_cash if first == all_first else float(hold_monthly[hold_monthly["month"] == str(pd.Period(first, freq="M") - 1)].iloc[-1]["nav_end"])
    hold_end = float(hold.iloc[-1]["nav_end"])
    nav_at_trade = trades["nav_before_trade"].astype(float) if not trades.empty else pd.Series(dtype=float)
    fee_sum = float(trades["fee"].sum()) if not trades.empty else 0.0
    fee_nav_sum = float((trades["fee"] / trades["nav_before_trade"]).sum()) if not trades.empty else 0.0
    return {
        "period": period_name, "first_month": first, "last_month": last, "months": n_months,
        "strategy": strategy, "fee_bps_per_side": fee_rate * 10000,
        "start_nav": start_nav, "end_nav": end_nav, "total_return": total,
        "cagr_exact_month_count": cagr, "max_drawdown_daily_close_in_slice": max_dd,
        "longest_underwater_trading_days": longest_underwater, "period_end_recovered": end_recovered,
        "average_exposure": float(monthly["average_exposure"].mean()),
        "trade_count": int(len(trades)),
        "buy_count": int((trades["side"] == "buy").sum()) if not trades.empty else 0,
        "sell_count": int((trades["side"] == "sell").sum()) if not trades.empty else 0,
        "fee_dollars": fee_sum, "sum_fee_over_nav_before_trade": fee_nav_sum,
        "same_fee_hold_total_return": hold_end / hold_start - 1.0,
        "cumulative_return_difference_vs_hold_percentage_points": (total - (hold_end / hold_start - 1.0)) * 100.0,
        "relative_wealth_vs_hold": (end_nav / start_nav) / (hold_end / hold_start) - 1.0,
        "paired_monthly_mean_difference_vs_hold": paired_mean,
        "paired_monthly_difference_nw3_descriptive_95_low": paired_low,
        "paired_monthly_difference_nw3_descriptive_95_high": paired_high,
        "exposure_gap_open_to_next_open_decomposition": {
            "interpretation": "unexposed share times SPY open-to-next-month-open return; opportunity description, not cash/fee attribution",
            "skipped_positive_months": missed_count, "avoided_negative_months": avoided_count,
            "sum_skipped_positive_return_fraction": missed,
            "sum_avoided_negative_return_fraction": avoided,
            "largest_missed_up_month": None if largest_missed is None else {
                "month": largest_missed[0], "market_return": largest_missed[1],
                "unexposed_fraction": largest_missed[2], "missed_positive_fraction": largest_missed[3]},
            "largest_avoided_down_month": None if largest_avoided is None else {
                "month": largest_avoided[0], "market_return": largest_avoided[1],
                "unexposed_fraction": largest_avoided[2], "avoided_negative_fraction": largest_avoided[4]},
            "months_without_following_open_excluded": int(sum(x is None or pd.isna(x) for x in market_returns)),
        },
    }


def run_scenario(contract: dict[str, Any], spy: pd.DataFrame) -> dict[str, pd.DataFrame]:
    account = contract["account"]
    start = pd.Timestamp(account["start"])
    end = pd.Timestamp(account["end"])
    source = spy[(spy["date"] >= start) & (spy["date"] <= end)].copy()
    if source.empty or source["date"].iloc[0].strftime("%Y-%m") != "1994-01" or source["date"].iloc[-1].strftime("%Y-%m") != "2026-08":
        raise ValueError("SPY daily coverage does not span 1994-01 through 2026-08")
    source["month"] = source["date"].dt.strftime("%Y-%m")
    opens = source.groupby("month", sort=True).first()["open"]
    months = list(opens.index)
    expected = _month_range("1994-01", "2026-08")
    if months != expected:
        raise ValueError("daily source has missing or out-of-order holding months")
    all_monthly = spy.copy()
    all_monthly["month"] = all_monthly["date"].dt.strftime("%Y-%m")
    monthly_close = all_monthly.groupby("month", sort=True).tail(1).set_index("month")["close"]
    if not all(x in monthly_close.index for x in _month_range("1993-03", "2026-07")):
        raise ValueError("missing completed monthly closes needed for signal warmup")
    month_last_dates = {str(row.month): pd.Timestamp(row.date).strftime("%Y-%m-%d")
                        for row in all_monthly.groupby("month", sort=True).tail(1)[["month", "date"]].itertuples(index=False)}
    month_first_dates = {str(row.month): pd.Timestamp(row.date).strftime("%Y-%m-%d")
                         for row in all_monthly.groupby("month", sort=True).head(1)[["month", "date"]].itertuples(index=False)}
    signal_map, signal_rows = build_signals(monthly_close, "1993-12", "2026-07", month_last_dates, month_first_dates)
    monthly_frames = []
    daily_frames = []
    trade_frames = []
    for strategy in STRATEGIES:
        for fee_rate in FEE_RATES:
            daily_ledger, trades = simulate_account(source, signal_map, strategy, fee_rate, float(account["initial_usd"]))
            monthly = make_monthly_table(daily_ledger, source, signal_map, float(account["initial_usd"]))
            key = f"{strategy}__fee{int(round(fee_rate * 10000))}bps"
            daily_ledger["account_id"] = key
            trades["account_id"] = key
            monthly["account_id"] = key
            daily_frames.append(daily_ledger)
            trade_frames.append(trades)
            monthly_frames.append(monthly)
    daily_all = pd.concat(daily_frames, ignore_index=True)
    trades_all = pd.concat([x for x in trade_frames if not x.empty], ignore_index=True) if any(not x.empty for x in trade_frames) else pd.DataFrame()
    monthly_all = pd.concat(monthly_frames, ignore_index=True)
    market_months = source.groupby("month", sort=True).first()
    # State records identify the signal actually used for each holding month.
    signals = []
    for month in expected:
        row = signal_map[month]
        signals.append({
            "formation_month": row["formation_month"], "formation_date": row["formation_date"],
            "action_date": row["action_date"],
            "holding_month": month, "state": row["state"], "formation_close": row["formation_close"],
            "sma10": row["sma10"], "window_months_json": json.dumps(row["window_months"], separators=(",", ":")),
            "window_formation_dates_json": json.dumps(row["window_dates"], separators=(",", ":")),
            "window_closes_json": json.dumps(row["window_closes"], separators=(",", ":")),
        })
    return {
        "daily": daily_all, "trades": trades_all, "monthly": monthly_all,
        "signals": pd.DataFrame(signals), "market": source,
    }


def summarize(contract: dict[str, Any], frames: dict[str, pd.DataFrame], metadata: dict[str, Any]) -> dict[str, Any]:
    periods = {"all": ("1994-01", "2026-08", 392), **PERIODS}
    summary_rows = []
    monthly = frames["monthly"]
    daily = frames["daily"]
    trades = frames["trades"]
    for key, (first, last, expected_months) in periods.items():
        if len(_month_range(first, last)) != expected_months:
            raise AssertionError(f"bad frozen period size: {key}")
        for strategy in STRATEGIES:
            for fee_rate in FEE_RATES:
                fee_bps = fee_rate * 10000
                account_id = f"{strategy}__fee{int(round(fee_bps))}bps"
                m = monthly[monthly["account_id"] == account_id]
                d = daily[daily["account_id"] == account_id]
                t = trades[trades["account_id"] == account_id] if not trades.empty else trades
                hold_id = f"hold__fee{int(round(fee_bps))}bps"
                h = monthly[monthly["account_id"] == hold_id]
                summary_rows.append(_period_summary(d, m, t, h, key, first, last,
                                                    float(contract["account"]["initial_usd"])))
    curves = []
    for account_id, group in monthly.groupby("account_id", sort=True):
        curves.append({
            "account_id": account_id,
            "points": [[str(row.month), float(row.nav_end)] for row in group.itertuples(index=False)],
        })
    return {
        "schema_version": 1,
        "task_id": contract["output"]["task_id"],
        "run_id": contract["output"]["run_id"],
        "identity": contract["research_identity"],
        "metadata": metadata,
        "limits": [
            "Current-vintage sequential replay; not a historical data-vintage reconstruction or unseen validation.",
            "Adjusted OHLC total-return approximation; do not add dividend cash again.",
            "SPY is an ETF proxy, not the official S&P 500 index; ^GSPC is used only for same-vendor date-set checking.",
            "Fee rates are hypothetical proportional friction per side, not verified personal broker fees.",
            "Zero cash interest, no terminal liquidation, no terminal sale fee; close marked at final observed adjusted close.",
            "Historical source vintage and acquisition-time availability are unknown.",
        ],
        "periods": summary_rows,
        "month_end_nav_curves": curves,
    }


def _check_input_calendar(contract: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, str]]:
    input_cfg = contract["input"]
    spy_path = Path(input_cfg["path"])
    gspc_path = Path(input_cfg["calendar_check_path"])
    if not spy_path.is_file():
        raise FileNotFoundError(f"SPY input missing: {spy_path}")
    spy_sha = sha256_file(spy_path)
    if spy_sha.lower() != input_cfg["sha256"].lower():
        raise ValueError(f"SPY input SHA-256 mismatch: expected {input_cfg['sha256']}, got {spy_sha}")
    spy, _ = load_ohlc_parquet(spy_path, need_ohlc=True, label="SPY")
    gspc, gspc_sha = load_ohlc_parquet(gspc_path, need_ohlc=False, label="^GSPC calendar")
    spy_dates = set(spy["date"])
    first_spy_date, last_spy_date = spy["date"].min(), spy["date"].max()
    gspc_in_span = gspc[(gspc["date"] >= first_spy_date) & (gspc["date"] <= last_spy_date)]
    gspc_dates = set(gspc_in_span["date"])
    if spy_dates != gspc_dates:
        missing_from_gspc = sorted(spy_dates - gspc_dates)[:5]
        missing_from_spy = sorted(gspc_dates - spy_dates)[:5]
        raise ValueError(f"full daily calendar mismatch; SPY-only={missing_from_gspc}; ^GSPC-only={missing_from_spy}")
    spy = spy.rename(columns={"date": "date"})
    spy["date"] = pd.to_datetime(spy["date"])
    # The contract treats each row as one vendor-observed session, not an exchange-calendar assertion.
    by_month = spy.assign(month=spy["date"].dt.strftime("%Y-%m")).groupby("month").size()
    expected_all = _month_range(str(spy["date"].min().to_period("M")), str(spy["date"].max().to_period("M")))
    if list(by_month.index) != expected_all:
        raise ValueError("missing calendar month in the full observed daily series")
    return spy, {"spy_sha256": spy_sha, "gspc_calendar_sha256": gspc_sha, "calendar_dates": len(spy_dates)}


def run_real(contract_path: Path, out_dir: Path, receipt_path: Path) -> None:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    _validate_contract(contract)
    contract_sha = sha256_file(contract_path)
    runner_sha = sha256_file(Path(__file__).resolve())
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (receipt.get("authorized") is not True
            or receipt.get("contract_sha256", "").lower() != contract_sha.lower()
            or receipt.get("runner_sha256", "").lower() != runner_sha.lower()):
        raise PermissionError("execution receipt must authorize true and match current contract and runner SHA-256")
    expected_out = Path(contract["output"]["output"]).expanduser().resolve()
    out_dir = out_dir.expanduser().resolve()
    if out_dir != expected_out:
        raise ValueError(f"--out must equal the frozen result output path: {expected_out}")
    result_dir = out_dir
    if result_dir.exists():
        raise FileExistsError(f"refusing to use existing output directory: {result_dir}")
    # Resolve and qualify all inputs before creating any output directory.
    spy, input_meta = _check_input_calendar(contract)
    metadata = {
        "contract_path": str(contract_path.resolve()), "contract_sha256": contract_sha,
        "runner_path": str(Path(__file__).resolve()), "runner_sha256": runner_sha,
        "spy_path": contract["input"]["path"], "spy_sha256": input_meta["spy_sha256"],
        "calendar_check_path": contract["input"]["calendar_check_path"],
        "calendar_check_sha256": input_meta["gspc_calendar_sha256"],
        "calendar_dates_equal": True, "daily_calendar_rows": input_meta["calendar_dates"],
        "source_vintage": contract["input"]["vintage"],
    }
    frames = run_scenario(contract, spy)
    result_dir.mkdir(exist_ok=False)
    frames["daily"].to_csv(result_dir / "daily.csv", index=False, float_format="%.17g")
    frames["trades"].to_csv(result_dir / "trades.csv", index=False, float_format="%.17g")
    frames["signals"].to_csv(result_dir / "signals.csv", index=False, float_format="%.17g")
    frames["monthly"].to_csv(result_dir / "monthly.csv", index=False, float_format="%.17g")
    summaries = summarize(contract, frames, metadata)
    _json_write(result_dir / "summary.json", summaries)
    period_rows = [{k: v for k, v in x.items() if k != "exposure_gap_open_to_next_open_decomposition"} for x in summaries["periods"]]
    pd.DataFrame(period_rows).to_csv(result_dir / "periods.csv", index=False, float_format="%.17g")
    decomposition_rows = []
    for item in summaries["periods"]:
        detail = item["exposure_gap_open_to_next_open_decomposition"]
        decomposition_rows.append({
            "period": item["period"], "strategy": item["strategy"],
            "fee_bps_per_side": item["fee_bps_per_side"], **detail,
        })
    pd.DataFrame(decomposition_rows).to_csv(result_dir / "opportunity-decomposition.csv", index=False, float_format="%.17g")
    print(json.dumps({"status": "complete", "result": str(result_dir), "accounts": 9,
                      "daily_rows": int(len(frames["daily"])), "trade_rows": int(len(frames["trades"])),
                      "signal_rows": int(len(frames["signals"]))}, ensure_ascii=False))


def _synthetic_daily(prices: list[tuple[str, float, float]]) -> pd.DataFrame:
    return pd.DataFrame([{"date": pd.Timestamp(d), "open": o, "close": c} for d, o, c in prices])


def run_synthetic_checks(output_path: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        if not ok:
            raise AssertionError(f"synthetic check failed: {name}: {detail}")
        checks.append({"name": name, "status": "pass", "detail": detail})

    # Hand-calculated buy and sell post-fee target equations.
    buy = rebalance(1000.0, 0.0, 10.0, 0.5, 0.01)
    record("post_fee_half_target_buy", abs(buy.units * 10 / buy.nav_after - 0.5) < 1e-12 and abs(buy.nav_before - buy.fee - buy.nav_after) < 1e-10,
           "buy notional uses (w*N-S)/(1+w*f); post-fee invested weight is 50%")
    sell = rebalance(buy.cash, buy.units, 10.0, 0.0, 0.01)
    record("post_fee_full_exit", sell.units == 0.0 and abs(sell.nav_after - (sell.nav_before - sell.fee)) < 1e-10 and sell.cash >= 0,
           "full exit sells only existing units and deducts fee from notional")

    # Simulated account buys in month 1 and exits in month 2 after an overnight gap.
    switch_sigs = {
        "1994-01": {"state": "strong", "formation_month": "1993-12", "formation_date": "1993-12-31", "action_date": "1994-01-03"},
        "1994-02": {"state": "weak", "formation_month": "1994-01", "formation_date": "1994-01-31", "action_date": "1994-02-01"},
    }
    switch_path = _synthetic_daily([("1994-01-03", 10.0, 10.0), ("1994-01-31", 10.0, 10.0),
                                    ("1994-02-01", 12.0, 12.0), ("1994-02-28", 11.0, 11.0)])
    switch_path["month"] = switch_path["date"].dt.strftime("%Y-%m")
    switch_ledger, switch_trades = simulate_account(switch_path, switch_sigs, "sma10", 0.01, 1000.0)
    prior_units = float(switch_ledger.iloc[1]["units_after_trade"])
    feb_open_nav = prior_units * 12.0
    record("simulated_overnight_before_month2_exit", switch_trades.iloc[1]["side"] == "sell"
           and abs(float(switch_ledger.iloc[2]["nav_before_trade"]) - feb_open_nav) < 1e-10
           and abs(float(switch_trades.iloc[1]["fee"]) - feb_open_nav * 0.01) < 1e-8,
           "simulated month-1 strong to month-2 weak path marks old units at the higher month-2 open before applying the sell fee")

    # Account paths use the same continuous simulation; period boundaries do not reset positions.
    sigs, _ = build_signals(pd.Series([100.0] * 11, index=pd.period_range("1993-03", periods=11, freq="M")), "1993-12", "1994-01")
    sigs["1994-01"]["state"] = "strong"
    sigs["1994-02"]["state"] = "strong"
    path = _synthetic_daily([("1994-01-03", 10.0, 10.0), ("1994-01-31", 11.0, 11.0),
                             ("1994-02-01", 12.0, 12.0), ("1994-02-28", 13.0, 13.0)])
    path["month"] = path["date"].dt.strftime("%Y-%m")
    ledger, trades = simulate_account(path, sigs, "sma10", 0.001, 1000.0)
    record("continuous_account_boundary", len(ledger) == 4 and len(trades) == 1 and float(ledger.iloc[2]["units_after_trade"]) == float(ledger.iloc[1]["units_after_trade"]),
           "a new calendar period does not reset units or create a boundary-only trade")

    # Positive uniform scaling preserves signal and account return path.
    monthly0 = pd.Series([90, 91, 92, 93, 94, 95, 96, 97, 98, 110],
                         index=pd.period_range("1993-03", periods=10, freq="M"))
    state0, _ = build_signals(monthly0, "1993-12", "1993-12")
    state1, _ = build_signals(monthly0 * 7.0, "1993-12", "1993-12")
    record("positive_scale_signal_invariance", state0["1994-01"]["state"] == state1["1994-01"]["state"],
           "uniform positive price scaling leaves the ten-month state unchanged")

    scale_months = {"1994-01": dict(switch_sigs["1994-01"]), "1994-02": dict(switch_sigs["1994-02"])}
    scaled_path = switch_path.copy()
    scaled_path[["open", "close"]] *= 7.0
    base_ledger, _ = simulate_account(switch_path, scale_months, "sma10", 0.01, 1000.0)
    scaled_ledger, _ = simulate_account(scaled_path, scale_months, "sma10", 0.01, 7000.0)
    base_returns = base_ledger["nav_close"].to_numpy() / 1000.0
    scaled_returns = scaled_ledger["nav_close"].to_numpy() / 7000.0
    record("whole_account_uniform_scale_path", np.allclose(base_returns, scaled_returns, rtol=1e-12, atol=1e-12),
           "scaling every price and starting cash by the same positive factor preserves the full simulated NAV-return path")

    # Signals formed through a month are invariant to appended or changed future monthly observations.
    future_a = pd.concat([monthly0, pd.Series([111.0, 112.0], index=pd.period_range("1994-01", periods=2, freq="M"))])
    future_b = pd.concat([monthly0, pd.Series([1.0, 10000.0], index=pd.period_range("1994-01", periods=2, freq="M"))])
    sig_a, _ = build_signals(future_a, "1993-12", "1993-12")
    sig_b, _ = build_signals(future_b, "1993-12", "1993-12")
    record("past_state_future_row_invariance", sig_a["1994-01"]["state"] == sig_b["1994-01"]["state"],
           "altering post-formation prices cannot change an already formed signal")

    # Terminal close is a mark only; no forced liquidation is implemented.
    final = ledger.iloc[-1]
    record("terminal_mark_without_sale", len(trades) == 1 and final["units_after_trade"] > 0 and final["nav_close"] == final["cash_close"] + final["position_value_close"],
           "last observed close marks the remaining units; no terminal sale or fee")

    payload = {
        "schema_version": 1,
        "kind": "synthetic_engine_checks_only",
        "status": "pass",
        "real_market_data_read": False,
        "real_market_statistics_run": False,
        "checks": checks,
        "limitation": "These deterministic cases test implementation arithmetic and information timing only; they are not historical SPY validation.",
    }
    _json_write(output_path, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--synthetic-only", action="store_true")
    parser.add_argument("--execution-receipt", type=Path)
    args = parser.parse_args(argv)
    if args.synthetic_only:
        destination = (args.out / "synthetic-checks-v2.json") if args.out else Path(__file__).with_name("synthetic-checks-v2.json")
        payload = run_synthetic_checks(destination)
        print(json.dumps({"status": payload["status"], "checks": len(payload["checks"]), "output": str(destination)}, ensure_ascii=False))
        return 0
    if args.out is None or args.execution_receipt is None:
        parser.error("--out and --execution-receipt are required unless --synthetic-only is used")
    try:
        run_real(args.contract, args.out, args.execution_receipt)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
