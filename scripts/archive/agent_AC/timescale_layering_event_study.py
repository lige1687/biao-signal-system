# -*- coding: utf-8 -*-
"""语义五前置验证——"长短期信号分层"简单事件研究（Prompt AC，2026-09-03）

【研究问题（一句话）】
在长周期宽度信号"允许做"的月份窗口里，等一个短周期"双极值警报"再入场，
比窗口一开始（月初第一个交易日）机械入场，入场质量好多少？好得不够多，
"分层"就没有价值。

【一层结构定义（跑前写死，全部复用已验证口径，不发明新指标）】
- 标的：创业板指 399006（主策略标的，冠军证据最全的口径）。只此一个，不扩标的。
- 长周期层（月度状态）：全A宽度 B200（站上200日均线个股占比，0-100，
  `~/.lei_signal_lab/cache/timing/breadth_cn_all.parquet`，回算口径含幸存者偏差）。
  每月最后一个交易日收盘的 B200 值，按冠军三档（`presets.py::cyb_b200_ladder3_final`，
  边界 30/70、逆势、gamma1.0；档位线 43.3333/56.6667）判定下个月的月度状态：
    * 主口径：上月末 B200 < 43.3333（冠军满仓档）→ 下月"允许做"；否则不允许；
      B200 为 NaN（成分 eligible 不足，2010-06~2012-07 段）→ 不允许（不造数据）。
    * 敏感性口径（只报告，不参与判定）：上月末 B200 < 56.6667（满仓或半仓档，
      即冠军任何非空仓档）→ 允许做。
- "允许窗口"= 连续允许月份的最大连段；窗口起=第一个允许月第一个交易日，
  窗口止=最后一个允许月最后一个交易日。
- 短周期层（日频触发）：双极值警报的低位侧"双≤20"——同日 B50 ≤ 20 且
  B200 ≤ 20（`timing_backtest/service.py::alert_state` 系统现值定义；
  归档验证：双≤20 后120日 13/13 标的正，
  `docs/experiments/kuandu-quanzhan-ARCHIVE-2026-09-01.md`）。
  高位侧"双≥85/90"是热度/逃顶警报，与"入场挑时点"无关，不使用。
- 执行口径（与仓库引擎 `timing_backtest/engine.py` 一致）：T 日收盘信号 →
  T+1 开盘成交。
    * 机械版：允许状态在上月末收盘已知 → 窗口第一个交易日的开盘价入场；
    * 分层版：窗口内（含起止两日）第一个"双≤20"日（T 收盘确认）的次一交易日
      开盘价入场；若整个窗口都没有双≤20 日 → 该窗口错过（不入场），
      错过本身就是关键数字。

【入场质量度量（跑前写死）】
- 入场日 D 以开盘价成交；N 日前瞻收益 = close[D+N] / open[D] - 1，
  D+N 为入场日后第 N 个交易日。N 主口径 = 60（约一个季度）；N=20 / 120 仅作
  描述性参考，不参与判定。
- 前瞻数据不足（数据末端）→ 该入场在该 N 期限下记"删失"并从该期限统计剔除
  （数量如实报告）。
- 进行中窗口细则（跑前写死）：数据结束时允许状态仍在延续的窗口 = "进行中"
  （下一月状态不可判定）。进行中窗口不计入错过率分母；若短信号已出现且收益
  可算，计入 N 期限统计；若短信号尚未出现，整窗从统计剔除（状态未定，
  不得记为 0% 也不得记为错过）。

【预注册判定线（跑前写死，跑完不得调整）】
设 n = 已完结允许窗口数（主口径、全历史），miss_rate = 已完结窗口中
  错过（等不到双≤20）的占比，
diff60 = 逐窗口差的均值 = mean over 统计纳入窗口 of
  [（分层版该窗 60 日收益；已完结但错过记 0%，即持币不亏不赚）
   -（机械版该窗 60 日收益）]，
matched_diff60 = 在两种方式都实际入场的纳入窗口里，
  短信号入场 60 日收益 - 机械入场 60 日收益 的逐窗差均值。

判定树（按顺序）：
  1) n < 8                        → 证据不足（样本太少，不足以下结论）
  2) miss_rate ≥ 2/3              → 无价值（错过太多：十窗七等不到，
                                     "时机精度"沦为抽签——任务书原话场景）
  3) diff60 ≥ +2.0pp 且 matched_diff60 > 0
                                  → 有价值（每窗平均净改善至少 2 个百分点，
                                     远超双边费用 10bp×2 的量级，且存在真实的
                                     时机改善而非全靠躲过坏窗口）
  4) diff60 < 0                   → 无价值（挑时点平均反而更差）
  5) 其余（0 ≤ diff60 < +2.0pp）  → 证据不足（改善太薄，撑不起分层复杂度）

费用说明：两版每个实际入场的窗口各付一次单边 10bp 入场费，费用差为零，
故上述收益差为费后等价口径；分层版在错过窗口不付费（这本身是其微小优势，
已包含在 diff60 的定义里）。

【诚实条款】
- 全部口径、阈值、判定线在跑第一遍之前写死于本 docstring，未做任何事后调整；
- 不做多标的、不嵌套多层、不做参数网格（敏感性口径是唯一的预注册变体，
  只报告不参与判定）；
- b200 的 NaN（2010-06~2012-07 成分 eligible 不足段）如实按"不允许"处理；
- 输出为带 sha256 的规范 JSON（PYTHONHASHSEED=0/42 双跑必须一致）。
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, "/Users/yongbiaoli/Desktop/lei-signal-lab/src")

import numpy as np
import pandas as pd

from lei_signal.timing_backtest.data import align_index_breadth, load_breadth, load_index_bars
from lei_signal.timing_backtest.strategies import _fixed_edges

SYMBOL = "399006"
HORIZONS = (20, 60, 120)
PRIMARY_N = 60
LOW_SIGNAL_THR = 20.0          # 双≤20
MIN_WINDOWS = 8                # 判定线 1
MISS_RATE_KILL = 2.0 / 3.0     # 判定线 2
DIFF60_VALUE_LINE = 0.02       # 判定线 3：+2.0pp

EDGES = _fixed_edges(3, 30.0, 70.0)   # [43.3333, 56.6667]（冠军三档，源码原函数）
FULL_BAND_EDGE = float(EDGES[0])      # 主口径：满仓档下界 43.3333
NONZERO_BAND_EDGE = float(EDGES[1])   # 敏感性口径：非空仓档下界 56.6667


def load_aligned() -> pd.DataFrame:
    px = load_index_bars(SYMBOL)
    br = load_breadth("cn_all")
    return align_index_breadth(px, br)


def forward_ret(open_: np.ndarray, close: np.ndarray, i_entry: int, n: int) -> float | None:
    j = i_entry + n
    if j >= len(close):
        return None
    return float(close[j] / open_[i_entry] - 1.0)


def study(df: pd.DataFrame, edge: float, label: str) -> dict:
    dates = df.index
    n_days = len(dates)
    open_ = df["open"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)

    periods = dates.to_period("M")
    # 每月最后交易日的 B200 → 次月是否允许（决策只用当月及以前数据，无未来函数）
    last_day_by_month: dict[pd.Period, pd.Timestamp] = {}
    for p, d in zip(periods, dates):
        last_day_by_month[p] = d  # 顺序遍历，留下每月最后一日
    decision_b200: dict[pd.Period, float | None] = {}  # key = 决策适用的月份
    for p, d in last_day_by_month.items():
        v = df["b200"].loc[d]
        decision_b200[p + 1] = None if pd.isna(v) else float(v)

    last_period = periods[-1]
    month_allowed = {p: (decision_b200.get(p) is not None and decision_b200[p] < edge)
                     for p in sorted(last_day_by_month.keys())}
    # 月份顺序序列上切连段
    all_months = sorted(last_day_by_month.keys())
    runs: list[list[pd.Period]] = []
    cur: list[pd.Period] = []
    for m in all_months:
        if month_allowed[m]:
            cur.append(m)
        else:
            if cur:
                runs.append(cur)
                cur = []
    if cur:
        runs.append(cur)

    # 窗口内交易日序号
    td_idx_by_month: dict[pd.Period, list[int]] = {}
    for i, p in enumerate(periods):
        td_idx_by_month.setdefault(p, []).append(i)

    sig_low = ((df["b50"] <= LOW_SIGNAL_THR) & (df["b200"] <= LOW_SIGNAL_THR)).to_numpy()

    rows = []
    for run in runs:
        ongoing = run[-1] == last_period
        i0 = td_idx_by_month[run[0]][0]
        i1 = td_idx_by_month[run[-1]][-1]
        first_period = run[0]
        b200_dec = decision_b200.get(first_period)

        row = {
            "start": str(dates[i0].date()),
            "end": str(dates[i1].date()),
            "months": len(run),
            "ongoing": ongoing,
            "b200_dec": None if b200_dec is None else round(b200_dec, 2),
            "mech_entry": str(dates[i0].date()),
        }

        hits = np.flatnonzero(sig_low[i0 : i1 + 1])
        if len(hits) > 0:
            sig_i = i0 + int(hits[0])
            entry_i = sig_i + 1  # T+1 开盘
            row.update(
                missed=False,
                sig_date=str(dates[sig_i].date()),
                entry_date=str(dates[min(entry_i, n_days - 1)].date()),
                wait_days=int(entry_i - i0),
            )
            entry_idx = entry_i
        else:
            row.update(missed=True, sig_date=None, entry_date=None, wait_days=None)
            entry_idx = None

        row["mech_ret20"] = forward_ret(open_, close, i0, 20)
        row["mech_ret60"] = forward_ret(open_, close, i0, 60)
        row["mech_ret120"] = forward_ret(open_, close, i0, 120)
        if entry_idx is None:
            row["short_ret20"] = row["short_ret60"] = row["short_ret120"] = None
        else:
            if entry_idx < n_days:
                row["short_ret20"] = forward_ret(open_, close, entry_idx, 20)
                row["short_ret60"] = forward_ret(open_, close, entry_idx, 60)
                row["short_ret120"] = forward_ret(open_, close, entry_idx, 120)
            else:  # 信号在最后一日，次日已无数据
                row["short_ret20"] = row["short_ret60"] = row["short_ret120"] = None
        rows.append(row)

    completed = [r for r in rows if not r["ongoing"]]
    ongoing_rows = [r for r in rows if r["ongoing"]]
    missed = [r for r in completed if r["missed"]]
    matched = [r for r in rows if not r["missed"]]

    stats: dict = {
        "label": label,
        "edge": round(edge, 4),
        "n_windows_total": len(rows),
        "n_completed": len(completed),
        "n_ongoing": len(ongoing_rows),
        "n_missed_completed": len(missed),
        "n_matched_total": len(matched),
        "miss_rate_completed": round(len(missed) / len(completed), 4) if completed else None,
    }

    for n in HORIZONS:
        key = f"ret{n}"
        # 纳入窗口：已完结（机械可算；分层错过记 0%）或 进行中且已入场（两者都可算才纳入）
        full = [
            r for r in completed if r[f"mech_{key}"] is not None
        ] + [
            r for r in ongoing_rows
            if not r["missed"] and r[f"mech_{key}"] is not None and r[f"short_{key}"] is not None
        ]
        mech_vals = np.array([r[f"mech_{key}"] for r in full], dtype=float)
        layered_vals = np.array(
            [r[f"short_{key}"] if r[f"short_{key}"] is not None else 0.0 for r in full],
            dtype=float,
        )
        diff = layered_vals - mech_vals
        # 匹配窗（两版都实际入场且都可算）
        m = [r for r in matched if r[f"mech_{key}"] is not None and r[f"short_{key}"] is not None]
        m_diff = np.array([r[f"short_{key}"] - r[f"mech_{key}"] for r in m], dtype=float) if m else np.array([])
        # 错过成本：已完结、错过、机械收益可算
        miss_mech = np.array(
            [r[f"mech_{key}"] for r in missed if r[f"mech_{key}"] is not None], dtype=float
        ) if missed else np.array([])
        stats[f"n{n}"] = {
            "n_full_eval": len(full),
            "n_censored": len(rows) - len(full),
            "mech_mean": round(float(mech_vals.mean()), 6) if len(mech_vals) else None,
            "layered_mean_incl_miss0": round(float(layered_vals.mean()), 6) if len(layered_vals) else None,
            "diff_mean": round(float(diff.mean()), 6) if len(diff) else None,
            "diff_median": round(float(np.median(diff)), 6) if len(diff) else None,
            "diff_win_rate": round(float((diff > 0).mean()), 4) if len(diff) else None,
            "n_matched_eval": len(m),
            "matched_diff_mean": round(float(m_diff.mean()), 6) if len(m_diff) else None,
            "matched_diff_median": round(float(np.median(m_diff)), 6) if len(m_diff) else None,
            "matched_diff_win_rate": round(float((m_diff > 0).mean()), 4) if len(m_diff) else None,
            "missed_mech_mean": round(float(miss_mech.mean()), 6) if len(miss_mech) else None,
            "missed_mech_n_eval": int(len(miss_mech)),
        }

    return {"stats": stats, "windows": rows}


def verdict(primary: dict) -> dict:
    s = primary["stats"]
    n = s["n_completed"]
    miss_rate = s["miss_rate_completed"]
    d60 = s["n60"]["diff_mean"]
    md60 = s["n60"]["matched_diff_mean"]

    if n < MIN_WINDOWS:
        v, reason = "证据不足", f"已完结窗口样本 {n} < {MIN_WINDOWS}，不足以下结论"
    elif miss_rate is None:
        v, reason = "证据不足", "无已完结窗口可算错过率"
    elif miss_rate >= MISS_RATE_KILL:
        v, reason = "无价值", f"错过率 {miss_rate:.1%} ≥ 2/3，时机精度沦为抽签"
    elif d60 is None:
        v, reason = "证据不足", "60 日主口径无可算样本"
    elif d60 >= DIFF60_VALUE_LINE and (md60 is not None and md60 > 0):
        v, reason = "有价值", (
            f"全窗 60 日平均差 {d60:+.2%} ≥ +2.0pp 且匹配窗时机改善 {md60:+.2%} > 0"
        )
    elif d60 < 0:
        v, reason = "无价值", f"全窗 60 日平均差 {d60:+.2%} < 0，挑时点反而更差"
    else:
        v, reason = "证据不足", f"改善 0 ≤ {d60:+.2%} < +2.0pp，太薄撑不起分层复杂度"
    return {"verdict": v, "reason": reason}


def main() -> None:
    df = load_aligned()
    primary = study(df, FULL_BAND_EDGE, "主口径：上月末B200<43.33（冠军满仓档）")
    sens = study(df, NONZERO_BAND_EDGE, "敏感性：上月末B200<56.67（非空仓档，不参与判定）")
    v = verdict(primary)

    result = {
        "symbol": SYMBOL,
        "data_range": [str(df.index[0].date()), str(df.index[-1].date())],
        "primary": primary,
        "sensitivity": sens,
        "verdict": v,
        "criteria_echo": {
            "min_completed_windows": MIN_WINDOWS,
            "miss_rate_kill": round(MISS_RATE_KILL, 4),
            "diff60_value_line": DIFF60_VALUE_LINE,
            "primary_N": PRIMARY_N,
            "note": "判定线与 docstring 预注册一致，跑前写死",
        },
    }

    canon = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canon.encode("utf-8")).hexdigest()

    out_dir = "/tmp/agent_AC"
    os.makedirs(out_dir, exist_ok=True)
    seed = os.environ.get("PYTHONHASHSEED", "x")
    with open(os.path.join(out_dir, f"result_{seed}.json"), "w", encoding="utf-8") as f:
        f.write(canon)
    with open(os.path.join(out_dir, f"result_{seed}.sha256"), "w", encoding="utf-8") as f:
        f.write(digest + "\n")

    s = primary["stats"]
    print("=" * 76)
    print(f"标的 {SYMBOL} 数据 {result['data_range'][0]} → {result['data_range'][1]}")
    print(
        f"主口径：窗口总数 {s['n_windows_total']}（已完结 {s['n_completed']} + 进行中 {s['n_ongoing']}），"
        f"已完结错过 {s['n_missed_completed']}（错过率 {s['miss_rate_completed']:.1%}），"
        f"匹配 {s['n_matched_total']}"
    )
    for n in HORIZONS:
        st = s[f"n{n}"]

        def fmt(x, pct=True):
            if x is None:
                return "  —"
            return f"{x:+.2%}" if pct else f"{x}"

        print(
            f"N={n:>3}: 纳入 {st['n_full_eval']:>2}（删失 {st['n_censored']}）"
            f" | 机械均值 {fmt(st['mech_mean'])}"
            f" | 分层(错过记0) {fmt(st['layered_mean_incl_miss0'])}"
            f" | 全窗差 {fmt(st['diff_mean'])}（中位 {fmt(st['diff_median'])}，"
            f"胜率 {fmt(st['diff_win_rate'], False)}）"
            f" | 匹配窗差 {fmt(st['matched_diff_mean'])}"
            f"（中位 {fmt(st['matched_diff_median'])}，胜率 {fmt(st['matched_diff_win_rate'], False)}，"
            f"n={st['n_matched_eval']}）"
            f" | 错过窗机械均值 {fmt(st['missed_mech_mean'])}（n={st['missed_mech_n_eval']}）"
        )
    print("-" * 76)
    print("主口径逐窗口明细（N=60）：")
    print(
        f"{'窗口起':<11}{'窗口止':<11}{'月数':>3}{'决策B200':>9}{'状态':>5}"
        f"{'信号日':<11}{'等待日':>5}{'机械60日':>9}{'短信号60日':>10}"
    )
    for r in primary["windows"]:
        status = "进行中" if r["ongoing"] else ("错过" if r["missed"] else "入场")

        def fr(x):
            if x is None:
                return "  删失—"
            return f"{x:+.1%}"

        mech = fr(r["mech_ret60"])
        sh = "   —" if r["missed"] else fr(r["short_ret60"])
        b200s = "NA" if r["b200_dec"] is None else f"{r['b200_dec']:.1f}"
        wait = "—" if r["wait_days"] is None else f"{r['wait_days']}"
        print(
            f"{r['start']:<11}{r['end']:<11}{r['months']:>3}{b200s:>9}{status:>5}"
            f"{r['sig_date'] or '—':<11}{wait:>5}{mech:>9}{sh:>10}"
        )
    print("-" * 76)
    ss = sens["stats"]

    def fmt2(x):
        return "—" if x is None else f"{x:+.2%}"

    print(
        f"敏感性（非空仓档56.67）：窗口 {ss['n_windows_total']}"
        f"（完结 {ss['n_completed']}，进行中 {ss['n_ongoing']}），"
        f"错过率 {ss['miss_rate_completed'] if ss['miss_rate_completed'] is None else format(ss['miss_rate_completed'], '.1%')}"
        f"，全窗差60 {fmt2(ss['n60']['diff_mean'])}，"
        f"匹配窗差60 {fmt2(ss['n60']['matched_diff_mean'])}"
    )
    print("-" * 76)
    print(f"判定：{v['verdict']} —— {v['reason']}")
    print(f"sha256(PYTHONHASHSEED={seed}): {digest}")


if __name__ == "__main__":
    main()
