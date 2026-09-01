#!/usr/bin/env python3
"""股债性价比门（TRD）·侧向探索（2026-08-31）：宏观门家族首测。

问题：宽度（B200）之外，股债性价比能不能做第二个门？——宏观门
家族（sentiment-gate / regime-gate）历史战绩差，本实验给 TRD 一次
严格的样本外机会。

【预注册协议】（跑前写死）
指标：TRD(t) = 沪深300 过去 252 日收益 − 511010 国债 ETF 过去 252 日
收益（股债滚动收益差；数据全为已落盘价格，无外部依赖）。
信号：TRD 周频（周内最后交易日收盘值）→ 次一交易日生效三档。
机械：与 run_portfolio_split 的 B_全宽度闸 逐位一致（9 标的等权 ×
档位覆盖、5% 带、10bp）。

无前视设计：前半窗（2015-06-16→2020-12-31）内 TRD 的 25/75 分位
定档线 → 冻结 → 后半窗（2021-01-01→2026-08-18）OOS 检验。
（TRD 序列本身用全历史价格计算滚动收益，属「指标计算」非「参数
选择」，与 B200 同口径，无前视。）

臂（后半窗 OOS）：持有 / TRD 门 / B200 门（对照披露）。
判定（冻结，OOS 窗）：
- T1：TRD 门 Calmar ≥ 持有 Calmar × 1.5；
- T2：TRD 门年化 ≥ 持有年化 − 2.0pp；
- 总 PASS = T1∧T2。
纪律：不改 configs/web/engine/service；结论建议级。
输出：docs/experiments/raw/trd_gate/trd_gate_results.json
复现：PYTHONHASHSEED=0 python3 scripts/run_trd_gate.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "docs/experiments/raw"
sys.path.insert(0, str(REPO / "scripts"))

import run_portfolio_split as rps  # noqa: E402

RAW = SRC / "trd_gate"
LOOKBACK = 252
SPLIT = "2021-01-01"
T1_CAL_MULT, T2_ANN_TOL = 1.5, 2.0


def weekly_signal(trd: pd.Series, dates: pd.DatetimeIndex,
                  lo: float, hi: float) -> pd.Series:
    """TRD 三档（≤lo→1.0，<hi→0.6，≥hi→0.2）周频次日生效。"""
    bw, bsig = rps.weekly_last(trd)
    tiers = bw.map(lambda v: 1.0 if v <= lo else (0.6 if v < hi else 0.2))
    out = pd.Series(np.nan, index=dates)
    pos = dates.searchsorted(list(bsig.values))
    for p, w in zip(pos, tiers.values, strict=True):
        if p + 1 < len(dates):
            out.iloc[p + 1] = w
    return out.ffill().fillna(0.6)


def run_arm(prices: pd.DataFrame, expo: pd.DataFrame) -> dict:
    return rps.metrics(rps.simulate(prices, expo)["eq"])


def main() -> None:
    members = [(k, v) for k, v in {**rps.GATED, **rps.TREND}.items()]
    frames = {}
    for name, rel in members:
        s = pd.read_parquet(SRC / rel)["close"].astype(float)
        s.index = pd.to_datetime(s.index)
        frames[name] = s
    prices = pd.DataFrame(frames)
    prices = prices[(prices.index >= pd.Timestamp(rps.WIN_START))
                    & (prices.index <= pd.Timestamp(rps.WIN_END))] \
        .dropna(axis=0, how="any")

    hs300 = pd.read_parquet(SRC / "portfolio_split/sh000300_close.parquet")["close"].astype(float)
    hs300.index = pd.to_datetime(hs300.index)
    bond = pd.read_parquet(SRC / "cash_leg/511010_close.parquet")["close"].astype(float)
    bond.index = pd.to_datetime(bond.index)
    both = pd.concat([hs300.rename("eq"), bond.rename("bond")], axis=1).dropna()
    trd = both["eq"].pct_change(LOOKBACK) - both["bond"].pct_change(LOOKBACK)
    trd = trd.dropna()

    # 前半窗定档线（冻结），后半窗 OOS
    fit = trd[(trd.index >= prices.index[0]) & (trd.index < pd.Timestamp(SPLIT))]
    lo_q, hi_q = float(fit.quantile(0.25)), float(fit.quantile(0.75))

    oos_mask = prices.index >= pd.Timestamp(SPLIT)
    p_oos = prices[oos_mask]
    ones_oos = pd.DataFrame(1.0, index=p_oos.index, columns=p_oos.columns)

    tier_trd = weekly_signal(trd, prices.index, lo_q, hi_q)[oos_mask]
    expo_trd = pd.DataFrame({c: tier_trd for c in p_oos.columns})

    b200 = rps.load_breadth()
    tier_b200 = rps.tier_daily(b200, prices.index)[oos_mask]
    expo_b200 = pd.DataFrame({c: tier_b200 for c in p_oos.columns})

    hold_m = run_arm(p_oos, ones_oos)
    trd_m = run_arm(p_oos, expo_trd)
    b200_m = run_arm(p_oos, expo_b200)

    t1 = bool(trd_m["calmar"] is not None and hold_m["calmar"] is not None
              and trd_m["calmar"] >= hold_m["calmar"] * T1_CAL_MULT)
    t2 = bool(trd_m["ann_pct"] >= hold_m["ann_pct"] - T2_ANN_TOL)

    out = {
        "experiment": "trd_gate_equity_bond",
        "window": [SPLIT, str(prices.index[-1].date())],
        "lookback_days": LOOKBACK,
        "fit_quantiles": {"q25": round(lo_q, 4), "q75": round(hi_q, 4)},
        "fit_window": [str(prices.index[0].date()), "2020-12-31"],
        "posterior_note": "档线由前半窗分位冻结，OOS 后半窗检验",
        "arms_oos": {"hold": hold_m, "trd_gate": trd_m, "b200_gate_ref": b200_m},
        "verdict_rules": {
            "T1": f"trd Calmar >= hold Calmar x {T1_CAL_MULT}",
            "T2": f"trd ann >= hold ann - {T2_ANN_TOL}pp",
        },
        "verdict": {"T1": t1, "T2": t2, "PASS_all": bool(t1 and t2)},
    }
    RAW.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True)
    (RAW / "trd_gate_results.json").write_text(text)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sha256:", hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
