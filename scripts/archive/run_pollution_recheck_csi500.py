#!/usr/bin/env python3
"""债务三复核：中证500ETF(510500) 宽度三档判负重审（修平数据 × 完整验证协议）
· 预注册（跑前写死，跑后不改）。

【被复核结论】（timing-sweep 执行手册第七/九轮 + 明确排除清单）
  510500 中证500ETF，30/70 三档逆势（无闸），窗口 2013-03→2026-08：
  策略年化 +8.7% vs 持有 +18.1%，超额 -9.8% → 「基准过强不适配」❌ 明确排除。
  跳变审计（data-quality-jump-audit §0/§5）发现该判负建立在被污染数据上：
  510500 在 timing 缓存有两处复权断裂（2015-04-15 +248.6%、2022-08-29 -12.7%），
  修平后全窗超额 -10.3%→+0.5%、前半 -23.7%→-0.8%，持有年化 +17.8%→+8.1%
  （"基准过强"部分是假象）——审计建议"重审，不直接下入选结论"。

【原始判负口径（事后重建，如实注明）】
  当年归档无明示数值判定线；从报告数字反推：全窗超额 -9.8% 且前半 -23.7%
  即判"明显不适配"。本重审把"明显不适配"的量级预注册为：无闸全窗 ≤0，
  或任一半窗 ≤ -5pp（第 9 轮判负的量级下界）。

【修平方法（复用，不重新发明）】
  跳变审计 §3 预注册修平法原样复用：跳变日 D 的 ratio=close[D]/close[D-1]，
  D 及之后全部 OHLC 同除 ratio，多跳变按时间序。这是"消除单点断裂"的
  下界修法，不是重建正确复权（审计 §7 欠账声明适用）。

【验证协议（对齐当年冠军三档的验证方法）】
  框架 = full_audit 第十四轮 BASE：ladder/b200/3bands/fixed/30-70/contrarian/
  gamma1/min_weight0/min_trade0.05/fee_bps10/cn_all × {无闸, +MA200闸(cap0)}；
  三窗 = 行数中点切分（全/前半/后半）；target 全历史热启动（无未来函数，
  与 compute_run 同语义）。
  完整协议三件套 = 三窗一致 + 参数邻域 + 5年滚动（robustness_20260827 同法）：
  - 参数邻域（单维扰动，预注册清单共 9 个）：
    low_edge∈{25,35}、high_edge∈{65,75}、gamma∈{0.85,1.15}、n_bands∈{1,5}、
    min_weight∈{0.10}（0.0−0.10 非法剔除）。不可算者剔除并披露，占比按可算数计。
  - 5年滚动：对齐帧每 252 个交易日起一窗，窗长 5×365.25 天，窗末超出数据
    末尾即停；每窗记超额年化。

【预注册判定标准（三选一，主口径=无闸版；跑完不得回头调整）】
  「翻案为值得进一步验证」须同时满足：
    (a) 无闸三窗（全/前半/后半）超额全 > 0；
    (b) 5年滚动窗正超额占比 ≥ 60%；
    (c) 参数邻域正超额占比 ≥ 2/3 且邻域中位 > 0。
    门槛依据（跑前论证）：在册入选配置的实证下界 = 沪深300攻守（滚动 67%、
    邻域 73%），创业板主仓（滚动 83%、邻域 100%）；60% 与 2/3 显著低于在册
    最弱入选配置、又明显高于"打平"（滚动 ~50%、邻域无偏）。审计明示
    "打平不等于值得入选"，故翻案门槛必须整体高于打平。
  「维持判负」：无闸全窗超额 ≤ 0，或任一半窗 ≤ -5pp。
  「证据不足」：其余中间情形；或实现校验未过（见下）。
  最高只判「值得进一步验证」，不下入选结论（审计原文要求）。

【实现校验（预注册，非判定）】
  本脚本对同一框架的复算须复现审计归档数字（jump_audit_results.json，
  容差 ±0.001）：未修平无闸 全窗/前半/后半 = -0.1033/-0.2367/+0.0181；
  修平无闸 = +0.0049/-0.0084/+0.0185。不匹配 → 判定中止，只报「证据不足
  （实现偏差）」并披露差异。

【红线遵守】不修改 ~/.lei_signal_lab 任何缓存数据与 src/ 生产代码；
不产生买卖点；输出只新增到 docs/experiments/raw/pollution_recheck/。

输出：docs/experiments/raw/pollution_recheck/csi500_510500_recheck.json
复现：PYTHONHASHSEED=0 / =42 各跑一次，规范化 JSON 的 sha256 须一致。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
sys.path.insert(0, str(REPO / "src"))

from lei_signal.timing_backtest.data import (  # noqa: E402
    TIMING_CACHE_DIR, align_index_breadth, load_breadth,
)
from lei_signal.timing_backtest.engine import simulate  # noqa: E402
from lei_signal.timing_backtest.metrics import summarize_run  # noqa: E402
from lei_signal.timing_backtest.strategies import (  # noqa: E402
    LadderParams, TrendGate, build_target,
)

RAW = REPO / "docs/experiments/raw/pollution_recheck"
OUT = RAW / "csi500_510500_recheck.json"
SYMBOL = "510500"
JUMP_DATES = ["2015-04-15", "2022-08-29"]  # 审计 §2 预注册清单
BASE = dict(n_bands=3, edge_mode="fixed", direction="contrarian",
            min_weight=0.0, gamma=1.0, low_edge=30.0, high_edge=70.0)
AUDIT_CHECK = {  # jump_audit_results.json 归档数字（实现校验用）
    "raw_nogate": {"full": -0.1033, "h1": -0.2367, "h2": 0.0181},
    "fixed_nogate": {"full": 0.0049, "h1": -0.0084, "h2": 0.0185},
}
NEIGHBORHOOD = {  # 预注册 9 变体（无闸、全窗）
    "low25": {"low_edge": 25.0}, "low35": {"low_edge": 35.0},
    "high65": {"high_edge": 65.0}, "high75": {"high_edge": 75.0},
    "gamma0.85": {"gamma": 0.85}, "gamma1.15": {"gamma": 1.15},
    "nbands1": {"n_bands": 1}, "nbands5": {"n_bands": 5},
    "minw0.1": {"min_weight": 0.10},
}
ROLL_YEARS = 5
ROLL_STEP = 252


def load_bars() -> pd.DataFrame:
    df = pd.read_parquet(TIMING_CACHE_DIR / f"{SYMBOL}.parquet")
    df = df[~df.index.duplicated(keep="last")].sort_index()
    for col in ("high", "low"):
        if col not in df.columns:
            df[col] = (df[["open", "close"]].max(axis=1) if col == "high"
                       else df[["open", "close"]].min(axis=1))
    return df[["open", "high", "low", "close"]]


def flatten_jumps(bars: pd.DataFrame, dates: list[str]):
    """审计 §3 预注册修平法原样复用（跳变日起 OHLC 同除跳变比，按时间序）。"""
    df = bars.copy()
    log = []
    for d in sorted(dates):
        ts = pd.Timestamp(d)
        i = df.index.get_loc(ts)
        ratio = float(df["close"].iloc[i] / df["close"].iloc[i - 1])
        mask = df.index >= ts
        for c in ("open", "high", "low", "close"):
            df.loc[mask, c] = df.loc[mask, c] / ratio
        log.append({"date": d, "ratio": round(ratio, 4)})
    return df, log


def run_ladder(aligned: pd.DataFrame, ladder_kw: dict, gate: bool,
               start=None, end=None) -> dict:
    window = aligned.loc[start:end] if (start or end) else aligned
    ladder = LadderParams(indicator="b200", **{**BASE, **ladder_kw})
    gate_p = TrendGate(mode="ma200" if gate else "off", cap=0.0)
    warmup = aligned.loc[: window.index[0]].iloc[:-1]
    target = build_target(aligned, ladder, None, gate_p, warmup, vol_target=0.0)
    result = simulate(window, target.loc[window.index], fee_bps=10.0, min_trade=0.05)
    return summarize_run(result.daily, result.trades)


def three_windows(aligned: pd.DataFrame, ladder_kw: dict, gate: bool) -> dict:
    mid = aligned.index[len(aligned) // 2]
    full = run_ladder(aligned, ladder_kw, gate)
    h1 = run_ladder(aligned, ladder_kw, gate, end=mid)
    h2 = run_ladder(aligned, ladder_kw, gate, start=mid)
    return {
        "full_excess": round(full["excess_cagr"], 4),
        "h1_excess": round(h1["excess_cagr"], 4),
        "h2_excess": round(h2["excess_cagr"], 4),
        "all_positive": bool(full["excess_cagr"] > 0 and h1["excess_cagr"] > 0
                             and h2["excess_cagr"] > 0),
        "full_strat_cagr": round(full["strategy_cagr"], 4),
        "full_bench_cagr": round(full["benchmark_cagr"], 4),
        "full_strat_mdd": round(full["strategy_mdd"], 4),
        "full_bench_mdd": round(full["benchmark_mdd"], 4),
        "window": [str(aligned.index[0].date()), str(aligned.index[-1].date())],
    }


def rolling(aligned: pd.DataFrame) -> dict:
    win_len = pd.Timedelta(days=int(ROLL_YEARS * 365.25))
    idx = aligned.index
    rows = []
    for i in range(0, len(idx), ROLL_STEP):
        s = idx[i]
        e = s + win_len
        if e > idx[-1]:
            break
        m = run_ladder(aligned, {}, False, start=s, end=e)
        rows.append({"start": str(s.date()), "end": str(e.date()),
                     "excess": round(m["excess_cagr"], 4)})
    vals = [r["excess"] for r in rows]
    se = pd.Series(vals)
    return {
        "windows": rows,
        "count": len(rows),
        "positive_pct": round(float((se > 0).mean()), 4) if len(se) else None,
        "median": round(float(se.median()), 4) if len(se) else None,
        "worst": round(float(se.min()), 4) if len(se) else None,
        "best": round(float(se.max()), 4) if len(se) else None,
    }


def neighborhood(aligned: pd.DataFrame) -> dict:
    out, failures = {}, []
    for name, kw in NEIGHBORHOOD.items():
        try:
            m = run_ladder(aligned, kw, False)
            out[name] = round(m["excess_cagr"], 4)
        except Exception as e:  # noqa: BLE001 - 不可算变体剔除并披露
            out[name] = None
            failures.append({"variant": name, "error": str(e)[:80]})
    vals = [v for v in out.values() if v is not None]
    se = pd.Series(vals)
    return {
        "per_variant": out,
        "dropped": failures,
        "computable": len(vals),
        "positive_pct": round(float((se > 0).mean()), 4) if len(se) else None,
        "median": round(float(se.median()), 4) if len(se) else None,
        "worst": round(float(se.min()), 4) if len(se) else None,
    }


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    breadth = load_breadth("cn_all")
    bars = load_bars()
    fixed_bars, jlog = flatten_jumps(bars, JUMP_DATES)
    rmax = float(fixed_bars["close"].pct_change(fill_method=None).abs().max())
    al_raw = align_index_breadth(bars, breadth)
    al_fix = align_index_breadth(fixed_bars, breadth)

    # 三窗：raw/fixed × 无闸/闸（raw 仅作实现校验与对照披露）
    raw_ng = three_windows(al_raw, {}, False)
    raw_g = three_windows(al_raw, {}, True)
    fix_ng = three_windows(al_fix, {}, False)
    fix_g = three_windows(al_fix, {}, True)

    impl_ok = (
        abs(raw_ng["full_excess"] - AUDIT_CHECK["raw_nogate"]["full"]) <= 0.001
        and abs(raw_ng["h1_excess"] - AUDIT_CHECK["raw_nogate"]["h1"]) <= 0.001
        and abs(raw_ng["h2_excess"] - AUDIT_CHECK["raw_nogate"]["h2"]) <= 0.001
        and abs(fix_ng["full_excess"] - AUDIT_CHECK["fixed_nogate"]["full"]) <= 0.001
        and abs(fix_ng["h1_excess"] - AUDIT_CHECK["fixed_nogate"]["h1"]) <= 0.001
        and abs(fix_ng["h2_excess"] - AUDIT_CHECK["fixed_nogate"]["h2"]) <= 0.001
    )

    roll = rolling(al_fix)
    nb = neighborhood(al_fix)

    # ---- 预注册判定 ----
    a = fix_ng["all_positive"]
    b = roll["positive_pct"] is not None and roll["positive_pct"] >= 0.60
    c = (nb["positive_pct"] is not None and nb["positive_pct"] >= 2 / 3
         and nb["median"] is not None and nb["median"] > 0)
    stay_neg = (fix_ng["full_excess"] <= 0
                or fix_ng["h1_excess"] <= -0.05
                or fix_ng["h2_excess"] <= -0.05)
    if not impl_ok:
        verdict = "证据不足（实现校验未过，判定中止）"
    elif a and b and c:
        verdict = "翻案为值得进一步验证"
    elif stay_neg:
        verdict = "维持判负"
    else:
        verdict = "证据不足"

    results = {
        "task": "债务三：510500 中证500ETF 判负重审（修平数据×完整验证协议，预注册）",
        "data": {
            "source": str(TIMING_CACHE_DIR / f"{SYMBOL}.parquet"),
            "window": [str(al_fix.index[0].date()), str(al_fix.index[-1].date())],
            "jumps_flattened": jlog,
            "post_fix_max_abs_daily": round(rmax, 4),
        },
        "framework": ("full_audit 第十四轮 BASE: ladder/b200/3bands/fixed/30-70/"
                      "contrarian/gamma1/minw0/fee10bp/cn_all/min_trade0.05 × "
                      "{无闸,+MA200闸cap0}; 三窗=行数中点切分"),
        "three_windows": {
            "raw_nogate": raw_ng, "raw_gate": raw_g,
            "fixed_nogate": fix_ng, "fixed_gate": fix_g,
        },
        "rolling_5y": roll,
        "neighborhood": nb,
        "criteria_check": {"a_three_windows_all_positive": a,
                           "b_rolling_pos_ge_60pct": b,
                           "c_neighborhood_pos_ge_2thirds_median_gt0": c,
                           "stay_negative_trigger": stay_neg},
        "implementation_check_vs_audit": impl_ok,
        "verdict_pre_registered": verdict,
    }
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    h = hashlib.sha256(json.dumps(results, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    print(f"[实现校验 vs 审计归档] {'通过' if impl_ok else '未通过'}")
    print(f"[未修平·无闸] 全窗 {raw_ng['full_excess']:+.1%} / 前半 {raw_ng['h1_excess']:+.1%}"
          f" / 后半 {raw_ng['h2_excess']:+.1%}（持有年化 {raw_ng['full_bench_cagr']:+.1%}）")
    print(f"[修平·无闸]   全窗 {fix_ng['full_excess']:+.1%} / 前半 {fix_ng['h1_excess']:+.1%}"
          f" / 后半 {fix_ng['h2_excess']:+.1%}（持有年化 {fix_ng['full_bench_cagr']:+.1%}）")
    print(f"[修平·+闸]    全窗 {fix_g['full_excess']:+.1%} / 前半 {fix_g['h1_excess']:+.1%}"
          f" / 后半 {fix_g['h2_excess']:+.1%}")
    print(f"[5年滚动] {roll['count']} 窗：正占比 {roll['positive_pct']:.0%}，"
          f"中位 {roll['median']:+.1%}，最差 {roll['worst']:+.1%}，最好 {roll['best']:+.1%}")
    print(f"[参数邻域] 可算 {nb['computable']}/{len(NEIGHBORHOOD)}：正占比 "
          f"{nb['positive_pct']:.0%}，中位 {nb['median']:+.1%}，最差 {nb['worst']:+.1%}"
          + (f"（剔除: {[d['variant'] for d in nb['dropped']]}）" if nb['dropped'] else ""))
    print(f"判定（预注册）: {verdict}")
    print(f"输出: {OUT}")
    print(f"HASH(规范化JSON): {h}")


if __name__ == "__main__":
    main()
