from __future__ import annotations

import csv
import json
import math
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def maximum_decline(values: list[float]) -> float:
    peak = values[0]
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        worst = max(worst, 1.0 - value / peak)
    return worst


def annual_return_from_dated_contributions(daily: list[dict[str, str]]) -> tuple[float, int]:
    end = date.fromisoformat(daily[-1]["date"])
    final_equity = float(daily[-1]["equity"])
    cashflows = []
    previous_funding = 0.0
    for row in daily:
        funding = float(row["total_funding"])
        added = funding - previous_funding
        if added > 0:
            cashflows.append((date.fromisoformat(row["date"]), added))
        previous_funding = funding

    def future_value(rate: float) -> float:
        return sum(amount * (1.0 + rate) ** ((end - when).days / 365.25) for when, amount in cashflows)

    low, high = -0.999999, 10.0
    for _ in range(200):
        mid = (low + high) / 2
        if future_value(mid) < final_equity:
            low = mid
        else:
            high = mid
    return (low + high) / 2, len(cashflows)


def account_check(folder: Path) -> dict:
    summary = json.loads((folder / "summary.json").read_text())
    daily = rows(folder / "daily.csv")
    trades = rows(folder / "trades.csv")
    return {
        "account_id": summary["account_id"],
        "reported_final_equity": summary["final_equity"],
        "daily_last_equity": float(daily[-1]["equity"]),
        "reported_max_drawdown_abs": abs(summary["max_drawdown"]),
        "daily_recomputed_max_drawdown": maximum_decline([float(r["equity"]) for r in daily]),
        "reported_buys_plus_sells": summary["buys"] + summary["sells"],
        "trade_rows": len(trades),
    }


first = ROOT / "docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12/account-results"
multi = ROOT / "docs/experiments/raw/research-broad-etf-multimethod-2026-09-08/execution/account-results"
accounts: dict[str, dict] = {}
for symbol in ("sh510300", "sz159915"):
    for method, base in (
        ("hold", first),
        ("breadth_three_tier", first),
        ("H1_weekly_binary_hysteresis", multi),
        ("H2_weekly_breadth_trend_participation", multi),
    ):
        folder = base / f"{symbol}-{method}-fee0.001"
        accounts[f"{symbol}:{method}"] = account_check(folder)

comparisons = []
for symbol in ("sh510300", "sz159915"):
    hold = accounts[f"{symbol}:hold"]
    width = accounts[f"{symbol}:breadth_three_tier"]
    h1 = accounts[f"{symbol}:H1_weekly_binary_hysteresis"]
    h2 = accounts[f"{symbol}:H2_weekly_breadth_trend_participation"]
    comparisons.append({
        "symbol": symbol,
        "width_minus_hold": width["daily_last_equity"] - hold["daily_last_equity"],
        "h1_minus_width": h1["daily_last_equity"] - width["daily_last_equity"],
        "h2_minus_width": h2["daily_last_equity"] - width["daily_last_equity"],
        "width_trade_rows": width["trade_rows"],
        "h1_trade_rows": h1["trade_rows"],
        "h2_trade_rows": h2["trade_rows"],
    })


dca_root = ROOT / "docs/experiments/raw/research-fifth-2026-09-08/study/results"
dca = {}
for arm in ("quarterly", "hold"):
    daily = rows(dca_root / f"full-base-{arm}" / "daily.csv")
    nav = [float(r["nav"]) for r in daily if float(r["account_units"]) > 0]
    annualized, contribution_count = annual_return_from_dated_contributions(daily)
    dca[arm] = {
        "last_equity": float(daily[-1]["equity"]),
        "max_drawdown_from_nav": maximum_decline(nav),
        "dated_contribution_annualized_recomputed": annualized,
        "positive_contribution_dates": contribution_count,
    }
dca["quarterly_minus_hold"] = dca["quarterly"]["last_equity"] - dca["hold"]["last_equity"]
dca["drawdown_improvement_pp"] = 100 * (dca["hold"]["max_drawdown_from_nav"] - dca["quarterly"]["max_drawdown_from_nav"])

summary = rows(ROOT / "docs/experiments/raw/research-fifth-2026-09-08/study/summary.csv")
base = {r["arm"]: r for r in summary if r["window"] == "full" and r["scenario"] == "base"}
dca["reported_annualized_difference_pp"] = 100 * (
    float(base["quarterly"]["cashflow_annual_return"]) - float(base["hold"]["cashflow_annual_return"])
)
dca["independently_recomputed_annualized_difference_pp"] = 100 * (
    dca["quarterly"]["dated_contribution_annualized_recomputed"]
    - dca["hold"]["dated_contribution_annualized_recomputed"]
)


invested = ROOT / "docs/experiments/raw/research-invested-capital-metrics-2026-09-08/independent-review"
factor_rows = rows(invested / "trade-factors.csv")
curve_rows = rows(invested / "unit-curve-daily.csv")
chosen = ("sh510300-R1-fee10bp", "sz159915-R1-risk1-fee20bp")
unit_checks = []
for account_id in chosen:
    factors = [float(r["factor"]) for r in factor_rows if r["account_id"] == account_id]
    curve = [r for r in curve_rows if r["account_id"] == account_id]
    values = [float(r["unit_curve"]) for r in curve]
    flat_idle_pairs = sum(
        curve[i - 1]["holding"] == "False"
        and curve[i]["holding"] == "False"
        and values[i] == values[i - 1]
        for i in range(1, len(curve))
    )
    idle_pairs = sum(
        curve[i - 1]["holding"] == "False" and curve[i]["holding"] == "False"
        for i in range(1, len(curve))
    )
    span = (date.fromisoformat(curve[-1]["date"]) - date.fromisoformat(curve[0]["date"])).days
    product = math.prod(factors)
    unit_checks.append({
        "account_id": account_id,
        "trade_factor_product": product,
        "curve_last_value": values[-1],
        "difference": product - values[-1],
        "calendar_span_days": span,
        "calendar_annualized_recomputed": product ** (365.25 / span) - 1,
        "max_drawdown_recomputed": maximum_decline(values),
        "idle_consecutive_pairs": idle_pairs,
        "idle_pairs_unchanged": flat_idle_pairs,
        "all_idle_pairs_unchanged": idle_pairs == flat_idle_pairs,
    })

analysis = json.loads((ROOT / "docs/experiments/raw/research-invested-capital-metrics-2026-09-08/analysis/results.json").read_text())
pair_summary = [{
    "symbol": p["symbol"],
    "fee_per_side": p["fee_per_side"],
    "max_daily_curve_difference": p["max_daily_unit_curve_difference"],
    "same_unit_capital_performance": p["same_unit_capital_performance"],
} for p in analysis["paired_checks"]]

result = {
    "account_checks": accounts,
    "width_h1_h2_comparisons": comparisons,
    "dca_check": dca,
    "invested_capital_two_path_checks": unit_checks,
    "full_vs_reduced_size_pair_summary_from_saved_results": pair_summary,
}
(OUT / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(result, ensure_ascii=False, indent=2))
