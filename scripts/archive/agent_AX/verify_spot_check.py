# -*- coding: utf-8 -*-
"""AX 独立数值抽查：用另一套朴素实现复算抽查事件的 vdiff / dd_exec_diff。

与主脚本 scripts/agent_AX/staged_exit_validation.py 无共享计算代码（仅共享
数据加载）：信号档位手写（不调 ladder_target）、事件/作废/批次逻辑独立重写、
账户用 flat-list 持仓簿（qty/cash 逐日演化，主脚本是 dict-state 闭包）。
首版曾用"每日开盘隐式再平衡"的闭式乘子，该式丢失隔夜段（c[i-1]→o[i]），
对全仓持有段系统性失真，已在抽查对不上时定位并废弃——正确口径必须跟踪
持仓数量。抽查 8 组（事件×档位），逐项对照主脚本 JSON，容差 1e-4pp，0 处
不符为通过。
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from lei_signal.timing_backtest.data import (  # noqa: E402
    align_index_breadth,
    load_breadth,
    load_index_bars,
)

FEE = 10.0e-4
LOW, HIGH, MT = 30.0 + 40.0 / 3.0, 30.0 + 80.0 / 3.0, 21  # 档位线=43.333…/56.666…（_fixed_edges 精确值）

al = align_index_breadth(load_index_bars("399006"), load_breadth("cn_all"))
b200 = al["b200"].tolist()
o = al["open"].to_numpy(float)
c = al["close"].to_numpy(float)
dates = [d.strftime("%Y-%m-%d") for d in al.index]
pos = {d: i for i, d in enumerate(dates)}


def tier(b):  # 手写档位（NaN→0.0，引擎 searchsorted 行为的显式复刻）
    if b != b:  # NaN
        return 0.0
    return 1.0 if b <= LOW else (0.5 if b <= HIGH else 0.0)


sig = [tier(b) for b in b200]
execw = [math.nan] + sig[:-1]  # T 收盘信号 → T+1 开盘执行


def book(i, w_new, qty, cash, w_old):
    """i 开盘把决策权重调到 w_new：按开盘价成交、费=|Δw|×开盘权益。"""
    eq_open = qty * o[i] + cash
    delta = w_new - w_old
    if abs(delta) < 1e-12:
        return qty, cash, w_old, 0.0
    fee = eq_open * abs(delta) * FEE
    eq = eq_open - fee
    return eq * w_new / o[i], eq * (1.0 - w_new), w_new, fee


def run(i0, months):
    tgt = execw[i0]
    assert execw[i0 - 1] == 1.0 and tgt < 1.0
    end = min(len(dates) - 1, i0 + 376)
    last = i0 + MT * months
    if last > end:
        return None
    out = {}
    for kind in ("base", "staged"):
        qty, cash, w = 1.0 / o[i0], 0.0, 1.0
        done = kind == "base"
        cancelled = False
        t_conv = i0 if kind == "base" else last
        eq = {}
        for i in range(i0, end + 1):
            if i == i0:
                if kind == "base":
                    qty, cash, w, _ = book(i, tgt, qty, cash, w)
            elif not done:
                if execw[i] != tgt:  # 任何档位变化 → 作废对齐
                    qty, cash, w, _ = book(i, execw[i], qty, cash, w)
                    done, cancelled, t_conv = True, True, i
                elif (i - i0) % MT == 0 and i <= last:  # 批次日
                    qty, cash, w, _ = book(i, w - (1.0 - tgt) / months, qty, cash, w)
                    if i == last:
                        done = True
            else:
                if execw[i] != w:
                    qty, cash, w, _ = book(i, execw[i], qty, cash, w)
            eq[i] = qty * c[i] + cash
        out[kind] = (eq, t_conv, cancelled)
    eb, tb, _ = out["base"]
    es, ts, cancelled = out["staged"]
    vdiff = (es[ts] / eb[ts] - 1.0) * 100.0

    def mdd(seq):
        peak, m = -1e18, 0.0
        for x in seq:
            peak = max(peak, x)
            m = min(m, x / peak - 1.0)
        return m

    dd = (mdd([es[i] for i in range(i0, last + 1)]) - mdd([eb[i] for i in range(i0, last + 1)])) * 100.0
    return vdiff, dd, cancelled


CHECKS = [
    ("2024-10-08", 1), ("2015-07-14", 3), ("2013-01-08", 3), ("2017-04-06", 1),
    ("2022-02-09", 6), ("2023-11-14", 3), ("2019-08-23", 6), ("2025-04-11", 1),
]

ref = json.load(open(REPO / "docs/experiments/raw/agent_AX/staged_exit_results.json"))
bad = 0
for ev_date, M in CHECKS:
    res = run(pos[ev_date], M)
    ent = ref["per_event"][ev_date]["variants"][f"M{M}"]
    v_ok = abs(res[0] - ent["vdiff_pp"]) < 1e-4
    d_ok = abs(res[1] - ent["dd_diff_pp"]) < 1e-4
    c_ok = res[2] == ent["cancelled"]
    ok = v_ok and d_ok and c_ok
    bad += 0 if ok else 1
    print(f"{ev_date} M{M}: vdiff {res[0]:+.4f} vs {ent['vdiff_pp']:+.4f} | "
          f"dd {res[1]:+.4f} vs {ent['dd_diff_pp']:+.4f} | cancel {res[2]} vs {ent['cancelled']} "
          f"-> {'OK' if ok else 'MISMATCH'}")
print("mismatches:", bad)
sys.exit(1 if bad else 0)
