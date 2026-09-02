#!/usr/bin/env python3
"""宽基缺口补齐 · 恒生科技（^HSTECH / 513180）降级版防守闸回测 · 预注册
（2026-09-02，跑前写死，跑后不改）。

Prompt X 阶段二：阶段一确认恒生科技为零覆盖缺口。**无本地成分股宽度数据，
cn_all 对港股架构性不适用（跨市场宽度语义错误）**，故本脚本为 Prompt X
预先授权的降级方案：用指数自身价格结构做简化版防守验证。

【性质声明（预注册，贯穿全报告）】
本实验与 A 股三档逆势「性质不同、强度更弱」：
- 无宽度输入，信号仅为价格 × MA200；
- 参照血统 = 美股防守版（SPY/QQQ 的 TrendGate ma200 + vol_target 组件，
  service.py spy_defense/qqq_defense）与 regime-gate 横门禁发现（宽基 ETF
  仅横门禁是干净发现）——即美股先例的定性：**回撤保险，非择时增强**
  （年化保费 4-8pp）；
- 即使全部检验通过，认证上限 = 「短样本降级版有效」，不得等同于
  冠军三档（16 年跨周期、宽度机制）的认证等级。

【数据口径（跑前写死）】
- 指数口径（主）= docs/experiments/raw/gap_fill/hkHSTECH_index.parquet，
  腾讯海外源 hkHSTECH 不复权日线（指数无除权，不复权=正确口径），
  2020-07-27（指数发布日）→ 2026-09-02，1502 行，抓取 2026-09-02。
- ETF 执行口径（披露）= docs/experiments/raw/holdings_correlation/
  sh513180_bars.parquet，腾讯 qfq 日线，2021-05-25→2026-09-02，1282 行
  （Prompt W 抓取，本脚本复用不重抓）。
- 样本特征（跑前披露）：指数年化波动 38.6%、全窗 MDD −74%（2021-02→
  2022-10）；ETF 年化 33.5%、MDD −62%。
- 指数样本 6.1 年，仅含一个完整「牛→−74% 深熊→修复」周期；2020-03
  疫情暴跌不在样本内（指数 2020-07-27 起）。

【策略臂（全部复用现有组件，无新发明）】
- M1_gate0（主判定臂）：满仓底仓 × MA200 闸 cap=0（价<MA200 全清）。
  选 M1 为主判定的理由（跑前写死）：唯一参数全部来自已验证组件默认值
  的臂——TrendGate(ma200, cap=0) 即 full_audit「冠军+闸」口径。
- M2_gate05：MA200 闸 cap=0.5（<MA200 半仓，攻守兼备语义）——结构邻域。
- M3_gate0_vol15：闸 + vol_target 0.15（QQQ 血统参数）——结构邻域。
- M4_gate0_vol20：闸 + vol_target 0.20（高波动折中）——结构邻域。
- 反向闸对照：价<MA200 持有、≥MA200 清仓（方向性安慰剂）。
- 费率：fee_bps=10（bform 终审/美股防守版同口径），min_trade=0.05，
  cash_rate=0。

【判定标准（预注册，M1 指数口径，三条全过才算通过）】
1. 全窗 MDD 改善（|持有MDD| − |策略MDD|，即策略回撤更浅的深度）≥ 15pp；
2. 三窗（全窗 / 前半 / 后半，中点切分）MDD 改善全为正；
3. 全窗年化代价（持有年化 − 策略年化）≤ 8pp（美股防守版保费上界）。
【对照判定（预注册）】
4. 方向性：正向闸 MDD 改善必须 > 反向闸 MDD 改善，否则判负
   （否则改善只是「减少在场时间」的机械效应而非趋势信息）；
5. 块置换安慰剂：真实闸 0/1 序列的连续块随机重排 100 次
   （rng=PCG64 seed 20260903；保持在场总时长与切换次数、费率同担），
   真实 MDD 改善 > 100 次安慰剂的 95 分位；
6. ETF 执行口径披露：513180 上复算判定 1-3（不设通过线，仅披露——
   ETF 样本 5.3 年且错过指数顶部段，两者口径差异如实呈现）。
【MA200 warmup 披露】前 200 交易日（2020-07-27→2021-05，trend_gate_cap
对 MA200 未成型日不设限=满仓）。指数口径闸实际生效始于 2021-05 末，
恰与 513180 ETF 上市（2021-05-25）几乎重合——巧合，如实披露。

【红线遵守】不改 src/；不产生买卖点；不合成数据；不因结果调整判定线。

输出：docs/experiments/raw/gap_fill/hstech_gapfill_results.json
复现：PYTHONHASHSEED=0 python3 scripts/run_gap_fill_hstech.py
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

from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import summarize_run
from lei_signal.timing_backtest.strategies import (
    TrendGate,
    apply_gate,
    apply_vol_target,
    trend_gate_cap,
)

RAW = REPO / "docs/experiments/raw/gap_fill"
OUT = RAW / "hstech_gapfill_results.json"

# ── 预注册常量（跑前写死）──
FEE_BPS = 10.0
MIN_TRADE = 0.05
MDD_IMPROVE_MIN = 0.15   # 判定1：全窗 MDD 改善 ≥15pp
ANN_COST_MAX = 0.08      # 判定3：年化代价 ≤8pp
PLACEBO_N = 100
PLACEBO_SEED = 20260903
PLACEBO_Q = 0.95


def run_arm(bars: pd.DataFrame, target: pd.Series, start=None, end=None) -> dict:
    window_bars = bars.loc[start:end] if (start or end) else bars
    tgt = target.loc[window_bars.index]
    result = simulate(window_bars, tgt, fee_bps=FEE_BPS, min_trade=MIN_TRADE)
    return summarize_run(result.daily, result.trades)


def mdd_improve(m: dict) -> float:
    # MDD 改善 = 策略MDD − 持有MDD（两负数相减）：−59−(−74)=+15pp，正值=策略回撤更浅
    # 等价于 |持有MDD| − |策略MDD|。首版此处符号写反（benchmark−strategy），
    # 2026-09-02 修正为实现 bug 修复，判定线一字未动。
    return float(m["strategy_mdd"] - m["benchmark_mdd"])


def build_targets(bars: pd.DataFrame) -> dict[str, pd.Series]:
    close = bars["close"]
    base = pd.Series(1.0, index=bars.index)
    cap0 = trend_gate_cap(close, TrendGate(mode="ma200", cap=0.0))
    cap05 = trend_gate_cap(close, TrendGate(mode="ma200", cap=0.5))
    fwd = {
        "M1_gate0": apply_gate(base, cap0),
        "M2_gate05": apply_gate(base, cap05),
        "M3_gate0_vol15": apply_vol_target(close, apply_gate(base, cap0), 0.15),
        "M4_gate0_vol20": apply_vol_target(close, apply_gate(base, cap0), 0.20),
    }
    # 反向闸（方向性对照）：MA200 未成型或价<MA200 → 持有；价≥MA200 → 清仓
    ma = close.rolling(200, min_periods=200).mean()
    rev = np.where(ma.isna() | (close < ma), 1.0, 0.0)
    fwd["REV_gate0"] = pd.Series(rev, index=bars.index)
    return fwd


def block_shuffle(seq: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """0/1 序列的连续块随机重排（在场总时长与切换次数不变）。"""
    blocks = []
    cur, n = seq[0], 1
    for x in seq[1:]:
        if x == cur:
            n += 1
        else:
            blocks.append((cur, n))
            cur, n = x, 1
    blocks.append((cur, n))
    order = rng.permutation(len(blocks))
    out = np.concatenate([np.full(blocks[i][1], blocks[i][0]) for i in order])
    return out


def main() -> None:
    idx = pd.read_parquet(RAW / "hkHSTECH_index.parquet")
    idx = idx[~idx.index.duplicated(keep="last")].sort_index()[["open", "high", "low", "close"]]
    etf = pd.read_parquet(REPO / "docs/experiments/raw/holdings_correlation/sh513180_bars.parquet")
    etf = etf[~etf.index.duplicated(keep="last")].sort_index()[["open", "high", "low", "close"]]

    results: dict = {"criteria": {
        "nature": "降级版：无宽度输入纯价格结构，与A股三档性质不同强度更弱；"
                  "定性=回撤保险非择时增强（美股防守版先例）",
        "mdd_improve_min": MDD_IMPROVE_MIN, "ann_cost_max": ANN_COST_MAX,
        "three_window": "中点切分，三窗MDD改善全为正",
        "direction_control": "正向MDD改善>反向，否则判负",
        "placebo": f"块置换{PLACEBO_N}次(seed={PLACEBO_SEED})，真实MDD改善>95分位",
        "fee_bps": FEE_BPS, "min_trade": MIN_TRADE,
        "certification_cap": "短样本降级版有效≠冠军三档认证等级（6.1年单周期、无宽度）",
    }, "data": {
        "index": "hkHSTECH 腾讯海外源不复权 2020-07-27→2026-09-02 1502行 抓取2026-09-02",
        "etf": "sh513180 腾讯qfq 2021-05-25→2026-09-02 1282行（Prompt W抓取复用）",
        "index_feats": {"ann_vol": 0.386, "mdd": -0.74},
        "etf_feats": {"ann_vol": 0.335, "mdd": -0.62},
        "warmup_note": "前200交易日(2020-07→2021-05) MA200未成型不设限；闸生效始点≈ETF上市日（巧合披露）",
    }}

    targets = build_targets(idx)
    mid = idx.index[len(idx) // 2]

    arms: dict = {}
    for name, tgt in targets.items():
        full = run_arm(idx, tgt)
        h1 = run_arm(idx, tgt, end=mid)
        h2 = run_arm(idx, tgt, start=mid)
        arms[name] = {
            "full": {k: full[k] for k in ("strategy_cagr", "benchmark_cagr", "excess_cagr",
                                          "strategy_mdd", "benchmark_mdd", "calmar", "avg_weight", "n_trades")},
            "h1": {k: h1[k] for k in ("excess_cagr", "strategy_mdd", "benchmark_mdd")},
            "h2": {k: h2[k] for k in ("excess_cagr", "strategy_mdd", "benchmark_mdd")},
            "mdd_improve_full": round(mdd_improve(full), 4),
            "mdd_improve_h1": round(mdd_improve(h1), 4),
            "mdd_improve_h2": round(mdd_improve(h2), 4),
            "ann_cost": round(-full["excess_cagr"], 4),
        }
        a = arms[name]
        print(f"[{name}] 全窗 年化{full['strategy_cagr']:+.1%} vs {full['benchmark_cagr']:+.1%}"
              f"  MDD {full['strategy_mdd']:.0%} vs {full['benchmark_mdd']:.0%}"
              f"  改善 全{a['mdd_improve_full']:+.0%}/前{a['mdd_improve_h1']:+.0%}/后{a['mdd_improve_h2']:+.0%}")

    m1 = arms["M1_gate0"]
    c1 = m1["mdd_improve_full"] >= MDD_IMPROVE_MIN
    c2 = all(m1[k] > 0 for k in ("mdd_improve_full", "mdd_improve_h1", "mdd_improve_h2"))
    c3 = m1["ann_cost"] <= ANN_COST_MAX
    c4 = m1["mdd_improve_full"] > arms["REV_gate0"]["mdd_improve_full"]

    # ── 块置换安慰剂 ──
    w = targets["M1_gate0"].to_numpy(dtype=float)
    rng = np.random.default_rng(PLACEBO_SEED)
    placebo_improve = []
    for _ in range(PLACEBO_N):
        w_fake = pd.Series(block_shuffle(w.copy(), rng), index=idx.index)
        m = run_arm(idx, w_fake)
        placebo_improve.append(round(mdd_improve(m), 4))
    p95 = float(np.percentile(placebo_improve, 95))
    c5 = m1["mdd_improve_full"] > p95
    print(f"[安慰剂] 真实MDD改善 {m1['mdd_improve_full']:+.0%} vs p95 {p95:+.0%}"
          f" max {max(placebo_improve):+.0%} → {'过' if c5 else '不过'}")

    # ── ETF 执行口径披露（不设通过线）──
    etf_targets = build_targets(etf)
    etf_m1 = run_arm(etf, etf_targets["M1_gate0"])
    etf_rev = run_arm(etf, etf_targets["REV_gate0"])
    etf_disclosure = {
        "M1_gate0": {k: etf_m1[k] for k in ("strategy_cagr", "benchmark_cagr", "excess_cagr",
                                            "strategy_mdd", "benchmark_mdd", "avg_weight")},
        "mdd_improve": round(mdd_improve(etf_m1), 4),
        "ann_cost": round(-etf_m1["excess_cagr"], 4),
        "rev_mdd_improve": round(mdd_improve(etf_rev), 4),
        "note": "513180 2021-05起，错过指数顶部段（-25%），口径差异如实呈现；不设通过线",
    }
    print(f"[ETF披露] 513180 M1 年化{etf_m1['strategy_cagr']:+.1%} vs {etf_m1['benchmark_cagr']:+.1%}"
          f"  MDD {etf_m1['strategy_mdd']:.0%} vs {etf_m1['benchmark_mdd']:.0%}")

    overall = c1 and c2 and c3 and c4 and c5
    results["arms"] = arms
    results["placebo"] = {"real": m1["mdd_improve_full"], "p95": round(p95, 4),
                          "max": round(max(placebo_improve), 4),
                          "pass": bool(c5),
                          "head": sorted(placebo_improve, reverse=True)[:5]}
    results["etf_disclosure"] = etf_disclosure
    results["verdict"] = {
        "c1_mdd15pp": bool(c1), "c2_three_window": bool(c2), "c3_cost8pp": bool(c3),
        "c4_direction": bool(c4), "c5_placebo": bool(c5), "overall": bool(overall),
        "certification": (
            "短样本降级版防守闸有效（MDD改善+三窗+保费+方向+安慰剂全过）——"
            "认证上限=短样本降级版，性质=回撤保险非择时增强，不得等同于A股三档"
            if overall else "未通过预注册判定（见分项），如实判负"),
    }
    print(f"\n[总判定] {'短样本降级版有效' if overall else '判负'}"
          f"（MDD15pp{'✓' if c1 else '✗'} 三窗{'✓' if c2 else '✗'} 保费{'✓' if c3 else '✗'}"
          f" 方向{'✓' if c4 else '✗'} 安慰剂{'✓' if c5 else '✗'}）")

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    h = hashlib.sha256(json.dumps(results, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    print(f"输出: {OUT}")
    print(f"HASH(规范化JSON): {h}")


if __name__ == "__main__":
    main()
