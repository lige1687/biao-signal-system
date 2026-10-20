"""Combine repeated reentries for one symbol within one monthly-list validity period."""
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
EXEC = HERE.parents[1] / "research-mixed-defense-2026-09-09/execution"


def main():
    cycles = pd.read_csv(HERE / "cycles.csv", dtype={"symbol": str})
    signals = pd.read_csv(EXEC / "signals.csv")
    rows = []
    for aid, g in cycles.groupby("account_id"):
        month_exec = sorted(signals[(signals.account_id == aid) & signals.opening_equity.notna()].eligible_date.unique())
        z = g.copy()
        z["period_start"] = z.reentry_date.map(lambda d: max(x for x in month_exec if x <= d))
        z["period_end"] = z.period_start.map(lambda d: next((x for x in month_exec if x > d), ""))
        for (symbol, start, end), q in z.groupby(["symbol", "period_start", "period_end"], dropna=False):
            q = q.sort_values("reentry_date")
            initial_cash = float(q.iloc[0].cash_invested)
            pnl = float(q.net_pnl.sum())
            rows.append(dict(account_id=aid, fee_rate=float(q.iloc[0].fee_rate), symbol=symbol,
                monthly_period_start=start, monthly_period_end=end, reentry_count=len(q),
                first_reentry_date=q.iloc[0].reentry_date, final_boundary_date=q.iloc[-1].boundary_date,
                final_end_reason=q.iloc[-1].end_reason, initial_cash_committed=initial_cash,
                turnover_cash_invested=float(q.cash_invested.sum()), buy_fees=float(q.buy_fee.sum()),
                exit_fees=float(q.exit_fee.sum()), dividends=float(q.dividend_entitlement.sum()),
                episode_net_pnl=pnl, episode_return_on_initial_cash=pnl/initial_cash,
                cycle_dates="|".join(q.reentry_date), cycle_end_reasons="|".join(q.end_reason)))
    out = pd.DataFrame(rows).sort_values(["account_id", "monthly_period_start", "symbol"])
    out.to_csv(HERE / "episodes.csv", index=False)
    lines = ["# 同一月度名单内的连续回补阶段", "",
             "同一标的在同一次月度名单有效期间可能止损后再次回补，因此多次回补不是彼此独立的交易机会。阶段损益为内部各段现金流损益之和；阶段回报用首次回补投入现金作分母，`turnover_cash_invested`只表示资金被重复投入的周转量。", ""]
    for aid, q in out.groupby("account_id"):
        lines += [f"## {aid}", "", f"49次回补合并为{len(q)}个标的月份阶段，其中{int((q.reentry_count>1).sum())}个阶段包含多次回补。", "",
                  "| 类别 | 标的 | 月度有效期 | 回补次数 | 阶段净损益 | 相对首次投入 |", "|---|---:|---:|---:|---:|---:|"]
        picks = pd.concat([q.nsmallest(3, "episode_net_pnl").assign(kind="最差"), q.nlargest(3, "episode_net_pnl").assign(kind="最好")])
        for _, r in picks.iterrows():
            lines.append(f"| {r.kind} | {r.symbol} | {r.monthly_period_start}至{r.monthly_period_end} | {r.reentry_count} | {r.episode_net_pnl:,.2f} | {r.episode_return_on_initial_cash:.2%} |")
        lines.append("")
    (HERE / "episodes-summary.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
