"""Artificial-only Y path, comparison, grant, and one-shot checks."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "src/lei_signal/research/native_risk_d_mae_real_y.py"
SPEC = importlib.util.spec_from_file_location("native_risk_d_mae_real_y", SOURCE)
assert SPEC and SPEC.loader
y = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(y)


def artificial_inputs():
    retained = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(177)]
    counts = {
        "510050.SS": 15,
        "510300.SS": 17,
        "510500.SS": 12,
        "512400.SS": 5,
        "512800.SS": 26,
        "588000.SS": 1,
    }
    groups = {
        "510050.SS": 6,
        "510300.SS": 7,
        "510500.SS": 5,
        "512400.SS": 3,
        "512800.SS": 11,
        "588000.SS": 1,
    }
    rows = []
    i = 0
    for asset, count in counts.items():
        for j in range(count):
            i += 1
            unknown = i == 76
            signal = "2026-06-16" if unknown else retained[i]
            position = retained.index(signal)
            future = retained[position + 1 : position + 22]
            cid = y.UNKNOWN_ID if unknown else f"artificial-case:{i}"
            event_ids = [f"artificial-event:{i}:0"]
            if i <= 8:
                event_ids.append(f"artificial-event:{i}:1")
            rows.append(
                {
                    "case_id": cid,
                    "asset": asset,
                    "signal_date": signal,
                    "lifecycle": f"artificial-lifecycle:{asset}:{j % groups[asset]}",
                    "event_ids": event_ids,
                    "event_ma_period": {eid: 20 for eid in event_ids},
                    "D_frozen": 1.0 + i / 100,
                    "V_volatility_pct": 1.0 + (i % 7) / 10,
                    "price_basis_id": "economic_price",
                    "source_sha256": [y.PRICE_SHA, y.CALENDAR_SHA],
                    "window_metadata": {
                        "label_start": future[0],
                        "label_end": None if unknown else future[-1],
                        "calendar_mature_by_20260626": not unknown,
                        "reason": "end_beyond_frozen_calendar" if unknown else None,
                    },
                }
            )
    closes = {(asset, day): 100.0 - (n % 9) for asset in counts for n, day in enumerate(retained)}
    return rows, retained, closes


def test_all_paths_qualified_before_y_and_unknown_retained():
    rows, retained, closes = artificial_inputs()
    paths, unknown = y._validate_paths(rows, retained, closes)
    assert len(paths) == 75 and unknown == y.UNKNOWN_ID
    assert sum(len(p["closes"]) for p in paths.values()) == 1575
    result = y._evaluate(rows, paths, unknown)
    assert len(result["rows"]) == 76 and len(result["paths"]) == 75
    assert result["rows"][-1]["Y"] is None
    assert len(result["statistics"]["leave_one_lifecycle"]) == 33
    assert y._mae([100] + [101] * 20) == 0
    assert y._mae([100] + [101] * 19 + [80]) == pytest.approx(20)


@pytest.mark.parametrize(
    "change,pattern",
    [
        (lambda r, d, c: r[0]["window_metadata"].update(label_start=d[3]), "t\\+1 window start"),
        (lambda r, d, c: r[0]["window_metadata"].update(label_end=d[23]), "21-session end"),
        (lambda r, d, c: c.update({(r[0]["asset"], d[2]): 0}), "full 21-close path"),
        (lambda r, d, c: c.update({(r[0]["asset"], d[22]): float("nan")}), "full 21-close path"),
        (lambda r, d, c: c.pop((r[0]["asset"], d[22])), "full 21-close path"),
        (
            lambda r, d, c: r[-1]["window_metadata"].update(calendar_mature_by_20260626=True),
            "21-session end",
        ),
    ],
)
def test_rejects_bad_windows_or_incomplete_paths(change, pattern):
    rows, retained, closes = artificial_inputs()
    change(rows, retained, closes)
    with pytest.raises(y.RealYError, match=pattern):
        y._validate_paths(rows, retained, closes)


def test_last_mature_bad_close_blocks_all_y(monkeypatch):
    rows, retained, closes = artificial_inputs()
    last = rows[-2]
    closes[(last["asset"], last["window_metadata"]["label_end"])] = 0
    calls = []
    monkeypatch.setattr(y, "_mae", lambda path: calls.append(path))
    with pytest.raises(y.RealYError, match="full 21-close path"):
        y._validate_paths(rows, retained, closes)
    assert calls == []


def test_original_shape_parser_ignores_lows_and_postcutoff_close():
    import json

    start = date(2019, 9, 1)
    days = [(start + timedelta(days=i)).isoformat() for i in range(2495)]
    calendar = {
        "schema_version": "research-trading-calendar/1.1",
        "days": {
            day: {"is_trading_day": True, "source_flag": "artificial", "source_month": day[:7]}
            for day in days
        },
    }
    bars = []
    for asset in y.ASSETS:
        for i in range(1337):
            day = "2026-06-27" if i == 1336 else days[i]
            bars.append(
                {
                    "asset": asset,
                    "date": day,
                    "open": 10,
                    "high": 10,
                    "low": -999,
                    "close": 10,
                    "volume": 1,
                }
            )
    retained, closes = y._parse_sources(
        json.dumps({"bars": bars}).encode(), json.dumps(calendar).encode()
    )
    assert len(retained) > 0
    assert closes[(y.ASSETS[0], days[0])] == 10
    assert (y.ASSETS[0], "2026-06-27") not in closes


def test_constant_tied_and_two_case_rank_edges():
    assert y._rho([1, 1, 1], [1, 2, 3]) is None
    assert y._rho([1], [2]) is None
    assert 0 < y._rho([1, 1, 2, 3], [1, 2, 2, 3]) < 1
    rows = [
        {
            "asset": "510050.SS",
            "lifecycle": "a",
            "case_id": "one",
            "D_frozen": 1,
            "V_volatility_pct": 2,
            "Y": 1,
        },
        {
            "asset": "510050.SS",
            "lifecycle": "b",
            "case_id": "two",
            "D_frozen": 2,
            "V_volatility_pct": 1,
            "Y": 2,
        },
    ]
    per = y._per_asset(rows)
    assert per["510050.SS"]["n2_degenerate"] is True
    assert per["510050.SS"]["rho_D_Y"] == 1
    assert per["510050.SS"]["rho_V_Y"] == -1
    assert per["510050.SS"]["rho_D_minus_V"] == 2
    assert per["510050.SS"]["complete_asset_lifecycle_groups"] == 2


def test_incomplete_d_or_v_excluded_from_common_cases():
    rows = [
        {
            "asset": "510050.SS",
            "lifecycle": "a",
            "case_id": "one",
            "D_frozen": 1,
            "V_volatility_pct": 2,
            "Y": 1,
        },
        {
            "asset": "510050.SS",
            "lifecycle": "b",
            "case_id": "two",
            "D_frozen": 2,
            "V_volatility_pct": None,
            "Y": 2,
        },
    ]
    per = y._per_asset(rows)["510050.SS"]
    assert per["all_cases"] == 2 and per["complete_cases"] == 1
    assert per["asset_lifecycle_groups"] == 2
    assert per["complete_asset_lifecycle_groups"] == 1
    assert per["rho_D_Y"] is None and per["reason"] == "n_lt_2"


def test_fixed_asset_delete_does_not_reweight():
    rows = [
        {
            "asset": asset,
            "lifecycle": str(i),
            "case_id": f"{asset}:{i}",
            "D_frozen": i,
            "V_volatility_pct": 3 - i,
            "Y": i,
        }
        for asset in ("510050.SS", "510300.SS")
        for i in (1, 2)
    ]
    fixed = ("510050.SS", "510300.SS")
    primary = y._fixed_global(y._per_asset(rows), fixed)
    assert primary["asset_count"] == 2
    remaining = [r for r in rows if r["case_id"] != "510050.SS:1"]
    deleted = y._fixed_global(y._per_asset(remaining), fixed)
    assert deleted["fixed_assets"] == list(fixed)
    assert deleted["rho_D_minus_V"] is None
    assert deleted["reason"] == "fixed_asset_became_uncomputable"


def _grant():
    return {
        "schema": "native-risk-d-mae-real-y-grant/1",
        "approved": True,
        "stage": "real_y",
        "design_sha256": y.DESIGN_SHA,
        "executor_contract_sha256": y.CONTRACT_SHA,
        "stage_a_sha256": y.STAGE_A_SHA,
        "stage_x_sha256": y.STAGE_X_SHA,
        "executable_sha256": "artificial-code",
        "x_sha256": y.X_SHA,
        "x_receipt_sha256": y.X_RECEIPT_SHA,
        "x_grant_sha256": y.X_GRANT_SHA,
        "x_ledger_sha256": "a" * 64,
        "membership_sha256": y.X_MEMBERSHIP_SHA,
        "original_sha256": {"artificial-original": "b" * 64},
        "prices_sha256": y.PRICE_SHA,
        "calendar_sha256": y.CALENDAR_SHA,
        "output_plan_sha256": y.PLAN_SHA,
        "output": str(y.OUTPUT),
        "real_y_directory": str(y.REAL_Y_DIR),
        "external_mount": str(y.MOUNT),
        "external_device": y.MOUNT_DEVICE,
        "external_uuid": y.MOUNT_UUID,
        "ledger_path": str(y.LEDGER_PATH),
        "permissions": dict(y.PERMISSIONS),
    }


@pytest.mark.parametrize(
    "change,pattern",
    [
        (lambda g: g.update(approved=False), "missing or invalid Y grant"),
        (lambda g: g.update(executable_sha256="changed"), "Y grant code/source"),
        (lambda g: g.update(x_receipt_sha256="changed"), "Y grant code/source"),
        (lambda g: g.update(membership_sha256="changed"), "Y grant code/source"),
        (lambda g: g.update(prices_sha256="changed"), "Y grant code/source"),
        (lambda g: g.update(real_y_directory=str(y.OUTPUT / "other")), "Y grant code/source"),
        (lambda g: g.update(ledger_path=str(y.LEDGER_PATH) + "2"), "Y grant code/source"),
        (lambda g: g.update(external_device=float(y.MOUNT_DEVICE)), "Y grant code/source"),
        (lambda g: g["permissions"].update(real_Y_passes=True), "Y grant permissions"),
        (lambda g: g["permissions"].update(fits=False), "Y grant permissions"),
        (lambda g: g["permissions"].update(auto_retries=1), "Y grant permissions"),
    ],
)
def test_grant_rejections(change, pattern):
    grant = _grant()
    change(grant)
    with pytest.raises(y.RealYError, match=pattern):
        y._validate_grant(
            grant,
            {
                "output": str(y.OUTPUT),
                "external_uuid": y.MOUNT_UUID,
                "external_device": y.MOUNT_DEVICE,
            },
            "artificial-code",
        )


def test_missing_grant_and_bad_json():
    with pytest.raises(y.RealYError, match="grant fields"):
        y._validate_grant(None, {}, "artificial-code")
    for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}'):
        with pytest.raises(y.RealYError):
            y._json(raw, "artificial")


def test_one_shot_replay_and_readback_change(tmp_path):
    ledger = tmp_path / "artificial-y-ledger.jsonl"
    y._start_ledger(ledger, {"status": "started", "output": "first"})
    with pytest.raises(y.RealYError, match="already consumed"):
        y._start_ledger(ledger, {"status": "started", "output": "other"})
    assert len(ledger.read_text().splitlines()) == 1
    result = tmp_path / "artificial-result.json"
    y._write(result, b'{"artificial":true}')
    y._readback(result, y._sha(result.read_bytes()))
    result.write_bytes(b'{"artificial":false}')
    with pytest.raises(y.RealYError, match="readback differs"):
        y._readback(result, y._sha(b'{"artificial":true}'))


def test_public_entry_refuses_override(monkeypatch):
    monkeypatch.setattr(sys, "argv", [str(y.SOURCE_PATH), "--price", "other"])
    with pytest.raises(y.RealYError, match="accepts no override"):
        y.main()
