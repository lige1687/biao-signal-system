"""推荐存证账本：幂等 upsert + 读取往返。"""
from __future__ import annotations

import pytest

from lei_signal.api.schemas import RecommendCardDTO
from lei_signal.copilot import journal
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    yield c
    c.close()


def _card(run_date: str) -> RecommendCardDTO:
    return RecommendCardDTO(run_date=run_date, items=[], sectors=[])


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
