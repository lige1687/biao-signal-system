#!/usr/bin/env python3
"""基本面/情绪信息统一相关性面板 + 数据准确性核查（2026-08-28 第十八轮）。

用户口径：测基本面信息与股指的相关性，并保证数据准确性。

指标清单（全部为已固化或本轮新增资产）：
  A 股（基准=沪深300）：全A B200/B50、CSI300 B200、两融 20 日变化分位、
  北向 20 日净流入分位（历史死源）、乐咕基金仓位、中债 10Y（水平+60日
  变化）、制造业 PMI（水平+3 月变化）
  美股（基准=SPX）：NAAIM、美债 10Y

每个指标输出：
  1) 数据质量：覆盖窗、点数、缺口（>10 交易日无数据段数）、重复日期、
     停滞值（最长连续同值）、合理域检查
  2) 相关性：指标 vs 基准——当期周收益 Pearson、水平对 3/12 月远期
     收益的 Spearman
  3) 极值区（自身分布 90/10 分位）：其后 3/6/12 月远期收益 vs 基线，
     标注 顺势/反向/不显著（|差|<2pp 视为不显著，事前指定）

数据准确性双源核查（事前指定）：
  - 全A宽度：研究史（新浪源回算） vs live 管线（腾讯源）重叠日偏差
  - 美债10Y：bond_zh_us_rate vs ^TNX 重叠日平均绝对误差
  - 两融：融资余额+融券余额 ≈ 融资融券余额（内部恒等式）

判定：无假设检验（面板为描述性）；每指标给方向标签供后续预登记实验
选用。输出 raw/sentiment/fundamental_panel.json
复现：python3 scripts/run_fundamental_panel.py（宏观数据首跑需联网）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from run_breadth_overlay import load_breadth  # noqa: E402

RAW = REPO / "docs/experiments/raw/sentiment"
CACHE = Path.home() / ".lei_signal_lab/cache"


def quality(idx: pd.Index, s: pd.Series, lo: float, hi: float,
            name: str) -> dict:
    dup = int(idx.duplicated().sum())
    gaps = int((pd.Series(idx).diff().dt.days > 15).sum())
    # 停滞值连跑计数
    run, best = 1, 1
    vals = s.values
    for i in range(1, len(vals)):
        run = run + 1 if vals[i] == vals[i - 1] else 1
        best = max(best, run)
    out_of_range = int(((s < lo) | (s > hi)).sum())
    return {"name": name, "n": len(s), "start": str(idx.min().date()),
            "end": str(idx.max().date()), "dup_dates": dup,
            "gap_segments": gaps, "max_stale_run": best,
            "out_of_range": out_of_range}


def analyze(s: pd.Series, bench: pd.Series, tag: str,
            horizons=(63, 252)) -> dict:
    s = s.dropna()
    common = bench.loc[s.index[0]:s.index[-1]]
    if len(common) < 300:
        return {"tag": tag, "note": "样本不足"}
    fwd = {h: common.shift(-h) / common - 1 for h in horizons}
    wk = common.resample("W-FRI").last().pct_change()
    sw = s.resample("W-FRI").last().diff()
    df = pd.concat([wk, sw], axis=1).dropna()
    df.columns = ["ret", "chg"]
    contemp = round(float(df["ret"].corr(df["chg"])), 3)
    out = {"tag": tag, "n_weeks": len(s),
           "contemporaneous_weekly_corr": contemp,
           "fwd": {}}
    hi, lo = s.quantile(0.9), s.quantile(0.1)
    for h, f in fwd.items():
        base = float(f.mean())
        hi_v = [f.get(d) for d in s.index[s >= hi] if d in f.index]
        lo_v = [f.get(d) for d in s.index[s <= lo] if d in f.index]
        hi_v = [v for v in hi_v if pd.notna(v)]
        lo_v = [v for v in lo_v if pd.notna(v)]
        hi_m = float(np.mean(hi_v)) if hi_v else None
        lo_m = float(np.mean(lo_v)) if lo_v else None
        corr = float(s.rank().corr(f.reindex(s.index).rank()))
        sig = ""
        if hi_m is not None and lo_m is not None:
            d_hi, d_lo = hi_m - base, lo_m - base
            if d_hi > 0.02 and d_lo < -0.02:
                sig = "顺势"
            elif d_hi < -0.02 and d_lo > 0.02:
                sig = "反向"
            else:
                sig = "不显著"
        out["fwd"][f"{h}d"] = {
            "baseline": round(base, 4),
            "hi(90%)": {"mean": round(hi_m, 4) if hi_m is not None else None,
                        "n": len(hi_v)},
            "lo(10%)": {"mean": round(lo_m, 4) if lo_m is not None else None,
                        "n": len(lo_v)},
            "spearman": round(corr, 3), "signal": sig}
    return out


def main() -> int:
    idx = pd.read_parquet(CACHE / "timing/000300.parquet")["close"]
    idx.index = pd.to_datetime(idx.index).tz_localize(None).normalize()
    spx = pd.read_parquet(REPO / "docs/experiments/raw/module_e/"
                          "us_gspc_ohlc.parquet")["close"]
    spx.index = pd.to_datetime(spx.index).tz_localize(None).normalize()

    br = load_breadth()
    csi = pd.DataFrame(json.loads(
        (CACHE / "csi300_ma_breadth_history.json").read_text()))
    csi["date"] = pd.to_datetime(csi["date"])
    csi = csi.set_index("date").sort_index()
    margin = pd.read_csv(RAW.parent / "sentiment/margin_signal.csv",
                         index_col=0, parse_dates=True)["margin_pct"] \
        if (RAW / "../sentiment/margin_signal.csv").exists() else None
    north = None
    nf = Path("/tmp/north_flow.csv")
    if nf.exists():
        d = pd.read_csv(nf)
        d["date"] = pd.to_datetime(d["日期"])
        ns = d.set_index("date")["历史累计净买额"].astype(float).sort_index()
        north = (ns.diff(20).rolling(756, min_periods=250)
                 .rank(pct=True)).rename("north")
    pos = pd.read_csv(RAW / "fund_stock_position_lg.csv",
                      parse_dates=["date"]).set_index("date")["position"] \
        .astype(float).sort_index()
    naaim = pd.Series(
        json.loads((RAW / "naaim_hist.json").read_text())["values"],
        index=pd.to_datetime(
            json.loads((RAW / "naaim_hist.json").read_text())["dates"])
    ).astype(float).sort_index()
    bond = pd.read_csv("/tmp/cn_bond_yield.csv", parse_dates=["日期"]) \
        .set_index("日期").sort_index()
    pmi = pd.read_csv("/tmp/cn_pmi.csv")
    pmi["date"] = pd.to_datetime(pmi["月份"].str.replace("年", "-")
                                 .str.replace("月份", ""), format="%Y-%m")
    pmi = pmi.set_index("date")["制造业-指数"].astype(float).sort_index()

    series = [
        (br["ma200_pct"].loc["2005":], idx, "全A B200", 0, 100),
        (br["ma50_pct"].loc["2005":], idx, "全A B50", 0, 100),
        (csi["ma200_pct"], idx, "CSI300 B200", 0, 100),
        (pos, idx, "基金仓位(乐咕)", 40, 100),
    ]
    if margin is not None:
        series.append((margin, idx, "两融20日变化分位", 0, 1))
    if north is not None:
        series.append((north, idx, "北向20日净流入分位(死源)", 0, 1))
    cn10 = bond["中国国债收益率10年"].dropna()
    series.append((cn10, idx, "中债10Y", 0, 8))
    series.append((cn10.diff(60), idx, "中债10Y 60日变化", -3, 3))
    series.append((pmi, idx, "制造业PMI", 30, 60))
    series.append((pmi.diff(3), idx, "PMI 3月变化", -5, 5))
    us10 = bond["美国国债收益率10年"].dropna()
    series.append((us10, spx, "美债10Y", 0, 10))
    series.append((naaim, spx, "NAAIM 敞口", -20, 200))

    results, quals = {}, {}
    for s, bench, tag, lo_b, hi_b in series:
        s = s[~s.index.duplicated()].dropna()
        results[tag] = analyze(s, bench, tag)
        quals[tag] = quality(s.index, s, lo_b, hi_b, tag)

    # ---- 双源交叉验证 ----
    live = pd.DataFrame(json.loads(
        (CACHE / "a_share_ma_breadth_history.json").read_text()))
    live["date"] = pd.to_datetime(live["date"])
    live = live.set_index("date").sort_index()
    ov = br.loc[live.index[0]:live.index[-1], "ma200_pct"]
    ov_live = live["ma200_pct"].reindex(ov.index)
    d1 = (ov - ov_live).abs().dropna()
    x1 = {"pair": "全A B200 研究(新浪源) vs live(腾讯源)",
          "overlap_days": len(d1),
          "mae_pp": round(float(d1.mean()), 2),
          "max_pp": round(float(d1.max()), 2)}
    tnx = pd.read_parquet("/tmp/us10y.parquet")["us10y"]
    tnx.index = pd.to_datetime(tnx.index).tz_localize(None).normalize()
    ov2 = pd.concat([us10, tnx], axis=1).dropna()
    ov2.columns = ["a", "b"]
    x2 = {"pair": "美债10Y bond_zh_us_rate vs ^TNX",
          "overlap_days": len(ov2),
          "mae_bp": round(float((ov2.a - ov2.b).abs().mean() * 100), 1)}
    m = pd.read_csv("/tmp/margin_sse.csv")
    msum = m["融资余额"].astype(float) + m["融券余量金额"].astype(float)
    derr = (msum - m["融资融券余额"].astype(float)).abs() \
        / m["融资融券余额"].astype(float)
    x3 = {"pair": "两融内部恒等式(融资+融券=两融)",
          "max_rel_err": round(float(derr.max()), 6)}

    out = {"date": "2026-08-28", "panel": results, "quality": quals,
           "cross_validation": [x1, x2, x3]}
    (RAW / "fundamental_panel.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print(json.dumps(out["cross_validation"], ensure_ascii=False, indent=1))
    for tag, r in results.items():
        if "fwd" not in r:
            continue
        f = r["fwd"].get("252d", {})
        print(f"{tag:20s} 当期corr {r['contemporaneous_weekly_corr']:+.2f}"
              f" | 12m: 高区 {f.get('hi(90%)',{}).get('mean')}"
              f" 低区 {f.get('lo(10%)',{}).get('mean')}"
              f" 基线 {f.get('baseline')} → {f.get('signal')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
