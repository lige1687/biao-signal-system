"""Four-variant selection and frozen-engine replay tests for factor library v0."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lei_signal.research import definitions as d
from lei_signal.research import factor_account_adapter as fa
from lei_signal.research import factor_runtime as fr

ROOT = Path(__file__).resolve().parents[2]


def _four_product_batch():
    # Mandated plan example: 000001 is exactly on the 0.8 percentile cutoff.
    momentum = {"000001": 0.4, "000002": 0.3, "000003": 0.2, "000004": 0.1}
    rv_rank = {"000001": 0.8, "000002": 0.2, "000003": 0.3, "000004": 0.4}
    rows = []
    for s, m in momentum.items():
        rows.append(
            dict(
                date="2026-01-30",
                symbol=s,
                economic_index=1.0,
                momentum=m,
                rv20=np.nan,
                rv_rank=rv_rank[s],
                valid_count=300,
                sma200=1.0,
                distance200=0.0,
                above200=1.0,
                total_return=0.0,
                prev_quote_date=None,
            )
        )
    return fr.FactorBatch(
        values=pd.DataFrame(rows),
        missing=pd.DataFrame(columns=["date", "symbol", "field", "reason"]),
        metadata={},
    )


def test_four_variant_selection_oracle():
    batch = _four_product_batch()
    symbols = ["000001", "000002", "000003", "000004"]
    expected = {
        "E00": ["000001", "000002", "000003", "000004"],
        "E01": ["000002", "000003", "000004"],
        "E10": ["000001", "000002", "000003"],
        "E11": ["000002", "000003", "000004"],
    }
    for variant, want in expected.items():
        dec = fr.monthly_decisions(
            batch, variant=variant, completed_months=["2026-01-30"], symbols=symbols
        ).iloc[0]
        assert dec.selected.split("|") == want, variant
        weights = json.loads(dec.weights)
        assert weights == {s: (1.0 / len(want) if s in want else 0.0) for s in symbols}
    e11 = fr.monthly_decisions(
        batch, variant="E11", completed_months=["2026-01-30"], symbols=symbols
    ).iloc[0]
    assert "000001" in e11.exclusion_reasons


def test_tie_uses_symbol_code_ascending():
    rows = []
    for s in ["000004", "000002", "000003"]:
        rows.append(
            dict(
                date="2026-01-30",
                symbol=s,
                economic_index=1.0,
                momentum=0.25,
                rv20=np.nan,
                rv_rank=0.2,
                valid_count=300,
                sma200=1.0,
                distance200=0.0,
                above200=1.0,
                total_return=0.0,
                prev_quote_date=None,
            )
        )
    batch = fr.FactorBatch(
        values=pd.DataFrame(rows),
        missing=pd.DataFrame(columns=["date", "symbol", "field", "reason"]),
        metadata={},
    )
    dec = fr.monthly_decisions(
        batch,
        variant="E10",
        completed_months=["2026-01-30"],
        symbols=["000004", "000002", "000003"],
    ).iloc[0]
    assert dec.selected.split("|") == ["000002", "000003", "000004"]


def test_no_candidates_is_all_cash():
    batch = fr.FactorBatch(
        values=pd.DataFrame(
            columns=[
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
                "total_return",
                "prev_quote_date",
            ]
        ),
        missing=pd.DataFrame(columns=["date", "symbol", "field", "reason"]),
        metadata={},
    )
    dec = fr.monthly_decisions(
        batch, variant="E11", completed_months=["2026-01-30"], symbols=["000001"]
    ).iloc[0]
    assert dec.selected == ""
    assert json.loads(dec.weights) == {"000001": 0.0}


def test_replay_rejects_unknown_variant_or_fee():
    reg = d.load_registry()
    with pytest.raises(ValueError, match="variant"):
        fa.replay_account(
            registry=reg,
            batch=None,
            decisions=pd.DataFrame(),
            prices=pd.DataFrame(),
            actions=[],
            fee=0.001,
            variant="E99",
        )
    with pytest.raises(ValueError, match="fee"):
        fa.replay_account(
            registry=reg,
            batch=None,
            decisions=pd.DataFrame(),
            prices=pd.DataFrame(),
            actions=[],
            fee=0.005,
            variant="E11",
        )


# ---------------------------------------------------------------------------
# Real frozen input
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def frozen():
    reg = d.load_registry()
    d.verify_sources(reg)
    mod = fa.load_frozen_defense(reg)
    prices = pd.read_csv(
        ROOT / reg["sources"]["mixed_prices"]["path"],
        dtype={"symbol": str, "date": str},
    )
    raw_actions = json.loads(
        (ROOT / reg["sources"]["mixed_actions"]["path"]).read_text()
    )["events"]
    return reg, mod, prices, raw_actions


def _batch_and_decision(reg, prices, actions, variant):
    identity = {
        "currency": "CNY",
        "price_basis": "nominal_close",
        "symbols": list(fa.FROZEN_SYMBOLS),
        "historical_reconstruction_only": True,
    }
    batch = fr.build_mixed_batch(prices, actions, registry=reg, input_identity=identity)
    frame = batch.values
    union = sorted(frame.date.unique())
    month_ends = (
        pd.DataFrame({"date": pd.to_datetime(union)})
        .assign(m=lambda x: x.date.dt.strftime("%Y-%m"))
        .groupby("m")
        .date.max()
        .dt.strftime("%Y-%m-%d")
        .tolist()
    )
    month_ends = [m for m in month_ends if "2020-11" <= m[:7] <= "2026-06"]
    decs = fr.monthly_decisions(
        batch, variant=variant, completed_months=month_ends, symbols=list(fa.FROZEN_SYMBOLS)
    )
    return batch, decs


def test_e11_replay_matches_frozen_results_row_by_row(frozen):
    reg, mod, prices_raw, raw_actions = frozen
    batch, decs = _batch_and_decision(reg, prices_raw, raw_actions, "E11")
    for fee in (0.001, 0.002):
        out = fa.replay_account(
            registry=reg,
            batch=batch,
            decisions=decs,
            prices=prices_raw,
            actions=raw_actions,
            fee=fee,
            variant="E11",
        )
        legacy_id = f"no_exit_100-fee{fee:.3f}"
        exec_dir = ROOT / reg["sources"]["defense_results"]["path"]
        exec_dir = exec_dir.parent
        frozen_equity = pd.read_csv(exec_dir / "equity.csv", dtype={"date": str})
        frozen_equity = frozen_equity[frozen_equity.account_id == legacy_id].drop(
            columns=["account_id"]
        )
        got = out["equity"].drop(columns=["account_id"])
        pd.testing.assert_frame_equal(
            got.reset_index(drop=True),
            frozen_equity.reset_index(drop=True),
            check_exact=False,
            atol=1e-6,
            rtol=0,
        )
        # trades and signal timing/selection must line up field by field
        frozen_tr = pd.read_csv(exec_dir / "trades.csv", dtype={"date": str, "symbol": str})
        frozen_tr = frozen_tr[frozen_tr.account_id == legacy_id].reset_index(drop=True)
        got_tr = out["trades"].reset_index(drop=True)
        assert len(got_tr) == len(frozen_tr)
        for col in ("date", "symbol", "side", "qty", "price", "reason"):
            pd.testing.assert_series_equal(
                got_tr[col].astype(str),
                frozen_tr[col].astype(str),
                check_names=False,
                obj=f"trades.{col}",
            )
        for col in ("notional", "fee"):  # CSV text round-trip leaves ulp differences
            np.testing.assert_allclose(
                got_tr[col].astype(float).to_numpy(),
                frozen_tr[col].astype(float).to_numpy(),
                rtol=0,
                atol=1e-6,
                err_msg=f"trades.{col}",
            )
        frozen_sig = pd.read_csv(exec_dir / "signals.csv", dtype=str)
        frozen_sig = frozen_sig[frozen_sig.account_id == legacy_id].reset_index(drop=True)
        got_sig = out["signals"].reset_index(drop=True)
        assert len(got_sig) == len(frozen_sig)
        for col in ("eligible_date", "decision_date", "selected", "weights"):
            pd.testing.assert_series_equal(
                got_sig[col], frozen_sig[col], check_names=False, obj=f"signals.{col}"
            )
        frozen_ord = pd.read_csv(exec_dir / "orders.csv", dtype=str)
        frozen_ord = frozen_ord[frozen_ord.account_id == legacy_id]
        assert len(out["orders"]) == len(frozen_ord)
        # external identity must be E11, not the legacy name
        assert out["summary"]["account_id"] == f"E11-fee{fee:.3f}"
        assert out["summary"]["legacy_account_id"] == legacy_id


def test_e11_replay_matches_fresh_legacy_engine_call(frozen):
    reg, mod, prices_raw, raw_actions = frozen
    p, acts = mod.load()
    idx = mod.economic_indices(p, acts)
    legacy_decs = [r for r in mod.decisions(idx) if r["config"] == "momentum_top3"]
    batch, new_decs = _batch_and_decision(reg, prices_raw, raw_actions, "E11")
    for fee in (0.001, 0.002):
        legacy = mod.simulate("no_exit_100", fee, p, acts, idx, legacy_decs)
        out = fa.replay_account(
            registry=reg,
            batch=batch,
            decisions=new_decs,
            prices=prices_raw,
            actions=raw_actions,
            fee=fee,
            variant="E11",
        )
        assert out["summary"]["final"] == pytest.approx(legacy[0]["final"], abs=1e-6)
        assert out["summary"]["fees"] == pytest.approx(legacy[0]["fees"], abs=1e-6)
        assert out["summary"]["trades"] == legacy[0]["trades"]
        assert len(out["equity"]) == len(legacy[1])


def test_replay_keeps_frozen_sources_unchanged(frozen):
    reg, mod, prices_raw, raw_actions = frozen
    before = {
        k: reg["sources"][k]["sha256"]
        for k in ("defense_code", "mixed_prices", "mixed_actions")
    }
    batch, decs = _batch_and_decision(reg, prices_raw, raw_actions, "E00")
    for variant in ("E00", "E01", "E10", "E11"):
        batch, decs = _batch_and_decision(reg, prices_raw, raw_actions, variant)
        fa.replay_account(
            registry=reg,
            batch=batch,
            decisions=decs,
            prices=prices_raw,
            actions=raw_actions,
            fee=0.001,
            variant=variant,
        )
    after = {k: d.fingerprint(ROOT / reg["sources"][k]["path"])["sha256"] for k in before}
    assert before == after


# ---------------------------------------------------------------------------
# Frozen-engine execution boundaries on synthetic inputs (engine unmodified)
# ---------------------------------------------------------------------------

def _synthetic_engine_input(mod):
    # Two real pool products; the engine globals always cover the full14 list,
    # so decision weights must provide every pool symbol.
    dates = pd.bdate_range("2020-12-01", "2021-03-31")
    rows = []
    for s, base in (("510300", 10.0), ("512400", 20.0)):
        for i, day in enumerate(dates):
            close = base * (1 + 0.001 * i)
            rows.append(
                dict(
                    date=day.strftime("%Y-%m-%d"),
                    symbol=s,
                    open=close,
                    high=close * 1.002,
                    low=close * 0.998,
                    close=close,
                    volume=100000,
                )
            )
    return pd.DataFrame(rows), pd.DataFrame(
        columns=["date", "symbol", "economic_index", "sma200", "momentum", "rv_rank", "valid_count"]
    )


def _dec(decision_day, selected, weights, scores=None):
    return dict(
        config="momentum_top3",
        decision_date=decision_day,
        selected=selected,
        ranked=selected,
        lookback_start="shift252",
        lookback_end="shift21",
        scores=json.dumps(scores or {}),
        weights=json.dumps(weights),
        trend_states=json.dumps({s: "x" for s in selected.split("|") if s}),
    )


def _weights(mod, chosen):
    return {s: (1.0 if s == chosen else 0.0) for s in mod.SYMS}


def test_engine_boundaries_via_frozen_simulate(frozen):
    reg, mod, _, _ = frozen
    p, idx = _synthetic_engine_input(mod)
    acts = []

    def run(decs, prices=None):
        prices = p if prices is None else prices
        return mod.simulate("no_exit_100", 0.001, prices, acts, idx, decs)

    first_quote = p.date.iloc[0]
    # 1. no candidates -> all cash, zero trades
    empty_weights = {s: 0.0 for s in mod.SYMS}
    s, daily, trades, *_ = run([_dec("2020-11-30", "", empty_weights)])
    assert trades == []
    assert all(r["equity"] == 1_000_000 for r in daily)

    # 2. missing open on execution day -> no trade that day
    prices_bad = p.copy()
    prices_bad.loc[
        (prices_bad.date == first_quote) & (prices_bad.symbol == "510300"), "open"
    ] = np.nan
    _, _, trades_bad, orders_bad, *_ = run(
        [_dec("2020-11-30", "510300", _weights(mod, "510300"), {"510300": 0.1})], prices_bad
    )
    assert all(t["date"] != first_quote for t in trades_bad)
    assert any(o["status"] == "delayed" and o["date"] == first_quote for o in orders_bad)

    # 3. sells execute before buys on the same day
    decs1 = [_dec("2020-11-30", "510300", _weights(mod, "510300"), {"510300": 0.1})]
    _, _, t0, *_ = run(decs1)
    assert t0 and t0[0]["side"] == "buy"
    second_decision_day = "2021-01-29"
    exec_day = min(x for x in p.date.unique() if x > second_decision_day)
    decs2 = decs1 + [
        _dec(second_decision_day, "512400", _weights(mod, "512400"), {"512400": 0.1})
    ]
    _, _, t2, *_ = run(decs2)
    day_trades = [t for t in t2 if t["date"] == exec_day]
    sides = [t["side"] for t in day_trades]
    assert sides[0] == "sell"
    assert sides == sorted(sides, key=lambda x: 0 if x == "sell" else 1)

    # 4. lot residual: buying 100% must not overspend cash (final cash nonnegative)
    _, daily2, *_ = run(decs1)
    assert daily2[-1]["cash"] >= 0

    # 5. corporate action on the monthly execution day: a split adjusts units
    # before the monthly target is evaluated; cash/receivable stay consistent.
    split_day = min(x for x in p.date.unique() if x > "2021-01-29")
    actions_split = [
        dict(
            event_id="510300-split-1",
            symbol="510300",
            type="split",
            effective_date=split_day,
            ratio=2.0,
        )
    ]
    s3, d3, t3, o3, sig3, events3, *_ = mod.simulate(
        "no_exit_100", 0.001, p, [mod.action_fields(a) for a in actions_split], idx, decs2
    )
    split_event = [e for e in events3 if e["event"] == "split"]
    assert split_event and split_event[0]["date"] == split_day
    # equity accounting identity holds on the action day: cash + receivable + MV
    row = next(r for r in d3 if r["date"] == split_day)
    mv = sum(row[f"units_{s}"] * row_close(p, split_day, s) for s in ("510300", "512400"))
    assert abs(row["cash"] + row["receivable"] + mv - row["equity"]) < 1e-6
    assert row["cash"] >= 0


def row_close(p, day, symbol):
    rows = p[(p.date == day) & (p.symbol == symbol)]
    return float(rows.close.iloc[0]) if len(rows) else 0.0
