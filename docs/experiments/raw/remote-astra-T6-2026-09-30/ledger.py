"""T6 独立核算器：人工标准答案。

按旧冻结协议的文字（出处见 boundaries.json 的 contracts 与各条“旧协议约定”）逐日记账。
不 import、不复制被测的 engine.py / metrics.py / run_accounts.py 的任何函数；全部十进制精确计算。

用法：/tmp/bq-venv/bin/python ledger.py
读：本目录 cases.json；写：本目录 hand-answers.json。不读写其他目录。

两种合同模式：
- technical：48账户冻结协议（TP）+ 其所称“已核引擎”的接口规范（IF）。
- f12_hold：首12账户冻结协议（F12）的一直持有方法。
除息/拆分无报价日按“财富不变”记账（IF 第21行“旧现金账户估值则减每份现金”，
F12 分红第4条“生效日先改份额和比较口径”）。
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from decimal import Decimal as D, ROUND_FLOOR, ROUND_HALF_UP, getcontext
from pathlib import Path

sys.dont_write_bytecode = True
getcontext().prec = 60
HERE = Path(__file__).resolve().parent
TOL = D("1e-9")
LIMIT_TOLERANCE = D("0.00051")  # IF 第11行：沿用第五开盘限制的0.00051容差


class HandStop(Exception):
    """旧合同要求停下核口径、不能静默继续的情形。"""


def dec(x):
    return None if x is None else D(str(x))


def floor_lots(x: D) -> D:
    """向下取整到100份；非正数为0。"""
    if x <= 0:
        return D(0)
    return (x / 100).to_integral_value(rounding=ROUND_FLOOR) * 100


def calendar(start: str, end: str):
    d, e = date.fromisoformat(start), date.fromisoformat(end)
    while d <= e:
        yield d.isoformat()
        d += timedelta(days=1)


def exchange_limits(ref: D, limit: D):
    """交易所普通涨跌停价：前收×(1±幅度)，四舍五入到0.001元（price-limit-regimes.json）。"""
    q = D("0.001")
    return (ref * (1 + limit)).quantize(q, ROUND_HALF_UP), (ref * (1 - limit)).quantize(q, ROUND_HALF_UP)


def contract_open_blocked(op: D, ref: D, limit: D) -> bool:
    """旧合同的对称保守判断：|开盘−参考价| ≥ 参考价×幅度−0.00051 即视为触及。"""
    return abs(op - ref) >= ref * limit - LIMIT_TOLERANCE


def merged(case: dict, defaults: dict) -> dict:
    out = dict(defaults)
    out.update({k: v for k, v in case.items() if k not in ("secondary",)})
    return out


# ----------------------------------------------------------------------------
# technical 合同：单产品、单持仓、A/C/D 或 R0/R1 诊断参照
# ----------------------------------------------------------------------------
def run_technical(case: dict, policy: dict) -> dict:
    fee, limit, kind = dec(case["fee"]), dec(case["limit"]), case["kind"]
    bars = {d: {"open": dec(o), "close": dec(c)} for d, (o, c) in case["bars"].items()}
    quote_days = sorted(bars)
    blocked = set(case.get("blocked", []))
    forbidden = set(case.get("forbidden_close", []))
    acts = [dict(a) for a in case.get("actions", [])]
    obs = {k: dec(v) for k, v in case["obs"].items()}
    start, end = case["start"], case["end"]
    initial, weekly = dec(case["initial"]), dec(case["weekly"])

    cash, units = initial, D(0)
    funding, acct_units, nav = initial, initial, D(1)
    prior = [d for d in quote_days if d < start]
    mark_date = prior[-1]
    mark = bars[mark_date]["close"]
    prev_equity = initial
    receivable, rights = {}, {}
    position, positions, pending_sell = None, [], None
    buys, orders, sells, trades, daily, calc = [], {}, [], [], {}, {}
    by_day = {}
    for c in case.get("candidates", []):
        by_day.setdefault(c["signal_date"], []).append(c)

    for d in calendar(start, end):
        ref = mark  # 前一有效收盘（当前份额单位）；开盘前行动再调整
        # ① 公司行动与到账：开盘前（IF 第13、21行）
        for a in sorted(acts, key=lambda x: (x["ex"], x["id"])):
            if a["ex"] == d:
                if a["type"] == "split":
                    r = dec(a["ratio"])
                    factor = 1 / r
                    units *= r
                    mark *= factor
                    ref *= factor
                    if position is not None:
                        position["shares"] = units
                else:
                    cps = dec(a["cash"])
                    between = [b["id"] for b in acts if b is not a and mark_date < b["ex"] < d]
                    if between and policy.get("stale_dividend_reference") == "stop":
                        raise HandStop(f"{d} 除息的参照收盘({mark_date})与除息之间还有行动{between}且无新报价："
                                       "价格换算器合同 protocol-amendment-1 第2条要求停止，不擅自二次推导")
                    factor = (ref - cps) / ref
                    mark -= cps
                    ref -= cps
                    ent = rights.get(a["id"], {"shares": D(0), "pos": None})
                    amount = ent["shares"] * cps
                    receivable[a["id"]] = {"amount": amount, "pos": ent["pos"]}
                    if ent["pos"] is not None:
                        ent["pos"]["div_accrued"] += amount
                targets = ([position] if position is not None else []) + \
                          [o for o in buys if o["status"] == "pending" and o["signal_date"] < d]
                for obj in targets:
                    for k in ("stop", "target"):
                        if obj.get(k) is not None:
                            obj[k] *= factor
            if a["type"] == "cash_dividend" and a["pay"] == d:
                item = receivable.pop(a["id"], None)
                if item is not None:
                    cash += item["amount"]
                    if item["pos"] is not None:
                        item["pos"]["div_paid"] += item["amount"]
        # ② 周一外部入金：按前一日净值折成账户单位（IF 第13行）
        flow = D(0)
        if weekly > 0 and date.fromisoformat(d).weekday() == 0:
            flow = weekly
            acct_units += flow / nav
            cash += flow
            funding += flow

        def open_block():
            if d in blocked:
                return "blocked"
            if d not in bars:
                return "missing_quote"
            if contract_open_blocked(bars[d]["open"], ref, limit):
                return "open_limit"
            return None

        sold_today = False
        # ③ 之前的待卖单：可顺延（TP「资金、时点、未成交」）
        if pending_sell is not None and d > pending_sell["signal_date"]:
            why = open_block()
            if why is None and d <= position["entry_date"]:
                why = "same_day_as_buy"
            pending_sell["attempts"].append([d, why or "filled"])
            if why is None:
                op = bars[d]["open"]
                notional = units * op
                f = notional * fee
                cash += notional - f
                position.update(closed=True, exit_date=d, exit_notional=notional, sell_fee=f, shares=D(0))
                trades.append(dict(date=d, side="sell", shares=units, price=op, notional=notional, fee=f))
                pending_sell.update(status="filled", fill_date=d)
                units, position, pending_sell, sold_today = D(0), None, None, True
        # ④ 计划买单：只在指定日试一次
        for o in buys:
            if o["status"] != "pending" or o["planned"] != d:
                continue
            why = "same_day_sale" if sold_today else ("position_held" if position is not None else open_block())
            op = bars[d]["open"] if d in bars else None
            if why is None:
                stop, tgt = o["stop"], o["target"]
                if kind == "diag":
                    if stop is None or stop <= 0 or stop >= op:
                        why = "nonpositive_open_risk"
                elif tgt is None or tgt <= 0:
                    why = "missing_or_invalid_target"
                elif stop is None or stop <= 0 or stop >= op:
                    why = "nonpositive_open_risk"
                elif (tgt - op) / (op - stop) < 3:
                    why = "open_rr_below3"
            qty, budget, cash_lots, risk_lots = D(0), None, None, None
            if why is None:
                cash_lots = floor_lots(cash / (op * (1 + fee)))
                if kind == "acd":
                    budget = prev_equity * D("0.01")
                    risk_lots = floor_lots(budget / (op - o["stop"]))
                    qty = min(cash_lots, risk_lots)
                else:
                    qty = cash_lots
                if qty <= 0:
                    why = "insufficient_cash_or_lot"
            o["attempts"].append([d, why or "filled"])
            if why:
                o.update(status="rejected", reason=why)
                if why == "open_limit":
                    up, dn = exchange_limits(ref, limit)
                    calc.setdefault("exchange_limit_up", up)
                    calc.setdefault("exchange_limit_down", dn)
                    calc.setdefault("open_strictly_inside_exchange_limits", dn < op < up)
                    if kind == "diag":
                        calc.setdefault("shares_if_exchange_rule", floor_lots(cash / (op * (1 + fee))))
                continue
            rec_total = sum(v["amount"] for v in receivable.values())
            if rec_total > 0:
                alt = floor_lots((cash + rec_total) / (op * (1 + fee)))
                calc.setdefault("shares_if_receivable_spendable", min(alt, risk_lots) if risk_lots is not None else alt)
            notional = qty * op
            f = notional * fee
            cash -= notional + f
            units += qty
            position = dict(cid=o["cid"], entry_date=d, entry_price=op, entry_notional=notional, buy_fee=f,
                            stop=o["stop"], target=o["target"], shares=qty, div_accrued=D(0), div_paid=D(0),
                            closed=False, exit_date=None, exit_notional=D(0), sell_fee=D(0), budget=budget,
                            cash_lots=cash_lots, risk_lots=risk_lots, planned_risk=qty * (op - o["stop"]),
                            prev_equity=prev_equity)
            positions.append(position)
            trades.append(dict(date=d, side="buy", shares=qty, price=op, notional=notional, fee=f, cid=o["cid"]))
            o.update(status="filled", fill_date=d)
        # ⑤ 收盘估值与退出判断（收盘确认，下一允许开盘卖）
        if d in bars:
            if d in forbidden:
                if policy.get("forbidden_close", "stop") == "stop":
                    raise HandStop(f"{d} 有报价但禁止收盘估值：TP「资金、时点、未成交」要求先停下核口径，不静默使用")
            else:
                mark, mark_date = bars[d]["close"], d
                if position is not None and pending_sell is None:
                    why = None
                    if mark < position["stop"]:
                        why = "structure_stop"
                    elif kind == "diag" and mark < obs["ema20"] and mark < obs["cost20"]:
                        why = "ema_cost_exit"
                    if why:
                        pending_sell = dict(signal_date=d, reason=why, attempts=[], status="pending")
                        sells.append(pending_sell)
        # ⑥ 收盘新机会：下一报价日计划买入；仍持有则拒绝
        for c in by_day.get(d, []):
            later = [q for q in quote_days if q > d]
            o = dict(cid=c["id"], signal_date=d, stop=dec(c["stop"]), target=dec(c.get("target")),
                     planned=later[0] if later else None, attempts=[], status="pending", reason=None)
            ref_s = dec(c["signal_ref"])
            why = None
            if o["stop"] is None or o["stop"] <= 0:
                why = "invalid_stop"
            elif kind == "acd" and (o["target"] is None or o["target"] <= 0):
                why = "missing_or_invalid_target"
            elif ref_s <= o["stop"]:
                why = "nonpositive_signal_risk"
            elif kind == "acd" and (o["target"] - ref_s) / (ref_s - o["stop"]) < 3:
                why = "signal_rr_below3"
            if why is None and position is not None:
                why = "position_held"
            if why:
                o.update(status="rejected", reason=why)
            else:
                buys.append(o)
            orders[c["id"]] = o
        # ⑦ 登记日收盘后锁定权利份数
        for a in acts:
            if a["type"] == "cash_dividend" and a["record"] == d:
                rights[a["id"]] = {"shares": units, "pos": position}
        # ⑧ 日账
        rec = sum(v["amount"] for v in receivable.values())
        equity = cash + units * mark + rec
        nav = equity / acct_units
        daily[d] = dict(cash=cash, units=units, mark=mark, mark_date=mark_date, receivable=rec,
                        equity=equity, funding=funding, nav=nav, deposit=flow)
        prev_equity = equity

    for o in buys:
        if o["status"] == "pending":
            o["status"] = "pending_at_end"
    if pending_sell is not None:
        pending_sell["status"] = "pending_at_end"
    last = daily[end]
    for p in positions:
        market = D(0) if p["closed"] else p["shares"] * last["mark"]
        p["market_value"] = market
        p["net_pnl"] = p["exit_notional"] + market + p["div_accrued"] - p["entry_notional"] - p["buy_fee"] - p["sell_fee"]
    calc["investment_pnl"] = last["equity"] - last["funding"]
    open_value = sum((p["market_value"] for p in positions if not p["closed"]), D(0))
    if open_value > 0:
        calc["hypothetical_sell_fee"] = open_value * fee
        calc["equity_after_hypothetical_sale"] = last["equity"] - open_value * fee
    return dict(status="ok", trades=trades, orders=orders, sells=sells, positions=positions, daily=daily, calc=calc)


# ----------------------------------------------------------------------------
# f12_hold 合同：首个可成交开盘按目标100%买入，之后不卖
# ----------------------------------------------------------------------------
def run_f12_hold(case: dict, policy: dict) -> dict:
    fee, limit = dec(case["fee"]), dec(case["limit"])
    bars = {d: {"open": dec(o), "close": dec(c)} for d, (o, c) in case["bars"].items()}
    blocked = set(case.get("blocked", []))
    forbidden = set(case.get("forbidden_close", []))
    acts = [dict(a) for a in case.get("actions", [])]
    start, end, initial = case["start"], case["end"], dec(case["initial"])
    prior = sorted(d for d in bars if d < start)
    mark_date = prior[-1]
    mark = ref = bars[mark_date]["close"]
    cash, units, receivable, rights = initial, D(0), {}, {}
    bought, trades, daily = False, [], {}
    for d in calendar(start, end):
        bar = bars.get(d)
        for a in sorted(acts, key=lambda x: (x["ex"], x["id"])):
            if a["ex"] == d:
                if a["type"] == "split":
                    r = dec(a["ratio"])
                    units *= r
                    mark /= r
                    ref /= r
                else:
                    cps = dec(a["cash"])
                    receivable[a["id"]] = rights.get(a["id"], D(0)) * cps
                    mark -= cps
                    ref -= cps
            if a["type"] == "cash_dividend" and a["pay"] == d:
                cash += receivable.pop(a["id"], D(0))
        if not bought and bar is not None and d not in blocked and not contract_open_blocked(bar["open"], ref, limit):
            op = bar["open"]
            rec = sum(receivable.values(), D(0))
            equity_open = cash + rec + units * op
            qty = min(floor_lots((equity_open - units * op) / op), floor_lots(cash / (op * (1 + fee))))
            if qty > 0:
                notional = qty * op
                f = notional * fee
                cash -= notional + f
                units += qty
                trades.append(dict(date=d, side="buy", shares=qty, price=op, notional=notional, fee=f))
            bought = True
        if bar is not None:
            if d in forbidden:
                if policy.get("forbidden_close", "stop") == "stop":
                    raise HandStop(f"{d} 有报价但禁止收盘估值")
            else:
                mark, ref, mark_date = bar["close"], bar["close"], d
        for a in acts:
            if a["type"] == "cash_dividend" and a["record"] == d:
                rights[a["id"]] = units
        rec = sum(receivable.values(), D(0))
        daily[d] = dict(cash=cash, units=units, mark=mark, mark_date=mark_date, receivable=rec,
                        equity=cash + units * mark + rec, funding=initial)
    last = daily[end]
    calc = {"investment_pnl": last["equity"] - initial}
    return dict(status="ok", trades=trades, orders={}, sells=[], positions=[], daily=daily, calc=calc)


# ----------------------------------------------------------------------------
def run_case(case: dict, policy: dict) -> dict:
    try:
        if case["engine"] == "technical":
            return run_technical(case, policy)
        if case["engine"] == "f12_hold":
            return run_f12_hold(case, policy)
        raise ValueError("unknown engine " + case["engine"])
    except HandStop as stop:
        return dict(status="stop", stop_reason=str(stop))


def pick(result: dict, path: str):
    head, *rest = path.split(".", 1)
    if head == "status":
        return result["status"]
    if head == "trade_count":
        return len(result["trades"])
    if head == "sell_count":
        return sum(t["side"] == "sell" for t in result["trades"])
    if head == "calc":
        return result["calc"].get(rest[0])
    if head == "daily":
        day, field = rest[0].rsplit(".", 1)
        return result["daily"][day][field]
    if head == "orders":
        cid, field = rest[0].split(".", 1)
        o = result["orders"][cid]
        return len(o["attempts"]) if field == "attempt_count" else o[field]
    if head in ("trades", "positions", "sell"):
        idx, field = rest[0].split(".", 1)
        seq = result["sells"] if head == "sell" else result[head]
        return seq[int(idx)][field]
    raise KeyError(path)


def same(expected: str, actual) -> bool:
    if isinstance(actual, bool):
        return expected == ("true" if actual else "false")
    try:
        return abs(D(str(actual)) - D(expected)) <= TOL
    except Exception:
        return str(actual) == expected


def check(result: dict, expected: dict) -> dict:
    out = {}
    for path, want in expected.items():
        try:
            got = pick(result, path)
        except (KeyError, IndexError) as exc:
            got = f"<缺失: {exc}>"
        out[path] = dict(expected=want, computed=jsonable(got), ok=same(want, got))
    return out


def jsonable(x):
    if isinstance(x, D):
        return format(x.normalize(), "f")
    if isinstance(x, dict):
        return {k: jsonable(v) for k, v in x.items() if k != "pos"}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    return x


def main():
    spec = json.loads((HERE / "cases.json").read_text())
    defaults = spec["defaults"]
    answers, failures = [], []
    for raw in spec["cases"]:
        case = merged(raw, defaults)
        entry = dict(id=case["id"], boundary=case["boundary"], engine=case["engine"], title=case["title"])
        variants = [("primary", case.get("hand_policy", {}), case["hand_expected"])]
        if "secondary" in raw:
            variants.append(("secondary", raw["secondary"]["hand_policy"], raw["secondary"]["hand_expected"]))
            entry["secondary_label"] = raw["secondary"]["label"]
        for name, policy, expected in variants:
            result = run_case(case, policy)
            checks = check(result, expected)
            failures += [(case["id"], name, p) for p, c in checks.items() if not c["ok"]]
            entry[name] = dict(policy=policy, result=jsonable(result), hand_expected_check=checks)
        answers.append(entry)
    out = dict(_note="人工标准答案：ledger.py 按旧合同文字独立计算；hand_expected_check 为与 cases.json 手算关键数字的逐项核对。",
               all_hand_expected_ok=not failures, failures=failures, cases=answers)
    (HERE / "hand-answers.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(f"cases={len(answers)} hand_expected_failures={len(failures)}")
    for f in failures:
        print("FAIL", *f)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
