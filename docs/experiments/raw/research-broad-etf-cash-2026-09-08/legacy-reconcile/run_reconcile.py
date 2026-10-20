#!/usr/bin/env python3
"""Reconcile locked B9 A/B weight simulation with a continuous-share cash ledger."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
LEGACY = REPO / "docs/experiments/raw/research-broad-etf-plan-2026-09-08/legacy-baseline"
SOURCE = LEGACY / "source"
INPUTS = LEGACY / "inputs"
COST = 0.001
BAND = 0.05
TOL = 1e-12


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def locked_hashes() -> dict[str, str]:
    paths = [p for base in (INPUTS, SOURCE) for p in base.rglob("*") if p.is_file()]
    paths += [HERE / "frozen-protocol.md", HERE / "run_reconcile.py",
              LEGACY / "legacy-ab-daily-equity.csv"]
    paths = sorted(paths)
    return {str(p.relative_to(REPO)): sha256(p) for p in paths}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def metrics(eq: pd.Series) -> dict:
    ann = float(eq.iloc[-1] ** (252.0 / len(eq)) - 1.0) * 100
    dd = float((eq / eq.cummax() - 1.0).min()) * 100
    ret = eq.pct_change().dropna()
    sharpe = float(ret.mean() / ret.std() * np.sqrt(252)) if ret.std() > 0 else np.nan
    return {
        "end_equity": float(eq.iloc[-1]),
        "total_return_pct": float((eq.iloc[-1] - 1.0) * 100),
        "ann_pct": ann,
        "maxdd_pct": dd,
        "return_drawdown_ratio": ann / abs(dd) if dd < 0 else None,
        "daily_stability": sharpe,
    }


def ledger(prices: pd.DataFrame, exposures: pd.DataFrame, account: str, buy_once: bool = False):
    names = list(prices.columns)
    shares = pd.Series(0.0, index=names)
    cash = 1.0
    daily, trades = [], []
    cumulative_fees = 0.0

    for day_no, (date, px) in enumerate(prices.iterrows()):
        values_before = shares * px
        equity_before = float(cash + values_before.sum())
        weights_before = values_before / equity_before
        target_weights = exposures.loc[date] / len(names)
        target_amounts = target_weights * equity_before

        if buy_once:
            eligible = pd.Series(day_no == 0, index=names)
        else:
            eligible = (target_weights - weights_before).abs() >= BAND

        desired_delta = (target_amounts - values_before).where(eligible, 0.0)
        sell_plan = (-desired_delta.clip(upper=0.0)).clip(upper=values_before)
        for name in names:
            gross = float(sell_plan[name])
            if gross <= TOL:
                continue
            qty = gross / float(px[name])
            fee = gross * COST
            shares[name] -= qty
            if abs(shares[name]) < TOL:
                shares[name] = 0.0
            cash += gross - fee
            cumulative_fees += fee
            trades.append({"account": account, "date": date.date().isoformat(), "asset": name,
                           "side": "sell", "price": float(px[name]), "shares": qty,
                           "gross_amount": gross, "fee": fee, "cash_after": cash,
                           "target_weight": float(target_weights[name]),
                           "pretrade_weight": float(weights_before[name]),
                           "reason": "initial_buy" if buy_once else "5pp_threshold"})

        values_after_sells = shares * px
        buy_plan = (target_amounts - values_after_sells).where(eligible, 0.0).clip(lower=0.0)
        planned = float(buy_plan.sum())
        scale = min(1.0, cash / (planned * (1.0 + COST))) if planned > TOL else 0.0
        for name in names:
            gross = float(buy_plan[name] * scale)
            if gross <= TOL:
                continue
            qty = gross / float(px[name])
            fee = gross * COST
            shares[name] += qty
            cash -= gross + fee
            if abs(cash) < TOL:
                cash = 0.0
            cumulative_fees += fee
            trades.append({"account": account, "date": date.date().isoformat(), "asset": name,
                           "side": "buy", "price": float(px[name]), "shares": qty,
                           "gross_amount": gross, "fee": fee, "cash_after": cash,
                           "target_weight": float(target_weights[name]),
                           "pretrade_weight": float(weights_before[name]),
                           "reason": "initial_buy" if buy_once else "5pp_threshold"})

        values_after = shares * px
        equity_after = float(cash + values_after.sum())
        if cash < -TOL or (shares < -TOL).any():
            raise AssertionError(f"negative balance on {date}: cash={cash}, min shares={shares.min()}")
        for name in names:
            daily.append({"account": account, "date": date.date().isoformat(), "asset": name,
                          "price": float(px[name]), "shares": float(shares[name]),
                          "asset_value": float(values_after[name]), "cash": cash,
                          "equity": equity_after, "pretrade_equity": equity_before,
                          "pretrade_weight": float(weights_before[name]),
                          "target_weight": float(target_weights[name]),
                          "posttrade_weight": float(values_after[name] / equity_after),
                          "cumulative_fees": cumulative_fees})

    daily_df = pd.DataFrame(daily)
    trades_df = pd.DataFrame(trades)
    eq = daily_df.groupby("date", sort=False)["equity"].first()
    eq.index = pd.to_datetime(eq.index)
    return {"daily": daily_df, "trades": trades_df, "eq": eq,
            "fees": cumulative_fees, "ending_cash": cash, "ending_shares": shares.to_dict()}


def minimal_cases() -> dict:
    idx = pd.date_range("2024-01-01", periods=3)
    cases = {}
    for name, data in {
        "two_assets_roundtrip_below_band": {"a": [100.0, 104.0, 100.0], "b": [100.0, 96.0, 100.0]},
        "one_asset_roundtrip": {"a": [100.0, 104.0, 100.0]},
        "two_assets_flat": {"a": [100.0, 100.0, 100.0], "b": [100.0, 100.0, 100.0]},
    }.items():
        p = pd.DataFrame(data, index=idx)
        e = pd.DataFrame(1.0, index=idx, columns=p.columns)
        out = ledger(p, e, name, buy_once=False)
        cases[name] = {"equity": out["eq"].tolist(), "trade_rows": len(out["trades"]),
                       "ending_cash": out["ending_cash"], "fees": out["fees"]}
    # A full investment of x costs x*(1+fee), hence x=1/(1+fee).
    expected_start = 1.0 / (1.0 + COST)
    assert abs(cases["two_assets_roundtrip_below_band"]["equity"][-1] - expected_start) < TOL
    assert abs(cases["one_asset_roundtrip"]["equity"][-1] - expected_start) < TOL
    assert abs(cases["two_assets_flat"]["equity"][-1] - expected_start) < TOL

    # Sell a half-position, then restore it; both legs pay fees from account cash.
    p = pd.DataFrame({"a": [100.0, 100.0, 100.0]}, index=idx)
    e = pd.DataFrame({"a": [1.0, 0.5, 1.0]}, index=idx)
    out = ledger(p, e, "sell_then_buy")
    assert out["daily"]["cash"].min() >= -TOL
    assert out["fees"] > COST / (1.0 + COST)
    cases["sell_then_buy_self_financed"] = {"equity": out["eq"].tolist(),
                                             "trade_rows": len(out["trades"]),
                                             "ending_cash": out["ending_cash"], "fees": out["fees"]}
    cases["full_investment_fee_identity"] = {
        "self_financed_asset_value": expected_start,
        "legacy_multiplier_asset_value": 1.0 - COST,
        "difference": expected_start - (1.0 - COST),
        "identity": "gross_buy * (1 + fee_rate) = starting_cash",
    }
    return cases


def main() -> None:
    before = locked_hashes()
    frozen_lines = (HERE / "run-lock-before.sha256").read_text().splitlines()
    frozen = {line.split("  ", 1)[1]: line.split("  ", 1)[0] for line in frozen_lines if line.strip()}
    if before != frozen:
        raise AssertionError("run inputs differ from frozen rerun manifest")

    # Boundary accounting checks must pass before any historical data is loaded.
    cases = minimal_cases()
    (HERE / "boundary-cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n")

    load_module("run_siphon_detector", SOURCE / "run_siphon_detector.py")
    rps = load_module("locked_run_portfolio_split", SOURCE / "run_portfolio_split.py")
    rps.SRC = INPUTS
    rps.RAW = HERE / "blocked-old-output"
    breadth = rps.load_breadth()
    members = [(k, v) for k, v in {**rps.GATED, **rps.TREND}.items()]
    prices, _split, allgate = rps.build_universe(breadth, members)
    ones = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)

    outputs = {
        "A_true_buy_once_hold": ledger(prices, ones, "A_true_buy_once_hold", buy_once=True),
        "A_5pp_equal_weight_rebalance": ledger(prices, ones, "A_5pp_equal_weight_rebalance"),
        "B_breadth_3tier_5pp_rebalance": ledger(prices, allgate, "B_breadth_3tier_5pp_rebalance"),
    }
    legacy = pd.read_csv(LEGACY / "legacy-ab-daily-equity.csv", parse_dates=["date"]).set_index("date")
    comparison = legacy.copy()
    for name, out in outputs.items():
        comparison[name] = out["eq"]
    comparison["A_legacy_minus_corrected_threshold"] = comparison["A_legacy_equity"] - comparison["A_5pp_equal_weight_rebalance"]
    comparison["B_legacy_minus_corrected"] = comparison["B_legacy_equity"] - comparison["B_breadth_3tier_5pp_rebalance"]
    comparison.index.name = "date"
    comparison.to_csv(HERE / "equity-comparison-daily.csv", float_format="%.15g")
    pd.concat([out["daily"] for out in outputs.values()], ignore_index=True).to_csv(HERE / "daily.csv", index=False, float_format="%.15g")
    pd.concat([out["trades"] for out in outputs.values()], ignore_index=True).to_csv(HERE / "trades.csv", index=False, float_format="%.15g")

    summaries = {name: {**metrics(out["eq"]), "fees_paid": out["fees"],
                        "trade_rows": len(out["trades"]),
                        "trade_dates": int(out["trades"]["date"].nunique()),
                        "ending_cash": out["ending_cash"]} for name, out in outputs.items()}
    summaries["A_legacy_weight_sim"] = metrics(legacy["A_legacy_equity"])
    summaries["B_legacy_weight_sim"] = metrics(legacy["B_legacy_equity"])
    attr = {
        "A_accounting_effect_vs_same_5pp_semantics": {
            "end_equity_delta_legacy_minus_cash": float(comparison["A_legacy_minus_corrected_threshold"].iloc[-1]),
            "annualized_return_delta_pp": summaries["A_legacy_weight_sim"]["ann_pct"] - summaries["A_5pp_equal_weight_rebalance"]["ann_pct"],
            "max_abs_daily_equity_delta": float(comparison["A_legacy_minus_corrected_threshold"].abs().max()),
        },
        "A_semantic_effect_true_hold_vs_corrected_5pp": {
            "end_equity_delta_true_hold_minus_5pp": summaries["A_true_buy_once_hold"]["end_equity"] - summaries["A_5pp_equal_weight_rebalance"]["end_equity"],
            "annualized_return_delta_pp": summaries["A_true_buy_once_hold"]["ann_pct"] - summaries["A_5pp_equal_weight_rebalance"]["ann_pct"],
        },
        "B_accounting_effect_vs_same_rule": {
            "end_equity_delta_legacy_minus_cash": float(comparison["B_legacy_minus_corrected"].iloc[-1]),
            "annualized_return_delta_pp": summaries["B_legacy_weight_sim"]["ann_pct"] - summaries["B_breadth_3tier_5pp_rebalance"]["ann_pct"],
            "max_abs_daily_equity_delta": float(comparison["B_legacy_minus_corrected"].abs().max()),
        },
        "mechanism": "legacy weights are not allowed to drift with relative prices; corrected accounts preserve shares between qualifying trades and self-finance fees",
    }
    after = locked_hashes()
    if before != after:
        raise AssertionError("locked inputs changed during run")
    (HERE / "run-lock-after.sha256").write_text("".join(f"{h}  {p}\n" for p, h in sorted(after.items())))
    result = {
        "scope": "locked nine-index A/B comparison only; continuous shares diagnose old math and are not tradeable ETF evidence",
        "window": [str(prices.index.min().date()), str(prices.index.max().date())],
        "rows": len(prices), "instruments": list(prices.columns),
        "rules": {"cost_one_way": COST, "rebalance_band_absolute_weight": BAND,
                  "execution": "next common quote day close", "initial_cash": 1.0,
                  "target_amount_basis": "pre-fee equity valued at execution close",
                  "cash_shortfall": "sell first; scale all planned buys pro rata so buys plus fees fit cash"},
        "summaries": summaries, "attribution": attr,
        "input_hashes_unchanged": before == after,
        "boundary_cases_passed": True,
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "numpy": np.__version__, "pandas": pd.__version__,
                        "pyarrow": __import__("pyarrow").__version__},
    }
    (HERE / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"summaries": summaries, "attribution": attr}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
