"""真实封存记录的数字核验：4个代表账户×三类日期，以及与12条边界对应的定向扫描。

只读旧封存文件（原始名义行情、actions.json、各账户 trades/daily/events/roundtrips/summary/annual），
不调用任何被测资金程序；成交价从原始行情开盘价重取，费用、现金、份数、分红权利和估值全部用十进制重算。
成交日期和份数是被核对的“决定”，按保存记录取用；数量是否按合同算对另在 B01 扫描里重算。

用法：/tmp/bq-venv/bin/python real_accounts.py
只写本目录 account-checks.json 与 real-scans.json。
"""
from __future__ import annotations

import csv
import glob
import json
import os
import sys
from decimal import Decimal as D, ROUND_FLOOR, ROUND_HALF_UP, getcontext
from pathlib import Path

sys.dont_write_bytecode = True
getcontext().prec = 50
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
TECH = REPO / "docs/experiments/raw/research-broad-etf-technical-2026-09-08/execution"
ACC = TECH / "account-results"
F12 = REPO / "docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12"
TOL = D("0.000001")  # 允许误差：1e-6 元（二进制小数累积误差量级；超过即报差）
START, END, INITIAL = "2015-01-01", "2026-06-30", D(100000)
FEE = {"fee10bp": D("0.001"), "fee20bp": D("0.002"), "fee0.001": D("0.001"), "fee0.002": D("0.002")}


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(REPO))


def read_csv(p: Path):
    if os.path.getsize(p) == 0:
        return []
    with open(p, newline="") as fh:
        return list(csv.DictReader(fh))


def load_bars(symbol: str, base: Path):
    return {r["date"]: {k: D(r[k]) for k in ("open", "close")} for r in read_csv(base / f"inputs/bars/{symbol}-nominal.csv")}


ACTIONS = json.loads((TECH / "inputs/actions.json").read_text())
DIVS = {s: [a for a in ACTIONS if a["symbol"] == s and a["type"] == "cash_dividend"] for s in ("sh510300", "sz159915")}
SPLITS = {s: [a for a in ACTIONS if a["symbol"] == s and a["type"] == "split"] for s in ("sh510300", "sz159915")}
BARS = {s: load_bars(s, TECH) for s in ("sh510300", "sz159915")}
QUOTE_DAYS = {s: sorted(BARS[s]) for s in BARS}


def floor_lots(x: D) -> D:
    return D(0) if x <= 0 else (x / 100).to_integral_value(ROUND_FLOOR) * 100


def diff(a, b) -> D:
    return abs(D(str(a)) - D(str(b)))


class Rebuild:
    """从成交决定（日期、方向、份数）和原始行情、行动独立重建一个单产品账户的逐日状态。"""

    def __init__(self, symbol: str, fee: D, trades: list[dict], bars: dict, divs: list[dict], forbidden=()):
        self.s, self.fee, self.bars, self.divs = symbol, fee, bars, divs
        self.trades = sorted(trades, key=lambda t: (t["date"], 0 if t["side"] == "sell" else 1))
        self.forbidden = set(forbidden)

    def units_at(self, d: str) -> D:
        u = D(0)
        for t in self.trades:
            if t["date"] <= d:
                u += D(t["shares"]) if t["side"] == "buy" else -D(t["shares"])
        return u

    def rights(self, a: dict) -> D:
        return self.units_at(a["record_date"])  # 登记日收盘后持有份数

    def mark(self, d: str):
        days = [x for x in self.bars if x <= d and x not in self.forbidden]
        md = max(days)
        m = self.bars[md]["close"]
        for a in self.divs:  # 收盘之后、d 之前生效的除息：旧估值价扣每份现金（IF 第21行）
            if md < a["effective_date"] <= d:
                m -= D(a["cash"])
        return m, md

    def state(self, d: str) -> dict:
        cash, fees, buys, sells = INITIAL, D(0), D(0), D(0)
        for t in self.trades:
            if t["date"] > d:
                continue
            px = self.bars[t["date"]]["open"]
            notional = D(t["shares"]) * px
            f = notional * self.fee
            fees += f
            if t["side"] == "buy":
                cash -= notional + f
                buys += notional
            else:
                cash += notional - f
                sells += notional
        paid = rec = D(0)
        for a in self.divs:
            if a["record_date"] < START:
                continue
            amt = self.rights(a) * D(a["cash"])
            if a["pay_date"] <= d:
                paid += amt
            elif a["effective_date"] <= d:
                rec += amt
        cash += paid
        units = self.units_at(d)
        m, md = self.mark(d)
        mv = units * m
        equity = cash + mv + rec
        return dict(cash=cash, units=units, mark=m, mark_date=md, receivable=rec, market_value=mv, equity=equity,
                    fees=fees, dividends_paid=paid, buy_notional=buys, sell_notional=sells,
                    investment_pnl=equity - INITIAL,
                    pnl_parts=dict(price=sells - buys + mv, dividends=paid + rec, fees=-fees))


def check_rows(saved: dict, rebuilt: dict, fields: dict) -> dict:
    out, worst = {}, D(0)
    for k_saved, k_rebuilt in fields.items():
        dv = diff(saved[k_saved], rebuilt[k_rebuilt])
        worst = max(worst, dv)
        out[k_saved] = dict(saved=saved[k_saved], independent=str(rebuilt[k_rebuilt]), diff=str(dv), ok=dv <= TOL)
    return dict(fields=out, max_diff=str(worst), ok=worst <= TOL)


# ----------------------------------------------------------------------------
# 4 个代表账户
# ----------------------------------------------------------------------------
TECH_PICKS = [
    dict(account="sh510300-A20E-fee10bp", why="A/C/D 1%计划风险；期末仍持有那一笔决定了全部净收益（21,750.69元）；持有期间有分红与失效位换算",
         dates={"普通成交日": ["2015-05-18"], "行动相关日": ["2026-01-16", "2026-01-19", "2026-01-27"], "期末": ["2026-06-30"]}),
    dict(account="sh510300-R1-fee10bp", why="尽量用满现金的诊断参照；除息后、到账前卖出又用现金买回；研究末日当天买入",
         dates={"普通成交日": ["2024-11-25"], "行动相关日": ["2025-06-17", "2025-06-18", "2025-06-20", "2025-06-25", "2025-06-27"], "期末": ["2026-06-30"]}),
    dict(account="sz159915-R1-fee10bp", why="48账户里期末金额最大（588,184.83元）；期末持仓贡献39,323.24元；持仓跨过2021-02-08停牌",
         dates={"普通成交日": ["2023-01-09"], "行动相关日": [], "期末": ["2026-06-30"], "停牌补充（不是公司行动）": ["2021-02-05", "2021-02-08", "2021-02-09"]}),
]
F12_PICK = dict(account="sh510300-breadth_three_tier-fee0.001",
                why="首12账户的另一套冻结程序；除息当天开盘卖出一半，应收仍归账户、到账前不可花",
                dates={"普通成交日": ["2022-02-14"], "行动相关日": ["2023-01-13", "2023-01-16", "2023-01-19"], "期末": ["2026-06-30"]})


def spendable_check(trades, daily, d, bars, fee, state_after) -> dict:
    """当日买入：现金上限按开盘前可花现金（不含未到账应收）计算；同时给出“若应收可花”能买多少，供对照。"""
    prev = daily[max(x for x in daily if x < d)]
    op = bars[d]["open"]
    cash_before = D(prev["cash"])
    for t in trades:  # 同日先卖后买：卖出所得当天可用
        if t["date"] == d and t["side"] == "sell":
            n = D(t["shares"]) * op
            cash_before += n - n * fee
    rec = state_after["receivable"]
    buy = next(t for t in trades if t["date"] == d and t["side"] == "buy")
    return dict(saved_shares=buy["shares"], open=str(op), spendable_cash_before_open=str(cash_before),
                receivable_outstanding=str(rec),
                cash_lot_cap_excluding_receivable=str(floor_lots(cash_before / (op * (1 + fee)))),
                cash_lot_cap_if_receivable_spendable=str(floor_lots((cash_before + rec) / (op * (1 + fee)))))


def tech_account(pick: dict) -> dict:
    acc = pick["account"]
    sym, _, fee_tag = acc.split("-")
    folder = ACC / acc
    trades = read_csv(folder / "trades.csv")
    daily = {r["date"]: r for r in read_csv(folder / "daily.csv")}
    rb = Rebuild(sym, FEE[fee_tag], trades, BARS[sym], DIVS[sym])
    for t in trades:  # 成交价与原始开盘价必须相同
        assert D(t["price"]) == BARS[sym][t["date"]]["open"], (acc, t["date"])
    checks = {}
    for kind, days in pick["dates"].items():
        if not days:
            checks[kind] = dict(status="未覆盖", reason="该产品研究期内 actions.json 没有现金分红或拆分记录（action-coverage.json：159915 现金分红为正式报告连续明确为零；拆分覆盖不完整）。不制造分红案例。")
            continue
        rows = {}
        for d in days:
            saved = daily[d]
            st = rb.state(d)
            c = check_rows(saved, st, {"cash": "cash", f"units_{sym}": "units", f"mark_{sym}": "mark",
                                       "receivable": "receivable", "assets": "market_value", "equity": "equity"})
            identity = D(saved["equity"]) - D(saved["cash"]) - D(saved["assets"]) - D(saved["receivable"])
            funding = D(saved["total_funding"])
            pnl_saved = D(saved["equity"]) - funding
            c.update(mark_date_saved=saved[f"mark_date_{sym}"], mark_date_independent=st["mark_date"],
                     equity_identity_residual=str(identity),
                     external_input=str(funding), investment_pnl_saved=str(pnl_saved),
                     investment_pnl_independent=str(st["investment_pnl"]),
                     capital_identity_diff=str(abs(D(saved["equity"]) - (INITIAL + st["investment_pnl"]))),
                     pnl_parts={k: str(v) for k, v in st["pnl_parts"].items()},
                     trades_that_day=[(t["side"], t["shares"], t["price"]) for t in trades if t["date"] == d])
            if any(t["date"] == d and t["side"] == "buy" for t in trades):
                c["buy_cash_constraint"] = spendable_check(trades, daily, d, BARS[sym], FEE[fee_tag], st)
            c["ok"] = c["ok"] and saved[f"mark_date_{sym}"] == st["mark_date"] and abs(identity) <= TOL \
                and funding == INITIAL and diff(pnl_saved, st["investment_pnl"]) <= TOL
            rows[d] = c
        checks[kind] = rows
    # 期末：总盈亏 = 已卖出各段 + 未卖出各段（不重复相加）；= 汇总 net_gain；= 逐年投资盈亏之和
    rts = json.loads((folder / "roundtrips.json").read_text())
    summ = next(s for s in json.loads((ACC / "summary.json").read_text()) if s["account_id"] == acc)
    annual = [r for r in read_csv(ACC / "annual.csv") if r["account_id"] == acc]
    closed = sum((D(str(p["net_pnl"])) for p in rts if p["closed"]), D(0))
    open_ = sum((D(str(p["net_pnl"])) for p in rts if not p["closed"]), D(0))
    end_state = rb.state(END)
    open_mv = sum((D(str(p["market_value"])) for p in rts if not p["closed"]), D(0))
    bridge = dict(closed_positions_net=str(closed), open_positions_net=str(open_), sum=str(closed + open_),
                  summary_net_gain=summ["net_gain"], annual_sum=str(sum((D(r["investment_pnl"]) for r in annual), D(0))),
                  independent_net_gain=str(end_state["investment_pnl"]),
                  max_diff=str(max(diff(closed + open_, summ["net_gain"]), diff(end_state["investment_pnl"], summ["net_gain"]),
                                   diff(sum((D(r["investment_pnl"]) for r in annual), D(0)), summ["net_gain"]))),
                  end_receivable=summ["receivable"],
                  hypothetical_terminal_sell_fee=str(open_mv * FEE[fee_tag]),
                  equity_after_hypothetical_terminal_sale=str(D(str(summ["last_equity"])) - open_mv * FEE[fee_tag]))
    bridge["ok"] = D(bridge["max_diff"]) <= TOL
    return dict(account=acc, source=rel(folder), engine="48账户冻结引擎（浮点）", why=pick["why"], checks=checks, end_bridge=bridge)


def f12_account(pick: dict) -> dict:
    acc = pick["account"]
    sym = acc.split("-")[0]
    fee = FEE[acc.rsplit("-", 1)[1]]
    folder = F12 / "account-results" / acc
    bars = load_bars(sym, F12)
    acts = json.loads((F12 / "inputs/actions.json").read_text())
    divs = [a for a in acts if a["symbol"] == sym and a["type"] == "cash_dividend"]
    restr = json.loads((F12 / "inputs/dated-restrictions.json").read_text())
    forbidden = [r["date"] for r in restr if r["symbol"] == sym and not r["close_mark_allowed"]]
    trades = read_csv(folder / "trades.csv")
    for t in trades:
        assert D(t["price"]) == bars[t["date"]]["open"], (acc, t["date"])
    rb = Rebuild(sym, fee, trades, bars, divs, forbidden)
    daily = {r["date"]: r for r in read_csv(folder / "daily.csv")}
    checks = {}
    for kind, days in pick["dates"].items():
        rows = {}
        for d in days:
            saved = daily[d]
            st = rb.state(d)
            c = check_rows(saved, st, {"cash": "cash", "units": "units", "mark": "mark", "receivable": "receivable",
                                       "market_value": "market_value", "equity": "equity"})
            identity = D(saved["equity"]) - D(saved["cash"]) - D(saved["market_value"]) - D(saved["receivable"])
            c.update(equity_identity_residual=str(identity), external_input=str(INITIAL),
                     investment_pnl_saved=str(D(saved["equity"]) - INITIAL),
                     investment_pnl_independent=str(st["investment_pnl"]),
                     dividends_received_saved=saved["dividends_received"], dividends_received_independent=str(st["dividends_paid"]),
                     pnl_parts={k: str(v) for k, v in st["pnl_parts"].items()},
                     trades_that_day=[(t["side"], t["shares"], t["price"]) for t in trades if t["date"] == d])
            if any(t["date"] == d and t["side"] == "buy" for t in trades):
                c["buy_cash_constraint"] = spendable_check(trades, daily, d, bars, fee, st)
            c["ok"] = c["ok"] and abs(identity) <= TOL and diff(saved["dividends_received"], st["dividends_paid"]) <= TOL
            rows[d] = c
        checks[kind] = rows
    summ = json.loads((folder / "summary.json").read_text())
    yearly = read_csv(folder / "yearly.csv")
    end_state = rb.state(END)
    mv = D(str(summ["terminal_market_value"]))
    bridge = dict(summary_net_gain=summ["net_gain"], yearly_change_sum=str(sum((D(r["change"]) for r in yearly), D(0))),
                  independent_net_gain=str(end_state["investment_pnl"]),
                  pnl_parts={k: str(v) for k, v in end_state["pnl_parts"].items()},
                  end_receivable=summ["final_receivable"],
                  hypothetical_terminal_sell_fee=str(mv * fee),
                  equity_after_hypothetical_terminal_sale=str(D(str(summ["final_equity"])) - mv * fee))
    bridge["max_diff"] = str(max(diff(bridge["yearly_change_sum"], summ["net_gain"]), diff(end_state["investment_pnl"], summ["net_gain"])))
    bridge["ok"] = D(bridge["max_diff"]) <= TOL
    return dict(account=acc, source=rel(folder), engine="首12冻结程序（十进制）", why=pick["why"], checks=checks, end_bridge=bridge)


def double_count_demo() -> dict:
    """A20E-510300 期末持仓：名义价格贡献+分红−费用=持仓净结果；若改用复权价再加分红，会把分红算两次。"""
    sym, ex = "sh510300", "2026-01-19"
    a = next(x for x in DIVS[sym] if x["effective_date"] == ex)
    prev = max(d for d in BARS[sym] if d < ex)
    factor = (BARS[sym][prev]["close"] - D(a["cash"])) / BARS[sym][prev]["close"]
    shares, entry, last = D(22900), BARS[sym]["2025-08-08"]["open"], BARS[sym][END]["close"]
    fee = entry * shares * D("0.001")
    div = shares * D(a["cash"])
    nominal = (last - entry) * shares
    adjusted = (last - entry * factor) * shares
    q = D("0.01")
    return dict(position="sh510300-A20E-fee10bp / A20E-sh510300-T3", shares=str(shares), entry_open=str(entry), last_close=str(last),
                nominal_price_gain=str(nominal.quantize(q)), dividend=str(div.quantize(q)), buy_fee=str(fee.quantize(q)),
                correct_net=str((nominal + div - fee).quantize(q)), saved_net_pnl="21750.69",
                proportional_adjust_factor=str(factor.quantize(D("0.000001"))),
                adjusted_price_gain_cash_proportional=str(adjusted.quantize(q)),
                wrong_if_adjusted_plus_dividend=str((adjusted + div - fee).quantize(q)),
                overstatement=str((adjusted - nominal).quantize(q)))


# ----------------------------------------------------------------------------
# 定向扫描：每条边界在真实封存记录里是否出现、出现多少次
# ----------------------------------------------------------------------------
def fills_near_limit() -> dict:
    """60个账户（48+12）的全部实际成交：开盘价是否落在或离交易所涨跌停价只差一个价位（0.001元）。"""
    files = [(ACC / a / "trades.csv", a) for a in sorted(p.name for p in ACC.iterdir() if p.is_dir())]
    files += [(F12 / "account-results" / a / "trades.csv", a)
              for a in sorted(p.name for p in (F12 / "account-results").iterdir() if p.is_dir())]
    n, rows = 0, []
    for path, acc in files:
        sym = acc.split("-")[0]
        days = QUOTE_DAYS[sym]
        for t in read_csv(path):
            n += 1
            d = t["date"]
            pc = BARS[sym][days[days.index(d) - 1]]["close"]
            for a in DIVS[sym]:
                if a["effective_date"] == d:
                    pc -= D(a["cash"])
            lim = D("0.2") if sym == "sz159915" and d >= "2020-08-24" else D("0.1")
            up = (pc * (1 + lim)).quantize(D("0.001"), ROUND_HALF_UP)
            dn = (pc * (1 - lim)).quantize(D("0.001"), ROUND_HALF_UP)
            op = BARS[sym][d]["open"]
            if op >= up - D("0.001") or op <= dn + D("0.001"):
                rows.append(dict(account=acc, date=d, side=t["side"], open=str(op), up=str(up), down=str(dn)))
    return dict(fills_checked=n, rows=rows)


def scans() -> dict:
    accounts = sorted(p.name for p in ACC.iterdir() if p.is_dir())
    summary = {s["account_id"]: s for s in json.loads((ACC / "summary.json").read_text())}
    cands = {c["candidate_id"]: c for c in json.loads((ACC / "candidates.json").read_text())}
    out = {}
    # B01/B02：全部买入数量十进制重算；A/C/D 现金与1%风险谁先卡住；已结束A/C/D实际亏损与计划风险之比
    qty_rows, binding, loss_rows = [], {"现金先卡住": 0, "1%风险先卡住": 0, "两者相同": 0}, []
    float_near = []
    for acc in accounts:
        sym, method, tag = acc.split("-")
        fee = FEE[tag]
        trades = read_csv(ACC / acc / "trades.csv")
        if not trades:
            continue
        daily = {r["date"]: r for r in read_csv(ACC / acc / "daily.csv")}
        dates = sorted(daily)
        events = json.loads((ACC / acc / "events.json").read_text())
        paid = {}
        for e in events:
            if e["kind"] == "dividend_paid":
                paid[e["date"]] = paid.get(e["date"], D(0)) + D(str(e["amount"]))
        for t in trades:
            if t["side"] != "buy":
                continue
            prev = daily[dates[dates.index(t["date"]) - 1]]
            cash = D(prev["cash"]) + paid.get(t["date"], D(0))  # 到账日开盘前现金可用
            op = BARS[sym][t["date"]]["open"]
            exact = cash / (op * (1 + fee)) / 100
            cash_lots = floor_lots(cash / (op * (1 + fee)))
            if method in ("R0", "R1"):
                want, kind = cash_lots, None
            else:
                stop, budget = D(t["stop"]), D(t["risk_budget"])
                risk_lots = floor_lots(budget / (op - stop))
                want = min(cash_lots, risk_lots)
                kind = "现金先卡住" if cash_lots < risk_lots else "1%风险先卡住" if risk_lots < cash_lots else "两者相同"
                binding[kind] += 1
                planned = D(t["shares"]) * (op - stop)
                rec = dict(account=acc, date=t["date"], shares=t["shares"], cash_lots=str(cash_lots), risk_lots=str(risk_lots),
                           binding=kind, planned_risk=str(planned.quantize(D("0.01"))),
                           planned_risk_pct_prev_equity=str((planned / D(t["previous_product_equity"]) * 100).quantize(D("0.001"))),
                           invested_pct_prev_equity=str((D(t["shares"]) * op / D(t["previous_product_equity"]) * 100).quantize(D("0.01"))))
                qty_rows.append(rec)
            frac = exact - exact.to_integral_value(ROUND_FLOOR)
            if frac < D("1e-9") or frac > 1 - D("1e-9"):
                float_near.append(dict(account=acc, date=t["date"], exact_lots=str(exact)))
            if D(t["shares"]) != want:
                float_near.append(dict(account=acc, date=t["date"], mismatch=True, saved=t["shares"], independent=str(want)))
        if method not in ("R0", "R1"):
            for p in json.loads((ACC / acc / "roundtrips.json").read_text()):
                if not p["closed"]:
                    continue
                buy = next(t for t in trades if t["side"] == "buy" and t["position_id"] == p["position_id"])
                planned = D(buy["shares"]) * (D(buy["price"]) - D(buy["stop"]))
                loss_rows.append(dict(account=acc, position=p["position_id"], entry=p["entry_date"], exit=p["exit_date"],
                                      net_pnl=round(p["net_pnl"], 2), planned_risk=str(planned.quantize(D("0.01"))),
                                      loss_over_planned=str((D(str(-p["net_pnl"])) / planned).quantize(D("0.01"))) if planned > 0 else None,
                                      net_pnl_pct_prev_equity=str((D(str(p["net_pnl"])) / D(buy["previous_product_equity"]) * 100).quantize(D("0.01")))))
    out["B01_B02_buy_quantity"] = dict(buys_checked=sum(1 for a in accounts for t in read_csv(ACC / a / "trades.csv") if t["side"] == "buy"),
                                       quantity_mismatch_or_float_edge=float_near,
                                       acd_binding_counts=binding, acd_buys=qty_rows, acd_closed_loss_vs_planned=loss_rows)
    # B04：全部买卖尝试的未成交原因；期末未执行订单；首12开盘受限是否真在涨跌停价
    attempt_reasons, pending_end = {}, []
    for acc in accounts:
        for o in json.loads((ACC / acc / "orders.json").read_text()):
            for a in o["attempts"]:
                key = f'{o["side"]}:{a["reason"]}'
                attempt_reasons[key] = attempt_reasons.get(key, 0) + 1
            if o["status"] == "pending_at_end":
                pending_end.append((acc, o["side"], o["signal_date"]))
    f12_limits = []
    prepared = json.loads((F12 / "prepared-signals.json").read_text())
    for acc in sorted(p.name for p in (F12 / "account-results").iterdir() if p.is_dir()):
        sym = acc.split("-")[0]
        fee = FEE[acc.rsplit("-", 1)[1]]
        bars = load_bars(sym, F12)
        days = sorted(bars)
        daily = {r["date"]: r for r in read_csv(F12 / "account-results" / acc / "daily.csv")}
        trades = read_csv(F12 / "account-results" / acc / "trades.csv")
        for r in json.loads((F12 / "account-results" / acc / "rejected.json").read_text()):
            if r["reason"] != "at_open_limit_conservative":
                continue
            prev = days[days.index(r["date"]) - 1]
            pc, op = bars[prev]["close"], bars[r["date"]]["open"]
            lim = D("0.2") if sym == "sz159915" and r["date"] >= "2020-08-24" else D("0.1")
            up = (pc * (1 + lim)).quantize(D("0.001"), ROUND_HALF_UP)
            dn = (pc * (1 - lim)).quantize(D("0.001"), ROUND_HALF_UP)
            pool = prepared["weekly_breadth"] if "breadth" in acc else prepared["breakout"][sym]
            target = D(next(s["target"] for s in pool if s["signal_date"] == r["signal_date"]))
            before = daily[max(d for d in daily if d < r["date"])]
            side = "buy" if target > D(before["invested_weight"]) else "sell"
            nxt = next(t for t in trades if t["date"] > r["date"])
            row = dict(account=acc, date=r["date"], side=side, target=str(target), prev_close=str(pc), open=str(op),
                       exchange_up=str(up), exchange_down=str(dn), at_exchange_limit=op in (up, dn),
                       blocked_side_is_easy_side=(side == "sell" and op == up) or (side == "buy" and op == dn),
                       next_fill=dict(date=nxt["date"], side=nxt["side"], shares=nxt["shares"], price=nxt["price"]))
            if nxt["side"] == side:
                q = D(nxt["shares"])
                sign = 1 if side == "sell" else -1
                first = sign * q * (op - D(nxt["price"])) * (1 - fee if side == "sell" else 1 + fee)
                row["first_order_cash_diff_if_filled_at_blocked_open"] = str(first.quantize(D("0.01")))
                row["first_order_note"] = "只算这一笔成交价差带来的当日现金差；之后资金路径会跟着改变，不是期末财富差，不能与其他差额相加。"
                eq_next = D(daily[nxt["date"]]["equity"])
                final = D(daily[END]["equity"])
                row["equity_on_next_fill_day"] = str(eq_next)
                row["diff_over_equity_on_next_fill_day"] = str((first / eq_next).quantize(D("0.0001")))
                if "breadth" in acc:
                    row["rough_final_equity_if_scaled"] = str((final * (1 + first / eq_next)).quantize(D("1")))
                    row["rough_note"] = "粗估：宽度三档按目标比例调仓，之后路径近似随资金同比例放大；未重跑，不计整百份取整与后续费用差，只用于判断量级与方向。"
            f12_limits.append(row)
    out["B04_unfilled"] = dict(attempt_reason_counts=attempt_reasons, pending_at_end=pending_end,
                               technical_open_limit_rejections=sum(v for k, v in attempt_reasons.items() if "open_limit" in k or "open_unavailable" in k),
                               first12_open_limit_rejections=f12_limits,
                               fills_at_or_one_tick_inside_exchange_limit=fills_near_limit())
    # B05：禁止估值日不在行情里；跨停牌持仓的估值
    sus = []
    for acc in ("sz159915-R1-fee10bp", "sz159915-R0-fee10bp", "sz159915-C1-fee10bp"):
        daily = {r["date"]: r for r in read_csv(ACC / acc / "daily.csv")}
        for d in ("2021-02-05", "2021-02-08", "2021-02-09"):
            sus.append(dict(account=acc, date=d, units=daily[d]["units_sz159915"], mark=daily[d]["mark_sz159915"],
                            mark_date=daily[d]["mark_date_sz159915"]))
    out["B05_suspension"] = dict(quote_2021_02_08_present_technical="2021-02-08" in BARS["sz159915"],
                                 quote_2021_02_08_present_first12="2021-02-08" in load_bars("sz159915", F12),
                                 valuation_rows=sus,
                                 open_attempts_on_2021_02_09=[k for k in attempt_reasons if "known_open_unavailable" in k])
    # B06/B07/B08：除息日与到账日是否有报价；全部账户分红事件的权利份数与金额；拆分
    ev_rows, ev_bad = 0, []
    for acc in accounts:
        sym, _, tag = acc.split("-")
        trades = read_csv(ACC / acc / "trades.csv")
        rb = Rebuild(sym, FEE[tag], trades, BARS[sym], DIVS[sym])
        events = {(e["kind"], e.get("event_id")): e for e in json.loads((ACC / acc / "events.json").read_text()) if "event_id" in e}
        for a in DIVS[sym]:
            if a["record_date"] < START:
                continue
            ev_rows += 1
            want = rb.rights(a) * D(a["cash"])
            got_rec = D(str(events[("dividend_receivable", a["event_id"])]["amount"]))
            got_paid = D(str(events[("dividend_paid", a["event_id"])]["amount"]))
            if diff(want, got_rec) > TOL or diff(want, got_paid) > TOL:
                ev_bad.append((acc, a["event_id"], str(want), str(got_rec), str(got_paid)))
    sold_before_pay = []
    for acc in accounts:
        sym = acc.split("-")[0]
        for p in json.loads((ACC / acc / "roundtrips.json").read_text()):
            for a in DIVS[sym]:
                if p["closed"] and p["entry_date"] <= a["record_date"] and a["effective_date"] <= p["exit_date"] < a["pay_date"]:
                    sold_before_pay.append(dict(account=acc, position=p["position_id"], event=a["event_id"], exit=p["exit_date"],
                                                pay=a["pay_date"], dividend_accrued=p["dividend_accrued"], dividend_paid=p["dividend_paid"]))
    out["B06_B07_B08_actions"] = dict(
        ex_dates_without_quote={s: [a["effective_date"] for a in DIVS[s] if a["effective_date"] >= START and a["effective_date"] not in BARS[s]] for s in DIVS},
        pay_dates_without_quote={s: [a["pay_date"] for a in DIVS[s] if a["pay_date"] >= START and a["pay_date"] not in BARS[s]] for s in DIVS},
        dividend_event_rows_checked=ev_rows, dividend_event_mismatches=ev_bad,
        positions_sold_between_ex_and_pay=sold_before_pay,
        splits_in_window={s: SPLITS[s] for s in SPLITS},
        split_coverage_note="action-coverage.json：两产品拆分正式覆盖都不完整（510300 全期未知；159915 2015/2017/2019/2021/2023–2024 未知），只应用已记录事件。")
    # B09：带行动换算的持仓，从源候选失效位/目标与原始收盘独立重算
    lv, lv_bad = [], []
    for acc in accounts:
        sym = acc.split("-")[0]
        trades = read_csv(ACC / acc / "trades.csv")
        for p in json.loads((ACC / acc / "roundtrips.json").read_text()):
            if not p.get("level_actions"):
                continue
            buy = next(t for t in trades if t["side"] == "buy" and t["position_id"] == p["position_id"])
            c = cands[buy["candidate_id"]]
            stop, tgt = D(str(c["stop"])), None if c.get("target") is None else D(str(c["target"]))
            last_day = p["exit_date"] or END
            used = []
            for a in DIVS[sym]:
                if c["signal_date"] < a["effective_date"] <= last_day:
                    prev = max(d for d in BARS[sym] if d < a["effective_date"])
                    f = (BARS[sym][prev]["close"] - D(a["cash"])) / BARS[sym][prev]["close"]
                    stop *= f
                    tgt = None if tgt is None else tgt * f
                    used.append(a["event_id"])
            dv = max(diff(stop, p["stop"]), D(0) if tgt is None else diff(tgt, p["target"]))
            row = dict(account=acc, position=p["position_id"], source_stop=c["stop"], saved_stop=p["stop"], independent_stop=str(stop),
                       events=used, saved_events=p["level_actions"], max_diff=str(dv))
            lv.append(row)
            if dv > D("1e-9") or used != p["level_actions"]:
                lv_bad.append(row)
    out["B09_level_conversion"] = dict(positions_checked=len(lv), mismatches=lv_bad, rows=lv)
    # B10/B12：期末持仓、期末应收、假想卖出费用；已卖出+未卖出=总盈亏
    ends = []
    for acc in accounts:
        tag = acc.split("-")[2]
        rts = json.loads((ACC / acc / "roundtrips.json").read_text())
        opens = [p for p in rts if not p["closed"]]
        s = summary[acc]
        closed = sum((D(str(p["net_pnl"])) for p in rts if p["closed"]), D(0))
        open_ = sum((D(str(p["net_pnl"])) for p in opens), D(0))
        mv = sum((D(str(p["market_value"])) for p in opens), D(0))
        ends.append(dict(account=acc, open_positions=len(opens), end_receivable=s["receivable"], open_market_value=str(mv),
                         closed_net=str(closed.quantize(D("0.01"))), open_net=str(open_.quantize(D("0.01"))),
                         bridge_diff=str(diff(closed + open_, s["net_gain"])),
                         hypothetical_sell_fee=str((mv * FEE[tag]).quantize(D("0.01"))),
                         hypothetical_fee_pct_of_net_gain=None if s["net_gain"] == 0 else str((mv * FEE[tag] / D(str(s["net_gain"])) * 100).quantize(D("0.01")))))
    out["B10_B12_terminal"] = dict(accounts=ends, max_bridge_diff=str(max(D(e["bridge_diff"]) for e in ends)),
                                   accounts_with_open_positions=[e["account"] for e in ends if e["open_positions"]],
                                   any_end_receivable=any(e["end_receivable"] for e in ends))
    # B11：每户每日外部投入恒为10万、无追加
    fund_bad = []
    for acc in accounts:
        for r in read_csv(ACC / acc / "daily.csv"):
            if D(r["total_funding"]) != INITIAL or D(r["deposit"]) != 0:
                fund_bad.append((acc, r["date"]))
                break
    out["B11_external_input"] = dict(accounts=len(accounts), rows_with_funding_not_100000_or_deposit=fund_bad)
    # B03：同一账户同一天既卖又买、买入当天卖出、持仓期间又买入
    same_day, tplus, overlap = [], [], []
    for acc in accounts:
        trades = read_csv(ACC / acc / "trades.csv")
        by_day = {}
        for t in trades:
            by_day.setdefault(t["date"], set()).add(t["side"])
        same_day += [(acc, d) for d, s in by_day.items() if s == {"buy", "sell"}]
        for p in json.loads((ACC / acc / "roundtrips.json").read_text()):
            if p["closed"] and p["exit_date"] <= p["entry_date"]:
                tplus.append((acc, p["position_id"]))
        rts = sorted(json.loads((ACC / acc / "roundtrips.json").read_text()), key=lambda p: p["entry_date"])
        for a, b in zip(rts, rts[1:]):
            if a["exit_date"] is None or b["entry_date"] <= a["exit_date"]:
                overlap.append((acc, a["position_id"], b["position_id"]))
    out["B03_same_day_order"] = dict(same_day_buy_and_sell=same_day, sell_on_or_before_entry=tplus,
                                     overlapping_positions=overlap,
                                     rejected_as_position_exists_or_pending_exit=sum(
                                         1 for acc in accounts for o in json.loads((ACC / acc / "orders.json").read_text())
                                         if o["status"] == "rejected" and o["reason"] in ("position_exists", "pending_exit")))
    out["input_integrity"] = input_integrity()
    return out


def input_integrity() -> dict:
    """本快照的输入文件与收益前锁的指纹是否一致；不一致时检查是否只是换行符（CRLF→LF）差别。"""
    import hashlib

    def h(b: bytes) -> str:
        return hashlib.sha256(b).hexdigest()

    rows = []
    tech_lock = json.loads((TECH / "source-lock.json").read_text())["files"]
    locked = [(p.split("lei-signal-lab/", 1)[1], v) for p, v in tech_lock.items()]
    locked += [(x["path"], x["sha256"]) for x in json.loads((F12 / "source-lock.json").read_text())["files"]]
    for path, want in locked:
        b = (REPO / path).read_bytes()
        now = h(b)
        crlf = h(b.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        rows.append(dict(path=path, locked=want, current=now, match=now == want,
                         match_after_lf_to_crlf=None if now == want else crlf == want,
                         current_has_crlf=b"\r\n" in b))
    return dict(files=len(rows), exact_match=sum(r["match"] for r in rows),
                mismatches=[r for r in rows if not r["match"]],
                note="收益前锁记录的是原机器上的字节；本快照里不一致的文件若把LF换回CRLF后指纹相同，说明只是换行符被改写、数值内容未变。")


def main():
    accounts = [tech_account(p) for p in TECH_PICKS] + [f12_account(F12_PICK)]
    demo = double_count_demo()
    result = dict(_note="4个代表账户×三类日期的独立数字核验；允许误差1e-6元；成交价、费用、现金、份数、分红权利与估值均由原始行情和行动独立重算。",
                  tolerance_cny=str(TOL), accounts=accounts, no_double_count_demo=demo)
    (HERE / "account-checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str) + "\n")
    sc = scans()
    (HERE / "real-scans.json").write_text(json.dumps(sc, ensure_ascii=False, indent=1, default=str) + "\n")
    for a in accounts:
        flags = []
        for kind, rows in a["checks"].items():
            if isinstance(rows, dict) and "status" in rows:
                flags.append(f"{kind}=未覆盖")
                continue
            for d, c in rows.items():
                flags.append(f"{d}:{'ok' if c['ok'] else 'DIFF'}({c['max_diff']})")
        print(a["account"], " ".join(flags), "end_bridge", a["end_bridge"]["ok"], a["end_bridge"]["max_diff"])
    print("double-count demo overstatement", demo["overstatement"])
    print("B01 buys", sc["B01_B02_buy_quantity"]["buys_checked"], "edge/mismatch", len(sc["B01_B02_buy_quantity"]["quantity_mismatch_or_float_edge"]),
          "binding", sc["B01_B02_buy_quantity"]["acd_binding_counts"])
    print("B04", sc["B04_unfilled"]["attempt_reason_counts"], "pending_end", sc["B04_unfilled"]["pending_at_end"],
          "f12 limits", [(x["date"], x["at_exchange_limit"]) for x in sc["B04_unfilled"]["first12_open_limit_rejections"]])
    print("B06", sc["B06_B07_B08_actions"]["ex_dates_without_quote"], "events", sc["B06_B07_B08_actions"]["dividend_event_rows_checked"],
          "bad", sc["B06_B07_B08_actions"]["dividend_event_mismatches"], "sold ex..pay", len(sc["B06_B07_B08_actions"]["positions_sold_between_ex_and_pay"]))
    print("B09", sc["B09_level_conversion"]["positions_checked"], "bad", len(sc["B09_level_conversion"]["mismatches"]))
    print("B10", sc["B10_B12_terminal"]["max_bridge_diff"], sc["B10_B12_terminal"]["accounts_with_open_positions"])
    print("B11", sc["B11_external_input"])
    ii = sc["input_integrity"]
    print("input_integrity", ii["exact_match"], "/", ii["files"], [(m["path"].rsplit("/", 1)[1], m["match_after_lf_to_crlf"]) for m in ii["mismatches"]])


if __name__ == "__main__":
    main()
