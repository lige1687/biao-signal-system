# -*- coding: utf-8 -*-
"""分腿出场政策的组合级联合模拟（第十六轮）：止盈菜单装进篮子 + 资金循环 + 部分止盈。

问题（用户 2026-09-08 拍板继续）：十五轮的「分腿出场菜单」是单腿分别验证的，
装进同一个篮子后的相互作用（止盈腿停摆期间其余腿怎么再平衡、现金何时回场）
未测；止盈后的资金循环（再入场规则）与部分止盈（卖一半）均未测。本轮一个
实验补齐三件事。

预注册口径（跑前写死，跑后不得改）：

- 篮子两枚（W5=2020-11-16→2026-08-27，5.8 年）：A0 跨资产四 = 000300/
  399006/518880/^IXIC；A2 进取版 = 000300/588000/518880/^IXIC。
- 基础引擎：周投平分至**在场腿**、季度再平衡（仅在场腿之间等权）、费用
  10bp 双边、跨资产按 A 股日历（沿九轮）。
- 止盈菜单（十五轮）：沪深300 腿 +30%；成长腿（创业板/科创50）+50%；
  黄金/纳指腿不设止盈。止盈基准 = 该腿市值/该腿累计成本 −1（部分卖出时
  成本按比例核减）；信号日收盘判定、次日开盘执行。
- 四政策：
  P0    纯季度再平衡（无止盈，九轮冠军，在任基准）；
  P1t   全额止盈 + 时间再入场：触发即清仓该腿进专属现金池、暂停参与买入与
        再平衡；离场满 126 根 K 线（约 6 个月）后用囤积现金一次性重新等权
        进场（买入计费）；
  P1m   全额止盈 + 年线再入场：同 P1t，但再入场条件 = 该腿收盘回到自身
        年线下方（point-in-time）；
  P2    部分止盈：触发只卖 50%（成本核减一半）， proceeds 入中央现金池，
        次周随新钱平分至在场腿，腿不停摆、再平衡照常。
- 判定线（写死）：P1t/P1m/P2 vs P0 各 2 篮 × 2 费率 = 4 格：≥3「有增量」/
  ≤1「判负」/ =2「混合」。预注册预期开放（十五轮证据支持单腿止盈对蓝筹/
  成长有效，但组合层有再平衡冲突与停摆期机会成本，两股力量方向未知）。
- 度量：终值 / 资金加权年化 / 最大回撤 / 止盈触发次数 / 期末滞留现金占比。
- 已知边界：W5 仅 5.8 年且含 2024-09 起大反弹（止盈场景丰富但单段行情）；
  P1 停摆期该腿目标权重归零（其余腿放大）为预注册设计；再入场规则仅测
  两种（不做网格）；沿一~十五轮全部其余边界。
- 结论级别：只检验不决策。禁止买卖指令类词汇。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.timing_backtest.data import load_index_bars

REPO = Path(__file__).resolve().parents[1]
RAW_DIR = REPO / "docs/experiments/raw/dca-joint-policy-2026-09-08"
RAW_DIR.mkdir(parents=True, exist_ok=True)
W5 = ("2020-11-16", "2026-08-27")
FEES = [1.0, 10.0]

BASKETS = {
    "A0_跨资产四": {"000300": 0.30, "399006": 0.50, "518880": None, "^IXIC": None},
    "A2_进取版": {"000300": 0.30, "588000": 0.50, "518880": None, "^IXIC": None},
}
POLICIES = ("P0", "P1t", "P1m", "P2")


def load_full(sym):
    return load_index_bars(sym)


def build(basket):
    opens = closes = ma200 = None
    for s in basket:
        b = load_full(s)
        m = (b["close"].rolling(200, min_periods=100).mean()).rename(s)
        o = b["open"].rename(s).to_frame()
        c = b["close"].rename(s).to_frame()
        opens = o if opens is None else opens.join(o, how="inner")
        closes = c if closes is None else closes.join(c, how="inner")
        ma200 = m.to_frame() if ma200 is None else ma200.join(m, how="inner")
    m = (opens.index >= W5[0]) & (opens.index <= W5[1])
    return opens[m], closes[m], ma200[m]


def period_ends(idx, freq):
    s = pd.Series(np.arange(len(idx)), index=idx)
    keys = ([idx.year, idx.quarter] if freq == "quarterly" else
            [idx.isocalendar().year, idx.isocalendar().week])
    return sorted(int(v) for v in s.groupby(keys).max())


def xirr_signed(flows, end_date, end_value):
    cfs = list(flows) + [(end_date, end_value)]
    t0 = min(d for d, _ in cfs)

    def npv(r):
        return sum(a / (1.0 + r) ** ((d - t0).days / 365.25) for d, a in cfs)

    lo, hi = -0.95, 10.0
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return float("nan")
    for _ in range(200):
        mid = (lo + hi) / 2
        if f_lo * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def run_policy(opens, closes, ma200, tp_menu, policy, fee_bps):
    idx = opens.index
    n = len(idx)
    legs = list(opens.columns)
    L = len(legs)
    o = opens.to_numpy(float)
    c = closes.to_numpy(float)
    m200 = ma200.to_numpy(float)
    f = fee_bps * 1e-4
    ends = period_ends(idx, "weekly")
    base = 1.0 / len(ends)
    inflow = np.zeros(n)
    for p in ends:
        inflow[p] += base
    rebal_days = set(p + 1 for p in period_ends(idx, "quarterly") if p + 1 < n)

    units = np.zeros((n, L))
    cur = np.zeros(L)
    cost = np.zeros(L)                # 各腿累计成本（部分卖出按比例核减）
    active = np.ones(L, dtype=bool)
    suspend_at = {k: None for k in range(L)}
    earmark = np.zeros(L)             # P1：停摆腿专属现金
    central = 0.0                     # 中央池（P2 部分止盈 proceeds + 周度新钱）
    tp_hits = 0
    flows = []
    eq_path = np.empty(n)
    for i in range(n):
        central += inflow[i]
        if i > 0 and inflow[i - 1] > 0:      # 周度执行日（昨日为周末）
            sig = i - 1
            # 1) 止盈检查（P0 不止盈；在场腿、收盘判定）
            for k in range(L):
                if policy == "P0" or not active[k] \
                        or tp_menu[legs[k]] is None or cost[k] <= 0:
                    continue
                leg_val = cur[k] * c[sig, k]
                if leg_val / cost[k] - 1.0 >= tp_menu[legs[k]]:
                    if policy == "P2":
                        sell_u = cur[k] * 0.5
                        central += sell_u * o[i, k] * (1.0 - f)
                        flows.append((idx[i], sell_u * o[i, k] * (1.0 - f)))
                        cur[k] -= sell_u
                        cost[k] *= 0.5
                    else:  # P1t / P1m 全额止盈
                        proceeds = cur[k] * o[i, k] * (1.0 - f)
                        flows.append((idx[i], proceeds))
                        earmark[k] += proceeds
                        cur[k] = 0.0
                        cost[k] = 0.0
                        active[k] = False
                        suspend_at[k] = i
                    tp_hits += 1
            # 2) 再入场（P1t 时间 / P1m 年线）
            if policy in ("P1t", "P1m"):
                for k in range(L):
                    if active[k] or earmark[k] <= 0:
                        continue
                    ok = (policy == "P1t" and i - suspend_at[k] >= 126) or \
                         (policy == "P1m" and np.isfinite(m200[sig, k])
                          and c[sig, k] < m200[sig, k])
                    if ok:
                        cur[k] += (earmark[k] - earmark[k] * f) / o[i, k]
                        cost[k] += earmark[k]
                        flows.append((idx[i], -earmark[k]))
                        earmark[k] = 0.0
                        active[k] = True
            # 3) 周度买入：在场腿平分（中央池全花）
            act = [k for k in range(L) if active[k]]
            if act and central > 0:
                amt = central / len(act)
                for k in act:
                    cur[k] += (amt - amt * f) / o[i, k]
                    cost[k] += amt
                flows.append((idx[i], -central))
                central = 0.0
        if i in rebal_days:
            act = [k for k in range(L) if active[k]]
            if len(act) > 1:
                vals = cur[act] * o[i, act]
                total = float(vals.sum())
                if total > 0:
                    tgt = total / len(act)
                    fee = float(np.abs(vals - tgt).sum()) * f
                    cur[act] = ((total - fee) / len(act)) / o[i, act]
        units[i] = cur
        eq_path[i] = (units[i] * c[i]).sum() + earmark.sum() + central
    final = float(eq_path[-1])
    eq = pd.Series(eq_path, index=idx)
    return {"final": final,
            "xirr": xirr_signed(flows, idx[-1], final),
            "mdd": float(((eq / eq.cummax()) - 1.0).min()),
            "tp_hits": tp_hits,
            "idle_cash_pct": float((earmark.sum() + central) / final)}


def main() -> None:
    out: dict = {"criteria_doc": __doc__, "results": {}, "verdicts": {}}
    for bname, menu in BASKETS.items():
        opens, closes, ma200 = build(menu)
        rec = {"years": round((opens.index[-1] - opens.index[0]).days / 365.25, 1),
               "cells": {}}
        for fee in FEES:
            for pol in POLICIES:
                rec["cells"][f"{pol}_fee{int(fee)}"] = run_policy(
                    opens, closes, ma200, menu, pol, fee)
        out["results"][bname] = rec
        b0 = rec["cells"]["P0_fee10"]
        print(f"[{bname} {rec['years']}y] P0 终值{b0['final']:.3f}/"
              f"年化{b0['xirr']*100:.2f}%/回撤{b0['mdd']*100:.1f}%", flush=True)
        for pol in POLICIES[1:]:
            r = rec["cells"][f"{pol}_fee10"]
            print(f"  {pol}: 终值{r['final']:.3f}"
                  f"({(r['final']/b0['final']-1)*100:+.1f}%) "
                  f"年化{r['xirr']*100:.2f}% 回撤{r['mdd']*100:.1f}% "
                  f"止盈{r['tp_hits']}次 滞留现金{r['idle_cash_pct']*100:.0f}%",
                  flush=True)

    def wins(pol):
        w, d = 0, {}
        for bname in BASKETS:
            for fee in FEES:
                fi = int(fee)
                a = out["results"][bname]["cells"][f"{pol}_fee{fi}"]["final"]
                b = out["results"][bname]["cells"][f"P0_fee{fi}"]["final"]
                win = bool(a > b)
                w += win
                d[f"{bname}|fee{fi}"] = {"a": a, "b": b, "pct": a / b - 1,
                                         "win": win}
        return w, d

    for pol in ("P1t", "P1m", "P2"):
        w, d = wins(pol)
        verdict = ("有增量" if w >= 3 else "判负" if w <= 1 else "混合")
        out["verdicts"][f"J_{pol}"] = {"wins": w, "total": 4,
                                       "verdict": verdict, "detail": d}
        print(f"J_{pol}: {w}/4 -> {verdict}", flush=True)

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True,
                         default=float).encode()
    h = hashlib.sha256(payload).hexdigest()
    (RAW_DIR / "dca_joint_policy_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=float))
    (RAW_DIR / "HASH.txt").write_text(h + "\n")
    print("HASH:", h)


if __name__ == "__main__":
    main()
