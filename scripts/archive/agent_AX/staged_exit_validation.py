# -*- coding: utf-8 -*-
"""卖出侧分批执行的正式检验：三档减仓信号触发后"一次性清到位 vs 分批减"（预注册版）。

任务书：调度者任务 AX（执行层拼图最后一块）。本脚本为唯一计算入口，
跑前写死全部规则与判定线，跑后不回改（如需改动须在报告中如实登记为
"事后变更"）。判定标准先于任何结果数字写定。

===============================================================================
一、预注册：信号与数据（全部复用已验证规则，不发明新信号）
===============================================================================
- 信号：创业板三档冠军（与 AE/AM 同源），参数逐字复用
  docs/experiments/raw/kuandu-quanzhan/champion_cyb.json：
  symbol=399006, ladder, indicator=b200, n_bands=3, direction=contrarian,
  low_edge=30, high_edge=70, gamma=1.0, min_trade=0.05, fee_bps=10。
  档位线 43.3/56.7：B200<=43.3→仓位1.0；43.3<B200<=56.7→0.5；B200>56.7→0.0。
  引擎 src/lei_signal/timing_backtest/strategies.py::ladder_target +
  engine.py::simulate 的执行口径：T 日收盘信号 → T+1 开盘执行（无未来函数）。
- 行情/宽度：~/.lei_signal_lab/cache/timing/ 399006.parquet +
  breadth_cn_all.parquet（全A宽度，幸存者偏差声明同 AE）。样本窗 2010-06→
  2026-08-27（与 AE 相同）。禁止抓取，只用现有缓存。
- 价格完整性（复用 AK 复权修正规则的"检查"半边）：399006 为指数，机械检查
  隔夜收盘比 >1.5 或 <1/1.5（scripts/agent_AK/extreme_bottom_event_study.py
  同规则），触发数登记（预查=0，指数无公司行为）。
- NaN 口径（引擎忠实）：b200 缺失日在 ladder_target 中经 searchsorted 映射为
  档位 0.0（np.searchsorted 把 NaN 排在末位）——这是归档引擎的真实行为，
  本脚本一律保持该口径；由此产生的事件层影响见下条。
- 费率：每次调仓按 |Δw| 名额 × 10bp（champion_cyb.json fee_bps=10.0，
  归档"统一口径：费用 10bp 双边"）。现金不计息（引擎默认 cash_rate=0；
  方向性登记：分批期间基准账户持现金、分批账户持仓，不计息对基准略不利，
  量级 ≈ Δ/2 × 1.5-2%年化 × M/12 ≈ 0.01-0.09pp，可忽略）。
- 死区：min_trade=0.05 仅作用于信号跟随调仓（引擎口径）；分批批次为计划内
  动作不受死区吞并（AE 同款登记）。本设计中信号调仓档差恒 0.5、最小批次
  (1.0-0.5)/6≈0.0833 均大于死区，该口径实际无作用，登记为无操作数。

===============================================================================
二、预注册：事件定义（机械提取，禁止看图挑事件）
===============================================================================
- 仓位序列：exec_w(t) = ladder_target(b200)(t-1)（T-1 收盘信号 → T 开盘执行
  的仓位，与 AE 逐字同构）。
- 原始减仓事件：exec_w 从 ==1.0 下跳到 <1.0 的交易日 t（事件执行日 i0=t，
  开盘可成交日）；标注目标档 tgt∈{0.5, 0.0}（to_half / to_zero 两类分开统计）。
- 数据完整性剔除（机械、跑前写死）：信号日（i0-1）b200 为 NaN 的事件剔除
  ——b200 缺失把档位机械映成 0.0，这不是宽度读数产生的减仓决策，是数据
  断供。被剔除事件全部登记于结果 JSON（含原因），不静默丢弃。
- 簇合并（对齐 AM/AE 簇规则）：与前一保留事件间隔 <40 个交易日的下跳并入
  前一簇不另计（B200 在 43.3 线附近抖动）。40 日为预注册固定值，不扫描。
  剔除动作先于簇合并执行（先剔除 NaN 伪事件、再对真实事件簇合并）。
- 每事件登记：执行日、信号日、tgt 档、信号日 B200 读数、类型标签。

===============================================================================
三、预注册：执行方式（AM 的镜像，跑前写死）
===============================================================================
- 基准 B0（现役行为）：i0 开盘把权重从 1.0 一次性调到 tgt（|Δw|=1.0-tgt，
  费 10bp）；此后每日开盘跟随 exec_w（信号优先，档变即调，引擎口径）。
- 分批 S_M（M∈{1,3,6} 三个档位）：i0 开盘不动（保持 1.0）；此后第 k 批在
  i0+21k 开盘把权重下调 (1.0-tgt)/M（k=1..M；月间隔=21 个交易日的固定近似，
  与 AM 同口径；"日历间隔"的操作定义）。M=1 为退化情形（单批=整体推迟
  一个月执行）——这是 AM "首批在 t0+21、t0 当日不投" 的逐字镜像（买入侧
  分批在 t0 不投、卖出侧分批在 t0 不减），登记该退化性质，不另行发明
  批内切分。"首批在 t0 立即减 1/M"的变体不在本次预注册内（登记为局限）。
- 作废规则（信号优先，任务书建议方案，跑前采纳并论证）：分批程序进行期间
  （i0+1 开盘起至 i0+21M），任一开盘日 prev 日信号档 exec_w ≠ tgt（不论
  升档还是降档，即任何档位变化）→ 剩余批次立即作废，当日开盘一次性对齐
  到 exec_w 新档（费按 |Δw|），登记作废方向（down=信号更低档 / up=信号
  更高档）。作废后账户此后与基准完全一致地跟随信号。同日"作废对齐"优先
  于"批次执行"。与 AE 的信号优先原则同构；AE 只在降向作废（建仓侧升向
  不跟），本任务两侧都作废（减仓侧升向同样改变目标档，任务书明示两种
  变化都处理）。作废率必须分档报告。
- 程序终点 t_conv：未作废=完成日 i0+21M；作废=作废对齐日。此后两账户
  行为完全一致（跟随同一信号序列、同一引擎规则）→ 两账户净值之比自
  t_conv 起冻结（数学恒等，脚本内用 i0+376 终点数值复核，容差 1e-9）。
- 敏感性（只登记不判定）：纯机械不中断版（忽略作废、批次照跑、完成后
  跟随信号），对照"信号冲突成本"。

===============================================================================
四、预注册：度量（跑前写死）
===============================================================================
每事件 × 每档 M∈{1,3,6}（基准同期重算）：
1. vdiff_main（主口径·价值维）：两账户自 i0 开盘等权起步（权益=1.0、
   权重=1.0），t_conv 日收盘权益比 eq_S/eq_B - 1（百分点）。对齐终点论证
   （吸取 AM 教训）：两方式在同一日期、同一账户规则下比终值，t_conv 后
   路径恒同，任何更晚的共同终点给出同一比值——窗口错位假象在构造上不
   存在；另在 i0+376（=最长程序 126 + 250 跟进，对齐任务"随后 250 日"）
   终点数值复核不变性。数据不足（i0+21M 超出数据末端）→ 该事件该档缺失
   （不编造）。
2. dd_exec_diff（主口径·回撤维）：固定窗 [i0, i0+21M]（两方式同日历窗，
   窗由档位 M 唯一决定、不依赖作废等结果）：日收盘权益最大回撤
   dd_S − dd_B（百分点；两者均为负数，差为负=分批跌得更深）。窗超出
   数据 → 缺失。
3. 补充（任务书点名，不参与判定）：
   - dd_actual：[i0, t_conv] 同窗两方式各自回撤及差（程序实际持续期）；
   - dd_full376：[i0, i0+376] 同窗（可用子样本）；
   - dd_plus250_own：任务书"执行期+随后 250 日"各自窗口版（基准 [i0,i0+250]、
     分批 [i0, t_conv+250]——窗口不对齐，登记偏差方向对分批不利（窗口更长
     且含持仓段），仅登记）；
   - up120（卖太快的罚金，事件级、与方式无关）：[i0, i0+120] 最高收盘相对
     i0 收盘涨幅；t_peak120 峰位滞后交易日数；r120 / r250 前瞻收益；
   - 事后路径类型（AN 机械分类镜像，含未来信息、仅作机制叙述）：
     20 交易日内收 < 0.9×c0 → 急跌型；t10>40 或 250 日内未出现 → 磨顶型
     （未出现记截尾）；其余中间型；前瞻不足 60 日不可分类。
   - 每方式 trades / turnover / fee_paid；作废标记、作废日、方向、已执行
     批数；t_conv 日期。
4. 统计（每档）：配对 N；vdiff 中位 (q1/q3)、>0 占比、双侧精确二项符号
   检验 p（并列剔除；描述性，不参与判定）；dd_exec_diff 中位 (q1/q3)、
   <0（更深）占比；作废率；分 to_half / to_zero 子组中位数；分路径类型
   子组中位数（事后）；up120 与 vdiff 的秩相关（描述性）。

===============================================================================
五、预注册：判定线（三选一，数值跑前写死，每档 M 独立判定）
===============================================================================
记 v = vdiff 配对中位（pp，正=分批终点更值钱）；d = dd_exec_diff 配对中位
（pp，负=分批执行期回撤更深）。两维同时定义"实质"：
- 线值：价值线 +1.5pp（AE 改善线 / AM 容忍线 Y 的原值复用，保证两侧结论
  可并排对照；399006 月波动约 8%，1.5pp 远小于常规月波动但大于费用与
  计息噪声一个数量级，是"实质而非噪声"的量级）；回撤线 3.0pp（AM/AE
  回撤线原值复用；AN 登记 60 日内最深下探中位 -8.4%，3pp≈其四成，与
  AM"吃到典型二次下探的一半"同构）。
- 分批有实质改善：v >= +1.5 且 d > -3.0（真实赚到价值且执行期多承受的
  回撤未过实质线）。
- 真实交换（判无实质差异并注明）：(v <= -1.5 且 d >= +3.0) 或
  (v >= +1.5 且 d <= -3.0)（一维付出实质代价、另一维换回实质补偿，
  AM 12 个月档同款情形的镜像）。
- 一次性更好：非改善、非交换，且 (v <= -1.5 或 d <= -3.0)（付出实质
  代价而补偿不过线——AM"代价>Y 且 改善<X"的镜像）。
- 其余 → 无实质差异。
- 样本下限：某档配对 N < 10 → 该档判无实质差异并标注"样本不足"（AM 池
  下限原值）。
- 子型护栏：若某档判{改善|一次性更好}但 to_half 子组（主力子型）vdiff
  中位数与池中位数严格反号 → 降为无实质差异（防单一子型驱动；to_zero
  预计仅约 3 个，不作护栏）。
判定枚举：分批有实质改善 / 一次性更好 / 无实质差异。

===============================================================================
六、红线
===============================================================================
只测既定减仓决策的执行结构，不回答"该不该减仓"、不产生任何买卖规则、
不产生新信号；事件机械提取；主口径终点对齐；判定线跑前写死跑后不调。

===============================================================================
七、双跑哈希
===============================================================================
PYTHONHASHSEED=0 与 42 各完整跑一遍，规范 JSON（键排序、NaN→null）的
sha256 必须逐位一致。
===============================================================================
"""
from __future__ import annotations

import hashlib
import json
import math
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
FEE_BPS = 10.0          # champion_cyb.json
MIN_TRADE = 0.05        # champion_cyb.json（信号跟随死区）
CLUSTER_GAP = 40        # 簇合并间隔（交易日）
MONTH_TD = 21           # 月间隔 = 21 交易日（AM 同口径）
VARIANTS = (1, 3, 6)    # 分批档位（月）
ALIGN_TD = 376          # 126（最长程序）+ 250（跟进），不变性复核终点
FOLLOWUP_TD = 250       # 任务书"随后 250 日"
VAL_LINE_PP = 1.5       # 价值线
DD_LINE_PP = 3.0        # 回撤线
MIN_PAIRS = 10          # 判定样本下限
UP_WINDOW = 120         # up120 窗口
RAW_DIR = REPO / "docs/experiments/raw/agent_AX"

# ---------------- 数据与信号（AE 同构） ----------------
al = align_index_breadth(load_index_bars("399006"), load_breadth("cn_all"))
ladder = LadderParams(
    indicator="b200", n_bands=3, direction="contrarian",
    low_edge=30.0, high_edge=70.0, gamma=1.0,
)
sig = ladder_target(al["b200"], ladder)   # T 日收盘目标仓位
exec_w = sig.shift(1)                     # 当日开盘执行的仓位（前日信号）
exec_w_vals = exec_w.to_numpy(dtype=float)
b200_vals = al["b200"].to_numpy(dtype=float)
opens = al["open"].to_numpy(dtype=float)
closes = al["close"].to_numpy(dtype=float)
dates = al.index
n_days = len(dates)
pos_of = {d: i for i, d in enumerate(dates)}

# ---------------- 完整性检查（登记，不修改数据） ----------------
_close = al["close"]
_ret = _close / _close.shift(1)
overnight_flags = int(((_ret > 1.5) | (_ret < 1.0 / 1.5)).sum())
nan_days = int(np.isnan(b200_vals).sum())

# ---------------- 事件提取（机械 + NaN 剔除 + 簇合并） ----------------
raw_events: list[dict] = []
for i in range(1, n_days):
    w, p = exec_w_vals[i], exec_w_vals[i - 1]
    if not np.isnan(p) and not np.isnan(w) and p == 1.0 and w < 1.0:
        ev = {
            "exec_date": dates[i].strftime("%Y-%m-%d"),
            "signal_date": dates[i - 1].strftime("%Y-%m-%d"),
            "tgt": float(w),
            "kind": "to_half" if w == 0.5 else "to_zero",
            "b200_at_signal": None if np.isnan(b200_vals[i - 1]) else round(float(b200_vals[i - 1]), 4),
            "excluded_nan_signal": bool(np.isnan(b200_vals[i - 1])),
        }
        raw_events.append(ev)

real_events = [e for e in raw_events if not e["excluded_nan_signal"]]
excluded_events = [e for e in raw_events if e["excluded_nan_signal"]]

kept: list[dict] = []
last_i = None
for ev in real_events:
    i = pos_of[pd.Timestamp(ev["exec_date"])]
    if last_i is None or i - last_i >= CLUSTER_GAP:
        ev2 = dict(ev)
        ev2["cluster_main"] = True
        kept.append(ev2)
        last_i = i
    else:
        ev2 = dict(ev)
        ev2["cluster_main"] = False
        kept.append(ev2)
main_events = [e for e in kept if e["cluster_main"]]

# ---------------- 账户模拟器（引擎口径：目标权重制、开盘成交、费 10bp） ----------------
fee_rate = FEE_BPS * 1e-4


def simulate(i0: int, tgt: float, months: int | None, mechanical: bool = False):
    """基准 months=None；分批 months=M。返回 None=程序无法在数据内完成。

    事件级账户：i0 开盘前权益 1.0、权重 1.0（全仓）。
    """
    end_i = min(n_days - 1, i0 + ALIGN_TD)
    if months is not None and i0 + MONTH_TD * months > end_i:
        return None
    plan = {}
    last_batch = i0
    if months is not None:
        dw = (1.0 - tgt) / months
        for k in range(1, months + 1):
            plan[i0 + MONTH_TD * k] = dw
        last_batch = i0 + MONTH_TD * months
    state = {"cash": 0.0, "units": 1.0 / opens[i0], "w": 1.0}
    trades, turnover, fee_paid = 0, 0.0, 0.0
    cancelled, cancel_i, cancel_dir, tranches_done = False, None, None, 0

    def rebalance(i: int, desired: float):
        nonlocal trades, turnover, fee_paid
        delta = desired - state["w"]
        if abs(delta) <= 1e-12:
            return
        eq_open = state["cash"] + state["units"] * opens[i]
        fee = eq_open * abs(delta) * fee_rate
        eq_after = eq_open - fee
        state["units"] = eq_after * desired / opens[i]
        state["cash"] = eq_after - eq_after * desired
        state["w"] = desired
        trades += 1
        turnover += abs(delta)
        fee_paid += fee

    eq_path: dict[int, float] = {}
    program_done = months is None  # 基准：i0 开盘即完成
    for i in range(i0, end_i + 1):
        sig_prev = exec_w_vals[i] if i > 0 else float("nan")
        if i == i0:
            if months is None:
                rebalance(i0, tgt)  # 一次性清到位（现役行为）
        elif not program_done:
            # 分批程序期：信号优先（任何档位变化→作废对齐）
            if not mechanical and not np.isnan(sig_prev) and sig_prev != tgt:
                rebalance(i, float(sig_prev))
                cancelled, cancel_i = True, i
                cancel_dir = "down" if sig_prev < tgt else "up"
                program_done = True
            elif i in plan:
                rebalance(i, state["w"] - plan[i])
                tranches_done += 1
                if i == last_batch:
                    program_done = True
        else:
            # 程序结束（或基准）：跟随信号（引擎死区口径）
            if not np.isnan(sig_prev) and sig_prev != state["w"] and abs(sig_prev - state["w"]) > max(1e-9, MIN_TRADE):
                rebalance(i, float(sig_prev))
        eq_path[i] = state["cash"] + state["units"] * closes[i]

    t_conv = last_batch if months is None or (not cancelled) else cancel_i
    if months is None:
        t_conv = i0  # 基准在 i0 即到位
    return {
        "eq_path": eq_path,
        "t_conv": t_conv,
        "last_batch": last_batch,
        "cancelled": cancelled,
        "cancel_date": dates[cancel_i].strftime("%Y-%m-%d") if cancel_i is not None else None,
        "cancel_dir": cancel_dir,
        "tranches_done": tranches_done,
        "n_trades": trades,
        "turnover": round(turnover, 4),
        "fee_paid": round(fee_paid, 6),
        "final_w": state["w"],
    }


def max_dd(eq: list[float]) -> float:
    peak, mdd = -np.inf, 0.0
    for v in eq:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1.0)
    return mdd


# ---------------- 逐事件 × 逐档计算 ----------------
per_event: dict[str, dict] = {}
for ev in main_events:
    i0 = pos_of[pd.Timestamp(ev["exec_date"])]
    tgt = ev["tgt"]
    # 事件级背景（卖太快的罚金 / 路径类型）
    c0 = closes[i0]
    i120 = min(n_days - 1, i0 + UP_WINDOW)
    n_fwd120 = i120 - i0
    seg120 = closes[i0 : i120 + 1]
    up120 = float(seg120.max() / c0 - 1.0) if n_fwd120 >= 60 else float("nan")
    t_peak = int(seg120.argmax()) if n_fwd120 >= 60 else None
    r120 = float(closes[i120] / c0 - 1.0) if i0 + UP_WINDOW <= n_days - 1 else float("nan")
    i250 = min(n_days - 1, i0 + 250)
    r250 = float(closes[i250] / c0 - 1.0) if i0 + 250 <= n_days - 1 else float("nan")
    # 路径类型（AN 机械分类镜像，事后描述）
    n_fwd = n_days - 1 - i0
    path_type = "unclassifiable"
    t10 = None
    if n_fwd >= 60:
        below = np.where(closes[i0 : min(n_days, i0 + 251)] < 0.9 * c0)[0]
        t10 = int(below[0]) if len(below) else None
        if t10 is not None and t10 <= 20:
            path_type = "sharp"
        elif t10 is None:
            path_type = "grind_censored"
        elif t10 > 40:
            path_type = "grind"
        else:
            path_type = "middle"
    base_res = simulate(i0, tgt, None)
    row = {
        "meta": {**{k: ev[k] for k in ("exec_date", "signal_date", "tgt", "kind", "b200_at_signal")},
                 "up120": None if np.isnan(up120) else round(up120, 6),
                 "t_peak120": t_peak,
                 "r120": None if np.isnan(r120) else round(r120, 6),
                 "r250": None if np.isnan(r250) else round(r250, 6),
                 "path_type": path_type, "t10": t10, "n_fwd": int(n_fwd)},
        "base": {
            "fee_paid": base_res["fee_paid"], "turnover": base_res["turnover"],
            "n_trades": base_res["n_trades"],
        },
        "variants": {},
    }
    eq_base = base_res["eq_path"]
    for M in VARIANTS:
        sres = simulate(i0, tgt, M)
        mres = simulate(i0, tgt, M, mechanical=True)  # 敏感性
        entry: dict = {"available": sres is not None}
        if sres is not None:
            eq_s = sres["eq_path"]
            t_conv = sres["t_conv"]
            vdiff = (eq_s[t_conv] / eq_base[t_conv] - 1.0) * 100.0
            w_end = i0 + MONTH_TD * M
            dd_win_ok = w_end <= n_days - 1
            dd_s = max_dd([eq_s[i] for i in range(i0, w_end + 1)]) if dd_win_ok else float("nan")
            dd_b = max_dd([eq_base[i] for i in range(i0, w_end + 1)]) if dd_win_ok else float("nan")
            # 补充：实际程序窗 / 全窗 376 / 各自+250
            dd_s_act = max_dd([eq_s[i] for i in range(i0, t_conv + 1)])
            dd_b_act = max_dd([eq_base[i] for i in range(i0, t_conv + 1)])
            full_ok = i0 + ALIGN_TD <= n_days - 1
            dd_s_full = max_dd([eq_s[i] for i in range(i0, i0 + ALIGN_TD + 1)]) if full_ok else float("nan")
            dd_b_full = max_dd([eq_base[i] for i in range(i0, i0 + ALIGN_TD + 1)]) if full_ok else float("nan")
            o250_b = i0 + FOLLOWUP_TD <= n_days - 1
            o250_s = t_conv + FOLLOWUP_TD <= n_days - 1
            dd_b_250 = max_dd([eq_base[i] for i in range(i0, i0 + FOLLOWUP_TD + 1)]) if o250_b else float("nan")
            dd_s_250 = max_dd([eq_s[i] for i in range(i0, t_conv + FOLLOWUP_TD + 1)]) if o250_s else float("nan")
            # 不变性复核：i0+376 终点比值应与 t_conv 终点一致
            vdiff_376 = (eq_s[i0 + ALIGN_TD] / eq_base[i0 + ALIGN_TD] - 1.0) * 100.0 if full_ok else float("nan")
            entry.update({
                "vdiff_pp": round(vdiff, 4),
                "vdiff_376_check": None if np.isnan(vdiff_376) else round(vdiff_376, 4),
                "t_conv_date": dates[t_conv].strftime("%Y-%m-%d"),
                "cancelled": sres["cancelled"],
                "cancel_dir": sres["cancel_dir"],
                "tranches_done": sres["tranches_done"],
                "fee_paid": sres["fee_paid"],
                "turnover": sres["turnover"],
                "n_trades": sres["n_trades"],
                "dd_staged": None if np.isnan(dd_s) else round(dd_s, 6),
                "dd_base": None if np.isnan(dd_b) else round(dd_b, 6),
                "dd_diff_pp": None if (np.isnan(dd_s) or np.isnan(dd_b)) else round((dd_s - dd_b) * 100.0, 4),
                "dd_staged_actual": round(dd_s_act, 6),
                "dd_base_actual": round(dd_b_act, 6),
                "dd_diff_actual_pp": round((dd_s_act - dd_b_act) * 100.0, 4),
                "dd_staged_full": None if np.isnan(dd_s_full) else round(dd_s_full, 6),
                "dd_base_full": None if np.isnan(dd_b_full) else round(dd_b_full, 6),
                "dd_staged_own250": None if np.isnan(dd_s_250) else round(dd_s_250, 6),
                "dd_base_own250": None if np.isnan(dd_b_250) else round(dd_b_250, 6),
            })
        if mres is not None:
            eq_m = mres["eq_path"]
            t_c = min(mres["last_batch"] + 1, n_days - 1)
            entry["mech_vdiff_pp"] = round((eq_m[t_c] / eq_base[t_c] - 1.0) * 100.0, 4)
        row["variants"][f"M{M}"] = entry
    per_event[ev["exec_date"]] = row

# ---------------- 统计与判定 ----------------
def median_q(x: list[float]):
    if not x:
        return None, None, None
    a = np.asarray(x)
    return float(np.median(a)), float(np.percentile(a, 25)), float(np.percentile(a, 75))


def sign_test_p(x: list[float]):
    pos = sum(1 for v in x if v > 0)
    neg = sum(1 for v in x if v < 0)
    n = pos + neg
    if n == 0:
        return None, None
    k = min(pos, neg)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2.0**n * 2.0
    return round(min(1.0, p), 4), (pos, neg)


def rank_corr(x: list[float], y: list[float]):
    if len(x) < 3:
        return None
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    return round(float(np.corrcoef(rx, ry)[0, 1]), 4)


variant_stats: dict[str, dict] = {}
verdicts: dict[str, dict] = {}
for M in VARIANTS:
    key = f"M{M}"
    vds, dds, vds_h, dds_h, vds_z, dds_z = [], [], [], [], [], []
    canc, n_avail, fee_s, fee_b = 0, 0, [], []
    mech_vds = []
    for ev in main_events:
        d = per_event[ev["exec_date"]]
        e = d["variants"][key]
        if not e["available"]:
            continue
        n_avail += 1
        if e["cancelled"]:
            canc += 1
        vds.append(e["vdiff_pp"])
        fee_s.append(e["fee_paid"])
        fee_b.append(d["base"]["fee_paid"])
        if e["dd_diff_pp"] is not None:
            dds.append(e["dd_diff_pp"])
        if e.get("mech_vdiff_pp") is not None:
            mech_vds.append(e["mech_vdiff_pp"])
        if ev["kind"] == "to_half":
            vds_h.append(e["vdiff_pp"])
            if e["dd_diff_pp"] is not None:
                dds_h.append(e["dd_diff_pp"])
        else:
            vds_z.append(e["vdiff_pp"])
            if e["dd_diff_pp"] is not None:
                dds_z.append(e["dd_diff_pp"])
    v_med, v_q1, v_q3 = median_q(vds)
    d_med, d_q1, d_q3 = median_q(dds)
    p_sign, counts = sign_test_p(vds)
    vm_h, _, _ = median_q(vds_h)
    dm_h, _, _ = median_q(dds_h)
    vm_z, _, _ = median_q(vds_z)
    dm_z, _, _ = median_q(dds_z)
    stats = {
        "n_pairs_value": len(vds),
        "n_pairs_dd": len(dds),
        "vdiff_med_pp": None if v_med is None else round(v_med, 3),
        "vdiff_q1_q3": None if v_med is None else [round(v_q1, 3), round(v_q3, 3)],
        "vdiff_pos_rate": None if not vds else round(sum(1 for v in vds if v > 0) / len(vds), 4),
        "sign_test_p": p_sign, "sign_counts": counts,
        "dd_diff_med_pp": None if d_med is None else round(d_med, 3),
        "dd_q1_q3": None if d_med is None else [round(d_q1, 3), round(d_q3, 3)],
        "dd_deeper_rate": None if not dds else round(sum(1 for v in dds if v < 0) / len(dds), 4),
        "cancel_rate": round(canc / n_avail, 4) if n_avail else None,
        "fee_staged_med_bp": None if not fee_s else round(float(np.median(fee_s)) * 1e4, 2),
        "fee_base_med_bp": None if not fee_b else round(float(np.median(fee_b)) * 1e4, 2),
        "mech_vdiff_med_pp": None if not mech_vds else round(float(np.median(mech_vds)), 3),
        "sub_to_half": {"n": len(vds_h), "vdiff_med_pp": None if vm_h is None else round(vm_h, 3),
                        "dd_diff_med_pp": None if dm_h is None else round(dm_h, 3)},
        "sub_to_zero": {"n": len(vds_z), "vdiff_med_pp": None if vm_z is None else round(vm_z, 3),
                        "dd_diff_med_pp": None if dm_z is None else round(dm_z, 3)},
    }
    variant_stats[key] = stats

    # 判定（预注册枚举，机械执行）
    n_ok = stats["n_pairs_value"] >= MIN_PAIRS and stats["n_pairs_dd"] >= MIN_PAIRS
    if v_med is None or d_med is None:
        verdict, reason = "无实质差异", "无配对样本"
    elif not n_ok:
        verdict, reason = "无实质差异", f"样本不足（价值配对 {stats['n_pairs_value']} / 回撤配对 {stats['n_pairs_dd']} < {MIN_PAIRS}，按预注册默认）"
    else:
        improvement = v_med >= VAL_LINE_PP and d_med > -DD_LINE_PP
        exchange = (v_med <= -VAL_LINE_PP and d_med >= DD_LINE_PP) or (v_med >= VAL_LINE_PP and d_med <= -DD_LINE_PP)
        cost_material = v_med <= -VAL_LINE_PP or d_med <= -DD_LINE_PP
        if improvement:
            verdict, reason = "分批有实质改善", f"v={v_med:.2f}pp>=+{VAL_LINE_PP} 且 d={d_med:.2f}pp>-{DD_LINE_PP}"
        elif exchange:
            verdict, reason = "无实质差异", f"真实交换（v={v_med:.2f}, d={d_med:.2f}：一维实质代价换另一维实质补偿）"
        elif cost_material:
            verdict, reason = "一次性更好", f"实质代价无实质补偿（v={v_med:.2f}, d={d_med:.2f}）"
        else:
            verdict, reason = "无实质差异", f"两维均未过实质线（v={v_med:.2f}, d={d_med:.2f}）"
        # 子型护栏
        if verdict in ("分批有实质改善", "一次性更好") and vm_h is not None and v_med != 0:
            if (v_med > 0 and vm_h < 0) or (v_med < 0 and vm_h > 0):
                verdict, reason = "无实质差异", f"子型护栏触发：池 v 中位 {v_med:.2f} 与 to_half 子组 {vm_h:.2f} 严格反号"
    verdicts[key] = {"verdict": verdict, "reason": reason}

# 事后分组（路径类型）与秩相关（描述性）
path_groups: dict[str, dict] = {}
for M in VARIANTS:
    key = f"M{M}"
    for pt in ("sharp", "middle", "grind", "grind_censored"):
        vds = [per_event[e["exec_date"]]["variants"][key]["vdiff_pp"]
               for e in main_events
               if per_event[e["exec_date"]]["meta"]["path_type"] == pt
               and per_event[e["exec_date"]]["variants"][key]["available"]]
        m, _, _ = median_q(vds)
        path_groups.setdefault(key, {})[pt] = {"n": len(vds), "vdiff_med_pp": None if m is None else round(m, 3)}

corr_up120 = {}
for M in VARIANTS:
    key = f"M{M}"
    xs, ys = [], []
    for e in main_events:
        d = per_event[e["exec_date"]]
        if d["variants"][key]["available"] and d["meta"]["up120"] is not None:
            xs.append(d["meta"]["up120"] * 100.0)
            ys.append(d["variants"][key]["vdiff_pp"])
    corr_up120[key] = rank_corr(xs, ys)

# 不变性复核汇总
inv_max = 0.0
inv_n = 0
for e in main_events:
    d = per_event[e["exec_date"]]
    for key, ent in d["variants"].items():
        if ent["available"] and ent.get("vdiff_376_check") is not None:
            inv_max = max(inv_max, abs(ent["vdiff_376_check"] - ent["vdiff_pp"]))
            inv_n += 1

# 作废方向统计
cancel_anatomy = {}
for M in VARIANTS:
    key = f"M{M}"
    up_c = sum(1 for e in main_events
               if per_event[e["exec_date"]]["variants"][key]["available"]
               and per_event[e["exec_date"]]["variants"][key]["cancelled"]
               and per_event[e["exec_date"]]["variants"][key]["cancel_dir"] == "up")
    dn_c = sum(1 for e in main_events
               if per_event[e["exec_date"]]["variants"][key]["available"]
               and per_event[e["exec_date"]]["variants"][key]["cancelled"]
               and per_event[e["exec_date"]]["variants"][key]["cancel_dir"] == "down")
    cancel_anatomy[key] = {"cancel_up": up_c, "cancel_down": dn_c}

# ---------------- 输出与哈希 ----------------
def _sanitize(o):
    if isinstance(o, dict):
        return {str(k): _sanitize(o[k]) for k in sorted(o)}
    if isinstance(o, (list, tuple)):
        return [_sanitize(x) for x in o]
    if isinstance(o, float) and (np.isnan(o) if isinstance(o, float) else False):
        return None
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, float) and math.isnan(o):
        return None
    return o


out = {
    "prereg": {
        "signal": "399006 b200 3-band 30/70 gamma1.0 (champion_cyb.json, AE 同构)",
        "fee_bps": FEE_BPS, "cluster_gap_td": CLUSTER_GAP, "month_td": MONTH_TD,
        "variants_months": list(VARIANTS), "align_td": ALIGN_TD,
        "cancel_rule": "程序期任何档位变化（升或降）→ 剩余批次作废并一次性对齐新档",
        "lines": {"value_pp": VAL_LINE_PP, "dd_pp": DD_LINE_PP, "min_pairs": MIN_PAIRS},
        "main_metrics": "vdiff=t_conv 终点权益比（对齐终点）；dd_diff=固定窗 [i0,i0+21M] 同窗回撤差",
    },
    "data_integrity": {
        "window": [str(dates[0].date()), str(dates[-1].date())],
        "overnight_ratio_flags": overnight_flags,
        "b200_nan_days": nan_days,
        "nan_excluded_events": excluded_events,
    },
    "events_all": kept,
    "events_main_count": len(main_events),
    "events_to_half": sum(1 for e in main_events if e["kind"] == "to_half"),
    "events_to_zero": sum(1 for e in main_events if e["kind"] == "to_zero"),
    "per_event": per_event,
    "variant_stats": variant_stats,
    "verdicts": verdicts,
    "path_type_groups": path_groups,
    "corr_vdiff_up120": corr_up120,
    "cancel_anatomy": cancel_anatomy,
    "invariance_check": {"n": inv_n, "max_abs_diff_pp": round(inv_max, 10)},
}

RAW_DIR.mkdir(parents=True, exist_ok=True)
payload = json.dumps(_sanitize(out), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
(RAW_DIR / "staged_exit_results.json").write_text(
    json.dumps(_sanitize(out), sort_keys=True, ensure_ascii=False, indent=1)
)
seed = os.environ.get("PYTHONHASHSEED", "?")
(RAW_DIR / "HASH.txt").write_text(f"PYTHONHASHSEED={seed}\nsha256={h}\n")

print("PYTHONHASHSEED =", seed)
print("window:", out["data_integrity"]["window"], "| overnight flags:", overnight_flags, "| b200 NaN days:", nan_days)
print("EVENTS raw/real/clustered:", len(raw_events), len(real_events), len(main_events),
      "| to_half:", out["events_to_half"], "| to_zero:", out["events_to_zero"],
      "| nan-excluded:", len(excluded_events))
for e in excluded_events:
    print("  [NaN-excluded]", e["exec_date"], "tgt", e["tgt"])
print("HASH:", h)
for key in (f"M{m}" for m in VARIANTS):
    s = variant_stats[key]
    v = verdicts[key]
    print(f"[{key}] {v['verdict']} — {v['reason']}")
    print(f"    N(v/dd)={s['n_pairs_value']}/{s['n_pairs_dd']}  vdiff中位 {s['vdiff_med_pp']}pp "
          f"(q {s['vdiff_q1_q3']}, 正占比 {s['vdiff_pos_rate']}, p={s['sign_test_p']})  "
          f"dd差中位 {s['dd_diff_med_pp']}pp (更深占比 {s['dd_deeper_rate']})  作废率 {s['cancel_rate']} "
          f"({cancel_anatomy[key]['cancel_up']}升/{cancel_anatomy[key]['cancel_down']}降)")
    print(f"    子组 to_half {s['sub_to_half']} | to_zero {s['sub_to_zero']} | 机械版 vdiff中位 {s['mech_vdiff_med_pp']}pp")
print("invariance |v376-vconv| max:", round(inv_max, 10), "on", inv_n, "checks")
print("corr(vdiff, up120):", corr_up120)
