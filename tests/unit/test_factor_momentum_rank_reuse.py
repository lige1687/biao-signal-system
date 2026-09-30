"""Synthetic evidence for reusing ``monthly_decisions(...).ranked``.

This file intentionally starts from hand-written momentum scores and quote
counts.  It does not call ``build_mixed_batch`` and does not exercise prices,
future returns, accounts, or production trading.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from lei_signal.research import definitions as d
from lei_signal.research import factor_runtime as fr


DAY = "2026-08-31"


def _row(
    symbol: str,
    momentum: float,
    *,
    valid_count: int = 273,
    date: str = DAY,
    rv_rank: float = 0.1,
) -> dict:
    return {
        "date": date,
        "symbol": symbol,
        "momentum": momentum,
        "valid_count": valid_count,
        "rv_rank": rv_rank,
    }


def _batch(rows: list[dict]) -> fr.FactorBatch:
    return fr.FactorBatch(
        values=pd.DataFrame(rows),
        missing=pd.DataFrame(columns=["date", "symbol", "field", "reason"]),
        metadata={"synthetic_rank_only": True},
    )


def _decision(
    rows: list[dict], symbols: list[str], *, variant: str = "E10", day: str = DAY
):
    return fr.monthly_decisions(
        _batch(rows), variant=variant, completed_months=[day], symbols=symbols
    ).iloc[0]


def test_rank_card_is_resolved_with_profile_and_bound_to_existing_runtime():
    registry = d.load_registry()

    card = d.resolve(registry, "mixed.momentum.rank@1.0.0", purpose="ranking")
    bound = fr.bound_reference("mixed.momentum.rank@1.0.0", registry=registry)

    assert card == bound
    assert card["scope"].startswith("full14")
    assert card["input"]["calendar"] == "每产品自身非缺失且close>0的报价行；无前填；月末用全池日期并集"
    assert card["universe"]["eligibility"].endswith("当前存续池有选择偏差")
    assert card["definition"]["unit"] == "ordered_symbol_list"
    assert card["definition"]["parameters"] == {
        "ties": "exact equality then symbol ascending"
    }
    assert card["status"]["production"] == "not_authorized"


def test_e10_ranked_is_full_order_not_selected_top3_and_ignores_rv_filter():
    symbols = ["000006", "000003", "000001", "000005", "000002", "000004"]
    rows = [
        _row("000001", -0.20, rv_rank=0.99),
        _row("000002", 0.40, rv_rank=0.99),
        _row("000003", 0.40, rv_rank=0.99),
        _row("000004", math.nextafter(0.40, -math.inf), rv_rank=0.99),
        _row("000005", 0.80, rv_rank=0.99),
        _row("000006", 0.10, rv_rank=0.99),
    ]
    expected_full = ["000005", "000002", "000003", "000004", "000006", "000001"]

    got = _decision(rows, symbols, variant="E10")

    assert got.ranked.split("|") == expected_full
    assert got.selected.split("|") == expected_full[:3]


def test_exact_ties_use_symbol_but_adjacent_floats_keep_numeric_order():
    lower = 0.3
    higher = math.nextafter(lower, math.inf)
    rows = [
        _row("000020", lower),
        _row("000010", lower),
        _row("000030", higher),
    ]
    expected = ["000030", "000010", "000020"]

    got = _decision(rows, ["000020", "000030", "000010"])

    assert got.ranked.split("|") == expected


def test_eligibility_boundaries_missing_current_and_nonfinite_scores():
    symbols = [
        "000001",
        "000002",
        "000003",
        "000004",
        "000005",
        "000006",
    ]
    rows = [
        _row("000001", -0.50, valid_count=273),
        _row("000002", 9.00, valid_count=272),
        _row("000003", np.nan, valid_count=273),
        _row("000004", np.inf, valid_count=273),
        _row("000005", -np.inf, valid_count=273),
        _row("000006", 99.0, valid_count=999, date="2026-08-28"),
    ]

    got = _decision(rows, symbols)

    assert got.ranked.split("|") == ["000001"]
    assert got.selected.split("|") == ["000001"]


def test_no_eligible_product_returns_empty_order_and_selection():
    symbols = ["000001", "000002", "000003"]
    rows = [
        _row("000001", 1.0, valid_count=272),
        _row("000002", np.nan, valid_count=300),
        _row("000003", 3.0, valid_count=300, date="2026-08-28"),
    ]

    got = _decision(rows, symbols)

    assert got.ranked == ""
    assert got.selected == ""


def test_input_order_and_future_append_do_not_change_historical_rank():
    symbols = ["000003", "000001", "000005", "000002", "000004"]
    current = [
        _row("000001", 0.10),
        _row("000002", 0.50),
        _row("000003", -0.10),
        _row("000004", 0.30),
        _row("000005", 0.20),
    ]
    expected = ["000002", "000004", "000005", "000001", "000003"]
    shuffled = [current[i] for i in [3, 0, 4, 2, 1]]
    future = [
        _row(symbol, 100.0 - i, date="2026-09-30")
        for i, symbol in enumerate(reversed(symbols))
    ]

    baseline = _decision(current, symbols)
    reordered_and_extended = _decision(shuffled + future, list(reversed(symbols)))

    assert baseline.ranked.split("|") == expected
    assert reordered_and_extended.ranked.split("|") == expected


def test_e11_filters_ranked_before_top3_but_e10_keeps_complete_unfiltered_rank():
    symbols = ["000001", "000002", "000003", "000004", "000005"]
    rows = [
        _row("000001", 0.50, rv_rank=0.80),
        _row("000002", 0.40, rv_rank=0.20),
        _row("000003", 0.30, rv_rank=np.nan),
        _row("000004", 0.20, rv_rank=0.99),
        _row("000005", 0.10, rv_rank=0.10),
    ]

    e10 = _decision(rows, symbols, variant="E10")
    e11 = _decision(rows, symbols, variant="E11")

    assert e10.ranked.split("|") == symbols
    assert e10.selected.split("|") == symbols[:3]
    assert e11.ranked.split("|") == ["000002", "000003", "000005"]
    assert e11.selected.split("|") == ["000002", "000003", "000005"]


def test_legacy_entry_does_not_reject_duplicate_rows_or_validate_count_provenance_or_month_end():
    arbitrary_non_month_end = "2026-08-14"
    symbols = ["000001", "000002"]
    rows = [
        _row("000001", 0.90, valid_count=273, date=arbitrary_non_month_end),
        _row("000001", -0.90, valid_count=273, date=arbitrary_non_month_end),
        _row("000002", 0.80, valid_count=273, date=arbitrary_non_month_end),
    ]

    got = _decision(rows, symbols, day=arbitrary_non_month_end)

    # The legacy entry trusts caller-supplied counts and dates, and takes the
    # first duplicate row.  These are caller preconditions, not auto-rejections.
    assert got.ranked.split("|") == ["000001", "000002"]
