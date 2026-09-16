#!/usr/bin/env python3
"""中间地带宽度择时研究（用户问题 2026-09-07）。

用户问题：宽度指标和价格相关性高，但不在机会位(≤20)/压力位(≥80)的时候
不知道何时买卖，导致利润跑掉或亏损。中间地带有没有可操作的规则？

检验的策略族（全部当日收盘信号、次日收盘执行、双边费率各 10bp）：
- 持有不动作基准；
- 极值反转（用户已有认知）：b50≤20 买、≥80 卖——只能抓极端，中间裸奔；
- 扩散确认/收窄退出（穿越）：b50 上穿 X 买（上涨家数扩散）、下穿 Y 卖
  （上涨面收窄），X∈{35,40,45,50}、Y∈{55,60,65}，要求 X<Y；
- 混合：≤20 抄底买 + 上穿40 右侧买 + 下穿60 卖；
- 宽度动量：b50 5日变化>+5 买 / <-5 卖。

评估：年化、最大回撤、回撤/收益性价比、交易数、在场时间比；
整体(2005-2026) + 近三年 + 分年胜率（跑赢买入持有的年份占比）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from lei_signal.timing_backtest.data import align_index_breadth, load_breadth, load_index_bars  # noqa: E402

FEE = 0.001  # 单边 10bp
START = "2005-01-01"  # b200 预热后


def run_strategy(aligned: pd.DataFrame, sig: pd.Series) -> dict:
    """sig=目标仓位(0/1，当日收盘可得)→次日收盘执行。返回绩效指标。"""
    px = aligned["close"]
    ret = px.pct_change().fillna(0)
    pos = sig.shift(1).fillna(0.0)  # 次日生效
    # 调仓日扣双边费（仓位变化部分）
    turnover = pos.diff().abs().fillna(pos.abs())
    strat = pos * ret - turnover * FEE
    eq = (1 + strat).cumprod()
    bh = (1 + ret).cumprod()

    yrs = len(eq) / 244
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    bh_cagr = bh.iloc[-1] ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    bh_dd = (bh / bh.cummax() - 1).min()
    trades = int((pos.diff().abs() > 0.5).sum())
    time_in = float(pos.mean())

    # 分年是否跑赢基准
    yearly = eq.resample("YE").last().pct_change()
    yearly_bh = bh.resample("YE").last().pct_change()
    first = True
    beats = []
    for d, r in yearly.items():
        if first:
            first = False
            continue
        rb = yearly_bh.get(d)
        if rb is not None and not (pd.isna(r) or pd.isna(rb)):
            beats.append(r > rb)
    return {
        "cagr": round(cagr * 100, 2), "bh_cagr": round(bh_cagr * 100, 2),
        "mdd": round(dd * 100, 1), "bh_mdd": round(bh_dd * 100, 1),
        "calmar": round(abs(cagr / dd), 2) if dd else None,
        "bh_calmar": round(abs(bh_cagr / bh_dd), 2) if bh_dd else None,
        "trades": trades, "time_in": round(time_in * 100, 0),
        "years_beat_bh": f"{sum(beats)}/{len(beats)}",
    }


def main() -> None:
    aligned = align_index_breadth(load_index_bars("000300"), load_breadth("cn_all"))
    aligned = aligned.loc[START:]
    b50 = aligned["b50"]
    results: dict[str, dict] = {}

    # 1) 持有不动作由 run_strategy 的 bh 字段承担
    # 2) 极值反转
    sig = pd.Series(np.where(b50 <= 20, 1.0, np.where(b50 >= 80, 0.0, np.nan)), index=b50.index).ffill().fillna(0.0)
    results["极值反转(20买/80卖)"] = run_strategy(aligned, sig)

    # 3) 穿越族（缓冲带状态机：宽度升破 B=扩散确认→买；跌破 S=收窄退出→卖；
    #    [S,B] 之间持有不动。B>S 才是有效缓冲带，B<S 会让买卖区重叠失效）
    def _cross_sig(s: pd.Series, buy_th: float, sell_th: float) -> pd.Series:
        out = pd.Series(0.0, index=s.index)
        holding = False
        for i, v in enumerate(s):
            if not pd.isna(v):
                if v > buy_th:
                    holding = True
                elif v < sell_th:
                    holding = False
            out.iloc[i] = 1.0 if holding else 0.0
        return out

    for bth in (50, 55, 60, 65):
        for sth in (30, 35, 40, 45):
            if bth <= sth:
                continue
            results[f"缓冲带(升破{bth}买/跌破{sth}卖)"] = run_strategy(aligned, _cross_sig(b50, bth, sth))

    # 4) 混合：缓冲带(60买/40卖) 之外，≤20 额外抄底买、≥80 额外清仓
    def _blend_sig(s: pd.Series) -> pd.Series:
        out = pd.Series(0.0, index=s.index)
        holding = False
        for i, v in enumerate(s):
            if pd.isna(v):
                out.iloc[i] = 1.0 if holding else 0.0
                continue
            if v <= 20 or v > 60:
                holding = True
            elif v >= 80:
                holding = False
            elif v < 40:
                holding = False
            out.iloc[i] = 1.0 if holding else 0.0
        return out
    results["混合(≤20抄底+升破60买/跌破40卖)"] = run_strategy(aligned, _blend_sig(b50))

    # 5) 宽度动量：b50 5日变化
    mom = b50.diff(5)
    state = pd.Series(np.nan, index=b50.index)
    state[mom > 5] = 1.0
    state[mom < -5] = 0.0
    results["宽度动量(5日+5买/-5卖)"] = run_strategy(aligned, state.ffill().fillna(0.0))

    df = pd.DataFrame(results).T
    print("=== 沪深300 × 全A宽度b50 全样本 2005-01 → 2026-08 ===")
    print(df.to_string())

    # 近三年子样本
    al3 = aligned.loc["2023-09-01":]
    b3 = al3["b50"]
    r3: dict[str, dict] = {}
    sig = pd.Series(np.where(b3 <= 20, 1.0, np.where(b3 >= 80, 0.0, np.nan)), index=b3.index).ffill().fillna(0.0)
    r3["极值反转"] = run_strategy(al3, sig)
    r3["缓冲带(60买/40卖)"] = run_strategy(al3, _cross_sig(b3, 60, 40))
    r3["缓冲带(55买/35卖)"] = run_strategy(al3, _cross_sig(b3, 55, 35))
    print("\n=== 近三年 2023-09 → 2026-08 ===")
    print(pd.DataFrame(r3).T.to_string())


if __name__ == "__main__":
    main()
