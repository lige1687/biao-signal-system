"""Validation guards for staged observation source refresh."""

from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/refresh_market_observation_history.py"
spec = importlib.util.spec_from_file_location("observation_source_refresh", SCRIPT)
refresh = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(refresh)


def test_fred_needs_expected_schema_and_coverage():
    raw = b"observation_date,NFCI\n2026-10-23,-0.467\n2026-10-30,-0.459\n"
    assert refresh.fred_points(raw, "NFCI", date(2026, 11, 9), 2)[-1] == {
        "date": "2026-10-30",
        "value": -0.459,
    }
    with pytest.raises(ValueError):
        refresh.fred_points(raw, "NFCI", date(2026, 11, 9), 156)
    with pytest.raises(ValueError):
        refresh.fred_points(b"date,NFCI\n2026-10-30,-0.459\n", "NFCI", date(2026, 11, 9), 1)


def test_sse_requires_510300_and_matching_date():
    row = {
        "SECURITY_CODE": "510300",
        "TRADE_DATE": "2026-11-06",
        "PUT_VOLUME": "276,350",
        "CALL_VOLUME": "434,050",
        "LEAVES_PUT_QTY": "477,183",
        "LEAVES_CALL_QTY": "717,209",
    }
    result = refresh.sse_point({"result": [row]}, date(2026, 11, 6))
    assert result == {"date": "2026-11-06", "volume": 0.636678, "oi": 0.665333}
    assert refresh.sse_point({"result": [row]}, date(2026, 11, 5)) is None
    assert refresh.sse_point({"result": [{**row, "CALL_VOLUME": "0"}]}, date(2026, 11, 6)) is None


def test_atomic_stage_replaces_complete_file(tmp_path):
    target = tmp_path / "overrides.json"
    target.write_text("old")
    refresh.atomic(target, json.dumps({"points": []}).encode())
    assert json.loads(target.read_text()) == {"points": []}


def test_vxn_cboe_requires_matching_overlap_before_append():
    from datetime import timedelta

    first = date(2025, 1, 1)
    days = [first + timedelta(days=i) for i in range(252)]
    points = [{"date": day.isoformat(), "value": 20.0} for day in days]
    text = "DATE,OPEN,HIGH,LOW,CLOSE\n" + "".join(f"{day:%m/%d/%Y},20,20,20,20\n" for day in days)
    next_day = days[-1] + timedelta(days=1)
    text += f"{next_day:%m/%d/%Y},21,21,21,21\n"
    assert refresh.vxn_with_cboe(points, text.encode(), next_day)[-1] == {
        "date": next_day.isoformat(),
        "value": 21.0,
    }
    with pytest.raises(ValueError):
        refresh.vxn_with_cboe(
            points, text.replace("20,20,20,20", "20,20,20,19", 1).encode(), next_day
        )
