"""Independent review: hand-derived examples plus a fixed finite input inventory.

No production edits, no legacy-oracle import, no performance/return selection.
Run with PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -p no:cacheprovider.
"""
from dataclasses import asdict
from itertools import product
from pathlib import Path
import sys

import pandas as pd
import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "research-package"
sys.path.insert(0, str(PACKAGE / "src"))
from lei_signal.rules import strict_structure as strict

assert Path(strict.__file__).resolve().is_relative_to(PACKAGE.resolve())


def frame(intervals, mirror=False):
    rows = [(100 + lo, 100 + hi) for lo, hi in intervals]
    if mirror:
        rows = [(200 - hi, 200 - lo) for lo, hi in rows]
    return pd.DataFrame(rows, columns=["low", "high"],
                        index=pd.bdate_range("2024-01-01", periods=len(rows)))


def signature(f, mirror=False):
    # Use ordinal dates to keep hand-worked expectations readable.
    days = list(f.index.date)
    def price(p):
        return 100 - p if mirror else p - 100
    return [
        (days.index(s.confirmed_date) + 1, price(s.reference_price),
         price(s.trigger_price), price(s.final_price),
         days.index(s.reference_date) + 1, s.contained_bars_merged,
         days.index(s.invalidated_date) + 1 if s.invalidated_date else None)
        for s in strict.detect_strict_structures(f)
        if s.side == ("top" if mirror else "bottom")
    ]


@pytest.mark.parametrize("mirror", [False, True])
def test_published_confirmation_can_fail_and_next_structure_can_form(mirror):
    # 1,2,3 confirm. 4 is inside 3. 5 engulfs that tail and breaches 1.
    # 5,6,7 then form a new structure; the previous publication remains dated 3.
    f = frame([(0, 2), (1, 3), (2, 4), (2.5, 3.5),
               (-1, 5), (0, 6), (1, 7)], mirror)
    assert signature(f, mirror) == [(3, 0, 3, 4, 1, 2, 5),
                                     (7, -1, 6, 7, 5, 4, None)]


@pytest.mark.parametrize("mirror", [False, True])
def test_equal_price_levels_on_different_dates_remain_distinct(mirror):
    # The final three intervals repeat 1,2,3 at later dates. Both confirmations
    # must survive even though reference, trigger, and final prices are equal.
    f = frame([(0, 2), (1, 3), (2, 4), (-1, 1),
               (0, 2), (1, 3), (2, 4)], mirror)
    assert signature(f, mirror) == [(3, 0, 3, 4, 1, 2, 4),
                                     (6, -1, 2, 3, 4, 2, None),
                                     (7, 0, 3, 4, 5, 2, None)]


@pytest.mark.parametrize("mirror", [False, True])
def test_unconfirmed_candidate_can_be_replaced_by_tail_containment(mirror):
    # Day 3 swallows day 2 before confirmation and extends below day 1.
    # Only the new reference from day 3 can be confirmed, on day 5.
    f = frame([(0, 2), (1, 3), (-1, 4), (0, 5), (1, 6)], mirror)
    assert signature(f, mirror) == [(5, -1, 5, 6, 3, 3, None)]


@pytest.mark.parametrize("mirror", [False, True])
def test_contained_tail_deduplicates_old_setup_and_preserves_next_setup(mirror):
    # Days 4 and 5 extend the completed date, but never create another copy
    # of day 3's publication. The next candidate's day-2 anchor remains usable.
    f = frame([(0, 2), (1, 3), (2, 4), (2.5, 3.5),
               (2, 4), (3, 5), (4, 6)], mirror)
    assert signature(f, mirror) == [(3, 0, 3, 4, 1, 2, None),
                                     (6, 1, 4, 5, 2, 4, None),
                                     (7, 2, 5, 6, 5, 4, None)]


def test_fixed_exhaustive_event_history_and_first_extreme_breach():
    # Fixed beforehand: every ordered length-five sequence of four intervals.
    # Tests containment/equality and both directions, without a legacy oracle.
    intervals = [(0, 2), (1, 3), (2, 4), (-1, 5)]
    for sequence in product(intervals, repeat=5):
        f = frame(sequence)
        full = [asdict(e) for e in strict.detect_strict_structure_events(f, "REVIEW")]
        assert len({e["event_id"] for e in full}) == len(full), sequence
        structures = strict.detect_strict_structures(f)
        assert len({s.structure_id for s in structures}) == len(structures), sequence
        for s in structures:
            later = f.loc[f.index.date > s.confirmed_date]
            hits = later["high"] > s.reference_price if s.side == "top" else later["low"] < s.reference_price
            expected = later.index[hits][0].date() if hits.any() else None
            assert s.invalidated_date == expected, sequence
        for n in range(1, 6):
            day = f.index[n - 1].date()
            actual = [asdict(e) for e in strict.detect_strict_structure_events(f.iloc[:n], "REVIEW")]
            assert actual == [e for e in full if e["available_date"] <= day], (sequence, n)
