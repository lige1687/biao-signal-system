"""前向验证成绩单路由（只读 GET）。

两套前向存证账本（情绪 JSON / 推荐 SQLite）的到期对账成绩并排展示。
判定与对账口径都在账本既有写入方（scripts/sentiment_journal.py review、
copilot journal.score_journal_outcomes）；本文件只读聚合，不写任何账本。
"""

from __future__ import annotations

import json
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.fwd_ledger import (
    build_recommendation_stats,
    load_sentiment_stats,
    sentiment_journal_path,
)
from lei_signal.forward_observation.service import build_dashboard
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


_ROOT = Path(__file__).resolve().parents[4]


def _forward_paths(request: Request) -> tuple[Path, Path]:
    db = Path(
        getattr(request.app.state, "forward_observation_db_path", None)
        or _ROOT / "data/forward-observation/ledger.db"
    )
    config = Path(
        getattr(request.app.state, "forward_observation_config_path", None)
        or _ROOT / "configs/forward-observation.v1.json"
    )
    return db, config


def _forward_config(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


@router.get("/strategies")
def strategy_observation(
    request: Request, range: str = Query("since_start", pattern="^(since_start|common)$")
) -> dict[str, Any]:
    """Read saved prospective account facts; never initializes or refreshes them."""
    db, config_path = _forward_paths(request)
    try:
        return build_dashboard(
            db, _forward_config(config_path), datetime.now(UTC).isoformat(), range=range
        )
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail=f"前向观察资料不可读：{exc}") from exc


@router.post("/strategies/observe")
def observe_strategy(request: Request) -> dict[str, Any]:
    """Explicit manual run; scheduled runs call the same runner directly."""
    db, config_path = _forward_paths(request)
    if not config_path.is_file():
        raise HTTPException(status_code=503, detail="前向观察配置未就绪")
    try:
        from lei_signal.forward_observation.runner import observe_once

        return observe_once(db_path=db, config_path=config_path, now=datetime.now(UTC).isoformat())
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"前向观察未完成：{exc}") from exc
