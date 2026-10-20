"""extract_sell_signals 四档口径门禁（纯提取，不做新判定）。

口径（docs/superpowers/specs/2026-08-23-unified-signal-panel-design.md §2）：
  hard  structure_invalidated    底部结构失效（trading-spec §2.3/§7）
  hard  exit_proxy               收盘同破 EMA20+20日抵扣价（A6①，research_proxy）
  warn  top_structure_confirmed  顶部构造确认（§7.4，预警不必然反向）
  warn  key_wave_black           反向关键性波动（§2.2，预警不必然反向）
  soft  color_black              三色转黑（生命周期状态机）
顶部结构失效（=创新高解除预警）是偏多事实，不得进卖点面板。
"""
from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from lei_signal.api.sell_signals import extract_sell_signals


def _frame(n: int = 3) -> pd.DataFrame:
    # bdate_range("2026-08-19", 3) -> 08-19(三) 08-20(四) 08-21(五)，today=08-21
    return pd.DataFrame(
        {"close": [10.0] * n},
        index=pd.bdate_range("2026-08-19", periods=n),
    )


def _bottom_invalidated(day, reason="跌破 C 点"):
    return SimpleNamespace(
        side="bottom", status="invalidated", invalidated_date=day,
        invalidated_reason=reason, c_price=9.5, confirmed_date=None, neckline=None,
    )


def _exit_event(day):
    return SimpleNamespace(
        rule_id="exit_ema20_costbasis", available_date=day,
        reason_cn="抵扣价退出触发：收盘同时跌破 EMA20 与 20 日抵扣价",
        evidence={"ema20": 10.5, "close_lag20": 10.8, "close": 10.1},
    )


def test_structure_invalidated_today_is_hard_and_new() -> None:
    today = _frame().index[-1].date()
    result = SimpleNamespace(
        frame=_frame(), events=[], structures=[_bottom_invalidated(today)], history=[],
    )
    sigs = extract_sell_signals(result)
    assert len(sigs) == 1
    s = sigs[0]
    assert s.kind == "structure_invalidated" and s.tier == "hard"
    assert s.is_new is True
    assert s.key_prices == {"invalidation_c": 9.5}
    assert "结构" in s.title


def test_structure_invalidated_three_bars_ago_is_continuing() -> None:
    # 3 根窗口的最早一天（仍在窗口内）但不是今天 -> is_new=False
    frame = _frame()
    oldest = frame.index[0].date()
    result = SimpleNamespace(
        frame=frame, events=[], structures=[_bottom_invalidated(oldest)], history=[],
    )
    sigs = extract_sell_signals(result)
    assert len(sigs) == 1 and sigs[0].is_new is False


def test_old_invalidation_outside_window_ignored() -> None:
    frame = _frame()
    old_day = pd.Timestamp("2026-07-01").date()
    result = SimpleNamespace(
        frame=frame, events=[], structures=[_bottom_invalidated(old_day)], history=[],
    )
    assert extract_sell_signals(result) == []


def test_top_side_invalidation_not_a_sell() -> None:
    today = _frame().index[-1].date()
    top_dead = SimpleNamespace(
        side="top", status="invalidated", invalidated_date=today,
        invalidated_reason="创新高解除", c_price=None, confirmed_date=None, neckline=None,
    )
    result = SimpleNamespace(frame=_frame(), events=[], structures=[top_dead], history=[])
    assert extract_sell_signals(result) == []


def test_exit_proxy_is_hard_research_proxy_with_prices() -> None:
    frame = _frame()
    today = frame.index[-1].date()
    result = SimpleNamespace(frame=frame, events=[_exit_event(today)], structures=[], history=[])
    sigs = extract_sell_signals(result)
    assert len(sigs) == 1
    s = sigs[0]
    assert s.kind == "exit_proxy" and s.tier == "hard" and s.is_new is True
    assert s.provenance == "research_proxy"
    assert s.key_prices == {"ema20": 10.5, "close_lag20": 10.8, "close": 10.1}


def test_top_structure_confirmed_is_warn_with_disclaimer() -> None:
    frame = _frame()
    today = frame.index[-1].date()
    top = SimpleNamespace(
        side="top", status="confirmed", confirmed_date=today, invalidated_date=None,
        invalidated_reason=None, c_price=None, neckline=11.2,
    )
    result = SimpleNamespace(frame=frame, events=[], structures=[top], history=[])
    sigs = extract_sell_signals(result)
    assert len(sigs) == 1
    s = sigs[0]
    assert s.kind == "top_structure_confirmed" and s.tier == "warn"
    assert "预警" in s.reason_cn and "不必然" in s.reason_cn
    assert s.key_prices == {"neckline": 11.2}


def test_key_wave_black_is_warn_with_disclaimer() -> None:
    frame = _frame()
    today = frame.index[-1].date()
    ev = SimpleNamespace(
        rule_id="key_wave_black", available_date=today, reason_cn="空头趋势中的向上关键波动",
        evidence={},
    )
    result = SimpleNamespace(frame=frame, events=[ev], structures=[], history=[])
    sigs = extract_sell_signals(result)
    assert len(sigs) == 1
    s = sigs[0]
    assert s.kind == "key_wave_black" and s.tier == "warn"
    assert "预警" in s.reason_cn and "不必然" in s.reason_cn


def test_color_black_transition_is_soft() -> None:
    frame = _frame()
    d1, d2 = frame.index[-2].date(), frame.index[-1].date()
    history = [
        SimpleNamespace(day=d1, color="gray"),
        SimpleNamespace(day=d2, color="black"),
    ]
    result = SimpleNamespace(frame=frame, events=[], structures=[], history=history)
    sigs = extract_sell_signals(result)
    assert len(sigs) == 1
    s = sigs[0]
    assert s.kind == "color_black" and s.tier == "soft" and s.is_new is True
    assert "灰转黑" in s.reason_cn


def test_black_to_black_is_not_a_transition() -> None:
    frame = _frame()
    d1, d2 = frame.index[-2].date(), frame.index[-1].date()
    history = [
        SimpleNamespace(day=d1, color="black"),
        SimpleNamespace(day=d2, color="black"),
    ]
    result = SimpleNamespace(frame=frame, events=[], structures=[], history=history)
    assert extract_sell_signals(result) == []


def test_empty_frame_returns_empty() -> None:
    result = SimpleNamespace(frame=pd.DataFrame(), events=[], structures=[], history=[])
    assert extract_sell_signals(result) == []
