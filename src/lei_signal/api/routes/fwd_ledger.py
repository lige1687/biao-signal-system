"""前向验证成绩单路由（只读 GET）。

两套前向存证账本（情绪 JSON / 推荐 SQLite）的到期对账成绩并排展示。
判定与对账口径都在账本既有写入方（scripts/sentiment_journal.py review、
copilot journal.score_journal_outcomes）；本文件只读聚合，不写任何账本。
"""
from __future__ import annotations

from contextlib import closing
from typing import Any

from fastapi import APIRouter, Request

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.fwd_ledger import (
    build_recommendation_stats,
    load_sentiment_stats,
    sentiment_journal_path,
)
from lei_signal.storage.sqlite_store import connect

router = APIRouter(prefix="/api/fwd-ledger", tags=["fwd-ledger"])


def _db_path(request: Request) -> str:
    return getattr(request.app.state, "plans_db_path", None) or default_db()


@router.get("/scorecard")
def scorecard(request: Request) -> dict[str, Any]:
    sentiment = load_sentiment_stats(sentiment_journal_path())
    try:
        with closing(connect(_db_path(request))) as conn:
            recommendation = build_recommendation_stats(conn)
    except Exception:  # noqa: BLE001  库缺席/迁移未跑：降级不阻断另一半
        recommendation = {"available": False, "reason": "推荐账本数据库不可用"}
    return {
        "sentiment": sentiment,
        "recommendation": recommendation,
        "disclaimerCn": (
            "前向存证成绩（research_proxy）：情绪线为板块冰点/强热信号的 "
            "10/20 日到期涨跌，推荐线为当日推荐标的的 1/5/20 日到期涨跌；"
            "均不构成买卖点。"
        ),
    }
