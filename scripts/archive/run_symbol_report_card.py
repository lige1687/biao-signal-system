"""全标的逐个成绩单：单标的完整系统（宽度预算×模块信号）vs 买入持有。

用户口径（2026-08-27 第八轮，事前写死）：
- 按单独标的算（用户明确要求账户级没法看）：每个实际成交标的一条
  独立成绩线，与同窗买入持有对比。
- 仓位层（分账规则，沿用已定方向）：ETF 腿 = B200 五档(h_80 版)
  调入场预算；518850 黄金豁免（用户拍板）；个股腿不上闸（乘数 1.0）。
- 买卖点 = 该标的的模块信号时间线（A 门禁/B'/C/D，标的内去重叠）。
- 指标：笔数 / 累计R（风险归一，跨标的可比）/ 胜率 / 平均持仓 /
  年化（1% 单笔风险口径）/ 最大回撤 / 同窗 BH 年化与回撤 /
  回撤改善（STRAT dd − BH dd）。
- 判定：无（成绩单展示）。1% 风险口径下单标的账户大部分时间持币，
  年化天然低于满仓 BH——比较策略质量看累计R 与回撤，年化仅供规模感。

输出：raw/breadth_overlay/symbol_report_card.csv（全量 71 标的）
复现：python3 scripts/run_symbol_report_card.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from run_breadth_overlay import load_breadth  # noqa: E402
from run_full_stack_sim import gate_a, load_runs  # noqa: E402
from run_symbol_showcase import (  # noqa: E402
    cagr_dd,
    sim_bh,
    sim_strat,
    strat_trades,
)

from lei_signal.backtest.full_sim import (  # noqa: E402
    cap_fn_from_map,
    position_cap_map,
)
from lei_signal.backtest.runner import load_pool_frames  # noqa: E402

RAW = REPO / "docs/experiments/raw/breadth_overlay"
GOLD = "518850.SS"
H80 = ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.5), (999, 0.25))


def main() -> None:
    runs = load_runs(rerun=False)
    br = load_breadth()
    b200_map = {str(d.date()): float(v)
                for d, v in br["ma200_pct"].items()}
    cap_h80 = cap_fn_from_map(position_cap_map(b200_map, H80))
    frames = load_pool_frames()

    pool = gate_a(runs["A"]) + runs["B'"] + runs["C"] + runs["D"]
    symbols = sorted({t["symbol"] for t in pool
                      if t["exit_date"] and t["symbol"] in frames})
    rows = []
    for sym in symbols:
        bars = frames[sym]
        tr = strat_trades(runs, sym)
        if not tr:
            continue
        is_etf = sym.split(".")[0].startswith(("51", "56", "58", "159"))
        gated = is_etf and sym != GOLD  # ETF 上闸，黄金豁免，个股无闸
        # 逐日乘数表（B200 五档 h_80，周频信号已在 map 内 t+1 生效）
        smap = ({str(d.date()): min(1.0, cap_h80(str(d.date())))
                 for d in bars.index} if gated else {})
        eq, n, cum_r = sim_strat(bars, tr, smap)
        bh = cagr_dd(sim_bh(bars))
        m = cagr_dd(eq)
        wins = sum(1 for t in tr if t["r_net"] > 0)
        hold = sum((pd.Timestamp(t["exit_date"]) - pd.Timestamp(t["entry_date"])
                    ).days for t in tr) / len(tr)
        rows.append({"symbol": sym, "is_etf": is_etf, "gated": gated,
                     "n": n, "cum_R": cum_r, "win": round(wins / len(tr), 2),
                     "avg_hold_d": round(hold, 0), "final": m["final"],
                     "cagr": m["cagr"], "max_dd": m["max_dd"],
                     "bh_cagr": bh["cagr"], "bh_dd": bh["max_dd"],
                     "dd_improve": round((m["max_dd"] - bh["max_dd"]) * 100, 1),
                     "span": f"{bars.index[0].date()}→{bars.index[-1].date()}"})
    df = pd.DataFrame(rows)
    df.to_csv(RAW / "symbol_report_card.csv", index=False)
    # 汇总打印
    print(f"\n标的数 {len(df)}（ETF {int(df['is_etf'].sum())} / "
          f"个股 {int((~df['is_etf']).sum())}）")
    pos = (df["cum_R"] > 0).mean()
    print(f"累计R>0 占比 {pos:.0%}；R 中位数 {df['cum_R'].median():+.1f}；"
          f"回撤改善中位数 {df['dd_improve'].median():+.1f}pp")
    cols = ["symbol", "n", "cum_R", "win", "cagr", "max_dd",
            "bh_cagr", "bh_dd", "dd_improve"]
    print("\n=== 累计R 前 15 ===")
    print(df.sort_values("cum_R", ascending=False)[cols].head(15)
          .to_string(index=False))
    print("\n=== 累计R 后 10 ===")
    print(df.sort_values("cum_R")[cols].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
