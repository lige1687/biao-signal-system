"""黄金样例逐行核对：三色。"""
from __future__ import annotations

import pandas as pd

from lei_signal.features.indicators import compute_features
from lei_signal.rules.lei_color import classify_colors
from tests.golden.fixtures import golden_color_series


def _classified() -> pd.DataFrame:
    return classify_colors(compute_features(golden_color_series()))


def test_golden_color_series_produces_all_four_states() -> None:
    """黄金样例必须覆盖未知、绿、灰、黑四种状态。"""
    result = _classified()
    observed = set(result["signal_color"])
    assert observed == {"unknown", "green", "gray", "black"}


def test_golden_first_twenty_bars_are_unknown() -> None:
    result = _classified()
    assert result["signal_color"].iloc[:20].tolist() == ["unknown"] * 20


def test_golden_every_ready_row_satisfies_its_declared_formula() -> None:
    """逐行核对：每一行的颜色必须与严格公式一致。"""
    result = _classified()
    ready = result["color_ready"]
    for timestamp, row in result[ready].iterrows():
        close, ema20, lag20 = row["close"], row["ema20"], row["close_lag20"]
        color = row["signal_color"]
        if color == "green":
            assert close > ema20 and close > lag20, f"{timestamp.date()} 绿色不满足双大于"
        elif color == "black":
            assert close < ema20 and close < lag20, f"{timestamp.date()} 黑色不满足双小于"
        else:
            assert color == "gray"
            assert not (close > ema20 and close > lag20), f"{timestamp.date()} 应为绿色"
            assert not (close < ema20 and close < lag20), f"{timestamp.date()} 应为黑色"


def test_golden_color_transitions_are_recorded_once_per_change() -> None:
    """颜色切换只在变化当天标记一次。"""
    result = _classified()
    changes = result[result["color_changed"]]
    assert len(changes) >= 2
    for timestamp in changes.index:
        position = result.index.get_loc(timestamp)
        assert result["signal_color"].iloc[position] != result["signal_color"].iloc[position - 1]


def test_golden_gray_segment_is_not_labelled_as_sell() -> None:
    """灰色理由必须表述为「需要关注」，不得包含卖出措辞。"""
    result = _classified()
    gray_reasons = set(result.loc[result["signal_color"] == "gray", "signal_reason"])
    assert len(gray_reasons) == 1
    reason = gray_reasons.pop()
    assert "关注" in reason
    for forbidden in ("卖出", "买入", "止损", "建议"):
        assert forbidden not in reason
