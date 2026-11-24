"""Small synthetic checks; no archived or live market-effect run."""

from __future__ import annotations

import copy

import pytest

from lei_signal.research.factor_curve_extension import build_targets
from lei_signal.research.factor_curve_rank_diagnostics import rank_records
from lei_signal.research.fip import month_add

SHA = "a" * 64
PERIODS = {
    "all": ["2016-02", "2025-12"],
    "early": ["2016-02", "2018-12"],
    "middle": ["2019-01", "2021-12"],
    "late": ["2022-01", "2025-12"],
}
DESIGN = {"formation": ["2016-01", "2025-11"], "minimum_names": 30, "periods": PERIODS}


def fixture(*, short_first=False, green_first_three=False, constant_first=False, unknown_first=3):
    months = []
    month = "2016-01"
    while month <= "2025-11":
        months.append(month)
        month = month_add(month, 1)
    calendar = [f"{month}-28" for month in months]
    old, residual, derived = [], [], []
    for index, month in enumerate(months):
        size = 29 if short_first and index == 0 else 30
        for i in range(size):
            code = f"s{i:03d}"
            identity = {"month": month, "code": code, "decision_date": calendar[index]}
            old.append(
                {
                    **identity,
                    "green": not green_first_three or index != 0 or i < 3,
                    "momentum": i + 1,
                    "vol60": i + 1,
                    "holding_month": month_add(month, 1),
                    "entry_date": f"{month_add(month, 1)}-01",
                    "exit_date": f"{month_add(month, 2)}-01",
                    "return": None if index == 0 and i < unknown_first else (i * 7) % 31,
                }
            )
            residual.append(
                {
                    **identity,
                    "reasons": [],
                    "ordinary": i + 1,
                    "residual": 30 - i,
                    "scaled_control": i + 1,
                }
            )
            derived.append(
                {
                    **identity,
                    "qualified": True,
                    "reasons": [],
                    "momentum20": i + 1,
                    "momentum60": i + 1,
                    "momentum120": i + 1,
                    "ma_distance": i + 1,
                    "ppo": 1 if constant_first and index == 0 else i + 1,
                    "downside": -(30 - i),
                }
            )
    frozen = build_targets(old, residual, derived, months, calendar, min_names=30)
    return old, residual, derived, frozen


@pytest.fixture(scope="module")
def normal():
    return fixture()


def run(parts):
    return rank_records(*parts, DESIGN, SHA)


def pick(records, factor="momentum20", pool="all_qualified", period="all"):
    return next(
        r for r in records if (r["factorId"], r["poolId"], r["periodId"]) == (factor, pool, period)
    )


def test_full_axis_80_records_maturity_and_known_pair_sizes(normal):
    records = run(normal)
    assert len(records) == 80
    row = pick(records)
    assert row["range"] == ["2016-01", "2025-11"]
    assert row["evaluationRange"] == ["2016-02", "2025-12"]
    assert len(row["points"]) == 119
    assert row["points"][0] == ["2016-01-28", row["points"][0][1], 27, 30]
    assert row["points"][-1][0] == "2025-11-28"
    assert "2026-01" in row["labelDefinition"]
    assert row["nPeriods"] == 119
    assert row["minAssets"] == 27
    assert row["medianAssets"] == 30
    assert row["coverage"] == (119 * 30 - 3) / (119 * 30)
    assert pick(records, period="late")["points"][0][0] == "2021-12-28"


@pytest.mark.parametrize("source", [0, 1, 2])
def test_duplicate_source_key_rejected(normal, source):
    parts = list(normal)
    parts[source] = [*parts[source], parts[source][0]]
    with pytest.raises(ValueError, match="duplicate"):
        run(parts)


@pytest.mark.parametrize("source", [0, 1, 2])
def test_formation_date_mismatch_rejected(normal, source):
    parts = list(normal)
    parts[source] = [dict(row) for row in parts[source]]
    parts[source][0]["decision_date"] = "2016-01-27"
    with pytest.raises(ValueError, match="decision date"):
        run(parts)


def test_frozen_pool_mismatch_rejected(normal):
    parts = list(normal)
    parts[3] = copy.deepcopy(parts[3])
    parts[3]["targets"]["all_qualified__pool"]["2016-01-28"]["weights"].pop("s000")
    with pytest.raises(ValueError, match="frozen targets mismatch"):
        run(parts)


def test_under_30_retains_null_month_on_full_axis():
    records = run(fixture(short_first=True))
    row = pick(records)
    assert row["points"][0] == ["2016-01-28", None, 0, 29]
    assert row["points"][1][0] == "2016-02-28"
    assert row["nPeriods"] == 118
    assert row["coverage"] == 1
    assert "不足30只月份1个" in row["limitations"]


def test_three_green_names_retained_without_coverage_denominator():
    records = run(fixture(green_first_three=True))
    row = pick(records, pool="green_only")
    assert row["points"][0] == ["2016-01-28", None, 0, 3]
    assert row["points"][1][1] is not None
    assert row["coverage"] == 1
    assert row["nPeriods"] == 118


def test_unknown_future_keeps_eligible_pool_and_coverage(normal):
    parts = list(normal)
    parts[0] = [dict(row) for row in parts[0]]
    for row in parts[0]:
        if row["month"] == "2016-01":
            row["return"] = None
    row = pick(run(parts))
    assert row["points"][0] == ["2016-01-28", None, 0, 30]
    assert row["points"][1][1] is not None
    assert row["coverage"] == 118 / 119


def test_constant_rank_keeps_null_month_and_known_coverage():
    row = pick(run(fixture(constant_first=True)), factor="ppo")
    assert row["points"][0] == ["2016-01-28", None, 27, 30]
    assert row["points"][1][1] is not None
    assert row["nPeriods"] == 118
    assert row["minAssets"] == 30
    assert row["coverage"] == (119 * 30 - 3) / (119 * 30)


def test_factor_orientation_and_frozen_group_membership(normal):
    records = run(normal)
    high_momentum = pick(records, "momentum20")["points"][1][1]
    low_vol = pick(records, "lowvol")["points"][1][1]
    downside = pick(records, "downside")["points"][1][1]
    distance = pick(records, "ma_distance")["points"][1][1]
    assert high_momentum == distance
    assert low_vol == -high_momentum
    assert downside == high_momentum


def test_malformed_holding_or_last_maturity_rejected(normal):
    parts = list(normal)
    parts[0] = [dict(row) for row in parts[0]]
    parts[0][0]["holding_month"] = "2016-01"
    with pytest.raises(ValueError, match="holding month"):
        run(parts)
    parts[0][0]["holding_month"] = "2016-02"
    parts[0][-1]["exit_date"] = "2025-12-31"
    with pytest.raises(ValueError, match="exit month"):
        run(parts)


def test_future_label_dates_must_agree_within_month(normal):
    parts = list(normal)
    parts[0] = [dict(row) for row in parts[0]]
    parts[0][0]["exit_date"] = "2016-03-02"
    with pytest.raises(ValueError, match="future label date mismatch"):
        run(parts)
