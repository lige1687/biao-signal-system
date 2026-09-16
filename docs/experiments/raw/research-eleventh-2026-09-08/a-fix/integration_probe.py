"""有界复测：真实 strict 输出接入 A；只控制上游派生列、clock 与周线。"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np
import pandas as pd


parser = argparse.ArgumentParser()
parser.add_argument("--package", required=True)
parser.add_argument("--expect-stale", type=int, required=True)
parser.add_argument("--expect-prefix-stable", choices=("yes", "no"), required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

package = Path(args.package).resolve()
sys.path.insert(0, str(package / "src"))

from lei_signal.rules import first_ma_pullback as a  # noqa: E402
from lei_signal.rules.strict_structure import (  # noqa: E402
    SIDE_BOTTOM,
    detect_strict_structures,
)


def encode(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def derived(rows):
    frame = pd.DataFrame(
        rows,
        columns=["open", "high", "low", "close"],
        index=pd.bdate_range("2024-01-01", periods=len(rows)),
    )
    frame["volume"] = 1_000.0
    frame["signal_color"] = "green"
    for period, sma, ema in ((20, 9.2, 8.9), (60, 8.0, 8.0), (120, 7.0, 7.0)):
        frame[f"sma{period}"] = sma
        frame[f"ema{period}"] = ema + np.arange(len(frame)) * 0.001
        frame[f"close_lag{period}"] = 8.5
    return frame


def controlled(frame, clock, observed=None):
    original_active = a._active_bottom_structures

    def recording_active(structures, start, as_of):
        result = original_active(structures, start, as_of)
        if observed is not None and result is not None:
            observed.append(
                {
                    "as_of": as_of,
                    "structure_id": result.structure_id,
                    "confirmed_date": result.confirmed_date,
                    "invalidated_date": result.invalidated_date,
                }
            )
        return result

    with (
        patch.object(
            a,
            "weekly_env_series",
            lambda data: pd.Series(True, index=data.index),
        ),
        patch.object(
            a,
            "clock_series",
            lambda data: pd.Series(clock[: len(data)], index=data.index),
        ),
        patch.object(a, "_active_bottom_structures", recording_active),
    ):
        return a.detect_first_ma_pullback_events(frame, "SYNTHETIC")


def confirmations(events):
    return [
        event
        for event in events
        if event.evidence["sub_rule"] == a.SUB_RULE_CONFIRMED
    ]


# 第十 a-review 的真实 strict 可达输入：底部在 1/31 确认，2/1 被新低实际破坏。
stale_frame = derived(
    [(9.0, 10.0, 8.0, 9.0)] * 20
    + [
        (9.2, 9.8, 9.0, 9.4),
        (9.9, 10.3, 9.3, 10.2),
        (10.2, 10.8, 9.7, 10.6),
        (10.1, 10.7, 7.5, 10.4),
    ]
)
clock = [2] * len(stale_frame)
clock[22] = 3
structures = detect_strict_structures(stale_frame)
bottoms = [structure for structure in structures if structure.side == SIDE_BOTTOM]
assert bottoms, "真实 strict 没有形成底部，场景没有到达目标路径"
target = next(
    structure
    for structure in bottoms
    if structure.confirmed_date == stale_frame.index[22].date()
    and structure.invalidated_date == stale_frame.index[23].date()
)
observed = []
stale_events = controlled(stale_frame, clock, observed)
stale = [
    event
    for event in confirmations(stale_events)
    if event.evidence.get("a3_structure_id") == target.structure_id
    and event.available_date >= target.invalidated_date
]
reclaims = (
    (stale_frame.close.shift(1) <= stale_frame.ema20.shift(1))
    & (stale_frame.close > stale_frame.ema20)
)
assert int(reclaims.sum()) == 0, "场景意外出现 EMA20 收复替代理由"
assert any(
    item["structure_id"] == target.structure_id
    and item["as_of"] == target.confirmed_date
    for item in observed
), "A 没有在确认日实际读取并缓存该底部"
assert len(stale) == args.expect_stale


# 第十 a-contract 的包含关系输入：同样的派生列与受控环境，比较完整事件字段。
contained = derived(
    [(9.0, 10.0, 8.0, 9.0)] * 20
    + [
        (9.2, 9.8, 9.0, 9.4),
        (9.9, 10.3, 9.3, 10.2),
        (10.2, 10.8, 9.7, 10.6),
        (10.1, 10.7, 9.8, 10.4),
    ]
)
contained_clock = [2] * len(contained)
prefix_events = controlled(contained.iloc[:23], contained_clock)
full_events = controlled(contained, contained_clock)
cutoff = contained.index[22].date()
prefix_confirmed = [asdict(event) for event in confirmations(prefix_events)]
full_past_confirmed = [
    asdict(event)
    for event in confirmations(full_events)
    if event.available_date <= cutoff
]
prefix_stable = prefix_confirmed == full_past_confirmed
assert prefix_confirmed, "包含关系场景没有产生原有确认，不能以删光事件通过"
assert prefix_stable is (args.expect_prefix_stable == "yes")

report = {
    "package": str(package),
    "controlled_upstream": [
        "SMA/EMA/close_lag 派生列",
        "clock_series",
        "weekly_env_series",
    ],
    "not_replaced": ["detect_strict_structures", "A 主状态机"],
    "stale_bottom_case": {
        "actual_bottoms": [asdict(item) for item in bottoms],
        "target_was_observed_by_A_on_confirmation_day": True,
        "observed_active_bottoms": observed,
        "ema20_reclaim_count": int(reclaims.sum()),
        "stale_confirmation_count": len(stale),
        "stale_confirmations": [asdict(event) for event in stale],
    },
    "contained_bar_case": {
        "prefix_confirmation_count": len(prefix_confirmed),
        "full_past_confirmation_count": len(full_past_confirmed),
        "full_field_prefix_stable": prefix_stable,
        "prefix_confirmations": prefix_confirmed,
        "full_past_confirmations": full_past_confirmed,
    },
}
Path(args.output).write_text(
    json.dumps(report, ensure_ascii=False, indent=2, default=encode) + "\n",
    encoding="utf-8",
)
print(
    json.dumps(
        {
            "stale_confirmation_count": len(stale),
            "bottom_cached_before_actual_invalidation": True,
            "ema20_reclaim_count": int(reclaims.sum()),
            "contained_prefix_confirmation_count": len(prefix_confirmed),
            "contained_full_field_prefix_stable": prefix_stable,
        },
        ensure_ascii=False,
        indent=2,
    )
)
