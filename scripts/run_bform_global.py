"""跨市场宽指组合·预注册实验（2026-08-28，跑前写死，跑后不改）。

用户立项：统一时间内配置 纳斯达克/标普/创业板/沪深300/红利 等宽基指数
（非行业），与宽度体系结合。

【预注册协议】
标的（5，用户点名）：标普500（GSPC 缓存 1985→）、纳斯达克（IXIC 2004→）、
创业板指、沪深300、上证红利（红利为价格指数，股息未计——该腿持有收益
被低估最多，跨臂同向不影响相对结论，引用绝对收益须声明）。
窗口：2010-06-01→2026-08-18（创业板起点与 A 股宽度终点）。日历 = A 股
交易日，美股价格 ffill 到 A 股日历（美假期折零收益、跨日合并，已声明）。
机械：等权 1/5、5% 带、单边 10bp、周频信号次日生效（与 B 形态同）。

臂：
- H5 等权持有（无覆盖）。
- G5 全上闸：A 腿×全A B200 三档；美腿×SP500 B200 三档（逆势 43.3/56.7）
  ——证伪臂，血统预期：美宽度逆势 40 年判负。
- M5 适配分治（主案）：A 腿（创业板/300/红利）× 全A B200 三档；
  美腿（标普/纳指）无闸持有。
- M5D = M5 + 美腿价格闸（收盘<自身 MA200 → ×0.5，周频）——防守画像。

判定（冻结）：
- C1（跨市场有效性）：M5 vs H5 年化差 ≥ +2pp 且 maxDD 浅 ≥10pp。
- C2（对纯 A 池）：M5 Calmar ≥ 同窗 B 形态 9 池 Calmar。
- C3（证伪臂确认）：G5 年化 < M5 年化。
- **PASS = C1∧C2 → 「跨市场版」候选进终审队列；仅 C1 → 归档为配置型
  可选（分散价值）；C1 不过 → 整体归档。**

输出：docs/experiments/raw/portfolio_split/bform_global_results.json
复现：PYTHONHASHSEED=0 python3 scripts/run_bform_global.py

---
恢复说明（2026-09-17，目录治理任务）：原文件在 2026-09-01 工作区回退事故中
丢失且 git 对象库中已无幸存 blob。本文件由 scripts/__pycache__/run_bform_
global.cpython-311.pyc 的字节码逐函数反汇编重建：文档字符串、全部模块常量
（腿配置、窗口、阈值）、load_px/tier_for/gate_ma200/main/expo_matrix 的
控制流均取自字节码常量与指令序列。验证方式：重跑后输出与已归档的
raw/portfolio_split/bform_global_results.json 逐字节一致（sha256 对照）。
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
from run_bform_dynamic import simulate_direct  # noqa: E402

WIN_S, WIN_E = "2010-06-01", "2026-08-18"
C1_ANN, C1_DD = 2.0, 10.0

A_LEGS = {
    "创业板指": "siphon_detector/cyb_399006_close.parquet",
    "沪深300": "portfolio_split/sh000300_close.parquet",
    "上证红利": "portfolio_split/sh000015_close.parquet",
}
US_LEGS = {
    "标普500": "breadth_position/gspc_long_close.parquet",
    "纳斯达克": "portfolio_split/ixic_close.parquet",
}


def load_px():
    frames = {}
    for name, rel in {**A_LEGS, **US_LEGS}.items():
        s = pd.read_parquet(SRC / rel)["close"].astype(float)
        s.index = pd.to_datetime(s.index)
        frames[name] = s
    px = pd.DataFrame(frames)
    cn = px[list(A_LEGS)].dropna().index
    px = px.reindex(cn).ffill()
    px = px[(px.index >= pd.Timestamp(WIN_S)) & (px.index <= pd.Timestamp(WIN_E))].dropna()
    return px


def tier_for(b200_daily: pd.Series, dates) -> pd.Series:
    bw, bsig = rps.weekly_last(b200_daily)
    w = bw.map(lambda v: 1.0 if v < 43.3 else 0.5 if v < 56.7 else 0.0)
    out = pd.Series(np.nan, index=dates)
    pos = dates.searchsorted(list(bsig.values))
    for p, wt in zip(pos, w.values):
        if p + 1 < len(dates):
            out.iloc[p + 1] = wt
    return out.ffill().fillna(0.0)


def gate_ma200(price_full: pd.Series, dates) -> pd.Series:
    above = (price_full > price_full.rolling(200).mean()).astype(float) * 0.5 + 0.5
    gw, gsig = rps.weekly_last(above)
    out = pd.Series(np.nan, index=dates)
    pos = dates.searchsorted(list(gsig.values))
    for p, gv in zip(pos, gw.values):
        if p + 1 < len(dates):
            out.iloc[p + 1] = float(gv)
    return out.ffill().fillna(1.0)


def main() -> None:
    b200a = rps.load_breadth()
    with open(Path("~/.lei_signal_lab/cache/sp500_ma_breadth_history.json").expanduser()) as f:
        urows = json.load(f)
    b200u = pd.Series(
        {pd.Timestamp(r["date"]): r["breadth_200"] for r in urows if r.get("breadth_200") is not None}
    ).astype(float).sort_index()

    px = load_px()
    dates = px.index
    n = px.shape[1]
    tier_a = tier_for(b200a, dates)
    tier_u = tier_for(b200u, dates)
    ones = pd.DataFrame(1.0, index=dates, columns=px.columns)

    def expo_matrix(mode: str) -> pd.DataFrame:
        df_ = ones.copy()
        for c in px.columns:
            if c in A_LEGS:
                df_[c] = tier_a if mode in ("gate_all", "split") else 1.0
            elif mode == "gate_all":
                df_[c] = tier_u
            elif mode == "split_d":
                s_us = pd.read_parquet(SRC / US_LEGS[c])["close"].astype(float)
                s_us.index = pd.to_datetime(s_us.index)
                df_[c] = tier_u * gate_ma200(s_us, dates)
            else:
                df_[c] = 1.0
        return df_

    arms = {
        "H5_等权持有": rps.metrics(simulate_direct(px, ones / n)),
        "G5_全上闸": rps.metrics(simulate_direct(px, expo_matrix("gate_all") / n)),
        "M5_适配分治": rps.metrics(simulate_direct(px, expo_matrix("split") / n)),
        "M5D_分治+美价格闸": rps.metrics(simulate_direct(px, expo_matrix("split_d") / n)),
    }

    members = [(k, v) for k, v in {**rps.GATED, **rps.TREND}.items()]
    frames = {}
    for name, rel in members:
        s = pd.read_parquet(SRC / rel)["close"].astype(float)
        s.index = pd.to_datetime(s.index)
        frames[name] = s
    p9 = pd.DataFrame(frames)
    p9 = p9[(p9.index >= pd.Timestamp(WIN_S)) & (p9.index <= pd.Timestamp(WIN_E))].dropna()
    t9 = tier_for(b200a, p9.index)
    tgt9 = pd.DataFrame({c: t9 / 9 for c in p9.columns})
    b9_ref = rps.metrics(simulate_direct(p9, tgt9))

    m5, h5, g5 = arms["M5_适配分治"], arms["H5_等权持有"], arms["G5_全上闸"]
    c1 = m5["ann_pct"] - h5["ann_pct"] >= C1_ANN and m5["maxdd_pct"] - h5["maxdd_pct"] >= C1_DD
    c2 = m5["calmar"] >= b9_ref["calmar"]
    c3 = g5["ann_pct"] < m5["ann_pct"]
    verdict = {
        "arms": arms,
        "B9_same_window_ref": b9_ref,
        "C1": {
            "ann_gap": round(m5["ann_pct"] - h5["ann_pct"], 2),
            "dd_gap": round(m5["maxdd_pct"] - h5["maxdd_pct"], 2),
            "pass": bool(c1),
        },
        "C2": {"calmar_M5": m5["calmar"], "calmar_B9": b9_ref["calmar"], "pass": bool(c2)},
        "C3_gate_all_worse": bool(c3),
        "VERDICT": "PASS_跨市场候选" if c1 and c2 else "仅C1_配置型可选" if c1 else "FAIL_归档",
    }
    path = SRC / "portfolio_split/bform_global_results.json"
    text = json.dumps(verdict, ensure_ascii=False, indent=1, sort_keys=True, default=str)
    path.write_text(text)
    print(json.dumps(verdict, ensure_ascii=False, indent=1, default=str))
    print("sha256:" + hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
