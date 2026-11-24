"""Arithmetic and split-window boundaries for fixed relative-volume candidates."""

from datetime import date, timedelta
import math

import pytest

from lei_signal.research import price_volume_path_information as path


@pytest.mark.parametrize("n", [20, 60])
def test_concentration_dispersion_trend_and_scale(n):
    days = [{"range": 0.02, "close_location": 0.2, "wick_balance": -0.1,
             "volume": 100.0 * math.exp(i / n)} for i in range(n)]
    values = path.candidate_values(days, n)
    weights = [d["volume"] / sum(x["volume"] for x in days) for d in days]
    assert values["volume_concentration"] == pytest.approx(n * sum(p*p for p in weights) - 1)
    assert values["log_volume_slope"] == pytest.approx((n-1)/n)
    assert values["log_volume_std"] > 0
    assert values["volume_close_location_excess"] == pytest.approx(0)
    assert values["volume_range_excess"] == pytest.approx(0)
    assert values["volume_wick_excess"] == pytest.approx(0)
    scaled = [{**d, "volume": d["volume"] * 10000} for d in days]
    for field in ("volume_concentration", "log_volume_std", "log_volume_slope",
                  "volume_close_location_excess", "volume_range_excess", "volume_wick_excess"):
        assert path.candidate_values(scaled, n)[field] == pytest.approx(values[field])
    uniform = [{**d, "volume": 100.0} for d in days]
    for field in ("volume_concentration", "log_volume_std", "log_volume_slope"):
        assert path.candidate_values(uniform, n)[field] == pytest.approx(0)


@pytest.mark.parametrize("n", [20, 60])
def test_weighted_intraday_excess_matches_manual_and_missing_volume(n):
    days = [{"range": 0.01 + i/1000, "close_location": (i % 3 - 1)/2,
             "wick_balance": (i % 4 - 2)/3, "volume": float(i+1)} for i in range(n)]
    actual = path.candidate_values(days, n)
    total = sum(d["volume"] for d in days)
    for source, field in (("range", "volume_range_excess"),
                          ("close_location", "volume_close_location_excess"),
                          ("wick_balance", "volume_wick_excess")):
        manual = sum(d[source]*d["volume"] for d in days)/total - sum(d[source] for d in days)/n
        assert actual[field] == pytest.approx(manual)
    missing = [dict(d) for d in days]
    missing[-1]["volume"] = None
    output = path.candidate_values(missing, n)
    assert output["range_mean"] is not None
    assert all(output[field] is None for field in path.FORMULAS[3:])


def test_known_split_restarts_volume_window_without_resetting_price_clock():
    dates = [(date(2022, 1, 1) + timedelta(days=i)).isoformat() for i in range(310)]
    bars = []
    for asset in ("synthetic-A", "synthetic-B"):
        for i, day in enumerate(dates):
            close = 100 + i/10 + math.sin(i/5)
            bars.append({"asset": asset, "date": day, "status": "quoted", "open": close-0.2,
                         "high": close+0.5, "low": close-0.7, "close": close,
                         "volume": float(100+i%17), "volume_break": asset=="synthetic-B" and i==280})
    payload = {"data_mode": "synthetic", "calendar": dates, "bars": bars}
    contract = {"feature": {"kind": path.KIND, "candidate": "volume_concentration20",
               "definition_ref": path.REFS["volume_concentration20"], "lookback": 20,
               "warmup": 252, "missing_policy": "segmented", "anchor_asset": "synthetic-A"},
               "universe": {"assets": ["synthetic-A", "synthetic-B"]},
               "question": {"period": [dates[0], dates[-1]]},
               "target": {"kind": "mae", "start_offset": 1, "end_offset": 21,
                          "entry_field": "close", "path_field": "close",
                          "unit": "percentage_point", "price_measure": "economic_price"}}
    rows = path.prepare_observations(payload, contract)["observations"]
    by_id = {r["id"]: r for r in rows}
    assert by_id[f"synthetic-B|{dates[279]}"]["eligible"]
    assert not by_id[f"synthetic-B|{dates[280]}"]["eligible"]
    assert not by_id[f"synthetic-B|{dates[298]}"]["eligible"]
    assert by_id[f"synthetic-B|{dates[299]}"]["eligible"]
    assert by_id[f"synthetic-A|{dates[280]}"]["eligible"]
