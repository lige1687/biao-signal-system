from datetime import date, timedelta
from math import sqrt

import pytest

from lei_signal.market_context.observation_panel import (
    build_card,
    month_end,
    nowcast,
    volatility,
)


def points(count, value=lambda i: i, step=1, start=date(2020, 1, 1)):
    return [
        {"date": (start + timedelta(days=i * step)).isoformat(), "value": value(i)}
        for i in range(count)
    ]


def test_daily_statistics_use_only_window_ending_on_each_date():
    rows = points(253)
    card = build_card({"frequency": "daily", "points": rows})
    assert card["points"][18]["ma20"] is None
    assert card["points"][19]["ma20"] == 9.5
    assert card["points"][250]["mean"] is None
    previous, current = card["points"][-2:]
    sigma = sqrt((252**2 - 1) / 12)
    assert previous["mean"] == 125.5
    assert current["mean"] == 126.5
    assert current["std"] == pytest.approx(sigma)
    assert current["band_upper_1_5"] == pytest.approx(126.5 + 1.5 * sigma)
    assert current["band_lower_2_0"] == pytest.approx(126.5 - 2 * sigma)
    assert card["current_zscore"] == 1.7
    assert card["current_zscore_raw"] == pytest.approx(125.5 / sigma)
    assert card["current_percentile"] == 100
    assert card["observations"] == 253


def test_ties_missing_data_and_secondary_lines_have_separate_statistics():
    rows = points(157, lambda i: 10 if i < 156 else None, step=7)
    alternative = points(157, lambda i: -i, step=7)
    card = build_card(
        {
            "frequency": "weekly",
            "points": rows,
            "lines": [
                {"id": "alt", "label": "另一口径", "points": alternative},
            ],
        }
    )
    assert card["points"][3]["ma20"] == 10
    assert card["points"][-1]["ma20"] is None
    assert card["points"][-2]["std"] == 0
    assert card["current_zscore"] is None and card["current_percentile"] is None
    assert card["lines"][0]["current_percentile"] == 0
    assert card["lines"][0]["points"][-1]["ma20"] == -154.5
    tied = build_card({"frequency": "weekly", "points": rows[:-1]})
    assert tied["current_zscore"] is None and tied["current_percentile"] == 50


def test_monthly_series_never_gets_moving_average_or_backfilled_statistics():
    rows = [{"date": month_end(2019, i).isoformat(), "value": i} for i in range(61)]
    card = build_card({"frequency": "monthly", "points": rows})
    assert card["points"][-1]["ma20"] is None
    assert card["window"] == 60 and card["points"][-2]["mean"] == 29.5
    assert card["points"][-1]["mean"] == 30.5
    with pytest.raises(ValueError, match="date"):
        build_card({"frequency": "monthly", "points": rows + [rows[-1]]})


def test_volatility_has_20_and_60_distinct_return_warmups():
    rows = points(75, lambda i: 100 + i + (-1) ** i)
    short, long = volatility(rows)
    assert short[19]["value"] is None and short[20]["value"] > 0
    assert long[59]["value"] is None and long[60]["value"] > 0


def test_nowcast_strict_cutoffs_and_complete_three_inputs():
    margin = [{"date": month_end(2018, i).isoformat(), "value": 100 + i + i**2} for i in range(106)]
    start = date(2018, 1, 4)
    aaii = [
        dict(row, available_at=row["date"])
        for row in points(
            470,
            lambda i: i % 31,
            step=7,
            start=start,
        )
    ]
    naaim = [
        dict(row, available_at=row["date"])
        for row in points(
            470,
            lambda i: i % 37,
            step=7,
            start=start,
        )
    ]
    after = date(2025, 12, 31)
    cutoff = date(2026, 2, 10)
    baseline = nowcast(margin, aaii, naaim, after, cutoff)
    assert [row["date"] for row in baseline] == ["2026-01-31", "2026-02-10"]
    assert all(row["value"] is not None for row in baseline)
    naaim.append({"date": "2026-02-06", "available_at": "2026-02-11", "value": 10000})
    assert nowcast(margin, aaii, naaim, after, cutoff) == baseline
    assert all(row["value"] is None for row in nowcast(margin, aaii, [], after, cutoff))
