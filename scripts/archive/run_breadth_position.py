"""宽度→仓位曲线回测（手册 3.6 极值区定调仓位 / 规格 4.2 市场层先于交易层）。

判定标准（事前写死，2026-08-27，跑之前落 docstring）：
- 美股 S2「成立」 = 全期最大回撤 ≤ 0.75 × S0 最大回撤（降 25%+）
  且 全期年化 ≥ 0.85 × S0 年化。
- E5 考题：S2 终值 < S1（周定投）终值 ⇒ 如实报告「择时无增量」。
- A 股 S2「有效」 = 全期最大回撤较 S0 改善 ≥30% 且 全期终值 ≥ 0.90 × S0。
- A 股宽度样本起点 2021-06-18（晚于 2021-02 峰），2021 阴跌段只覆盖一半，
  A 股全部结论标注「短样本」。

口径：
- 信号：调仓日（每周最后一个交易日）收盘时的宽度 B50（A 股另跑 B200 变体），
  执行：次一交易日收盘调仓（无前视）。单边成本 5bp 按换手名义额计。
- S0 买入持有；S1 周定投（初始资金均分 N_tranche=min(260, ⌈周数/2⌉) 份，
  每调仓日投一份，成本同 5bp，投完持有）；S2 目标仓位=f(B50) 档位表；
  S3 纯择时（B50≤40 全仓 else 空仓）。
- S2 档位（基准 V1）：≤20→100%，20-40→80%，40-60→60%，60-85→40%，>85→20%。
  变体 V2 激进：100/70/40/20/10；V3 温和：100/90/75/60/40。
- 月度再平衡变体：调仓日改为每月最后交易日（防过拟合对照）。

输出：docs/experiments/raw/breadth_position/breadth_position_results.json
复现：python3 scripts/run_breadth_position.py（约 1 分钟）
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from breadth_data import (  # noqa: E402
    RAW_DIR,
    load_cn_breadth,
    load_gspc_long,
    load_pool_close,
    load_us_breadth,
    merge_breadth_price,
)

COST = 0.0005  # 单边 5bp
TIERS_V1 = [(20, 1.0), (40, 0.8), (60, 0.6), (85, 0.4), (999, 0.2)]
TIERS_V2 = [(20, 1.0), (40, 0.7), (60, 0.4), (85, 0.2), (999, 0.1)]
TIERS_V3 = [(20, 1.0), (40, 0.9), (60, 0.75), (85, 0.6), (999, 0.4)]


def target_position(breadth: float, tiers) -> float:
    for th, w in tiers:
        if breadth <= th:
            return w
    return tiers[-1][1]


def simulate(price: pd.Series, targets: pd.Series, capital: float = 1_000_000.0,
             dca_tranches: int | None = None):
    """按执行日 targets（目标仓位）模拟；targets 为执行日→目标权重。

    dca_tranches 非 None 时为定投模式：忽略 targets，每次执行日投入
    capital/tranches 现金买入，投完后持有不动。
    返回 (equity 日序列, 换手名义额合计, 调仓次数)。
    """
    dates = price.index
    cash, shares = capital, 0.0
    invested = 0
    equity = {}
    turnover = 0.0
    n_rebal = 0
    exec_map = dict(targets)
    for d in dates:
        px = price[d]
        if d in exec_map:
            if dca_tranches is not None:
                if invested < dca_tranches:
                    amt = capital / dca_tranches
                    buy = amt / (1 + COST)
                    cash -= amt
                    shares += buy / px
                    turnover += amt
                    invested += 1
                    n_rebal += 1
            else:
                tw = exec_map[d]
                eq = cash + shares * px
                want = tw * eq
                cur = shares * px
                trade_val = want - cur
                if trade_val > 0:  # 买入：付手续费
                    cost = trade_val * COST
                    cash -= trade_val + cost
                    shares += trade_val / px
                else:  # 卖出：卖出额里扣费
                    proceeds = -trade_val
                    cost = proceeds * COST
                    shares -= proceeds / px
                    cash += proceeds - cost
                turnover += abs(trade_val)
                n_rebal += 1
        cash = max(cash, 0.0)
        equity[d] = cash + shares * price[d]
    return pd.Series(equity).sort_index(), turnover, n_rebal


def metrics(equity: pd.Series) -> dict:
    rets = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1
    dd = (equity / equity.cummax() - 1).min()
    sharpe = rets.mean() / rets.std() * math.sqrt(252) if rets.std() > 0 else None
    return {
        "terminal": round(equity.iloc[-1], 0),
        "cagr": round(cagr, 4),
        "max_dd": round(dd, 4),
        "sharpe": round(sharpe, 3) if sharpe is not None else None,
        "start": str(equity.index[0]),
        "end": str(equity.index[-1]),
    }


def run_strategy_set(df: pd.DataFrame, label: str, breadth_col: str = "breadth",
                     freq: str = "W") -> dict:
    """df: index=date, columns=[breadth, close]。跑 S0-S3 + 变体。"""
    price = df["close"]
    # 信号日：每周（或每月）最后交易日；执行日 = 次一交易日
    if freq == "W":
        key = [f"{d.isocalendar()[0]}-{d.isocalendar()[1]:02d}" for d in df.index]
    else:
        key = [f"{d.year}-{d.month:02d}" for d in df.index]
    sig_days = (pd.Series(list(df.index)).groupby(key).last().tolist())
    dates = list(df.index)
    pos = dates.index(sig_days[0]) if sig_days else 0
    exec_days = {}
    for sd in sig_days:
        i = dates.index(sd)
        if i + 1 < len(dates):
            exec_days[dates[i + 1]] = sd  # 执行日→信号日宽度
    bmap = dict(zip(df.index, df[breadth_col]))

    n_weeks = len(sig_days)
    tranches = min(260, math.ceil(n_weeks / 2))

    results: dict[str, dict] = {}
    # S0
    eq0, _, _ = simulate(price, pd.Series({dates[0]: 1.0}), 1_000_000)
    # S0 也收 5bp 一次性买入成本：近似忽略（首日建仓成本 5bp 影响年化 <1bp/十年）
    results["S0_buyhold"] = {**metrics(eq0), "turnover": None, "n_rebal": 0}
    # S1 DCA
    eq1, to1, nr1 = simulate(price, pd.Series(dict.fromkeys(exec_days, 1.0)),
                             1_000_000, dca_tranches=tranches)
    results["S1_dca"] = {**metrics(eq1), "turnover": round(to1, 0), "n_rebal": nr1,
                         "tranches": tranches}
    # S2 变体
    for name, tiers in (("S2_v1", TIERS_V1), ("S2_v2", TIERS_V2), ("S2_v3", TIERS_V3)):
        tg = pd.Series({e: target_position(bmap[s], tiers) for e, s in exec_days.items()})
        eq, to, nr = simulate(price, tg, 1_000_000)
        results[name] = {**metrics(eq), "turnover": round(to, 0), "n_rebal": nr}
        results[name]["equity"] = eq
    # S3
    tg3 = pd.Series({e: (1.0 if bmap[s] <= 40 else 0.0) for e, s in exec_days.items()})
    eq3, to3, nr3 = simulate(price, tg3, 1_000_000)
    results["S3_binary"] = {**metrics(eq3), "turnover": round(to3, 0), "n_rebal": nr3}
    results["S3_binary"]["equity"] = eq3
    results["_exec_days"] = list(exec_days)
    return {"label": label, "breadth_col": breadth_col, "freq": freq,
            "n_signal_days": n_weeks, "results": results, "_df": df}


def slice_metrics(equity: pd.Series, lo, hi) -> dict:
    seg = equity[(equity.index >= pd.to_datetime(lo).date())
                 & (equity.index <= pd.to_datetime(hi).date())]
    seg = seg / seg.iloc[0]
    m = metrics(seg)
    m["terminal"] = round(float(seg.iloc[-1]), 4)  # 相对值（起点=1）
    return m


def yearly_returns(equity: pd.Series) -> dict:
    out = {}
    for y in sorted({d.year for d in equity.index}):
        seg = equity[[d.year == y for d in equity.index]]
        out[y] = round(float(seg.iloc[-1] / seg.iloc[0] - 1), 4)
    return out


def lag_years(eq2: pd.Series, eq0: pd.Series, topn=10) -> list:
    y2, y0 = yearly_returns(eq2), yearly_returns(eq0)
    rows = [{"year": y, "s2": y2[y], "s0": y0[y],
             "lag_pp": round((y2[y] - y0[y]) * 100, 1)}
            for y in y0 if y in y2]
    rows.sort(key=lambda r: r["lag_pp"])
    return rows[:topn]


def by_decade(equity: pd.Series) -> dict:
    out = {}
    for y0 in range(1986, 2027, 10):
        seg = equity[[d.year in range(y0, y0 + 10) for d in equity.index]]
        if len(seg) > 250:
            seg = seg / seg.iloc[0]
            m = metrics(seg)
            out[f"{y0}s"] = {k: m[k] for k in ("cagr", "max_dd")}
    return out


def missed_upside(eq2: pd.Series, eq0: pd.Series, topn=8) -> list:
    """S2 相对 S0 的落后段（S2/S0 比值自峰值回落 ≥8% 的区间）。"""
    ratio = (eq2 / eq0).dropna()
    peak = ratio.cummax()
    lag = ratio / peak - 1
    events, in_seg, seg_peak_date = [], False, None
    dates = list(ratio.index)
    for i, d in enumerate(dates):
        if not in_seg and lag[d] <= -0.08:
            in_seg = True
            seg_peak_date = ratio[:d].idxmax()
        elif in_seg and lag[d] >= -0.02:
            depth_d = lag[seg_peak_date:d].idxmin()
            events.append({
                "peak": str(seg_peak_date), "trough": str(depth_d),
                "end": str(d),
                "rel_lag": round(float(lag[depth_d]), 3),
                "idx_ret_over_seg": round(
                    float(eq0[depth_d] / eq0[seg_peak_date] - 1), 3),
            })
            in_seg = False
    if in_seg:
        depth_d = lag[seg_peak_date:].idxmin()
        events.append({"peak": str(seg_peak_date), "trough": str(depth_d),
                       "end": str(dates[-1]),
                       "rel_lag": round(float(lag[depth_d]), 3),
                       "idx_ret_over_seg": round(
                           float(eq0[depth_d] / eq0[seg_peak_date] - 1), 3)})
    events.sort(key=lambda e: e["rel_lag"])
    return events[:topn]


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = {"generated": "2026-08-27", "capital": 1_000_000, "cost_side_bp": 5}

    # ===== 任务一：美股长验证（B50，1986-03 → 2026-08）=====
    us_b = load_us_breadth()
    gspc = load_gspc_long()
    us = merge_breadth_price(us_b, gspc, "breadth_50")
    us_run = run_strategy_set(us, "US ^GSPC B50 1986-2026")
    eq0 = None
    res = us_run["results"]
    print("== 美股 S0-S3（周频，B50）==")
    for k in ("S0_buyhold", "S1_dca", "S2_v1", "S2_v2", "S2_v3", "S3_binary"):
        r = {kk: vv for kk, vv in res[k].items() if kk != "equity"}
        print(k, r)

    out["us"] = {
        "sample": res["S0_buyhold"]["start"] + " → " + res["S0_buyhold"]["end"],
        "weekly": {k: {kk: vv for kk, vv in v.items() if kk != "equity"}
                   for k, v in res.items() if k != "_exec_days"},
        "s2_v1_by_decade": by_decade(res["S2_v1"]["equity"]),
        "s0_by_decade": by_decade(res["S0_buyhold"].get("equity", res["S2_v1"]["equity"]))
        if "equity" in res["S0_buyhold"] else None,
        "missed_upside_s2v1_vs_s0": missed_upside(res["S2_v1"]["equity"],
                                                  res["S3_binary"]["equity"]),
    }
    # S0 equity：重算一次（S0 没存 equity）
    eq0_us, _, _ = simulate(us["close"], pd.Series({us.index[0]: 1.0}), 1_000_000)
    out["us"]["s0_by_decade"] = by_decade(eq0_us)
    out["us"]["missed_upside_s2v1_vs_s0"] = missed_upside(res["S2_v1"]["equity"], eq0_us)
    out["us"]["yearly_s0"] = yearly_returns(eq0_us)
    out["us"]["yearly_s2v1"] = yearly_returns(res["S2_v1"]["equity"])
    out["us"]["lag_years_top"] = lag_years(res["S2_v1"]["equity"], eq0_us)
    # 月频对照
    us_m = run_strategy_set(us, "US monthly", freq="M")
    out["us"]["monthly"] = {k: {kk: vv for kk, vv in v.items() if kk != "equity"}
                            for k, v in us_m["results"].items() if k != "_exec_days"}
    # 月度曲线落盘（S0/S1/S2v1/S3）
    curves = {"S0": eq0_us, "S1": res["S1_dca"].get("equity"),
              "S2_v1": res["S2_v1"]["equity"], "S3": res["S3_binary"]["equity"]}
    curves = {k: v for k, v in curves.items() if v is not None}
    pd.DataFrame({k: pd.Series(v.values, index=pd.to_datetime(list(v.index)))
                  .resample("ME").last()
                  for k, v in curves.items()}).to_csv(RAW_DIR / "us_monthly_equity.csv")

    # ===== 任务二：A 股（000300.SS，B50 基准 + B200 变体）=====
    cn_b = load_cn_breadth()
    csi = load_pool_close("000300.SS")
    cn = merge_breadth_price(cn_b, csi, "ma50_pct")
    cn_run = run_strategy_set(cn, "CN 000300 B50 2021-2026（短样本）")
    cres = cn_run["results"]
    print("\n== A 股 S0-S3（周频，B50，短样本 2021-06-18 起）==")
    for k in ("S0_buyhold", "S1_dca", "S2_v1", "S2_v2", "S2_v3", "S3_binary"):
        print(k, {kk: vv for kk, vv in cres[k].items() if kk != "equity"})

    cn200 = merge_breadth_price(cn_b, csi, "ma200_pct")
    cn200_run = run_strategy_set(cn200, "CN B200 variant")
    eq0_cn, _, _ = simulate(cn["close"], pd.Series({cn.index[0]: 1.0}), 1_000_000)

    # 2021-06→2024-02 阴跌段专项（注意：晚于 2021-02 峰，仅覆盖后半段）
    seg = {}
    for k in ("S2_v1", "S3_binary"):
        seg[k] = slice_metrics(cres[k]["equity"], "2021-06-18", "2024-02-29")
    seg["S0"] = slice_metrics(eq0_cn, "2021-06-18", "2024-02-29")
    # 2026 背离市逐月：宽度 + S2 仓位
    bmap = dict(zip(cn.index, cn["breadth"]))
    monthly_2026 = []
    eq2 = cres["S2_v1"]["equity"]
    tg = {}
    dates = list(cn.index)
    key = pd.Index([(d.year, d.month) for d in dates])
    # 用周频 exec_days 重算目标仓位序列（月表展示用）
    week_key = [f"{d.isocalendar()[0]}-{d.isocalendar()[1]:02d}" for d in dates]
    sig_days = pd.Series(dates).groupby(week_key).last().tolist()
    pos_by_date = {}
    for sd in sig_days:
        i = dates.index(sd)
        if i + 1 < len(dates):
            pos_by_date[dates[i + 1]] = target_position(bmap[sd], TIERS_V1)
    for (y, m) in sorted({(d.year, d.month) for d in dates if d.year == 2026}):
        md = [d for d in dates if d.year == y and d.month == m]
        b50_end = cn.loc[md[-1], "breadth"]
        b200_end = cn_b.loc[md[-1], "ma200_pct"] if md[-1] in cn_b.index else None
        pos_end = pos_by_date.get(md[-1])
        if pos_end is None:
            prev = [d for d in pos_by_date if d <= md[-1]]
            pos_end = pos_by_date[prev[-1]] if prev else None
        monthly_2026.append({"month": f"{y}-{m:02d}", "b50_end": round(b50_end, 1),
                             "b200_end": round(b200_end, 1) if b200_end else None,
                             "s2_target_pos": pos_end,
                             "s2_equity": round(float(eq2[md[-1]]), 0),
                             "s0_equity": round(float(eq0_cn[md[-1]]), 0)})
    # 2026 宽度极值
    b26 = cn.loc[[d for d in cn.index if d.year == 2026], "breadth"]
    b26200 = cn_b.loc[[d for d in cn_b.index if d.year == 2026], "ma200_pct"]

    out["cn"] = {
        "sample": cres["S0_buyhold"]["start"] + " → " + cres["S0_buyhold"]["end"],
        "short_sample_warning": "A 股宽度起点 2021-06-18，2021-02→2024-02 阴跌段仅覆盖后半段",
        "weekly_b50": {k: {kk: vv for kk, vv in v.items() if kk != "equity"}
                       for k, v in cres.items() if k != "_exec_days"},
        "weekly_b200": {k: {kk: vv for kk, vv in v.items() if kk != "equity"}
                        for k, v in cn200_run["results"].items() if k != "_exec_days"},
        "seg_2021_2024": seg,
        "monthly_2026": monthly_2026,
        "b50_2026_max_min": [round(float(b26.max()), 1), round(float(b26.min()), 1),
                             str(b26.idxmax()), str(b26.idxmin())],
        "b200_2026_max_min": [round(float(b26200.max()), 1), round(float(b26200.min()), 1),
                              str(b26200.idxmax()), str(b26200.idxmin())],
        "by_year_s2v1": by_decade(cres["S2_v1"]["equity"]),
        "by_year_s0": by_decade(eq0_cn),
    }
    pd.DataFrame({"S0": eq0_cn, "S2_v1": cres["S2_v1"]["equity"],
                  "S3": cres["S3_binary"]["equity"]}).to_csv(
        RAW_DIR / "cn_monthly_equity.csv")

    # 判定（事前标准）
    m0, m2 = res["S0_buyhold"], res["S2_v1"]
    out["us"]["verdict"] = {
        "s2_dd_le_0.75x_s0": m2["max_dd"] >= m0["max_dd"] * 0.75,
        "s2_cagr_ge_0.85x_s0": m2["cagr"] >= 0.85 * m0["cagr"],
        "s2_beats_dca_E5": m2["terminal"] >= res["S1_dca"]["terminal"],
    }
    c0, c2 = cres["S0_buyhold"], cres["S2_v1"]
    out["cn"]["verdict"] = {
        "s2_dd_improve_30pct": c2["max_dd"] >= c0["max_dd"] * 0.70,
        "s2_terminal_ge_0.9x_s0": c2["terminal"] >= 0.90 * c0["terminal"],
    }

    with open(RAW_DIR / "breadth_position_results.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print("\nVerdict US:", out["us"]["verdict"])
    print("Verdict CN:", out["cn"]["verdict"])
    print("missed upside (top):", out["us"]["missed_upside_s2v1_vs_s0"][:3])
    print("CN 2026 monthly:")
    for row in monthly_2026:
        print(row)
    print("raw →", RAW_DIR / "breadth_position_results.json")


if __name__ == "__main__":
    main()
