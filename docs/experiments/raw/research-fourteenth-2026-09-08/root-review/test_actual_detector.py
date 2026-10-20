"""Independent small integration checks; synthetic bars, real strict detector.

EMA and lag observations are deliberately supplied, not independently recomputed.
This isolates detector -> prepare_frame -> exit timing, not a return experiment.
"""
import importlib.util
import os
from pathlib import Path
import sys

import pandas as pd

HERE = Path(__file__).resolve().parent
P14 = HERE.parent
P11 = P14.parent / 'research-eleventh-2026-09-08/research-package'
sys.path.insert(0, str(P11 / 'src'))
path = Path(os.environ.get('ENGINE_UNDER_TEST', P14 / 'consumer-audit/research-copy/engine.py'))
spec = importlib.util.spec_from_file_location('root_actual_detector_engine', path)
engine = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = engine
spec.loader.exec_module(engine)


def run(rows, wave_position):
    frame = pd.DataFrame(rows, columns=['high', 'low'], index=pd.date_range('2024-01-01', periods=len(rows)))
    frame['open'] = (frame.high + frame.low) / 2
    frame['close'] = frame.open
    frame['volume'] = 1000.0
    frame['ema20'] = frame.close - 1
    frame['close_lag20'] = frame.close - 1
    frame.loc[frame.index[wave_position], ['ema20', 'close_lag20']] = frame.close.iloc[wave_position] + 1
    frame['sma20'] = 80.0
    frame['sma60'] = 70.0
    tops = [s for s in engine.detect_strict_structures(frame) if s.side == engine.SIDE_TOP]
    entry = engine.EntrySpec(
        symbol='TEST', signal_date=frame.index[0].date(), signal_position=0,
        entry_ref_price=94.0, stop_price=70.0, target_price=200.0,
        target_source='synthetic_fixture', reward_risk=4.0, entry_variant='early',
        is_first_touch=True, ma_period=20, clock_type=2, weekly_bull_env=True,
        event_id='synthetic_fixture',
    )
    trade = engine.simulate_trade(frame, entry, exit_variant=engine.EXIT_TOP_PLUS_KEYWAVE,
                                  fee=engine.FeeModel('none', 0.0, 0.0),
                                  prepared=engine.prepare_frame(frame))
    return frame, tops, trade


def test_real_detector_invalid_top_does_not_exit():
    frame, tops, trade = run([(100,90),(99,89),(98,88),(105,95),(106,96),(107,97),(108,98),(109,99)], 6)
    assert len(tops) == 1
    assert tops[0].confirmed_date == frame.index[2].date()
    assert tops[0].invalidated_date == frame.index[3].date()
    assert trade.exit_reason == 'open_at_end'


def test_real_detector_future_invalidation_keeps_previous_exit():
    frame, tops, trade = run([(100,90),(99,89),(98,88),(99,90),(101,95),(102,96)], 3)
    assert len(tops) == 1
    assert tops[0].confirmed_date == frame.index[2].date()
    assert tops[0].invalidated_date == frame.index[4].date()
    assert trade.exit_reason == 'exit_a6_2_top_plus_keywave'
    assert trade.exit_date == frame.index[4].date()
