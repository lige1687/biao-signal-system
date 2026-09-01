"""VIX 期限结构 / 股票 Put-Call 比率 · 情绪触发层候选信号事件研究（2026-09-01）。

任务 B（docs/experiments 任务拆分 2026-09-01）：更高频情绪代理做美股
**触发层**信号的事件信息量核验。不做仓位系数映射（仓位层已被环境组+
LEI 组三次判负）；不重复测 NAAIM/AAII 本身（定位=叙事标注，LEI-ARCHIVE 三节）。

判定标准（事前写死，跑之前落此 docstring，跑完不许改）：

  JV1 信息量主判（每信号 × ^GSPC）：
    信号后远期收益均值在 126 与 252 交易日两档**都** > 同区间全样本
    逐日基线均值，且具有完整 252 日数据的信号数 n >= 5。
    （21/63 日档只报告不判定；不足 n>=5 只报告不判定。）
  JV2 安慰剂检验（主判）：
    252 日档：信号日集合整体平移 300 次构造伪信号（每次平移量从
    {-750..-30} ∪ {30..750} 交易日均匀抽取，numpy default_rng(20260901)，
    与 PYTHONHASHSEED 无关），伪信号用与真信号完全相同的执行/收益口径，
    超出样本者丢弃；若某次平移后有效信号数 < 5 则重抽（至多 50 次，仍
    失败记 NaN 并在分位计算中忽略）。真信号均值必须 > 伪信号均值分布
    的 95 分位。安慰剂与真信号同为重叠窗口结构，可控制重叠窗偏差。
  JV3 阴性对照（黄金 518880，A 股日历）：
    同一信号日施于黄金（执行日=黄金日历上 >= t+1 的首个交易日，远期
    按黄金自身交易日计数）。若黄金上 126 与 252 档均值也都 > 黄金自身
    基线且 n >= 5，判"泛化噪音嫌疑"，该信号不得进通过清单。
  JV4 NAAIM 交叉验证（只报告不判定）：
    NAAIM 重叠窗（2023-11→2026-05）内，每信号日取 available <= 信号日
    且间隔 <= 7 天的最近 NAAIM 观测，计算其相对 NAAIM 自身扩张分位
    （min_periods=52）。一致性 = 信号日对应 NAAIM 分位 <= 50% 的占比
    （恐慌低仓位与恐惧触发同现才算同源印证）。
  综合分级：
    通过  = JV1 ∧ JV2 ∧ 无 JV3 嫌疑
    观察  = JV1 过但 JV2 未过（或 95 分位压线：均值 > 90 分位而 <= 95 分位）
    判负  = JV1 未过
  QQQ 次要资产：同 JV1 口径统计，只报告不判定（宽度宇宙≠标的，口径近似）。
  OOS 尾段（信号日 >= 2024-08-27）：单独报告，不判定。
  多重比较：本轮判定量 = 3 信号 × 1 资产主判，家族 N=3，如实登记。
  敏感性（预注册，只报告不再判定）：S1 尖峰资格线 1.05→{1.10, 关闭}；
    S2/S3 冷却 10→21 交易日；S3 触发分位 90→{85, 95}。

信号定义（事前冻结，全部收盘生成、t+1 收盘执行）：

  S1 期限倒挂解除（VIX9D/VIX）：
    r = VIX9D/VIX 日收盘比。信号日 t = 首个 r_t < 1.0 且 r_{t-1} >= 1.0
    （backwardation→contango 转换日），且资格条件 max(r_{t-9..t}) >= 1.05
    （近端恐惧真实尖峰，排除贴线噪声）。样本自 VIX9D 起点 2011-01-04。
  S2 长端深度倒挂（VIX/VIX3M）：
    q = VIX/VIX3M 日收盘比。分位 = q 相对**扩张窗口**（只用过去数据，
    min_periods=252）的百分位——继承第 19 轮铁律：禁全样本分位（防前视）。
    信号日 = 分位 <= 10。冷却 10 交易日（簇内只取首日）。
    样本自 VIX3M 起点 2009-09-18 + 252 日暖机。
  S3 股票 P/C 极端（equity put/call）：
    p = 股票 P/C 比率（CBOE 三段拼接，1995-09→2019-10）。分位 = p 的
    扩张窗口百分位（min_periods=252）。信号日 = 分位 >= 90（大量买认沽
    =人群对冲恐慌，反向买点候选）。冷却 10 交易日。
    样本止于 2019-10-04（数据源缺口，DATA_SOURCES.md 登记欠账）。

口径：
- 主资产 ^GSPC 收盘（raw/module_e 同源拷贝）；entry = close_{t+1}；
  远期收益 = close_{t+1+H}/close_{t+1} - 1，H ∈ {21, 63, 126, 252}。
- 基线 = 信号可用区间内全部交易日同一执行口径（该日为某假想信号的 t+1
  执行日）的均值——每信号与各自时代基线比较。
- 事件研究不建模交易成本（信息量核验，非可交易策略——与模块 E J2 同定位）。
- P/C 与 VIX 收盘值当日收盘后才可得 → t+1 执行是 PIT 保守处理。

复现：python3 docs/experiments/raw/vix-sentiment/run_vix_sentiment.py
双跑：PYTHONHASHSEED=0 与 =42，产物 sha256 写入 hash.json。
输出：docs/experiments/raw/vix-sentiment/{vix_sentiment_results.json,
events_S*.csv, hash.json}
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

HORIZONS = [21, 63, 126, 252]
COOLDOWN_TD = 10          # S2/S3 信号簇冷却（交易日）
MIN_PCT_PERIODS = 252     # 扩张分位最少历史
PCTILE_LOW = 10.0         # S2 触发分位
PCTILE_HIGH = 90.0        # S3 触发分位
SPIKE_QUAL = 1.05         # S1 尖峰资格线
SPIKE_WIN = 10            # S1 尖峰回看窗（交易日）
N_MIN = 5                 # 最少可判定信号数
PLACEBO_N = 300
PLACEBO_RNG_SEED = 20260901
OOS_CUT = pd.Timestamp("2024-08-27")
NAAIM_MAX_AGE_DAYS = 7
NAAIM_MIN_HIST = 52
GOLD_START_MIN = pd.Timestamp("2013-07-29")

R6 = lambda x: (round(float(x), 6) if x is not None and np.isfinite(x) else None)


# ---------------------------------------------------------------- 数据加载

def _read_cboe_index(fname: str) -> pd.Series:
    df = pd.read_csv(DATA / fname)  # 首行即列头 DATE,OPEN,HIGH,LOW,CLOSE
    df["DATE"] = pd.to_datetime(df["DATE"])
    s = df.set_index("DATE")["CLOSE"].astype(float).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s


def load_equity_pc() -> pd.Series:
    """股票 P/C 拼接：段2 equitypcarchive(2003-10-21→2006-11-01) | 段3 equitypc(2006-11-02→2019-10-04)。

    事实更正留痕（2026-09-01）：段1 pcratioarchive 的 EQUITY 列 2077 行仅
    50 个非空值（其 1995-2003 段只有 TOTAL/INDEX P/C），且这 50 天与段2
    重叠被覆盖——股票 P/C 实际起点 = 2003-10-21（16 年）。首版误记 1995 起。
    段1 现仅作覆盖校验，不进拼接。
    """
    pa = pd.read_csv(DATA / "pcratioarchive.csv", skiprows=2, encoding="latin-1")
    pa.columns = ["date", "total", "index", "equity", "disclaimer"]
    seg1_n_valid = int(pa["equity"].notna().sum())

    def _seg(fname: str) -> pd.Series:
        d = pd.read_csv(DATA / fname, skiprows=3, encoding="latin-1").iloc[:, :5]
        d.columns = ["date", "call", "put", "total", "pc"]
        return pd.Series(
            d["pc"].astype(float).values, index=pd.to_datetime(d["date"])
        ).sort_index()

    seg2_all = _seg("equitypcarchive.csv")
    seg3 = _seg("equitypc.csv")
    cut2 = seg3.index.min() - pd.Timedelta(days=1)      # 2006-11-01
    seg2 = seg2_all[seg2_all.index <= cut2]
    s = pd.concat([seg2, seg3])
    s = s[~s.index.duplicated(keep="last")].dropna()
    load_equity_pc.seg1_n_valid = seg1_n_valid
    return s


def _load_prices() -> dict[str, pd.DataFrame]:
    out = {}
    for name in ["gspc_ohlc", "qqq_ohlc"]:
        out[name] = pd.read_parquet(DATA / f"{name}.parquet").sort_index()
    gold = pd.read_parquet(DATA / "gold518880_close.parquet").sort_index()
    out["gold"] = gold[gold.index >= GOLD_START_MIN]
    return out


# ---------------------------------------------------------------- 信号构造

def expanding_pctile(s: pd.Series, min_periods: int = MIN_PCT_PERIODS) -> pd.Series:
    """扩张窗口百分位（0-100），只用过去数据。"""
    vals = s.to_numpy(dtype=float)
    n = len(vals)
    out = np.full(n, np.nan)
    for i in range(n):
        if i + 1 >= min_periods:
            hist = vals[: i + 1]  # 含当期（当日分位以当日收盘值对全部已见历史比较）
            out[i] = (hist <= vals[i]).sum() / len(hist) * 100.0
    return pd.Series(out, index=s.index)


def apply_cooldown(dates: list[pd.Timestamp], cooldown_td: int,
                   ref_index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    if not dates:
        return []
    pos = {d: ref_index.get_loc(d) for d in dates}
    kept: list[pd.Timestamp] = []
    last_pos = None
    for d in sorted(dates, key=lambda x: pos[x]):
        p = pos[d]
        if last_pos is None or p - last_pos > cooldown_td:
            kept.append(d)
            last_pos = p
    return kept


def build_signals(vix9d, vix, vix3m, epc) -> dict[str, dict]:
    sig = {}

    # S1: VIX9D/VIX backwardation → contango 转换日
    r = (vix9d / vix).dropna()
    r = r[r.index >= vix9d.index.min()]
    spike = r.rolling(SPIKE_WIN, min_periods=SPIKE_WIN).max()
    prev = r.shift(1)
    mask = (r < 1.0) & (prev >= 1.0) & (spike >= SPIKE_QUAL)
    dates = list(r.index[mask.fillna(False)])
    sig["S1_term_recontango"] = {
        "dates": dates,
        "sample_start": r.index.min(),
        "sample_end": r.index.max(),
        "def": "VIX9D/VIX: r_t<1.0 & r_{t-1}>=1.0 & max(r,10d)>=1.05",
    }

    # S2: VIX/VIX3M 扩张分位 <= 10
    q = (vix / vix3m).dropna()
    pct_q = expanding_pctile(q)
    mask = pct_q <= PCTILE_LOW
    raw_dates = list(q.index[mask.fillna(False)])
    dates = apply_cooldown(raw_dates, COOLDOWN_TD, q.index)
    sig["S2_vix_vix3m_extreme"] = {
        "dates": dates,
        "sample_start": q.index[MIN_PCT_PERIODS - 1],
        "sample_end": q.index.max(),
        "def": "VIX/VIX3M expanding pctile <= 10, cooldown 10td",
        "n_raw_cluster_days": len(raw_dates),
    }

    # S3: 股票 P/C 扩张分位 >= 90
    pct_p = expanding_pctile(epc)
    mask = pct_p >= PCTILE_HIGH
    raw_dates = list(epc.index[mask.fillna(False)])
    dates = apply_cooldown(raw_dates, COOLDOWN_TD, epc.index)
    sig["S3_equitypc_extreme"] = {
        "dates": dates,
        "sample_start": epc.index[MIN_PCT_PERIODS - 1],
        "sample_end": epc.index.max(),
        "def": "equity P/C expanding pctile >= 90, cooldown 10td",
        "n_raw_cluster_days": len(raw_dates),
    }
    return sig


# ---------------------------------------------------------------- 事件研究

def forward_returns(
    price: pd.Series, sig_dates: list[pd.Timestamp], horizons=HORIZONS
) -> pd.DataFrame:
    """entry=信号日 t+1 收盘；收益=close_{t+1+H}/close_{t+1}-1。"""
    idx = price.index
    rows = []
    for d in sig_dates:
        if d not in idx:
            continue
        p = idx.get_loc(d)
        e = p + 1
        if e >= len(idx):
            continue
        row = {"signal_date": d, "entry_date": idx[e], "entry": float(price.iloc[e])}
        for h in horizons:
            x = e + h
            row[f"fwd_{h}"] = (
                float(price.iloc[x] / price.iloc[e]) - 1.0 if x < len(idx) else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)


def baseline_returns(
    price: pd.Series, start: pd.Timestamp, end: pd.Timestamp, horizons=HORIZONS
) -> dict[int, float]:
    """区间内全部交易日作 entry 的同口径远期收益均值。"""
    sub = price[(price.index >= start) & (price.index <= end)]
    idx = price.index
    out = {}
    if len(sub) == 0:
        return {h: float("nan") for h in horizons}
    for h in horizons:
        vals = []
        for d in sub.index:
            e = idx.get_loc(d)
            if e + h < len(idx):
                vals.append(price.iloc[e + h] / price.iloc[e] - 1.0)
        out[h] = float(np.mean(vals)) if vals else float("nan")
    return out


def gold_forward(price: pd.Series, sig_dates: list[pd.Timestamp],
                  horizons=HORIZONS, max_gap_days: int = 5) -> pd.DataFrame:
    """黄金自身日历：执行日=黄金日历上 >= t+1 的首个交易日。

    修正留痕（2026-09-01）：首版未过滤黄金序列开始前的信号日，导致
    2013-07 前的信号错误地以黄金首日为执行日（JV3 数字失真，仅阴性
    对照字段受影响，JV1/JV2 主判不受影响）。现要求执行日距目标 <= 5
    自然日，否则跳过该信号日。
    """
    idx = price.index
    rows = []
    for d in sig_dates:
        target = d + pd.Timedelta(days=1)
        loc = idx.searchsorted(target)
        e = loc
        if e >= len(idx):
            continue
        if (idx[e] - target).days > max_gap_days:
            continue
        row = {"signal_date": d, "entry_date": idx[e]}
        for h in horizons:
            row[f"fwd_{h}"] = (
                float(price.iloc[e + h] / price.iloc[e]) - 1.0
                if e + h < len(idx) else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)


def placebo_test(
    price: pd.Series,
    sig_dates: list[pd.Timestamp],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict:
    """300 次整体平移安慰剂（252 日档）。rng 与 PYTHONHASHSEED 无关。"""
    rng = np.random.default_rng(PLACEBO_RNG_SEED)
    idx = price.index
    dates_in = [d for d in sig_dates if d in idx]
    pos = np.array([idx.get_loc(d) for d in dates_in], dtype=int)
    n_valid = len(pos)
    means = []
    n_redraw_total = 0
    for _ in range(PLACEBO_N):
        ok = False
        for _try in range(51):
            off = int(rng.integers(30, 751))
            if rng.random() < 0.5:
                off = -off
            pp = pos + off
            pp = pp[(pp >= 0) & (pp + 1 + 252 < len(idx))]
            if len(pp) >= N_MIN:
                rvals = [
                    price.iloc[p + 1 + 252] / price.iloc[p + 1] - 1.0 for p in pp
                ]
                means.append(float(np.mean(rvals)))
                n_redraw_total += _try
                ok = True
                break
        if not ok:
            means.append(float("nan"))
            n_redraw_total += 50
    arr = np.array(means, dtype=float)
    finite = arr[np.isfinite(arr)]
    return {
        "n_placebo": int(len(finite)),
        "p95": R6(np.percentile(finite, 95)) if len(finite) else None,
        "p90": R6(np.percentile(finite, 90)) if len(finite) else None,
        "mean": R6(np.mean(finite)) if len(finite) else None,
        "redraws_total": int(n_redraw_total),
    }


# ---------------------------------------------------------------- NAAIM 交叉

def naaim_crosscheck(sig_dates: list[pd.Timestamp]) -> dict:
    raw = json.loads((DATA / "naaim_hist.json").read_text())
    obs = pd.Series(
        [float(v) for v in raw["values"]],
        index=pd.to_datetime(raw["dates"]),
    ).sort_index()
    pct = expanding_pctile(obs, min_periods=NAAIM_MIN_HIST)
    matched, lows = 0, 0
    details = []
    for d in sig_dates:
        hist = obs[obs.index <= d]
        if not len(hist):
            continue
        last_date = hist.index[-1]
        age = (d - last_date).days
        if age > NAAIM_MAX_AGE_DAYS:
            continue
        p = pct.loc[last_date]
        if not np.isfinite(p):
            continue
        matched += 1
        if p <= 50.0:
            lows += 1
        details.append({
            "signal_date": str(d.date()),
            "naaim_date": str(last_date.date()),
            "naaim_pct": R6(p),
        })
    return {
        "naaim_window": [str(obs.index.min().date()), str(obs.index.max().date())],
        "n_signal_matched": matched,
        "n_naaim_pct_le_50": lows,
        "concordance": R6(lows / matched) if matched else None,
        "details": details,
    }


# ---------------------------------------------------------------- 主流程

def main() -> None:
    vix9d = _read_cboe_index("VIX9D_History.csv")
    vix = _read_cboe_index("VIX_History.csv")
    vix3m = _read_cboe_index("VIX3M_History.csv")
    epc = load_equity_pc()
    prices = _load_prices()
    gspc_close = prices["gspc_ohlc"]["close"]
    qqq_close = prices["qqq_ohlc"]["close"]
    gold_close = prices["gold"]["close"]

    # 数据验证（拼接缝复检，写入结果）
    def _seg23_overlap():
        d3 = pd.read_csv(DATA / "equitypc.csv", skiprows=3, encoding="latin-1").iloc[:, :5]
        d3.columns = ["date", "c", "p", "t", "pc"]
        d2 = pd.read_csv(DATA / "equitypcarchive.csv", skiprows=3, encoding="latin-1").iloc[:, :5]
        d2.columns = ["date", "c", "p", "t", "pc"]
        s3 = pd.Series(d3["pc"].astype(float).values, index=pd.to_datetime(d3["date"]))
        s2 = pd.Series(d2["pc"].astype(float).values, index=pd.to_datetime(d2["date"]))
        j = pd.concat([s2, s3], axis=1, join="inner").dropna()
        diff = (j.iloc[:, 0] - j.iloc[:, 1]).abs()
        return {"overlap_days": int(len(j)), "MAE": R6(diff.mean()),
                "corr": R6(j.iloc[:, 0].corr(j.iloc[:, 1]))}

    validation = {
        "vix9d_range": [str(vix9d.index.min().date()), str(vix9d.index.max().date())],
        "vix3m_range": [str(vix3m.index.min().date()), str(vix3m.index.max().date())],
        "epc_range": [str(epc.index.min().date()), str(epc.index.max().date())],
        "epc_seg1_pcratioarchive_equity_n_valid": getattr(load_equity_pc, "seg1_n_valid", None),
        "epc_splice_seg2_seg3": _seg23_overlap(),
        "gspc_range": [str(gspc_close.index.min().date()), str(gspc_close.index.max().date())],
        "gold_range": [str(gold_close.index.min().date()), str(gold_close.index.max().date())],
    }

    sig = build_signals(vix9d, vix, vix3m, epc)

    results = {
        "experiment": "vix-sentiment trigger-layer event study",
        "date": "2026-09-01",
        "criteria": "JV1-JV4 frozen in run_vix_sentiment.py docstring (pre-registered)",
        "validation": validation,
        "signals": {},
    }

    for sid, meta in sig.items():
        dates = meta["dates"]
        start, end = meta["sample_start"], meta["sample_end"]

        ev = forward_returns(gspc_close, dates)
        ev_qqq = forward_returns(qqq_close, dates)
        base = baseline_returns(gspc_close, start, end)
        base_qqq = baseline_returns(qqq_close, start, end)

        ev.to_csv(HERE / f"events_{sid}.csv", index=False)

        n252 = int(ev["fwd_252"].notna().sum())
        entry = {
            "definition": meta["def"],
            "sample": [str(start.date()), str(end.date())],
            "n_signals": len(dates),
            "n_with_252": n252,
            "first_last": [
                str(dates[0].date()) if dates else None,
                str(dates[-1].date()) if dates else None,
            ],
            "gspc": {
                "signal_mean": {h: R6(ev[f"fwd_{h}"].mean()) for h in HORIZONS},
                "baseline_mean": {h: R6(base[h]) for h in HORIZONS},
                "signal_median_252": R6(ev["fwd_252"].median()),
                "win_rate_252": R6((ev["fwd_252"] > 0).mean()),
            },
            "qqq_report_only": {
                "signal_mean": {h: R6(ev_qqq[f"fwd_{h}"].mean()) if len(ev_qqq) else None
                                 for h in HORIZONS},
                "baseline_mean": {h: R6(base_qqq[h]) for h in HORIZONS},
                "n": int(len(ev_qqq)),
            },
        }

        # JV1
        if len(ev) == 0:
            jv1 = False
            entry["JV1_info"] = {"pass": False, "edge_126": None, "edge_252": None}
        else:
            m126, m252 = ev["fwd_126"].mean(), ev["fwd_252"].mean()
            jv1 = bool(
                n252 >= N_MIN
                and m126 > base[126]
                and m252 > base[252]
            )
            entry["JV1_info"] = {
                "pass": jv1,
                "edge_126": R6(m126 - base[126]),
                "edge_252": R6(m252 - base[252]),
            }

        # JV2
        if n252 >= N_MIN:
            pl = placebo_test(gspc_close, dates, start, end)
            jv2 = bool(m252 > pl["p95"])
            jv2_borderline = bool(pl["p90"] is not None and m252 > pl["p90"] and not jv2)
            entry["JV2_placebo_252"] = {**pl, "pass": jv2, "borderline": jv2_borderline}
        else:
            entry["JV2_placebo_252"] = {"pass": False, "skipped": "n<N_MIN"}

        # JV3 阴性对照（黄金）
        ev_g = gold_forward(gold_close, dates)
        base_g = baseline_returns(gold_close, max(start, GOLD_START_MIN), end)
        ng = int(ev_g["fwd_252"].notna().sum()) if len(ev_g) else 0
        g126 = ev_g["fwd_126"].mean() if len(ev_g) else float("nan")
        g252 = ev_g["fwd_252"].mean() if len(ev_g) else float("nan")
        suspicion = bool(ng >= N_MIN and g126 > base_g[126] and g252 > base_g[252])
        entry["JV3_gold_control"] = {
            "n": ng,
            "signal_mean": {h: R6(ev_g[f"fwd_{h}"].mean()) if len(ev_g) else None
                             for h in HORIZONS},
            "baseline_mean": {h: R6(base_g[h]) for h in HORIZONS},
            "generalized_noise_suspicion": suspicion,
        }

        # JV4 NAAIM
        entry["JV4_naaim_report_only"] = naaim_crosscheck(dates)

        # OOS 尾段
        oos_dates = [d for d in dates if d >= OOS_CUT]
        ev_oos = forward_returns(gspc_close, oos_dates)
        entry["oos_tail_report_only"] = {
            "n": len(oos_dates),
            "signal_mean": {h: R6(ev_oos[f"fwd_{h}"].mean()) if len(ev_oos) else None
                             for h in HORIZONS},
        }

        # 综合分级
        if not jv1:
            verdict = "FALSIFIED"
        elif entry["JV2_placebo_252"].get("pass"):
            verdict = "PASS" if not suspicion else "FAIL_NOISE_SUSPECT"
        elif entry["JV2_placebo_252"].get("borderline"):
            verdict = "WATCH"
        else:
            verdict = "FALSIFIED_PLACEBO"
        entry["verdict"] = verdict

        results["signals"][sid] = entry

    # 敏感性（预注册，只报告）
    sens = {}

    # S1 变体：资格线 1.10 / 关闭资格线
    r = (vix9d / vix).dropna()
    prev = r.shift(1)
    for tag, qual in [("spike110", 1.10), ("noqual", None)]:
        spike = r.rolling(SPIKE_WIN, min_periods=SPIKE_WIN).max()
        mask = (r < 1.0) & (prev >= 1.0)
        if qual is not None:
            mask = mask & (spike >= qual)
        ds = list(r.index[mask.fillna(False)])
        ev = forward_returns(gspc_close, ds)
        base = baseline_returns(gspc_close, r.index.min(), r.index.max())
        sens[f"S1_{tag}"] = {
            "n": len(ds),
            "mean_252": R6(ev["fwd_252"].mean()) if len(ev) else None,
            "base_252": R6(base[252]),
        }

    # S2/S3 冷却 21
    q = (vix / vix3m).dropna()
    pct_q = expanding_pctile(q)
    ds = apply_cooldown(list(q.index[(pct_q <= PCTILE_LOW).fillna(False)]), 21, q.index)
    ev = forward_returns(gspc_close, ds)
    base = baseline_returns(gspc_close, q.index[MIN_PCT_PERIODS - 1], q.index.max())
    sens["S2_cooldown21"] = {"n": len(ds), "mean_252": R6(ev["fwd_252"].mean()) if len(ev) else None,
                              "base_252": R6(base[252])}

    pct_p = expanding_pctile(epc)
    for thr in (85.0, 95.0):
        ds = apply_cooldown(list(epc.index[(pct_p >= thr).fillna(False)]), COOLDOWN_TD, epc.index)
        ev = forward_returns(gspc_close, ds)
        base = baseline_returns(gspc_close, epc.index[MIN_PCT_PERIODS - 1], epc.index.max())
        sens[f"S3_thr{int(thr)}"] = {"n": len(ds), "mean_252": R6(ev["fwd_252"].mean()) if len(ev) else None,
                                      "base_252": R6(base[252])}
    results["sensitivity_report_only"] = sens

    out_path = HERE / "vix_sentiment_results.json"
    out_path.write_text(
        json.dumps(results, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )
    print(f"written: {out_path}")
    for sid, e in results["signals"].items():
        print(f"{sid}: n={e['n_signals']} verdict={e['verdict']}")


if __name__ == "__main__":
    main()
