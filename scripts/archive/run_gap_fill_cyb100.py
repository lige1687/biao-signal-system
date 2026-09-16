#!/usr/bin/env python3
"""宽基缺口补齐 · 科创100（000698）三档逆势回测 · 预注册（2026-09-02，跑前写死，跑后不改）。

Prompt X 阶段二：阶段一确认科创100 为零覆盖缺口。本脚本套用现有 A 股
三档逆势框架（全A等权宽度 cn_all 定档，第 8/14 轮已验协议），不发明新规则。

【数据口径（跑前写死）】
- 标的行情 = docs/experiments/raw/gap_fill/sh000698_index.parquet（新浪源
  stock_zh_index_daily，2020-01-02→2026-09-02，1617 行，抓取时间 2026-09-02；
  三个源中东财被本机代理拦截、腾讯无 2020 前数据，新浪为最长可用）。
- 宽度 = cn_all（全A等权宽度 B200，~/.lei_signal_lab/cache/timing/
  breadth_cn_all.parquet，截至 2026-08-27）。对齐 = 交易日 inner join，
  对齐后窗口 2020-01-02→2026-08-27（≈6.6 年）。
- 参照组行情 = 本地 timing 缓存（截至 2026-08-27）。
- 指数口径披露：科创100 指数 2023-08 发布（基日 2015-12-31），2020-01 至
  2023-08 段为发布日回溯计算值；ETF 载体（588800 等）2023-08 才上市。
  回测为回溯指数口径，与科创50（阶段一 §3）同一性质的样本短问题。

【第一步：档位线选择规则（先于任何回测执行，写死）】
特征向量 = (年化波动率, |最大回撤|)，共同窗 2020-01-02→2026-08-27 日收益。
- 参照组 A（宽基 30/70 线）：创业板 399006、科创50 588000、中证1000 512100。
- 参照组 B（行业 40/60 线）：新能源车 399976、白酒 399997、有色 000819、银行 399986。
- 两组 7 个参照标的合并算各特征的均值/标准差 → z-score 标准化；
  科创100 到两组特征中位数向量的欧氏距离，近者为主档位线；
  距离差 < 0.25σ 判「无显著归属」→ 用宽基先验 30/70（执行手册执行规则
  第 47 行：A 股宽基进攻组统一 43.3/56.7）。另一档位线只作邻域披露，不参与判定。

【主回测（复用 full_audit_20260827.py 第十四轮协议）】
BASE = ladder / indicator=b200 / n_bands=3 / edge_mode=fixed / direction=contrarian
       / gamma=1.0 / min_trade=0.05 / fee_bps=10 / breadth=cn_all。
变体 = 主档位线×{无闸, +MA200闸(cap=0)}；邻档位线×{无闸, +MA200闸}（仅披露）。
三窗 = 全窗 / 前半(end=中点日) / 后半(start=中点日)，中点=对齐后行数一半处
（复用 half_date 语义）。
【入选标准（预注册，沿用第八/十四轮）】进攻入选 = 无闸版三窗超额全 > 0；
「闸版入选」= 闸版三窗超额全 > 0（两版分别判定，都不过 = 不入选）。

【稳健性检验（预注册）】
1. 起点偏移：月度起点 2020-01→2022-07 共 31 个，每个起点至窗口末（≥4.1 年），
   主档位线无闸版；判定 = 超额>0 的起点数 ≥ 29/31（94%）为「起点稳健」，
   全 31 为「起点全占优」；< 29 不通过。
2. 参数邻域：low∈{35,40,43.3,45,50} × high∈{50,55,56.7,60,65}，
   排除 low≥high 的格 = 24 格（复用 portfolio-params-pool E1 网格），无闸全窗；
   判定 = 超额>0 格数 ≥ 20/24（83%）为「高原」且主档位线所在格超额 > 0。
3. 留一（留年份）：逐个剔除日历年 2020-2026（7 个），策略/持有日收益序列
   同步剔除后各自复利重算年化差；判定 = 7/7 全 > 0。
4. 安慰剂：cn_all B200 序列循环平移 100 次（平移量 ∈ [260, N-260]，
   rng=PCG64 seed 20260902 抽样去重），主档位线无闸全窗超额；
   判定 = 真实超额 > 100 个安慰剂超额的 95 分位；另披露是否 > max（100% 分位）。
5. 阴性对照：黄金 518880 同框架同窗（30/70 无闸 + 40/60 无闸），
   预期超额 ≤ 0（先例：宽度对无关资产无效，kuandu-quanzhan 黄金 -2.6%）；
   若任一档位线黄金超额 > +3pp → 框架在本窗存在机械性收益偏置，
   如实报告并将科创100 判定整体降级表述。

【认证强度上限声明（预注册，不因结果调整）】
样本 6.6 年 = 冠军三档 16.2 年的 41%；每半窗仅 ≈3.3 年；样本内无 2015/2018
型跨年度深熊（最深为 2021-2024 科创深跌）。即使全部检验通过，认证上限
= 「短样本全检通过」，不得表述为与冠军三档（16 年跨周期）同等级。
若三窗/邻域/起点任一不过 → 如实判负，不得降格凑「测过了」。

【红线遵守】不改 src/ 生产代码；只输出统计数字与判定，不产生买卖点、
不合成数据、不因结果调整判定线。

输出：docs/experiments/raw/gap_fill/cyb100_gapfill_results.json
复现：PYTHONHASHSEED=0 python3 scripts/run_gap_fill_cyb100.py
     （再以 PYTHONHASHSEED=42 复跑核对哈希）
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from lei_signal.timing_backtest.data import (
    TIMING_CACHE_DIR,
    align_index_breadth,
    load_breadth,
)
from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import summarize_run
from lei_signal.timing_backtest.strategies import (
    LadderParams,
    TrendGate,
    build_target,
)

RAW = REPO / "docs/experiments/raw/gap_fill"
OUT = RAW / "cyb100_gapfill_results.json"

# ── 预注册常量（跑前写死）──
FEE_BPS = 10.0
MIN_TRADE = 0.05
GAMMA = 1.0
NEIGHBORHOOD_LOWS = [35.0, 40.0, 43.3, 45.0, 50.0]
NEIGHBORHOOD_HIGHS = [50.0, 55.0, 56.7, 60.0, 65.0]
HIGH_GRID_MIN = 20  # 24 格中至少 20 格超额>0
STARTS_MIN = 29     # 31 个起点中至少 29 个超额>0
PLACEBO_Q = 0.95    # 真实超额须超安慰剂 95 分位
PLACEBO_N = 100
PLACEBO_SEED = 20260902
GOLD_BIAS_TH = 0.03  # 黄金对照机械偏置线 +3pp
GROUP_TIE_SIGMA = 0.25  # 档位线归属无显著差距离线

REF_GROUP_A = {  # 宽基 30/70 组
    "399006": "创业板指", "588000": "科创50", "512100": "中证1000",
}
REF_GROUP_B = {  # 行业 40/60 组
    "399976": "新能源车", "399997": "中证白酒", "000819": "有色金属", "399986": "中证银行",
}


def load_local_bars(symbol: str) -> pd.DataFrame:
    df = pd.read_parquet(TIMING_CACHE_DIR / f"{symbol}.parquet")
    for col in ("high", "low"):
        if col not in df.columns:
            df[col] = df[["open", "close"]].max(axis=1) if col == "high" else df[["open", "close"]].min(axis=1)
    return df[~df.index.duplicated(keep="last")].sort_index()[["open", "high", "low", "close"]]


def run_ladder(
    aligned: pd.DataFrame, low_edge: float, high_edge: float, gate: bool,
    start=None, end=None,
) -> dict:
    """三档回测一次（复用 build_target + simulate + summarize_run）。"""
    window = aligned.loc[start:end] if (start or end) else aligned
    ladder = LadderParams(
        indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
        min_weight=0.0, gamma=GAMMA, low_edge=low_edge, high_edge=high_edge,
    )
    gate_p = TrendGate(mode="ma200" if gate else "off", cap=0.0)
    warmup = aligned.loc[: window.index[0]].iloc[:-1]
    target = build_target(aligned, ladder, None, gate_p, warmup, vol_target=0.0)
    result = simulate(window, target.loc[window.index], fee_bps=FEE_BPS, min_trade=MIN_TRADE)
    return summarize_run(result.daily, result.trades) | {"daily": result.daily}


def feat_vector(close: pd.Series) -> tuple[float, float]:
    """(年化波动率, |最大回撤|)。"""
    ret = close.pct_change().dropna()
    vol = float(ret.std(ddof=1) * np.sqrt(252.0))
    dd = close / close.cummax() - 1.0
    return vol, float(abs(dd.min()))


def znorm(v: float, mu: dict, sd: dict) -> tuple[float, float]:
    return ((v[0] - mu["vol"]) / sd["vol"], (v[1] - mu["mdd"]) / sd["mdd"])


def main() -> None:
    results: dict = {"criteria": {
        "fee_bps": FEE_BPS, "min_trade": MIN_TRADE, "gamma": GAMMA,
        "start_offset_rule": "月度起点2020-01→2022-07共31个，≥29/31超额>0",
        "neighborhood_rule": "low{35,40,43.3,45,50}×high{50,55,56.7,60,65}有效24格，≥20格超额>0且主参数格>0",
        "loo_rule": "逐年剔除2020-2026共7次，7/7超额>0",
        "placebo_rule": f"B200循环平移{PLACEBO_N}次(seed={PLACEBO_SEED})，真实超额>95分位",
        "gold_control_rule": f"黄金518880同框架，任一档位线超额>+{GOLD_BIAS_TH:.0%}判机械偏置",
        "band_selection_rule": "z-score特征(年化波动,|MDD|)到两组中位数欧氏距离，<0.25σ用宽基先验30/70",
        "entry_rule": "无闸版三窗超额全>0=入选；闸版三窗全>0=闸版入选",
        "certification_cap": "短样本全检通过≠冠军级（6.6年无2015/2018型深熊）",
    }}

    # ── 数据装载与对齐 ──
    bars = pd.read_parquet(RAW / "sh000698_index.parquet")
    bars = bars[~bars.index.duplicated(keep="last")].sort_index()[["open", "high", "low", "close"]]
    breadth = load_breadth("cn_all")
    aligned = align_index_breadth(bars, breadth)
    results["data"] = {
        "bars": "raw/gap_fill/sh000698_index.parquet 新浪源 2026-09-02抓取",
        "aligned_rows": int(len(aligned)),
        "window": [str(aligned.index[0].date()), str(aligned.index[-1].date())],
        "breadth_end": "cn_all 截至 2026-08-27（对齐窗口右端被宽度截断，全标的同口径）",
        "index_retro_note": "科创100指数2023-08发布，2020-01→2023-08为回溯计算值；ETF载体2023-08后存在",
    }

    # ── 第一步：档位线选择 ──
    win = aligned["close"]
    f_cyb = feat_vector(win)
    feats_a = {s: feat_vector(load_local_bars(s)["close"].loc[win.index[0]: win.index[-1]]) for s in REF_GROUP_A}
    feats_b = {s: feat_vector(load_local_bars(s)["close"].loc[win.index[0]: win.index[-1]]) for s in REF_GROUP_B}
    all_f = list(feats_a.values()) + list(feats_b.values())
    mu = {"vol": float(np.mean([f[0] for f in all_f])), "mdd": float(np.mean([f[1] for f in all_f]))}
    sd = {"vol": float(np.std([f[0] for f in all_f], ddof=1)), "mdd": float(np.std([f[1] for f in all_f], ddof=1))}
    med_a = np.median(np.array([znorm(f, mu, sd) for f in feats_a.values()]), axis=0)
    med_b = np.median(np.array([znorm(f, mu, sd) for f in feats_b.values()]), axis=0)
    z_cyb = np.array(znorm(f_cyb, mu, sd))
    dist_a, dist_b = float(np.linalg.norm(z_cyb - med_a)), float(np.linalg.norm(z_cyb - med_b))
    if abs(dist_a - dist_b) < GROUP_TIE_SIGMA:
        main_edges, alt_edges, band_reason = (30.0, 70.0), (40.0, 60.0), (
            f"距离差|{dist_a:.2f}-{dist_b:.2f}|<{GROUP_TIE_SIGMA}σ 判无显著归属 → 宽基先验30/70")
    elif dist_a < dist_b:
        main_edges, alt_edges, band_reason = (30.0, 70.0), (40.0, 60.0), (
            f"距宽基组A({dist_a:.2f}σ) < 距行业组B({dist_b:.2f}σ)")
    else:
        main_edges, alt_edges, band_reason = (40.0, 60.0), (30.0, 70.0), (
            f"距行业组B({dist_b:.2f}σ) < 距宽基组A({dist_a:.2f}σ)")
    results["band_selection"] = {
        "cyb100_features": {"ann_vol": round(f_cyb[0], 4), "abs_mdd": round(f_cyb[1], 4)},
        "ref_group_A_30_70": {REF_GROUP_A[s]: {"ann_vol": round(f[0], 4), "abs_mdd": round(f[1], 4)} for s, f in feats_a.items()},
        "ref_group_B_40_60": {REF_GROUP_B[s]: {"ann_vol": round(f[0], 4), "abs_mdd": round(f[1], 4)} for s, f in feats_b.items()},
        "dist_A": round(dist_a, 3), "dist_B": round(dist_b, 3),
        "main_edges": list(main_edges), "alt_edges": list(alt_edges),
        "reason": band_reason,
    }
    print(f"[档位线] {band_reason} → 主 {main_edges} / 邻 {alt_edges}")

    # ── 主回测：三窗 × 两档位线 × 两闸 ──
    mid = aligned.index[len(aligned) // 2]
    main_backtests: dict = {}
    for tag, (lo, hi) in (("main", main_edges), ("alt", alt_edges)):
        for gate in (False, True):
            key = f"{tag}_{lo}_{hi}_{'gate' if gate else 'nogate'}"
            full = run_ladder(aligned, lo, hi, gate)
            h1 = run_ladder(aligned, lo, hi, gate, end=mid)
            h2 = run_ladder(aligned, lo, hi, gate, start=mid)
            three = [full["excess_cagr"], h1["excess_cagr"], h2["excess_cagr"]]
            main_backtests[key] = {
                "full": {k: full[k] for k in ("strategy_cagr", "benchmark_cagr", "excess_cagr", "strategy_mdd", "benchmark_mdd", "calmar", "avg_weight", "n_trades", "years")},
                "h1_excess": h1["excess_cagr"], "h2_excess": h2["excess_cagr"],
                "three_window_all_positive": bool(all(x > 0 for x in three)),
                "mid_date": str(mid.date()),
                "_daily": full["daily"], "_h1": h1, "_h2": h2,
            }
            print(f"[三窗] {key}: 全{three[0]:+.1%} 前{h1['excess_cagr']:+.1%} 后{h2['excess_cagr']:+.1%}"
                  f"  MDD {full['strategy_mdd']:.0%} vs {full['benchmark_mdd']:.0%}")

    entry_nogate = main_backtests[f"main_{main_edges[0]}_{main_edges[1]}_nogate"]["three_window_all_positive"]
    entry_gate = main_backtests[f"main_{main_edges[0]}_{main_edges[1]}_gate"]["three_window_all_positive"]

    # ── 起点偏移（月度起点 31 个）──
    start_dates = pd.date_range("2020-01-01", "2022-07-01", freq="MS")
    start_offset = []
    for sd in start_dates:
        ts = aligned.index[aligned.index >= sd][0]
        r = run_ladder(aligned, main_edges[0], main_edges[1], False, start=ts)
        start_offset.append({"start": str(ts.date()), "excess": round(r["excess_cagr"], 4)})
    n_pos = sum(1 for s in start_offset if s["excess"] > 0)
    robustness_starts = {"n_starts": len(start_offset), "n_positive": n_pos,
                         "pass": bool(n_pos >= STARTS_MIN)}
    print(f"[起点偏移] {n_pos}/{len(start_offset)} 超额>0 → {'过' if robustness_starts['pass'] else '不过'}")

    # ── 参数邻域 24 格 ──
    grid = []
    for lo in NEIGHBORHOOD_LOWS:
        for hi in NEIGHBORHOOD_HIGHS:
            if lo >= hi:
                continue
            r = run_ladder(aligned, lo, hi, False)
            grid.append({"low": lo, "high": hi, "excess": round(r["excess_cagr"], 4)})
    n_grid_pos = sum(1 for g in grid if g["excess"] > 0)
    main_cell = [g for g in grid if abs(g["low"] - main_edges[0]) < 1e-9 and abs(g["high"] - main_edges[1]) < 1e-9]
    main_cell_pos = bool(main_cell and main_cell[0]["excess"] > 0)
    robustness_grid = {"n_cells": len(grid), "n_positive": n_grid_pos,
                       "main_cell_positive": main_cell_pos,
                       "pass": bool(n_grid_pos >= HIGH_GRID_MIN and main_cell_pos)}
    print(f"[邻域] {n_grid_pos}/{len(grid)} 格超额>0, 主参数格{main_cell[0]['excess'] if main_cell else 'N/A'} → {'过' if robustness_grid['pass'] else '不过'}")

    # ── 留一年 7 次 ──
    daily = main_backtests[f"main_{main_edges[0]}_{main_edges[1]}_nogate"]["_daily"]
    sret = daily["equity"].pct_change().dropna()
    bret = daily["benchmark"].pct_change().dropna()
    loo = []
    for yr in sorted(set(daily.index.year)):
        s2 = (1 + sret[sret.index.year != yr]).prod() ** (252 / len(sret[sret.index.year != yr])) - 1
        b2 = (1 + bret[bret.index.year != yr]).prod() ** (252 / len(bret[bret.index.year != yr])) - 1
        loo.append({"excluded_year": yr, "excess": round(s2 - b2, 4)})
    loo_all_pos = all(x["excess"] > 0 for x in loo)
    robustness_loo = {"n": len(loo), "all_positive": loo_all_pos, "pass": loo_all_pos}
    print(f"[留一] {sum(1 for x in loo if x['excess']>0)}/{len(loo)} 年剔除后超额>0 → {'过' if loo_all_pos else '不过'}")

    # ── 安慰剂：B200 循环平移 100 次 ──
    rng = np.random.default_rng(PLACEBO_SEED)
    n_shift_pool = len(aligned)
    shifts = rng.choice(np.arange(260, n_shift_pool - 260), size=PLACEBO_N * 2, replace=False)
    b200 = aligned["b200"].to_numpy(dtype=float)
    placebo_excess = []
    for sh in shifts[:PLACEBO_N]:
        fake_b = pd.Series(np.roll(b200, int(sh)), index=aligned.index)
        fake_aligned = aligned.copy()
        fake_aligned["b200"] = fake_b
        r = run_ladder(fake_aligned, main_edges[0], main_edges[1], False)
        placebo_excess.append(round(r["excess_cagr"], 4))
    real_excess = main_backtests[f"main_{main_edges[0]}_{main_edges[1]}_nogate"]["full"]["excess_cagr"]
    p95 = float(np.percentile(placebo_excess, 95))
    robustness_placebo = {
        "real_excess": round(real_excess, 4), "placebo_p95": round(p95, 4),
        "placebo_max": round(max(placebo_excess), 4),
        "pass_p95": bool(real_excess > p95),
        "pass_max": bool(real_excess > max(placebo_excess)),
    }
    print(f"[安慰剂] 真实{real_excess:+.1%} vs p95 {p95:+.1%} max {max(placebo_excess):+.1%}"
          f" → {'过p95' if robustness_placebo['pass_p95'] else '不过'}")

    # ── 阴性对照：黄金同框架同窗 ──
    gold_bars = load_local_bars("518880")
    gold_aligned = align_index_breadth(gold_bars, breadth)
    gold_aligned = gold_aligned.loc[aligned.index[0]:]
    gold_ctrl = {}
    for tag, (lo, hi) in (("30_70", (30.0, 70.0)), ("40_60", (40.0, 60.0))):
        r = run_ladder(gold_aligned, lo, hi, False)
        gold_ctrl[tag] = {k: round(r[k], 4) for k in ("excess_cagr", "strategy_mdd", "benchmark_mdd")}
    gold_bias = max(gold_ctrl["30_70"]["excess_cagr"], gold_ctrl["40_60"]["excess_cagr"])
    gold_pass = bool(gold_bias <= GOLD_BIAS_TH)
    print(f"[黄金对照] 30/70 {gold_ctrl['30_70']['excess_cagr']:+.1%} / 40/60 {gold_ctrl['40_60']['excess_cagr']:+.1%}"
          f" → {'对照有效' if gold_pass else '机械偏置警告'}")

    # ── 汇总判定 ──
    overall_pass = entry_nogate and robustness_starts["pass"] and robustness_grid["pass"] \
        and robustness_loo["pass"] and robustness_placebo["pass_p95"] and gold_pass
    results["backtests"] = {
        k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
        for k, v in main_backtests.items()
    }
    results["start_offset"] = robustness_starts | {"detail": start_offset}
    results["neighborhood"] = robustness_grid | {"grid": grid}
    results["loo_year"] = robustness_loo | {"detail": loo}
    results["placebo"] = robustness_placebo | {"distribution_head": sorted(placebo_excess, reverse=True)[:5]}
    results["gold_control"] = {"detail": gold_ctrl, "pass": gold_pass}
    results["verdict"] = {
        "entry_nogate": bool(entry_nogate), "entry_gate": bool(entry_gate),
        "starts": robustness_starts["pass"], "grid": robustness_grid["pass"],
        "loo": robustness_loo["pass"], "placebo_p95": robustness_placebo["pass_p95"],
        "gold_control": gold_pass,
        "overall": bool(overall_pass),
        "certification": (
            "短样本全检通过（三窗+起点+邻域+留一+安慰剂+对照）——认证上限=短样本，"
            "样本6.6年无2015/2018型深熊，不得表述为与冠军三档16年跨周期同等级"
            if overall_pass else
            "未通过全部预注册检验，按预注册如实判负（见各项分判定）"
        ),
    }
    print(f"\n[总判定] {'短样本全检通过' if overall_pass else '判负'}"
          f"（三窗{'✓' if entry_nogate else '✗'} 起点{'✓' if robustness_starts['pass'] else '✗'}"
          f" 邻域{'✓' if robustness_grid['pass'] else '✗'} 留一{'✓' if robustness_loo['pass'] else '✗'}"
          f" 安慰剂{'✓' if robustness_placebo['pass_p95'] else '✗'} 黄金{'✓' if gold_pass else '✗'}）")

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    h = hashlib.sha256(json.dumps(results, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    print(f"输出: {OUT}")
    print(f"HASH(规范化JSON): {h}")


if __name__ == "__main__":
    main()
