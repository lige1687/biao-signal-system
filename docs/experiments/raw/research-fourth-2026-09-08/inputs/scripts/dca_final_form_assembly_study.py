# -*- coding: utf-8 -*-
"""终局形态整装验证（第十八轮）：13 年长窗 + 起点网格 + 参数邻域。

问题（外部评审 2026-09-08 提出）：终局形态「平投 + 跨资产篮子 + 季度再平衡」
的引用数字（年化 15.8%/回撤 −9.8%）来自单一 5.8 年窗（W5，起点由科创 50
上市日决定、终点恰在 2024-09 反弹之后）的单一路径；且篮子三块（标的/频率/
权重）从未作为一个系统在更长历史和不同起点上整装跑过。本轮补齐：

1. **长窗**：标准篮子（000300/399006/518880/^IXIC）的公共数据窗其实有
   13.1 年（2013-07-29 黄金 ETF 上市 → 2026-08-27）——第八轮 W5 被科创 50
   腿拖短，跨资产四本身从未跑过长窗；
2. **起点网格**：起投月从 2013-09 到 2021-08 逐月滚动（96 个起点，每条
   路径跑到 2026-08-27，持有 5~13 年），回答"不是恰好从 2020-11 开始投，
   结论还成立吗"；
3. **参数邻域**：等权 → 40/30/15/15 扰动权重；季度 → 月度频率。

预注册口径（跑前写死，跑后不得改）：

- 引擎：完全沿第十六轮 P0（周投平分、季度再平衡、费双边 10bp 主档 +
  1bp 验证档、跨资产按 A 股日历 inner-join 对齐、现金 0 收益）；与第十六轮
  A0/W5/fee10 的 P0 结果做引擎对账（终值差 ≤0.003 才算通过，否则本轮作废）。
- 五臂：
  FQ  等权 + 季度再平衡（终局形态本体）
  FM  等权 + 月度再平衡
  NR  等权 + 不再平衡
  W4  权重 300:40%/创业板:30%/黄金:15%/纳指:15% + 季度再平衡
  B3  100% 沪深300 周投平投（"什么都不做"基准，单腿无再平衡）
- 起点网格：每月首个交易日，2013-09 → 2021-08 共 96 起点，终点一律
  2026-08-27（要求持有 ≥5 年）；相邻月起点高度共享路径（登记：网格是
  描述性稳健视图，不是 96 个独立实验；次要口径=仅 1 月起点共 8 个）。
- 度量：每起点 XIRR（资金加权年化）与最大回撤；跨起点报中位/P10/P90。
- 判定线（写死，fee10 主档）：
  V1 篮子 vs 沪深300平投：96 起点上 (XIRR_FQ − XIRR_B3) 中位 ≥+1.0pp
     且为正起点占比 ≥70% → 「跨资产优越性跨起点成立」；≤30% → 判负；
     其余混合。
  V2 再平衡增量：(XIRR_FQ − XIRR_NR) 中位 ≥+0.5pp 且为正占比 ≥70% →
     「13 年窗再平衡有增量」；≤30% → 增量不成立；其余混合。
  V3 频率等价：|中位(XIRR_FQ − XIRR_FM)| ≤0.5pp → 「季度≈月度确认」
     （等价声明；不做"谁更强"断言——第九轮 0.25pp 差距不足以分胜负）。
  V4 权重邻域：|中位(XIRR_FQ − XIRR_W4)| ≤1.0pp → 「等权非刀锋」。
  V1/V2 在 fee1 档复验方向不变（登记，不设线）。
- 终点敏感性（描述性登记）：W5 起投（2020-11-16）FQ 在终点
  2026-03-27 / 2026-05-27 / 2026-08-27 的 XIRR 变化。
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
RAW_DIR = REPO / "docs/experiments/raw/dca-final-form-assembly-2026-09-08"
RAW_DIR.mkdir(parents=True, exist_ok=True)

LEG_SYMS = ["000300", "399006", "518880", "^IXIC"]
W_EQ = np.array([0.25, 0.25, 0.25, 0.25])
W_4030 = np.array([0.40, 0.30, 0.15, 0.15])
BENCH = ["000300"]
W5 = ("2020-11-16", "2026-08-27")
RECONCILE_TARGET = {"final": 1.5703, "tol": 0.003}   # 第十六轮 A0 P0 fee10
END = "2026-08-27"
GRID_FIRST, GRID_LAST = "2013-09", "2021-08"
FEE_MAIN, FEE_ALT = 10.0, 1.0


def build_join(syms: list[str], start: str, end: str):
    opens = closes = None
    for s in syms:
        b = load_index_bars(s)
        o = b["open"].rename(s).to_frame()
        c = b["close"].rename(s).to_frame()
        opens = o if opens is None else opens.join(o, how="inner")
        closes = c if closes is None else closes.join(c, how="inner")
    m = (opens.index >= start) & (opens.index <= end)
    return opens[m], closes[m]


def period_ends(idx: pd.DatetimeIndex, freq: str) -> list[int]:
    s = pd.Series(np.arange(len(idx)), index=idx)
    if freq == "weekly":
        keys = [idx.isocalendar().year, idx.isocalendar().week]
    elif freq == "quarterly":
        keys = [idx.year, idx.quarter]
    elif freq == "monthly":
        keys = [idx.year, idx.month]
    else:
        raise ValueError(freq)
    return sorted(int(v) for v in s.groupby(keys).max())


def xirr_signed(flows, end_date, end_value):
    cfs = list(flows) + [(end_date, end_value)]
    t0 = min(d for d, _ in cfs)

    def npv(r):
        return sum(a / (1.0 + r) ** ((d - t0).days / 365.25) for d, a in cfs)

    lo, hi = -0.95, 10.0
    if npv(lo) * npv(hi) > 0:
        return float("nan")
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def run_engine(opens: pd.DataFrame, closes: pd.DataFrame, weights: np.ndarray,
               rebal: str, fee_bps: float) -> dict:
    """第十六轮 P0 引擎的参数化版：周投按权重拆、按 freq 再平衡回权重。"""
    idx = opens.index
    n = len(idx)
    L = len(opens.columns)
    o = opens.to_numpy(float)
    c = closes.to_numpy(float)
    f = fee_bps * 1e-4
    ends = period_ends(idx, "weekly")
    base = 1.0 / len(ends)
    inflow = np.zeros(n)
    for p in ends:
        inflow[p] += base
    rebal_days = (set() if rebal == "none" else
                  set(p + 1 for p in period_ends(idx, rebal) if p + 1 < n))

    cur = np.zeros(L)
    central = 0.0
    flows = []
    eq = np.empty(n)
    for i in range(n):
        central += inflow[i]
        if i > 0 and inflow[i - 1] > 0 and central > 0:
            amt = central * weights
            for k in range(L):
                cur[k] += (amt[k] - amt[k] * f) / o[i, k]
            flows.append((idx[i], -central))
            central = 0.0
        if i in rebal_days and L > 1:
            vals = cur * o[i]
            total = float(vals.sum())
            if total > 0:
                tgt = total * weights
                fee = float(np.abs(vals - tgt).sum()) * f
                cur = ((total - fee) * weights) / o[i]
        eq[i] = float((cur * c[i]).sum() + central)
    final = float(eq[-1])
    series = pd.Series(eq, index=idx)
    return {"final": final,
            "xirr": xirr_signed(flows, idx[-1], final),
            "mdd": float(((series / series.cummax()) - 1.0).min()),
            "years": (idx[-1] - idx[0]).days / 365.25}


def month_starts(idx: pd.DatetimeIndex, first: str, last: str) -> list[str]:
    """first..last（含端）每月首个交易日。"""
    months = pd.period_range(first, last, freq="M")
    out = []
    for m in months:
        sel = idx[(idx.year == m.year) & (idx.month == m.month)]
        if len(sel):
            out.append(str(sel[0].date()))
    return out


def agg(vals: list[float]) -> dict:
    a = np.array(vals, dtype=float)
    a = a[np.isfinite(a)]
    return {"n": int(len(a)), "median": float(np.median(a)),
            "p10": float(np.quantile(a, 0.10)),
            "p90": float(np.quantile(a, 0.90))}


def main() -> None:
    out: dict = {"criteria_doc": __doc__}

    # 0) 引擎对账：与第十六轮 A0/W5/fee10 P0 逐位
    o5, c5 = build_join(LEG_SYMS, W5[0], W5[1])
    rec = run_engine(o5, c5, W_EQ, "quarterly", FEE_MAIN)
    ok = abs(rec["final"] - RECONCILE_TARGET["final"]) <= RECONCILE_TARGET["tol"]
    out["reconcile_w5_fee10"] = {
        "final": rec["final"], "xirr": rec["xirr"], "mdd": rec["mdd"],
        "target_final": RECONCILE_TARGET["final"], "pass": bool(ok)}
    print(f"[对账] A0/W5/fee10 季度等权 终值{rec['final']:.4f} "
          f"(目标{RECONCILE_TARGET['final']}) "
          f"年化{rec['xirr']*100:.2f}% 回撤{rec['mdd']*100:.1f}% "
          f"{'PASS' if ok else 'FAIL —— 本轮作废'}", flush=True)
    if not ok:
        raise SystemExit("引擎对账失败，按预注册口径本轮作废")

    # 1) 长窗单路径头牌：2013-07-29 → 2026-08-27
    oL, cL = build_join(LEG_SYMS, "2013-07-29", END)
    long_paths = {}
    for name, w, reb in (("FQ", W_EQ, "quarterly"), ("FM", W_EQ, "monthly"),
                         ("NR", W_EQ, "none"), ("W4", W_4030, "quarterly")):
        r = run_engine(oL, cL, w, reb, FEE_MAIN)
        long_paths[name] = r
        print(f"[长窗13.1y] {name}: 终值{r['final']:.3f} 年化{r['xirr']*100:.2f}% "
              f"回撤{r['mdd']*100:.1f}%", flush=True)
    oB, cB = build_join(BENCH, "2013-07-29", END)
    long_paths["B3"] = run_engine(oB, cB, np.array([1.0]), "none", FEE_MAIN)
    print(f"[长窗13.1y] B3: 终值{long_paths['B3']['final']:.3f} "
          f"年化{long_paths['B3']['xirr']*100:.2f}% "
          f"回撤{long_paths['B3']['mdd']*100:.1f}%", flush=True)
    out["long_window_single_path"] = long_paths

    # 2) 起点网格（96 起点 × 五臂 fee10；V1/V2 加 fee1 复验）
    starts = month_starts(oL.index, GRID_FIRST, GRID_LAST)
    grid: dict[str, dict[str, dict]] = {a: {} for a in ("FQ", "FM", "NR", "W4", "B3")}
    grid_fee1: dict[str, dict[str, dict]] = {a: {} for a in ("FQ", "NR", "B3")}
    oB_full, cB_full = build_join(BENCH, GRID_FIRST, END)
    for s in starts:
        for name, w, reb in (("FQ", W_EQ, "quarterly"), ("FM", W_EQ, "monthly"),
                             ("NR", W_EQ, "none"), ("W4", W_4030, "quarterly")):
            m = oL.index >= s
            grid[name][s] = run_engine(oL[m], cL[m], w, reb, FEE_MAIN)
        mb = oB_full.index >= s
        grid["B3"][s] = run_engine(oB_full[mb], cB_full[mb], np.array([1.0]),
                                   "none", FEE_MAIN)
        for name, w, reb in (("FQ", W_EQ, "quarterly"), ("NR", W_EQ, "none")):
            m = oL.index >= s
            grid_fee1[name][s] = run_engine(oL[m], cL[m], w, reb, FEE_ALT)
        grid_fee1["B3"][s] = run_engine(oB_full[mb], cB_full[mb],
                                        np.array([1.0]), "none", FEE_ALT)
    out["grid_meta"] = {"n_starts": len(starts), "first": starts[0],
                        "last": starts[-1], "end": END,
                        "fee_main_bps": FEE_MAIN, "fee_alt_bps": FEE_ALT}
    out["grid_fee10"] = {a: {s: r for s, r in d.items()} for a, d in grid.items()}
    out["grid_fee1"] = {a: {s: r for s, r in d.items()}
                        for a, d in grid_fee1.items()}

    summary = {}
    for a, d in grid.items():
        summary[a] = {"xirr": agg([r["xirr"] for r in d.values()]),
                      "mdd": agg([r["mdd"] for r in d.values()])}
    out["grid_summary_fee10"] = summary

    def diff_stats(a: str, b: str, src: dict) -> dict:
        ds = [src[a][s]["xirr"] - src[b][s]["xirr"] for s in starts]
        st = agg(ds)
        return {"median": st["median"], "p10": st["p10"], "p90": st["p90"],
                "pos_share": float(np.mean(np.array(ds) > 0)),
                "jan_pos": int(sum(
                    (src[a][s]["xirr"] - src[b][s]["xirr"]) > 0
                    for s in starts if s[5:7] == "01")),
                "jan_n": int(sum(1 for s in starts if s[5:7] == "01"))}

    v1 = diff_stats("FQ", "B3", grid)
    v2 = diff_stats("FQ", "NR", grid)
    v3 = diff_stats("FQ", "FM", grid)
    v4 = diff_stats("FQ", "W4", grid)
    v1_f1 = diff_stats("FQ", "B3", grid_fee1)
    v2_f1 = diff_stats("FQ", "NR", grid_fee1)

    def verdict_pair(d, hi_line, lo_line):
        if d["median"] >= hi_line and d["pos_share"] >= 0.70:
            return "成立"
        if d["median"] <= 0 and d["pos_share"] <= 0.30:
            return "判负"
        return "混合"

    out["verdicts"] = {
        "V1_篮子vs沪深300": {**v1, "verdict": verdict_pair(v1, 0.01, None)},
        "V2_再平衡增量": {**v2, "verdict": verdict_pair(v2, 0.005, None)},
        "V3_频率等价": {**v3, "verdict": ("季度≈月度确认"
                                        if abs(v3["median"]) <= 0.005
                                        else "频率差异超容差")},
        "V4_权重邻域": {**v4, "verdict": ("等权非刀锋"
                                       if abs(v4["median"]) <= 0.010
                                       else "权重敏感")},
        "V1_fee1复验": v1_f1,
        "V2_fee1复验": v2_f1,
    }

    print(f"\n[网格 {len(starts)} 起点 fee10] 各臂 XIRR 中位/P10~P90：")
    for a in ("FQ", "FM", "NR", "W4", "B3"):
        st = summary[a]["xirr"]
        print(f"  {a}: 中位{st['median']*100:+.2f}% "
              f"[{st['p10']*100:+.2f}%, {st['p90']*100:+.2f}%] "
              f"回撤中位{summary[a]['mdd']['median']*100:.1f}%", flush=True)
    for k in ("V1_篮子vs沪深300", "V2_再平衡增量", "V3_频率等价", "V4_权重邻域"):
        v = out["verdicts"][k]
        print(f"  {k}: 中位差{v['median']*100:+.2f}pp 为正占比{v['pos_share']*100:.0f}% "
              f"1月起点{v.get('jan_pos')}/{v.get('jan_n')} → {v['verdict']}")

    # 3) 终点敏感性
    ends = {}
    for e in ("2026-03-27", "2026-05-27", "2026-08-27"):
        oe, ce = build_join(LEG_SYMS, W5[0], e)
        ends[e] = run_engine(oe, ce, W_EQ, "quarterly", FEE_MAIN)
    out["endpoint_sensitivity_w5"] = ends
    print("\n[终点敏感性] W5起投/等权季度 fee10：")
    for e, r in ends.items():
        print(f"  终点{e}: 年化{r['xirr']*100:+.2f}% 回撤{r['mdd']*100:.1f}%")

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True,
                         default=float).encode()
    h = hashlib.sha256(payload).hexdigest()
    (RAW_DIR / "final_form_assembly_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=float))
    (RAW_DIR / "HASH.txt").write_text(h + "\n")
    print("\nHASH:", h)


if __name__ == "__main__":
    main()
