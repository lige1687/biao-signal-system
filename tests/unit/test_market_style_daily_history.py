from datetime import date
import hashlib
import json

import pytest

from lei_signal.market_style_observation import daily_history as daily
from lei_signal.market_style_observation.review import apply_daily_answers, question_cards


def rows():
    return [["Index Level :", "Gross"], ["Currency :", "USD"],
            ["Date", *[item[3] for item in daily.INDEXES]],
            ["Oct 16, 2026", "100", "100", "100", "100", "100"],
            ["Oct 19, 2026", "110", "120", "105", "99", "101"],
            ["Oct 20, 2026", "105", "108", "106", "98", "102"], [""]]


def history():
    points = daily.parse_export_rows(rows(), requested_end=date(2026, 10, 21))
    return dict(available=True, points=points, retrieved_at="2026-10-21T12:00:00Z", source_url=daily.SOURCE,
                fingerprint="test", source_sha256="test", refresh_failed=False)


def test_official_column_identity_is_validated_and_order_independent():
    source = rows()
    for row in source[2:6]:
        row[1], row[2] = row[2], row[1]
    points = daily.parse_export_rows(source, requested_end=date(2026, 10, 21))
    assert points[-1]["world"] == 105
    assert points[-1]["momentum"] == 108


@pytest.mark.parametrize("mutation", ["net", "eur", "wrong_index", "duplicate", "future", "negative"])
def test_unqualified_source_is_rejected(mutation):
    source = rows()
    if mutation == "net": source[0][1] = "Net"
    if mutation == "eur": source[1][1] = "EUR"
    if mutation == "wrong_index": source[2][2] = "WORLD SECTOR NEUTRAL QUALITY"
    if mutation == "duplicate": source[4][0] = source[3][0]
    if mutation == "future": source[5][0] = "Oct 22, 2026"
    if mutation == "negative": source[5][2] = "-1"
    with pytest.raises(ValueError):
        daily.parse_export_rows(source, requested_end=date(2026, 10, 21))


def test_return_difference_is_not_relative_wealth_ratio_and_drawdown_is_path_based():
    view = daily.build_window(history(), 365)
    m = next(s for s in view["series"] if s["id"] == "momentum")
    assert m["return_pct"] == pytest.approx(8)
    assert m["excess_pp"] == pytest.approx(3)
    assert m["relative"][-1] == pytest.approx(108 / 105 * 100)
    assert m["max_drawdown_pct"] == pytest.approx(-10)
    assert all(x == pytest.approx(100) for x in view["series"][0]["relative"])


def test_missing_value_is_not_interpolated_and_risk_is_withheld():
    h = history()
    h["points"][1]["momentum"] = None
    m = daily.build_window(h, 365)["series"][1]
    assert m["wealth"] == [100, None, 108]
    assert m["relative"][1] is None
    assert m["max_drawdown_pct"] is None
    assert m["volatility_pct"] is None


def test_all_series_use_same_start_and_latest_common_date():
    h = history()
    h["points"][0]["quality"] = None
    view = daily.build_window(h, 365)
    assert view["start"] == "2026-10-19"
    assert all(s["wealth"][0] == 100 for s in view["series"])
    h = history()
    h["points"][-1]["quality"] = None
    view = daily.build_window(h, 365)
    assert view["end"] == "2026-10-19"
    assert view["latest_source_date"] == "2026-10-20"


def test_five_questions_take_daily_evidence_but_keep_monthly_valuation_date():
    cards = question_cards({}, "cn")
    apply_daily_answers(cards, daily.build_window(history(), 365))
    assert cards[0]["data_date"] == "2026-10-20"
    assert cards[0]["source_ids"] == ["msci_daily"]
    assert "+3.00个百分点" in cards[1]["fact"]
    assert cards[2]["data_date"] == "2026-09-30"
    assert "估值 2026-09-30" in cards[3]["data_date"]
    assert "历史最高点" in cards[3]["watch"]


def test_same_day_reads_do_not_fetch_and_failed_refresh_keeps_flagged_cache(monkeypatch):
    h = {**history(), "schema": 1, "currency": "USD", "variant": "GRTR", "frequency": "daily",
         "request_date": daily.datetime.now(daily.timezone.utc).date().isoformat()}
    monkeypatch.setattr(daily, "_MEMORY", h)
    monkeypatch.setattr(daily, "_LAST_ERROR", False)
    monkeypatch.setattr(daily, "_RETRY_AFTER", 0)
    calls = []
    def unavailable(*args, **kwargs):
        calls.append(args)
        raise TimeoutError("test timeout")
    monkeypatch.setattr(daily, "urlopen", unavailable)
    assert daily.get_history()["available"]
    assert not calls
    h["request_date"] = "2000-01-01"
    assert daily.get_history()["refresh_failed"]
    assert len(calls) == 1
    assert daily.get_history()["refresh_failed"]
    assert len(calls) == 1  # failure cooldown prevents one request per render


def test_html_with_success_status_is_not_an_excel_export():
    with pytest.raises(ValueError, match="expected_xls_not_html"):
        daily.parse_export(b"<html>Loading</html>", requested_end=date(2026, 10, 21))
