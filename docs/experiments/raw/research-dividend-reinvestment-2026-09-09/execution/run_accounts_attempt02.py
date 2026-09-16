"""Prepare and run the frozen first 12 broad-ETF cash accounts. Local research only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path

sys.dont_write_bytecode = True
D = Decimal
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
INPUTS = HERE / "inputs"
OUT = HERE / "attempt-02"
OLD = ROOT / "docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12"


def load_json(path: Path):
    return json.loads(path.read_text())


def save_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("first12_price_basis", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_bars(path: Path):
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [dict(r, **{k: D(r[k]) for k in ("open", "high", "low", "close", "volume")}) for r in rows]


def week_key(day: str):
    iso = date.fromisoformat(day).isocalendar()
    return iso.year, iso.week


def next_monday(day: str) -> str:
    d = date.fromisoformat(day)
    return (d + timedelta(days=7 - d.weekday())).isoformat()


def breadth_target(value) -> D:
    value = D(str(value))
    if value < D("43.3"):
        return D("1")
    if value < D("56.7"):
        return D("0.5")
    return D("0")


def build_weekly_breadth(rows, start: str, end: str):
    valid = [r for r in rows if r.get("ma200_pct") is not None and r["date"] <= end]
    by_week = {}
    for row in valid:
        by_week[week_key(row["date"])] = row
    signals = []
    for row in sorted(by_week.values(), key=lambda x: x["date"]):
        eligible = next_monday(row["date"])
        if eligible >= start and row["date"] <= end:
            signals.append({"signal_date": row["date"], "eligible_date": eligible,
                            "source_week": list(week_key(row["date"])), "breadth": row["ma200_pct"],
                            "target": str(breadth_target(row["ma200_pct"])), "reason": "weekly_breadth_target"})
    return signals


def build_breakout_signals(symbol, bars, actions, helper, settings, start, end, lookback=60):
    forbidden_marks = {r["date"] for r in load_json(INPUTS / "dated-restrictions.json")
                       if r["symbol"] == symbol and not r["close_mark_allowed"]}
    bars = [b for b in bars if b["date"] not in forbidden_marks]
    basis = helper.PriceBasis({symbol: bars}, actions)
    state = D("0")
    signals = []
    for i, bar in enumerate(bars):
        day = bar["date"]
        if i < lookback or day < start or day > end:
            continue
        history = bars[i-lookback:i]
        adjusted = [basis.mapping(symbol, x["date"], day, "cash_proportional_v1", "close").forward(x["close"])
                    for x in history]
        current = bar["close"]
        target = state
        reason = None
        if state == 0 and current > max(adjusted):
            target, reason = D("1"), "close_above_prior_60_high"
        elif state == 1 and current < min(adjusted):
            target, reason = D("0"), "close_below_prior_60_low"
        if reason:
            signals.append({"symbol": symbol, "signal_date": day,
                            "eligible_date": (date.fromisoformat(day) + timedelta(days=1)).isoformat(),
                            "target": str(target), "reason": reason,
                            "current_close": str(current), "prior_60_min": str(min(adjusted)),
                            "prior_60_max": str(max(adjusted)), "point_in_time_adjustment": True})
            state = target
    return signals


def previous_reference(day, bars):
    prior = [b for b in bars if b["date"] < day]
    return prior[-1]["close"] if prior else None


def effective_reference(reference: D, actions, symbol, day):
    for action in sorted((a for a in actions if a["symbol"] == symbol and a["effective_date"] == day), key=lambda x: x["event_id"]):
        if action["type"] == "cash_dividend":
            reference -= D(action["cash"])
        elif action["type"] == "split":
            reference /= D(action["ratio"])
    return reference


def unavailable(symbol, day, bar, reference, settings):
    if day in settings["blocked_dates"].get(symbol, []):
        return "known_open_unavailable"
    if bar is None:
        return "missing_quote"
    if reference is None:
        return None
    limit = D(str(settings["limits"][symbol]))
    for effective, value in settings["limit_changes"].get(symbol, []):
        if effective <= day:
            limit = D(str(value))
    boundary = reference * limit - D("0.00051")
    return "at_open_limit_conservative" if abs(bar["open"] - reference) >= boundary else None


def floor_lot(units: D, lot=D("100")) -> D:
    return (units / lot).to_integral_value(rounding=ROUND_FLOOR) * lot


def execute_target(cash, receivable, units, price, target, fee, apply_band=False, lot=D("100")):
    equity_open = cash + receivable + units * price
    actual = units * price / equity_open if equity_open else D("0")
    if apply_band and abs(target - actual) < D("0.05"):
        return cash, units, None, "inside_5pp_band", equity_open, actual
    desired_value = equity_open * target
    if desired_value > units * price:
        wanted = floor_lot((desired_value - units * price) / price, lot)
        affordable = floor_lot(cash / (price * (D("1") + fee)), lot)
        qty = min(wanted, affordable)
        if qty <= 0:
            return cash, units, None, "buy_rounds_to_zero_or_cash_short", equity_open, actual
        notional = qty * price
        cost = notional * fee
        return cash - notional - cost, units + qty, ("buy", qty, notional, cost), None, equity_open, actual
    qty = units if target == 0 else min(units, floor_lot((units * price - desired_value) / price, lot))
    if qty <= 0:
        return cash, units, None, "sell_rounds_to_zero", equity_open, actual
    notional = qty * price
    cost = notional * fee
    return cash + notional - cost, units - qty, ("sell", qty, notional, cost), None, equity_open, actual


def drawdown_intervals(daily, initial_equity=100000.0):
    daily = [{"date": "2014-12-31", "equity": initial_equity}] + daily
    intervals, peak_i, valley_i, active = [], 0, 0, None
    peak = daily[0]["equity"]
    for i, row in enumerate(daily):
        equity = row["equity"]
        if equity >= peak:
            if active is not None:
                active["recovery_date"] = row["date"]
                active["recovery_days"] = (date.fromisoformat(row["date"]) - date.fromisoformat(active["start_date"])).days
                intervals.append(active); active = None
            peak, peak_i, valley_i = equity, i, i
        else:
            dd = equity / peak - 1
            if active is None:
                active = {"start_date": daily[peak_i]["date"], "peak_equity": peak,
                          "valley_date": row["date"], "valley_equity": equity, "max_drawdown": dd,
                          "recovery_date": None, "recovery_days": None}
            elif dd < active["max_drawdown"]:
                active.update(valley_date=row["date"], valley_equity=equity, max_drawdown=dd)
                valley_i = i
    if active is not None:
        intervals.append(active)
    return intervals


def period_rows(daily, trades, period, initial_equity=100000.0):
    groups = defaultdict(list)
    for row in daily:
        key = row["date"][:7] if period == "month" else row["date"][:4]
        groups[key].append(row)
    result = []
    prior_end = initial_equity
    prior_dividends = 0.0
    for key, rows in sorted(groups.items()):
        start, end = rows[0], rows[-1]
        high = prior_end
        worst = 0.0
        for r in rows:
            high = max(high, r["equity"]); worst = min(worst, r["equity"] / high - 1)
        ts = [t for t in trades if t["date"].startswith(key)]
        result.append({"period": key, "start_equity": prior_end, "end_equity": end["equity"],
                       "change": end["equity"] - prior_end,
                       "return": end["equity"] / prior_end - 1 if prior_end else None,
                       "max_drawdown": worst, "buys": sum(t["side"] == "buy" for t in ts),
                       "sells": sum(t["side"] == "sell" for t in ts),
                       "fees": sum(t["fee"] for t in ts),
                       "dividends_received": end["dividends_received"] - prior_dividends,
                       "cash_only_days": sum(r["units"] == 0 for r in rows)})
        prior_end = end["equity"]
        prior_dividends = end["dividends_received"]
    return result


def simulate(account_id, symbol, method, fee, bars, actions, settings, method_signals, start, end):
    bar_map = {b["date"]: b for b in bars}
    run_bars = [b for b in bars if start <= b["date"] <= end]
    action_days = {a["effective_date"] for a in actions if a["symbol"] == symbol} | {a.get("pay_date") for a in actions if a["symbol"] == symbol}
    cursor, finish = date.fromisoformat(start), date.fromisoformat(end)
    days = []
    while cursor <= finish:
        days.append(cursor.isoformat()); cursor += timedelta(days=1)
    cash, receivable, units = D("100000"), D("0"), D("0")
    rights, dues = {}, {}
    pending = None
    signals_out, rejected, trades, daily = [], [], [], []
    signal_by_day = defaultdict(list)
    if method in ("hold", "hold_dividend_reinvest"):
        method_signals = []
    for s in method_signals:
        signal_by_day[s["eligible_date"]].append(s)
    if method in ("hold", "hold_dividend_reinvest"):
        first = min(b["date"] for b in run_bars)
        signal_by_day[first].append({"symbol": symbol, "signal_date": start, "eligible_date": first,
                                     "target": "1", "reason": "initial_hold_allocation"})
    reference = previous_reference(start, bars)
    last_mark = reference
    cumulative_fees = D("0"); dividends_received = D("0")
    no_close_mark = {r["date"] for r in load_json(INPUTS / "dated-restrictions.json")
                     if r["symbol"] == symbol and not r["close_mark_allowed"]}
    for day in days:
        bar = bar_map.get(day)
        for action in sorted((a for a in actions if a["symbol"] == symbol and a["effective_date"] == day), key=lambda x: x["event_id"]):
            if action["type"] == "cash_dividend":
                amount = rights.get(action["event_id"], D("0")) * D(action["cash"])
                dues[action["event_id"]] = amount; receivable += amount
            elif action["type"] == "split":
                units *= D(action["ratio"])
        paid_sources = []
        for action in (a for a in actions if a["symbol"] == symbol and a["type"] == "cash_dividend" and a.get("pay_date") == day):
            amount = dues.pop(action["event_id"], D("0")); receivable -= amount; cash += amount; dividends_received += amount
            if amount > 0:
                paid_sources.append({"event_id": action["event_id"], "pay_date": day, "amount": str(amount)})
        if method == "hold_dividend_reinvest" and paid_sources:
            if pending is None:
                pending = {"symbol": symbol, "signal_date": day, "eligible_date": day,
                           "target": "reinvest_cash", "reason": "dividend_reinvestment",
                           "payment_sources": paid_sources}
            elif pending.get("reason") == "dividend_reinvestment":
                pending["payment_sources"].extend(paid_sources)
            else:
                pending.setdefault("payment_sources", []).extend(paid_sources)
        incoming = signal_by_day.get(day, [])
        if method == "breadth_three_tier" and pending is not None and week_key(day) != tuple(pending["execution_week"]):
            rejected.append({"account_id": account_id, "date": day, "signal_date": pending["signal_date"],
                             "reason": "stale_weekly_order_cancelled"}); pending = None
        for signal in incoming:
            if method == "breadth_three_tier":
                if pending is not None:
                    rejected.append({"account_id": account_id, "date": day, "signal_date": pending["signal_date"],
                                     "reason": "replaced_by_latest_completed_week"})
                pending = dict(signal, execution_week=list(week_key(day)))
            else:
                if pending is not None:
                    rejected.append({"account_id": account_id, "date": day, "signal_date": pending["signal_date"],
                                     "reason": "replaced_by_new_state_signal"})
                pending = dict(signal)
        if pending is not None and bar is None:
            rejected.append({"account_id": account_id, "date": day, "signal_date": pending["signal_date"], "reason": "missing_quote"})
        if pending is not None and bar is not None:
            ref_open = effective_reference(reference, actions, symbol, day) if reference is not None else None
            block = unavailable(symbol, day, bar, ref_open, settings)
            if block:
                rejected.append({"account_id": account_id, "date": day, "signal_date": pending["signal_date"], "reason": block})
            else:
                if pending["reason"] == "dividend_reinvestment":
                    qty = floor_lot(cash / (bar["open"] * (D("1") + fee)))
                    equity_open = cash + receivable + units * bar["open"]
                    actual = units * bar["open"] / equity_open if equity_open else D("0")
                    if qty <= 0:
                        cash2, units2, trade, reason = cash, units, None, "reinvestment_below_one_lot"
                    else:
                        notional = qty * bar["open"]
                        cost = notional * fee
                        cash2, units2 = cash - notional - cost, units + qty
                        trade, reason = ("buy", qty, notional, cost), None
                else:
                    cash2, units2, trade, reason, equity_open, actual = execute_target(
                        cash, receivable, units, bar["open"], D(pending["target"]), fee,
                        apply_band=(method == "breadth_three_tier"))
                if reason:
                    rejected.append({"account_id": account_id, "date": day, "signal_date": pending["signal_date"],
                                     "reason": reason, "actual_open_weight": float(actual),
                                     "target": pending["target"],
                                     "payment_sources": pending.get("payment_sources", [])})
                    pending = None
                elif trade:
                    side, qty, notional, cost = trade
                    cash, units = cash2, units2; cumulative_fees += cost
                    trade_row = {"account_id": account_id, "date": day, "signal_date": pending["signal_date"],
                                 "side": side, "shares": float(qty), "price": float(bar["open"]),
                                 "notional": float(notional), "fee": float(cost), "reason": pending["reason"],
                                 "target": pending["target"] if pending["target"] == "reinvest_cash" else float(D(pending["target"])),
                                 "equity_open_before_fee": float(equity_open),
                                 "actual_open_weight_before": float(actual), "cash_after": float(cash), "units_after": float(units)}
                    if pending.get("payment_sources"):
                        trade_row["payment_sources"] = pending["payment_sources"]
                    trades.append(trade_row)
                    pending = None
        assert cash >= 0 and receivable >= 0 and units >= 0, (account_id, day, cash, receivable, units)
        if bar is not None and day not in no_close_mark:
            last_mark = bar["close"]; reference = bar["close"]
        for action in (a for a in actions if a["symbol"] == symbol and a["type"] == "cash_dividend" and a.get("record_date") == day):
            rights[action["event_id"]] = units
        if last_mark is None:
            continue
        mark_date = max(b["date"] for b in bars if b["date"] <= day and b["date"] not in no_close_mark)
        equity = cash + receivable + units * last_mark
        daily.append({"account_id": account_id, "date": day, "cash": float(cash), "receivable": float(receivable),
                      "units": float(units), "mark": float(last_mark), "market_value": float(units * last_mark),
                      "equity": float(equity), "invested_weight": float(units * last_mark / equity) if equity else 0,
                      "fees": float(cumulative_fees), "dividends_received": float(dividends_received),
                      "mark_age_days": (date.fromisoformat(day)-date.fromisoformat(mark_date)).days})
    signals_out = [dict(s, account_id=account_id) for s in method_signals]
    if method in ("hold", "hold_dividend_reinvest"):
        signals_out = [{"symbol": symbol, "signal_date": start, "eligible_date": min(b["date"] for b in run_bars),
                        "target": "1", "reason": "initial_hold_allocation", "account_id": account_id}]
    if pending is not None:
        rejected.append({"account_id": account_id, "date": end, "signal_date": pending["signal_date"],
                         "reason": "pending_at_period_end"})
    for signal in method_signals:
        if signal["eligible_date"] > end:
            rejected.append({"account_id": account_id, "date": end, "signal_date": signal["signal_date"],
                             "reason": "signal_awaiting_next_open_after_period_end"})
    intervals = drawdown_intervals(daily)
    final = daily[-1]
    summary = {"account_id": account_id, "symbol": symbol, "method": method, "fee_per_side": float(fee),
               "initial_cash": 100000.0, "final_equity": final["equity"], "net_gain": final["equity"]-100000,
               "total_return": final["equity"]/100000-1, "final_cash": final["cash"],
               "final_receivable": final["receivable"], "final_units": final["units"],
               "terminal_market_value": final["market_value"], "fees": final["fees"],
               "dividends_received": final["dividends_received"], "buys": sum(t["side"]=="buy" for t in trades),
               "sells": sum(t["side"]=="sell" for t in trades), "cash_only_days": sum(r["units"]==0 for r in daily),
               "max_drawdown": min(r["equity"] / max([100000.0] + [x["equity"] for x in daily[:i+1]])-1 for i,r in enumerate(daily)),
               "unrecovered_drawdowns": sum(i["recovery_date"] is None for i in intervals),
               "conditional_product_qualification": True}
    monthly, yearly = period_rows(daily, trades, "month"), period_rows(daily, trades, "year")
    assert abs(sum(r["change"] for r in monthly) - summary["net_gain"]) < 1e-6
    assert abs(sum(r["change"] for r in yearly) - summary["net_gain"]) < 1e-6
    return {"daily": daily, "trades": trades, "signals": signals_out, "rejected": rejected,
            "summary": summary, "monthly": monthly, "yearly": yearly, "drawdown_recovery": intervals}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-main", action="store_true")
    parser.add_argument("--regress-old-hold", action="store_true")
    args = parser.parse_args()
    config = load_json(HERE / "config.json")
    settings = load_json(INPUTS / "execution-parameters-source.json")
    actions = load_json(INPUTS / "actions.json")
    bars = {s: read_bars(INPUTS / "bars" / f"{s}-nominal.csv") for s in config["symbols"]}
    if args.regress_old_hold:
        regressions = []
        for symbol in config["symbols"]:
            for fee_text in config["fees_per_side"]:
                account_id = f"{symbol}-hold-fee{fee_text}"
                got = simulate(account_id, symbol, "hold", D(fee_text), bars[symbol], actions, settings, [], *config["research_window"])
                old_dir = OLD / "account-results" / account_id
                old_daily = list(csv.DictReader((old_dir / "daily.csv").open()))
                old_trades = list(csv.DictReader((old_dir / "trades.csv").open()))
                got_daily = [{k: str(v) for k, v in row.items()} for row in got["daily"]]
                got_trades = [{k: str(v) for k, v in row.items()} for row in got["trades"]]
                # Compare serialized values through the same CSV writer to avoid Python str differences.
                import io
                def csv_rows(rows):
                    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
                    buf.seek(0); return list(csv.DictReader(buf))
                ok_daily = csv_rows(got["daily"]) == old_daily
                ok_trades = csv_rows(got["trades"]) == old_trades
                regressions.append({"account_id": account_id, "daily_identical": ok_daily, "trades_identical": ok_trades})
                if not (ok_daily and ok_trades):
                    raise RuntimeError(f"old hold regression failed: {account_id}")
        save_json(HERE / "old-hold-regression.json", regressions)
        print(json.dumps({"status": "old_hold_regression_passed", "accounts": 4}, ensure_ascii=False))
        return
    if not args.run_main:
        parser.error("choose --run-main or --regress-old-hold")
    if OUT.exists():
        raise RuntimeError("preserve prior account-results attempt")
    OUT.mkdir()
    locked = load_json(HERE / "source-lock.json")
    for item in locked["files"]:
        if sha256(HERE / item["path"]) != item["sha256"]:
            raise RuntimeError(f"source changed: {item['path']}")
    code_lock = load_json(HERE / "code-lock-attempt-02.json")
    for path, digest in code_lock["files"].items():
        if sha256(HERE / path) != digest:
            raise RuntimeError(f"code changed: {path}")
    run_inputs = [HERE/"protocol.md", HERE/"config.json", HERE/"source-lock.json", HERE/"code-lock-attempt-02.json", Path(__file__),
                  INPUTS/"actions.json", INPUTS/"action-coverage.json", INPUTS/"execution-parameters-source.json",
                  INPUTS/"dated-restrictions.json", INPUTS/"price-limit-regimes.json", INPUTS/"price-helper/price_basis.py"]
    run_inputs += [INPUTS / "bars" / f"{s}-nominal.csv" for s in config["symbols"]]
    save_json(OUT / "run-lock.json", {"started_at_utc": datetime.now(timezone.utc).isoformat(),
              "inputs": {str(path.resolve()): sha256(path) for path in run_inputs}})
    summaries = []
    for symbol in config["symbols"]:
        for method in config["methods"]:
            source = []
            for fee_text in config["fees_per_side"]:
                fee = D(fee_text); account_id = f"{symbol}-{method}-fee{fee_text}"
                result = simulate(account_id, symbol, method, fee, bars[symbol], actions, settings, source, *config["research_window"])
                folder = OUT / account_id; folder.mkdir()
                for name in ("daily", "trades", "monthly", "yearly", "drawdown_recovery"):
                    rows = result[name]
                    with (folder / f"{name}.csv").open("w", newline="") as fh:
                        fieldnames = list(rows[0]) if rows else ["account_id"]
                        writer = csv.DictWriter(fh, fieldnames=fieldnames); writer.writeheader(); writer.writerows(rows)
                for name in ("signals", "rejected", "summary"):
                    save_json(folder / f"{name}.json", result[name])
                summaries.append(result["summary"])
    save_json(OUT / "summary.json", summaries)
    run_lock = load_json(OUT / "run-lock.json")
    for path, digest in run_lock["inputs"].items():
        if sha256(Path(path)) != digest:
            raise RuntimeError(f"input changed during run: {path}")
    save_json(OUT / "completion.json", {"finished_at_utc": datetime.now(timezone.utc).isoformat(),
              "accounts": len(summaries), "period_reconciliations": {
                  s["account_id"]: "checked_in_account_generation" for s in summaries}, "input_hashes_checked_before_run": True})


if __name__ == "__main__":
    main()
