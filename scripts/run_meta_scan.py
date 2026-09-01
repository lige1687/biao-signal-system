#!/usr/bin/env python3
"""LEI 信号元特征大扫描·侧向探索（2026-08-31）：六假设一次检验。

问题：已留痕逐笔交易里，哪些「信号元特征」与实现收益相关？——
为执行层/资金层提供分组证据，也为后续预注册实验找候选。

【探索协议】（后验探索、如实标注：非预注册；发现的任何分组不直接
入门禁，只作候选线索。）
数据：三流已留痕 run 的 trades——
- A = portfolio/A_ETF_cm05_shrink.json（ETF 池，283 笔）
- B'= portfolio/Bp_stocks_30_3_a61.json（股票池，101 笔）
- C = lifecycle_combo/T2_C_stocks_v3_b15.json（股票池，177 笔）
环境变量：沪深300 收盘（20 日实现波动、信号日环境）。

六假设：
- H1 校准：纸面 reward_risk 五分位 → 平均实现 r_net 是否单调递增
  （正校准 = 门槛有信息；并对照对角线看系统性高估/低估）；
- H2 止损穿透：r_net < -1.5R 的跳空穿透单占比与深度分布
  （a6_1 抵扣价出场的隐性执行成本）；
- H3 周内效应：signal_date 的 weekday → expR；
- H4 持有期：holding_bars 分桶 → r_net 与占比；
- H5 同日聚集：同日信号数 → 当批平均 r_net；
- H6 波动率环境：信号日沪深300 20 日实现波动三分位 → r_net。

产出：raw/meta_scan/meta_scan_results.json + 报告。
复现：PYTHONHASHSEED=0 python3 scripts/run_meta_scan.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "docs/experiments/raw"
RAW = SRC / "meta_scan"

RUNS = {
    "A": SRC / "portfolio/A_ETF_cm05_shrink.json",
    "B'": SRC / "portfolio/Bp_stocks_30_3_a61.json",
    "C": SRC / "lifecycle_combo/T2_C_stocks_v3_b15.json",
}


def main() -> None:
    frames = []
    for m, p in RUNS.items():
        trs = json.loads(p.read_text())["trades"]
        f = pd.DataFrame([{ "signal_date": t["signal_date"],
                            "symbol": t["symbol"], "rr": t.get("reward_risk"),
                            "r_net": t.get("r_net"), "r_gross": t.get("r_gross"),
                            "hold": t.get("holding_bars"),
                            "stage": t.get("trend_stage")} for t in trs])
        f["module"] = m
        frames.append(f)
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["signal_date"])
    df["weekday"] = df["date"].dt.dayofweek  # 0=Mon
    df = df.dropna(subset=["r_net"]).reset_index(drop=True)

    hs300 = pd.read_parquet(SRC / "portfolio_split/sh000300_close.parquet")["close"].astype(float)
    hs300.index = pd.to_datetime(hs300.index)
    vol20 = (hs300.pct_change().rolling(20).std() * (252 ** 0.5) * 100)
    df["vol20"] = vol20.reindex(df["date"]).values

    out: dict = {"experiment": "lei_meta_scan",
                 "posterior_disclaimer": "后验探索非预注册；分组不直接入门禁",
                 "total_trades": int(len(df)),
                 "by_module": {m: {"n": int(len(g)), "expR": round(float(g.r_net.mean()), 3)}
                               for m, g in df.groupby("module")}}

    # H1 校准：纸面 RR 五分位 → 实现（rr 可能缺失）
    sub = df.dropna(subset=["rr"]).copy()
    sub = sub[sub["rr"] > 0]
    sub["rr_q"] = pd.qcut(sub["rr"].rank(method="first"), 5,
                          labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
    h1 = {}
    for name, g in sub.groupby("rr_q", observed=True):
        h1[str(name)] = {"n": int(len(g)), "mean_rr": round(float(g.rr.mean()), 2),
                         "expR": round(float(g.r_net.mean()), 3),
                         "win": round(float((g.r_net > 0).mean()), 3)}
    corr = float(sub["rr"].corr(sub["r_net"]))
    keys = sorted(h1)
    out["H1_calibration"] = {"quintiles": h1,
                             "corr_rr_rnet": round(corr, 3),
                             "monotone": bool(all(h1[a]["expR"] <= h1[b]["expR"]
                                                  for a, b in zip(keys, keys[1:],
                                                                  strict=True)))}

    # H2 止损穿透
    through = df[df["r_net"] < -1.5]
    out["H2_stop_through"] = {
        "n_lt_-1.5R": int(len(through)),
        "pct": round(float(len(through) / len(df)), 3),
        "mean_depth": round(float(through.r_net.mean()), 2) if len(through) else None,
        "worst": round(float(df.r_net.min()), 2),
        "p5_rnet": round(float(df.r_net.quantile(0.05)), 2),
    }

    # H3 周内效应
    wd = df.groupby("weekday")["r_net"].agg(["size", "mean"])
    out["H3_weekday"] = {["Mon", "Tue", "Wed", "Thu", "Fri"][k]:
                         {"n": int(r["size"]), "expR": round(float(r["mean"]), 3)}
                         for k, r in wd.iterrows()}

    # H4 持有期
    bins = [0, 5, 10, 20, 40, 10000]
    labels = ["1-5", "6-10", "11-20", "21-40", "40+"]
    df["hold_b"] = pd.cut(df["hold"], bins=bins, labels=labels)
    hb = df.groupby("hold_b", observed=True)["r_net"].agg(["size", "mean"])
    out["H4_holding"] = {str(k): {"n": int(r["size"]), "expR": round(float(r["mean"]), 3)}
                         for k, r in hb.iterrows()}

    # H5 同日聚集（同日同模块信号数）
    cnt = df.groupby(["module", "signal_date"]).size().rename("n_day")
    df2 = df.merge(cnt, left_on=["module", "signal_date"], right_index=True)
    df2["cl_b"] = pd.cut(df2["n_day"], [0, 1, 3, 100],
                         labels=["1", "2-3", "4+"])
    cl = df2.groupby("cl_b", observed=True)["r_net"].agg(["size", "mean"])
    out["H5_cluster"] = {str(k): {"n": int(r["size"]), "expR": round(float(r["mean"]), 3)}
                         for k, r in cl.iterrows()}

    # H6 波动率环境
    sub6 = df.dropna(subset=["vol20"]).copy()
    sub6["vol_q"] = pd.qcut(sub6["vol20"].rank(method="first"), 3,
                            labels=["低", "中", "高"])
    h6 = {}
    for name, g in sub6.groupby("vol_q", observed=True):
        h6[str(name)] = {"n": int(len(g)),
                         "expR": round(float(g.r_net.mean()), 3),
                         "win": round(float((g.r_net > 0).mean()), 3),
                         "vol_band": [round(float(g.vol20.min()), 1),
                                      round(float(g.vol20.max()), 1)]}
    out["H6_vol_env"] = h6

    RAW.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True)
    (RAW / "meta_scan_results.json").write_text(text)
    df.to_csv(RAW / "merged_trades.csv", index=False, float_format="%.4f")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sha256:", hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
