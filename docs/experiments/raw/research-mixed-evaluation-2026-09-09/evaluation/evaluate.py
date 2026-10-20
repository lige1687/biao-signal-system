from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[5]
BATCH = ROOT / "docs/experiments/raw/research-mixed-evaluation-2026-09-09"
OUT = BATCH / "evaluation"
SOURCE = ROOT / "docs/experiments/raw/research-mixed-pool-audit-2026-09-09/dedup-execution"
PRICES = ROOT / "docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation/prices.csv"
INITIAL = 1_000_000.0
YEAR_DAYS = 365.2425


def write_csv(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def max_drawdown(values: list[float]) -> float:
    peak = values[0]
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        worst = min(worst, value / peak - 1.0)
    return worst


def recovery_stats(rows: pd.DataFrame) -> dict:
    points = [(date(2020, 12, 1), INITIAL)] + list(zip(rows.date.dt.date, rows.equity))
    peak_value = points[0][1]
    peak_date = points[0][0]
    open_peak = None
    completed = []
    for day, value in points[1:]:
        if value >= peak_value - 1e-9:
            if open_peak is not None:
                completed.append((open_peak, day, (day - open_peak).days))
                open_peak = None
            if value > peak_value + 1e-9:
                peak_value, peak_date = value, day
        elif open_peak is None:
            open_peak = peak_date
    longest = max(completed, key=lambda x: x[2])
    end = points[-1][0]
    return {
        "longest_peak_date": str(longest[0]),
        "longest_recovery_date": str(longest[1]),
        "longest_recovery_days": longest[2],
        "unrecovered_at_end": open_peak is not None,
        "end_unrecovered_peak_date": str(open_peak) if open_peak else "",
        "end_unrecovered_days": (end - open_peak).days if open_peak else 0,
    }


def main() -> None:
    protocol = json.loads((BATCH / "protocol.json").read_text())
    for rel, expected in protocol["source_files"].items():
        actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"source hash changed: {rel}")

    equity = pd.read_csv(SOURCE / "equity.csv", parse_dates=["date"])
    trades = pd.read_csv(SOURCE / "trades.csv", parse_dates=["date"])
    actions = pd.read_csv(SOURCE / "actions.csv", parse_dates=["date"])
    prices = pd.read_csv(PRICES, parse_dates=["date"])
    prices["symbol"] = prices.symbol.str.split(".").str[0]
    close = {(r.date.date(), r.symbol): float(r.close) for r in prices.itertuples()}

    windows = {
        "early": (date(2020, 12, 1), date(2024, 12, 31)),
        "late": (date(2025, 1, 1), date(2026, 6, 30)),
        "full": (date(2020, 12, 1), date(2026, 6, 30)),
    }
    phase_rows, annual_rows, recovery_rows, attribution_rows = [], [], [], []
    for account_id, eq in equity.groupby("account_id", sort=True):
        eq = eq.sort_values("date").copy()
        method, fee_text = account_id.rsplit("-fee", 1)
        fee_rate = float(fee_text)
        tr = trades[trades.account_id == account_id].sort_values(["date"], kind="stable")
        ac = actions[actions.account_id == account_id].sort_values(["date"], kind="stable")

        for window, (start, end) in windows.items():
            mask = (eq.date.dt.date >= start) & (eq.date.dt.date <= end)
            part = eq[mask]
            if window in ("early", "full"):
                base = INITIAL
                base_date = start
            else:
                prior = eq[eq.date.dt.date < start].iloc[-1]
                base = float(prior.equity)
                base_date = prior.date.date()
            final = float(part.iloc[-1].equity)
            days = (end - base_date).days
            values = [base] + part.equity.astype(float).tolist()
            pt = tr[(tr.date.dt.date >= start) & (tr.date.dt.date <= end)]
            phase_rows.append({
                "account_id": account_id, "method": method, "fee_rate": fee_rate,
                "window": window, "start": start, "end": end,
                "starting_equity": base, "ending_equity": final,
                "profit": final - base, "cumulative_return": final / base - 1,
                "calendar_days": days,
                "annualized_return": (final / base) ** (YEAR_DAYS / days) - 1,
                "local_max_drawdown": max_drawdown(values),
                "average_exposure": float(part.exposure.mean()),
                "ending_exposure": float(part.iloc[-1].exposure),
                "average_equity": float(part.equity.mean()),
                "two_sided_traded_notional": float(pt.notional.sum()),
                "turnover_over_average_equity": float(pt.notional.sum() / part.equity.mean()),
                "fees": float(pt.fee.sum()), "trade_rows": len(pt),
            })

        recovery_rows.append({"account_id": account_id, "method": method,
                              "fee_rate": fee_rate, **recovery_stats(eq)})

        for year in sorted(eq.date.dt.year.unique()):
            part = eq[eq.date.dt.year == year]
            prior = eq[eq.date < part.iloc[0].date]
            base = INITIAL if prior.empty else float(prior.iloc[-1].equity)
            pt = tr[tr.date.dt.year == year]
            annual_rows.append({
                "account_id": account_id, "year": int(year), "starting_equity": base,
                "ending_equity": float(part.iloc[-1].equity),
                "return": float(part.iloc[-1].equity) / base - 1,
                "average_exposure": float(part.exposure.mean()),
                "year_end_exposure": float(part.iloc[-1].exposure),
                "average_equity": float(part.equity.mean()),
                "two_sided_traded_notional": float(pt.notional.sum()),
                "turnover_over_average_equity": float(pt.notional.sum() / part.equity.mean()),
                "fees": float(pt.fee.sum()), "trade_rows": len(pt),
            })

        units, basis = defaultdict(float), defaultdict(float)
        realized = 0.0
        event_rows = defaultdict(list)
        trade_rows = defaultdict(list)
        for r in ac.itertuples(): event_rows[r.date.date()].append(r)
        for r in tr.itertuples(): trade_rows[r.date.date()].append(r)
        for day in sorted(set(event_rows) | set(trade_rows)):
            for r in event_rows[day]:
                if r.event == "split":
                    symbol = r.event_id.split("-")[0]
                    units[symbol] *= float(r.amount)  # total cost basis stays unchanged
            for r in trade_rows[day]:
                symbol, qty = str(r.symbol), float(r.qty)
                if r.side == "buy":
                    units[symbol] += qty
                    basis[symbol] += float(r.notional)
                else:
                    avg = basis[symbol] / units[symbol] if units[symbol] else 0.0
                    removed = avg * qty
                    realized += float(r.notional) - removed
                    units[symbol] -= qty
                    basis[symbol] -= removed
                    if abs(units[symbol]) < 1e-8:
                        units[symbol] = basis[symbol] = 0.0
        end_day = date(2026, 6, 30)
        unrealized = sum(units[s] * close[(end_day, s)] - basis[s] for s in units)
        dividends = float(ac[ac.event == "receivable"].amount.sum())
        total_fees = float(tr.fee.sum())
        final = float(eq.iloc[-1].equity)
        attributed = realized + unrealized + dividends - total_fees
        attribution_rows.append({
            "account_id": account_id, "realized_price_pnl": realized,
            "ending_unrealized_price_pnl": unrealized, "earned_dividends": dividends,
            "fees": total_fees, "attributed_net_profit": attributed,
            "account_net_profit": final - INITIAL,
            "reconciliation_difference": attributed - (final - INITIAL),
            "ending_cost_basis": sum(basis.values()), "ending_units_symbols": sum(v > 0 for v in units.values()),
        })

    write_csv("phase-metrics.csv", phase_rows)
    write_csv("annual-metrics.csv", annual_rows)
    write_csv("recovery.csv", recovery_rows)
    write_csv("profit-attribution.csv", attribution_rows)
    checks = {
        "status": "passed" if max(abs(r["reconciliation_difference"]) for r in attribution_rows) < 1e-5 else "failed",
        "accounts": len(attribution_rows), "phase_rows": len(phase_rows),
        "annual_rows": len(annual_rows),
        "max_abs_profit_reconciliation_difference": max(abs(r["reconciliation_difference"]) for r in attribution_rows),
        "principles_version": "experiment-backtest-principles.md v1.0",
    }
    (OUT / "results.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
