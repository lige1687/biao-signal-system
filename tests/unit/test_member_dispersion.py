from datetime import date, timedelta
from math import sqrt
from statistics import stdev

import pytest

from lei_signal.market_context.member_dispersion import build_member_dispersion


def point_series(count):
    return [
        {
            "date": (date(2020, 1, 1) + timedelta(days=i)).isoformat(),
            "disp_raw": i,
            "index_close": 100 + i,
            "pct_above_ma20": 55,
            "pct_above_ma60": 60,
            "sector_disp_raw": i * 2,
        }
        for i in range(count)
    ]


def packet(points):
    return {
        "schemaVersion": 1,
        "cards": [{
            "id": "cn-current-members-daily-dispersion",
            "sources": {key: key for key in ("members", "breadth", "index", "sectors")},
            "points": points,
        }],
    }


def build(points):
    return build_member_dispersion(packet(points))["cards"][0]["points"]


def test_percentiles_use_previous_sessions_and_linear_quantiles():
    raw = point_series(259)
    raw[0]["disp_raw"] = 10000
    raw[257]["disp_raw"] = 0
    rows = build(raw)
    assert rows[63]["disp_sample_count"] == 59
    assert rows[63]["disp_pct_252d"] is None
    assert rows[64]["disp_sample_count"] == 60
    assert rows[64]["disp_pct_252d"] == pytest.approx(100 * 59 / 60)
    assert rows[64]["disp_p20"] == pytest.approx(14.8)
    assert rows[64]["disp_p50"] == pytest.approx(32.5)
    assert rows[64]["disp_p80"] == pytest.approx(50.2)
    assert rows[255]["disp_sample_count"] == 251
    assert rows[256]["disp_sample_count"] == 252
    assert rows[257]["disp_sample_count"] == 252
    assert rows[257]["disp_ma5"] == 203.6
    assert rows[257]["disp_pct_252d"] == pytest.approx(100 * 201 / 252)
    assert rows[258]["disp_sample_count"] == 252


def test_dispersion_percentile_counts_ma5_ties_at_midrank():
    raw = point_series(65)
    for row in raw:
        row["disp_raw"] = 7
    assert build(raw)[-1]["disp_pct_252d"] == 50


def test_calendar_holes_limit_reference_and_break_strict_windows():
    raw = point_series(256)
    for row in raw[5:200]:
        row["disp_raw"] = None
    raw[240]["index_close"] = None
    rows = build(raw)
    assert rows[-1]["disp_sample_count"] == 52  # Index 4 and indices 204 through 254.
    assert rows[-1]["disp_pct_252d"] is None
    assert rows[203]["disp_ma5"] is None
    assert rows[204]["disp_ma5"] == 202
    assert rows[218]["disp_ma20"] is None
    assert rows[219]["disp_ma20"] == 209.5
    assert rows[239]["index_rv20"] is not None
    assert rows[-1]["index_rv20"] is None


def test_index_rv_and_sector_ratio_on_exact_sessions():
    raw = point_series(90)
    rows = build(raw)
    assert rows[4]["sector_dominance_ratio"] is None
    assert rows[5]["sector_dominance_ratio"] == 2
    assert rows[64]["sector_dominance_pct"] is None
    assert rows[65]["sector_dominance_pct"] == 50
    assert rows[19]["index_rv20"] is None
    expected = stdev((100 + i) / (99 + i) - 1 for i in range(1, 21)) * sqrt(252) * 100
    assert rows[20]["index_rv20"] == pytest.approx(expected)
    assert rows[79]["rv_sample_count"] == 59
    assert rows[79]["rv20_pct_252d"] is None
    assert rows[80]["rv_sample_count"] == 60
    assert rows[80]["rv20_pct_252d"] == 0


def test_warmup_only_supplies_index_and_missing_current_rank_stays_null():
    raw = point_series(90)
    for row in raw[:25]:
        for name in ("disp_raw", "pct_above_ma20", "pct_above_ma60", "sector_disp_raw"):
            row[name] = None
    raw[-1]["disp_raw"] = None
    rows = build(raw)
    assert rows[20]["index_rv20"] is not None
    assert rows[88]["disp_sample_count"] == 59
    assert rows[-1]["disp_sample_count"] == 60
    assert rows[-1]["disp_p50"] == 56.5
    assert rows[-1]["disp_pct_252d"] is None
    assert rows[-1]["regime_diagnosis"] is None


def test_breadth_divergence_needs_five_declines_and_nonfalling_index():
    raw = point_series(9)
    for index in range(6):
        raw[index]["pct_above_ma20"] = 50 - index
    raw[5]["index_close"] = raw[0]["index_close"]
    raw[6]["pct_above_ma20"] = 44
    raw[6]["index_close"] = raw[1]["index_close"] - 1
    raw[7]["pct_above_ma20"] = None
    raw[8]["pct_above_ma20"] = 43
    rows = build(raw)
    assert rows[4]["breadth_divergence"] is None
    assert rows[5]["breadth_divergence"] is True
    assert rows[6]["breadth_divergence"] is False
    assert rows[8]["breadth_divergence"] is None


@pytest.mark.parametrize("field,value", [
    ("date", "2020-1-3"),
    ("date", "2020-01-01"),
    ("date", "2020-01-04"),
    ("disp_raw", -1),
    ("disp_raw", float("nan")),
    ("index_close", 0),
    ("index_close", True),
    ("pct_above_ma20", 101),
    ("pct_above_ma60", "40"),
    ("sector_disp_raw", float("inf")),
])
def test_rejects_malformed_and_misaligned_rows(field, value):
    raw = point_series(4)
    raw[2][field] = value
    with pytest.raises(ValueError, match=field):
        build(raw)


@pytest.mark.parametrize("disp,breadth,rv,divergence,expected", [
    (40, 20, 70, True, "PANIC"),
    (70, 19, 70, True, "VOLATILE_DISAGREEMENT"),
    (70, 34.9, 69, False, "SIPHON_WARNING"),
    (65, 55, 69, True, "SIPHON_WARNING"),
    (60, 50, 69.9, False, "HEALTHY_ROTATION"),
    (40, 65, 70, False, "BROAD_TREND"),
    (70, 35, 69, False, "BALANCED"),
    (60, 50, 70, False, "BALANCED"),
    (40, 20.1, 70, False, "BALANCED"),
    (None, 20, 70, True, None),
    (70, None, 70, True, None),
    (70, 20, None, True, None),
])
def test_diagnoses_and_precedence(disp, breadth, rv, divergence, expected):
    from lei_signal.market_context.member_dispersion import _diagnose

    assert _diagnose(disp, breadth, rv, divergence) == expected


def test_build_wires_regime_and_high_dispersion_low_breadth():
    raw = point_series(85)
    raw[81]["pct_above_ma20"] = 35
    raw[82]["pct_above_ma20"] = 34.9
    raw[83]["pct_above_ma20"] = None
    rows = build(raw)
    assert rows[80]["regime_diagnosis"] == "HEALTHY_ROTATION"
    assert rows[81]["high_disp_low_breadth"] is False
    assert rows[82]["high_disp_low_breadth"] is True
    assert rows[82]["regime_diagnosis"] == "SIPHON_WARNING"
    assert rows[83]["high_disp_low_breadth"] is None
    assert rows[83]["regime_diagnosis"] is None


def test_validates_schema_and_unique_card_ids():
    raw = packet(point_series(1))
    raw["cards"].append(raw["cards"][0])
    with pytest.raises(ValueError, match="id"):
        build_member_dispersion(raw)
    raw["schemaVersion"] = True
    with pytest.raises(ValueError, match="schemaVersion"):
        build_member_dispersion(raw)
    raw = packet(point_series(1))
    del raw["cards"][0]["points"][0]["sector_disp_raw"]
    with pytest.raises(ValueError, match="sector_disp_raw"):
        build_member_dispersion(raw)
