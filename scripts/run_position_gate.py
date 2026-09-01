#!/usr/bin/env python3
"""机构权益仓位 vs 股指：A 股乐咕仓位指数 + 美股 NAAIM（2026-08-28 第十七轮）。

用户假设（原文）：「机构也是大号散户，仓位达到一定阈值市场就要回撤」
——机构持仓占比做逆势温度计的可测化。

数据（本轮新增，固化 raw/sentiment/）：
- A 股：乐咕「股票仓位」指数（fund_stock_position_lg，周频
  2017-12→2026-08，449 期；当前 96.5% = 历史 98 分位）
- 美股：NAAIM Exposure（官方嵌入图表解析，130 周 2023-11→2026-05；
  全史 2006 起需会员——挂账）

预注册判定（跑前落死）：
- J-P1（A 股事件研究）：仓位 ≥ 自身 90 分位（自适应阈值，当前=94.7%）
  / ≤ 10 分位后，沪深300 的 1/3/6/12 月远期收益 vs 全样本基线。
  用户假设成立方向 = 高仓位区远期收益显著低于基线。
- J-P2（A 股闸）：档位 ≥90 分位→0.5 / ≤10 分位→1.0 / 中间→0.8
  （周频 t+1 开盘、5bp），对照 BH 与宽度五档（同窗 2017-12→2026-08）。
  胜出 = DD 改善 ≥15%（vs BH）且 CAGR ≥ 0.8×BH。
- J-P3（当前状态专项）：仓位 ≥96% 的历史周之后 3/6/12 月表现
  （当前 96.5% 的前瞻参考）。
- J-P4（美股，130 周短样本仅方向参考）：NAAIM ≥90/≤10 分位后
  SPX 的 3/6/12 月远期。
- 声明：乐咕口径为基金股票仓位估算（非官方审计）；NAAIM 为主动
  管理人自报周度调查；窗口重叠未做显著性检验；A 股窗口 8.7 年
  覆盖 2018 熊/2019-20 牛/2021-24 阴跌/2025-26。

输出：raw/sentiment/position_gate_results.json
复现：python3 scripts/run_position_gate.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from run_breadth_overlay import load_breadth  # noqa: E402
from run_caliber_check import tier_target_map  # noqa: E402
from run_final_form_v2 import H80  # noqa: E402
from run_sentiment_gate import cagr_dd, event_study, sim_bh, sim_width  # noqa: E402

RAW = REPO / "docs/experiments/raw/sentiment"
CACHE = Path.home() / ".lei_signal_lab/cache"


def load_a_position() -> pd.Series:
    df = pd.read_csv(RAW / "fund_stock_position_lg.csv", parse_dates=["date"])
    return df.set_index("date")["position"].astype(float).sort_index()


def load_naaim() -> pd.Series:
    obj = json.loads((RAW / "naaim_hist.json").read_text())
    s = pd.Series(obj["values"], index=pd.to_datetime(obj["dates"]),
                  dtype=float).sort_index()
    return s


def pct_gate_map(sig: pd.Series, hi_q=0.9, lo_q=0.1) -> dict[str, float]:
    hi, lo = sig.quantile(hi_q), sig.quantile(lo_q)
    out: dict[str, float] = {}
    days = sig.index
    for i in range(len(days) - 1):
        v = sig.iloc[i]
        if pd.isna(v):
            continue
        pos = 0.5 if v >= hi else (1.0 if v <= lo else 0.8)
        out[str(days[i + 1].date())] = pos
    return out


def main() -> int:
    # 数据固化
    for src, dst in (("/tmp/fund_stock_position_lg.csv",
                      RAW / "fund_stock_position_lg.csv"),
                     ("/tmp/naaim_hist.json", RAW / "naaim_hist.json")):
        p = Path(src)
        if p.exists():
            shutil.copy(p, dst)
    pos = load_a_position()
    naaim = load_naaim()
    idx = pd.read_parquet(CACHE / "timing/000300.parquet")[["open", "close"]]
    idx.index = pd.to_datetime(idx.index).tz_localize(None).normalize()
    spx = pd.read_parquet(REPO / "docs/experiments/raw/module_e/"
                          "us_gspc_ohlc.parquet")["close"]
    spx.index = pd.to_datetime(spx.index).tz_localize(None).normalize()

    hi, lo = pos.quantile(0.9), pos.quantile(0.1)
    win = idx.loc[pos.index[0]:]
    jp1 = {"hi_th": round(float(hi), 1), "lo_th": round(float(lo), 1),
           **event_study(pos, win["close"], lo=2, hi=-1)}  # 占位替换↓
    # event_study 用分位掩码重算（其 lo/hi 是数值阈值——这里传分位值）
    jp1 = {"hi_th": round(float(hi), 1), "lo_th": round(float(lo), 1)}
    sig_hi = pos >= hi
    sig_lo = pos <= lo
    fwd = {h: win["close"].shift(-h) / win["close"] - 1
           for h in (21, 63, 126, 252)}
    base = {h: round(float(f.mean()), 4) for h, f in fwd.items()}
    hi_res, lo_res = {}, {}
    for h, f in fwd.items():
        vals = [f.get(d) for d in pos.index[sig_hi] if d in f.index]
        vals = [v for v in vals if pd.notna(v)]
        hi_res[h] = {"n": len(vals),
                     "mean": round(float(pd.Series(vals).mean()), 4)}
        vals = [f.get(d) for d in pos.index[sig_lo] if d in f.index]
        vals = [v for v in vals if pd.notna(v)]
        lo_res[h] = {"n": len(vals),
                     "mean": round(float(pd.Series(vals).mean()), 4)}
    jp1.update({"baseline": base, "hi": hi_res, "lo": lo_res})

    # J-P3：≥96% 专项
    sig96 = pos >= 96
    r96 = {}
    for h, f in fwd.items():
        vals = [f.get(d) for d in pos.index[sig96] if d in f.index]
        vals = [v for v in vals if pd.notna(v)]
        r96[h] = {"n": len(vals),
                  "mean": round(float(pd.Series(vals).mean()), 4)}
    jp3 = {"current_pos": float(pos.iloc[-1]),
           "after_ge96": r96}

    # J-P2 闸
    bars = win
    p_map = pct_gate_map(pos)
    br = load_breadth()
    w_map = tier_target_map(br, "ma200_pct", H80)
    p_eq = sim_width(bars, p_map)
    w_eq = sim_width(bars, w_map)
    bh = sim_bh(bars)
    arms = {"position_gate": cagr_dd(p_eq), "breadth_gate": cagr_dd(w_eq),
            "bh": cagr_dd(bh)}
    dd_impr = (abs(arms["bh"]["max_dd"]) - abs(arms["position_gate"]["max_dd"])) \
        / abs(arms["bh"]["max_dd"])
    keep = arms["position_gate"]["cagr"] / arms["bh"]["cagr"] \
        if arms["bh"]["cagr"] else None
    jp2 = {"arms": arms,
           "dd_improve": round(float(dd_impr), 3),
           "cagr_keep": round(keep, 3) if keep is not None else None,
           "pass": bool(dd_impr >= 0.15 and keep is not None and keep >= 0.8)}

    # J-P4 NAAIM（短样本方向参考）
    nw = spx.loc[naaim.index[0]:]
    nhi, nlo = naaim.quantile(0.9), naaim.quantile(0.1)
    nf = {h: nw.shift(-h) / nw - 1 for h in (63, 126, 252)}
    jp4 = {"hi_th": round(float(nhi), 1), "lo_th": round(float(nlo), 1),
           "baseline": {h: round(float(f.mean()), 4) for h, f in nf.items()}}
    for name, mask in (("hi", naaim >= nhi), ("lo", naaim <= nlo)):
        res = {}
        for h, f in nf.items():
            vals = [f.get(d) for d in naaim.index[mask] if d in f.index]
            vals = [v for v in vals if pd.notna(v)]
            res[h] = {"n": len(vals),
                      "mean": round(float(pd.Series(vals).mean()), 4)}
        jp4[name] = res

    out = {"date": "2026-08-28", "JP1_cn_event": jp1, "JP2_gate": jp2,
           "JP3_ge96": jp3, "JP4_naaim": jp4,
           "notes": "NAAIM 全史 2006 起需会员（挂账）；乐咕口径为估算仓位"}
    (RAW / "position_gate_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
