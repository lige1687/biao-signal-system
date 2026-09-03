#!/usr/bin/env python3
"""模块B（密集突破）机制依赖诊断 · 预注册（跑前写死，跑后不得调）。

【被诊断结论】（docs/experiments/module-b-robustness-2026-09-03.md，AI 任务）
  宽基7池模块B breakout×b3_dual×vc0, cb=40/cl=8%，深池干净数据：
  N=37, expR=+0.9441；前三笔占正贡献 69.4%，2025 单年占 57.0%。
  悬而未决：集中是"模块只在某种市场状态下工作"（机制依赖）还是纯运气。

【核心问题】37 笔入场时刻的市场状态标签，能否把"赚大钱的笔"与"亏小钱的笔"
  分开？定位是**假设生成**，不是假设检验：全程描述性，不做任何显著性断言，
  不回测任何过滤后的组合，不设计过滤参数。

【数据（只读，来源写明）】
  - 37 笔逐笔明细：docs/experiments/raw/module_b_robustness/moduleB_robustness.json
    （AI 归档，含 symbol/signal_date/r_net；不重跑回测）。
  - 标的行情：~/.lei_signal_lab/backtest_pool/{sym}.bars.parquet（深池，Y 已核实
    7 宽基无跳变污染，且就是产生这 37 笔的同一数据）。深池自 2016-08 起。
  - 市场宽度：~/.lei_signal_lab/cache/timing/breadth_cn_all.parquet 的 b20/b200
    （全体 A 股站上自身 20/200 日均线的比例%，股票全集口径≈2670只；跳变审计
    的 13 处污染在 timing 的 ETF 个股序列，不在该宽度文件）。

【状态变量（全部机械可算，全部以 signal_date 收盘为时点，无未来函数）】
  市场层：
    V1 b200_raw      信号日 cn_all 200日宽度读数（%）。
    V2 b200_pctl5y   该读数在过去 1260 个交易日（5年）内的百分位（含当日）。
    V3 b20_pctl5y    20日宽度读数的同期 5 年百分位。
  标的层（深池）：
    V4 rv60_pctl     60日已实现波动（日对数收益std×√252）在自身近 min(756,可得)
                     窗口内的百分位；序列<120个观测打 hist_short 标。
    V5 dd250         收盘 / 过去250日最高收盘 - 1（≤0）；可得历史<250根（≥120）
                     打 hist_short 标。
    V6 ret_sig       信号日当日涨幅%（close/prev_close-1）。
    V7 volratio20    信号日成交量 / 前20日均量（不含信号日）。
  描述性附表（不参与分隔判定）：rv120_ann、pos250（250日区间位置）、年份、标的。
  百分位口径：pct = (#(窗口值<当前) + 0.5×#(窗口值==当前)) / n × 100。

【桶边界（跑前写死）】
  b200_raw : <30 | 30-45 | 45-60 | 60-75 | ≥75
  b200_pctl5y / b20_pctl5y / rv60_pctl : Q1[0,20) | Q2[20,40) | Q3[40,60) | Q4[60,80) | Q5[80,100]
  dd250    : ≥-2% | -2~-5% | -5~-10% | ≤-10%
  ret_sig  : <0.5% | 0.5~1.5% | 1.5~3% | ≥3%
  volratio20: <1.0 | 1.0~1.5 | 1.5~2.5 | ≥2.5
  pos250   : ≥0.95 | 0.8~0.95 | <0.8

【分组定义（跑前写死）】
  大赢单 top5 = AI 归档 D1 top5（按 r_net 降序前五，已知名单）：
    512100.SS 2025-06-23 / 510050.SS 2017-06-08 / 510500.SS 2025-06-24 /
    159901.SZ 2020-06-24 / 510300.SS 2025-06-25。
  输单 = 全部 r_net ≤ 0 的笔（n=23）。
  2017冠军 = 510050.SS 2017-06-08；2020冠军 = 159901.SZ 2020-06-24（跨年一致性用）。

【分隔判定（跑前写死，机械）】
  对 V1..V7 每个变量，考察其"相邻桶并集"（region）。该变量计为【分隔】 iff
  存在 region R 同时满足：
    (a) top5 中 ≥4 笔落入 R；
    (b) 输单落入 R 的笔数 ≤ 11（≤50%×23）；
    (c) 跨年一致：2017冠军与2020冠军均落入 R。
  三选一判定线：
    存在清晰栖息地  iff 分隔变量数 ≥ 2（须写明状态与下一个可检验过滤假设，
                       仅登记，不启用）；
    无清晰栖息地    iff 分隔变量数 = 0（集中度按运气记账，登记监控建议）；
    样本不足以下结论 iff 分隔变量数 = 1（登记单条弱线索，不判定栖息地）。
  诚实声明（预注册解读约束，跑前写死）：top5 中三笔是 2025-06 连续三天、状态
  高度相关，有效独立信息量小于表面笔数；无论判定结果如何，报告必须带此限定。

【分析动作（全部描述性）】
  A1 每笔状态表（37行×全部变量原始值+桶标签）。
  A2 各变量分桶的 n / mean_r / median_r / sum_r。
  A3 top5 vs 输单：各变量桶内 top5笔数 vs 输单笔数并排。
  A4 累计 r_net 时间线（按 signal_date,symbol 排序）：top5 在序列中的位次、
     各年末累计值、边界是否前/后加载。
  A5 2025 专问：五个大赢单（含2017/2020冠军）状态标签并排对比；2025 全部
     8 笔状态表。

【红线】描述性诊断；不回测过滤组合；不设计过滤规则参数；无显著性断言；
  不改任何既有文件与缓存；输出只新增 docs/experiments/raw/module_b_regime/。
复现：PYTHONHASHSEED=0 / =42 各跑一次，规范化 JSON sha256 须一致。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
TRADES_JSON = REPO / "docs/experiments/raw/module_b_robustness/moduleB_robustness.json"
BREADTH = Path("/Users/yongbiaoli/.lei_signal_lab/cache/timing/breadth_cn_all.parquet")
POOL_ROOT = Path("/Users/yongbiaoli/.lei_signal_lab/backtest_pool")
RAW_OUT = REPO / "docs/experiments/raw/module_b_regime"
OUT = RAW_OUT / "moduleB_regime.json"

TOP5_KEYS = [(  "512100.SS", "2025-06-23"), ("510050.SS", "2017-06-08"),
             ("510500.SS", "2025-06-24"), ("159901.SZ", "2020-06-24"),
             ("510300.SS", "2025-06-25")]
WIN17 = ("510050.SS", "2017-06-08")
WIN20 = ("159901.SZ", "2020-06-24")

B_B200_RAW = [("<30", 0.0, 30.0), ("30-45", 30.0, 45.0), ("45-60", 45.0, 60.0),
              ("60-75", 60.0, 75.0), ("75+", 75.0, 101.0)]
B_Q = [("Q1[0,20)", 0.0, 20.0), ("Q2[20,40)", 20.0, 40.0), ("Q3[40,60)", 40.0, 60.0),
       ("Q4[60,80)", 60.0, 80.0), ("Q5[80,100]", 80.0, 100.0001)]
B_DD = [("<=-10%", -10.0, -0.10), ("-5~-10%", -0.10, -0.05),
        ("-2~-5%", -0.05, -0.02), (">=-2%", -0.02, 0.000001)]  # lo<=dd<hi
B_RET = [("<0.5%", -100.0, 0.5), ("0.5~1.5%", 0.5, 1.5), ("1.5~3%", 1.5, 3.0),
         (">=3%", 3.0, 100.0)]
B_VOL = [("<1.0", 0.0, 1.0), ("1.0~1.5", 1.0, 1.5), ("1.5~2.5", 1.5, 2.5),
         (">=2.5", 2.5, 1e9)]
B_POS = [(">=0.95", 0.95, 1.01), ("0.8~0.95", 0.80, 0.95), ("<0.8", -0.01, 0.80)]

VARS_BUCKETED = ["b200_raw", "b200_pctl5y", "b20_pctl5y", "rv60_pctl",
                 "dd250", "ret_sig", "volratio20"]
BUCKETS = {"b200_raw": B_B200_RAW, "b200_pctl5y": B_Q, "b20_pctl5y": B_Q,
           "rv60_pctl": B_Q, "dd250": B_DD, "ret_sig": B_RET, "volratio20": B_VOL,
           "pos250": B_POS}


def pct_rank(window: np.ndarray, cur: float) -> float:
    n = len(window)
    return (float((window < cur).sum()) + 0.5 * float((window == cur).sum())) / n * 100.0


def bucket_label(var: str, val: float) -> str:
    for lab, lo, hi in BUCKETS[var]:
        if lo <= val < hi:
            return lab
    raise ValueError(f"{var}={val} 未落入任何预注册桶")


def main() -> None:
    RAW_OUT.mkdir(parents=True, exist_ok=True)
    src = json.loads(TRADES_JSON.read_text())
    trades = src["trades_detail"]
    assert len(trades) == 37, "复现锚：N=37"
    assert abs(sum(t["r_net"] for t in trades) / 37 - 0.9441) < 5e-4, "复现锚：expR"

    brd = pd.read_parquet(BREADTH)[["b20", "b200"]]
    b200 = brd["b200"].dropna()
    b20 = brd["b20"].dropna()
    b200_idx = {d: i for i, d in enumerate(b200.index)}
    b20_idx = {d: i for i, d in enumerate(b20.index)}

    bars = {}
    for sym in sorted({t["symbol"] for t in trades}):
        df = pd.read_parquet(POOL_ROOT / f"{sym}.bars.parquet")
        df["lr"] = np.log(df["close"]).diff()
        df["rv60"] = df["lr"].rolling(60).std() * np.sqrt(252) * 100
        df["rv120"] = df["lr"].rolling(120).std() * np.sqrt(252) * 100
        df["max250"] = df["close"].rolling(250, min_periods=120).max()
        df["min250"] = df["close"].rolling(250, min_periods=120).min()
        bars[sym] = df

    rows = []
    for t in sorted(trades, key=lambda t: (t["signal_date"], t["symbol"])):
        sym, sd = t["symbol"], t["signal_date"]
        ts = pd.Timestamp(sd)
        df = bars[sym]
        assert ts in df.index, f"{sym} {sd} 不在深池日历"
        i = df.index.get_loc(ts)
        close = float(df["close"].iloc[i])
        n_hist = i + 1
        hist_short = n_hist < 250

        # 市场层
        b200_cur = float(b200.iloc[b200_idx[ts]])
        b20_cur = float(b20.iloc[b20_idx[ts]])
        w2 = b200.iloc[max(0, b200_idx[ts] - 1259): b200_idx[ts] + 1].to_numpy()
        w1 = b20.iloc[max(0, b20_idx[ts] - 1259): b20_idx[ts] + 1].to_numpy()
        # 标的层
        rv60 = float(df["rv60"].iloc[i])
        rv120 = float(df["rv120"].iloc[i])
        rv_series = df["rv60"].iloc[: i + 1].dropna().iloc[-756:].to_numpy()
        max250 = float(df["max250"].iloc[i])
        min250 = float(df["min250"].iloc[i])
        dd250 = close / max250 - 1.0
        pos250 = (close - min250) / (max250 - min250) if max250 > min250 else 1.0
        ret_sig = (close / float(df["close"].iloc[i - 1]) - 1.0) * 100
        volratio = float(df["volume"].iloc[i]) / float(df["volume"].iloc[i - 20: i].mean())

        row = {
            "symbol": sym, "signal_date": sd, "r_net": t["r_net"],
            "year": sd[:4],
            "b200_raw": round(b200_cur, 2),
            "b200_pctl5y": round(pct_rank(w2, b200_cur), 1),
            "b20_pctl5y": round(pct_rank(w1, b20_cur), 1),
            "rv60_ann": round(rv60, 1), "rv120_ann": round(rv120, 1),
            "rv60_pctl": round(pct_rank(rv_series, rv60), 1),
            "dd250": round(dd250, 4), "ret_sig": round(ret_sig, 2),
            "volratio20": round(volratio, 2), "pos250": round(pos250, 3),
            "hist_short_250": bool(hist_short or len(rv_series) < 120),
        }
        for v in VARS_BUCKETED + ["pos250"]:
            row[f"bk_{v}"] = bucket_label(v, row[v])
        rows.append(row)

    is_top5 = lambda r: (r["symbol"], r["signal_date"]) in set(TOP5_KEYS)
    is_win17 = lambda r: (r["symbol"], r["signal_date"]) == WIN17
    is_win20 = lambda r: (r["symbol"], r["signal_date"]) == WIN20
    losers = [r for r in rows if r["r_net"] <= 0]
    tops = [r for r in rows if is_top5(r)]
    assert len(tops) == 5 and len(losers) == 23

    # ---------- A2/A3 分桶 ----------
    bucket_tables, separation = {}, {}
    for v in VARS_BUCKETED:
        order = [lab for lab, _, _ in BUCKETS[v]]
        tbl = {}
        for lab in order:
            grp = [r for r in rows if r[f"bk_{v}"] == lab]
            rs = [r["r_net"] for r in grp]
            tbl[lab] = {"n": len(grp),
                        "n_top5": sum(is_top5(r) for r in grp),
                        "n_losers": sum(r["r_net"] <= 0 for r in grp),
                        "mean_r": round(float(np.mean(rs)), 4) if rs else None,
                        "median_r": round(float(np.median(rs)), 4) if rs else None,
                        "sum_r": round(float(np.sum(rs)), 4) if rs else None}
        bucket_tables[v] = tbl

        # 预注册分隔搜索：相邻桶并集
        best = None
        for a in range(len(order)):
            for b in range(a, len(order)):
                region = set(order[a: b + 1])
                if len(region) == len(order):
                    continue  # 全域不构成分隔
                inR = [r for r in rows if r[f"bk_{v}"] in region]
                n_top = sum(is_top5(r) for r in inR)
                n_los = sum(r["r_net"] <= 0 for r in inR)
                if n_top >= 4 and n_los <= 11 \
                        and any(is_win17(r) for r in inR) and any(is_win20(r) for r in inR):
                    cand = {"region": sorted(region), "n_top5": n_top,
                            "n_losers": n_los, "n_total": len(inR)}
                    if best is None or cand["n_los"] < best["n_losers"]:
                        best = cand
        separation[v] = best
    n_sep = sum(1 for v in separation.values() if v is not None)
    if n_sep >= 2:
        verdict = "存在清晰栖息地（登记过滤假设，不启用）"
    elif n_sep == 0:
        verdict = "无清晰栖息地（集中度按运气记账）"
    else:
        verdict = "样本不足以下结论（单条弱线索，登记不判定）"

    # ---------- A4 累计时间线 ----------
    cum, timeline = 0.0, []
    for k, r in enumerate(rows, 1):
        cum += r["r_net"]
        timeline.append({"seq": k, "signal_date": r["signal_date"],
                         "symbol": r["symbol"], "r_net": r["r_net"],
                         "cum_r": round(cum, 4),
                         "top5": is_top5(r)})
    year_end = {}
    for e in timeline:
        year_end[e["signal_date"][:4]] = e["cum_r"]
    top5_seq = [e["seq"] for e in timeline if e["top5"]]

    # ---------- A5 大赢单画像 + 2025 全笔 ----------
    big5 = [{k: r[k] for k in ("symbol", "signal_date", "r_net", "b200_raw",
                               "b200_pctl5y", "b20_pctl5y", "rv60_pctl", "dd250",
                               "ret_sig", "volratio20", "rv60_ann", "pos250",
                               "bk_b200_raw", "bk_b200_pctl5y", "bk_b20_pctl5y",
                               "bk_rv60_pctl", "bk_dd250", "bk_ret_sig",
                               "bk_volratio20")} for r in rows if is_top5(r)]
    y2025 = [{k: r[k] for k in ("symbol", "signal_date", "r_net", "bk_b200_raw",
                                "bk_b200_pctl5y", "bk_b20_pctl5y", "bk_rv60_pctl",
                                "bk_dd250", "bk_ret_sig", "bk_volratio20",
                                "hist_short_250")} for r in rows if r["year"] == "2025"]

    results = {
        "task": "模块B机制依赖诊断（预注册，描述性假设生成）",
        "anchor": {"N": len(rows), "expR": round(np.mean([r['r_net'] for r in rows]), 4),
                   "top5_match": sorted((r["symbol"], r["signal_date"]) for r in tops)},
        "state_table": rows,
        "bucket_tables": bucket_tables,
        "top5_vs_losers": {
            "n_losers": len(losers),
            "loss_mean_r": round(float(np.mean([r["r_net"] for r in losers])), 4),
            "separation_search": separation,
            "n_separating_vars": n_sep,
        },
        "timeline": {"ordered": timeline, "year_end_cum": year_end,
                     "top5_seq_positions": top5_seq},
        "big5_profile": big5,
        "year2025_all_trades": y2025,
        "verdict_pre_registered": verdict,
    }
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    canon = json.dumps(results, sort_keys=True, ensure_ascii=False)
    print(f"锚: N={results['anchor']['N']} expR={results['anchor']['expR']:+.4f} top5匹配={len(tops)}/5 输单={len(losers)}")
    for v in VARS_BUCKETED:
        bt = bucket_tables[v]
        line = " | ".join(f"{lab}:n={d['n']},top5={d['n_top5']},输={d['n_losers']},均值={d['mean_r']}"
                          for lab, d in bt.items() if d["n"])
        sep = separation[v]
        print(f"[{v}] {line}")
        if sep:
            print(f"    分隔region: {sep}")
    print(f"分隔变量数={n_sep} → 判定: {verdict}")
    print(f"top5 时间线位次(共{len(rows)}): {top5_seq}")
    print(f"HASH(规范化JSON): {hashlib.sha256(canon.encode()).hexdigest()}")


if __name__ == "__main__":
    main()
