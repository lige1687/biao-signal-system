"""Audit frozen fast-reentry cycles without rerunning or changing the strategy."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
EXEC = ROOT / "docs/experiments/raw/research-mixed-pool-audit-2026-09-09/dedup-execution"
DATA = ROOT / "docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    protocol_path = ROOT / "docs/experiments/raw/research-mixed-evaluation-2026-09-09/protocol.json"
    protocol_sha_path = protocol_path.with_suffix(".sha256")
    if sha256(protocol_path) != protocol_sha_path.read_text().split()[0]:
        raise AssertionError("protocol hash mismatch")
    sources = [EXEC / x for x in ("trades.csv", "signals.csv", "actions.csv", "reentry_events.csv", "per_symbol.csv")]
    sources += [ROOT / "docs/experiments/raw/research-mixed-evaluation-2026-09-09/protocol.json",
                ROOT / "docs/experiments/raw/research-mixed-evaluation-2026-09-09/protocol.sha256",
                ROOT / "docs/research/experiment-backtest-principles.md",
                ROOT / "docs/research/experiment-report-template.md"]
    sources += [DATA / "prices.csv", DATA / "action-sources/normalized-actions.json"]
    before = {str(p): sha256(p) for p in sources}

    trades = pd.read_csv(EXEC / "trades.csv", dtype={"symbol": str})
    signals = pd.read_csv(EXEC / "signals.csv", dtype={"selected": str})
    reentry_events = pd.read_csv(EXEC / "reentry_events.csv", dtype={"symbol": str})
    prices = pd.read_csv(DATA / "prices.csv", dtype={"symbol": str})
    prices["symbol"] = prices.symbol.str.split(".").str[0]
    raw_actions = json.loads((DATA / "action-sources/normalized-actions.json").read_text())["events"]
    actions = []
    for a in raw_actions:
        b = dict(a)
        b["symbol"] = str(a["symbol"]).split(".")[0]
        b["type"] = a.get("type") or a.get("action_type")
        b["cash"] = float(a.get("cash", a.get("cash_per_share", a.get("cash_per_unit", 0))) or 0)
        b["ratio"] = float(a.get("ratio", a.get("split_ratio", 1)) or 1)
        b["effective_date"] = a.get("effective_date") or a.get("ex_date")
        actions.append(b)

    rows = []
    dividend_rows = []
    for aid in sorted(x for x in trades.account_id.unique() if x.startswith("fast_reentry_exit")):
        fee_rate = float(aid.rsplit("fee", 1)[1])
        tt = trades[trades.account_id == aid].reset_index(drop=True)
        monthly = sorted(signals[(signals.account_id == aid) & signals.opening_equity.notna()].eligible_date.unique())
        monthly = sorted(signals[(signals.account_id == aid) & signals.opening_equity.notna()].eligible_date.unique())
        for i, buy in tt.iterrows():
            if buy.side != "buy" or buy.reason != "fast_reentry":
                continue
            monthly_boundary = next((d for d in monthly if d > buy.date), None)
            later = tt[(tt.index > i) & (tt.symbol == buy.symbol) & (tt.side == "sell") & (tt.reason == "stop")]
            if monthly_boundary is not None:
                later = later[later.date < monthly_boundary]
            stop = None if later.empty else later.iloc[0]
            boundary = stop.date if stop is not None else monthly_boundary
            end_reason = "stop" if stop is not None else "monthly_reset"
            if boundary is None:
                raise AssertionError(f"no completed cycle boundary: {aid} {buy.symbol} {buy.date}")
            qty = float(buy.qty)
            original_qty = qty
            cycle_dividend = 0.0
            paid_by_boundary = 0.0
            receivable_at_boundary = 0.0
            cycle_actions = []
            for a in sorted((x for x in actions if x["symbol"] == buy.symbol), key=lambda x: (x.get("effective_date") or "", x.get("event_id") or "")):
                effective = a.get("effective_date") or ""
                if not (buy.date < effective <= boundary):
                    continue
                if a["type"] == "split":
                    qty *= a["ratio"]
                    cycle_actions.append(f"split:{effective}:x{a['ratio']}")
                elif a["type"] == "cash_dividend":
                    record = a.get("record_date") or effective
                    # The position must exist at record-date close; boundary is before its opening.
                    if buy.date <= record < boundary:
                        amount = qty * a["cash"]
                        cycle_dividend += amount
                        paid = bool(a.get("pay_date") and a["pay_date"] < boundary)
                        paid_by_boundary += amount if paid else 0.0
                        receivable_at_boundary += 0.0 if paid else amount
                        dividend_rows.append(dict(account_id=aid, reentry_date=buy.date, symbol=buy.symbol,
                            event_id=a.get("event_id"), record_date=record, ex_date=effective,
                            pay_date=a.get("pay_date"), entitled_units=qty, cash_per_unit=a["cash"],
                            amount=amount, status_at_boundary="paid" if paid else "receivable",
                            boundary_date=boundary))
                        cycle_actions.append(f"dividend:{effective}:{amount:.6f}")

            buy_out = float(buy.notional + buy.fee)
            fills = reentry_events[(reentry_events.account_id == aid) & (reentry_events.symbol == buy.symbol) &
                                   (reentry_events.date == buy.date) & (reentry_events.event == "reentry_filled")]
            if len(fills) != 1:
                raise AssertionError(f"expected one reentry event: {aid} {buy.symbol} {buy.date}")
            source_budget = float(fills.iloc[0].net_budget)
            if buy_out > source_budget + 1e-6:
                raise AssertionError(f"reentry exceeded stop budget: {aid} {buy.symbol} {buy.date}")
            if end_reason == "stop":
                sells = tt[(tt.index > i) & (tt.symbol == buy.symbol) & (tt.side == "sell") &
                           (tt.reason == "stop") & (tt.date == boundary)]
                if len(sells) != 1:
                    raise AssertionError(f"expected one stop: {aid} {buy.symbol} {buy.date}")
                sell = sells.iloc[0]
                if abs(float(sell.qty) - qty) > 1e-8:
                    raise AssertionError(f"cycle quantity mismatch: {aid} {buy.symbol} {buy.date}")
                exit_price = float(sell.price)
                exit_notional = float(sell.notional)
                exit_fee = float(sell.fee)
                terminal_value = exit_notional - exit_fee
            else:
                px = prices[(prices.symbol == buy.symbol) & (prices.date == boundary)]
                if len(px) != 1 or pd.isna(px.iloc[0].open) or float(px.iloc[0].open) <= 0:
                    raise AssertionError(f"missing boundary open: {aid} {buy.symbol} {boundary}")
                exit_price = float(px.iloc[0].open)
                exit_notional = qty * exit_price
                exit_fee = 0.0
                terminal_value = exit_notional
            pnl = terminal_value + cycle_dividend - buy_out
            rows.append(dict(account_id=aid, fee_rate=fee_rate, symbol=buy.symbol,
                reentry_date=buy.date, boundary_date=boundary, end_reason=end_reason,
                initial_units=original_qty, terminal_units=qty, entry_price=float(buy.price),
                buy_notional=float(buy.notional), buy_fee=float(buy.fee), cash_invested=buy_out,
                source_stop_net_budget=source_budget, unused_stop_budget=source_budget-buy_out,
                exit_or_mark_price=exit_price, exit_notional_or_mark=exit_notional,
                exit_fee=exit_fee, terminal_net_value=terminal_value,
                dividend_entitlement=cycle_dividend, dividend_paid_by_boundary=paid_by_boundary,
                dividend_receivable_at_boundary=receivable_at_boundary,
                net_pnl=pnl, net_return=pnl / buy_out, actions="|".join(cycle_actions),
                outcome="positive" if pnl > 0 else ("negative" if pnl < 0 else "flat")))

    cycles = pd.DataFrame(rows).sort_values(["account_id", "reentry_date", "symbol"])
    if cycles.groupby("account_id").size().to_dict() != {"fast_reentry_exit-fee0.001": 48, "fast_reentry_exit-fee0.002": 48}:
        raise AssertionError("expected 48 cycles per fee")
    summary = cycles.groupby(["account_id", "fee_rate", "end_reason", "outcome"], as_index=False).agg(
        cycles=("symbol", "size"), cash_invested=("cash_invested", "sum"),
        buy_fees=("buy_fee", "sum"), exit_fees=("exit_fee", "sum"),
        dividends=("dividend_entitlement", "sum"), net_pnl=("net_pnl", "sum"))
    summary["aggregate_return_on_cycle_cash"] = summary.net_pnl / summary.cash_invested
    by_symbol = cycles.groupby(["account_id", "fee_rate", "symbol"], as_index=False).agg(
        cycles=("symbol", "size"), cash_invested=("cash_invested", "sum"),
        dividends=("dividend_entitlement", "sum"), net_pnl=("net_pnl", "sum"))
    by_symbol["aggregate_return_on_cycle_cash"] = by_symbol.net_pnl / by_symbol.cash_invested

    cycles.to_csv(HERE / "cycles.csv", index=False)
    dividend_columns = ["account_id", "reentry_date", "symbol", "event_id", "record_date", "ex_date",
                        "pay_date", "entitled_units", "cash_per_unit", "amount", "status_at_boundary", "boundary_date"]
    pd.DataFrame(dividend_rows, columns=dividend_columns).to_csv(HERE / "cycle-dividends.csv", index=False)
    summary.to_csv(HERE / "summary.csv", index=False)
    by_symbol.to_csv(HERE / "by-symbol.csv", index=False)
    account_symbols = pd.read_csv(EXEC / "per_symbol.csv")
    account_symbols = account_symbols[account_symbols.account_id.str.startswith("fast_reentry_exit")].copy()
    account_symbols.to_csv(HERE / "account-profit-by-symbol.csv", index=False)
    bridge = account_symbols.groupby("account_id", as_index=False).net_pnl.sum().rename(columns={"net_pnl": "account_total_profit"})
    local = cycles.groupby("account_id", as_index=False).net_pnl.sum().rename(columns={"net_pnl": "reentry_cycle_local_pnl"})
    bridge = bridge.merge(local, on="account_id")
    bridge["local_pnl_over_account_profit"] = bridge.reentry_cycle_local_pnl / bridge.account_total_profit
    bridge["interpretation"] = "局部持有周期算术占比，不是快速回补相对其他策略的因果贡献"
    bridge.to_csv(HERE / "account-profit-bridge.csv", index=False)
    after = {str(p): sha256(p) for p in sources}
    if before != after:
        raise AssertionError("frozen source changed during audit")
    (HERE / "source-lock.json").write_text(json.dumps({"before": before, "after": after, "unchanged": True}, indent=2) + "\n")


if __name__ == "__main__":
    main()
