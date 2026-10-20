"""Money reconciliation and comparison tests for factor library v0."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lei_signal.research import definitions as d
from lei_signal.research import factor_account_adapter as fa
from lei_signal.research import factor_diagnostics as fd
from lei_signal.research import factor_runtime as fr

ROOT = Path(__file__).resolve().parents[2]


def test_capital_contribution_oracle():
    net_sales, purchases, paid, receivable, market_value = 20.0, 60.0, 2.0, 3.0, 50.0
    contribution = net_sales - purchases + paid + receivable + market_value
    cash_end = 100.0 - purchases + net_sales + paid
    assert contribution == 15.0
    assert cash_end + receivable + market_value - 100.0 == contribution


def _hand_account_frames():
    # initial 100; buy gross 60 (notional 59.9 fee .1); sell net 20 (20.1/.1);
    # dividend 5 accrued, 2 paid -> ending receivable 3; ending market value 50.
    trades = pd.DataFrame(
        [
            dict(date="2021-01-04", symbol="000001", side="buy", qty=100, price=0.599,
                 notional=59.9, fee=0.1),
            dict(date="2021-02-01", symbol="000001", side="sell", qty=50, price=0.402,
                 notional=20.1, fee=0.1),
        ]
    )
    events = pd.DataFrame(
        [
            dict(date="2021-03-01", event_id="000001-d1", event="receivable", amount=5.0),
            dict(date="2021-03-05", event_id="000001-d1", event="cash_paid", amount=2.0),
        ]
    )
    actions = [dict(event_id="000001-d1", symbol="000001", type="cash_dividend")]
    prices = pd.DataFrame(
        [
            dict(date="2021-01-04", symbol="000001", close=0.599),
            dict(date="2021-02-01", symbol="000001", close=0.402),
            dict(date="2021-06-30", symbol="000001", close=1.0),
        ]
    )
    equity = pd.DataFrame(
        [dict(date="2021-06-30", equity=115.0, cash=62.0, receivable=3.0, units_000001=50)]
    )
    return equity, trades, events, actions, prices


def test_capital_contributions_reconcile_hand_account():
    equity, trades, events, actions, prices = _hand_account_frames()
    out = fd.capital_contributions(
        equity=equity,
        trades=trades,
        events=events,
        actions=actions,
        prices=prices,
        initial=100.0,
    )
    row = out.iloc[0]
    assert row.symbol == "000001"
    assert row.net_sales == 20.0
    assert row.gross_purchases == 60.0
    assert row.cash_dividends_paid == 2.0
    assert row.ending_receivable == 3.0
    assert row.ending_market_value == 50.0
    assert row.net_contribution == 15.0
    quality = fd.reconcile(
        contributions=out, equity=equity, initial=100.0
    )
    assert quality["max_abs_error"] <= 0.01
    assert quality["passed"] is True


def test_missing_event_mapping_blocks_reconciliation():
    equity, trades, events, actions, prices = _hand_account_frames()
    with pytest.raises(ValueError, match="event_id"):
        fd.capital_contributions(
            equity=equity, trades=trades, events=events, actions=[], prices=prices, initial=100.0
        )


def test_phase_contributions_subtract_beginning_state():
    # same account; a phase that starts after the buy already happened must not
    # count the opening position as profit earned inside the phase
    equity, trades, events, actions, prices = _hand_account_frames()
    opening = pd.DataFrame(
        [dict(date="2021-01-31", equity=100.0, cash=40.0, receivable=0.0, units_000001=100)]
    )
    prices2 = pd.concat(
        [prices, pd.DataFrame([dict(date="2021-01-31", symbol="000001", close=0.6)])]
    )
    phases = fd.phase_contributions(
        equity=equity,
        opening_equity=opening,
        trades=trades[trades.date >= "2021-02-01"],
        events=events,
        actions=actions,
        prices=prices2,
        phase_start="2021-02-01",
        phase_end="2021-06-30",
    )
    row = phases.iloc[0]
    # mv end 50 - mv start 60; rec end 3 - rec start 0; sell net 20; paid 2
    assert row.ending_market_value - row.beginning_market_value == -10.0
    assert row.ending_receivable - row.beginning_receivable == 3.0
    assert row.net_contribution == pytest.approx(20.0 - 10.0 + 2.0 + 3.0)


def test_compare_accounts_uses_net_pnl_for_money_difference():
    def path(final, dd, fee, trades_count, cash, rec, name):
        dates = pd.date_range("2020-12-01", periods=400, freq="D")
        eq = np.linspace(1_000_000, final, len(dates))
        equity = pd.DataFrame(
            {"date": dates.strftime("%Y-%m-%d"), "equity": eq, "cash": cash, "receivable": rec}
        )
        summary = dict(
            account_id=name,
            initial=1_000_000,
            final=final,
            cagr=(final / 1_000_000) ** (1 / 5.5) - 1,
            max_drawdown=dd,
            fees=fee,
            trades=trades_count,
            start="2020-12-01",
            end="2026-06-30",
        )
        trades = pd.DataFrame(columns=["date", "symbol", "side", "notional", "fee"])
        periods = pd.DataFrame(
            [
                dict(period="2020Dec-2024", return_=0.1, fees=0),
                dict(period="2025-2026Jun", return_=0.02, fees=0),
            ]
        )
        return dict(summary=summary, equity=equity, trades=trades, periods=periods)

    accounts = {
        "E10-fee0.001": path(1_100_000, -0.2, 1000, 50, 10_000, 0, "E10-fee0.001"),
        "E11-fee0.001": path(1_080_000, -0.15, 900, 40, 20_000, 0, "E11-fee0.001"),
    }
    table = fd.compare_accounts(accounts)
    paths = table[table.kind == "path"].set_index("key")
    diffs = table[table.kind == "difference"].set_index("comparison")
    assert paths.loc["E11-fee0.001", "net_pnl"] == 80_000
    assert paths.loc["E10-fee0.001", "net_pnl"] == 100_000
    primary = diffs.loc["E11-E10@fee0.001"]
    assert primary.net_pnl_difference == -20_000
    # CAGR/DD differences are reported separately, never as additive profit
    assert {"net_pnl_difference", "cagr_difference", "max_drawdown_difference"} <= set(
        table.columns
    )


# ---------------------------------------------------------------------------
# Real frozen paths: every account must reconcile within CNY 0.01
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_accounts():
    reg = d.load_registry()
    d.verify_sources(reg)
    prices = pd.read_csv(
        ROOT / reg["sources"]["mixed_prices"]["path"],
        dtype={"symbol": str, "date": str},
    )
    raw_actions = json.loads(
        (ROOT / reg["sources"]["mixed_actions"]["path"]).read_text()
    )["events"]
    identity = {
        "currency": "CNY",
        "price_basis": "nominal_close",
        "symbols": list(fa.FROZEN_SYMBOLS),
        "historical_reconstruction_only": True,
    }
    batch = fr.build_mixed_batch(prices, raw_actions, registry=reg, input_identity=identity)
    union = sorted(batch.values.date.unique())
    grouped = (
        pd.DataFrame({"date": pd.to_datetime(union)})
        .assign(m=lambda x: x.date.dt.strftime("%Y-%m"))
        .groupby("m")
        .date.max()
        .dt.strftime("%Y-%m-%d")
    )
    month_ends = [m for m in grouped if "2020-11" <= m[:7] <= "2026-06"]
    out = {}
    for variant in ("E00", "E01", "E10", "E11"):
        decs = fr.monthly_decisions(
            batch, variant=variant, completed_months=month_ends, symbols=list(fa.FROZEN_SYMBOLS)
        )
        for fee in (0.001, 0.002):
            acc = fa.replay_account(
                registry=reg,
                batch=batch,
                decisions=decs,
                prices=prices,
                actions=raw_actions,
                fee=fee,
                variant=variant,
            )
            out[f"{variant}-fee{fee:.3f}"] = acc
    return reg, out, prices, raw_actions


def test_all_eight_real_paths_reconcile_within_one_cent(real_accounts):
    reg, accounts, prices, raw_actions = real_accounts
    worst = 0.0
    for key, acc in accounts.items():
        contrib = fd.capital_contributions(
            equity=acc["equity"],
            trades=acc["trades"],
            events=acc["actions"],
            actions=raw_actions,
            prices=prices,
            initial=acc["summary"]["initial"],
        )
        quality = fd.reconcile(
            contributions=contrib, equity=acc["equity"], initial=acc["summary"]["initial"]
        )
        worst = max(worst, quality["max_abs_error"])
        assert quality["passed"], (key, quality)
    assert worst <= 0.01


def test_direction_weights_use_exclusive_frozen_groups(real_accounts):
    reg, accounts, prices, raw_actions = real_accounts
    groups = fd.load_direction_groups(reg)
    assert len(groups) == 14
    # mutually exclusive: exactly one direction per product; direction names
    # may repeat across related products (11 directions among 14 products)
    assert all(isinstance(v, str) and v for v in groups.values())
    acc = accounts["E11-fee0.001"]
    weights = fd.daily_direction_weights(acc["equity"], groups, prices, raw_actions)
    # groups are mutually exclusive, so the sum of group weights is total exposure
    totals = weights.groupby("date").account_weight.sum()
    exposure = acc["equity"].set_index("date").exposure
    joined = pd.concat([totals.rename("groups"), exposure], axis=1).dropna()
    np.testing.assert_allclose(joined.groups, joined.exposure, atol=1e-8, rtol=0)
