#!/usr/bin/env python3
"""Independent R1 exit checker. Does not import the frozen account simulator.

Preparation mode only validates the locked source inventory. Real calculations are
run later with --run after the new executor result path is supplied and locked.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TECH = ROOT.parent / "research-broad-etf-technical-2026-09-08" / "execution"
START, END = "2015-01-01", "2026-06-30"
SYMBOLS = ("sh510300", "sz159915")
FEES = (0.001, 0.002)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_sources() -> tuple[dict, dict, list, dict, list]:
    cfg = read_json(TECH / "inputs/execution-config.json")
    bars = {}
    for symbol in SYMBOLS:
        with (TECH / f"inputs/bars/{symbol}-nominal.csv").open(newline="", encoding="utf-8") as f:
            bars[symbol] = {r["date"]: {k: float(r[k]) for k in ("open", "high", "low", "close", "volume")} for r in csv.DictReader(f)}
    actions = [a for a in read_json(TECH / "inputs/actions.json") if a["symbol"] in SYMBOLS]
    with gzip.open(TECH / "inputs/exit-observations.json.gz", "rt", encoding="utf-8") as f:
        observations = json.load(f)
    candidates = [c for c in read_json(TECH / "inputs/source-candidates/diagnostic-candidates.json") if c["symbol"] in SYMBOLS and c["config_id"] == "R1"]
    return cfg, bars, actions, observations, candidates


def next_day(d: str) -> str:
    return (date.fromisoformat(d) + timedelta(days=1)).isoformat()


def unavailable(symbol: str, d: str, bars: dict, reference: float, cfg: dict) -> str | None:
    if d in set(cfg["blocked_dates"].get(symbol, [])):
        return "known_open_unavailable"
    if d not in bars[symbol]:
        return "missing_quote"
    limit = float(cfg["limits"][symbol])
    for effective, value in sorted(cfg["limit_changes"].get(symbol, [])):
        if effective <= d:
            limit = float(value)
    if abs(bars[symbol][d]["open"] - reference) >= reference * limit - 0.00051:
        return "at_open_limit_conservative"
    return None


def accepted_r1(c: dict) -> bool:
    if not math.isfinite(float(c.get("stop", float("nan")))) or float(c["stop"]) <= 0:
        return False
    if c.get("signal_accepted") is not False:
        return True
    return c.get("signal_reject_reason") in {"target_unavailable", "signal_reward_risk_below_3"}


@dataclass
class Position:
    candidate_id: str
    entry_date: str
    entry_price: float
    shares: float
    stop: float
    buy_fee: float
    entry_notional: float
    dividends: float = 0.0
    road_weakened_dates: list[str] = field(default_factory=list)


def exit_reason(rule: str, close: float, stop: float, obs: dict) -> str | None:
    if close < stop:
        return "structure_stop"
    road = close < float(obs["ema20"]) and close < float(obs["cost20"])
    if rule == "original" and road:
        return "ema_cost_exit"
    return None


def simulate_complete(symbol: str, fee: float, rule: str, cfg: dict, bars: dict, actions: list, observations: dict, candidates: list) -> dict:
    """Clean-room single-product cash account for R1 candidates."""
    b = bars[symbol]
    action_list = sorted((a for a in actions if a["symbol"] == symbol), key=lambda x: (x["effective_date"], x["event_id"]))
    cs_by_date: dict[str, list[dict]] = {}
    for c in sorted((x for x in candidates if x["symbol"] == symbol), key=lambda x: (x["signal_date"], x["candidate_id"])):
        if START <= c["signal_date"] <= END:
            cs_by_date.setdefault(c["signal_date"], []).append(c)
    cash, shares, fees = 100000.0, 0.0, 0.0
    prior_dates = sorted(d for d in b if d < START)
    reference = float(b[prior_dates[-1]]["close"])
    position: Position | None = None
    pending_sell: dict | None = None
    pending_buys: list[dict] = []
    rights: dict[str, tuple[float, Position | None]] = {}
    receivables: dict[str, tuple[float, Position | None]] = {}
    trades, roundtrips, daily, rejected, road_events = [], [], [], [], []
    day = date.fromisoformat(START)
    while day <= date.fromisoformat(END):
        d = day.isoformat()
        open_reference = reference
        sold_today = False
        for a in action_list:
            if a["effective_date"] == d:
                if a["type"] == "cash_dividend":
                    div = float(a["cash"])
                    factor = (open_reference - div) / open_reference
                    open_reference -= div
                    reference -= div
                    entitled, entitled_position = rights.get(a["event_id"], (0.0, None))
                    amount = entitled * div
                    receivables[a["event_id"]] = (amount, entitled_position)
                    if entitled_position is not None:
                        entitled_position.dividends += amount
                    if position is not None:
                        position.stop *= factor
                    for order in pending_buys:
                        if order["status"] == "pending" and order["signal_date"] < d:
                            order["stop"] *= factor
                else:
                    ratio = float(a["ratio"])
                    reference /= ratio
                    open_reference /= ratio
                    shares *= ratio
                    if position is not None:
                        position.shares = shares
                        position.stop /= ratio
                    for order in pending_buys:
                        if order["status"] == "pending" and order["signal_date"] < d:
                            order["stop"] /= ratio
            if a["type"] == "cash_dividend" and a["pay_date"] == d:
                amount, _ = receivables.pop(a["event_id"], (0.0, None))
                cash += amount
        if pending_sell and d > pending_sell["signal_date"]:
            reason = unavailable(symbol, d, bars, open_reference, cfg)
            if reason is None and position is not None and d > position.entry_date:
                px = b[d]["open"]
                notional = shares * px
                sell_fee = notional * fee
                cash += notional - sell_fee
                fees += sell_fee
                trades.append({"date": d, "side": "sell", "shares": shares, "price": px, "fee": sell_fee, "reason": pending_sell["reason"], "candidate_id": position.candidate_id})
                roundtrips.append({"candidate_id": position.candidate_id, "entry_date": position.entry_date, "entry_price": position.entry_price, "shares": position.shares, "entry_notional": position.entry_notional, "buy_fee": position.buy_fee, "exit_date": d, "exit_price": px, "sell_fee": sell_fee, "dividends": position.dividends, "exit_reason": pending_sell["reason"], "road_weakened_dates": position.road_weakened_dates})
                position = None
                shares = 0.0
                pending_sell = None
                sold_today = True
        for order in pending_buys:
            if order["status"] != "pending" or order["planned_date"] != d:
                continue
            reason = "same_day_sale" if sold_today else "position_exists" if position else unavailable(symbol, d, bars, open_reference, cfg)
            if reason is None:
                px = b[d]["open"]
                if order["stop"] >= px:
                    reason = "nonpositive_open_risk"
            qty = 0
            if reason is None:
                qty = math.floor(cash / (px * (1 + fee)) / 100) * 100
                if qty <= 0:
                    reason = "insufficient_cash_or_risk_lot"
            if reason:
                order["status"] = "rejected"
                rejected.append({"candidate_id": order["candidate_id"], "date": d, "reason": reason})
            else:
                notional = qty * px
                buy_fee = notional * fee
                cash -= notional + buy_fee
                shares = float(qty)
                fees += buy_fee
                position = Position(order["candidate_id"], d, px, shares, order["stop"], buy_fee, notional)
                order["status"] = "filled"
                trades.append({"date": d, "side": "buy", "shares": shares, "price": px, "fee": buy_fee, "reason": "candidate_entry", "candidate_id": order["candidate_id"]})
        if d in b:
            reference = b[d]["close"]
            if position is not None and pending_sell is None:
                obs = observations[symbol][d]
                road = reference < float(obs["ema20"]) and reference < float(obs["cost20"])
                if road:
                    position.road_weakened_dates.append(d)
                    road_events.append({"candidate_id": position.candidate_id, "date": d})
                reason = exit_reason(rule, reference, position.stop, obs)
                if reason:
                    pending_sell = {"signal_date": d, "reason": reason}
        for c in cs_by_date.get(d, []):
            if not accepted_r1(c):
                rejected.append({"candidate_id": c["candidate_id"], "date": d, "reason": c.get("signal_reject_reason") or "signal_rejected"})
                continue
            if position is not None:
                rejected.append({"candidate_id": c["candidate_id"], "date": d, "reason": "pending_exit" if pending_sell else "position_exists"})
                continue
            future = sorted(x for x in b if x > d)
            planned = future[0] if future else None
            pending_buys.append({"candidate_id": c["candidate_id"], "signal_date": d, "planned_date": planned, "stop": float(c["stop"]), "status": "pending"})
        for a in action_list:
            if a["type"] == "cash_dividend" and a["record_date"] == d:
                rights[a["event_id"]] = (shares, position)
        receivable = sum(amount for amount, _ in receivables.values())
        mark = reference
        equity = cash + shares * mark + receivable
        daily.append({"date": d, "equity": equity, "cash": cash, "shares": shares, "mark": mark, "receivable": receivable, "fees": fees})
        day += timedelta(days=1)
    if position is not None:
        roundtrips.append({"candidate_id": position.candidate_id, "entry_date": position.entry_date, "entry_price": position.entry_price, "shares": position.shares, "entry_notional": position.entry_notional, "buy_fee": position.buy_fee, "exit_date": None, "exit_price": None, "sell_fee": 0.0, "dividends": position.dividends, "exit_reason": None, "road_weakened_dates": position.road_weakened_dates, "terminal_mark": reference})
    return {"symbol": symbol, "fee": fee, "rule": rule, "daily": daily, "trades": trades, "roundtrips": roundtrips, "rejected": rejected, "road_events": road_events}


def fixed_entry_path(entry: dict, symbol: str, fee: float, rule: str, cfg: dict, bars: dict, actions: list, observations: dict) -> dict:
    """Rebuild one frozen old buy independently; never opens another position."""
    b = bars[symbol]
    shares = float(entry["shares"] if entry.get("shares", 0) else entry["entry_notional"] / entry["entry_price"])
    # Closed old roundtrips store shares=0; recover the exact buy quantity from notional.
    shares = float(entry["entry_notional"]) / float(entry["entry_price"])
    stop = float(entry["initial_stop"])
    dividends = 0.0
    rights: dict[str, float] = {}
    entry_obs = observations[symbol][entry["entry_date"]]
    entry_close = float(b[entry["entry_date"]]["close"])
    entry_road = entry_close < float(entry_obs["ema20"]) and entry_close < float(entry_obs["cost20"])
    road_dates = [entry["entry_date"]] if entry_road else []
    first_reason = exit_reason(rule, entry_close, stop, entry_obs)
    pending: dict | None = {"signal_date": entry["entry_date"], "reason": first_reason} if first_reason else None
    prior = sorted(d for d in b if d <= entry["entry_date"])
    reference = float(b[prior[-1]]["close"])
    # The frozen buy can itself occur on a record date. It owns the entitlement
    # at that close; starting the loop on the next day must not drop that right.
    for a in actions:
        if a["symbol"] == symbol and a["type"] == "cash_dividend" and a["record_date"] == entry["entry_date"]:
            rights[a["event_id"]] = shares
    day = date.fromisoformat(next_day(entry["entry_date"]))
    while day <= date.fromisoformat(END):
        d = day.isoformat()
        open_reference = reference
        for a in sorted((x for x in actions if x["symbol"] == symbol), key=lambda x: (x["effective_date"], x["event_id"])):
            if a["effective_date"] == d:
                if a["type"] == "cash_dividend":
                    div = float(a["cash"])
                    factor = (open_reference - div) / open_reference
                    open_reference -= div
                    reference -= div
                    stop *= factor
                    dividends += rights.get(a["event_id"], 0.0) * div
                else:
                    ratio = float(a["ratio"])
                    shares *= ratio
                    stop /= ratio
                    reference /= ratio
                    open_reference /= ratio
        if pending and d > pending["signal_date"] and unavailable(symbol, d, bars, open_reference, cfg) is None:
            px = b[d]["open"]
            sell_fee = shares * px * fee
            terminal = shares * px - sell_fee + dividends - float(entry["entry_notional"]) - float(entry["buy_fee"])
            return {"candidate_id": entry["candidate_id"], "symbol": symbol, "fee": fee, "rule": rule, "entry_date": entry["entry_date"], "entry_price": entry["entry_price"], "shares": shares, "initial_stop": entry["initial_stop"], "exit_signal_date": pending["signal_date"], "exit_date": d, "exit_price": px, "exit_reason": pending["reason"], "sell_fee": sell_fee, "dividends": dividends, "net_pnl": terminal, "terminal_value": float(entry["entry_notional"]) + float(entry["buy_fee"]) + terminal, "road_weakened_dates": road_dates}
        if d in b:
            reference = b[d]["close"]
            obs = observations[symbol][d]
            if reference < float(obs["ema20"]) and reference < float(obs["cost20"]):
                road_dates.append(d)
            if pending is None:
                reason = exit_reason(rule, reference, stop, obs)
                if reason:
                    pending = {"signal_date": d, "reason": reason}
        for a in actions:
            if a["symbol"] == symbol and a["type"] == "cash_dividend" and a["record_date"] == d:
                rights[a["event_id"]] = shares
        day += timedelta(days=1)
    mark = float(b[max(d for d in b if d <= END)]["close"])
    terminal = shares * mark + dividends - float(entry["entry_notional"]) - float(entry["buy_fee"])
    return {"candidate_id": entry["candidate_id"], "symbol": symbol, "fee": fee, "rule": rule, "entry_date": entry["entry_date"], "entry_price": entry["entry_price"], "shares": shares, "initial_stop": entry["initial_stop"], "exit_signal_date": pending["signal_date"] if pending else None, "exit_date": None, "exit_price": None, "exit_reason": None, "sell_fee": 0.0, "dividends": dividends, "net_pnl": terminal, "terminal_value": float(entry["entry_notional"]) + float(entry["buy_fee"]) + terminal, "road_weakened_dates": road_dates, "terminal_mark": mark}


def load_fixed_entries() -> list[dict]:
    out = []
    for symbol in SYMBOLS:
        for fee in FEES:
            tag = int(round(fee * 10000))
            path = TECH / f"account-results/{symbol}-R1-fee{tag:02d}bp/roundtrips.json"
            for item in read_json(path):
                x = dict(item)
                x["source_account"] = f"{symbol}-R1-fee{tag:02d}bp"
                x["fee"] = fee
                out.append(x)
    if len(out) != 330:
        raise AssertionError(f"expected 330 frozen entries, got {len(out)}")
    return out


def self_test() -> None:
    obs = {"ema20": 10.0, "cost20": 9.0}
    assert exit_reason("original", 8.9, 7.0, obs) == "ema_cost_exit"
    assert exit_reason("structure_only", 8.9, 7.0, obs) is None
    assert exit_reason("original", 7.0, 7.0, obs) == "ema_cost_exit"  # equal stop is not structure
    assert exit_reason("original", 9.0, 7.0, obs) is None  # equal cost20 is not road exit
    assert exit_reason("original", 6.9, 7.0, obs) == "structure_stop"


def run_real(output: Path) -> None:
    cfg, bars, actions, observations, candidates = load_sources()
    output.mkdir(parents=True, exist_ok=False)
    complete = []
    for symbol in SYMBOLS:
        for fee in FEES:
            # Original is reconstructed for regression; structure_only is the four-account new result.
            for rule in ("original", "structure_only"):
                complete.append(simulate_complete(symbol, fee, rule, cfg, bars, actions, observations, candidates))
    fixed = []
    for entry in load_fixed_entries():
        for rule in ("original", "structure_only"):
            fixed.append(fixed_entry_path(entry, entry["symbol"], entry["fee"], rule, cfg, bars, actions, observations))
    (output / "complete-independent.json").write_text(json.dumps(complete, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "fixed-entries-independent.json").write_text(json.dumps(fixed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    self_test()
    if args.run:
        if args.output is None:
            raise SystemExit("--run requires --output")
        run_real(args.output)
    elif not args.self_test:
        print("prepared: self-tests passed; no real account calculation run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
