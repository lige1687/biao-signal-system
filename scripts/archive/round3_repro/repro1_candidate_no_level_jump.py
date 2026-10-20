"""Round 3 最小复现 1：candidate 不得越级。

复现什么
--------
D1 的原始缺陷是 ``_resolve_opportunity()`` 用 ``live_bottoms and joint_now``
判断共同确认——只要「有存活底部」且「全局双均线共同向上」，就抬到
JOINT_CONFIRMED，完全不看该结构是否已确认。

本脚本构造一条**全局双均线确实共同向上、长周期确实转为改善**的行情，
但底部结构是纯 candidate（``confirmed_date is None``）。
修复后必须每日都停在 BOTTOM_WATCH。

先打印前提条件，避免「因为触发条件没出现所以看起来通过」的假阳性。

运行：/opt/homebrew/bin/python3.11 scripts/round3_repro/repro1_candidate_no_level_jump.py
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.domain.types import (
    Provenance,
    Stage,
    StructureInstance,
    StructureStatus,
)
from lei_signal.rules.dual_ma import dual_ma_bull_state
from lei_signal.rules.ema_reclaim_tiers import detect_structure_bound_ema_reclaim
from lei_signal.state.machine import run_state_machine

_INDEX = pd.bdate_range("2024-01-01", periods=10)


def _frame() -> pd.DataFrame:
    close = [100, 103, 104, 105, 106, 107, 108, 109, 110, 111]
    return pd.DataFrame(
        {
            "open": close,
            "high": [v + 1.0 for v in close],
            "low": [v - 1.0 for v in close],
            "close": close,
            "volume": [1_000_000.0] * 10,
            "ema20": [101, 101.5, 102, 102.5, 103, 103.5, 104, 104.5, 105, 105.5],
            "sma20": [110, 109, 108, 107, 106, 105, 104, 103.5, 104, 104.5],
            "signal_color": ["green"] * 10,
            "long_trend": ["unknown"] * 9 + ["long_improving"],
            "long_is_improving": [False] * 9 + [True],
            "long_is_supportive": [False] * 10,
        },
        index=_INDEX,
    )


def main() -> int:
    frame = _frame()
    candidate = StructureInstance(
        structure_id="S-CAND",
        symbol="600000",
        structure_type="bottom_C",
        side="bottom",
        detected_date=date(2024, 1, 1),
        confirmed_date=None,          # <<< 关键：未确认
        invalidated_date=None,
        c_price=95.0,
        neckline=105.0,
        status=StructureStatus.CANDIDATE,
        provenance=Provenance.LEI_EXPLICIT,
    )

    events = detect_structure_bound_ema_reclaim(frame, "600000", [candidate])
    history = run_state_machine(frame, [candidate], ema_reclaim_events=events)

    joint = dual_ma_bull_state(frame)
    print("== 前提条件（证明触发条件确实出现了）==")
    print(f"结构 S-CAND: status={candidate.status.value} confirmed_date={candidate.confirmed_date}")
    print(f"全局 joint_now @01-11 = {bool(joint.loc[pd.Timestamp('2024-01-11')])}")
    print(f"全局 joint_now @01-12 = {bool(joint.loc[pd.Timestamp('2024-01-12')])}")
    print(f"长周期改善     @01-12 = {bool(frame['long_is_improving'].iloc[-1])}")
    print(f"事件层产出档位 = {[e.evidence['tier'] for e in events]}")
    print()

    print("== 逐日阶段（修复后）==")
    forbidden = {Stage.EARLY_STRENGTH, Stage.JOINT_CONFIRMED, Stage.TREND_REINFORCED}
    violations = []
    for state in history:
        obs = state.observations.get("S-CAND")
        tier = obs.tier if obs else None
        flag = "  <<< 越级!" if state.opportunity_stage in forbidden else ""
        print(
            f"{state.day}  stage={state.opportunity_stage.value:<20}"
            f" joint_now={str(state.joint_confirmed_now):<5}"
            f" long_sup={str(state.long_supportive):<5}"
            f" tier={str(tier):<12}{flag}"
        )
        if state.opportunity_stage in forbidden:
            violations.append((state.day, state.opportunity_stage.value))

    print()
    if violations:
        print(f"FAIL: 候选结构越级 {violations}")
        return 1
    print("PASS: 全部 10 个交易日均停在 bottom_watch，候选结构未越级。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
