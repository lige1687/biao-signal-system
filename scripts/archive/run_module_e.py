"""模块 E 情绪极值择时·手册口径正式测（手册 3.6 / 规格 V2.2 §9，2026-08-27）。

背景：宽度→仓位实验（breadth-position）测的是档位式调仓（S2/S3），非手册
口径。本轮按规格 §9 原文补模块 E 正式测：v1 宽度单信号 / v3 三线共振
（v2 共振版需 AAII/NAAIM/PutCall 历史，当前仅 1 周数据，登记暂缓）。

判定标准（事前写死，跑之前落 docstring，跑完不许改）：
- J1（E5 主判·美股）：E 完整版（v1+对冲50%）终值 ≥ S1 周定投终值
  ⇒ 「择时有增量」；否则如实判负。同时对 S0 买入持有只报告不判定。
- J2（事件信息量·每版本×每市场）：信号执行日后 12 个月平均远期收益
  > 全样本逐日同口径平均，且该版本信号数 ≥5 才判（<5 只报告不判定）；
  1/3/6/12/24 月全部落表。
- J3（对冲腿·美股）：对冲分段合计盈亏 > 0（避免损失>错过反弹）
  且 E 完整版最大回撤 < E 纯长腿（对冲0）最大回撤。
- J4（A 股主口径·短样本）：J2 同口径判定；E 长腿 vs S1/S0 执行同一
  E5 比较但结论标「短样本」。
- IS/OOS：OOS = 2024-08-27 之后的信号（末日回推 2 年），只报告。

口径（规格 E1–E5 原文）：
- v1 底 = B20≤15 且 B50≤15 收盘确认；v3 底 = 三线同 ≤15；
  顶部对冲 = B20≥85 且 B50≥85（对冲侧不用 B200）。次日开盘执行。
- 冷却 e_reentry_cooldown=4 周（20 交易日）：一次连续在场极值区只出
  一个信号；须离场连续 ≥20 交易日后再次进场才算新信号（敏感性 2/8 周，
  仅 v1@对冲50%）。
- 分批 e_tranche=50%：每信号投入剩余现金的 50%（规格标定值）。
- E3 只买不卖：长腿无止损/无目标/无持有期（设计而非遗漏，报告明示）。
- E4 对冲（仅美股；A 股无指数做空数据腿）：顶部区在场即对冲、离场即平
  （各滞后一日开盘），对冲名义 = 进场日多头市值 × hedge_ratio（分段内
  静态），敏感性 0/50/100%。
- 成本单边 5bp；闲置现金 0 收益；做空按指数合成（无保证金/carry，声明）。
- 基准：S0 买入持有；S1 周定投 N=min(260, ⌈周数/2⌉) 份（沿用上轮口径）；
  S1b 全窗周均分（敏感性）。

数据：
- 美股宽度 ~/.lei_signal_lab/cache/timing/breadth_sp500.parquet
  （b20/b50/b200，1986-01-29→2026-08-14，今日 503 成分股回算：幸存者
  偏差使历史宽度系统性偏高 ⇒ 底部信号是真实口径的保守子集）。
- 美股价格 ^GSPC OHLC（yfinance auto_adjust，1985 起，落盘 raw 缓存；
  指数价格序列不含股息，E 与基准同源，相对比较自洽）。
- A 股主口径宽度 cache/a_share_ma_breadth_history.json（2021-06-18→，
  全 A 日更管线）；价格 = 回测池 000300.SS.bars.parquet（OHLC 十年）。
- A 股参考口径（不计判定，双偏差声明）timing/breadth_cn_all.parquet
  （1990-12→2026-08-18，约 2900 只存续股回算，宇宙与主口径不同）；
  价格 000300.SS yfinance 2005 起。
- QQQ 交叉：SP500 宽度信号施于 QQQ（宽度宇宙≠标的，标注口径近似）。
- 多重比较：本轮新增判定量约 12 组，累计 N 继续叠加。

输出：docs/experiments/raw/module_e/（JSON + CSV）
复现：python3 scripts/run_module_e.py（首次联网拉指数 OHLC 后离线可复跑）
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "docs/experiments/raw/module_e"
CACHE = Path.home() / ".lei_signal_lab/cache"
POOL = Path.home() / ".lei_signal_lab/backtest_pool"

COST = 0.0005          # 单边 5bp
LOW, HIGH = 15.0, 85.0  # 手册极值阈值（百分比）
TRANCHE = 0.50          # 规格 e_tranche 标定值
COOLDOWN_TD = 20        # 规格 e_reentry_cooldown=4 周 → 20 交易日
HEDGE_RATIO = 0.50      # 规格 hedge_ratio 标定值
CAPITAL = 1_000_000.0
HORIZONS = {  # 事件研究远期窗口（交易日）
    "1m": 21, "3m": 63, "6m": 126, "12m": 252, "24m": 504,
}
OOS_CUT = pd.Timestamp("2024-08-27")  # 末日回推 2 年


# ---------------------------------------------------------------- 数据


def fetch_ohlc(symbol: str, start: str, cache_name: str) -> pd.DataFrame:
    """yfinance OHLC（auto_adjust），缓存 raw 目录；离线优先用缓存。"""
    f = RAW / cache_name
    if f.exists():
        df = pd.read_parquet(f)
        return df
    import yfinance as yf

    raw = yf.download(symbol, start=start, auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):  # (Price, Ticker) → 扁平
        raw.columns = [c[0].lower() for c in raw.columns]
    else:
        raw.columns = [c.lower() for c in raw.columns]
    df = raw[["open", "close"]].dropna()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.to_parquet(f)
    return df


def load_us_breadth() -> pd.DataFrame:
    df = pd.read_parquet(CACHE / "timing/breadth_sp500.parquet")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df[["b20", "b50", "b200"]].astype(float)


def load_cn_breadth() -> pd.DataFrame:
    obj = json.loads((CACHE / "a_share_ma_breadth_history.json").read_text())
    df = pd.DataFrame(obj)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    br = df[["ma20_pct", "ma50_pct", "ma200_pct"]].astype(float)  # 已是百分数
    br.columns = ["b20", "b50", "b200"]
    return br


def load_cn_breadth_ref() -> pd.DataFrame:
    df = pd.read_parquet(CACHE / "timing/breadth_cn_all.parquet")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df[["b20", "b50", "b200"]].astype(float)


def load_pool_ohlc(symbol: str) -> pd.DataFrame:
    df = pd.read_parquet(POOL / f"{symbol}.bars.parquet")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df[["open", "close"]].astype(float)




# ---------------------------------------------------------------- 信号状态机


def zone_mask(breadth: pd.DataFrame, version: str, side: str) -> pd.Series:
    """极值区在场判定。side='buy'（≤15）/ 'top'（≥85，对冲侧不用 B200）。"""
    b20, b50, b200 = breadth["b20"], breadth["b50"], breadth["b200"]
    if side == "buy":
        if version == "v1":
            return (b20 <= LOW) & (b50 <= LOW)
        return (b20 <= LOW) & (b50 <= LOW) & (b200 <= LOW)
    return (b20 >= HIGH) & (b50 >= HIGH)


def gen_buy_signals(breadth: pd.DataFrame, version: str,
                    cooldown_td: int = COOLDOWN_TD) -> pd.Series:
    """规格 E2：在场首日触发一个信号；离场连续 ≥cooldown_td 交易日后
    再次进场才算新信号（冷却用连续离场天数计数，防极值区停留重复触发）。"""
    z = zone_mask(breadth, version, "buy").fillna(False)
    armed, out_run, sigs = True, 0, []
    for d, in_zone in z.items():
        if in_zone and armed:
            sigs.append(d)
            armed, out_run = False, 0
        elif not in_zone and not armed:
            out_run += 1
            if out_run >= cooldown_td:
                armed = True
    return pd.Series(True, index=pd.DatetimeIndex(sigs), dtype=bool)


def next_day_map(days: pd.DatetimeIndex, price_days: pd.DatetimeIndex
                 ) -> dict[pd.Timestamp, pd.Timestamp]:
    """信号日 → 下一价格交易日（执行日）。"""
    pdays = np.array(price_days)
    return {d: pd.Timestamp(pdays[pdays > d][0]) for d in days
            if (pdays > d).any()}


# ---------------------------------------------------------------- 模拟


def cagr(equity: pd.Series) -> float:
    yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    return (equity.iloc[-1] / equity.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else np.nan


def max_dd(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1).min())


def sim_module_e(price: pd.DataFrame, buy_exec: dict, breadth: pd.DataFrame,
                 tranche: float = TRANCHE, hedge_ratio: float = HEDGE_RATIO,
                 capital: float = CAPITAL):
    """E 主体模拟：长腿只买不卖（每信号投剩余现金×tranche，次日开盘）；
    对冲腿 = 顶部区在场即做空（进场日多头市值×hedge_ratio，分段静态），
    离场次日开盘平仓。做空按指数合成、费用入现金。返回
    (日权益序列, 买入流水, 对冲分段, 换手名义)。"""
    days = price.index
    top_zone = zone_mask(breadth, "v1", "top").reindex(days, fill_value=False)
    # 执行日映射：t 收盘确认 → t+1 开盘执行
    exec_buy = {v: k for k, v in buy_exec.items()}  # 执行日 → 信号日
    want_hedge_today = top_zone.shift(1, fill_value=False)  # 昨收状态今日执行
    cash, units = capital, 0.0
    hedge_units, hedge_px = 0.0, np.nan
    hedge_realized = 0.0  # 已实现对冲盈亏累计（毛额；费用单独入 fees_paid）
    fees_paid = 0.0  # 对冲费用入权益、不动现金（防耗干分批现金）
    equity, trades, hedges, turnover = {}, [], [], 0.0
    for d in days:
        op, cl = price.at[d, "open"], price.at[d, "close"]
        if d in exec_buy and cash > 1e-9:  # 长腿买入（只买不卖）
            amt = cash * tranche
            fee = amt * COST
            units += (amt - fee) / op
            cash -= amt
            turnover += amt
            trades.append({"signal_date": exec_buy[d].date().isoformat(),
                           "exec_date": d.date().isoformat(), "exec_open": round(op, 2),
                           "amount": round(amt, 2)})
        hedging = bool(want_hedge_today.get(d, False))
        if (hedging and hedge_ratio > 0 and hedge_units == 0.0
                and units > 0):  # 开对冲
            notional = units * op * hedge_ratio
            hedge_units, hedge_px = notional / op, op
            fees_paid += notional * COST
            turnover += notional
            hedges.append({"entry_date": d.date().isoformat(),
                           "entry_open": round(op, 2),
                           "notional": round(notional, 2)})
        elif not hedging and hedge_units > 0.0:  # 平对冲
            gross = hedge_units * (hedge_px - op)
            exit_fee = hedge_units * op * COST
            hedge_realized += gross
            fees_paid += exit_fee
            turnover += hedge_units * op
            hedges[-1].update({"exit_date": d.date().isoformat(),
                               "exit_open": round(op, 2),
                               "pnl": round(gross - exit_fee
                                            - hedges[-1]["notional"] * COST, 2)})
            hedge_units, hedge_px = 0.0, np.nan
        hedge_mark = hedge_units * (hedge_px - cl) if hedge_units > 0 else 0.0
        equity[d] = (cash + units * cl + hedge_mark + hedge_realized
                     - fees_paid)
    if hedge_units > 0:  # 末端未平仓按最后收盘标记（费用已计）
        hedges[-1].update({"exit_date": None,
                           "pnl": round(hedge_units
                                        * (hedge_px - price["close"].iloc[-1])
                                        - hedges[-1]["notional"] * COST, 2)})
    return (pd.Series(equity).sort_index(), trades, hedges, turnover)


def sim_bh(price: pd.DataFrame, capital: float = CAPITAL):
    amt = capital / (1 + COST)
    units = amt / price["open"].iloc[0]
    eq = units * price["close"]
    return eq, capital  # 全额买入，换手=本金


def sim_dca(price: pd.DataFrame, n_tranches: int | None, capital: float = CAPITAL):
    """周定投：每周最后交易日收盘投一份；n_tranches=None → 全窗均分。"""
    days = price.index
    weeks = pd.Series(days, index=days).groupby(
        [days.isocalendar().year, days.isocalendar().week]).max()
    invest_days = list(pd.DatetimeIndex(sorted(set(weeks))))
    if n_tranches is None:
        n_tranches = len(invest_days)
    n = min(n_tranches, len(invest_days))
    per = capital / n
    cash, units, turnover = capital, 0.0, 0.0
    eq, invested = {}, 0
    inv = set(invest_days[:n])
    for d in days:
        if d in inv and invested < n:
            fee = per * COST
            units += (per - fee) / price.at[d, "close"]
            cash -= per
            turnover += per
            invested += 1
        eq[d] = cash + units * price.at[d, "close"]
    return pd.Series(eq).sort_index(), turnover


# ---------------------------------------------------------------- 事件研究


def event_study(exec_days: list[pd.Timestamp], price: pd.DataFrame) -> dict:
    """执行日开盘 → t+H 收盘的远期收益；基线 = 全样本逐日同口径。"""
    closes = price["close"]
    pos = {d: i for i, d in enumerate(price.index)}
    base = {}
    for h, n in HORIZONS.items():
        fwd = closes.shift(-n) / price["open"] - 1
        base[h] = {"mean": float(fwd.mean()), "median": float(fwd.median())}
    out = {"baseline_all_days": base, "signals": []}
    sig_rows = []
    for d in exec_days:
        i = pos[d]
        row = {"exec_date": d.date().isoformat()}
        for h, n in HORIZONS.items():
            j = i + n
            row[h] = float(closes.iloc[j] / price["open"].iloc[i] - 1) \
                if j < len(closes) else None
        sig_rows.append(row)
    out["signals"] = sig_rows
    for h in HORIZONS:
        vals = [r[h] for r in sig_rows if r[h] is not None]
        out[f"mean_{h}"] = round(float(np.mean(vals)), 4) if vals else None
        out[f"n_{h}"] = len(vals)
        out[f"win_{h}"] = round(float(np.mean([v > 0 for v in vals])), 3) if vals else None
    return out


# ---------------------------------------------------------------- 汇总


def summarize(name: str, equity: pd.Series, turnover: float) -> dict:
    return {"name": name, "final": round(float(equity.iloc[-1]), 0),
            "cagr": round(float(cagr(equity)), 4),
            "max_dd": round(max_dd(equity), 4),
            "turnover": round(turnover, 0)}


def run_market(tag: str, breadth: pd.DataFrame, price: pd.DataFrame,
               versions=("v1", "v3"), hedge_grid=(0.0, 0.5, 1.0),
               v3_hedge=0.5, cooldown_sens=(10, 40),
               do_hedge: bool = True) -> dict:
    """单市场全套：各版本×对冲档 + 基准 + 事件研究 + 判定。"""
    res: dict = {"window": [str(price.index[0].date()), str(price.index[-1].date())]}
    # 宽度仅按自身覆盖日对齐（缺失日不信号），不向未来前推过期值
    br = breadth.reindex(price.index)
    br_cov = [str(breadth.index[0].date()), str(breadth.index[-1].date())]
    # ---- 基准 ----
    bh_eq, bh_to = sim_bh(price)
    s1_eq, s1_to = sim_dca(price, n_tranches=min(260, math.ceil(len(price) / 2 / 5)))
    s1b_eq, s1b_to = sim_dca(price, n_tranches=None)
    res["baselines"] = {
        "S0_buy_hold": summarize("S0", bh_eq, bh_to),
        "S1_weekly_dca": summarize("S1", s1_eq, s1_to),
        "S1b_full_window_dca": summarize("S1b", s1b_eq, s1b_to),
    }
    # ---- E 各臂 ----
    arms: dict[str, dict] = {}
    for v in versions:
        sigs = gen_buy_signals(br, v)
        emap = next_day_map(sigs.index, price.index)
        study = event_study(list(emap.values()), price)
        hrs = list(hedge_grid) if v == "v1" else [v3_hedge]
        if not do_hedge:
            hrs = [0.0]
        for hr in hrs:
            eq, trades, hedges, to = sim_module_e(
                price, emap, br, hedge_ratio=hr)
            key = f"{v}_hedge{int(hr * 100)}"
            arms[key] = {
                **summarize(key, eq, to),
                "_equity": eq,
                "n_signals": len(trades), "n_hedge_episodes": len(
                    [h for h in hedges if h.get("exit_date")]),
                "hedge_pnl_sum": round(sum(h.get("pnl", 0) for h in hedges), 0),
                "signals": [t["signal_date"] for t in trades],
                "hedge_episodes": hedges,
                "event_study": study,
            }
            if v == "v1" and hr == HEDGE_RATIO:
                for cd in cooldown_sens:  # 冷却敏感性（仅 v1@50%）
                    sigs_cd = gen_buy_signals(br, v, cooldown_td=cd)
                    emap_cd = next_day_map(sigs_cd.index, price.index)
                    eq_cd, tr_cd, hd_cd, to_cd = sim_module_e(
                        price, emap_cd, br, hedge_ratio=hr)
                    arms[f"v1_cd{cd}_hedge50"] = {
                        **summarize(f"v1_cd{cd}", eq_cd, to_cd),
                        "n_signals": len(tr_cd)}
    res["arms"] = arms
    res["breadth_coverage"] = br_cov
    # ---- OOS 拆分（事件研究里标注 2024-08-27 后的信号）----
    for key in ("v1_hedge50", "v1_hedge0", "v3_hedge50", "v3_hedge0"):
        if key in arms and "event_study" in arms[key]:
            st = arms[key]["event_study"]
            st["oos_signals"] = [s for s in st["signals"]
                                 if pd.Timestamp(s["exec_date"]) > OOS_CUT]
    # ---- 月度权益曲线落盘（审计用）----
    try:
        cols = {"S0_bh": bh_eq, "S1_dca": s1_eq}
        for key in ("v1_hedge0", "v1_hedge50", "v1_hedge100", "v3_hedge50"):
            if key in arms:
                cols[key] = arms[key]["_equity"]
        monthly = pd.DataFrame(cols).resample("ME").last().dropna(how="all")
        monthly.to_csv(RAW / f"{tag}_monthly_equity.csv")
    except Exception:  # noqa: BLE001 — 落盘失败不阻断主流程
        pass
    return res


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)

    # ---------- 美股（主考场）----------
    us_br = load_us_breadth()
    us_px = fetch_ohlc("^GSPC", "1985-01-01", "us_gspc_ohlc.parquet")
    us_px = us_px[us_px.index >= pd.Timestamp("1986-10-15")]  # B200 就绪日统一起点
    us = run_market("us", us_br, us_px)
    # 判定 J1/J2/J3
    v1 = us["arms"]["v1_hedge50"]
    us["verdicts"] = {
        "J1_beats_dca": bool(v1["final"] >= us["baselines"]["S1_weekly_dca"]["final"]),
        "J2_v1_info": bool(v1["n_signals"] >= 5
                           and v1["event_study"]["mean_12m"]
                           > v1["event_study"]["baseline_all_days"]["12m"]["mean"]),
        "J2_v3_info": bool(us["arms"]["v3_hedge50"]["n_signals"] >= 5
                           and us["arms"]["v3_hedge50"]["event_study"]["mean_12m"]
                           > us["arms"]["v3_hedge50"]["event_study"]
                           ["baseline_all_days"]["12m"]["mean"]),
        "J3_hedge_pnl_pos": bool(v1["hedge_pnl_sum"] > 0),
        # max_dd 为负数：回撤更浅 = 数值更大（更接近 0）
        "J3_hedge_reduces_dd": bool(v1["max_dd"]
                                    > us["arms"]["v1_hedge0"]["max_dd"]),
    }

    # ---------- QQQ 交叉（宽度宇宙≠标的，口径近似）----------
    qqq_px = fetch_ohlc("QQQ", "1999-01-01", "us_qqq_ohlc.parquet")
    qqq = run_market("qqq", us_br, qqq_px, versions=("v1",), do_hedge=True,
                     hedge_grid=(0.5,), cooldown_sens=())

    # ---------- A 股主口径（短样本）----------
    cn_br = load_cn_breadth()
    cn_px = load_pool_ohlc("000300.SS")
    cn_px = cn_px[cn_px.index >= cn_br.index[0]]
    cn = run_market("cn", cn_br, cn_px, do_hedge=False)  # 无做空腿
    cn["verdicts"] = {}
    for v in ("v1", "v3"):
        arm = cn["arms"][f"{v}_hedge0"]
        cn["verdicts"][f"J4_{v}_info"] = bool(
            arm["n_signals"] >= 5
            and arm["event_study"]["mean_12m"]
            > arm["event_study"]["baseline_all_days"]["12m"]["mean"])
        cn["verdicts"][f"J4_{v}_beats_dca_short_sample"] = bool(
            arm["final"] >= cn["baselines"]["S1_weekly_dca"]["final"])

    # ---------- A 股参考口径（1990 宽度 × 2005 起指数，不计判定）----------
    ref_br = load_cn_breadth_ref()
    ref_px = pd.read_parquet(CACHE / "timing/000300.parquet")[["open", "close"]]
    ref_px.index = pd.to_datetime(ref_px.index).tz_localize(None).normalize()
    ref = run_market("cn_ref", ref_br, ref_px, do_hedge=False)

    out = {
        "config": {"LOW": LOW, "HIGH": HIGH, "TRANCHE": TRANCHE,
                   "COOLDOWN_TD": COOLDOWN_TD, "HEDGE_RATIO": HEDGE_RATIO,
                   "COST": COST, "CAPITAL": CAPITAL,
                   "oos_cut": str(OOS_CUT.date())},
        "us": us, "us_qqq_cross": qqq, "cn": cn, "cn_reference_only": ref,
    }
    def _strip(obj):
        if isinstance(obj, dict):
            return {k: _strip(v) for k, v in obj.items()
                    if not str(k).startswith("_")}
        return obj

    (RAW / "module_e_results.json").write_text(
        json.dumps(_strip(out), indent=2, ensure_ascii=False, default=str))
    # 明细 CSV
    for tag, blk in (("us", us), ("cn", cn), ("cn_ref", ref)):
        rows = []
        for k, a in blk.get("arms", {}).items():
            rows.append({"arm": k, **{x: a.get(x) for x in
                          ("final", "cagr", "max_dd", "n_signals",
                           "n_hedge_episodes", "hedge_pnl_sum")}})
        if rows:
            pd.DataFrame(rows).to_csv(RAW / f"{tag}_arms.csv", index=False)
        for a in blk.get("arms", {}).values():  # 每版本一份信号明细
            if "event_study" in a:
                fn = RAW / f"{tag}_event_signals_{a['name']}.csv"
                pd.DataFrame(a["event_study"]["signals"]).to_csv(fn, index=False)
    print(json.dumps({"us_verdicts": us["verdicts"], "cn_verdicts": cn["verdicts"],
                      "us_baselines": us["baselines"],
                      "us_v1": {k: us["arms"]["v1_hedge50"][k]
                                for k in ("final", "cagr", "max_dd",
                                          "n_signals", "hedge_pnl_sum")},
                      "us_v3_n": us["arms"]["v3_hedge50"]["n_signals"]},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
