"""Run the frozen breadth-source and confirmation accounts. Research only."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path

import numpy as np
import pandas as pd

from research_engine import target_action

sys.dont_write_bytecode = True
D = Decimal
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PREP = HERE / "prepared"
OUT = HERE / "results"
OLD = ROOT / "docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12"
START = "2018-07-05"  # first qualified All-A date; all comparisons use this common start
END = "2026-06-30"
INITIAL = D("1000000")


def save_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def load_json(path: Path):
    return json.loads(path.read_text())


def load_bars(symbol: str) -> pd.DataFrame:
    prefix = "sh" if symbol.startswith("5") else "sz"
    p = OLD / "inputs/bars" / f"{prefix}{symbol}-nominal.csv"
    df = pd.read_csv(p, dtype=str)
    df["date"] = pd.to_datetime(df["date"])
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c])
    return df.sort_values("date").set_index("date")


def continuous_close(bars: pd.DataFrame, actions: list[dict], internal_symbol: str) -> pd.Series:
    """Point-in-time continuous price, chaining only actions effective by each date."""
    cash = {pd.Timestamp(a["effective_date"]): float(a["cash"]) for a in actions if a["symbol"] == internal_symbol and a["type"] == "cash_dividend"}
    ratio = {pd.Timestamp(a["effective_date"]): float(a["ratio"]) for a in actions if a["symbol"] == internal_symbol and a["type"] == "split"}
    out, level, prev = {}, None, None
    for day, row in bars.iterrows():
        close = float(row.close)
        if level is None:
            level = close
        else:
            ref = prev
            if day in cash:
                ref -= cash[day]
            if day in ratio:
                ref /= ratio[day]
            if ref > 0:
                level *= close / ref
        out[day] = level
        prev = close
    return pd.Series(out, dtype=float)


def weekly_events(width: pd.DataFrame, trading_dates: pd.DatetimeIndex, start: str, end: str):
    work = width.reindex(trading_dates)
    iso = work.index.isocalendar()
    rows = []
    for _, g in work.groupby([iso.year, iso.week]):
        g = g.loc[(g.index >= pd.Timestamp(start)) & (g.index <= pd.Timestamp(end))]
        if g.empty:
            continue
        next_monday = g.index.max() + pd.Timedelta(days=7 - g.index.max().weekday())
        if next_monday > pd.Timestamp(end):
            continue  # the research end cut through an unfinished natural week
        valid = g[g.valid.fillna(False)]
        signal_day = g.index.max()
        if valid.empty:
            rows.append({"signal_date": signal_day, "valid": False})
        else:
            last = valid.iloc[-1]
            b = float(last.b200)
            target = 1.0 if b < 43.3 else (0.5 if b < 56.7 else 0.0)
            rows.append({"signal_date": signal_day, "width_date": valid.index[-1], "valid": True, "b200": b, "target": target})
    return {r["signal_date"]: r for r in rows}


def floor_lot(value: D, lot=D("100")) -> D:
    return (value / lot).to_integral_value(rounding=ROUND_FLOOR) * lot


def execute_target(cash: D, receivable: D, units: D, price: D, target: D, fee: D, band: bool):
    equity = cash + receivable + units * price
    weight = units * price / equity if equity else D("0")
    if band and abs(target - weight) < D("0.05"):
        return cash, units, None, "inside_5pp_band", float(weight)
    desired = equity * target
    current = units * price
    if desired > current:
        wanted = floor_lot((desired - current) / price)
        affordable = floor_lot(cash / (price * (D("1") + fee)))
        qty = min(wanted, affordable)
        if qty <= 0:
            return cash, units, None, "buy_rounds_to_zero_or_cash_short", float(weight)
        notional, cost = qty * price, qty * price * fee
        return cash - notional - cost, units + qty, ("buy", qty, notional, cost), None, float(weight)
    qty = units if target == 0 else min(units, floor_lot((current - desired) / price))
    if qty <= 0:
        return cash, units, None, "sell_rounds_to_zero", float(weight)
    notional, cost = qty * price, qty * price * fee
    return cash + notional - cost, units - qty, ("sell", qty, notional, cost), None, float(weight)


def block_reason(symbol: str, day: pd.Timestamp, side: str, bar, prev_close: D | None, actions, restrictions, regimes):
    internal = ("sh" if symbol.startswith("5") else "sz") + symbol
    for r in restrictions:
        if r["symbol"] == internal and pd.Timestamp(r["date"]) == day and not r[f"open_{side}_allowed"]:
            return r["reason"]
    if bar is None or pd.isna(bar.open):
        return "missing_open"
    if prev_close is None:
        return None
    ref = prev_close
    for a in actions:
        if a["symbol"] == internal and pd.Timestamp(a["effective_date"]) == day:
            if a["type"] == "cash_dividend":
                ref -= D(a["cash"])
            elif a["type"] == "split":
                ref /= D(a["ratio"])
    limit = next((D(r["price_limit_fraction"]) for r in regimes if r["symbol"] == internal and r["start"] <= str(day.date()) <= r["end"]), D("0.10"))
    if abs(D(str(bar.open)) - ref) >= ref * limit - D("0.00051"):
        return "at_open_limit_conservative"
    return None


def confirmation_series(variant: str, width: pd.DataFrame | None, cont: pd.Series):
    if variant == "W0":
        return pd.Series(True, index=cont.index)
    if variant == "W1":
        s = width.b50.reindex(cont.index)
        return (s - s.shift(20)) > 0
    if variant == "W2":
        s = width.b200.reindex(cont.index)
        return (s - s.shift(20)) > 0
    if variant == "W3":
        return cont > cont.rolling(50, min_periods=50).mean()
    raise ValueError(variant)


def drawdown_intervals(daily: pd.DataFrame):
    peak = float(INITIAL)
    peak_date = pd.Timestamp(START) - pd.Timedelta(days=1)
    active = None
    out = []
    for row in daily.itertuples():
        eq = row.equity
        if eq >= peak:
            if active:
                active["recovery_date"] = str(row.date.date())
                active["recovery_days"] = int((row.date - pd.Timestamp(active["start_date"])).days)
                out.append(active)
                active = None
            peak, peak_date = eq, row.date
        else:
            dd = eq / peak - 1
            if active is None:
                active = {"start_date": str(peak_date.date()), "peak_equity": peak, "valley_date": str(row.date.date()), "valley_equity": eq, "max_drawdown": dd, "recovery_date": None, "recovery_days": None}
            elif dd < active["max_drawdown"]:
                active.update(valley_date=str(row.date.date()), valley_equity=eq, max_drawdown=dd)
    if active:
        active["unrecovered_days_to_end"] = int((daily.date.iloc[-1] - pd.Timestamp(active["start_date"])).days)
        out.append(active)
    return out


def simulate(symbol: str, method: str, fee_rate: float, width: pd.DataFrame | None = None):
    internal = ("sh" if symbol.startswith("5") else "sz") + symbol
    bars_all = load_bars(symbol)
    bars = bars_all.loc[(bars_all.index >= START) & (bars_all.index <= END)]
    actions = load_json(OLD / "inputs/actions.json")
    restrictions = load_json(OLD / "inputs/dated-restrictions.json")
    regimes = load_json(OLD / "inputs/price-limit-regimes.json")
    cont_all = continuous_close(bars_all, actions, internal)
    cont = cont_all.reindex(bars.index)
    variant = method if method.startswith("W") else None
    confirm = confirmation_series(variant, width, cont_all).reindex(bars.index) if variant else None
    w_events = weekly_events(width, bars.index, START, END) if variant else {}
    b1 = (cont_all > cont_all.rolling(200, min_periods=200).mean()).astype(float).reindex(bars.index)
    month_ends = set(pd.Series(bars.index, index=bars.index).groupby(bars.index.to_period("M")).max())
    cash, recv, units = INITIAL, D("0"), D("0")
    fee = D(str(fee_rate))
    rights, dues = {}, {}
    order = None
    waiting = None
    raw_target = None
    b1_state = None
    trades, rejects, signals, daily, wait_events = [], [], [], [], []
    last_mark = None
    prev_close = None
    dividends = D("0")
    start_d, end_d = pd.Timestamp(START), pd.Timestamp(END)
    bar_map = {d: r for d, r in bars.iterrows()}
    days = pd.date_range(start_d, end_d, freq="D")
    first_bar = bars.index.min()
    for day in days:
        bar = bar_map.get(day)
        # Corporate actions are booked before the open; rights were fixed at record close.
        for a in actions:
            if a["symbol"] != internal:
                continue
            if pd.Timestamp(a["effective_date"]) == day:
                if a["type"] == "cash_dividend":
                    amount = rights.get(a["event_id"], D("0")) * D(a["cash"])
                    dues[a["event_id"]] = amount
                    recv += amount
                elif a["type"] == "split":
                    units *= D(a["ratio"])
            if a["type"] == "cash_dividend" and a.get("pay_date") and pd.Timestamp(a["pay_date"]) == day:
                amount = dues.pop(a["event_id"], D("0"))
                recv -= amount
                cash += amount
                dividends += amount
                if method == "B0" and amount > 0:
                    order = {"kind": "reinvest", "signal_date": day, "target": None}
        if method == "B0" and day == first_bar:
            order = {"kind": "target", "signal_date": day - pd.Timedelta(days=1), "target": 1.0, "band": False}

        # Execute only orders created by an earlier close, except B0's fixed first-open/reinvestment rule.
        if bar is not None and order is not None and (method == "B0" or order["signal_date"] < day):
            price = D(str(bar.open))
            if order["kind"] == "reinvest":
                qty = floor_lot(cash / (price * (D("1") + fee)))
                side = "buy"
                block = block_reason(symbol, day, side, bar, prev_close, actions, restrictions, regimes)
                if block:
                    rejects.append({"date": day, "reason": block, "kind": "reinvest"})
                elif qty > 0:
                    notional, cost = qty * price, qty * price * fee
                    cash -= notional + cost
                    units += qty
                    trades.append({"date": day, "side": "buy", "qty": float(qty), "price": float(price), "notional": float(notional), "fee": float(cost), "reason": "dividend_reinvestment"})
                    order = None
                else:
                    rejects.append({"date": day, "reason": "below_one_lot", "kind": "reinvest"})
                    order = None
            else:
                target = D(str(order["target"]))
                equity_open = cash + recv + units * price
                actual = units * price / equity_open if equity_open else D("0")
                action = target_action(float(actual), float(target), 0.05 if variant else 0.0)
                if action == "none":
                    rejects.append({"date": day, "reason": "inside_5pp_band", "target": float(target), "before_weight": float(actual)})
                    if waiting:
                        waiting.update(status="cancelled_inside_5pp_band", resolution_date=day)
                        waiting = None
                    order = None
                    is_buy = False
                    continue_execution = False
                else:
                    is_buy = action == "buy"
                    continue_execution = True
                if continue_execution and variant and is_buy and not order.get("confirmed", variant == "W0"):
                    if waiting is None:
                        waiting = {"start_date": order["signal_date"], "first_open": day, "first_open_price": float(price), "target": float(target), "source": method}
                        wait_events.append(waiting)
                    order = None
                elif continue_execution:
                    side = "buy" if is_buy else "sell"
                    block = block_reason(symbol, day, side, bar, prev_close, actions, restrictions, regimes)
                    if block:
                        rejects.append({"date": day, "reason": block, "target": float(target)})
                    else:
                        cash2, units2, trade, reason, before_weight = execute_target(cash, recv, units, price, target, fee, bool(order.get("band")))
                        if trade:
                            cash, units = cash2, units2
                            side, qty, notional, cost = trade
                            trades.append({"date": day, "side": side, "qty": float(qty), "price": float(price), "notional": float(notional), "fee": float(cost), "reason": order.get("reason", method), "target": float(target), "before_weight": before_weight})
                            if waiting:
                                waiting.update(status="delayed_bought", resolution_date=day, execution_price=float(price))
                                waiting = None
                        else:
                            rejects.append({"date": day, "reason": reason, "target": float(target), "before_weight": before_weight})
                            if waiting:
                                waiting.update(status="no_trade_inside_or_rounding", resolution_date=day)
                                waiting = None
                        order = None

        if bar is not None:
            last_mark = D(str(bar.close))
            prev_close = last_mark
            # End-of-day rights.
            for a in actions:
                if a["symbol"] == internal and a.get("record_date") and pd.Timestamp(a["record_date"]) == day:
                    rights[a["event_id"]] = units

            if variant:
                ev = w_events.get(day)
                if ev is not None:
                    if not ev["valid"]:
                        if waiting:
                            waiting.update(status="cancelled_invalid_width_week", resolution_date=day)
                            waiting = None
                        order = None
                        raw_target = None
                        signals.append({"date": day, "kind": "invalid_width_week"})
                    else:
                        new_target = float(ev["target"])
                        if waiting and new_target <= float(units * last_mark / (cash + recv + units * last_mark)):
                            waiting.update(status="cancelled_raw_target_changed", resolution_date=day)
                            waiting = None
                        raw_target = new_target
                        is_confirmed = bool(confirm.loc[day]) if day in confirm.index and pd.notna(confirm.loc[day]) else False
                        order = {"kind": "target", "signal_date": day, "target": raw_target, "band": True, "confirmed": is_confirmed, "reason": "weekly_b200_target"}
                        signals.append({"date": day, "kind": "weekly_target", "target": raw_target, "confirmed": is_confirmed, "b200": ev["b200"]})
                if waiting and raw_target is not None:
                    current_weight = float(units * last_mark / (cash + recv + units * last_mark))
                    if target_action(current_weight, raw_target, 0.05) != "buy":
                        waiting.update(status="cancelled_reason_no_longer_valid", resolution_date=day)
                        waiting = None
                    elif bool(confirm.loc[day]) if day in confirm.index and pd.notna(confirm.loc[day]) else False:
                        order = {"kind": "target", "signal_date": day, "target": raw_target, "band": True, "confirmed": True, "reason": "confirmed_waiting_buy"}
                        waiting["confirmation_date"] = day
            elif method == "B1":
                target = float(b1.loc[day])
                if b1_state is None or target != b1_state:
                    b1_state = target
                    order = {"kind": "target", "signal_date": day, "target": target, "band": False, "reason": "price_sma200_state"}
                    signals.append({"date": day, "kind": "price_sma200_state", "target": target})
            elif method == "B2" and day in month_ends:
                order = {"kind": "target", "signal_date": day, "target": 0.5, "band": False, "reason": "month_end_50pct"}
                signals.append({"date": day, "kind": "month_end_50pct", "target": 0.5})

        equity = cash + recv + units * (last_mark or D("0"))
        weight = units * (last_mark or D("0")) / equity if equity else D("0")
        daily.append({"date": day, "cash": float(cash), "receivable": float(recv), "units": float(units), "mark": float(last_mark or 0), "equity": float(equity), "weight": float(weight), "is_quote_day": bar is not None, "dividends_received": float(dividends)})
    if waiting:
        waiting.update(status="unresolved_at_end", resolution_date=pd.Timestamp(END))

    daily_df = pd.DataFrame(daily)
    trade_df = pd.DataFrame(trades)
    dd = drawdown_intervals(daily_df)
    end_equity = float(daily_df.equity.iloc[-1])
    years = (pd.Timestamp(END) - pd.Timestamp(START)).days / 365.25
    quote_rows = daily_df[daily_df.is_quote_day]
    summary = {
        "symbol": symbol, "method": method, "fee_rate": fee_rate, "start": START, "end": END,
        "end_equity": end_equity, "cagr": (end_equity / float(INITIAL)) ** (1 / years) - 1,
        "max_drawdown": min([0.0] + [x["max_drawdown"] for x in dd]),
        "longest_recovery_days": max([0] + [x.get("recovery_days") or x.get("unrecovered_days_to_end", 0) for x in dd]),
        "longest_recovery_unrecovered": any(x.get("recovery_date") is None and (x.get("unrecovered_days_to_end", 0) == max([0] + [y.get("recovery_days") or y.get("unrecovered_days_to_end", 0) for y in dd])) for x in dd),
        "average_weight": float(quote_rows.weight.mean()),
        "turnover_initial_multiple": float(trade_df.notional.sum() / float(INITIAL)) if not trade_df.empty else 0.0,
        "fees": float(trade_df.fee.sum()) if not trade_df.empty else 0.0,
        "trades": len(trade_df), "buys": int((trade_df.side == "buy").sum()) if not trade_df.empty else 0,
        "sells": int((trade_df.side == "sell").sum()) if not trade_df.empty else 0,
        "final_cash": float(cash), "final_receivable": float(recv), "final_units": float(units),
        "pending_at_end": order is not None,
        "pending_kind_at_end": order.get("kind") if order else None,
        "pending_signal_date_at_end": str(order.get("signal_date").date()) if order and hasattr(order.get("signal_date"), "date") else None,
    }
    # Add wait price diagnostics after the account path is finished.
    for w in wait_events:
        end = pd.Timestamp(w.get("resolution_date", END))
        span = bars.loc[(bars.index >= pd.Timestamp(w["first_open"])) & (bars.index <= end), "close"]
        base = w["first_open_price"]
        w["wait_trading_days"] = max(0, len(span) - 1)
        w["worst_price_change"] = float(span.min() / base - 1) if len(span) else None
        w["best_price_change"] = float(span.max() / base - 1) if len(span) else None
    return summary, daily_df, trade_df, pd.DataFrame(signals), pd.DataFrame(rejects), pd.DataFrame(wait_events), dd


def annual_rows(daily: pd.DataFrame, account_id: str):
    rows, prior = [], float(INITIAL)
    for year, g in daily.groupby(daily.date.dt.year):
        end = float(g.equity.iloc[-1])
        rows.append({"account_id": account_id, "year": int(year), "label": "上半年" if year == 2026 else "全年", "start_equity": prior, "end_equity": end, "return": end / prior - 1})
        prior = end
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    quality = load_json(PREP / "data_quality.json")
    widths = {
        "all_a": pd.read_parquet(PREP / "breadth_all_a.parquet"),
        "csi300": pd.read_parquet(PREP / "breadth_csi300.parquet"),
    }
    account_specs = []
    for symbol in ["510300", "159915"]:
        sources = ["all_a"] + (["csi300"] if symbol == "510300" else [])
        for source in sources:
            for variant in ["W0", "W1", "W2", "W3"]:
                account_specs.append((symbol, source, variant))
        for baseline in ["B0", "B1", "B2"]:
            account_specs.append((symbol, "baseline", baseline))
    all_summaries, all_annual = [], []
    for fee in [0.001, 0.002]:
        fee_dir = OUT / ("fee-10bp" if fee == 0.001 else "fee-20bp")
        fee_dir.mkdir(exist_ok=True)
        for symbol, source, method in account_specs:
            account_id = f"{symbol}-{source}-{method}-{int(fee*10000)}bp"
            width = widths.get(source)
            summary, daily, trades, signals, rejects, waits, dd = simulate(symbol, method, fee, width)
            summary.update(account_id=account_id, width_source=source, data_grade=(quality.get(source, {}).get("grade") if source != "baseline" else "reference"))
            all_summaries.append(summary)
            all_annual.extend(annual_rows(daily, account_id))
            daily.to_parquet(fee_dir / f"{account_id}-daily.parquet", index=False)
            trades.to_csv(fee_dir / f"{account_id}-trades.csv", index=False)
            signals.to_csv(fee_dir / f"{account_id}-signals.csv", index=False)
            rejects.to_csv(fee_dir / f"{account_id}-rejected.csv", index=False)
            waits.to_csv(fee_dir / f"{account_id}-waits.csv", index=False)
            save_json(fee_dir / f"{account_id}-drawdowns.json", dd)
            print(account_id, f"{summary['end_equity']:.2f}", flush=True)
    pd.DataFrame(all_summaries).to_csv(OUT / "summary.csv", index=False)
    pd.DataFrame(all_annual).to_csv(OUT / "annual.csv", index=False)
    # Fixed period returns from account daily ledgers.
    periods = [("2018-07-05—2019", "2018-07-05", "2019-12-31"), ("2020—2024", "2020-01-01", "2024-12-31"), ("2025—2026H1", "2025-01-01", END)]
    period_rows = []
    for s in all_summaries:
        p = OUT / ("fee-10bp" if s["fee_rate"] == 0.001 else "fee-20bp") / f"{s['account_id']}-daily.parquet"
        d = pd.read_parquet(p)
        for label, a, b in periods:
            g = d[(d.date >= pd.Timestamp(a)) & (d.date <= pd.Timestamp(b))]
            before = d[d.date < pd.Timestamp(a)]
            start_eq = float(before.equity.iloc[-1]) if len(before) else float(INITIAL)
            period_rows.append({"account_id": s["account_id"], "period": label, "start_equity": start_eq, "end_equity": float(g.equity.iloc[-1]), "return": float(g.equity.iloc[-1] / start_eq - 1)})
    pd.DataFrame(period_rows).to_csv(OUT / "periods.csv", index=False)
    save_json(OUT / "matrix_status.json", {
        "planned_main_paths": 22, "completed_main_paths_10bp": len(account_specs),
        "completed_stress_paths_20bp": len(account_specs),
        "paused": ["159915-own-index-W0/W1/W2/W3"],
        "common_start": START, "common_end": END,
        "reason": quality["chinext"]["reason"],
    })


if __name__ == "__main__":
    main()
