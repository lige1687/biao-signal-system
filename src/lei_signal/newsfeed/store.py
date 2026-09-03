"""newsfeed 存储：迁移 016 表的读写。只追加 + 幂等（INSERT OR IGNORE）。"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from lei_signal.storage.sqlite_store import connect

_ITEM_COLUMNS = (
    "source",
    "source_name",
    "dedupe_key",
    "url",
    "category",
    "title",
    "summary",
    "content",
    "published_at",
)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class NewsStore:
    """单连接封装（管线线程与 API 线程各自持有一个实例，WAL + busy_timeout 兜底）。"""

    def __init__(self, path: str | Path) -> None:
        self._conn: sqlite3.Connection = connect(path)  # 含 WAL + 迁移

    def close(self) -> None:
        self._conn.close()

    # ---------------- 条目 ----------------

    def insert_items(self, items: list[dict]) -> int:
        inserted = 0
        for it in items:
            cur = self._conn.execute(
                f"INSERT OR IGNORE INTO news_items ({', '.join(_ITEM_COLUMNS)}, ingested_at) "
                f"VALUES ({', '.join('?' * len(_ITEM_COLUMNS))}, ?)",
                [it.get(c) for c in _ITEM_COLUMNS] + [_now()],
            )
            inserted += cur.rowcount
        self._conn.commit()
        return inserted

    def fetch_unscored(self, limit: int = 500) -> list[sqlite3.Row]:
        return list(
            self._conn.execute(
                "SELECT * FROM news_items WHERE importance IS NULL "
                "ORDER BY published_at DESC LIMIT ?",
                (limit,),
            )
        )

    def apply_scores(self, scores: list[dict]) -> int:
        n = 0
        for s in scores:
            cur = self._conn.execute(
                "UPDATE news_items SET category=?, importance=?, direction=?, "
                "symbols=?, llm_note=?, scored_at=? WHERE id=? AND importance IS NULL",
                (
                    s.get("category"),
                    s.get("importance"),
                    s.get("direction"),
                    json.dumps(s.get("symbols") or [], ensure_ascii=False),
                    s.get("note"),
                    _now(),
                    s.get("id"),
                ),
            )
            n += cur.rowcount
        self._conn.commit()
        return n

    def query_items(
        self,
        *,
        category: str | None = None,
        q: str | None = None,
        source: str | None = None,
        symbol: str | None = None,
        direction: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        scored: str = "all",
        min_importance: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[sqlite3.Row], int]:
        where: list[str] = []
        args: list = []
        if category:
            where.append("category = ?")
            args.append(category)
        if source:
            where.append("source = ?")
            args.append(source)
        if direction:
            where.append("direction = ?")
            args.append(direction)
        if symbol:
            # 标的关联 = LLM 提取的 symbols 数组（JSON 文本）或标题/摘要里出现。
            # SQLite LIKE 对 ASCII 大小写不敏感，代码匹配（NVDA/nvda）天然覆盖。
            like = f"%{symbol}%"
            where.append("(symbols LIKE ? OR title LIKE ? OR summary LIKE ?)")
            args.extend([like, like, like])
        if date_from:
            where.append("published_at >= ?")
            args.append(date_from)
        if date_to:
            where.append("published_at < date(?, '+1 day')")
            args.append(date_to)
        if min_importance is not None:
            where.append("importance >= ?")
            args.append(min_importance)
        if scored == "scored":
            where.append("importance IS NOT NULL")
        elif scored == "unscored":
            where.append("importance IS NULL")
        if q:
            like = f"%{q}%"
            where.append("(title LIKE ? OR summary LIKE ? OR llm_note LIKE ? OR symbols LIKE ?)")
            args.extend([like, like, like, like])
        wsql = (" WHERE " + " AND ".join(where)) if where else ""
        total = self._conn.execute(
            f"SELECT COUNT(*) FROM news_items{wsql}", args
        ).fetchone()[0]
        # 默认排序：已评分在前（importance 降序），未评分垫底按时间倒序。
        if scored == "unscored":
            order = "published_at DESC"
        else:
            order = "(importance IS NULL) ASC, importance DESC, published_at DESC"
        rows = list(
            self._conn.execute(
                f"SELECT * FROM news_items{wsql} ORDER BY {order} LIMIT ? OFFSET ?",
                args + [limit, offset],
            )
        )
        return rows, total

    def scored_recent(self, date_from: str, limit: int = 1000) -> list[sqlite3.Row]:
        """指定日期起的已评分条目（时间倒序），自选雷达聚合用。"""
        return list(
            self._conn.execute(
                "SELECT * FROM news_items "
                "WHERE importance IS NOT NULL AND published_at >= ? "
                "ORDER BY published_at DESC LIMIT ?",
                (date_from, limit),
            )
        )

    def scored_rows_for_digest(self, day_prefix: str, limit: int = 400) -> list[sqlite3.Row]:
        """取指定本地日期（YYYY-MM-DD 前缀）的已评分条目，按重要性倒序。"""
        return list(
            self._conn.execute(
                "SELECT id, title, summary, llm_note, category, importance, direction, "
                "symbols, source FROM news_items "
                "WHERE importance IS NOT NULL AND substr(published_at, 1, 10) = ? "
                "ORDER BY importance DESC, published_at DESC LIMIT ?",
                (day_prefix, limit),
            )
        )

    # ---------------- 简报 ----------------

    def save_digest(self, digest_date: str, payload: dict) -> None:
        self._conn.execute(
            "INSERT INTO news_digests (digest_date, payload_json, created_at) "
            "VALUES (?, ?, ?) ON CONFLICT(digest_date) DO UPDATE SET "
            "payload_json=excluded.payload_json, created_at=excluded.created_at",
            (digest_date, json.dumps(payload, ensure_ascii=False), _now()),
        )
        self._conn.commit()

    def digests(self, limit: int = 7) -> list[sqlite3.Row]:
        return list(
            self._conn.execute(
                "SELECT * FROM news_digests ORDER BY digest_date DESC LIMIT ?", (limit,)
            )
        )

    # ---------------- 水位 ----------------

    def get_watermark(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT cursor_value FROM news_watermarks WHERE source_key = ?", (key,)
        ).fetchone()
        return row["cursor_value"] if row else None

    def set_watermark(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO news_watermarks (source_key, cursor_value, updated_at) "
            "VALUES (?, ?, ?) ON CONFLICT(source_key) DO UPDATE SET "
            "cursor_value=excluded.cursor_value, updated_at=excluded.updated_at",
            (key, value, _now()),
        )
        self._conn.commit()

    # ---------------- 运行留痕 ----------------

    def start_run(self) -> int:
        cur = self._conn.execute(
            "INSERT INTO news_runs (started_at, status) VALUES (?, 'running')", (_now(),)
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def finish_run(
        self,
        run_id: int,
        status: str,
        stats: dict | None = None,
        errors: list | None = None,
    ) -> None:
        self._conn.execute(
            "UPDATE news_runs SET finished_at=?, status=?, stats_json=?, errors_json=? "
            "WHERE id=?",
            (
                _now(),
                status,
                json.dumps(stats or {}, ensure_ascii=False),
                json.dumps(errors or [], ensure_ascii=False),
                run_id,
            ),
        )
        self._conn.commit()

    def latest_run(self) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM news_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()

    def counts(self) -> dict:
        row = self._conn.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN importance IS NOT NULL THEN 1 ELSE 0 END) AS scored "
            "FROM news_items"
        ).fetchone()
        return {"total": row["total"] or 0, "scored": row["scored"] or 0}


__all__ = ["NewsStore"]
