"""美债 10Y / 收益率曲线做美股触发信号·独立交叉验证轮（2026-09-01）。

定位声明：本脚本是 agent D（Prompt D 正交性检查）为解锁依赖而预跑的
Prompt A **独立冗余实现**；正版 Prompt A 归档以同日另一 agent 的
raw/us-treasury-signal/ 与其 ARCHIVE 为准（其判定更严：JB1 波动预警按
基线×1.15 硬线+2000 次安慰剂 95 分位线判 falsified）。本实现保留价值 =
独立双实现的交叉对照（事件集/方向一致性），不作为独立证据链引用。

背景：现有美股信号只测过宽度双线极值（B20&B50≤15/≥85）与模块 E 手册买入
（docs/experiments/module-e-report-2026-08-27.md），从未用利率类数据做**触发**
信号。红线（lei-ARCHIVE 第二节"利率档位闸"）：中债 10Y 滚动 5 年分位 ≥85 做
**仓位打折**已判负（DD 改善 0，面板哑铃为全样本分位前视假象）。本轮测的是
利率**曲线形态**作为**买卖触发**（引擎层/触发层），不是仓位缩放——机制不同，
若证伪亦不得反推仓位层。

信号候选（事前写死）：
- A1 倒挂解除买入触发：us_10_2_spread 连续 ≥MIN_RUN(10) 交易日 <0 后，首个
  ≥0 收盘日为信号日（冷却：一段倒挂只出一个事件）。敏感性 min_run=5/1 仅报告。
- A2 10Y 快速变动波动预警：chg20 = us_10y − us_10y[t−20 交易日]；expanding
  分位（截至 t 自身历史，暖机 ≥1260 交易日，无前视）≥0.95 且 chg20>0 为
  上行臂信号；≤0.05 且 chg20<0 为下行臂信号。连续触发用 20 交易日冷却去重。
- A3 长倒挂后解除：倒挂段连续 ≥252 交易日的解除事件（A1 子集）。预计 n≈2，
  事前定性为只报告不判定。

判定标准（事前写死，跑之前落 docstring，跑完不许改；三档沿用 huanjing 范式）：
- T1（A1 买入信息量·SPX 主判）：
  passed  = n≥4 且 12m 平均远期收益 > 全样本逐日同口径基线 且 6m 同向（>基线）
  watch   = n≥4 且仅 12m 一项过
  falsified = n≥4 且 12m 不过
  n<4     → 「样本不足，只报告不判定」（利率周期事件天然稀少，如实降级）
  QQQ 交叉与 min_run 敏感性只报告不计判定。
- T2（A2 波动预警·两臂分别判）：
  通过 = n≥30 且信号执行日后 63 交易日已实现年化波动（日收益 std×√252）
         均值 > 全样本逐日子窗同口径均值
  证伪 = 任一臂 n≥30 且波动不高于基线
  n<30 的臂只报告。远期收益差（1/3/6/12m）全部落表但不进判定（预警的是
  波动不是方向；若收益差与波动叙述矛盾，报告明示）。
- T3（A3）：只报告。
- NC（阴性对照）：A1 主口径事件窗套黄金（COMEX GC=F 连续，覆盖 2000 起；
  若拉取失败回落 GLD 并声明）。判据：黄金 12m 均值−基线差 与 SPX 同号且
  |差| ≥ |SPX 差|×50% → 「对照异常：事件窗或含泛化 drift，信号特异性存疑」；
  否则对照通过。注意黄金与实际利率有机制关联（非纯无关资产），报告披露。
- 策略级（只报告不判定）：A1 主口径每事件投入剩余现金 50%，持有 252 交易
  日平仓（次日开盘执行），vs S0 买入持有；单边 5bp，闲置现金 0 收益。

口径（无未来函数）：利率值按信号日收盘已知、执行 = 下一美股交易日开盘
（沿用 module E 次日开盘纪律）；东财中美混合日历 reindex 到 SPX 交易日时
仅用过去值（asof/ffill，无前视）。事件研究远期收益 = 执行日开盘 → t+H 收盘
（H=21/63/126/252/504 交易日）；基线 = 全样本逐日同口径。多重比较：本轮新增
判定量 3 组（T1、T2×2 臂、NC），累计 N 继续叠加。

数据：
- 美债：东财 RPTA_WEB_TREASURYYIELD（src/lei_signal/fundamentals/sources.py
  fetch_treasury_history，全史 1990-12 起，首次联网后落盘 raw 缓存离线复跑）。
- SPX/QQQ OHLC：复用 docs/experiments/raw/module_e/ 已归档缓存（yfinance
  auto_adjust）。
- 黄金：GC=F（缺则 GLD）首次联网拉取后落盘 raw 缓存。

输出：docs/experiments/raw/us-treasury-signal-crosscheck/（JSON + CSV）。
复现：python3 scripts/run_us_treasury_signal_crosscheck.py（缓存齐后离线可复跑）。
双跑：PYTHONHASHSEED=0 / =42 输出 JSON sha256 一致方可引用。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "docs/experiments/raw/us-treasury-signal-crosscheck"
MODULE_E_RAW = REPO / "docs/experiments/raw/module_e"

MIN_RUN = 10            # A1 主口径：构成倒挂段所需连续 <0 交易日数
MIN_RUN_SENS = (5, 1)   # A1 敏感性（只报告）
LONG_INV = 252          # A3：长倒挂段定义（交易日）
QUANT_HI = 0.95         # A2 上行臂 expanding 分位阈
QUANT_LO = 0.05         # A2 下行臂
WARMUP = 1260           # A2 expanding 分位暖机（约 5 年）
CHG = 20                # A2 利率变动窗口（交易日）
COOLDOWN_TD = 20        # A2 连续触发去重（交易日）
HOLD_TD = 252           # 策略级持有期
COST = 0.0005           # 单边 5bp
HORIZONS = {"1m": 21, "3m": 63, "6m": 126, "12m": 252, "24m": 504}
VOL_WIN = 63            # T2 波动口径：执行日后 63 交易日
N_MIN_A1 = 4            # T1 判定最小事件数
N_MIN_A2 = 30           # T2 判定最小事件数


# ---------------------------------------------------------------- 数据


def fetch_treasury_cached() -> pd.DataFrame:
    """东财中美国债历史 → 仅美侧列，缓存优先。"""
    f = RAW / "treasury_us_history.parquet"
    if f.exists():
        return pd.read_parquet(f)
    sys.path.insert(0, str(REPO / "src"))
    from lei_signal.fundamentals import sources

    th = sources.fetch_treasury_history(lookback_days=12000)
    df = pd.DataFrame.from_dict(th, orient="index")
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df = df[["us_2y", "us_5y", "us_10y", "us_30y", "us_10_2_spread"]]
    df.to_parquet(f)
    return df


def fetch_ohlc_cached(symbol: str, start: str, cache_name: Path) -> pd.DataFrame:
    if cache_name.exists():
        return pd.read_parquet(cache_name)
    import yfinance as yf

    raw = yf.download(symbol, start=start, auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [c[0].lower() for c in raw.columns]
    else:
        raw.columns = [c.lower() for c in raw.columns]
    df = raw[["open", "close"]].dropna()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.to_parquet(cache_name)
    return df


def align_rate_to_trading(treasury: pd.DataFrame,
                          trading_days: pd.DatetimeIndex) -> pd.Series:
    """利率 reindex 到美股交易日，仅用过去已知值（asof，无前视）。"""
    s = treasury["us_10_2_spread"].dropna()
    return pd.Series(
        s.reindex(s.index.union(trading_days)).ffill().reindex(trading_days))


# ---------------------------------------------------------------- 信号


def inversion_events(spread: pd.Series, min_run: int) -> pd.DataFrame:
    """A1：连续 min_run 日 <0 的倒挂段 → 解除日（段后首个 ≥0 日）+ 段长。

    返回列：inv_start, inv_end, days(段长交易日), un_inversion(解除日=信号日)。
    段末之后若再无 ≥0 日（如末端仍倒挂/数据终），不产事件。
    """
    neg = spread < 0
    runs, start = [], None
    for d, v in neg.items():
        if v and start is None:
            start = d
        elif not v and start is not None:
            runs.append((start, d))  # [start, d) 为连续 <0 段
            start = None
    if start is not None:
        pass  # 末端未解除的倒挂段不产事件
    rows = []
    for s0, e0 in runs:
        n = int(neg.loc[s0:e0].sum())
        if n >= min_run:
            rows.append({"inv_start": s0, "inv_end": e0, "days": n,
                         "un_inversion": e0})
    return pd.DataFrame(rows)


def fast_move_signals(rate10: pd.Series, side: str) -> pd.Series:
    """A2：chg20 expanding 分位极值，20 交易日冷却去重。side='up'/'down'。"""
    chg = rate10 - rate10.shift(CHG)
    valid = chg.dropna()
    q = valid.expanding(min_periods=WARMUP).apply(
        lambda x: float((x <= x[-1]).mean()), raw=True)
    if side == "up":
        raw_sig = (chg > 0) & (q >= QUANT_HI)
    else:
        raw_sig = (chg < 0) & (q <= QUANT_LO)
    raw_sig = raw_sig.fillna(False)
    sigs, last = [], None
    for d, v in raw_sig.items():
        if v and (last is None or (d - last).days >= COOLDOWN_TD):
            sigs.append(d)
            last = d
    return pd.Series(True, index=pd.DatetimeIndex(sigs), dtype=bool)


# ---------------------------------------------------------------- 研究


def next_day_map(days: pd.DatetimeIndex, price_days: pd.DatetimeIndex
                 ) -> dict[pd.Timestamp, pd.Timestamp]:
    pdays = np.array(price_days)
    return {d: pd.Timestamp(pdays[pdays > d][0]) for d in days
            if (pdays > d).any()}


def event_study(signal_days: list[pd.Timestamp], price: pd.DataFrame) -> dict:
    """执行日开盘 → t+H 收盘远期收益 + 基线（全样本逐日同口径）。"""
    closes, opens = price["close"], price["open"]
    base = {}
    for h, n in HORIZONS.items():
        fwd = closes.shift(-n) / opens - 1
        base[h] = {"mean": float(fwd.mean()), "median": float(fwd.median()),
                   "n": int(fwd.notna().sum())}
    pos = {d: i for i, d in enumerate(price.index)}
    rows = []
    for d in signal_days:
        if d not in pos:
            continue
        i = pos[d]
        row = {"exec_date": d.date().isoformat()}
        for h, n in HORIZONS.items():
            j = i + n
            row[h] = float(closes.iloc[j] / opens.iloc[i] - 1) \
                if j < len(closes) else None
        # T2 波动口径：执行日后 VOL_WIN 日已实现年化波动（含执行日）
        w = closes.iloc[i:i + VOL_WIN]
        row["realized_vol63"] = float(w.pct_change().dropna().std()
                                      * np.sqrt(252)) if len(w) > 10 else None
        rows.append(row)
    out = {"baseline_all_days": base, "signals": rows}
    for h in HORIZONS:
        vals = [r[h] for r in rows if r[h] is not None]
        out[f"mean_{h}"] = round(float(np.mean(vals)), 4) if vals else None
        out[f"n_{h}"] = len(vals)
        out[f"win_{h}"] = round(float(np.mean([v > 0 for v in vals])), 3) \
            if vals else None
    vols = [r["realized_vol63"] for r in rows if r["realized_vol63"] is not None]
    all_vols = closes.pct_change().rolling(VOL_WIN).std().dropna() * np.sqrt(252)
    out["mean_realized_vol63"] = round(float(np.mean(vols)), 4) if vols else None
    out["baseline_realized_vol63"] = round(float(all_vols.mean()), 4)
    out["n_vol63"] = len(vols)
    return out


def sim_a1_strategy(price: pd.DataFrame, exec_days: list[pd.Timestamp]) -> dict:
    """策略级（只报告）：每事件投剩余现金 50%，持有 HOLD_TD 交易日平仓。"""
    days = price.index
    exec_set = set(exec_days)
    cash, units, equity = 1_000_000.0, 0.0, {}
    open_lots: list[tuple[int, float]] = []  # (到期下标, 份额)
    for i, d in enumerate(days):
        # 到期平仓（当日开盘）
        due = [lot for lot in open_lots if lot[0] <= i]
        if due:
            op = price.at[d, "open"]
            for _, sh in due:
                cash -= sh * op * COST
                cash += sh * op
                units -= sh
            open_lots = [lot for lot in open_lots if lot[0] > i]
        if d in exec_set and cash > 1e-9:
            op = price.at[d, "open"]
            amt = cash * 0.50
            sh = amt * (1 - COST) / op
            units += sh
            cash -= amt
            open_lots.append((i + HOLD_TD, sh))
        equity[d] = cash + units * price.at[d, "close"]
    eq = pd.Series(equity).sort_index()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    bh_units = 1_000_000.0 * (1 - COST) / price["open"].iloc[0]
    bh = bh_units * price["close"]
    return {
        "n_events": len(exec_days),
        "final": round(float(eq.iloc[-1]), 0),
        "cagr": round(float((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1), 4),
        "max_dd": round(float((eq / eq.cummax() - 1).min()), 4),
        "buy_hold_final": round(float(bh.iloc[-1]), 0),
        "buy_hold_cagr": round(float((bh.iloc[-1] / bh.iloc[0]) ** (1 / yrs) - 1), 4),
        "buy_hold_max_dd": round(float((bh / bh.cummax() - 1).min()), 4),
        "equity_monthly": eq.resample("ME").last().round(4),
    }


# ---------------------------------------------------------------- 判定


def judge_t1(study: dict) -> str:
    n = study["n_12m"]
    if n < N_MIN_A1:
        return f"insufficient_n(n={n}<{N_MIN_A1})_report_only"
    m12, m6 = study["mean_12m"], study["mean_6m"]
    b12 = study["baseline_all_days"]["12m"]["mean"]
    b6 = study["baseline_all_days"]["6m"]["mean"]
    if m12 > b12 and m6 > b6:
        return "passed"
    if m12 > b12:
        return "watch"
    return "falsified"


def judge_t2(study: dict) -> str:
    n = study["n_vol63"]
    if n < N_MIN_A2:
        return f"insufficient_n(n={n}<{N_MIN_A2})_report_only"
    if study["mean_realized_vol63"] > study["baseline_realized_vol63"]:
        return "passed"
    return "falsified"


def judge_nc(spx_study: dict, gold_study: dict) -> dict:
    d_spx = spx_study["mean_12m"] - spx_study["baseline_all_days"]["12m"]["mean"]
    d_gld = gold_study["mean_12m"] - gold_study["baseline_all_days"]["12m"]["mean"]
    if d_spx is None or d_gld is None:
        return {"diff_spx": d_spx, "diff_gold": d_gld, "verdict": "n/a"}
    anomalous = (d_spx * d_gld > 0) and (abs(d_gld) >= abs(d_spx) * 0.5)
    return {"diff_spx": round(d_spx, 4), "diff_gold": round(d_gld, 4),
            "verdict": "anomalous_general_drift" if anomalous else "control_ok"}


# ---------------------------------------------------------------- 主流程


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)

    treasury = fetch_treasury_cached()
    spx = pd.read_parquet(MODULE_E_RAW / "us_gspc_ohlc.parquet")
    qqq = pd.read_parquet(MODULE_E_RAW / "us_qqq_ohlc.parquet")
    gold_name = "gold_gcf_ohlc.parquet"
    try:
        gold = fetch_ohlc_cached("GC=F", "2000-01-01", RAW / gold_name)
        gold_src = "GC=F (COMEX 连续, yfinance auto_adjust)"
    except Exception as exc:  # noqa: BLE001 —— 回落 GLD 并声明
        gold = fetch_ohlc_cached("GLD", "2004-11-01", RAW / "gold_gld_ohlc.parquet")
        gold_src = f"GLD 回落（GC=F 拉取失败：{exc}）"

    res: dict = {
        "experiment": "us_treasury_trigger_signals",
        "config": {"MIN_RUN": MIN_RUN, "MIN_RUN_SENS": list(MIN_RUN_SENS),
                   "LONG_INV": LONG_INV, "QUANT_HI": QUANT_HI, "QUANT_LO": QUANT_LO,
                   "WARMUP": WARMUP, "CHG": CHG, "COOLDOWN_TD": COOLDOWN_TD,
                   "HOLD_TD": HOLD_TD, "COST": COST, "VOL_WIN": VOL_WIN,
                   "N_MIN_A1": N_MIN_A1, "N_MIN_A2": N_MIN_A2},
        "data": {
            "treasury": [str(treasury.index[0].date()),
                         str(treasury.index[-1].date())],
            "treasury_rows": len(treasury),
            "us10_null": int(treasury["us_10y"].isna().sum()),
            "spread_null": int(treasury["us_10_2_spread"].isna().sum()),
            "spx": [str(spx.index[0].date()), str(spx.index[-1].date())],
            "qqq": [str(qqq.index[0].date()), str(qqq.index[-1].date())],
            "gold_source": gold_src,
            "gold": [str(gold.index[0].date()), str(gold.index[-1].date())],
        },
    }

    # ---- A1：倒挂解除（主口径 + 敏感性）----
    spread_spx = align_rate_to_trading(treasury, spx.index)
    ev_main = inversion_events(spread_spx, MIN_RUN)
    sig_days = list(pd.DatetimeIndex(ev_main["un_inversion"]))
    emap = next_day_map(sig_days, spx.index)
    a1 = {
        "events": [{k: (str(v.date()) if hasattr(v, "date") else int(v))
                    for k, v in r.items()}
                   for r in ev_main.to_dict("records")],
        "study_spx": event_study(list(emap.values()), spx),
        "study_qqq": event_study(
            list(next_day_map(sig_days, qqq.index).values()), qqq),
        "study_gold": event_study(
            list(next_day_map(sig_days, gold.index).values()), gold),
    }
    a1["T1_spx"] = judge_t1(a1["study_spx"])
    a1["NC_gold"] = judge_nc(a1["study_spx"], a1["study_gold"])
    strat = sim_a1_strategy(spx, list(emap.values()))
    a1["strategy_report_only"] = {
        k: v for k, v in strat.items() if k != "equity_monthly"}
    (pd.DataFrame({"date": strat["equity_monthly"].index.strftime("%Y-%m-%d"),
                   "equity": strat["equity_monthly"].values})
     ).to_csv(RAW / "a1_strategy_equity_monthly.csv", index=False)
    a1["sens_min_run"] = {}
    for mr in MIN_RUN_SENS:
        ev_s = inversion_events(spread_spx, mr)
        sd_s = list(pd.DatetimeIndex(ev_s["un_inversion"]))
        a1["sens_min_run"][str(mr)] = {
            "n_events": len(sd_s),
            "study_spx": event_study(
                list(next_day_map(sd_s, spx.index).values()), spx),
        }
    res["A1_un_inversion"] = a1

    # ---- A2：10Y 快速变动（expanding 分位）----
    rate_spx = pd.Series(treasury["us_10y"].dropna()).reindex(
        treasury.index.union(spx.index)).ffill().reindex(spx.index)
    a2 = {}
    for side in ("up", "down"):
        sigs = fast_move_signals(rate_spx, side)
        emap2 = next_day_map(list(sigs.index), spx.index)
        st = event_study(list(emap2.values()), spx)
        st_qqq = event_study(
            list(next_day_map(list(sigs.index), qqq.index).values()), qqq)
        a2[side] = {"n_signals": int(len(sigs)),
                    "signal_days": [str(d.date()) for d in sigs.index],
                    "study_spx": st, "study_qqq": st_qqq,
                    "T2_spx": judge_t2(st)}
    res["A2_fast_move"] = a2

    # ---- A3：长倒挂（≥252 交易日）解除，只报告 ----
    ev_long = inversion_events(spread_spx, LONG_INV)
    sd_l = list(pd.DatetimeIndex(ev_long["un_inversion"]))
    res["A3_long_inversion_report_only"] = {
        "n_events": len(sd_l),
        "events": [{k: (str(v.date()) if hasattr(v, "date") else int(v))
                    for k, v in r.items()}
                   for r in ev_long.to_dict("records")],
        "study_spx": event_study(list(next_day_map(sd_l, spx.index).values()), spx),
    }

    # ---- 明细 CSV ----
    pd.DataFrame(a1["study_spx"]["signals"]).to_csv(
        RAW / "a1_event_spx.csv", index=False)
    for side in ("up", "down"):
        pd.DataFrame(a2[side]["study_spx"]["signals"]).to_csv(
            RAW / f"a2_{side}_event_spx.csv", index=False)

    (RAW / "us_treasury_results.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False, default=str))

    brief = {
        "A1_events": a1["events"],
        "T1_spx": a1["T1_spx"],
        "A1_12m_mean_vs_base": [a1["study_spx"]["mean_12m"],
                                a1["study_spx"]["baseline_all_days"]["12m"]["mean"]],
        "NC_gold": a1["NC_gold"],
        "strategy": a1["strategy_report_only"],
        "A2_up": {"n": a2["up"]["n_signals"], "T2": a2["up"]["T2_spx"]},
        "A2_down": {"n": a2["down"]["n_signals"], "T2": a2["down"]["T2_spx"]},
        "A3_n": res["A3_long_inversion_report_only"]["n_events"],
    }
    print(json.dumps(brief, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
