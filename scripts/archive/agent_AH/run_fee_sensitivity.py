#!/usr/bin/env python3
"""任务AH：中证500ETF(510500) 修平数据上 30/70 三档规则的费用敏感性收口
· 预注册（跑前写死，跑后不改）。

【背景】（pollution-recheck-moduleB-csi500-2026-09-03.md 债务三，直接采用不重验）
  修平·无闸三窗超额在 fee=10bp 口径为 +0.5%/-0.8%/+1.8%（未全正），在 1bp
  口径为 +1.5%/+0.2%/+2.8%（恰好全正）——正负号被费用假设左右。本任务把
  "费率敏感性"从两个点变成一条曲线，收口判定。

【复用】直接 import Y 的管线（scripts/run_pollution_recheck_csi500.py）：
  修平法（跳变日 2015-04-15/2022-08-29 起 OHLC 同除跳变比）、宽度对齐、
  full_audit 第十四轮 BASE（ladder/b200/3bands/fixed/30-70/contrarian/gamma1/
  minw0/min_trade0.05/cn_all、无闸、行数中点三窗、target 全历史热启动）。
  唯一改动：fee_bps 从写死 10.0 参数化为变量。不调参、不换规则。

【费率口径】fee_bps = 单边费率（bp），按引擎定义 = |调仓市值|×fee_bps×1e-4，
  策略每次调仓计费、基准只计一次买入费。网格 {0, 0.5, 1, 2, 5, 10, 15} bp。

【现实费率带论证（跑前写死）】510500 为 A 股 ETF 场内交易：
  - 佣金：主流券商 ETF 场内佣金约万 0.5-2.5（0.5-2.5bp）免五后；
  - 点差+冲击：510500 日均成交额数亿至数十亿元，点差通常 1 tick≈0.1-0.2%?
    否——510500 价格 ~6-7 元，1 tick=0.001 元 ≈ 0.15bp，典型半点差 ~1bp，
    小资金冲击可忽略、保守计 1-3bp；
  - 故单边现实区间 ≈ 1-10bp：1bp ≈ 最低佣金+零点差（最乐观可实现），
    10bp ≈ 高佣金+保守冲击（保守上限）。5bp 取为"现实上限的代表值"（带内
    偏保守一侧的中点）。0bp 仅理论参考（下界），15bp 超出现实带（披露用）。

【盈亏平衡费率方法（跑前写死）】对全窗/前半/后半分别求数值根：
  excess_cagr(fee)=0。excess 对 fee 单调递减（策略换手远高于基准一次性买入，
  fee 越高策略相对越吃亏——单调性用网格数值验证：网格上 excess 随 fee 严格
  不增即认为成立，否则披露）。求根用二分法于 [0, 60] bp，容差 0.01bp，
  区间端点同号则记 None 并披露。非线性来源（费用复利乘法效应）由数值法
  自然涵盖，不做线性近似假设。

【预注册判定标准（三选一，主口径=修平·无闸·三窗；跑完不得回头调整）】
  「值得进一步验证」：fee=5bp（现实上限代表值）时三窗（全/前半/后半）超额
    全 > 0，且全窗超额 ≥ +1.0pp（0.01）。
    门槛依据：Y 报告明示"打平不等于值得入选，翻案门槛要明显高于打平"——
    0.5pp 量级（10bp 口径的全窗值）只算打平噪声带，+1.0pp 为最小有意义的
    翻案幅度下限（仍远低于在册配置的优势量级）。
  「维持判负」：全窗盈亏平衡费率 < 1bp（即任何现实可实现费率下全窗超额
    都为负）；或 1bp 口径下（最乐观现实费率）全窗超额 ≤ 0 且任一半窗 ≤ -2pp
    （保留第 9 轮判负量级下界的痕迹但不苛求 -5pp，因旧判负幅度依据已失效）。
  「证据不足（费率敏感带内）」：其余中间情形；或实现校验未过。
  最高只判「值得进一步验证」，不下入选结论（审计与 Y 报告原文要求）。

【实现校验（预注册，非判定）】fee=10bp 的修平·无闸三窗须复现 Y 归档
  （csi500_510500_recheck.json：+0.0049/-0.0084/+0.0185，容差 ±0.001），
  不匹配 → 判定中止，只报「证据不足（实现偏差）」并披露差异。

【附加稳健性（不影响主判定，如实呈现）】
  R1 换手：全窗年化单边换手（Σ|Δw|/年数）、年换手中位、费率敏感斜率
     （每 1bp 费率拖累多少超额，由 fee=0 与 fee=10 两点差分近似，披露口径）；
  R2 拖后腿窗与单年主导：全窗在 1bp 与 10bp 两口径下的逐年超额表，
     标出前半窗内贡献最负/最正的年份。

【红线遵守】不修改 ~/.lei_signal_lab 任何缓存数据与 src/ 生产代码与既有
  归档；不产生买卖点；输出只新增。判定标准跑前写死于本 docstring。

输出：docs/experiments/raw/fee_sensitivity_csi500/fee_grid.json
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
sys.path.insert(0, str(REPO / "scripts"))

from run_pollution_recheck_csi500 import (  # noqa: E402
    BASE, JUMP_DATES, SYMBOL, align_index_breadth, flatten_jumps,
    load_bars, load_breadth,
)
from lei_signal.timing_backtest.engine import simulate  # noqa: E402
from lei_signal.timing_backtest.metrics import (  # noqa: E402
    compute_performance, summarize_run, yearly_returns,
)
from lei_signal.timing_backtest.strategies import (  # noqa: E402
    LadderParams, TrendGate, build_target,
)

RAW = REPO / "docs/experiments/raw/fee_sensitivity_csi500"
OUT = RAW / "fee_grid.json"
FEE_GRID = [0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 15.0]
IMPL_CHECK = {"full": 0.0049, "h1": -0.0084, "h2": 0.0185}  # Y 归档（fee=10bp）


def run(aligned: pd.DataFrame, fee: float, start=None, end=None):
    window = aligned.loc[start:end] if (start or end) else aligned
    ladder = LadderParams(indicator="b200", **BASE)
    gate = TrendGate(mode="off", cap=0.0)
    warmup = aligned.loc[: window.index[0]].iloc[:-1]
    target = build_target(aligned, ladder, None, gate, warmup, vol_target=0.0)
    result = simulate(window, target.loc[window.index], fee_bps=fee, min_trade=0.05)
    summary = summarize_run(result.daily, result.trades)
    return result, summary


def three_windows(aligned: pd.DataFrame, fee: float) -> dict:
    mid = aligned.index[len(aligned) // 2]
    full, sfull = run(aligned, fee)
    _, sh1 = run(aligned, fee, end=mid)
    _, sh2 = run(aligned, fee, start=mid)
    return {
        "full": sfull["excess_cagr"], "h1": sh1["excess_cagr"],
        "h2": sh2["excess_cagr"],
        "full_strat_cagr": sfull["strategy_cagr"],
        "full_bench_cagr": sfull["benchmark_cagr"],
        "n_trades": sfull["n_trades"],
        "total_turnover": sfull["total_turnover"],
        "years": sfull["years"],
        "_daily": full.daily,
    }


def breakeven(aligned: pd.DataFrame, which: str, lo=0.0, hi=60.0,
              tol=0.01, max_iter=60) -> float | None:
    def f(fee):
        mid = aligned.index[len(aligned) // 2]
        if which == "full":
            _, s = run(aligned, fee)
        elif which == "h1":
            _, s = run(aligned, fee, end=mid)
        else:
            _, s = run(aligned, fee, start=mid)
        return s["excess_cagr"]

    flo, fhi = f(lo), f(hi)
    if flo == 0:
        return lo
    if flo * fhi > 0:
        return None
    for _ in range(max_iter):
        m = (lo + hi) / 2
        fm = f(m)
        if abs(hi - lo) < tol or fm == 0:
            return round(m, 2)
        if flo * fm < 0:
            hi = m
        else:
            lo, flo = m, fm
    return round((lo + hi) / 2, 2)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    breadth = load_breadth("cn_all")
    bars = load_bars()
    fixed_bars, jlog = flatten_jumps(bars, JUMP_DATES)
    al_fix = align_index_breadth(fixed_bars, breadth)

    grid = {}
    daily_cache = {}
    for fee in FEE_GRID:
        r = three_windows(al_fix, fee)
        daily_cache[fee] = r.pop("_daily")
        grid[str(fee)] = {k: (round(v, 6) if isinstance(v, float) else v)
                          for k, v in r.items()}
        print(f"fee={fee:>5}bp: 全窗 {r['full']:+.2%} / 前半 {r['h1']:+.2%}"
              f" / 后半 {r['h2']:+.2%}")

    # 单调性验证（网格上 excess 随 fee 严格不增）
    monotone = all(
        grid[str(FEE_GRID[i])]["full"] >= grid[str(FEE_GRID[i + 1])]["full"] - 1e-9
        and grid[str(FEE_GRID[i])]["h1"] >= grid[str(FEE_GRID[i + 1])]["h1"] - 1e-9
        for i in range(len(FEE_GRID) - 1)
    )

    impl_ok = all(
        abs(grid["10.0"][k] - IMPL_CHECK[k]) <= 0.001 for k in IMPL_CHECK
    )

    be = {w: breakeven(al_fix, w) for w in ("full", "h1", "h2")}
    print(f"盈亏平衡费率(bp): 全窗 {be['full']} / 前半 {be['h1']} / 后半 {be['h2']}")

    # ---- 附加稳健性 ----
    g0, g10 = grid["0.0"], grid["10.0"]
    slope_full_per_bp = (g0["full"] - g10["full"]) / 10.0
    slope_h1_per_bp = (g0["h1"] - g10["h1"]) / 10.0
    years = g0["years"]
    ann_turnover = g0["total_turnover"] / years

    yearly = {}
    for fee in (1.0, 10.0):
        d = daily_cache[fee]
        ys = yearly_returns(d["equity"])
        yb = yearly_returns(d["benchmark"])
        ye = (ys - yb).dropna()
        yearly[str(fee)] = {str(int(k)): round(float(v), 4) for k, v in ye.items()}

    y1 = pd.Series(yearly["1.0"], dtype=float)
    mid_ts = al_fix.index[len(al_fix) // 2]
    h1_years = [y for y in y1.index if int(y) < mid_ts.year]
    h1_worst = min(h1_years, key=lambda y: y1[y]) if h1_years else None

    # ---- 预注册判定 ----
    f5 = grid["5.0"]
    f1 = grid["1.0"]
    promote = f5["full"] > 0 and f5["h1"] > 0 and f5["h2"] > 0 and f5["full"] >= 0.01
    stay_neg = (
        (be["full"] is not None and be["full"] < 1.0)
        or (f1["full"] <= 0 and (f1["h1"] <= -0.02 or f1["h2"] <= -0.02))
    )
    if not impl_ok:
        verdict = "证据不足（实现校验未过，判定中止）"
    elif promote:
        verdict = "值得进一步验证（仅费率维度收口，非入选结论）"
    elif stay_neg:
        verdict = "维持判负"
    else:
        verdict = "证据不足（费率敏感带内）"
    print(f"判定（预注册）: {verdict}")

    results = {
        "task": "任务AH：510500 修平数据 30/70 三档费用敏感性（预注册）",
        "framework": "复用 run_pollution_recheck_csi500.py 管线，仅参数化 fee_bps；"
                     "修平·无闸·三窗（行数中点切分）",
        "fee_grid_bps": FEE_GRID,
        "grid": grid,
        "monotone_check": monotone,
        "breakeven_fee_bps": be,
        "breakeven_method": "二分法 [0,60]bp，tol 0.01bp，excess_cagr(fee)=0 数值根",
        "realistic_band_bps": [1.0, 10.0],
        "turnover": {
            "n_trades_full": g0["n_trades"],
            "total_one_way_turnover": round(g0["total_turnover"], 2),
            "years": round(years, 2),
            "annualized_turnover": round(ann_turnover, 2),
            "fee_drag_full_per_bp": round(slope_full_per_bp, 5),
            "fee_drag_h1_per_bp": round(slope_h1_per_bp, 5),
            "note": "斜率=fee0 与 fee10 两点差分/10；费率敏感度=年化换手×~1bp",
        },
        "yearly_excess": yearly,
        "h1_laggard_year_at_1bp": h1_worst,
        "impl_check_vs_Y": impl_ok,
        "verdict_pre_registered": verdict,
        "jumps_flattened": jlog,
        "window": [str(al_fix.index[0].date()), str(al_fix.index[-1].date())],
    }
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    h = hashlib.sha256(
        json.dumps(results, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    print(f"输出: {OUT}")
    print(f"HASH(规范化JSON): {h}")


if __name__ == "__main__":
    main()
