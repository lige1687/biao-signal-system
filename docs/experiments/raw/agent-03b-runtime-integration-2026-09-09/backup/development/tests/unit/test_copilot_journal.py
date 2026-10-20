"""推荐存证账本：幂等 upsert + 读取往返 + T+N 分档补齐（2026-09-07 修复锚定）。"""
from __future__ import annotations

import pandas as pd
import pytest

from lei_signal.api.schemas import RecommendCardDTO, RecommendItemDTO
from lei_signal.copilot import journal
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    yield c
    c.close()


def _card(run_date: str) -> RecommendCardDTO:
    return RecommendCardDTO(run_date=run_date, items=[], sectors=[])


def _card_with(run_date: str, symbol: str) -> RecommendCardDTO:
    return RecommendCardDTO(
        run_date=run_date, items=[RecommendItemDTO(symbol=symbol, verdict="waiting")]
    )


class _FakeEntry:
    def __init__(self, frame):
        self.result = type("R", (), {"frame": frame})()
        self.error = None


class _FakeService:
    def __init__(self, frames):
        self._frames = frames

    def get(self, symbol, refresh=False):
        return _FakeEntry(self._frames[symbol])


def test_save_and_load_roundtrip(conn):
    journal.save_recommendation(conn, _card("2026-09-05"))
    got = journal.load_recommendation(conn, "2026-09-05")
    assert got is not None and got.run_date == "2026-09-05"


def test_save_is_idempotent_upsert(conn):
    journal.save_recommendation(conn, _card("2026-09-05"))
    journal.save_recommendation(conn, _card("2026-09-05"))
    dates = journal.list_journal_dates(conn)
    assert dates == ["2026-09-05"]
    assert journal.load_recommendation(conn, "2026-09-05") is not None


def test_outcome_roundtrip(conn):
    assert journal.load_outcome(conn, "2026-09-05") is None
    journal.save_recommendation(conn, _card("2026-09-05"))
    journal.save_outcome(conn, "2026-09-05", {"515880": {"chg_5d": 2.1}})
    out = journal.load_outcome(conn, "2026-09-05")
    assert out is not None and out["515880"]["chg_5d"] == pytest.approx(2.1)


def test_load_missing_returns_none(conn):
    assert journal.load_recommendation(conn, "1999-01-01") is None


def test_outcome_progressively_filled(conn):
    """修复锚定：先写 chg_1d，行情到 22 天后继续补 chg_5d/chg_20d（旧实现永久缺失）。"""
    dates = pd.bdate_range("2026-09-01", periods=26)
    closes = [100.0 + i for i in range(26)]
    journal.save_recommendation(conn, _card_with("2026-09-01", "515880"))
    conn.commit()

    journal.score_journal_outcomes(
        conn, _FakeService({"515880": pd.DataFrame({"close": closes[:2]},
                                                  index=pd.DatetimeIndex(dates[:2]))}),
        today="2026-09-02",
    )
    out = journal.load_outcome(conn, "2026-09-01")["515880"]
    assert sorted(out) == ["chg_1d"]

    journal.score_journal_outcomes(
        conn, _FakeService({"515880": pd.DataFrame({"close": closes},
                                                  index=pd.DatetimeIndex(dates))}),
        today="2026-09-30",
    )
    out = journal.load_outcome(conn, "2026-09-01")["515880"]
    assert sorted(out) == ["chg_1d", "chg_20d", "chg_5d"]


def test_save_recommendation_records_observations(conn):
    """save_recommendation 同步落观察账本：主张去重、批次修订、删除留痕。"""
    journal.save_recommendation(conn, _card_with("2026-09-05", "515880"))
    journal.save_recommendation(conn, _card_with("2026-09-05", "515880"))
    conn.commit()
    claims = conn.execute(
        "SELECT COUNT(*) c FROM agent_observations WHERE record_type='claim'"
    ).fetchone()["c"]
    batches = conn.execute(
        "SELECT COUNT(*) c FROM agent_observations WHERE record_type='display_batch'"
    ).fetchone()["c"]
    assert claims == 1 and batches == 1  # 同内容重试：主张与批次都不重复

    journal.save_recommendation(conn, _card_with("2026-09-05", "159915"))
    conn.commit()
    claims2 = conn.execute(
        "SELECT COUNT(*) c FROM agent_observations WHERE record_type='claim'"
    ).fetchone()["c"]
    batches2 = conn.execute(
        "SELECT COUNT(*) c FROM agent_observations WHERE record_type='display_batch'"
    ).fetchone()["c"]
    assert claims2 == 2 and batches2 == 2  # 内容变化：新主张+新批次
    # 当前集合只含新标的；旧主张留档（说过的话算数）
    from lei_signal.copilot import observation
    cur = observation.current_claim_ids(conn, "recommendation")
    assert len(cur) == 1
