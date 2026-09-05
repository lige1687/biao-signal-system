"""推荐对账：T+N 涨跌幅打分（前向存证，D9）。"""
from __future__ import annotations

import pandas as pd

from lei_signal.api.schemas import RecommendCardDTO, RecommendItemDTO
from lei_signal.copilot import journal
from lei_signal.storage.sqlite_store import connect


class _FakeResult:
    def __init__(self, frame):
        self.frame = frame


class _FakeEntry:
    def __init__(self, frame):
        self.result = _FakeResult(frame)
        self.error = None


class _FakeService:
    def __init__(self, frames):
        self._frames = frames

    def get(self, symbol, refresh=False):
        return _FakeEntry(self._frames[symbol])


def _frame(closes):  # 2026-09-01 起逐个交易日；日期在索引（生产口径）
    dates = pd.bdate_range("2026-09-01", periods=len(closes))
    return pd.DataFrame({"close": closes}, index=dates)


def _card(run_date: str) -> RecommendCardDTO:
    return RecommendCardDTO(
        run_date=run_date,
        items=[RecommendItemDTO(symbol="515880", verdict="waiting")],
    )


def test_scores_one_five_twenty():
    conn = connect(":memory:")
    journal.save_recommendation(conn, _card("2026-09-01"))
    svc = _FakeService({"515880": _frame([1.0, 1.0, 1.0, 1.0, 1.0, 1.0] * 5)})
    n = journal.score_journal_outcomes(conn, svc, today="2026-10-15")
    assert n == 1
    out = journal.load_outcome(conn, "2026-09-01")
    assert out["515880"]["chg_1d"] == 0.0
    assert "chg_20d" in out["515880"]


def test_skips_already_scored_and_missing_data():
    conn = connect(":memory:")
    journal.save_recommendation(conn, _card("2026-09-01"))
    svc = _FakeService({})  # 无数据
    assert journal.score_journal_outcomes(conn, svc, today="2026-10-01") == 0
    journal.save_outcome(conn, "2026-09-01", {})
    assert journal.score_journal_outcomes(conn, svc, today="2026-10-01") == 0


def test_not_enough_future_days_scores_partial():
    conn = connect(":memory:")
    journal.save_recommendation(conn, _card("2026-09-01"))
    svc = _FakeService({"515880": _frame([1.0, 1.1])})  # 只有 2 天
    n = journal.score_journal_outcomes(conn, svc, today="2026-09-03")
    if n == 1:
        out = journal.load_outcome(conn, "2026-09-01")
        assert "chg_1d" in out["515880"]
        assert "chg_20d" not in out["515880"]
