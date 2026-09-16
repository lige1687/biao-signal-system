# -*- coding: utf-8 -*-
"""语义九前置验证：分批执行叠加现有信号——基础事件研究（预注册版）。

任务书：docs/experiments/prompt-AE-staged-entry-precheck-2026-09-03.md
本脚本为唯一计算入口，跑前写死全部规则与判定线，跑后不回改（如需改动须在
报告中如实登记为"事后变更"）。

===============================================================================
一、预注册：信号与数据（全部复用已验证规则，不发明新信号）
===============================================================================
- 信号：创业板三档冠军（宽度全栈组 31 轮归档通过项），
  来源 docs/experiments/raw/kuandu-quanzhan/champion_cyb.json：
  symbol=399006, ladder, indicator=b200, n_bands=3, direction=contrarian,
  low_edge=30, high_edge=70, gamma=1.0, min_trade=0.05, fee_bps=10。
  档位线 43.3/56.7（30+40/3, 30+80/3）：B200<=43.3→仓位1.0；43.3<B200<=56.7→0.5；
  B200>56.7→0.0。引擎 src/lei_signal/timing_backtest/strategies.py::ladder_target。
- 执行口径：T 日收盘信号 → T+1 开盘执行（与归档统一口径一致，无未来函数）。
- 行情/宽度：~/.lei_signal_lab/cache/timing/ 399006.parquet + breadth_cn_all.parquet
  （全A宽度，幸存者偏差声明见 data.py）。样本窗 2010-06→2026-08-27。
- 费率：每次调仓按换手名义额 10bp（champion_cyb.json fee_bps=10.0；
  归档摘要"统一口径：费用 10bp 双边"）。换手次数与费用单列。
  全部结论口径为净费（费用不计入的毛收益结论无效）。

===============================================================================
二、预注册：事件定义与清单
===============================================================================
- 原始上穿：执行仓位序列 exec_w(t)=signal(t-1) 从 <1.0 上穿到 ==1.0 的交易日
  （此前仓位 prev_w ∈ {0.0, 0.5}），事件执行日 = 上穿当日（开盘可成交日）。
- 簇合并（主口径）：B200 为 200 日均线宽度，自相关极高，43.3 线附近会连续抖动；
  与前一保留事件间隔 < 40 个交易日的上穿视为同一决策簇的抖动，并入前一簇
  （不单独成事件）。40 日为预注册固定值，不扫描。全部 78 个原始上穿仍完整登记。
- 每事件登记：执行日、信号日、prev_w、信号日 B200 读数、事件类型分组标签。

===============================================================================
三、预注册：事件分组（决定结论能否推广，跑前写死）
===============================================================================
- 极端底部组：触发信号日前 120 个交易日内 B200 曾 <= 20
  （锚定 CROSS-GROUP-SYNTHESIS-2026-09-01 历史教训"双≤20 应 12 个月分批建仓"
  中的 B200≤20 那条线；120 日≈半年，覆盖一次完整宽度崩塌）。
- 普通加仓组：其余事件。
- 辅助登记（不参与判定）：触发前 120 日内出现"同日双≤20"（B20 与 B200 同日
  均<=20）的事件数。

===============================================================================
四、预注册：执行方式（小邻域，非参数优化）
===============================================================================
基准 B0：事件执行日开盘一次性到位（目标权重 1.0）。
阶梯式（9 档 = 批数{3,4,5} × 间隔{5,10,20} 交易日）：批 k 于执行日后第
  (k-1)*g 个交易日开盘执行，每批把目标权重提高 1/n（等分，引擎目标权重制：
  每批按开盘价再平衡到累计目标权重，费用按 |Δw|×名义×10bp）。
定投式（2 档）：
  D1 每日一份：连续 60 个交易日每日目标权重 +1/60（约 3 个月，"几十份"下沿）；
  W1 每周一份：每 5 个交易日目标权重 +1/52，共 52 批 ≈ 12 个月（对齐教训
  原文"12 个月分批建仓"）。
反向规则（任务书原文写死）：分批期间任意交易日，前日收盘信号目标仓位
  < 当前已建权重 → 当日开盘减仓至信号目标，剩余批次作废（程序终止）。
程序终止后账户此后完全跟随信号目标（信号升回 1.0 则加回 1.0，信号驱动而非
批次重启）；基准全程同样遵守信号优先（信号降档即减），三种方式信号处理一致，
差异只来自建仓节奏。
死区说明：champion 配置 min_trade=0.05 是信号档位间的调仓死区（档差 0.5 远大于
死区，几乎不起作用）；本研究的分批批次是计划内动作，不受死区吞并（否则每日
定投 1/60<0.05 的批次会被全部忽略，测的就不是分批本身）。

===============================================================================
五、预注册：度量（跑前写死）
===============================================================================
每事件、每执行方式记录：
1. ret_60 / ret_120：建仓完成日（末批执行日；基准=事件执行日）权益与其后
   第 60/120 个交易日权益之比 -1。程序被作废的事件无建仓完成日 → NaN 单列；
   窗口超出数据末尾 → NaN。净费口径。
2. cost_gap：建仓期加权平均买入成本（含买入费）相对基准成本（执行日开盘价
   含费）之差（avg_cost/base_cost-1），负=成本更低。
3. dd_build：建仓期（执行日→完成日或作废日）每日收盘权益最大回撤。
4. dd_aligned / ret_aligned_180：统一窗口口径——事件执行日起 180 个交易日的
   权益比与区间最大回撤（三种方式同起终点，账户全程信号优先）。尾部事件
   窗口不足 180 日 → NaN。
5. n_trades（建仓期调仓次数）、turnover（|Δw| 累计）、fee_paid（费用/初始权益）、
   terminated（是否被信号作废）、complete_date。

===============================================================================
六、预注册：判定线（跑前写死，三选一）
===============================================================================
对两个子方向（阶梯式、定投式）分别独立判定：
- 样本量下限：配对样本（该方式与基准均有 ret_120）>= 12；分组判定各组 >= 4；
  不满足 → 证据不足。
- 作废率上限：该子方向全部档位的事件作废率中位数 > 40% → 证据不足
  （度量被作废规则主导，不可比）。
- "有实质改善"须两维度同时达标（以该子方向全部档位的中位数档位为代表，
  且要求全部档位 ret_120 改善中位数同号 >0，防止挑档位）：
  * 收益维度：ret_120 配对改善（分批-基准）中位数 >= +1.5pp 且改善>0 事件
    占比 >= 55%；
  * 回撤维度：dd_build 配对改善（基准-分批）中位数 >= +3pp 且改善>0 事件
    占比 >= 55%。
- 仅一维度达标或全部不达标 → "无实质增量"（明确结论，非失败）。
- 分组结论单列：极端底部组与普通加仓组分别给出上述统计；推广表述只看
  普通组是否也达标。
判定枚举：有实质改善 / 无实质增量 / 证据不足。

===============================================================================
七、预注册：敏感性（只登记，不参与判定）
===============================================================================
- 机械不中断：忽略反向作废、纯机械跑完全部批次（阶梯中位档 4×10 与定投两档）。
- 全原始事件：不做 40 日簇合并的 78 个事件，同样中位档位。
- 阶梯档位间一致性：9 档逐档统计（看方向稳定性，非选优）。

===============================================================================
八、双跑哈希
===============================================================================
PYTHONHASHSEED=0 与 42 各完整跑一遍，输出哈希必须一致（事件清单+全部度量+
汇总统计的规范 JSON sha256）。
===============================================================================
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from lei_signal.timing_backtest.data import (  # noqa: E402
    align_index_breadth,
    load_breadth,
    load_index_bars,
)
from lei_signal.timing_backtest.strategies import LadderParams, ladder_target  # noqa: E402

# ---------------- 预注册常量（与 docstring 一致，跑前写死） ----------------
FEE_BPS = 10.0            # champion_cyb.json；每次调仓按 |Δw| 名额 × 10bp
MIN_TRADE = 0.05          # champion_cyb.json
CLUSTER_GAP = 40          # 交易日，簇合并间隔
EXTREME_LOOKBACK = 120    # 交易日
EXTREME_B200_LINE = 20.0  # B200 触及线
N_HOLD = (60, 120)        # 建仓完成后持有窗口
ALIGNED_WIN = 180         # 统一窗口交易日
RET120_LINE_PP = 1.5      # 收益改善线（百分点）
DD_LINE_PP = 3.0          # 回撤改善线（百分点）
POS_RATE_LINE = 0.55      # 改善为正的事件占比线
MIN_PAIRS_TOTAL = 12      # 配对样本下限
MIN_PAIRS_GROUP = 4       # 分组配对下限
TERM_RATE_LINE = 0.40     # 作废率上限
LADDER_GRID = [(n, g) for n in (3, 4, 5) for g in (5, 10, 20)]
DCA_PLANS = {"dca_daily60": [("every", 1, 60)], "dca_weekly52": [("every", 5, 52)]}
SENS_MODES = ["ladder_4x10", "dca_daily60", "dca_weekly52"]  # 敏感性口径

RAW_DIR = REPO / "docs/experiments/raw/agent-AE-staged-entry"

# ---------------- 数据与信号 ----------------
al = align_index_breadth(load_index_bars("399006"), load_breadth("cn_all"))
ladder = LadderParams(
    indicator="b200", n_bands=3, direction="contrarian",
    low_edge=30.0, high_edge=70.0, gamma=1.0,
)
sig = ladder_target(al["b200"], ladder)          # T 日收盘目标仓位
exec_w = sig.shift(1)                            # 当日开盘执行的仓位（前日信号）
sig_target = sig.reindex(al.index)

opens = al["open"].to_numpy(dtype=float)
closes = al["close"].to_numpy(dtype=float)
b200 = al["b200"]
dates = al.index
pos_of = {d: i for i, d in enumerate(dates)}

# ---------------- 事件清单 ----------------
raw_events: list[dict] = []
vals = exec_w.to_numpy(dtype=float)
for i in range(1, len(vals)):
    w, p = vals[i], vals[i - 1]
    if not np.isnan(p) and not np.isnan(w) and p < 1.0 and w == 1.0:
        lo = max(0, i - 1 - EXTREME_LOOKBACK)
        raw_events.append(
            {
                "exec_date": dates[i].strftime("%Y-%m-%d"),
                "signal_date": dates[i - 1].strftime("%Y-%m-%d"),
                "prev_w": float(p),
                "b200_at_signal": round(float(b200.iloc[i - 1]), 4),
                "b200_min120": round(float(b200.iloc[lo:i].min()), 4),
            }
        )

kept: list[dict] = []
last_i = None
for ev in raw_events:
    i = pos_of[pd.Timestamp(ev["exec_date"])]
    if last_i is None or i - last_i >= CLUSTER_GAP:
        ev2 = dict(ev)
        ev2["cluster_main"] = True
        ev2["extreme_bottom"] = ev["b200_min120"] <= EXTREME_B200_LINE
        kept.append(ev2)
        last_i = i
    else:
        ev2 = dict(ev)
        ev2["cluster_main"] = False
        ev2["extreme_bottom"] = ev["b200_min120"] <= EXTREME_B200_LINE
        kept.append(ev2)

main_events = [e for e in kept if e["cluster_main"]]

# 辅助登记：同日双≤20 出现在触发前 120 日内的事件数
b20_all = load_breadth("cn_all")["b20"].reindex(al.index)


def _dl20(e):
    i = pos_of[pd.Timestamp(e["signal_date"])]
    lo = max(0, i - EXTREME_LOOKBACK)
    w = (b200.iloc[lo:i] <= EXTREME_B200_LINE) & (b20_all.iloc[lo:i] <= EXTREME_B200_LINE)
    return bool(w.any())


double_le20 = int(sum(1 for e in main_events if _dl20(e)))

# ---------------- 执行计划生成 ----------------


def ladder_plan(n: int, gap: int):
    """批 k（0 起）执行日偏移 = k*gap 个交易日；每批权重 +1/n。"""
    return [(k * gap, 1.0 / n) for k in range(n)]


def dca_plan(step: int, batches: int):
    return [(k * step, 1.0 / batches) for k in range(batches)]


PLANS: dict[str, list] = {}
for n, g in LADDER_GRID:
    PLANS[f"ladder_{n}x{g}"] = ladder_plan(n, g)
for key, spec in DCA_PLANS.items():
    step, batches = spec[0][1], spec[0][2]
    PLANS[key] = dca_plan(step, batches)
PLANS["baseline"] = None  # 一次性

# ---------------- 单事件单方式模拟 ----------------


def simulate_event(exec_date: pd.Timestamp, plan: list | None, mechanical: bool = False):
    """返回 dict：账户从执行日开盘起，目标权重制建仓，信号优先（除非 mechanical）。

    mechanical=True 时忽略反向作废（批次照跑），但建仓完成后仍跟随信号。
    """
    i0 = pos_of[exec_date]
    n_days = len(dates)
    fee_rate = FEE_BPS * 1e-4
    plan_map = {}
    if plan is not None:
        for off, dw in plan:
            j = i0 + off
            if j < n_days:
                plan_map.setdefault(j, 0.0)
                plan_map[j] += dw
    if plan is not None and not plan_map:
        return None  # 全部批次超出数据范围，无法模拟
    last_batch_idx = max(plan_map) if plan_map else i0
    terminated_at = None
    trades = 0
    turnover = 0.0
    fee_paid = 0.0
    cash, units, w = 1.0, 0.0, 0.0
    equity_path = {}  # i -> (close equity, weight)
    end_i = min(n_days - 1, i0 + ALIGNED_WIN + 260)  # 覆盖最长建仓+持有
    bought_shares = []  # (units_added, value_inc_fee)

    for i in range(i0, end_i + 1):
        # 开盘：信号优先（前日收盘信号）
        sig_prev = sig_target.iloc[i - 1] if i - 1 >= 0 else np.nan
        if not mechanical and not np.isnan(sig_prev) and sig_prev < w - 1e-9:
            # 减仓至信号目标；分批程序作废
            desired = float(sig_prev)
            delta = desired - w
            eq_open = cash + units * opens[i]
            fee = eq_open * abs(delta) * fee_rate
            eq_after = eq_open - fee
            units = eq_after * desired / opens[i]
            cash = eq_after - eq_after * desired
            trades += 1
            turnover += abs(delta)
            fee_paid += fee
            w = desired
            if plan is not None and terminated_at is None and i <= last_batch_idx:
                terminated_at = i
                plan_map = {k: v for k, v in plan_map.items() if k <= i}
        # 开盘：批次执行
        if plan is None:
            if i == i0 and w < 1.0 - 1e-9:
                delta = 1.0 - w
                eq_open = cash + units * opens[i]
                fee = eq_open * abs(delta) * fee_rate
                eq_after = eq_open - fee
                units = eq_after * 1.0 / opens[i]
                cash = 0.0
                trades += 1
                turnover += abs(delta)
                fee_paid += fee
                bought_shares.append((units, eq_after))
                w = 1.0
        elif i in plan_map and (mechanical or terminated_at is None):
            desired = min(1.0, w + plan_map[i])
            delta = desired - w
            eq_open = cash + units * opens[i]
            fee = eq_open * abs(delta) * fee_rate
            eq_after = eq_open - fee
            units_new = eq_after * desired / opens[i]
            add_units = units_new - units
            if add_units > 0:
                bought_shares.append((add_units, add_units * opens[i] + fee))
            units = units_new
            cash = eq_after - eq_after * desired
            trades += 1
            turnover += abs(delta)
            fee_paid += fee
            w = desired
        # 开盘：信号升回（跟随信号，非批次）
        if not np.isnan(sig_prev) and sig_prev > w + 1e-9 and (
            plan is None or i > last_batch_idx or terminated_at is not None
        ):
            desired = float(sig_prev)
            delta = desired - w
            eq_open = cash + units * opens[i]
            fee = eq_open * abs(delta) * fee_rate
            eq_after = eq_open - fee
            units = eq_after * desired / opens[i]
            cash = eq_after - eq_after * desired
            trades += 1
            turnover += abs(delta)
            fee_paid += fee
            w = desired
        equity_path[i] = (cash + units * closes[i], w)

    # 建仓完成日
    if plan is None:
        complete_i = i0
    else:
        # 建仓期内被信号作废 → 无完成日；建仓完成后才发生的减仓不影响完成日
        complete_i = None if (terminated_at is not None and terminated_at <= last_batch_idx) else last_batch_idx
        if complete_i is not None and complete_i > end_i:
            complete_i = None

    def eq_at(i: int | None) -> float:
        if i is None or i not in equity_path:
            return float("nan")
        return equity_path[i][0]

    def ret_n(complete: int | None, n: int) -> float:
        if complete is None:
            return float("nan")
        j = complete + n
        if j > end_i or j not in equity_path:
            return float("nan")
        return eq_at(j) / eq_at(complete) - 1.0

    def max_dd(path_ids: list[int]) -> float:
        eq = [equity_path[i][0] for i in path_ids if i in equity_path]
        if not eq:
            return float("nan")
        peak, mdd = -np.inf, 0.0
        for v in eq:
            peak = max(peak, v)
            mdd = min(mdd, v / peak - 1.0)
        return mdd

    build_end = complete_i if complete_i is not None else (terminated_at if terminated_at is not None else i0)
    dd_build = max_dd(list(range(i0, build_end + 1)))
    aligned_ids = list(range(i0, min(end_i, i0 + ALIGNED_WIN) + 1))
    dd_aligned = max_dd(aligned_ids)
    ret_aligned = eq_at(min(end_i, i0 + ALIGNED_WIN)) / 1.0 - 1.0

    total_buy_value = sum(v for _, v in bought_shares)
    avg_cost = float("nan")
    if total_buy_value > 0:
        total_units_bought = sum(u for u, _ in bought_shares)
        avg_cost = total_buy_value / total_units_bought
    base_cost = opens[i0] * (1.0 + fee_rate)
    cost_gap = avg_cost / base_cost - 1.0 if avg_cost == avg_cost else float("nan")

    return {
        "ret_60": round(ret_n(complete_i, N_HOLD[0]), 6),
        "ret_120": round(ret_n(complete_i, N_HOLD[1]), 6),
        "cost_gap": round(float(cost_gap), 6),
        "dd_build": round(float(dd_build), 6),
        "ret_aligned_180": round(float(ret_aligned), 6),
        "dd_aligned_180": round(float(dd_aligned), 6),
        "n_trades": int(trades),
        "turnover": round(float(turnover), 4),
        "fee_paid": round(float(fee_paid), 6),
        "terminated": bool(terminated_at is not None and (plan is not None) and terminated_at <= last_batch_idx),
        "complete_date": dates[complete_i].strftime("%Y-%m-%d") if complete_i is not None and complete_i in equity_path else None,
    }


# ---------------- 主口径：簇合并主事件 × 全部方式 ----------------
results: dict[str, dict] = {}
for ev in main_events:
    exec_date = pd.Timestamp(ev["exec_date"])
    row: dict[str, dict] = {}
    for mode, plan in PLANS.items():
        row[mode] = simulate_event(exec_date, plan)
    # 敏感性：机械不中断
    for mode in SENS_MODES:
        row[mode + "|mech"] = simulate_event(exec_date, PLANS[mode], mechanical=True)
    results[ev["exec_date"]] = row

# 敏感性：全原始事件（不合并），中位档位
raw_results: dict[str, dict] = {}
for ev in raw_events:
    exec_date = pd.Timestamp(ev["exec_date"])
    row = {"baseline": simulate_event(exec_date, None)}
    for mode in SENS_MODES:
        row[mode] = simulate_event(exec_date, PLANS[mode])
    raw_results[ev["exec_date"]] = row

# ---------------- 统计与判定 ----------------
LADDER_MODES = [f"ladder_{n}x{g}" for n, g in LADDER_GRID]
DCA_MODES = list(DCA_PLANS.keys())


def pair_stats(events: list[dict], res: dict, modes: list[str]):
    """对一组事件：每档位配对统计 + 档位中位数汇总。"""
    per_mode = {}
    for m in modes:
        imp_ret120, imp_ret60, imp_dd, pairs, terms, cg, imp_aligned = [], [], [], 0, 0, [], []
        for ev in events:
            d = ev["exec_date"]
            if d not in res:
                continue
            b = res[d]["baseline"]
            s = res[d][m]
            if s["terminated"]:
                terms += 1
            if not np.isnan(b["ret_120"]) and not np.isnan(s["ret_120"]):
                imp_ret120.append(s["ret_120"] - b["ret_120"])
                pairs += 1
            if not np.isnan(b["ret_60"]) and not np.isnan(s["ret_60"]):
                imp_ret60.append(s["ret_60"] - b["ret_60"])
            if not np.isnan(b["dd_build"]) and not np.isnan(s["dd_build"]):
                imp_dd.append(b["dd_build"] - s["dd_build"])  # 正 = 分批回撤更浅
            if not np.isnan(b["ret_aligned_180"]) and not np.isnan(s["ret_aligned_180"]):
                imp_aligned.append(s["ret_aligned_180"] - b["ret_aligned_180"])
            if not np.isnan(s["cost_gap"]):
                cg.append(s["cost_gap"])
        n_ev = sum(1 for ev in events if ev["exec_date"] in res)
        per_mode[m] = {
            "n_events": n_ev,
            "n_pairs_ret120": pairs,
            "terminate_rate": round(terms / n_ev, 4) if n_ev else None,
            "ret120_improve_med_pp": round(float(np.median(imp_ret120)) * 100, 3) if imp_ret120 else None,
            "ret120_improve_pos_rate": round(float(np.mean(np.array(imp_ret120) > 0)), 4) if imp_ret120 else None,
            "ret60_improve_med_pp": round(float(np.median(imp_ret60)) * 100, 3) if imp_ret60 else None,
            "dd_improve_med_pp": round(float(np.median(imp_dd)) * 100, 3) if imp_dd else None,
            "dd_improve_pos_rate": round(float(np.mean(np.array(imp_dd) > 0)), 4) if imp_dd else None,
            "ret180_improve_med_pp": round(float(np.median(imp_aligned)) * 100, 3) if imp_aligned else None,
            "cost_gap_med_pp": round(float(np.median(cg)) * 100, 3) if cg else None,
        }
    # 子方向汇总：全部档位中位数
    meds = [v["ret120_improve_med_pp"] for v in per_mode.values() if v["ret120_improve_med_pp"] is not None]
    posr = [v["ret120_improve_pos_rate"] for v in per_mode.values() if v["ret120_improve_pos_rate"] is not None]
    dds = [v["dd_improve_med_pp"] for v in per_mode.values() if v["dd_improve_med_pp"] is not None]
    ddpos = [v["dd_improve_pos_rate"] for v in per_mode.values() if v["dd_improve_pos_rate"] is not None]
    pairs_n = [v["n_pairs_ret120"] for v in per_mode.values()]
    terms_r = [v["terminate_rate"] for v in per_mode.values() if v["terminate_rate"] is not None]
    summary = {
        "ret120_improve_med_pp": round(float(np.median(meds)), 3) if meds else None,
        "ret120_improve_pos_rate": round(float(np.median(posr)), 4) if posr else None,
        "dd_improve_med_pp": round(float(np.median(dds)), 3) if dds else None,
        "dd_improve_pos_rate": round(float(np.median(ddpos)), 4) if ddpos else None,
        "min_pairs_ret120": min(pairs_n) if pairs_n else 0,
        "terminate_rate_med": round(float(np.median(terms_r)), 4) if terms_r else None,
        "all_modes_ret120_positive": bool(meds and all(x > 0 for x in meds)),
    }
    return per_mode, summary


def judge(per_mode: dict, summary: dict, label: str) -> dict:
    if summary["min_pairs_ret120"] < MIN_PAIRS_TOTAL:
        verdict = "证据不足"
        reason = f"配对样本 {summary['min_pairs_ret120']} < {MIN_PAIRS_TOTAL}"
    elif summary["terminate_rate_med"] is not None and summary["terminate_rate_med"] > TERM_RATE_LINE:
        verdict = "证据不足"
        reason = f"作废率中位数 {summary['terminate_rate_med']} > {TERM_RATE_LINE}"
    else:
        ret_ok = (
            summary["ret120_improve_med_pp"] is not None
            and summary["ret120_improve_med_pp"] >= RET120_LINE_PP
            and summary["ret120_improve_pos_rate"] is not None
            and summary["ret120_improve_pos_rate"] >= POS_RATE_LINE
        )
        dd_ok = (
            summary["dd_improve_med_pp"] is not None
            and summary["dd_improve_med_pp"] >= DD_LINE_PP
            and summary["dd_improve_pos_rate"] is not None
            and summary["dd_improve_pos_rate"] >= POS_RATE_LINE
        )
        consistent = summary["all_modes_ret120_positive"]
        if ret_ok and dd_ok and consistent:
            verdict = "有实质改善"
            reason = "收益与回撤两维度均过预注册线且档位方向一致"
        elif (ret_ok and not dd_ok) or (dd_ok and not ret_ok):
            verdict = "无实质增量"
            reason = f"仅单维度达标（收益过线={ret_ok}，回撤过线={dd_ok}）"
        else:
            verdict = "无实质增量"
            reason = f"两维度均未达线（收益过线={ret_ok}，回撤过线={dd_ok}，档位一致={consistent}）"
    return {"label": label, "verdict": verdict, "reason": reason, "summary": summary,
            "per_mode": per_mode}


extreme_events = [e for e in main_events if e["extreme_bottom"]]
normal_events = [e for e in main_events if not e["extreme_bottom"]]

verdicts = {}
for name, modes in (("ladder", LADDER_MODES), ("dca", DCA_MODES)):
    pm_all, sm_all = pair_stats(main_events, results, modes)
    verdicts[f"{name}_overall"] = judge(pm_all, sm_all, f"{name} 全事件")
    pm_ext, sm_ext = pair_stats(extreme_events, results, modes)
    v_ext = judge(pm_ext, sm_ext, f"{name} 极端底部组")
    if sm_ext["min_pairs_ret120"] < MIN_PAIRS_GROUP:
        v_ext["verdict"] = "证据不足"
        v_ext["reason"] = f"分组配对样本 {sm_ext['min_pairs_ret120']} < {MIN_PAIRS_GROUP}"
    verdicts[f"{name}_extreme"] = v_ext
    pm_nor, sm_nor = pair_stats(normal_events, results, modes)
    v_nor = judge(pm_nor, sm_nor, f"{name} 普通加仓组")
    if sm_nor["min_pairs_ret120"] < MIN_PAIRS_GROUP:
        v_nor["verdict"] = "证据不足"
        v_nor["reason"] = f"分组配对样本 {sm_nor['min_pairs_ret120']} < {MIN_PAIRS_GROUP}"
    verdicts[f"{name}_normal"] = v_nor

# 敏感性汇总（不判定）
sens_mech = pair_stats(main_events, {d: {**v, **{m: v[m + "|mech"] for m in SENS_MODES}} for d, v in results.items()}, SENS_MODES)
sens_raw = pair_stats(raw_events, raw_results, SENS_MODES)

# 基准本身的事件统计（供报告）
base_stats = {
    e["exec_date"]: {
        "ret_120": results[e["exec_date"]]["baseline"]["ret_120"],
        "ret_60": results[e["exec_date"]]["baseline"]["ret_60"],
    }
    for e in main_events
}

# ---------------- 输出与哈希 ----------------
def _sanitize(o):
    """递归把 NaN/Inf 转 None（JSON 规范化），dict 键排序保证双跑稳定。"""
    if isinstance(o, dict):
        return {str(k): _sanitize(o[k]) for k in sorted(o)}
    if isinstance(o, (list, tuple)):
        return [_sanitize(x) for x in o]
    if isinstance(o, float) and (np.isnan(o) or np.isinf(o)):
        return None
    return o


out = {
    "prereg": {
        "signal": "399006 b200 3-band 30/70 gamma1.0 (champion_cyb.json)",
        "fee_bps": FEE_BPS,
        "cluster_gap_td": CLUSTER_GAP,
        "extreme_rule": f"B200<={EXTREME_B200_LINE} within {EXTREME_LOOKBACK}td before signal",
        "hold_windows": list(N_HOLD),
        "aligned_window": ALIGNED_WIN,
        "lines": {
            "ret120_pp": RET120_LINE_PP, "dd_pp": DD_LINE_PP,
            "pos_rate": POS_RATE_LINE, "min_pairs": MIN_PAIRS_TOTAL,
            "min_pairs_group": MIN_PAIRS_GROUP, "term_rate": TERM_RATE_LINE,
        },
    },
    "events_raw": kept,
    "events_main_count": len(main_events),
    "events_extreme_count": len(extreme_events),
    "events_normal_count": len(normal_events),
    "double_le20_count": double_le20,
    "results": results,
    "verdicts": verdicts,
    "baseline_stats": base_stats,
    "sens_mechanical": {"summary": sens_mech[1], "per_mode": sens_mech[0]},
    "sens_raw_events": {"summary": sens_raw[1], "per_mode": sens_raw[0]},
}

RAW_DIR.mkdir(parents=True, exist_ok=True)
payload = json.dumps(_sanitize(out), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
(RAW_DIR / "staged_entry_results.json").write_text(
    json.dumps(_sanitize(out), sort_keys=True, ensure_ascii=False, indent=1)
)
seed = os.environ.get("PYTHONHASHSEED", "?")
(RAW_DIR / "HASH.txt").write_text(f"PYTHONHASHSEED={seed}\nsha256={h}\n")
print("PYTHONHASHSEED =", seed)
print("EVENTS raw/merged/main:", len(kept), len(main_events), "| extreme:", len(extreme_events),
      "| normal:", len(normal_events), "| double_le20:", double_le20)
print("HASH:", h)
for k, v in verdicts.items():
    print(f"[{k}] {v['verdict']} — {v['reason']}")
    s = v["summary"]
    print(f"    ret120改善中位 {s['ret120_improve_med_pp']}pp / 正占比 {s['ret120_improve_pos_rate']}"
          f" | dd改善中位 {s['dd_improve_med_pp']}pp / 正占比 {s['dd_improve_pos_rate']}"
          f" | 作废率 {s['terminate_rate_med']} | 配对 {s['min_pairs_ret120']}")
print("SENS mech:", {k: vv for k, vv in sens_mech[1].items()})
print("SENS raw :", {k: vv for k, vv in sens_raw[1].items()})
