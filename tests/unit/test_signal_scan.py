"""run_signal_scan 统一扫描门禁：买点走既有链路，卖点从同缓存提取，失败显式落库。

build_review 被 monkeypatch 成恒返回 none-verdict（买点过滤掉），
单测聚焦：卖点行生成、unavailable 行生成、as_of meta 行、当日重写。
"""
from __future__ import annotations

from contextlib import closing
from datetime import UTC, datetime
from types import SimpleNamespace

import pandas as pd

from lei_signal.api.opportunity_scan import list_scan, today_date
from lei_signal.api.services import AnalysisEntry
from lei_signal.api.signal_alerts_store import (
    SIDE_SELL,
    SIDE_UNAVAILABLE,
    get_scan_as_of,
    list_signal_alerts,
)
from lei_signal.api.signal_scan import AS_OF_INTRADAY, run_signal_scan
from lei_signal.storage.sqlite_store import connect


class _FakeService:
    def __init__(self, entries: dict[str, AnalysisEntry]):
        self._entries = entries
        self.get_many_calls: list[bool] = []

    def get_many(self, symbols, refresh=False):
        self.get_many_calls.append(refresh)
        return {s: self._entries[s] for s in symbols if s in self._entries}


def _entry(result=None, error=None) -> AnalysisEntry:
    return AnalysisEntry(result=result, error=error, fetched_at=datetime.now(UTC))


def _result_with_exit_event() -> SimpleNamespace:
    frame = pd.DataFrame(
        {"close": [10.0] * 3}, index=pd.bdate_range("2026-08-19", periods=3),
    )
    today = frame.index[-1].date()
    return SimpleNamespace(
        frame=frame,
        display_name="测试标的",
        events=[SimpleNamespace(
            rule_id="exit_ema20_costbasis", available_date=today,
            reason_cn="抵扣价退出触发", evidence={"ema20": 10.5, "close_lag20": 10.8, "close": 10.1},
        )],
        structures=[],
        history=[],
    )


def _none_review(monkeypatch, verdict="none"):
    review = SimpleNamespace(
        verdict=verdict, verdict_cn="", display_name="", has_active_plan=False,
        candidates=[], resonance_groups=[], watch_conditions=[], tradability=None,
    )
    monkeypatch.setattr(
        "lei_signal.api.routes.opportunities.build_review", lambda *a, **kw: review,
    )


def test_sell_and_unavailable_rows_persisted(monkeypatch, tmp_path) -> None:
    _none_review(monkeypatch)
    db = str(tmp_path / "lab.db")
    entries = {
        "600519.SS": _entry(result=_result_with_exit_event()),
        "bad.SS": _entry(error="DATA_UNAVAILABLE: 行情获取失败"),
    }
    service = _FakeService(entries)
    summary = run_signal_scan(service, db, symbols=list(entries), as_of=AS_OF_INTRADAY)

    assert summary["scanned"] == 2
    assert summary["sell_rows"] == 1
    assert summary["unavailable"] == 1
    with closing(connect(db)) as conn:
        assert get_scan_as_of(conn, today_date()) == AS_OF_INTRADAY
        sell = list_signal_alerts(conn, today_date(), side=SIDE_SELL)
        assert len(sell) == 1
        assert sell[0].symbol == "600519.SS"
        assert sell[0].kind == "exit_proxy" and sell[0].provenance == "research_proxy"
        unavailable = list_signal_alerts(conn, today_date(), side=SIDE_UNAVAILABLE)
        assert len(unavailable) == 1
        assert unavailable[0].symbol == "bad.SS"
        assert "DATA_UNAVAILABLE" in (unavailable[0].error or "")
        # 买点表同轮同步重写：bad.SS 失败行在；600519.SS none-verdict 被 only_with_candidates 过滤
        buy_rows = list_scan(conn, today_date())
        assert [r.symbol for r in buy_rows] == ["bad.SS"]
        assert "DATA_UNAVAILABLE" in (buy_rows[0].error or "")


def test_rescan_rewrites_same_day(monkeypatch, tmp_path) -> None:
    _none_review(monkeypatch)
    db = str(tmp_path / "lab.db")
    service = _FakeService({"600519.SS": _entry(result=_result_with_exit_event())})
    run_signal_scan(service, db, symbols=["600519.SS"], as_of=AS_OF_INTRADAY)
    # 第二轮换成无信号标的：当日卖点行必须被整体重写掉
    service2 = _FakeService({"600519.SS": _entry(result=SimpleNamespace(
        frame=pd.DataFrame({"close": [10.0] * 3}, index=pd.bdate_range("2026-08-19", periods=3)),
        display_name="测试标的", events=[], structures=[], history=[],
    ))})
    run_signal_scan(service2, db, symbols=["600519.SS"], as_of="close")
    with closing(connect(db)) as conn:
        assert list_signal_alerts(conn, today_date(), side=SIDE_SELL) == []
        assert get_scan_as_of(conn, today_date()) == "close"


def test_empty_watchlist_writes_meta_only(tmp_path) -> None:
    db = str(tmp_path / "lab.db")
    service = _FakeService({})
    summary = run_signal_scan(service, db, symbols=[], as_of="close")
    assert summary["scanned"] == 0
    with closing(connect(db)) as conn:
        assert get_scan_as_of(conn, today_date()) == "close"
        assert list_signal_alerts(conn, today_date(), side=SIDE_SELL) == []


def test_sell_uses_cached_entries_no_refetch(monkeypatch, tmp_path) -> None:
    """买点扫描刷新缓存后，卖点提取 refresh=False 复用缓存，不再二次抓网。"""
    _none_review(monkeypatch)
    db = str(tmp_path / "lab.db")
    service = _FakeService({"600519.SS": _entry(result=_result_with_exit_event())})
    run_signal_scan(service, db, symbols=["600519.SS"])
    assert service.get_many_calls == [True, False]  # run_opportunity_scan 一次 True，卖点一次 False


def test_buy_table_rewritten_by_rescan(monkeypatch, tmp_path) -> None:
    """二轮扫描整体重写当日买点表：上一轮的失败行不残留（设计 §3.2 两表整体重写）。"""
    _none_review(monkeypatch)
    db = str(tmp_path / "lab.db")
    service = _FakeService({"bad.SS": _entry(error="DATA_UNAVAILABLE: 行情获取失败")})
    run_signal_scan(service, db, symbols=["bad.SS"], as_of=AS_OF_INTRADAY)
    with closing(connect(db)) as conn:
        rows = list_scan(conn, today_date())
        assert [r.symbol for r in rows] == ["bad.SS"]
        assert "DATA_UNAVAILABLE" in (rows[0].error or "")

    clean = _FakeService({"600519.SS": _entry(result=SimpleNamespace(
        frame=pd.DataFrame({"close": [10.0] * 3}, index=pd.bdate_range("2026-08-19", periods=3)),
        display_name="测试标的", events=[], structures=[], history=[],
    ))})
    run_signal_scan(clean, db, symbols=["600519.SS"], as_of="close")
    with closing(connect(db)) as conn:
        assert list_scan(conn, today_date()) == []  # none-verdict 过滤后当日重写，stale 失败行已清
