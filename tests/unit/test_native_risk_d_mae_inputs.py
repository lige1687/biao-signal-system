"""Artificial identity mutations only; no frozen original is read here."""

from __future__ import annotations

import importlib.util
import inspect
from datetime import date, timedelta
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[2] / "src/lei_signal/research/native_risk_d_mae_inputs.py"
SPEC = importlib.util.spec_from_file_location("native_risk_d_mae_inputs", MODULE)
assert SPEC and SPEC.loader
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


COUNTS = {
    "510050.SS": 15,
    "510300.SS": 17,
    "510500.SS": 12,
    "512400.SS": 5,
    "512800.SS": 26,
    "588000.SS": 1,
}
GROUPS = {
    "510050.SS": 6,
    "510300.SS": 7,
    "510500.SS": 5,
    "512400.SS": 3,
    "512800.SS": 11,
    "588000.SS": 1,
}
OTHER_FEATURES = [
    ("synthetic.ppo", "ppo-v1"),
    ("synthetic.b1", "b1-v1"),
    ("synthetic.bottom", "bottom-v1"),
]


def artificial_documents():
    sources = ["bars", "calendar", adapter.ORIGINALS["validated-input-binding.json"][1]]
    feature_list = [
        {
            "feature_id": adapter.FEATURE_ID,
            "variant_id": adapter.VARIANT_ID,
            "atr_definition": {"method": "simple_average"},
        }
    ]
    feature_list += [{"feature_id": fid, "variant_id": variant} for fid, variant in OTHER_FEATURES]
    docs = {
        "deduplicated-cases.json": [],
        "native-early-events.json": [],
        "x-panel-long.json": [],
        "validated-input-binding.json": {
            "bars_sha256": "bars",
            "calendar_sha256": "calendar",
            "price_basis_by_asset": {a: {"price_basis_id": "economic_price"} for a in COUNTS},
        },
        "feature-contract.json": {"contract_id": "artificial", "features": feature_list},
        "label-protocol.json": {"price_cutoff": "2026-06-26"},
    }
    metadata = {
        "case_sha256": adapter.ORIGINALS["deduplicated-cases.json"][1],
        "calendar_sha256": "calendar",
        "exact_cases": 76,
        "native_events": 84,
        "asset_lifecycle_groups": 33,
        "calendar_mature_count": 75,
        "new_X_values_computed": 0,
        "new_Y_values_computed": 0,
        "same_asset_signal_date_keys": 76,
        "repeated_same_asset_signal_date": {},
        "per_asset_case_count": COUNTS,
        "per_asset_calendar_mature_count": {a: n for a, n in COUNTS.items() if a != "588000.SS"},
        "all_window_metadata": [],
        "not_date_qualified": [],
    }
    index = 0
    for asset, count in COUNTS.items():
        for j in range(count):
            index += 1
            cid = adapter.UNKNOWN_CASE_ID if index == 76 else f"artificial-case:{index}"
            signal = str(date(2025, 1, 1) + timedelta(days=index))
            touch = str(date(2024, 12, 31) + timedelta(days=index))
            lifecycle = f"artificial-lifecycle:{asset}:{j % GROUPS[asset]}"
            aliases = [f"artificial-event:{index}:0"]
            if index <= 8:
                aliases.append(f"artificial-event:{index}:1")
            periods = [20 + 40 * k for k in range(len(aliases))]
            case = {
                "case_id": cid,
                "event_id": aliases[0],
                "member_event_ids": aliases,
                "member_ma_periods": periods,
                "ma": periods[0],
                "asset": asset,
                "date": signal,
                "lifecycle": lifecycle,
                "touch_date": touch,
                "a3_source": "artificial",
                "a3_structure_id": None,
                "A": 2.0,
                "C": 1.0,
                "ATR": 1.0,
                "D": 1.0,
                "price_basis_id": "economic_price",
                "source_sha256": sources,
                "calendar_id": "artificial-calendar",
            }
            docs["deduplicated-cases.json"].append(case)
            window = {
                "case_id": cid,
                "asset": asset,
                "signal_date": signal,
                "label_start": "artificial-next",
                "label_end": None if index == 76 else "artificial-end",
                "calendar_mature_by_20260626": index != 76,
                "reason": "end_beyond_frozen_calendar" if index == 76 else None,
            }
            metadata["all_window_metadata"].append(window)
            if index == 76:
                metadata["not_date_qualified"].append(window)
            for eid, ma in zip(aliases, periods, strict=True):
                event = {
                    "event_id": eid,
                    "symbol": asset,
                    "event_date": signal,
                    "available_date": signal,
                    "lifecycle_id": lifecycle,
                    "evidence": {
                        "touch_date": touch,
                        "ma_period": ma,
                        "a3_source": "artificial",
                        "a3_structure_id": None,
                        "entry_ref_close": 2.0,
                        "stop_price": 1.0,
                        "atr20": 1.0,
                        "entry_variant": "early",
                    },
                }
                docs["native-early-events.json"].append(event)
                for feature in feature_list:
                    docs["x-panel-long.json"].append(
                        {
                            "signal_event_id": eid,
                            "feature_id": feature["feature_id"],
                            "variant_id": feature["variant_id"],
                            "contract_sha256": adapter.ORIGINALS["feature-contract.json"][1],
                            "contract_id": "artificial",
                            "source_sha256": sources,
                            "asset_id": asset,
                            "asof_session_date": signal,
                            "entry_variant": "early",
                            "price_basis_id": "economic_price",
                            "calendar_id": "artificial-calendar",
                            "value": 1.0,
                            "formula_value": None,
                            "quality_status": "ok",
                            "arrival_certification_status": "historical_arrival_unknown",
                            "live_eligible": False,
                            "opportunity_group_key": [asset, lifecycle, ma, touch],
                        }
                    )
    return docs, metadata


def test_artificial_population_preserves_aliases_and_unknown():
    docs, metadata = artificial_documents()
    result = adapter._validate_identity(docs, metadata)
    assert result["counts"] == {
        "cases": 76,
        "events": 84,
        "long_rows": 336,
        "D_rows": 84,
        "asset_lifecycle_groups": 33,
        "calendar_mature": 75,
        "calendar_unknown": 1,
    }
    assert result["cases"][0]["event_ids"] == ["artificial-event:1:0", "artificial-event:1:1"]
    assert result["cases"][-1]["case_id"] == adapter.UNKNOWN_CASE_ID


def test_member_period_list_order_is_not_event_order():
    docs, metadata = artificial_documents()
    docs["deduplicated-cases.json"][0]["member_ma_periods"] = [60, 20]
    result = adapter._validate_identity(docs, metadata)
    first = result["cases"][0]
    assert first["member_ma_periods"] == [60, 20]
    assert first["event_ma_period"] == {"artificial-event:1:0": 20, "artificial-event:1:1": 60}


@pytest.mark.parametrize(
    "mutation,pattern",
    [
        (lambda d, m: d["deduplicated-cases.json"][0].update(D=2.0), "case/D row mismatch"),
        (
            lambda d, m: d["deduplicated-cases.json"][0]["member_event_ids"].append(
                "artificial-event:2:0"
            ),
            "case alias identity mismatch",
        ),
        (
            lambda d, m: d["x-panel-long.json"][0].update(source_sha256=["wrong"]),
            "long row binding mismatch",
        ),
        (
            lambda d, m: d["x-panel-long.json"][0].update(variant_id="wrong"),
            "long row binding mismatch",
        ),
        (
            lambda d, m: d["native-early-events.json"][0]["evidence"].update(stop_price=0.5),
            "case/event value",
        ),
        (
            lambda d, m: d["deduplicated-cases.json"][0].update(member_ma_periods=[20, 120]),
            "member MA periods mismatch",
        ),
        (
            lambda d, m: m["all_window_metadata"][0].update(signal_date="wrong"),
            "window case/date mismatch",
        ),
        (
            lambda d, m: d["deduplicated-cases.json"][1].update(
                date=d["deduplicated-cases.json"][0]["date"]
            ),
            "repeated asset/date case",
        ),
        (lambda d, m: d["deduplicated-cases.json"][0].update(ATR=float("nan")), "positive finite"),
    ],
)
def test_rejects_identity_mutations(mutation, pattern):
    docs, metadata = artificial_documents()
    mutation(docs, metadata)
    with pytest.raises(adapter.IdentityError, match=pattern):
        adapter._validate_identity(docs, metadata)


def test_strict_json_rejects_duplicate_and_nonfinite():
    for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}'):
        with pytest.raises(adapter.IdentityError):
            adapter._strict_json(raw, "artificial")


def test_real_loader_has_no_path_or_expected_hash_override():
    assert len(inspect.signature(adapter.load_original_identity).parameters) == 0
    assert adapter.ORIGINALS["deduplicated-cases.json"][1] == (
        "7540cbe16abec5e6c5dbe9569ab0879d2160d2f4a86c640556f3550aba633bb7"
    )
