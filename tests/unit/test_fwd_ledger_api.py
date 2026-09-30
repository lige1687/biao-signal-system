"""前向成绩单 API（/api/fwd-ledger/scorecard）单元测试：临时 JSON + 临时 SQLite。

只读性：断言两个数据源在请求前后内容不变（本端点不写任何账本）。
降级真实性：情绪账本缺席、推荐库无 outcome 时必须有 available=false + 原因。
"""
from __future__ import annotations

import json
from contextlib import closing
from pathlib import Path

from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.fwd_ledger import (
    build_recommendation_stats,
    build_sentiment_stats,
)
from lei_signal.api.schemas import RecommendCardDTO, RecommendItemDTO
from lei_signal.copilot import journal as copilot_journal
from lei_signal.storage.sqlite_store import connect


def _write_sentiment_journal(path: Path) -> None:
    path.write_text(
        json.dumps(
            {"records": [{
                "date": "2025-09-18",
                "picks": [{"code": "BK1621", "name": "x", "z": -2.1,
                           "close": 100.0, "holding": False}],
                "alarms": [{"code": "BK1617", "name": "y", "z": 2.3,
                            "b50": 55.0, "close": 200.0, "holding": True}],
                "review": {"t10": [0.05, -0.02], "t20": [0.10],
                           "a10": [-0.03], "a20": [0.01], "done": True},
            }]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _seed_recommendation_db(db: Path) -> None:
    with closing(connect(str(db))) as conn:
        for run_date, chg1 in (("2026-08-01", 1.5), ("2026-08-02", -0.5)):
            card = RecommendCardDTO(
                run_date=run_date,
                items=[
                    RecommendItemDTO(symbol="510300", display_name="沪深300ETF",
                                     verdict="watch"),
                    RecommendItemDTO(symbol="513100", display_name="纳指ETF",
                                     verdict="watch"),
                ],
            )
            copilot_journal.save_recommendation(conn, card)
            copilot_journal.save_outcome(
                conn, run_date,
                {"510300": {"chg_1d": chg1, "chg_5d": 2.0},
                 "513100": {"chg_1d": -chg1}},
            )
            conn.commit()


def _client(db: Path) -> TestClient:
    app = create_app()
    app.state.plans_db_path = str(db)
    return TestClient(app)


def test_sentiment_buckets_match_review_output(tmp_path):
    """四桶口径与 scripts/sentiment_journal.py review 打印一致（n/胜率/均值百分点）。"""
    _write_sentiment_journal(tmp_path / "sentiment_signal_journal.json")
    journal = json.loads(
        (tmp_path / "sentiment_signal_journal.json").read_text(encoding="utf-8"))
    stats = build_sentiment_stats(journal)
    buckets = {b["key"]: b for b in stats["buckets"]}
    assert buckets["pick10"]["n"] == 2
    assert buckets["pick10"]["winRatePct"] == 50.0   # 0.05/-0.02 一正一负
    assert buckets["pick10"]["meanPct"] == 1.5       # (5-2)/2 = +1.5%
    assert buckets["alarm10"]["winRatePct"] == 0.0
    assert buckets["alarm10"]["meanPct"] == -3.0
    assert stats["records"] == 1 and stats["reviewedRecords"] == 1


def test_scorecard_both_available_and_readonly(tmp_path, monkeypatch):
    """双可用形态 + 请求前后两个数据源字节不变（只读）。"""
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    _write_sentiment_journal(tmp_path / "sentiment_signal_journal.json")
    db = tmp_path / "api.db"
    _seed_recommendation_db(db)
    journal_sha_before = (tmp_path / "sentiment_signal_journal.json").read_bytes()
    db_before = db.read_bytes()

    resp = _client(db).get("/api/fwd-ledger/scorecard")
    assert resp.status_code == 200
    body = resp.json()

    sent = body["sentiment"]
    assert sent["available"] is True
    assert {b["key"] for b in sent["buckets"]} == {"pick10", "pick20", "alarm10", "alarm20"}

    rec = body["recommendation"]
    assert rec["available"] is True
    assert rec["scoredDates"] == 2
    assert rec["latestDate"] == "2026-08-02"
    by = {s["symbol"]: s for s in rec["bySymbol"]}
    # 单位：outcome 的 chg_* 本就是百分点，直接聚合（不 ×100）
    assert by["510300"]["t1"]["meanPct"] == 0.5   # (1.5 + -0.5)/2
    assert by["510300"]["t1"]["n"] == 2
    assert by["510300"]["t5"]["meanPct"] == 2.0
    assert by["510300"]["t20"] is None             # 无该档样本 → None，不编数
    assert by["510300"]["nameCn"] == "沪深300ETF"
    assert by["513100"]["t1"]["meanPct"] == -0.5

    # 只读：请求前后数据源不变
    assert (tmp_path / "sentiment_signal_journal.json").read_bytes() == journal_sha_before
    assert db.read_bytes() == db_before


def test_scorecard_degrades_when_data_missing(tmp_path, monkeypatch):
    """缺数据降级：情绪账本缺席、推荐库无 outcome → available=false + 原因。"""
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))  # 不写情绪 JSON
    empty_db = tmp_path / "empty.db"
    with closing(connect(str(empty_db))) as conn:
        pass  # 建表即可，无 outcome
    resp = _client(empty_db).get("/api/fwd-ledger/scorecard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sentiment"]["available"] is False
    assert "不存在" in body["sentiment"]["reason"]
    assert body["recommendation"]["available"] is False
    assert body["recommendation"]["reason"]


def test_sentiment_records_without_expired_samples_degrade(tmp_path, monkeypatch):
    """有存证但无到期样本：available=false + 原因，且不误报成绩。"""
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    (tmp_path / "sentiment_signal_journal.json").write_text(
        json.dumps({"records": [{
            "date": "2026-09-18",
            "picks": [{"code": "BK1621", "name": "x", "z": -2.1,
                       "close": 100.0, "holding": False}],
            "alarms": [], "review": {},
        }]}, ensure_ascii=False), encoding="utf-8")
    from lei_signal.api.fwd_ledger import load_sentiment_stats
    stats = load_sentiment_stats(tmp_path / "sentiment_signal_journal.json")
    assert stats["available"] is False
    assert "到期" in stats["reason"]
    assert all(b["n"] == 0 for b in stats["buckets"])


def test_recommendation_corrupt_outcome_rows_skipped(tmp_path):
    """outcome 非法 JSON 的行跳过，不崩、不编数。"""
    db = tmp_path / "api.db"
    with closing(connect(str(db))) as conn:
        conn.execute(
            "INSERT INTO recommendation_journal (journal_id, run_date, payload, outcome,"
            " created_at, updated_at) VALUES ('rj_x', '2026-08-01', '{}', 'NOT_JSON',"
            " '2026-08-01T00:00:00+00:00', '2026-08-01T00:00:00+00:00')"
        )
        conn.commit()
        stats = build_recommendation_stats(conn)
    assert stats["available"] is False
    assert stats["reason"]
