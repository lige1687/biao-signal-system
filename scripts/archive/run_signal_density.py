#!/usr/bin/env python3
"""LEI 信号密度温度计·侧向探索（2026-08-31）：体系内生信息源初探。

问题：宽度 B200 是外部数据（全 A 市场）。LEI 系统自己的信号流（A 回调/
C 破底翻的产生率）是否本身就是市场状态信息？若成立，体系获得一个
「自举」信息源（不依赖外部宽度数据）。

【探索协议】（后验探索、如实标注：非预注册认证；任何规则不入门禁）
数据：已留痕 run 的信号流——
- A = portfolio/A_ETF_cm05_shrink.json（ETF 池 18 只，门禁后 283 笔）
- C = lifecycle_combo/T2_C_stocks_v3_b15.json（股票池 53 只，v3+b15，177 笔）
（D 默认参数仅 2 笔无统计力，不入分析；池规模归一化密度。）
指标：月度信号密度 = 当月信号数 ÷ 池规模。分析窗 2019-08→2026-06
（两流交集）。对照：B200 月均、沪深300 未来 1 月收益。
产出：IC、三分位、同期相关、阴跌段形态、脉冲事件表。
定位声明：83 个月样本、密度脉冲事件仅 3 次——不足以支撑门控规则，
只作为「观察指标候选」进入打分卡观察名单，不做任何仓位规则。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "docs/experiments/raw"
sys.path.insert(0, str(REPO / "scripts"))

RAW = SRC / "signal_density"

POOL_A, POOL_C = 18, 53


def main() -> None:
    a_tr = json.loads((SRC / "portfolio/A_ETF_cm05_shrink.json").read_text())["trades"]
    c_tr = json.loads((SRC / "lifecycle_combo/T2_C_stocks_v3_b15.json").read_text())["trades"]
    a = pd.to_datetime(pd.Series([t["signal_date"] for t in a_tr])).value_counts().sort_index()
    c = pd.to_datetime(pd.Series([t["signal_date"] for t in c_tr])).value_counts().sort_index()
    a_m = a.resample("ME").sum() / POOL_A
    c_m = c.resample("ME").sum() / POOL_C

    b200_rows = json.loads(
        (SRC / "breadth_overlay/a_share_breadth_33y_snapshot.json").read_text())
    b200 = pd.Series(
        {pd.Timestamp(r["date"]): r["ma200_pct"] for r in b200_rows
         if r.get("ma200_pct") is not None}).astype(float).sort_index()
    hs300 = pd.read_parquet(SRC / "portfolio_split/sh000300_close.parquet")["close"].astype(float)
    hs300.index = pd.to_datetime(hs300.index)

    fwd1m = hs300.resample("ME").last().pct_change().shift(-1)
    b200_m = b200.resample("ME").mean()
    df = pd.DataFrame({"a_dens": a_m, "c_dens": c_m, "b200": b200_m,
                       "fwd1m": fwd1m}).dropna()

    def tercile(col: str) -> dict:
        q = pd.qcut(df[col].rank(method="first"), 3, labels=["低", "中", "高"])
        g = df.groupby(q, observed=True)["fwd1m"]
        return {k: round(float(v) * 100, 2) for k, v in g.mean().items()}

    # 阴跌段形态（2021-06-18 → 2024-02-29，B9 最痛段）
    seg = c_m[(c_m.index >= "2021-06") & (c_m.index <= "2024-03")]
    # 密度脉冲事件：月密度 >= 0.10（池内 ≥5% 标的当月出破底翻信号）
    pulses = c_m[c_m >= 0.10]

    out = {
        "experiment": "lei_signal_density_thermometer",
        "sample_months": int(len(df)),
        "window": [str(df.index.min().date()), str(df.index.max().date())],
        "posterior_disclaimer": "后验探索非预注册；不入门禁；仅观察指标候选",
        "ic_with_hs300_fwd1m": {
            "a_density": round(float(df.a_dens.corr(df.fwd1m)), 3),
            "c_density": round(float(df.c_dens.corr(df.fwd1m)), 3),
            "b200_monthly": round(float(df.b200.corr(df.fwd1m)), 3),
        },
        "tercile_fwd1m_pct": {"a_density": tercile("a_dens"),
                              "c_density": tercile("c_dens"),
                              "b200": tercile("b200")},
        "contemp_corr": {
            "c_vs_b200": round(float(df.c_dens.corr(df.b200)), 3),
            "a_vs_b200": round(float(df.a_dens.corr(df.b200)), 3),
        },
        "drawdown_seg_c_density": {
            "window": ["2021-06", "2024-03"],
            "zero_month_ratio": round(float((seg == 0).mean()), 2),
            "mean": round(float(seg.mean()), 3),
        },
        "pulse_events_c": {str(k.date()): round(float(v), 3)
                           for k, v in pulses.items()},
        "a_zero_month_ratio": round(float((df.a_dens == 0).mean()), 2),
    }
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True)
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "signal_density_results.json").write_text(text)
    pd.DataFrame({"a_dens": a_m, "c_dens": c_m}).to_csv(
        RAW / "monthly_density.csv", float_format="%.4f")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sha256:", hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
