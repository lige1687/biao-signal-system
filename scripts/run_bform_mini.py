"""迷你指数池·预注册实验（2026-08-28，跑前写死，跑后不改）。

用户诉求：标的太多看不过来，精简为少数几只宽基（点名：沪深300、标普、
创业板、科创50/100）。本实验测「简化的代价」。

【预注册协议】
机械与 B 形态/M5 完全一致：A 腿 × B200 三档 43.3/56.7（周频次日生效），
美腿无闸持有；等权、5% 带、单边 10bp；A 股日历（美腿 ffill）。
迷你池（*=A 腿上闸；美腿持有）：
- MINI3  = 沪深300*、创业板* | 标普          （窗 2010-06→2026-08）
- MINI4  = 沪深300*、创业板* | 标普、纳指      （窗 2010-06→）
- MINI5  = 沪深300*、创业板*、科创50* | 标普、纳指（窗 2020-01→）
- MINI4K = 创业板*、科创50*、科创100* | 标普    （窗 2020-01→，科创重仓变体）
判定（冻结，每池独立）：
- C1 风险转换有效：该池 M 版 vs 该池等权持有——maxDD 浅 ≥8pp 且 Calmar 更高。
- C2 简化代价可接受：该池 M 版年化 ≥ 同窗 B9 年化 − 2pp。
- 两过 =「可用简化版」；只过 C1 = 简化有代价；C1 不过 = 弃。

输出：docs/experiments/raw/portfolio_split/bform_mini_results.json
复现：PYTHONHASHSEED=0 python3 scripts/run_bform_mini.py

---
恢复说明（2026-09-17，目录治理任务）：原文件在 2026-09-01 工作区回退事故中
丢失且 git 对象库中已无幸存 blob（其余三个同根脚本见
scripts/legacy_recovery/）。本文件由 scripts/__pycache__/run_bform_mini.
cpython-311.pyc 的字节码逐函数反汇编重建：文档字符串、全部模块常量
（迷你池配置、阈值、数据路径）、load_series/b9_ref/main 的控制流均取自
字节码常量与指令序列。验证方式：重跑后输出与已归档的
raw/portfolio_split/bform_mini_results.json 逐字节一致（sha256 对照）。
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

import run_portfolio_split as rps  # noqa: E402
from run_bform_dynamic import simulate_direct  # noqa: E402
from run_m5_walkforward import tier_for  # noqa: E402

_A_BASE = [
    ("沪深300", "portfolio_split/sh000300_close.parquet"),
    ("创业板指", "siphon_detector/cyb_399006_close.parquet"),
]
_A_KC = ("科创50", "portfolio_split/sh000688_close.parquet")
_A_KC100 = ("科创100", "portfolio_split/sh000698_close.parquet")
_US_SPX = ("标普500", "breadth_position/gspc_long_close.parquet")
_US_NDX = ("纳斯达克", "portfolio_split/ixic_close.parquet")

POOLS = {
    "MINI3": {"A": _A_BASE, "US": [_US_SPX], "start": "2010-06-01"},
    "MINI4": {"A": _A_BASE, "US": [_US_SPX, _US_NDX], "start": "2010-06-01"},
    "MINI5": {"A": _A_BASE + [_A_KC], "US": [_US_SPX, _US_NDX], "start": "2020-01-02"},
    "MINI4K": {
        "A": [_A_BASE[1], _A_KC, _A_KC100],
        "US": [_US_SPX],
        "start": "2020-01-02",
    },
}
C1_DD, C2_TOL = 8.0, 2.0


def load_series(rel):
    s = pd.read_parquet(SRC / rel)["close"].astype(float)
    s.index = pd.to_datetime(s.index)
    return s


def b9_ref(b200, lo):
    members = [(k, v) for k, v in {**rps.GATED, **rps.TREND}.items()]
    frames = {n: load_series(rel) for n, rel in members}
    p9 = pd.DataFrame(frames)
    p9 = p9[(p9.index >= pd.Timestamp(lo)) & (p9.index <= pd.Timestamp(rps.WIN_END))].dropna()
    t9 = tier_for(b200, p9.index, 43.3, 56.7)
    return rps.metrics(simulate_direct(p9, pd.DataFrame({c: t9 / 9 for c in p9.columns})))


def main():
    b200 = rps.load_breadth()
    out = {}
    for name, cfg in POOLS.items():
        frames = {n: load_series(rel) for n, rel in cfg["A"] + cfg["US"]}
        px = pd.DataFrame(frames)
        cn = px[[n for n, _ in cfg["A"]]].dropna().index
        px = px.reindex(cn).ffill()
        px = px[(px.index >= pd.Timestamp(cfg["start"]))
                & (px.index <= pd.Timestamp(rps.WIN_END))].dropna()
        n = px.shape[1]
        tier = tier_for(b200, px.index, 43.3, 56.7)
        ones = pd.DataFrame(1.0, px.index, px.columns)
        expo = ones.copy()
        for c, _ in cfg["A"]:
            expo[c] = tier
        m_m = rps.metrics(simulate_direct(px, expo / n))
        m_h = rps.metrics(simulate_direct(px, ones / n))
        m_b9 = b9_ref(b200, cfg["start"])
        c1 = m_m["maxdd_pct"] - m_h["maxdd_pct"] >= C1_DD and m_m["calmar"] > m_h["calmar"]
        c2 = m_m["ann_pct"] >= m_b9["ann_pct"] - C2_TOL
        out[name] = {
            "legs": [n for n, _ in cfg["A"]] + [f"{n}(持有)" for n, _ in cfg["US"]],
            "窗口": f"{cfg['start']}→{rps.WIN_END}",
            "M版": m_m,
            "等权持有": m_h,
            "B9同窗参考": m_b9,
            "C1": bool(c1),
            "C2": bool(c2),
            "判定": "可用简化版" if c1 and c2 else "简化有代价" if c1 else "弃",
        }
    path = SRC / "portfolio_split/bform_mini_results.json"
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True, default=str)
    path.write_text(text)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print("sha256:" + hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
