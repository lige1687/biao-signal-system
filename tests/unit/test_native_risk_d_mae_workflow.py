"""Artificial-only acceptance examples for the frozen D/V close-MAE20 adapter."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from lei_signal.research import native_risk_d_mae_workflow as native


def artificial_inputs():
    """76 invented cases, 84 invented aliases, 33 invented lifecycle groups."""
    dates = []
    current = date(2025, 12, 1)
    while current <= date(2026, 7, 31):
        if current.weekday() < 5:
            dates.append(current.isoformat())
        current += timedelta(days=1)
    grouped = (6, 6, 5, 3, 12, 1)
    cases, windows = [], {}
    retained = {asset: dates[:] for asset in native.ASSETS}
    prices = {}
    serial = 0
    for asset_index, (asset, n, group_count) in enumerate(zip(native.ASSETS, native.COUNTS, grouped)):
        prices[asset] = {
            day: {"close": round(100 + 7 * asset_index + i * 0.07 + ((i + asset_index) % 9 - 4) * 1.3, 6),
                  "status": "quoted", "action_known": True}
            for i, day in enumerate(dates)
        }
        for local in range(n):
            cid = f"artificial-case-{serial:03d}"
            signal_day = "2026-06-16" if asset == "588000.SS" else dates[20 + local]
            lifecycle = f"artificial-life-{asset_index}-{local % group_count}"
            A = float(100 + 2 * local + asset_index)
            atr = float(2 + (local + asset_index) / 10)
            D = float((local % 11 + 1) / 10 + asset_index * 0.03)
            C = A - D * atr
            event_ids = [f"artificial-event-{serial:03d}"]
            if serial < 8:
                event_ids.append(f"artificial-extra-{serial:03d}")
            cases.append({"case_id": cid, "asset": asset, "signal_date": signal_day,
                          "lifecycle": lifecycle, "event_ids": event_ids,
                          "A": A, "C": C, "ATR20_SMA": atr, "D": D})
            future = dates[dates.index(signal_day) + 1:dates.index(signal_day) + 22]
            mature = future[-1] <= native.CUTOFF
            windows[cid] = {"asset": asset, "signal_date": signal_day,
                            "label_start": future[0], "label_end": future[-1] if mature else None,
                            "calendar_mature_by_20260626": mature}
            serial += 1
    return ({"schema_version": "native-d-mae-x/1.0", "artificial_only": True, "cases": cases},
            {"schema_version": "native-d-mae-y/1.0", "artificial_only": True,
             "cutoff": native.CUTOFF, "windows": windows, "retained_dates": retained,
             "prices": prices})


def test_x_only_keeps_exact_structure_and_has_no_outcomes():
    x, _ = artificial_inputs()
    rows = native.prepare_x(x)
    assert len(rows) == 76
    assert sum(len(r["event_ids"]) for r in rows) == 84
    assert len({(r["asset"], r["lifecycle"]) for r in rows}) == 33
    assert all("Y" not in r and "closes" not in r for r in rows)
    assert rows[0]["D"] == x["cases"][0]["D"]


def test_path_qualification_and_comparison_hold_one_fixed_denominator():
    x, y = artificial_inputs()
    rows = native.prepare_x(x)
    paths, unknown = native.validate_y_paths(rows, y)
    assert len(paths) == 75
    assert unknown == "artificial-case-075"
    result = native.evaluate_y(rows, paths, unknown)
    assert len(result["rows"]) == 76
    assert sum(row["Y"] is not None for row in result["rows"]) == 75
    assert result["rows"][-1]["label_reason"] == "beyond_frozen_cutoff"
    assert len(result["statistics"]["leave_one_lifecycle"]) == 33
    for asset in native.ASSETS:
        detail = result["statistics"]["per_asset"][asset]
        assert detail["complete_cases"] == len(detail["complete_case_ids"])


@pytest.mark.parametrize("bad", [None, 0, "false", False])
def test_explicit_unknown_action_encoding_is_rejected(bad):
    assert native.path_close({"close": 100, "status": "quoted", "action_known": bad}) is None
    assert native.path_close({"close": 100}) == 100


def test_any_halt_blocks_whole_75_path_batch():
    x, y = artificial_inputs()
    case = x["cases"][0]
    bad_day = y["windows"][case["case_id"]]["label_start"]
    y["prices"][case["asset"]][bad_day]["status"] = "halted"
    with pytest.raises(ValueError, match="full 21-close path"):
        native.validate_y_paths(native.prepare_x(x), y)


def test_unknown_case_can_end_at_cutoff_without_future_quotes():
    x, y = artificial_inputs()
    asset = "588000.SS"
    y["retained_dates"][asset] = [day for day in y["retained_dates"][asset] if day <= native.CUTOFF]
    paths, unknown = native.validate_y_paths(native.prepare_x(x), y)
    assert len(paths) == 75 and unknown == "artificial-case-075"


def test_unknown_case_needs_calendar_through_cutoff():
    x, y = artificial_inputs()
    asset = "588000.SS"
    y["retained_dates"][asset] = [day for day in y["retained_dates"][asset] if day < native.CUTOFF]
    with pytest.raises(ValueError, match="unknown window contradicts cutoff"):
        native.validate_y_paths(native.prepare_x(x), y)


def test_v_nonfinite_result_rejected_after_arithmetic():
    with pytest.raises(ValueError, match="nonfinite"):
        native.volatility_scale(1e308, 1e308)


def test_reference_price_not_running_peak():
    assert native.close_mae20([100, 110, 105] + [105] * 18) == 0
    assert native.close_mae20([100, 90] + [100] * 19) == pytest.approx(10)


def test_fixed_asset_set_does_not_reweight_after_deletion():
    x, y = artificial_inputs()
    rows = native.prepare_x(x)
    paths, unknown = native.validate_y_paths(rows, y)
    result = native.evaluate_y(rows, paths, unknown)
    fixed = result["statistics"]["primary"]["fixed_assets"]
    assert all(s["fixed_asset_summary"]["fixed_assets"] == fixed
               for s in result["statistics"]["leave_one_lifecycle"])
