"""推荐存证账本（recommendation_journal 表 CRUD）。

每次「今日推荐」流水线运行的完整输出按 run_date 幂等落库（当日重跑整体
覆盖 payload，不追加）；T+N 对账结果单独 upsert 进 outcome。历史无逐日扫描
数据，不做伪历史回测，用前向存证替代（设计定稿 §5）。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from lei_signal.api.schemas import RecommendCardDTO


def _now() -> str:
    return datetime.now(UTC).isoformat()


def save_recommendation(conn: sqlite3.Connection, card: RecommendCardDTO) -> str:
    conn.execute(
        """
        INSERT INTO recommendation_journal (journal_id, run_date, payload, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(run_date) DO UPDATE SET
            payload = excluded.payload,
            updated_at = excluded.updated_at
        """,
        (
            f"rj_{card.run_date}",
            card.run_date,
            card.model_dump_json(),
            _now(),
            _now(),
        ),
    )
    return card.run_date


def load_recommendation(
    conn: sqlite3.Connection, run_date: str
) -> RecommendCardDTO | None:
    row = conn.execute(
        "SELECT payload FROM recommendation_journal WHERE run_date = ?",
        (run_date,),
    ).fetchone()
    if row is None:
        return None
    return RecommendCardDTO.model_validate_json(row["payload"])


def list_journal_dates(conn: sqlite3.Connection, limit: int = 60) -> list[str]:
    rows = conn.execute(
        "SELECT run_date FROM recommendation_journal ORDER BY run_date DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [r["run_date"] for r in rows]


def save_outcome(conn: sqlite3.Connection, run_date: str, outcome: dict) -> None:
    """T+N 对账结果 upsert。只对已有 journal 行使用（编排方保证先存证后对账）。

    独立调用（该日无 journal 行）时 INSERT 的 payload 为占位 JSON，
    ``load_recommendation`` 会因校验失败抛错——这是有意的防御，避免无存证
    的对账结果伪装成推荐记录。
    """
    conn.execute(
        """
        INSERT INTO recommendation_journal (journal_id, run_date, payload,
                                            outcome, outcome_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_date) DO UPDATE SET
            outcome = excluded.outcome,
            outcome_at = excluded.outcome_at,
            updated_at = excluded.updated_at
        """,
        (
            f"rj_{run_date}",
            run_date,
            json.dumps({"placeholder": True}, ensure_ascii=False),
            json.dumps(outcome, ensure_ascii=False),
            _now(),
            _now(),
            _now(),
        ),
    )


def load_outcome(conn: sqlite3.Connection, run_date: str) -> dict | None:
    row = conn.execute(
        "SELECT outcome FROM recommendation_journal WHERE run_date = ?",
        (run_date,),
    ).fetchone()
    if row is None or not row["outcome"]:
        return None
    try:
        return json.loads(row["outcome"])
    except (TypeError, ValueError):
        return None
