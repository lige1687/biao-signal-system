from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent / "research-package"
TENTH = HERE.parents[1] / "research-tenth-2026-09-08" / "cd-contract"
sys.path.insert(0, str(PACKAGE / "src"))

from lei_signal.domain.rules_config import get_rule  # noqa: E402
from lei_signal.rules import module_d_false_breakout as d  # noqa: E402
from lei_signal.rules import two_b_reversal as c  # noqa: E402


def _load(name: str) -> pd.DataFrame:
    return pd.read_csv(TENTH / name, index_col="date", parse_dates=True)


def _serial(events: list) -> list[dict]:
    return [
        {
            "event_id": event.event_id,
            "available_date": str(event.available_date),
            "lifecycle_id": event.lifecycle_id,
            "evidence": event.evidence,
        }
        for event in events
    ]


def test_c_new_breakdown_uses_only_latest_confirmed_low() -> None:
    frame = _load("c-recent-valley.csv")
    confirmed = [
        event
        for event in c.detect_two_b_reversal_events(frame, "SYNTH")
        if event.evidence["sub_rule"] == c.SUB_RULE_V1
    ]
    assert {event.evidence["l1_price"] for event in confirmed} == {101.0}


def test_c_all_27_prefixes_equal_published_full_history() -> None:
    frame = _load("c-recent-valley.csv")
    full = _serial(c.detect_two_b_reversal_events(frame, "SYNTH"))
    for cut in range(1, 28):
        prefix = _serial(c.detect_two_b_reversal_events(frame.iloc[:cut], "SYNTH"))
        known = [event for event in full if event["available_date"] <= str(frame.index[cut - 1].date())]
        assert prefix == known, f"C prefix {cut} changed published fields"


def test_d_new_breakdown_uses_only_latest_confirmed_valley() -> None:
    frame = _load("d-recent-valley.csv")
    confirmed = [
        event
        for event in d.detect_module_d_events(frame, "SYNTH")
        if event.evidence["sub_rule"] == d.SUB_RULE_CONFIRMED
    ]
    assert {event.evidence["valley_price"] for event in confirmed} == {99.2}


def test_d_all_219_prefixes_equal_published_full_history_all_fields() -> None:
    frame = _load("d-future-zone-end.csv")
    full = _serial(d.detect_module_d_events(frame, "SYNTH"))
    for cut in range(1, 220):
        prefix = _serial(d.detect_module_d_events(frame.iloc[:cut], "SYNTH"))
        known = [event for event in full if event["available_date"] <= str(frame.index[cut - 1].date())]
        assert prefix == known, f"D prefix {cut} changed published fields"


def test_d_zone_stays_open_for_first_20_absent_bars_and_ends_on_21st() -> None:
    frame = _load("d-future-zone-end.csv")
    reclaim_window, threshold, minimum, exit_bars = d._params(get_rule(d.RULE_ID))
    del reclaim_window
    through_20 = d._zone_intervals(frame.iloc[:211], threshold, minimum, exit_bars)
    through_21 = d._zone_intervals(frame.iloc[:212], threshold, minimum, exit_bars)
    assert through_20[-1][1] == 211
    assert through_21[-1][1] == 211


def test_d_zone_reentry_on_21st_bar_keeps_same_zone_open() -> None:
    frame = _load("d-future-zone-end.csv").iloc[:212].copy()
    # 第 21 根重新满足密集条件：离开计数应清零，不能结束旧区间。
    frame.iloc[-1, frame.columns.get_loc("ema120")] = 100.0
    _, threshold, minimum, exit_bars = d._params(get_rule(d.RULE_ID))
    intervals = d._zone_intervals(frame, threshold, minimum, exit_bars)
    assert intervals[-1][1] == len(frame)


def test_imports_are_from_eleventh_research_package() -> None:
    assert Path(c.__file__).resolve().is_relative_to(PACKAGE)
    assert Path(d.__file__).resolve().is_relative_to(PACKAGE)
