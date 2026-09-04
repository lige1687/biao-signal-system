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


def _outcome_changes(
    frame, run_date: str, horizons: tuple[int, ...]
) -> dict[str, float]:
    """run_date 收盘为基准的 T+N 收盘涨跌幅（百分点）。数据不足的档位跳过。"""
    from datetime import date as _date

    import pandas as pd

    pairs = sorted(zip(
        pd.to_datetime(frame["date"]).dt.date.tolist(),
        frame["close"].astype(float).tolist(),
        strict=False,
    ))
    base_i = max(
        (k for k, (d, _) in enumerate(pairs) if d <= _date.fromisoformat(run_date)),
        default=None,
    )
    if base_i is None or pairs[base_i][1] <= 0:
        return {}
    base = pairs[base_i][1]
    out: dict[str, float] = {}
    for h in horizons:
        j = base_i + h
        if j < len(pairs):
            out[f"chg_{h}d"] = round((pairs[j][1] / base - 1.0) * 100.0, 2)
    return out


def score_journal_outcomes(
    conn: sqlite3.Connection,
    service,
    *,
    horizons: tuple[int, ...] = (1, 5, 20),
    today: str | None = None,
) -> int:
    """给尚无 outcome 的推荐账本日补 T+N 对账（只补一次，幂等）。

    前向存证口径（设计定稿 §5）：不做伪历史回测，从推荐次日起用真实行情
    逐档打分；行情不足的档位跳过，已有 outcome 的日期不重打。
    """
    from datetime import UTC as _UTC
    from datetime import datetime as _dt

    today = today or _dt.now(_UTC).date().isoformat()
    rows = conn.execute(
        "SELECT run_date FROM recommendation_journal "
        "WHERE outcome IS NULL AND run_date < ? ORDER BY run_date",
        (today,),
    ).fetchall()
    written = 0
    for row in rows:
        run_date = row["run_date"]
        card = load_recommendation(conn, run_date)
        if card is None or not card.items:
            continue
        outcome: dict[str, dict[str, float]] = {}
        for item in card.items:
            try:
                entry = service.get(item.symbol)
            except Exception:  # noqa: BLE001  单标的失败不影响其余
                continue
            if getattr(entry, "result", None) is None:
                continue
            changes = _outcome_changes(entry.result.frame, run_date, horizons)
            if changes:
                outcome[item.symbol] = changes
        if outcome:
            save_outcome(conn, run_date, outcome)
            written += 1
    return written
