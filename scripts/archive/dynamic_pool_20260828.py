"""动态入池系统回测——用户方向：什么标的何时凭什么标准进入组合池。

预注册协议（2026-08-28）：
- 股票池：全部可用 A 股标的（指数+ETF，隔离区/排除名单除外）
- 入池标准主指标：RS120（标的120日收益 − 全A等权120日收益）
- 调仓：每月末排名，次日起持有；等权；费用=换手×10bp（单边）
- 变体（不挑选，全展示）：
    T5 = RS120 前5名 | T3 = 前3名 | B5 = 后5名（对照：若A股动量反效则B5胜）
    T5G = 前5名 + 宽度闸（全A B200<43.3 时空仓避险）
- 基准：全A等权 | 静态8指数持有 | 静态8指数冠军组合（第19轮口径）
- 通过线（预注册）：任一变体年化 ≥ 全A等权+3pp 且回撤 ≤ 静态持有组合。
先验警告：A股月频动量在文献上普遍弱/反转，此实验一半目的是验证这个先验。
起点 2013-01（股票池 ≥5 只存活），同报 2015-06 共同窗口。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from lei_signal.timing_backtest.data import (
    INSTRUMENTS,
    TIMING_CACHE_DIR,
    align_index_breadth,
    load_breadth,
    load_index_bars,
)
from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import compute_performance
from lei_signal.timing_backtest.strategies import LadderParams, TrendGate, build_target

EXCLUDED = {"159819", "980017", "510500", "000932", "518880", "^GSPC", "^IXIC", "SPY", "QQQ"}
LADDER = LadderParams(
    indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
    min_weight=0.0, gamma=1.0, low_edge=30.0, high_edge=70.0,
)
STATIC8 = ["399006", "399975", "399976", "399997", "000819", "399986", "980030", "000300"]
FEE = 0.001  # 单边 10bp


def perf(eq: pd.Series) -> str:
    p = compute_performance(eq)
    return f"年化{p['cagr']:+6.1%}/回撤{p['mdd']:5.0%}/Calmar{p['calmar']:5.2f}"


def rotation(closes: dict[str, pd.Series], rs: pd.DataFrame, ew: pd.Series,
             k: int, bottom: bool, gate: pd.Series | None) -> pd.Series:
    """月末排名 → 次日起持有 Top/Bot-K 等权至下次调仓，换手×10bp 费用。"""
    master = ew.index
    rets = pd.DataFrame(
        {s: c.reindex(master).ffill().pct_change().fillna(0) for s, c in closes.items()}
    )
    month_ends = master.to_series().groupby(master.to_period("M")).tail(1)
    w = pd.DataFrame(0.0, index=master, columns=rs.columns)
    turnover = pd.Series(0.0, index=master)
    held: list[str] = []
    for d in month_ends:
        i = master.get_loc(d)
        if i + 1 >= len(master):
            break
        row = rs.loc[d].dropna()
        elig = [s for s in row.index if len(closes[s].loc[:d].dropna()) >= 250]
        if not elig:
            continue
        ranked = row.loc[elig].sort_values(ascending=bottom)
        pick = list(ranked.index[:k])
        names = pick if gate is None or bool(gate.loc[d]) else []
        w_old = pd.Series(0.0, index=w.columns)
        if held:
            w_old[held] = 1.0 / len(held)
        w_new = pd.Series(0.0, index=w.columns)
        if names:
            w_new[names] = 1.0 / len(names)
        nxt = master[i + 1]
        w.loc[nxt:] = w_new.values
        turnover.loc[nxt] = float((w_new - w_old).abs().sum())
        held = names
    gross = (w.shift(1).fillna(0.0) * rets).sum(axis=1)
    net = gross - turnover.shift(1).fillna(0.0) * FEE
    return (1 + net).cumprod()


def main() -> None:
    wide = pd.read_parquet(TIMING_CACHE_DIR.parent / "a_share_klines_full.parquet")
    ew = (1 + wide.pct_change(fill_method=None).mean(axis=1, skipna=True).fillna(0)).cumprod()
    closes: dict[str, pd.Series] = {}
    for sym, spec in INSTRUMENTS.items():
        if sym in EXCLUDED or spec.market != "cn":
            continue
        try:
            closes[sym] = load_index_bars(sym)["close"]
        except Exception:  # noqa: BLE001 - 隔离区/缺数据跳过
            continue
    master = ew.index
    rs = pd.DataFrame(index=master)
    for sym, c in closes.items():
        c2 = c.reindex(master)
        rs[sym] = (c2 / c2.shift(120) - ew / ew.shift(120)) * 100
    b200 = load_breadth("cn_all")["b200"].reindex(master)
    gate = b200 >= 43.3

    start = pd.Timestamp("2013-01-01")
    eqs = {
        "T5·RS前5": rotation(closes, rs, ew, 5, False, None),
        "T3·RS前3": rotation(closes, rs, ew, 3, False, None),
        "B5·RS后5(对照)": rotation(closes, rs, ew, 5, True, None),
        "T5G·前5+宽度闸": rotation(closes, rs, ew, 5, False, gate),
        "全A等权": ew,
    }
    # 静态8：持有组合 + 冠军组合（复用第19轮口径）
    hold_r, champ_r = [], []
    for sym in STATIC8:
        aligned = align_index_breadth(load_index_bars(sym), load_breadth("cn_all"))
        budget = build_target(aligned, LADDER, None, TrendGate(), aligned.iloc[:0])
        res = simulate(aligned, budget, fee_bps=10.0, cash_rate=0.0, min_trade=0.05)
        r = res.daily["equity"].pct_change().fillna(0)
        res2 = simulate(aligned, pd.Series(1.0, index=aligned.index), fee_bps=10.0,
                        cash_rate=0.0, min_trade=0.05)
        champ_r.append(r)
        hold_r.append(res2.daily["equity"].pct_change().fillna(0))
    eqs["静态8·持有"] = (1 + pd.concat(hold_r, axis=1).mean(axis=1)).cumprod()
    eqs["静态8·冠军"] = (1 + pd.concat(champ_r, axis=1).mean(axis=1)).cumprod()

    wins = [("起点2013-01", start, None), ("共同窗口2015-06", pd.Timestamp("2015-06-16"), None),
            ("2015股灾", pd.Timestamp("2015-06-01"), pd.Timestamp("2016-02-29")),
            ("2018阴跌", pd.Timestamp("2018-01-01"), pd.Timestamp("2019-01-31")),
            ("本轮科技牛", pd.Timestamp("2024-09-20"), None)]
    names = "、".join(INSTRUMENTS[s].name for s in list(closes)[:6])
    print(f"股票池 {len(closes)} 只（{names} …）")
    for wtag, s, e in wins:
        print(f"\n[{wtag}]")
        for name, eq in eqs.items():
            seg = eq.loc[s:e].dropna()
            seg = seg / seg.iloc[0]
            print(f"  {name:<14} {perf(seg)}")


if __name__ == "__main__":
    main()
