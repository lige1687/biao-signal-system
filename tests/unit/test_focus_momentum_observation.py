"""Frozen historical display bundle: source identity, dates, and explicit staleness."""

from __future__ import annotations

import csv
import json
import math
from datetime import date as system_date
from pathlib import Path

import pytest

from lei_signal.market_context import focus_momentum


ROOT = Path(__file__).resolve().parents[2]


def test_real_archived_snapshot_matches_export_values() -> None:
    bundle = focus_momentum.build_observation_bundle(ROOT)
    assert bundle["schemaVersion"] == 1
    assert bundle["definitionId"] == focus_momentum.DEFINITION_ID
    assert bundle["historicalOnly"] is True
    assert bundle["current"] is None
    assert bundle["asOf"] == "2025-12-31"
    assert len(bundle["series"]) == 2674
    assert bundle["series"][0]["date"] == "2015-01-05"
    assert bundle["series"][-1]["date"] == "2025-12-31"
    assert all(point["date"] <= bundle["asOf"] for point in bundle["series"])

    with (ROOT / focus_momentum.DAILY_REL).open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    last, prior = rows[-1], rows[-2]
    assert bundle["latest"]["focus"] == float(last["focus"])
    assert bundle["latest"]["poolMomentum"] == float(last["pool_momentum"])
    assert bundle["latest"]["concentration"] == float(last["concentration"])
    assert bundle["latest"]["members"] == json.loads(last["focus_members"])
    assert bundle["latest"]["changeFocus"] == float(last["focus"]) - float(prior["focus"])
    assert len(bundle["research"]["comparisons"]) == 2
    assert {row["target"] for row in bundle["research"]["comparisons"]} == {"CSI300", "CSI1000"}
    assert bundle["source"]["sha256"][focus_momentum.WEEKLY_REL] == focus_momentum.EXPECTED_SHA256[focus_momentum.WEEKLY_REL]


def test_mapping_matches_frozen_common_weeks_and_daily_focus() -> None:
    bundle = focus_momentum.build_observation_bundle(ROOT)
    mapping = bundle["mapping"]
    assert (mapping["frequency"], mapping["horizonSessions"]) == ("weekly", 20)
    assert (mapping["sampleStart"], mapping["sampleEnd"], mapping["labelEndMax"]) == (
        "2015-01-09", "2025-12-12", "2026-01-13")
    assert mapping["us"]["status"] == "unavailable"
    targets = {row["target"]: row for row in mapping["targets"]}
    assert set(targets) == {"CSI300", "CSI1000"}
    dates = [p["date"] for p in targets["CSI300"]["points"]]
    assert len(dates) == len(set(dates)) == 560
    assert dates == [p["date"] for p in targets["CSI1000"]["points"]]
    daily = {p["date"]: p["focus"] for p in bundle["series"]}
    with (ROOT / focus_momentum.WEEKLY_REL).open(newline="", encoding="utf-8") as source:
        original = {(r["target"], r["date"]): r for r in csv.DictReader(source)}
    for target, row in targets.items():
        points = row["points"]
        assert len(points) == 560
        assert row["baselineMean"] == pytest.approx(
            math.fsum(float(r["label"]) for (t, _), r in original.items() if t == target) / 560)
        assert max(p["labelEnd"] for p in points) == "2026-01-13"
        for point in points:
            archived = original[(target, point["date"])]
            assert point["focus"] == daily[point["date"]] == float(archived["focus"])
            assert point["forwardReturn"] == float(archived["label"])
            assert point["labelEnd"] == archived["label_end"]
            assert point["date"] < point["labelEnd"] <= "2026-01-15"


def test_tampered_or_missing_source_cannot_build_bundle() -> None:
    wrong = dict(focus_momentum.EXPECTED_SHA256)
    wrong[focus_momentum.DAILY_REL] = "0" * 64
    with pytest.raises(ValueError, match="verification hash differs"):
        focus_momentum.build_observation_bundle(ROOT, expected_hashes=wrong)
    wrong_weekly = dict(focus_momentum.EXPECTED_SHA256)
    wrong_weekly[focus_momentum.WEEKLY_REL] = "0" * 64
    with pytest.raises(ValueError, match="verification hash differs"):
        focus_momentum.build_observation_bundle(ROOT, expected_hashes=wrong_weekly)
    with pytest.raises(FileNotFoundError):
        focus_momentum.build_observation_bundle(ROOT / "missing-source-root")


def test_historical_date_does_not_follow_export_time(monkeypatch: pytest.MonkeyPatch) -> None:
    class FutureDate:
        @classmethod
        def fromisoformat(cls, value: str) -> system_date:
            return system_date.fromisoformat(value)

        @classmethod
        def today(cls) -> None:
            raise AssertionError("export must not inspect wall-clock date")

    monkeypatch.setattr(focus_momentum, "date", FutureDate)
    bundle = focus_momentum.build_observation_bundle(ROOT)
    assert bundle["current"] is None
    assert bundle["asOf"] == "2025-12-31"
    assert bundle["latest"]["date"] == "2025-12-31"
