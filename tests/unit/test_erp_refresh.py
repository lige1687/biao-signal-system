import copy
import json

import pytest

from lei_signal.fundamentals.erp_refresh import build_live_reference, parse_daily_page


def fixture():
    rows = [{"date": f"2026-09-{i:02d}", "value": 6.0, "close": 4000.0} for i in range(1, 29)]
    base = {"points": copy.deepcopy(rows), "asOf": "2026-09-28", "historicalOnly": True}
    return base, rows


def test_current_week_keeps_one_latest_observation_and_frozen_history():
    base, rows = fixture()
    before = copy.deepcopy(base)
    rows += [{"date": d, "value": 5.8, "close": 4100.0} for d in ("2026-10-01", "2026-10-02", "2026-10-05")]
    result = build_live_reference(base, rows, "2026-10-02")
    assert base == before
    assert result["points"][:28] == base["points"]
    assert result["points"][-1]["date"] == "2026-10-02"
    assert len(result["points"]) == 29
    assert result["historicalOnly"] is False


def test_source_drift_or_wrong_index_date_is_rejected():
    base, rows = fixture()
    rows[0]["value"] = 7.0
    with pytest.raises(ValueError, match="alignment"):
        build_live_reference(base, rows, "2026-09-30")


def test_daily_parser_rejects_duplicate_and_respects_closed_date():
    rows = [{"date": f"2026-10-{i:02d}", "spread": 6, "cp": 4000, "ratio": 4} for i in range(1, 32)]
    page = '沪深300 PE-TTM var seriesByRange=' + json.dumps({"1": rows}) + ';'
    assert parse_daily_page(page, "2026-10-29")[-1]["date"] == "2026-10-29"
    rows[1] = rows[0]
    with pytest.raises(ValueError, match="duplicated"):
        parse_daily_page('沪深300 PE-TTM var seriesByRange=' + json.dumps({"1": rows}), "2026-10-29")
