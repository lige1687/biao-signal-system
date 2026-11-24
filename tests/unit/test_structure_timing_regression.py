"""Synthetic software regressions; no market data or strategy-profit assertions.

Run with PYTHONPATH pointing at the chosen isolated base/fixed src directory.
Expected dates and prices below are written independently of detector output.
"""

from __future__ import annotations

import unittest
from dataclasses import asdict
from unittest.mock import patch

import pandas as pd

from lei_signal.backtest import engine
from lei_signal.rules import strict_structure as strict


def bars(ranges: list[tuple[float, float]]) -> pd.DataFrame:
    """Input pairs are high/low; every row is a unique ascending business day."""
    index = pd.bdate_range("2024-01-01", periods=len(ranges))
    return pd.DataFrame(
        [
            {
                "open": (high + low) / 2,
                "high": high,
                "low": low,
                "close": (high + low) / 2,
                "volume": 1_000_000.0,
            }
            for high, low in ranges
        ],
        index=index,
    )


def mirrored(ranges: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return [(20.0 - low, 20.0 - high) for high, low in ranges]


def serialized(frame: pd.DataFrame) -> list[dict]:
    return [asdict(e) for e in strict.detect_strict_structure_events(frame, "SYNTHETIC")]


class StrictFirstPublicationRegression(unittest.TestCase):
    def _check_tail(self, side: str) -> None:
        ranges = [(9.8, 9.0), (10.3, 9.3), (10.8, 9.7), (10.7, 9.8), (11.0, 8.8)]
        frame = bars(mirrored(ranges) if side == strict.SIDE_TOP else ranges)
        reference = 11.0 if side == strict.SIDE_TOP else 9.0
        final_price = 9.2 if side == strict.SIDE_TOP else 10.8
        early = next(
            s
            for s in strict.detect_strict_structures(frame.iloc[:3])
            if s.side == side and s.reference_price == reference
        )
        for cut in (4, 5):
            with self.subTest(side=side, cut=cut):
                matches = [
                    s
                    for s in strict.detect_strict_structures(frame.iloc[:cut])
                    if s.side == side and s.reference_price == reference
                ]
                self.assertEqual(len(matches), 1)
                result = matches[0]
                self.assertEqual(result.confirmed_date, frame.index[2].date())
                self.assertEqual(result.structure_id, early.structure_id)
                self.assertAlmostEqual(result.final_price, final_price)
                self.assertEqual(result.reference_date, early.reference_date)
                self.assertEqual(result.trigger_price, early.trigger_price)
                self.assertEqual(result.contained_bars_merged, early.contained_bars_merged)
                self.assertEqual(
                    result.invalidated_date, frame.index[4].date() if cut == 5 else None
                )
        full = serialized(frame)
        for cut in range(1, len(frame) + 1):
            self.assertEqual(
                serialized(frame.iloc[:cut]),
                [e for e in full if e["available_date"] <= frame.index[cut - 1].date()],
            )
        self.assertEqual(len({e["event_id"] for e in full}), len(full))

    def test_bottom_confirmed_fields_survive_future_containment(self) -> None:
        self._check_tail(strict.SIDE_BOTTOM)

    def test_top_confirmed_fields_survive_future_containment(self) -> None:
        self._check_tail(strict.SIDE_TOP)

    def test_multiple_valid_tops_are_preserved(self) -> None:
        frame = bars([(12.0, 10.0), (11.0, 9.0), (10.0, 8.0), (9.0, 7.0)])
        tops = [s for s in strict.detect_strict_structures(frame) if s.side == strict.SIDE_TOP]
        self.assertEqual(
            [s.confirmed_date for s in tops], [frame.index[2].date(), frame.index[3].date()]
        )
        self.assertEqual([s.reference_price for s in tops], [12.0, 11.0])
        self.assertTrue(all(s.is_valid for s in tops))

    def test_complex_candidate_waits_beyond_third_merged_bar(self) -> None:
        frame = bars([(12.0, 10.0), (11.0, 9.0), (11.5, 9.5), (11.8, 9.6), (11.0, 8.8)])
        tops = [s for s in strict.detect_strict_structures(frame) if s.side == strict.SIDE_TOP]
        self.assertEqual(len(tops), 1)
        self.assertEqual(tops[0].confirmed_date, frame.index[4].date())
        self.assertEqual(tops[0].reference_price, 12.0)
        self.assertEqual(tops[0].trigger_price, 9.0)

    def test_equal_reference_extreme_does_not_invalidate(self) -> None:
        frame = bars([(12.0, 10.0), (11.0, 9.0), (10.0, 8.0), (12.0, 10.0)])
        top = next(
            s
            for s in strict.detect_strict_structures(frame)
            if s.side == strict.SIDE_TOP and s.reference_price == 12.0
        )
        self.assertIsNone(top.invalidated_date)


class A6TopValidityRegression(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = bars([(110.0 + i, 100.0 + i) for i in range(8)])
        # These are controlled observations, not recalculated price indicators.
        self.frame["ema20"] = self.frame["close"] - 1.0
        self.frame["close_lag20"] = self.frame["close"] - 1.0

    def _top(self, confirmation: int, invalidation: int | None = None) -> strict.StrictStructure:
        return strict.StrictStructure(
            side=strict.SIDE_TOP,
            confirmed_date=self.frame.index[confirmation].date(),
            reference_price=150.0,
            trigger_price=90.0,
            final_price=80.0,
            reference_date=self.frame.index[0].date(),
            contained_bars_merged=2,
            structure_id=f"synthetic:{confirmation}",
            invalidated_date=None
            if invalidation is None
            else self.frame.index[invalidation].date(),
        )

    def _trade(
        self,
        tops: list[strict.StrictStructure],
        black: int,
        *,
        signal: int = 0,
        stop: float = 1.0,
        exit_variant: str = engine.EXIT_TOP_PLUS_KEYWAVE,
    ) -> engine.Trade:
        frame = self.frame.copy()
        for column in ("ema20", "close_lag20"):
            frame.iloc[black, frame.columns.get_loc(column)] = frame["close"].iloc[black] + 1.0
        spec = engine.EntrySpec(
            symbol="SYNTHETIC",
            signal_date=frame.index[signal].date(),
            signal_position=signal,
            entry_ref_price=float(frame["close"].iloc[signal]),
            stop_price=stop,
            target_price=None,
            target_source=None,
            reward_risk=None,
            entry_variant="early",
            is_first_touch=True,
            ma_period=20,
            clock_type=2,
            weekly_bull_env=True,
            event_id="synthetic-entry",
        )
        with patch.object(engine, "detect_strict_structures", return_value=tops):
            prepared = engine.prepare_frame(frame)
        return engine.simulate_trade(
            frame,
            spec,
            prepared=prepared,
            exit_variant=exit_variant,
            fee=engine.FeeModel("none", 0.0, 0.0),
        )

    def test_expired_top_cannot_trigger_later_black_exit(self) -> None:
        trade = self._trade([self._top(2, 3)], 5)
        self.assertEqual(trade.exit_reason, "open_at_end")
        self.assertIsNone(trade.exit_date)

    def test_top_expiring_today_is_ineligible_today(self) -> None:
        trade = self._trade([self._top(2, 5)], 5)
        self.assertEqual(trade.exit_reason, "open_at_end")

    def test_future_expiry_does_not_erase_earlier_valid_exit(self) -> None:
        trade = self._trade([self._top(2, 6)], 5)
        self.assertEqual(trade.exit_reason, "exit_a6_2_top_plus_keywave")
        self.assertEqual(trade.exit_date, self.frame.index[6].date())

    def test_valid_top_still_exits_next_open(self) -> None:
        trade = self._trade([self._top(2)], 5)
        self.assertEqual(trade.exit_date, self.frame.index[6].date())

    def test_pre_signal_top_is_excluded(self) -> None:
        self.assertEqual(self._trade([self._top(0)], 5, signal=1).exit_reason, "open_at_end")

    def test_signal_day_top_remains_excluded(self) -> None:
        self.assertEqual(self._trade([self._top(1)], 5, signal=1).exit_reason, "open_at_end")

    def test_entry_day_top_remains_eligible(self) -> None:
        self.assertEqual(self._trade([self._top(1)], 5).exit_date, self.frame.index[6].date())

    def test_new_valid_top_after_old_expiry_is_eligible(self) -> None:
        self.assertEqual(
            self._trade([self._top(2, 3), self._top(4)], 5).exit_date, self.frame.index[6].date()
        )

    def test_older_valid_top_survives_latest_top_expiry(self) -> None:
        self.assertEqual(
            self._trade([self._top(2), self._top(4, 5)], 5).exit_date, self.frame.index[6].date()
        )

    def test_existing_same_day_confirmation_behavior_is_preserved(self) -> None:
        self.assertEqual(self._trade([self._top(5)], 5).exit_date, self.frame.index[6].date())

    def test_no_top_does_not_trigger_combined_exit(self) -> None:
        self.assertEqual(self._trade([], 5).exit_reason, "open_at_end")

    def test_initial_structure_stop_still_has_priority(self) -> None:
        self.frame.iloc[5, self.frame.columns.get_loc("close")] = 90.0
        trade = self._trade([self._top(2)], 5, stop=100.0)
        self.assertEqual(trade.exit_reason, "structure_stop_C")
        self.assertEqual(trade.exit_date, self.frame.index[6].date())

    def test_other_exit_variants_keep_existing_behavior(self) -> None:
        tops = [self._top(2, 3)]
        self.assertEqual(
            self._trade(tops, 5, exit_variant=engine.EXIT_COSTBASIS).exit_reason,
            "exit_a6_1_costbasis",
        )
        self.assertEqual(
            self._trade(tops, 5, exit_variant=engine.EXIT_STRUCTURE_STOP).exit_reason, "open_at_end"
        )


class A6ActualDetectorRegression(unittest.TestCase):
    def _run(self, *, black_before_expiry: bool) -> tuple[pd.DataFrame, list, engine.Trade]:
        # The top is confirmed on day 3; a raw high strictly above 110 expires it.
        ranges = [(110.0, 100.0), (108.0, 99.0), (106.0, 98.0)]
        ranges += (
            [(108.0, 100.0), (112.0, 104.0), (114.0, 106.0), (116.0, 108.0)]
            if black_before_expiry
            else [(112.0, 104.0), (114.0, 106.0), (116.0, 108.0), (118.0, 110.0)]
        )
        frame = bars(ranges)
        black = 3 if black_before_expiry else 5
        frame["ema20"] = frame["close"] - 1.0
        frame["close_lag20"] = frame["close"] - 1.0
        for column in ("ema20", "close_lag20"):
            frame.iloc[black, frame.columns.get_loc(column)] = frame["close"].iloc[black] + 1.0
        structures = strict.detect_strict_structures(frame)
        spec = engine.EntrySpec(
            symbol="SYNTHETIC",
            signal_date=frame.index[0].date(),
            signal_position=0,
            entry_ref_price=float(frame["close"].iloc[0]),
            stop_price=1.0,
            target_price=None,
            target_source=None,
            reward_risk=None,
            entry_variant="early",
            is_first_touch=True,
            ma_period=20,
            clock_type=2,
            weekly_bull_env=True,
            event_id="synthetic-entry",
        )
        trade = engine.simulate_trade(
            frame,
            spec,
            prepared=engine.prepare_frame(frame),
            exit_variant=engine.EXIT_TOP_PLUS_KEYWAVE,
            fee=engine.FeeModel("none", 0.0, 0.0),
        )
        return frame, structures, trade

    def test_actual_expired_top_is_not_consumed(self) -> None:
        frame, structures, trade = self._run(black_before_expiry=False)
        tops = [s for s in structures if s.side == strict.SIDE_TOP]
        self.assertEqual(len(tops), 1)
        self.assertEqual(tops[0].confirmed_date, frame.index[2].date())
        self.assertEqual(tops[0].invalidated_date, frame.index[3].date())
        self.assertEqual(trade.exit_reason, "open_at_end")

    def test_actual_later_expiry_preserves_valid_prior_exit(self) -> None:
        frame, structures, trade = self._run(black_before_expiry=True)
        top = next(s for s in structures if s.side == strict.SIDE_TOP)
        self.assertEqual(top.invalidated_date, frame.index[4].date())
        self.assertEqual(trade.exit_reason, "exit_a6_2_top_plus_keywave")
        self.assertEqual(trade.exit_date, frame.index[4].date())


if __name__ == "__main__":
    unittest.main(verbosity=2)
