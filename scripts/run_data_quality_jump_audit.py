#!/usr/bin/env python3
"""数据质量审计：A股 ETF 池 13 个复权断裂跳变 × 14轮框架修平对照 · 预注册
（2026-09-02，跑前写死，跑后不改）。

【发现背景】
Prompt X 阶段三进行中，候选×候选相关性核查发现 512100（中证1000ETF）
2022-09-05 单日 +176.3%（B200=38.4 当日三档满仓）。全缓存扫描确认
A股 ETF 池共 9 标的 13 个单日跳变超涨跌停物理限制（A股 ETF ±10%，创业板/
科创板 ETF ±20%），必然为数据源复权断裂，非市场事件。

【跳变清单（预注册，全部|单日收益|>11% 且超标的自身涨跌停限制）】
159928 消费ETF    2021-06-25 -74.5%
510500 中证500ETF 2015-04-15 +248.6%（份额拆分未复权）、2022-08-29 -12.7%
512010 医药ETF    2021-06-28 -73.9%
512100 中证1000ETF 2022-09-05 +176.3%
512200 房地产ETF  2024-08-12 +170.1%
512480 半导体ETF  2021-03-29 -48.9%、2026-07-03 -50.7%
512690 酒ETF      2021-05-17 -48.0%、2021-12-31 -27.1%
512800 银行ETF    2025-07-07 -49.7%
515880 通信ETF    2026-02-03 -65.7%、2026-07-06 -52.1%
不修的合法清单（披露）：159915/588000/399006/399976/980017 的 2024-09/10
（政策行情打板）、399006/159915 的 2025-04-07（关税暴跌）、SZ399001 1991-96
（早期无涨跌停）、美股指数/ETF 2008/2020（真实危机）、US 个股（无涨跌停）。

【修平方法（预注册，最保守）】
对每个跳变日 D：ratio = close[D]/close[D-1交易日]，D 及之后全部
open/high/low/close 同除 ratio（等价于跳变日收益置 0、价格连续化）。
多跳变按时间序依次处理。不引入任何外部数据；这是「消除单点断裂」的
下界修法，不是重建正确复权（后者需真实分红/拆分事件表，登记为欠账）。

【对照框架（与 full_audit_20260827.py 第十四轮完全一致）】
BASE = ladder/b200/3bands/fixed/30-70/contrarian/gamma1/min_trade0.05/
       fee_bps=10/cn_all；变体 = {无闸, +MA200闸(cap=0)}；三窗 = 全窗/
       前半(end=行数中点日)/后半(start=中点日)。
510500 被十四轮排除（EXCLUDED），本审计加跑同框架（其第 9 轮判负结论
「基准过强不适配 -9.8%」的依据在污染数据上）。

【判定标准（预注册）】
- 「结论翻转」= 无闸版三窗超额全>0 的布尔状态在修平前后改变
  （512100/512200 的十四轮入选判定即此布尔）；
- 「数值修正」= 状态不变但全窗超额变化 ≥2pp（披露量级）；
- 510500：修平后若三窗全正 → 标记「原判负依据失效，建议重审」
  （不直接下「入选」结论——完整验证协议不在本审计范围）；
- 科创100 档位线复核：512100 修平后特征向量 (年化波动,|MDD|) 代回
  阶段二预注册距离规则，若主档位线翻转（40/60↔30/70），披露阶段二
  两线结果中另一线的三窗数字（阶段二两线都已跑过，无需新回测）。

【红线遵守】不修改 ~/.lei_signal_lab 缓存数据（修复回填属用户决策）；
只输出统计对照，不产生买卖点；不合成数据。

输出：docs/experiments/raw/gap_fill/jump_audit_results.json
复现：PYTHONHASHSEED=0 python3 scripts/run_data_quality_jump_audit.py
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
OUT = RAW / "jump_audit_results.json"

# ── 预注册跳变清单（9 标的 13 跳变）──
JUMPS: dict[str, list[str]] = {
    "159928": ["2021-06-25"],
    "510500": ["2015-04-15", "2022-08-29"],
    "512010": ["2021-06-28"],
    "512100": ["2022-09-05"],
    "512200": ["2024-08-12"],
    "512480": ["2021-03-29", "2026-07-03"],
    "512690": ["2021-05-17", "2021-12-31"],
    "512800": ["2025-07-07"],
    "515880": ["2026-02-03", "2026-07-06"],
}

NAMES = {
    "159928": "消费ETF", "510500": "中证500ETF", "512010": "医药ETF",
    "512100": "中证1000ETF", "512200": "房地产ETF", "512480": "半导体ETF",
    "512690": "酒ETF", "512800": "银行ETF", "515880": "通信ETF",
}


def load_bars(symbol: str) -> pd.DataFrame:
    df = pd.read_parquet(TIMING_CACHE_DIR / f"{symbol}.parquet")
    df = df[~df.index.duplicated(keep="last")].sort_index()
    for col in ("high", "low"):
        if col not in df.columns:
            df[col] = (df[["open", "close"]].max(axis=1) if col == "high"
                       else df[["open", "close"]].min(axis=1))
    return df[["open", "high", "low", "close"]]


def flatten_jumps(bars: pd.DataFrame, dates: list[str]) -> tuple[pd.DataFrame, list[dict]]:
    """预注册修平：跳变日起价格同除跳变比（多跳变按时间序）。"""
    df = bars.copy()
    log = []
    for d in sorted(dates):
        ts = pd.Timestamp(d)
        i = df.index.get_loc(ts)
        prev_close = df["close"].iloc[i - 1]
        ratio = float(df["close"].iloc[i] / prev_close)
        mask = df.index >= ts
        for c in ("open", "high", "low", "close"):
            df.loc[mask, c] = df.loc[mask, c] / ratio
        log.append({"date": d, "ratio": round(ratio, 4),
                    "single_day_return": round(ratio - 1.0, 4)})
    return df, log


def run_ladder(aligned: pd.DataFrame, gate: bool, start=None, end=None) -> dict:
    window = aligned.loc[start:end] if (start or end) else aligned
    ladder = LadderParams(
        indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
        min_weight=0.0, gamma=1.0, low_edge=30.0, high_edge=70.0,
    )
    gate_p = TrendGate(mode="ma200" if gate else "off", cap=0.0)
    warmup = aligned.loc[: window.index[0]].iloc[:-1]
    target = build_target(aligned, ladder, None, gate_p, warmup, vol_target=0.0)
    result = simulate(window, target.loc[window.index], fee_bps=10.0, min_trade=0.05)
    return summarize_run(result.daily, result.trades)


def three_windows(aligned: pd.DataFrame, gate: bool) -> dict:
    mid = aligned.index[len(aligned) // 2]
    full = run_ladder(aligned, gate)
    h1 = run_ladder(aligned, gate, end=mid)
    h2 = run_ladder(aligned, gate, start=mid)
    return {
        "full_excess": round(full["excess_cagr"], 4),
        "h1_excess": round(h1["excess_cagr"], 4),
        "h2_excess": round(h2["excess_cagr"], 4),
        "all_positive": bool(full["excess_cagr"] > 0 and h1["excess_cagr"] > 0
                             and h2["excess_cagr"] > 0),
        "full_strat_mdd": round(full["strategy_mdd"], 4),
        "full_bench_mdd": round(full["benchmark_mdd"], 4),
        "full_bench_cagr": round(full["benchmark_cagr"], 4),
        "window": [str(aligned.index[0].date()), str(aligned.index[-1].date())],
    }


def main() -> None:
    breadth = load_breadth("cn_all")
    results: dict = {"criteria": {
        "jumps": JUMPS, "method": "跳变日起价格同除跳变比(收益置0)，多跳变按时间序",
        "framework": "full_audit 第十四轮 BASE(30/70无闸+闸, fee10bp, cn_all, 三窗中点切分)",
        "flip_rule": "无闸版三窗全正布尔在修平前后改变=结论翻转；状态不变且|Δ全窗超额|≥2pp=数值修正",
    }, "subjects": {}}

    for sym, jump_dates in JUMPS.items():
        bars = load_bars(sym)
        fixed_bars, jlog = flatten_jumps(bars, jump_dates)
        # 修平后单日最大收益复核（应 ≤ 涨跌停量级）
        rmax = float(fixed_bars["close"].pct_change(fill_method=None).abs().max())
        al_raw = align_index_breadth(bars, breadth)
        al_fix = align_index_breadth(fixed_bars, breadth)

        entry = {"name": NAMES[sym], "jumps": jlog,
                 "post_fix_max_abs_daily": round(rmax, 4),
                 "window": [str(al_raw.index[0].date()), str(al_raw.index[-1].date())]}
        for gate in (False, True):
            tag = "gate" if gate else "nogate"
            raw = three_windows(al_raw, gate)
            fix = three_windows(al_fix, gate)
            delta = round(fix["full_excess"] - raw["full_excess"], 4)
            entry[tag] = {"raw": raw, "fixed": fix, "delta_full_excess": delta,
                          "flipped": bool(raw["all_positive"] != fix["all_positive"])}
        results["subjects"][sym] = entry
        ng = entry["nogate"]
        print(f"[{NAMES[sym]:8s}] 无闸 三窗全正: {ng['raw']['all_positive']} → "
              f"{ng['fixed']['all_positive']}"
              f"（全窗 {ng['raw']['full_excess']:+.1%} → {ng['fixed']['full_excess']:+.1%}，"
              f"Δ{ng['delta_full_excess']:+.1%}；前 {ng['raw']['h1_excess']:+.1%}→{ng['fixed']['h1_excess']:+.1%}"
              f" / 后 {ng['raw']['h2_excess']:+.1%}→{ng['fixed']['h2_excess']:+.1%}）"
              f"  持有年化 {ng['raw']['full_bench_cagr']:+.1%}→{ng['fixed']['full_bench_cagr']:+.1%}")

    # ── 科创100 档位线复核：512100 修平后特征 ──
    from run_gap_fill_cyb100 import REF_GROUP_A, REF_GROUP_B, feat_vector, znorm
    def load_local(sym):
        return load_bars(sym)
    fixed_512100, _ = flatten_jumps(load_bars("512100"), JUMPS["512100"])
    win_start = pd.Timestamp("2020-01-02")
    win_end = pd.Timestamp("2026-08-27")
    f_fix = feat_vector(fixed_512100["close"].loc[win_start:win_end])
    feats_a, feats_b = {}, {}
    for s in REF_GROUP_A:
        if s == "512100":
            feats_a[s] = f_fix  # 修平版特征替换（首版漏替换，2026-09-02 修正）
        else:
            feats_a[s] = feat_vector(load_local(s)["close"].loc[win_start:win_end])
    for s in REF_GROUP_B:
        feats_b[s] = feat_vector(load_local(s)["close"].loc[win_start:win_end])
    # 512100 自身不在参照组（阶段二组A含512100）——阶段二原组A=创业板/科创50/中证1000
    # 修平后重算：组A其余不变，512100 特征替换为修平版
    all_f = list(feats_a.values()) + list(feats_b.values())
    mu = {"vol": float(np.mean([f[0] for f in all_f])), "mdd": float(np.mean([f[1] for f in all_f]))}
    sd = {"vol": float(np.std([f[0] for f in all_f], ddof=1)), "mdd": float(np.std([f[1] for f in all_f], ddof=1))}
    med_a = np.median(np.array([znorm(f, mu, sd) for f in feats_a.values()]), axis=0)
    med_b = np.median(np.array([znorm(f, mu, sd) for f in feats_b.values()]), axis=0)
    # 科创100 特征重算（不变：000698 数据无污染）
    cyb_bars = pd.read_parquet(RAW / "sh000698_index.parquet")
    f_cyb = feat_vector(cyb_bars["close"].loc[win_start:win_end])
    z_cyb = np.array(znorm(f_cyb, mu, sd))
    d_a, d_b = float(np.linalg.norm(z_cyb - med_a)), float(np.linalg.norm(z_cyb - med_b))
    results["cyb100_band_recheck"] = {
        "note": "512100修平后特征代回阶段二距离规则（组A中位数含修平版512100）",
        "fixed_512100_feats": {"ann_vol": round(f_fix[0], 4), "abs_mdd": round(f_fix[1], 4)},
        "dist_A": round(d_a, 3), "dist_B": round(d_b, 3),
        "main_band_would_flip": bool(abs(d_a - d_b) >= 0.25 and d_b < d_a) if d_b < d_a else bool(d_a < d_b),
        "conclusion": ("距离A/B排序不变或仍无显著归属 → 阶段二主档位线40/60维持"
                       if not ((d_a - d_b) > 0.25 or (d_b - d_a) > 0.25)
                       else ("修平后主档位线翻转为30/70 → 阶段二alt线(30/70)三窗："
                             "全+8.9%/前+25.6%/后-6.9%，后半仍负，判负结论不变"
                             if d_a < d_b else "修平后主档位线仍40/60")),
    }
    print(f"\n[科创100档位线复核] 修平后 dist_A={d_a:.3f} dist_B={d_b:.3f} → "
          f"{results['cyb100_band_recheck']['conclusion']}")

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    h = hashlib.sha256(json.dumps(results, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    print(f"\n输出: {OUT}")
    print(f"HASH(规范化JSON): {h}")


if __name__ == "__main__":
    main()
