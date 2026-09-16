"""Identity-bound batch calculation for the factor library v0.

The two oracle tests below freeze the legacy numerical contract; the rest pin
the new batch interface, identity rejection and the real frozen-input rebuild.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lei_signal.research import definitions as d
from lei_signal.research import factor_runtime as fr

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Mandatory legacy numerical contracts (plan Task 2)
# ---------------------------------------------------------------------------

def test_reference_momentum_is_252_to_21():
    q = pd.Series(np.arange(1.0, 281.0))
    out = d.quote_features(q)
    assert out.momentum.iloc[252] == 231.0
    assert out.valid_count.iloc[272] == 273


def test_mixed_price_chain_oracle():
    # Dividend 1 then a 1-for-2 split between two quotes: 100 -> 49.5 nominal,
    # the economic index must not move.
    q = pd.Series(
        [100.0, 49.5], index=pd.to_datetime(["2020-01-01", "2020-01-04"])
    )
    events = [
        dict(
            event_id="d",
            type="cash_dividend",
            cash=1.0,
            effective_date="2020-01-02",
            available_at="2020-01-01T12:00:00+08:00",
        ),
        dict(
            event_id="s",
            type="split",
            ratio=2.0,
            effective_date="2020-01-03",
            available_at="2020-01-02T12:00:00+08:00",
        ),
    ]
    assert d.economic_index(q, events).iloc[-1] == 1.0


# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------

def _prices_frame(symbols, n=300, start="2019-09-02", scale=1.0, suffix=True):
    dates = pd.bdate_range(start, periods=n)
    rows = []
    for i, s in enumerate(symbols):
        base = 100.0 + i
        for t, day in enumerate(dates):
            close = (base + t) * scale
            rows.append(
                dict(
                    date=day.strftime("%Y-%m-%d"),
                    symbol=f"{s}.SH" if suffix else s,
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=10000,
                )
            )
    return pd.DataFrame(rows)


def _identity(reg, tmp_path=None):
    return {
        "currency": "CNY",
        "price_basis": "nominal_close",
        "symbols": ["510300", "512400"],
        "historical_reconstruction_only": True,
    }


def test_build_mixed_batch_interface_exists_and_basic_values():
    reg = d.load_registry()
    prices = _prices_frame(["510300", "512400"])
    batch = fr.build_mixed_batch(prices, [], registry=reg, input_identity=_identity(reg))
    # columns promised by the interface contract
    for col in [
        "date",
        "symbol",
        "economic_index",
        "momentum",
        "rv20",
        "rv_rank",
        "valid_count",
        "sma200",
        "distance200",
        "above200",
    ]:
        assert col in batch.values.columns
    first = batch.values[(batch.values.symbol == "510300")].sort_values("date")
    assert first.iloc[0].economic_index == pytest.approx(1.0)
    # I_t = (100+t)/100; momentum at own-grid t=252: I231/I0 - 1
    assert first.iloc[252].momentum == pytest.approx(331.0 / 100.0 - 1.0)
    assert first.iloc[252].total_return == pytest.approx(1.0 / 351.0)
    assert first.iloc[0].prev_quote_date is None
    assert first.iloc[1].prev_quote_date == first.iloc[0].date
    # valid_count is per-symbol own valid-quote count
    assert int(first.iloc[272].valid_count) == 273
    # sma200 only from the 200th own quote onward
    assert pd.isna(first.iloc[198].sma200)
    assert pd.notna(first.iloc[199].sma200)
    # identity metadata
    refs = batch.metadata["bindings"]
    assert "mixed.momentum.raw@1.0.0" in refs
    assert "mixed.price.economic@1.0.0" in refs
    assert batch.metadata["quality"]["mode"] == "historical_reconstruction_only"
    assert isinstance(batch.missing, pd.DataFrame)


def test_dimensionless_outputs_invariant_to_price_scale():
    reg = d.load_registry()
    a = fr.build_mixed_batch(
        _prices_frame(["510300"]), [], registry=reg, input_identity=_identity(reg)
    )
    b = fr.build_mixed_batch(
        _prices_frame(["510300"], scale=10.0), [], registry=reg, input_identity=_identity(reg)
    )
    cols = ["momentum", "rv20", "rv_rank", "distance200", "above200", "total_return"]
    x = a.values.sort_values("date").reset_index(drop=True)
    y = b.values.sort_values("date").reset_index(drop=True)
    pd.testing.assert_frame_equal(x[cols], y[cols], atol=1e-12, rtol=1e-12)


def test_appended_future_leaves_history_unchanged_but_revision_changes_fingerprint():
    reg = d.load_registry()
    prices = _prices_frame(["510300"], n=300)
    b1 = fr.build_mixed_batch(prices, [], registry=reg, input_identity=_identity(reg))
    longer = _prices_frame(["510300"], n=305)
    b2 = fr.build_mixed_batch(longer, [], registry=reg, input_identity=_identity(reg))
    h = b2.values.merge(
        b1.values[["date", "symbol", "economic_index", "momentum"]],
        on=["date", "symbol"],
        suffixes=("_new", "_old"),
    )
    pd.testing.assert_series_equal(
        h.economic_index_new, h.economic_index_old, check_names=False, atol=1e-12, rtol=1e-12
    )
    # revising an observed price changes the input fingerprint
    revised = prices.copy()
    revised.loc[revised.date == revised.date.iloc[10], "close"] += 1.0
    b3 = fr.build_mixed_batch(revised, [], registry=reg, input_identity=_identity(reg))
    assert b3.metadata["input_fingerprint"] != b1.metadata["input_fingerprint"]
    # appending future quotes legitimately changes the full-input fingerprint;
    # history values are what must stay unchanged (checked above)


def test_missing_and_nonpositive_quotes_are_abnormal_rows_not_silently_dropped():
    reg = d.load_registry()
    prices = _prices_frame(["510300"], n=300)
    prices.loc[prices.date == prices.date.iloc[5], "close"] = np.nan
    prices.loc[prices.date == prices.date.iloc[6], "close"] = 0.0
    prices.loc[prices.date == prices.date.iloc[7], "close"] = np.inf
    batch = fr.build_mixed_batch(prices, [], registry=reg, input_identity=_identity(reg))
    reasons = set(batch.missing.reason)
    assert "missing_quote" in reasons
    assert "nonpositive_quote" in reasons
    assert "nonfinite_quote" in reasons
    # the valid grid simply excludes those sessions; no fabricated zero returns
    grid = batch.values.sort_values("date")
    assert len(grid) == 297
    assert pd.notna(grid.economic_index).all()


def test_all_missing_symbol_does_not_emit_zero_series():
    reg = d.load_registry()
    prices = _prices_frame(["510300", "512400"])
    prices.loc[prices.symbol == "512400.SH", "close"] = np.nan
    identity = _identity(reg)
    batch = fr.build_mixed_batch(prices, [], registry=reg, input_identity=identity)
    assert set(batch.values.symbol) == {"510300"}
    assert (batch.missing.symbol == "512400").any()


def test_wrong_currency_or_basis_is_rejected():
    reg = d.load_registry()
    prices = _prices_frame(["510300"])
    bad = _identity(reg)
    bad["currency"] = "USD"
    with pytest.raises(ValueError, match="currency"):
        fr.build_mixed_batch(prices, [], registry=reg, input_identity=bad)
    bad = _identity(reg)
    bad["price_basis"] = "qfq_adjusted"
    with pytest.raises(ValueError, match="price_basis"):
        fr.build_mixed_batch(prices, [], registry=reg, input_identity=bad)


def test_non_mixed_identities_cannot_bind_to_mixed_batch():
    reg = d.load_registry()
    with pytest.raises(ValueError, match="not a mixed-pool binding"):
        fr.bound_reference("etf.price.continuous@1.0.0", registry=reg)
    with pytest.raises(ValueError, match="not a mixed-pool binding"):
        fr.bound_reference("breadth.csi300.b200.common@1.0.0", registry=reg)
    with pytest.raises(ValueError, match="unknown exact definition"):
        fr.bound_reference("mixed.momentum.raw@9.9.9", registry=reg)
    # a breadth fraction in [0,1] handed in as prices must not enter the chain
    breadth_like = _prices_frame(["510300"])
    breadth_like["close"] = 0.5
    identity = dict(_identity(reg), kind="breadth_fraction")
    with pytest.raises(ValueError, match="breadth"):
        fr.build_mixed_batch(breadth_like, [], registry=reg, input_identity=identity)


def test_binding_rejects_registered_parameter_or_formula_change():
    reg = d.load_registry()
    # tamper with the resolved card content: implementation must notice
    card = next(o for o in reg["objects"] if o["id"] == "mixed.momentum.raw")
    card.setdefault("definition", {})["parameters"] = {"long_lag": 250, "skip_lag": 21}
    prices = _prices_frame(["510300"])
    with pytest.raises(ValueError, match="binding differs"):
        fr.build_mixed_batch(prices, [], registry=reg, input_identity=_identity(reg))


def test_unknown_availability_cannot_feed_the_strict_chain():
    q = pd.Series([100.0, 99.0], index=pd.to_datetime(["2020-01-01", "2020-01-04"]))
    events = [
        dict(event_id="x", type="cash_dividend", cash=1.0, effective_date="2020-01-02")
    ]
    with pytest.raises((KeyError, ValueError), match="available_at"):
        d.economic_index(q, events)
    # the reconstruction branch is explicit and records the unknown events
    idx, unknown = fr.reconstructed_economic_index(q, events)
    assert idx.iloc[-1] == pytest.approx((99.0 + 1.0) / 100.0)
    assert unknown == ["x"]


def test_rv_percentile_exactly_0_8_is_excluded_nan_passes():
    # four eligible products; 000001 sits exactly on 0.8 and must be excluded
    dates = pd.to_datetime(["2026-01-30"])
    rows = []
    mom = {"000001": 0.4, "000002": 0.3, "000003": 0.2, "000004": 0.1}
    rank = {"000001": 0.8, "000002": 0.2, "000003": 0.3, "000004": 0.4}
    for s in mom:
        rows.append(
            dict(
                date=dates[0],
                symbol=s,
                economic_index=1.0,
                momentum=mom[s],
                rv20=np.nan,
                rv_rank=rank[s],
                valid_count=300,
                sma200=1.0,
                distance200=0.0,
                above200=1.0,
                total_return=0.0,
                prev_quote_date=None,
            )
        )
    # add a NaN-rank product that must pass the legacy rule
    rows.append({**rows[0], "symbol": "000005", "momentum": 0.05, "rv_rank": np.nan})
    values = pd.DataFrame(rows)
    batch = fr.FactorBatch(values=values, missing=pd.DataFrame(), metadata={"nan_rv_pass_count": 0})
    dec = fr.monthly_decisions(
        batch, variant="E11", completed_months=["2026-01-30"], symbols=list(mom) + ["000005"]
    )
    row = dec.iloc[0]
    assert row.selected.split("|") == ["000002", "000003", "000004"]
    assert "000001" in row.exclusion_reasons
    # the NaN product is eligible and ranked (it would be 4th by momentum anyway)
    dec10 = fr.monthly_decisions(
        batch, variant="E10", completed_months=["2026-01-30"], symbols=list(mom) + ["000005"]
    )
    assert dec10.iloc[0].selected.split("|") == ["000001", "000002", "000003"]
    # E00 averages every eligible product including the NaN-rank one
    dec00 = fr.monthly_decisions(
        batch, variant="E00", completed_months=["2026-01-30"], symbols=list(mom) + ["000005"]
    )
    assert dec00.iloc[0].selected.split("|") == ["000001", "000002", "000003", "000004", "000005"]


# ---------------------------------------------------------------------------
# Real frozen-input rebuild, compared independently with the frozen engine
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def frozen_setup():
    reg = d.load_registry()
    d.verify_sources(reg)
    src = reg["sources"]
    prices_path = ROOT / src["mixed_prices"]["path"]
    actions_path = ROOT / src["mixed_actions"]["path"]
    code_path = ROOT / src["defense_code"]["path"]
    assert d.fingerprint(code_path)["sha256"] == src["defense_code"]["sha256"]
    spec = importlib.util.spec_from_file_location("_frozen_defense_run", code_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    prices = pd.read_csv(prices_path, dtype={"symbol": str, "date": str})
    raw_actions = __import__("json").loads(actions_path.read_text())["events"]
    return reg, mod, prices, raw_actions


def test_frozen_rebuild_matches_legacy_engine_value_by_value(frozen_setup):
    reg, mod, prices_raw, raw_actions = frozen_setup
    p, acts = mod.load()
    legacy = mod.economic_indices(p, acts)
    identity = {
        "currency": "CNY",
        "price_basis": "nominal_close",
        "symbols": mod.FULL,
        "historical_reconstruction_only": True,
    }
    batch = fr.build_mixed_batch(prices_raw, raw_actions, registry=reg, input_identity=identity)
    got = batch.values.rename(
        columns={
            "economic_index": "economic_index",
            "momentum": "momentum",
            "rv_rank": "rv_rank",
            "valid_count": "valid_count",
            "sma200": "sma200",
        }
    )
    merged = legacy.merge(
        got,
        on=["date", "symbol"],
        suffixes=("_old", "_new"),
        validate="one_to_one",
    )
    assert len(merged) == len(legacy)
    for col in ["economic_index", "momentum", "rv_rank", "sma200"]:
        np.testing.assert_allclose(
            merged[f"{col}_old"].astype(float),
            merged[f"{col}_new"].astype(float),
            rtol=1e-10,
            atol=1e-10,
            equal_nan=True,
            err_msg=col,
        )
    assert (merged.valid_count_old.astype(int) == merged.valid_count_new.astype(int)).all()


def test_e11_monthly_decisions_match_legacy_decisions(frozen_setup):
    reg, mod, prices_raw, raw_actions = frozen_setup
    p, acts = mod.load()
    legacy = mod.economic_indices(p, acts)
    legacy_decs = {
        r["decision_date"]: r
        for r in mod.decisions(legacy)
        if r["config"] == "momentum_top3"
    }
    identity = {
        "currency": "CNY",
        "price_basis": "nominal_close",
        "symbols": mod.FULL,
        "historical_reconstruction_only": True,
    }
    batch = fr.build_mixed_batch(prices_raw, raw_actions, registry=reg, input_identity=identity)
    months = sorted(legacy_decs)
    dec = fr.monthly_decisions(
        batch, variant="E11", completed_months=months, symbols=mod.FULL
    ).set_index("decision_date")
    assert list(dec.index) == months
    for day in months:
        assert dec.loc[day, "selected"] == legacy_decs[day]["selected"], day
        assert dec.loc[day, "weights"] == legacy_decs[day]["weights"], day
