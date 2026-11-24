"""Prospective research-unit accounts. No broker or real-share execution."""

from __future__ import annotations

import math
from copy import deepcopy
from datetime import datetime, timedelta
from statistics import mean, stdev
from zoneinfo import ZoneInfo

from .engine import build_feature_panel, select_targets
from .sources import completed_market_date, proposed_session_open


def sessions(market, year=2026):
    """2026 official exchange holidays; unknown years fail closed."""
    if year != 2026:
        raise ValueError("需更新并核实新年度交易日历")
    if market == "CN":
        ranges = [
            ("01-01", "01-03"),
            ("02-15", "02-23"),
            ("04-04", "04-06"),
            ("05-01", "05-05"),
            ("06-19", "06-21"),
            ("09-25", "09-27"),
            ("10-01", "10-07"),
        ]
    else:
        ranges = [
            (d, d)
            for d in [
                "01-01",
                "01-19",
                "02-16",
                "04-03",
                "05-25",
                "06-19",
                "07-03",
                "09-07",
                "11-26",
                "12-25",
            ]
        ]
    holidays = set()
    for begin, end in ranges:
        day = datetime.fromisoformat(f"{year}-{begin}").date()
        last = datetime.fromisoformat(f"{year}-{end}").date()
        while day <= last:
            holidays.add(day)
            day += timedelta(days=1)
    day = datetime(year, 1, 1).date()
    result = []
    while day.year == year:
        if day.weekday() < 5 and day not in holidays:
            result.append(day.isoformat())
        day += timedelta(days=1)
    return result


def expected_close(market, at):
    cutoff = completed_market_date(market, at)
    days = sessions(market, int(cutoff[:4]))
    return max((d for d in days if d <= cutoff), default=None)


def summary(series, initial_cash, cost=0):
    if not series:
        return None
    returns = [p["return"] for p in series]
    days = (
        datetime.fromisoformat(series[-1]["date"]) - datetime.fromisoformat(series[0]["date"])
    ).days + 1
    ratio = series[-1]["equity"] / initial_cash
    return {
        "cumulative_return": ratio - 1,
        "annual_return": ratio ** (365.25 / days) - 1 if days >= 365 else None,
        "max_drawdown": min(p["drawdown"] for p in series),
        "sharpe": mean(returns) / stdev(returns) * math.sqrt(252)
        if len(returns) >= 252 and stdev(returns) > 0
        else None,
        "cost": cost,
        "average_exposure": mean(p.get("exposure", 0) for p in series),
        "max_stale_weight": max(p.get("unknown_weight", 0) for p in series),
    }


def initialize(config, at):
    if datetime.fromisoformat(at).tzinfo is None:
        raise ValueError("freeze must include timezone")
    return {"started_at": at, "config": deepcopy(config), "markets": {}}


def _empty_account(config):
    return {
        "cash": config["initial_cash"],
        "holdings": {},
        "orders": [],
        "decisions": [],
        "targets": [],
        "series": [],
        "cost": 0,
        "peak": config["initial_cash"],
        "forced_exits": [],
        "target_symbols": [],
        "last_decision": None,
    }


def _alignment(existing, rows):
    """Adjust changing vendor quote scale to immutable per-name research units."""
    by_symbol = {}
    for row in rows:
        by_symbol.setdefault(row["symbol"], {})[row["date"]] = row
    scales, errors = {}, {}
    for symbol, references in existing.items():
        source = by_symbol.get(symbol, {})
        pairs = [
            (old / source[d]["close"])
            for d, old in references
            if source.get(d, {}).get("valid") and source[d].get("close", 0)
        ]
        if len(pairs) != len(references):
            errors[symbol] = "固定价格锚点缺失"
        elif max(pairs) / min(pairs) - 1 > 1e-5:
            errors[symbol] = "历史价格发生非统一比例修订"
        else:
            scales[symbol] = pairs[-1]
    return scales, errors, by_symbol


def advance(state, market, snapshot, observed_at):
    """One complete-close batch; decisions only now, never backdated.

    Previously frozen orders may receive indicative next-session-open prices
    after that session closes. Both actual receipt and simulated fill times stay
    visible. Missing sessions expire orders and never create catch-up decisions.
    """
    result = deepcopy(state)
    now = datetime.fromisoformat(observed_at)
    if now.tzinfo is None or now < datetime.fromisoformat(state["started_at"]):
        raise ValueError("observation before freeze or timezone missing")
    config = result["config"]
    ms = result["markets"].setdefault(
        market,
        {
            "anchors": {},
            "last_date": None,
            "accounts": {s: _empty_account(config) for s in config["schemes"]},
            "status": "等待资料",
            "errors": {},
            "qualified_count": 0,
        },
    )
    expected = expected_close(market, observed_at)
    rows = snapshot.get("bars", [])
    universe = snapshot.get("universe", [])
    ms["universe"] = universe
    ms["received_at"] = observed_at
    ms["source_date"] = max((r["date"] for r in rows), default=None)
    current = {r["symbol"]: r for r in rows if r["date"] == expected and r.get("valid")}
    if not universe or len(current) / len(universe) < 0.90:
        ms["status"] = "等待最新资料"
        ms["reason"] = (
            f"应有 {expected} 收盘；当前有效 {len(current)}/{len(universe)}，"
            "未达到固定90%覆盖要求。"
        )
        return result
    if ms["last_date"] == expected:
        return result
    days = sessions(market, int(expected[:4]))
    future = [d for d in days if d > expected]
    next_date = future[0] if future else None
    opening = datetime.fromisoformat(proposed_session_open(market, expected))
    if now <= opening:
        raise ValueError("incomplete session")
    scales, errors, by_symbol = _alignment(ms["anchors"], rows)
    for symbol, source in by_symbol.items():
        if symbol not in ms["anchors"]:
            refs = [
                (d, r["close"])
                for d, r in sorted(source.items())
                if d <= expected and r.get("valid") and r.get("close", 0)
            ]
            if len(refs) >= 5:
                ms["anchors"][symbol] = refs[-5:]
                scales[symbol] = 1.0
    ms["errors"] = errors
    features = [r for r in build_feature_panel(rows) if r["date"] == expected]
    for feature in features:
        symbol = feature["symbol"]
        if symbol in errors or symbol not in scales:
            feature["eligible"] = False
            feature["close"] = feature["sma120"] = None
        else:
            for field in ("close", "sma120"):
                if feature[field] is not None:
                    feature[field] *= scales[symbol]
    ms["qualified_count"] = sum(r["eligible"] for r in features)
    features_by_symbol = {r["symbol"]: r for r in features}
    prices = {}
    for symbol, row in current.items():
        if symbol in scales and symbol not in errors:
            prices[symbol] = dict(
                row,
                open=row["open"] * scales[symbol] if row.get("open") else None,
                close=row["close"] * scales[symbol],
            )
    month_end = bool(next_date and next_date[:7] != expected[:7])
    initial = not ms.get("initial_decision_completed", False)
    names = {r["symbol"]: r.get("name", r["symbol"]) for r in universe}
    for scheme, account in ms["accounts"].items():
        fee_rate = config["cost_bps"][market] / 10000
        # Orders are single-session instructions. A late process cannot move them.
        for order in sorted(
            (o for o in account["orders"] if o["status"] == "等待"),
            key=lambda o: (o["side"] != "sell", o["symbol"]),
        ):
            if order["execute_date"] > expected:
                continue
            row = prices.get(order["symbol"])
            price = row.get("open") if row else None
            reason = None
            if order["execute_date"] != expected:
                reason = "错过指定交易日，未补记成交"
            elif datetime.fromisoformat(order["created_at"]) >= opening:
                reason = "下单时间晚于开盘"
            elif not price or row.get("open_tradable") is False:
                reason = "缺开盘报价或当日不可交易"
            elif order["side"] == "buy" and row.get("open_buy_allowed") is False:
                reason = "当日买入限制"
            quantity = 0.0
            holding = account["holdings"].get(order["symbol"])
            if reason is None:
                if order["side"] == "sell":
                    quantity = min(order["quantity"], holding["shares"] if holding else 0)
                    account["cash"] += quantity * price * (1 - fee_rate)
                    if holding:
                        holding["shares"] -= quantity
                        if holding["shares"] < 1e-9:
                            del account["holdings"][order["symbol"]]
                else:
                    quantity = min(order["quantity"], account["cash"] / (price * (1 + fee_rate)))
                    account["cash"] -= quantity * price * (1 + fee_rate)
                    holding = account["holdings"].setdefault(
                        order["symbol"],
                        {
                            "symbol": order["symbol"],
                            "name": names.get(order["symbol"], order["symbol"]),
                            "shares": 0,
                            "price": price,
                        },
                    )
                    holding["shares"] += quantity
                account["cost"] += quantity * price * fee_rate
            order.update(
                status="报价模拟成交" if quantity else "未成交",
                filled_quantity=quantity,
                price=price if quantity else None,
                observed_at=observed_at,
                scheduled_open_at=proposed_session_open(market, order["execute_date"]),
                simulated_open_at=opening.isoformat() if quantity else None,
                failure_reason=reason,
                cost=quantity * (price or 0) * fee_rate,
            )
        invested = stale = 0.0
        for symbol, holding in account["holdings"].items():
            if symbol in prices:
                holding["price"] = prices[symbol]["close"]
            else:
                stale += holding["shares"] * holding["price"]
            holding["value"] = holding["shares"] * holding["price"]
            invested += holding["value"]
        equity = account["cash"] + invested
        account["peak"] = max(account["peak"], equity)
        for holding in account["holdings"].values():
            holding["weight"] = holding["value"] / equity
        # Seed prices can precede freeze, but may never enter the return record.
        local_freeze = datetime.fromisoformat(state["started_at"]).astimezone(
            ZoneInfo("Asia/Shanghai" if market == "CN" else "America/New_York")
        )
        close_hour = (
            15 if market == "CN" else (13 if expected in {"2026-11-27", "2026-12-24"} else 16)
        )
        close_at = datetime.fromisoformat(f"{expected}T{close_hour:02}:00:00").replace(
            tzinfo=local_freeze.tzinfo
        )
        if close_at > local_freeze:
            previous = (
                account["series"][-1]["equity"] if account["series"] else config["initial_cash"]
            )
            account["series"].append(
                {
                    "date": expected,
                    "equity": equity,
                    "nav": equity / config["initial_cash"],
                    "cash": account["cash"],
                    "drawdown": equity / account["peak"] - 1,
                    "return": equity / previous - 1,
                    "exposure": invested / equity,
                    "unknown_weight": stale / equity,
                    "observed_at": observed_at,
                }
            )
        targets = select_targets(features, scheme, config["slots"])
        account["targets"] = [dict(t, name=names.get(t["symbol"], t["symbol"])) for t in targets]
        forced = set(account["forced_exits"])
        monthly = initial or month_end
        if monthly:
            account["target_symbols"] = [t["symbol"] for t in targets]
            forced.difference_update(account["target_symbols"])
        order_map = {}
        for symbol, holding in account["holdings"].items():
            f = features_by_symbol.get(symbol, {})
            if f.get("close") and f.get("sma120") and f["close"] < f["sma120"]:
                forced.add(symbol)
            if symbol in forced or symbol not in account["target_symbols"]:
                order_map[symbol] = (
                    "sell",
                    holding["shares"],
                    "跌破120日均线退出" if symbol in forced else "月度名单退出",
                )
            elif holding["weight"] > config["concentration_cap"] and symbol in prices:
                order_map[symbol] = (
                    "sell",
                    holding["shares"] - 0.05 * equity / holding["price"],
                    "单只超过10%，降回5%",
                )
        if monthly:
            for target in targets:
                symbol = target["symbol"]
                if symbol in forced or symbol in order_map:
                    continue
                current_quantity = account["holdings"].get(symbol, {}).get("shares", 0)
                delta = (
                    equity * target["target_weight"] / target["reference_price"] - current_quantity
                )
                if abs(delta) > 1e-9:
                    order_map[symbol] = (
                        "buy" if delta > 0 else "sell",
                        abs(delta),
                        "首次配置" if initial else "月度调仓",
                    )
        account["forced_exits"] = sorted(forced)
        if next_date and now < datetime.fromisoformat(proposed_session_open(market, next_date)):
            for symbol, (side, quantity, reason) in sorted(order_map.items()):
                order = {
                    "id": f"{market}:{scheme}:{expected}:{symbol}",
                    "date": expected,
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "reason": reason,
                    "status": "等待",
                    "created_at": observed_at,
                    "execute_date": next_date,
                }
                account["orders"].append(order)
                account["decisions"].append({k: order[k] for k in ("date", "symbol", "reason")})
        account["last_decision"] = observed_at
    ms["last_date"] = expected
    if next_date and now < datetime.fromisoformat(proposed_session_open(market, next_date)):
        ms["initial_decision_completed"] = True
    ms["status"] = "报价模拟观察" if next_date else "等待新年度交易日历"
    ms["reason"] = (
        "固定研究单位；开盘报价模拟在收盘采集后记录，不代表实际成交。"
        if next_date
        else "交易日历到期，保留持仓与估值，暂停新订单。"
    )
    return result
