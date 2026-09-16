"""Small deterministic checks of the archived factor-backtest accounting model.

No historical prices and no strategy returns are computed here.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def archived_fixed_weight_return(returns: pd.DataFrame, weights: pd.Series) -> float:
    daily = returns.mul(weights, axis=1).sum(axis=1)
    return float((1.0 + daily).prod() - 1.0)


def buy_and_hold_return(prices: pd.DataFrame, weights: pd.Series) -> float:
    shares = weights / prices.iloc[0]
    return float((prices.iloc[-1].mul(shares)).sum() - 1.0)


def main() -> None:
    # Buy A/B 50/50. A doubles then halves; B is flat. A real unchanged-share
    # holding ends at 1.0. Re-applying 50/50 every day ends at 1.125 and requires
    # an unrecorded rebalance between the two return days.
    prices = pd.DataFrame(
        {"A": [1.0, 2.0, 1.0], "B": [1.0, 1.0, 1.0]},
        index=pd.date_range("2026-01-01", periods=3),
    )
    returns = prices.pct_change().iloc[1:]
    weights = pd.Series({"A": 0.5, "B": 0.5})

    # Forward fill makes a missing quote a zero-return day. A requested exit on
    # that day can therefore be represented as completed even though no price is
    # present to establish an executable trade.
    raw = pd.Series([10.0, np.nan, 8.0], index=pd.date_range("2026-02-01", periods=3))
    filled = raw.ffill()

    # cummax without an initial capital anchor misses a loss on the first row.
    equity_after_first_day = pd.Series([0.8, 0.9])
    unanchored_mdd = float((equity_after_first_day / equity_after_first_day.cummax() - 1).min())
    anchored = pd.concat([pd.Series([1.0]), equity_after_first_day], ignore_index=True)
    anchored_mdd = float((anchored / anchored.cummax() - 1).min())

    result = {
        "fixed_weight_without_daily_turnover": {
            "archived_style_total_return": archived_fixed_weight_return(returns, weights),
            "unchanged_share_total_return": buy_and_hold_return(prices, weights),
            "difference": archived_fixed_weight_return(returns, weights)
            - buy_and_hold_return(prices, weights),
        },
        "missing_quote": {
            "raw_middle_is_missing": bool(pd.isna(raw.iloc[1])),
            "forward_filled_middle": float(filled.iloc[1]),
            "reported_return_on_missing_day": float(filled.pct_change().iloc[1]),
            "execution_price_exists": False,
        },
        "initial_capital_drawdown_anchor": {
            "unanchored_mdd": unanchored_mdd,
            "anchored_mdd": anchored_mdd,
        },
    }
    out = Path(__file__).with_name("mechanism-counterexamples.json")
    out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
