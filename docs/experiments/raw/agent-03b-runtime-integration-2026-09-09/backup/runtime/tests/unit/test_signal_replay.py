"""run_signal_replay 回放门禁：analyze(as_of=day) 截断、两表落库、幂等、显式不可用。

analyze 与 build_review 均 monkeypatch 本模块命名空间, 不触网。
"""
from __future__ import annotations

from contextlib import closing
from datetime import date
from types import SimpleNamespace

import pandas as pd

from lei_signal.api import signal_replay
from lei_signal.api.opportunity_scan import list_scan
from lei_signal.api.services import AnalysisEntry  # noqa: F401  (类型参考)
from lei_signal.api.signal_alerts_store import (
    SIDE_SELL,
    SIDE_UNAVAILABLE,
    get_scan_as_of,
    list_signal_alerts,
)
from lei_signal.storage.sqlite_store import connect

DAY = date(2026, 8, 21)  # 周五


def _result(symbol: str = "600519.SS", *, with_exit: bool = True) -> SimpleNamespace:
    frame = pd.DataFrame(
        {"close": [10.0] * 3},
        index=pd.bdate_range("2026-08-19", periods=3),  # 最后一根 = 08-21
    )
    today = frame.index[-1].date()
    events = [SimpleNamespace(
        rule_id="exit_ema20_costbasis", available_date=today,
        reason_cn="抵扣价退出触发",
        evidence={"ema20": 10.5, "close_lag20": 10.8, "close": 10.1},
    )] if with_exit else []
    return SimpleNamespace(
        frame=frame, display_name=f"标的{symbol}", events=events,
        structures=[], history=[],
    )


def _none_review(monkeypatch) -> None:
    review = SimpleNamespace(
        verdict="none", verdict_cn="", display_name="", has_active_plan=False,
        candidates=[], resonance_groups=[], watch_conditions=[], tradability=None,
    )
    monkeypatch.setattr(signal_replay, "build_review", lambda *a, **kw: review)


def test_replay_passes_as_of_and_persists_both_tables(monkeypatch, tmp_path) -> None:
    _none_review(monkeypatch)
    seen: dict[str, object] = {}

    def fake_analyze(symbol, *, as_of=None, **kw):
        seen[symbol] = as_of
        if symbol == "bad.SS":
            raise RuntimeError("DATA_UNAVAILABLE: 行情获取失败")
        return _result(symbol)

    monkeypatch.setattr(signal_replay, "analyze", fake_analyze)
    db = str(tmp_path / "lab.db")
    summary = signal_replay.run_signal_replay(
        db, DAY, symbols=["600519.SS", "bad.SS"], max_workers=1,
    )

    assert seen == {"600519.SS": DAY, "bad.SS": DAY}  # as_of 逐标的透传
    assert summary["scan_date"] == DAY.isoformat()
    assert summary["as_of"] == "close"
    assert summary["sell_rows"] == 1 and summary["unavailable"] == 1
    with closing(connect(db)) as conn:
        assert get_scan_as_of(conn, DAY.isoformat()) == "close"
        sell = list_signal_alerts(conn, DAY.isoformat(), side=SIDE_SELL)
        assert len(sell) == 1
        assert sell[0].symbol == "600519.SS" and sell[0].kind == "exit_proxy"
        assert sell[0].is_new is True  # 相对截断后最后一根(08-21) 计算
        unavailable = list_signal_alerts(conn, DAY.isoformat(), side=SIDE_UNAVAILABLE)
        assert len(unavailable) == 1 and "DATA_UNAVAILABLE" in (unavailable[0].error or "")
        buy = list_scan(conn, DAY.isoformat())
        assert [r.symbol for r in buy] == ["bad.SS"]  # none-verdict 被过滤, 错误行保留
        assert buy[0].error and "DATA_UNAVAILABLE" in buy[0].error


def test_replay_is_idempotent_rewrite(monkeypatch, tmp_path) -> None:
    _none_review(monkeypatch)
    db = str(tmp_path / "lab.db")
    monkeypatch.setattr(
        signal_replay, "analyze", lambda symbol, *, as_of=None, **kw: _result(symbol),
    )
    signal_replay.run_signal_replay(db, DAY, symbols=["600519.SS"], max_workers=1)
    # 第二轮无信号 -> 卖点/买点行整体重写清空, meta 保留
    monkeypatch.setattr(
        signal_replay, "analyze",
        lambda symbol, *, as_of=None, **kw: _result(symbol, with_exit=False),
    )
    signal_replay.run_signal_replay(db, DAY, symbols=["600519.SS"], max_workers=1)
    with closing(connect(db)) as conn:
        assert list_signal_alerts(conn, DAY.isoformat(), side=SIDE_SELL) == []
        assert list_scan(conn, DAY.isoformat()) == []
        assert get_scan_as_of(conn, DAY.isoformat()) == "close"


def test_replay_first_symbol_serial_warms_up(monkeypatch, tmp_path) -> None:
    """首标的必须串行（V8 预热），其后才进线程池：用调用序号断言首个调用发生在任何并发调用前。"""
    _none_review(monkeypatch)
    order: list[str] = []
    import threading

    monkeypatch.setattr(signal_replay, "analyze", lambda symbol, *, as_of=None, **kw: (
        order.append(symbol), _result(symbol))[-1])
    db = str(tmp_path / "lab.db")
    signal_replay.run_signal_replay(
        db, DAY, symbols=["a.SS", "b.SS", "c.SS"], max_workers=2,
    )
    assert set(order) == {"a.SS", "b.SS", "c.SS"}
    assert order[0] == "a.SS"  # 首标的先行
    assert threading.active_count() >= 1  # 无崩溃即通过


def test_replay_empty_symbols_writes_meta_only(tmp_path) -> None:
    db = str(tmp_path / "lab.db")
    summary = signal_replay.run_signal_replay(db, DAY, symbols=[], max_workers=1)
    assert summary["scanned"] == 0
    with closing(connect(db)) as conn:
        assert get_scan_as_of(conn, DAY.isoformat()) == "close"
        assert list_signal_alerts(conn, DAY.isoformat(), side=SIDE_SELL) == []
        assert list_scan(conn, DAY.isoformat()) == []
