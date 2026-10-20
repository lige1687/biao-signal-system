#!/usr/bin/env python3
"""Prompt P · 标普500 替代纳指——同框架换标的对比（预注册 2026-09-03，跑前写死，跑后不改）。

任务来源：docs/experiments/prompt-PQ-broad-index-2026-09-02.md · Prompt P。
两个子任务，只换标的不改机制：

P1（两只版换腿）：复现认证"两只版"（创业板×B200 三档 43.3/56.7 择时 + 融资虹吸
豁免 + 美股腿满仓持有，2010-06-01→2026-08-18，费用 10bp 双边 + 5% 调仓带），
创业板择时部分逐字不动，仅把美腿 ^IXIC（纳指）换成 ^GSPC（标普500）。
P2（防守版对齐对比）：确认归档 us_defense.json 中 SPY 档与纳指档是否同窗对齐，
重算回撤削减/年化代价直接对比表；归档标签"5档"与生成代码 n_bands=3 不符，
补跑生产终版预设（纳指 5 档 20/80 底仓 0.3）作为补充口径。

═══════ 预注册判定标准（冻结，跑后不得调整）═══════

P1 判定标准（冻结）：
- 性质：描述性对比实验，非假设检验，非选优。产出完整对比表：
  两版本组合的 年化 / 最大回撤 / Calmar（年化÷|最大回撤|）/ 两版本日收益相关系数，
  外加两条美腿各自同期满仓持有的 年化 / 回撤 / 日收益相关（机制归因用）。
  如实报告差异方向（谁高谁低）与幅度（pp），不设"显著/不显著"判定线，
  不产生"应选标普还是纳指"的结论。
- G1 基线复现门（不过即 ABORT）：纳指版必须复现认证值
  （web/public/reports/duo-trades-2026-09-01.html）：
  年化 round(...,1)==15.9% ，最大回撤 round(...,1)==-25.6% ，调仓笔数==139。
- G2 换标的不变量门（不过即 ABORT）：两版本创业板腿逐日目标仓位序列必须
  逐元素相等（择时逐字未动的机器验证）；两版本调仓笔数必须相等。
- 机制归因规则（冻结）：两版本唯一自由度=美腿。若组合 Δ年化 方向与
  美腿持有 Δ年化 方向一致 → 记"美腿收益差主导"；并检查 Δ回撤 是否同样
  由美腿持有回撤差解释；若方向不一致，记"存在等权再平衡交互效应"，
  用年度收益表定位分歧年份。行业权重结构差异只能作为解释性叙述引用，
  不得当作被本实验直接检验的假设（本实验不拆行业权重）。

P2 判定标准（冻结）：
- G3 逐位复现门（不过即 ABORT）：用当前缓存（~/.lei_signal_lab/cache/timing/
  breadth_sp500.parquet + 引擎 src/lei_signal/timing_backtest/）重算归档
  us_defense.json 两档（^GSPC 40/80·3档·vol0.15·MA200闸；^IXIC 20/80·3档·
  同闸同vol），strategy_cagr/strategy_mdd/benchmark_cagr/benchmark_mdd 四项
  与归档 JSON 之差 |Δ|<1e-12。
- 对齐性判定：归档两档日度序列日期数组逐日相同 → 判"原报告已对齐"，
  直接引用认证序列重算衍生指标（本脚本此前已人工核对相同，正式判定以
  脚本输出 dates_identical 为准）；不同 → 补跑较短共同窗（本脚本实现了
  对齐逻辑，若已对齐则该分支自然跳过）。
- 对比表输出（每档）：策略年化/回撤/Calmar、持有年化/回撤、
  回撤削减（pp 与 %）、年化代价（pp）、保险性价比（回撤削减pp÷年化代价pp）、
  十年段分段（1986-89/1990s/2000s/2010s/2020-26）策略与持有年化回撤、
  两防守策略日收益相关系数。
- 机制归因规则（冻结）：若两档差异 |Δ策略年化|≥1pp 或 |Δ策略回撤|≥3pp，
  必须区分 (a) 指数本身差异（两持有腿同期年化/回撤差——纳指科技集中 vs
  标普行业分散的解释只能以持有腿差为中介引用）与 (b) 数据工程差异
  （窗口覆盖、复权口径、宽度宇宙差异），(b) 类如实声明"数据工程欠账"。
- 补充臂（口径歧义解决，非认证对替代）：生产终版预设 nq_b200_defense_final
  （IXIC 5档 20/80 γ1.5 vol0.15 底仓0.3 MA200闸）与 us_b200_defense_final
  （GSPC 3档 30/70 γ1.5 vol0.10 MA200闸）在共同窗重跑，费用 10bp、
  min_trade 0.05 与认证对一致；标签"5档"歧义在报告中如实披露。

数据源选择（P1 美腿用 ^GSPC 而非 SPY，理由冻结）：
- 认证基线的纳指腿 = raw/portfolio_split/ixic_close.parquet（^IXIC 价格指数，
  不含股息）。^GSPC 同为价格指数、同不含股息、同 Yahoo 族口径
  （raw/module_e/us_gspc_ohlc.parquet，yfinance auto_adjust 对指数为无操作），
  换腿后唯一变化是"指数本身"，不混入"股息是否计入"的口径变化。
- SPY 为含股息复权的 ETF 总收益口径，若用它会把"换指数"与"计股息"两个
  效应混在一起；脚本末尾附一组 ^GSPC vs SPY 同窗年化差（描述性，无判定门），
  量化该口径差量级供报告引用。
- 防守版（P2）原报告即用 ^GSPC，与本选择一致。

诚实条款：
- 创业板择时 / 虹吸 / 费用 / 执行时滞 / 5% 带全部逐字复用认证实现
  （tier_for←run_m5_walkforward、siphon_daily←run_ashare_axes、
  simulate_direct←run_bform_dynamic，三者原文件已移入 scripts/legacy_recovery/
  且其 REPO 路径失效无法 import，故逐字复制函数体并保留出处注释，
  原文见 scripts/legacy_recovery/）。
- 本脚本不修改任何现有文件；输出只写 docs/experiments/raw/spx_vs_ndx/。
- 双跑哈希：PYTHONHASHSEED=0 / 42 各一次，canonical JSON 的 sha256 必须一致。

复现：PYTHONHASHSEED=0 python3 scripts/run_spx_vs_ndx.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "docs/experiments/raw"
OUT = RAW / "spx_vs_ndx"
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "src"))

import run_portfolio_split as rps  # noqa: E402  (scripts/run_portfolio_split.py，认证在用)
from lei_signal.timing_backtest.service import compute_run  # noqa: E402

START = "2010-06-01"          # 两只版认证窗口起点（render_duo_page.START 逐字）
# 窗口终点 = rps.WIN_END = 2026-08-18（render_duo_page 用 rps.WIN_END，逐字）

# ═══════════════ 逐字复制的认证函数（出处：scripts/legacy_recovery/）═══════════════


def tier_for(b200, dates, low, high):
    """出处：legacy_recovery/run_m5_walkforward.py（原 scripts/run_m5_walkforward.py）。

    周频 B200（周内最后观测）→ 三档 <low→1.0 / <high→0.5 / else 0.0，
    信号日次一交易日生效，ffill，前置补 0。逐字未改（rps.weekly_last 即
    run_portfolio_split 从 run_siphon_detector 导入的同一函数对象）。
    """
    bw, bsig = rps.weekly_last(b200)
    w = bw.map(lambda v: 1.0 if v < low else (0.5 if v < high else 0.0))
    out = pd.Series(np.nan, index=dates)
    pos = dates.searchsorted(list(bsig.values))
    for p, wt in zip(pos, w.values):
        if p + 1 < len(dates):
            out.iloc[p + 1] = wt
    return out.ffill().fillna(0.0)


def siphon_daily(dates) -> pd.Series:
    """出处：legacy_recovery/run_ashare_axes.py（原 scripts/run_ashare_axes.py）。

    沪市融资余额 20 日增速 3 年滚动分位 ≥90% 且连续 20 日 → 虹吸 ON。
    逐字未改（仅 AX 路径按本文件位置重新解析到同一份 margin_sh.csv）。
    """
    ax = RAW / "ashare_axes"
    df = pd.read_csv(ax / "margin_sh.csv")
    df["date"] = pd.to_datetime(df["日期"])
    df = df.sort_values("date").set_index("date")
    bal = pd.to_numeric(df["融资余额"], errors="coerce").dropna()
    g20 = bal.pct_change(20)
    rank = g20.rolling(750, min_periods=500).rank(pct=True)  # 3年自分位
    on = (rank >= 0.90).rolling(20, min_periods=20).min() == 1  # 连续20日
    on = on.reindex(pd.DatetimeIndex(dates)).ffill().fillna(False)
    return on


def simulate_direct(prices: pd.DataFrame, target: pd.DataFrame) -> pd.Series:
    """出处：legacy_recovery/run_bform_dynamic.py（原 scripts/run_bform_dynamic.py）。

    target 为完整目标权重矩阵（列=prices 列），5% 带 + 10bp。逐字未改。
    """
    rets = prices.pct_change().fillna(0.0)
    names = list(prices.columns)
    actual = np.zeros(len(names))
    eq = []
    port = 1.0
    tgt_vals = target[names].values
    for i in range(len(prices)):
        if i > 0:
            port *= 1.0 + float(actual @ rets.iloc[i].values)
        t = tgt_vals[i]
        trade = np.abs(t - actual) >= 0.05
        new = np.where(trade, t, actual)
        port *= 1.0 - 0.001 * float(np.abs(new - actual).sum())
        actual = new
        eq.append(port)
    return pd.Series(eq, index=prices.index)


# ═══════════════ P1：两只版换腿（创业板×三档+虹吸 + 美腿满仓持有）═══════════════


def duo_arm(us_name: str, us_close: pd.Series):
    """两只版一只臂：与 render_duo_page.py 逐字同构，仅美腿序列可替换。"""
    b200 = rps.load_breadth()
    cyb = pd.read_parquet(RAW / "siphon_detector/cyb_399006_close.parquet")["close"].astype(float)
    cyb.index = pd.to_datetime(cyb.index)
    us = us_close.astype(float)
    us.index = pd.to_datetime(us.index)
    cn = cyb.index
    px = pd.DataFrame({"创业板指": cyb, us_name: us.reindex(cn).ffill()})
    px = px[(px.index >= pd.Timestamp(START)) & (px.index <= pd.Timestamp(rps.WIN_END))].dropna()
    dates = px.index

    t0 = tier_for(b200, dates, 43.3, 56.7)
    sip = siphon_daily(dates)
    bud = t0.copy()
    bud[(t0 <= 0.001) & sip] = 0.5  # 虹吸：空仓档→半仓

    expo = pd.DataFrame({"创业板指": bud, us_name: 1.0}) / 2
    eq = simulate_direct(px, expo)

    ch = bud.diff().fillna(0)
    n_events = int((ch != 0).sum())
    return {"px": px, "bud": bud, "expo": expo, "eq": eq, "events": n_events,
            "dates": dates, "b200_last": float(b200.iloc[-1])}


def m_ann_dd(e: pd.Series):
    """render_duo_page.metrics 同式：365.25 日年化 + 峰谷最大回撤。"""
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    ann = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1
    dd = float((e / e.cummax() - 1).min())
    return float(ann), dd


def yearly_returns(e: pd.Series) -> dict:
    y = e.groupby(e.index.year).last()
    y0 = e.groupby(e.index.year).first()
    # 年内首日也算收益（对齐自然年），首年以前一年末为基期不适用——用组内首日
    prev = e.groupby(e.index.year).last().shift(1)
    out = {}
    for yr in y.index:
        base = prev.loc[yr] if yr - 1 in prev.index and not np.isnan(prev.loc[yr]) else y0.loc[yr]
        out[int(yr)] = float(y.loc[yr] / base - 1)
    return out


def run_p1() -> dict:
    ixic = pd.read_parquet(RAW / "portfolio_split/ixic_close.parquet")["close"]
    gspc = pd.read_parquet(RAW / "module_e/us_gspc_ohlc.parquet")["close"]

    armA = duo_arm("纳斯达克", ixic)   # 基线复现臂（认证=纳指）
    armB = duo_arm("标普500", gspc)    # 换腿臂

    annA, ddA = m_ann_dd(armA["eq"])
    annB, ddB = m_ann_dd(armB["eq"])
    calA = annA / abs(ddA)
    calB = annB / abs(ddB)

    # G1 基线复现门
    g1 = {
        "ann_round1": round(annA * 100, 1), "dd_round1": round(ddA * 100, 1),
        "events": armA["events"],
        "pass": bool(round(annA * 100, 1) == 15.9 and round(ddA * 100, 1) == -25.6
                     and armA["events"] == 139),
    }
    # G2 换标的不变量门
    a_leg_equal = bool(np.array_equal(armA["expo"]["创业板指"].to_numpy(),
                                      armB["expo"]["创业板指"].to_numpy()))
    dates_equal = armA["dates"].equals(armB["dates"])
    g2 = {"a_leg_weights_identical": a_leg_equal, "dates_identical": dates_equal,
          "events_equal": bool(armA["events"] == armB["events"]),
          "pass": bool(a_leg_equal and dates_equal and armA["events"] == armB["events"])}
    if not (g1["pass"] and g2["pass"]):
        print("ABORT: P1 门未过", json.dumps({"G1": g1, "G2": g2}, ensure_ascii=False))
        sys.exit(2)

    # 美腿自身同期满仓持有（同一 cn 日历、同窗口）
    leg_stats = {}
    for name, arm in (("纳斯达克^IXIC", armA), ("标普500^GSPC", armB)):
        leg = arm["px"][{"纳斯达克^IXIC": "纳斯达克", "标普500^GSPC": "标普500"}[name]]
        la, ld = m_ann_dd(leg)
        leg_stats[name] = {"ann_pct": la * 100, "mdd_pct": ld * 100}
    rets = armA["px"]["纳斯达克"].pct_change()
    rets2 = armB["px"]["标普500"].pct_change()
    leg_corr = float(rets.corr(rets2))

    # 组合层相关性（日收益）
    port_corr = float(armA["eq"].pct_change().corr(armB["eq"].pct_change()))

    return {
        "window": {"start": str(armA["dates"][0].date()), "end": str(armA["dates"][-1].date()),
                   "years": round((armA["dates"][-1] - armA["dates"][0]).days / 365.25, 2)},
        "G1_baseline_reproduction": g1,
        "G2_invariance": g2,
        "portfolio": {
            "ndx_version": {"ann_pct": annA * 100, "mdd_pct": ddA * 100, "calmar": calA,
                            "events": armA["events"]},
            "spx_version": {"ann_pct": annB * 100, "mdd_pct": ddB * 100, "calmar": calB,
                            "events": armB["events"]},
            "diff_spx_minus_ndx": {"ann_pp": (annB - annA) * 100,
                                   "mdd_pp": (ddB - ddA) * 100,
                                   "calmar": calB - calA},
            "daily_return_corr": port_corr,
        },
        "us_leg_hold_same_window": {**leg_stats,
                                    "leg_daily_return_corr": leg_corr},
        "yearly_pct": {"ndx_version": yearly_returns(armA["eq"]),
                       "spx_version": yearly_returns(armB["eq"])},
        "attribution_note": "两版本创业板腿逐日权重逐元素相等（G2），全部组合差异只能来自美腿。",
        "_armA_eq": armA["eq"], "_armB_eq": armB["eq"],
    }


# ═══════════════ P2：防守版同窗对齐对比 ═══════════════

DEFENSE_CFG = {  # render_kuandu_archive.py jrun 调用逐字（相对 jrun 基座补 symbol/breadth）
    "strategy": "ladder", "indicator": "b200", "n_bands": 3, "edge_mode": "fixed",
    "direction": "momentum", "high_edge": 80.0, "gamma": 1.5, "vol_target": 0.15,
    "gate_mode": "ma200", "min_trade": 0.05, "fee_bps": 10.0, "breadth": "sp500",
}


def seg_ann_dd(eq: pd.Series, lo: str, hi: str):
    s = eq.loc[lo:hi]
    if len(s) < 30:
        return None
    s = s / s.iloc[0]
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    return {"ann_pct": float((s.iloc[-1]) ** (1 / yrs) - 1) * 100,
            "mdd_pct": float((s / s.cummax() - 1).min()) * 100}


def defense_compare(sym: str, low_edge: float, label: str) -> dict:
    rr = compute_run({**DEFENSE_CFG, "symbol": sym, "low_edge": low_edge})
    dates = pd.to_datetime(rr["daily"]["date"])
    eq = pd.Series(rr["daily"]["equity"], index=dates)
    bm = pd.Series(rr["daily"]["benchmark"], index=dates)
    return {"label": label, "metrics": {k: rr["metrics"][k] for k in
                                        ("strategy_cagr", "strategy_mdd",
                                         "benchmark_cagr", "benchmark_mdd")},
            "dates": dates, "eq": eq, "bm": bm}


def run_p2() -> dict:
    archived = json.loads((RAW / "kuandu-quanzhan/us_defense.json").read_text())

    gspc = defense_compare("^GSPC", 40.0, "SPY档 40/80·3档·vol0.15·MA200闸")
    ixic = defense_compare("^IXIC", 20.0, "纳指档 20/80·3档·vol0.15·MA200闸（归档实际代码口径）")

    # G3 逐位复现门
    g3 = {"pass": True, "detail": {}}
    for sym, arm in (("^GSPC", gspc), ("^IXIC", ixic)):
        am = archived["instruments"][sym]["metrics"]
        for k in ("strategy_cagr", "strategy_mdd", "benchmark_cagr", "benchmark_mdd"):
            d = abs(arm["metrics"][k] - am[k])
            g3["detail"][f"{sym}.{k}"] = d
            if d >= 1e-12:
                g3["pass"] = False
    dates_identical = bool(gspc["dates"].equals(ixic["dates"]))
    if not (g3["pass"] and dates_identical):
        print("ABORT: P2 门未过", json.dumps({"G3_pass": g3["pass"],
                                              "dates_identical": dates_identical}))
        sys.exit(3)

    # 共同窗（两者已逐日同日期；对齐分支自动满足）
    def full(arm):
        sc, sm = arm["metrics"]["strategy_cagr"], arm["metrics"]["strategy_mdd"]
        bc, bm_ = arm["metrics"]["benchmark_cagr"], arm["metrics"]["benchmark_mdd"]
        dd_cut_pp = abs(bm_) * 100 - abs(sm) * 100
        cost_pp = (bc - sc) * 100
        return {
            "label": arm["label"],
            "strategy_ann_pct": sc * 100, "strategy_mdd_pct": sm * 100,
            "strategy_calmar": sc / abs(sm),
            "hold_ann_pct": bc * 100, "hold_mdd_pct": bm_ * 100,
            "dd_reduction_pp": dd_cut_pp,
            "dd_reduction_pct_of_hold": dd_cut_pp / (abs(bm_) * 100) * 100,
            "ann_cost_pp": cost_pp,
            "insurance_ratio_pp_per_pp": (dd_cut_pp / cost_pp) if cost_pp > 0 else None,
        }

    segs = [("1986-01-01", "1989-12-31", "1986-89"), ("1990-01-01", "1999-12-31", "1990s"),
            ("2000-01-01", "2009-12-31", "2000s"), ("2010-01-01", "2019-12-31", "2010s"),
            ("2020-01-01", "2026-12-31", "2020-26")]
    seg_table = {}
    for lo, hi, tag in segs:
        row = {}
        for name, arm in (("spx", gspc), ("ndx", ixic)):
            row[f"{name}_strategy"] = seg_ann_dd(arm["eq"], lo, hi)
            row[f"{name}_hold"] = seg_ann_dd(arm["bm"], lo, hi)
        seg_table[tag] = row
    defense_corr = float(gspc["eq"].pct_change().corr(ixic["eq"].pct_change()))
    bench_corr = float(gspc["bm"].pct_change().corr(ixic["bm"].pct_change()))

    # 补充臂：生产终版预设（解决"5档"标签歧义），共同窗、同费用执行口径
    sup = {}
    for sym, cfg, label in (
        ("^IXIC", {"n_bands": 5, "low_edge": 20.0, "high_edge": 80.0, "gamma": 1.5,
                   "vol_target": 0.15, "min_weight": 0.3, "gate_mode": "ma200"},
         "纳指终版预设 5档20/80·底仓0.3·vol0.15（presets nq_b200_defense_final）"),
        ("^GSPC", {"n_bands": 3, "low_edge": 30.0, "high_edge": 70.0, "gamma": 1.5,
                   "vol_target": 0.10, "gate_mode": "ma200"},
         "标普终版预设 3档30/70·vol0.10（presets us_b200_defense_final）"),
    ):
        rr = compute_run({**DEFENSE_CFG, "symbol": sym, **cfg})
        dts = pd.to_datetime(rr["daily"]["date"])
        eq = pd.Series(rr["daily"]["equity"], index=dts)
        bm2 = pd.Series(rr["daily"]["benchmark"], index=dts)
        sc, sm = rr["metrics"]["strategy_cagr"], rr["metrics"]["strategy_mdd"]
        bc, bm_ = rr["metrics"]["benchmark_cagr"], rr["metrics"]["benchmark_mdd"]
        sup[label] = {"window": f"{dts[0].date()}→{dts[-1].date()}",
                      "strategy_ann_pct": sc * 100, "strategy_mdd_pct": sm * 100,
                      "hold_ann_pct": bc * 100, "hold_mdd_pct": bm_ * 100,
                      "dd_reduction_pp": (abs(bm_) - abs(sm)) * 100,
                      "ann_cost_pp": (bc - sc) * 100}

    # 股息口径差（描述性）：^GSPC vs 缓存 SPY（复权）同窗年化
    div_note = None
    try:
        spy = pd.read_parquet(Path.home() / ".lei_signal_lab/cache/timing/SPY.parquet")
        c = spy["close"]
        c = c[(c.index >= pd.Timestamp(START)) & (c.index <= pd.Timestamp(rps.WIN_END))]
        g2 = pd.read_parquet(RAW / "module_e/us_gspc_ohlc.parquet")["close"]
        g2 = g2[(g2.index >= pd.Timestamp(START)) & (g2.index <= pd.Timestamp(rps.WIN_END))]
        sa, _ = m_ann_dd(c)
        ga, _ = m_ann_dd(g2)
        div_note = {"spy_adjusted_ann_pct": sa * 100, "gspc_price_index_ann_pct": ga * 100,
                    "gap_pp": (sa - ga) * 100,
                    "note": "SPY 为复权含息口径（timing 缓存），^GSPC 为价格指数不含息；"
                            "差值≈股息贡献量级，仅描述性。"}
    except Exception as e:  # noqa: BLE001
        div_note = {"error": str(e)}

    return {
        "alignment_verdict": "原报告已对齐（us_defense.json 两档日期数组逐日相同）",
        "common_window": f"{gspc['dates'][0].date()}→{gspc['dates'][-1].date()}（{len(gspc['dates'])} 交易日）",
        "G3_bitwise_reproduction": {"pass": g3["pass"],
                                    "max_abs_diff": max(g3["detail"].values())},
        "certified_pair": {"spx": full(gspc), "ndx": full(ixic)},
        "defense_daily_return_corr": defense_corr,
        "benchmark_daily_return_corr": bench_corr,
        "decade_segments": seg_table,
        "supplement_presets": sup,
        "dividend_caliber_note": div_note,
        "_gspc_eq": gspc["eq"], "_ixic_eq": ixic["eq"],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p1 = run_p1()
    p2 = run_p2()

    # P2 机制归因阈值（冻结）：|Δ策略年化|≥1pp 或 |Δ策略回撤|≥3pp → 触发归因要求
    d_ann = abs(p2["certified_pair"]["spx"]["strategy_ann_pct"]
                - p2["certified_pair"]["ndx"]["strategy_ann_pct"])
    d_mdd = abs(p2["certified_pair"]["spx"]["strategy_mdd_pct"]
                - p2["certified_pair"]["ndx"]["strategy_mdd_pct"])
    p2["attribution_threshold_triggered"] = bool(d_ann >= 1.0 or d_mdd >= 3.0)
    p2["diff_spx_minus_ndx"] = {
        "strategy_ann_pp": p2["certified_pair"]["spx"]["strategy_ann_pct"]
        - p2["certified_pair"]["ndx"]["strategy_ann_pct"],
        "strategy_mdd_pp": p2["certified_pair"]["spx"]["strategy_mdd_pct"]
        - p2["certified_pair"]["ndx"]["strategy_mdd_pct"],
        "hold_ann_pp": p2["certified_pair"]["spx"]["hold_ann_pct"]
        - p2["certified_pair"]["ndx"]["hold_ann_pct"],
        "hold_mdd_pp": p2["certified_pair"]["spx"]["hold_mdd_pct"]
        - p2["certified_pair"]["ndx"]["hold_mdd_pct"],
    }

    # 逐日净值降采样落盘（周采样，足够画图复核），全量留在哈希外的辅助 csv
    for tag, s in (("p1_eq_ndx", p1["_armA_eq"]), ("p1_eq_spx", p1["_armB_eq"]),
                   ("p2_eq_spx_defense", p2["_gspc_eq"]), ("p2_eq_ndx_defense", p2["_ixic_eq"])):
        s.rename("equity").to_frame().iloc[::5].to_csv(OUT / f"{tag}_weekly.csv")

    for k in ("_armA_eq", "_armB_eq", "_gspc_eq", "_ixic_eq"):
        (p1 if k in p1 else p2).pop(k)

    results = {"p1_duo_leg_swap": p1, "p2_defense_aligned": p2,
               "meta": {"script": "scripts/run_spx_vs_ndx.py",
                        "repo_window_sources": {
                            "p1": "render_duo_page.py 认证窗口 2010-06-01→rps.WIN_END(2026-08-18)",
                            "p2": "us_defense.json 认证窗口 1986-01-02→2026-08-26"},
                        "python": sys.version.split()[0],
                        "pandas": pd.__version__, "numpy": np.__version__}}
    canon = json.dumps(results, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), default=float)
    h = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    results["meta"]["sha256_canonical"] = h
    (OUT / "spx_vs_ndx_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True, default=float) + "\n")

    print("=" * 72)
    print("P1 两只版换腿（2010-06→2026-08，10bp，5%带）")
    pa, pb = p1["portfolio"]["ndx_version"], p1["portfolio"]["spx_version"]
    print(f"  纳指版  ann {pa['ann_pct']:.2f}%  mdd {pa['mdd_pct']:.2f}%  "
          f"Calmar {pa['calmar']:.3f}  events {pa['events']}")
    print(f"  标普版  ann {pb['ann_pct']:.2f}%  mdd {pb['mdd_pct']:.2f}%  "
          f"Calmar {pb['calmar']:.3f}  events {pb['events']}")
    d = p1["portfolio"]["diff_spx_minus_ndx"]
    print(f"  Δ(标普-纳指): ann {d['ann_pp']:+.2f}pp  mdd {d['mdd_pp']:+.2f}pp  "
          f"corr {p1['portfolio']['daily_return_corr']:.3f}")
    ls = p1["us_leg_hold_same_window"]
    print(f"  美腿持有同期: 纳指 {ls['纳斯达克^IXIC']['ann_pct']:.2f}%/{ls['纳斯达克^IXIC']['mdd_pct']:.1f}%"
          f"  标普 {ls['标普500^GSPC']['ann_pct']:.2f}%/{ls['标普500^GSPC']['mdd_pct']:.1f}%"
          f"  腿相关 {ls['leg_daily_return_corr']:.3f}")
    print("-" * 72)
    print("P2 防守版同窗对齐（1986-01→2026-08-26）")
    for tag in ("spx", "ndx"):
        c = p2["certified_pair"][tag]
        print(f"  {c['label']}: 策略 {c['strategy_ann_pct']:.2f}%/{c['strategy_mdd_pct']:.1f}%"
              f"  持有 {c['hold_ann_pct']:.2f}%/{c['hold_mdd_pct']:.1f}%"
              f"  回撤削减 {c['dd_reduction_pp']:.1f}pp  年化代价 {c['ann_cost_pp']:.2f}pp"
              f"  性价比 {c['insurance_ratio_pp_per_pp']:.2f}")
    print(f"  防守策略日收益相关 {p2['defense_daily_return_corr']:.3f}  "
          f"持有日收益相关 {p2['benchmark_daily_return_corr']:.3f}")
    for k, v in p2["supplement_presets"].items():
        print(f"  [补充] {k}: {v['strategy_ann_pct']:.2f}%/{v['strategy_mdd_pct']:.1f}%"
              f" vs 持有 {v['hold_ann_pct']:.2f}%/{v['hold_mdd_pct']:.1f}%"
              f"  窗口 {v['window']}")
    if p2["dividend_caliber_note"] and "spy_adjusted_ann_pct" in p2["dividend_caliber_note"]:
        dn = p2["dividend_caliber_note"]
        print(f"  [口径] SPY复权 {dn['spy_adjusted_ann_pct']:.2f}% vs ^GSPC {dn['gspc_price_index_ann_pct']:.2f}%"
              f"（股息差≈{dn['gap_pp']:.2f}pp/年，描述性）")
    print("=" * 72)
    print("sha256(canonical):", h)


if __name__ == "__main__":
    main()
