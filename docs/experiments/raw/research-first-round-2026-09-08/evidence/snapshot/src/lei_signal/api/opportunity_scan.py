"""今日机会雷达的当日 scan 结果 CRUD (migration 015 的 daily_opportunity_scan 表).

设计语义:
  15:00 launchd 扫全自选 -> upsert_scan_results 整体重写当日 -> 面板/红点读表.
  不现场跑 scan (scan 5-10s, 60s 轮询不可接受). 表只存"当日快照"这一个事实.

当日重扫语义: upsert_scan_results 先 DELETE 当日所有行再 INSERT, 避免部分更新
导致旧 verdict 残留 (eg 某标的昨天 actionable, 今天 none, only_with_candidates
过滤后今天不返回, 旧行不删就会误导).
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class DailyScanRow:
    """daily_opportunity_scan 一行 (已反序列化, blocking_reasons 为 list)."""
    scan_date: str
    symbol: str
    display_name: str
    verdict: str
    verdict_cn: str
    best_scenario_cn: str | None
    best_state: str | None
    reward_risk_ratio: float | None
    reward_risk_computable: bool
    blocking_reasons: list[str]
    missing_summary_cn: str
    has_active_plan: bool
    error: str | None
    generated_at: str


def today_date() -> str:
    """UTC date, 与 entered_on / scan_date 同口径."""
    return datetime.now(UTC).date().isoformat()


def upsert_scan_results(
    conn: sqlite3.Connection,
    scan_date: str,
    items: list,  # list[ScanItemDTO], 避免循环 import 用 duck typing
) -> int:
    """当日整体重写: 先 DELETE 当日, 再 INSERT 新结果. 返回写入行数.

    items 元素需有 .symbol/.verdict/.verdict_cn 等字段 (ScanItemDTO 形态).
    """
    conn.execute(
        "DELETE FROM daily_opportunity_scan WHERE scan_date = ?",
        (scan_date,),
    )
    generated_at = datetime.now(UTC).isoformat()
    rows = 0
    for it in items:
        conn.execute(
            """
            INSERT INTO daily_opportunity_scan (
                scan_date, symbol, display_name, verdict, verdict_cn,
                best_scenario_cn, best_state, reward_risk_ratio,
                reward_risk_computable, blocking_reasons, missing_summary_cn,
                has_active_plan, error, generated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan_date,
                it.symbol,
                getattr(it, "display_name", "") or "",
                it.verdict,
                getattr(it, "verdict_cn", "") or "",
                it.best_scenario_cn,
                it.best_state,
                it.reward_risk_ratio,
                1 if it.reward_risk_computable else 0,
                json.dumps(getattr(it, "blocking_reasons", []) or [], ensure_ascii=False),
                getattr(it, "missing_summary_cn", "") or "",
                1 if getattr(it, "has_active_plan", False) else 0,
                getattr(it, "error", None),
                generated_at,
            ),
        )
        rows += 1
    conn.commit()
    return rows


def _row_to_scan(row: sqlite3.Row) -> DailyScanRow:
    raw_reasons = row["blocking_reasons"] or "[]"
    try:
        reasons: list[str] = json.loads(raw_reasons)
    except (json.JSONDecodeError, TypeError):
        reasons = []
    return DailyScanRow(
        scan_date=row["scan_date"],
        symbol=row["symbol"],
        display_name=row["display_name"],
        verdict=row["verdict"],
        verdict_cn=row["verdict_cn"],
        best_scenario_cn=row["best_scenario_cn"],
        best_state=row["best_state"],
        reward_risk_ratio=row["reward_risk_ratio"],
        reward_risk_computable=bool(row["reward_risk_computable"]),
        blocking_reasons=reasons,
        missing_summary_cn=row["missing_summary_cn"],
        has_active_plan=bool(row["has_active_plan"]),
        error=row["error"],
        generated_at=row["generated_at"],
    )


def list_scan(conn: sqlite3.Connection, scan_date: str) -> list[DailyScanRow]:
    """读当日所有行, 按 verdict 优先级 + R/R 降序排序 (与 run_opportunity_scan 一致)."""
    rows = conn.execute(
        """
        SELECT * FROM daily_opportunity_scan
        WHERE scan_date = ?
        ORDER BY CASE verdict
            WHEN 'actionable' THEN 0
            WHEN 'waiting' THEN 1
            WHEN 'blocked' THEN 2
            ELSE 3
        END, reward_risk_ratio DESC, symbol
        """,
        (scan_date,),
    ).fetchall()
    return [_row_to_scan(r) for r in rows]


def has_scan(conn: sqlite3.Connection, scan_date: str) -> bool:
    """当日是否已扫 (表里有无行)."""
    row = conn.execute(
        "SELECT 1 FROM daily_opportunity_scan WHERE scan_date = ? LIMIT 1",
        (scan_date,),
    ).fetchone()
    return row is not None


def count_opportunities(conn: sqlite3.Connection, scan_date: str) -> int:
    """当日 actionable + waiting 计数 (红点用). blocked 不计 (环境阻断不算机会)."""
    row = conn.execute(
        """
        SELECT COUNT(*) FROM daily_opportunity_scan
        WHERE scan_date = ? AND verdict IN ('actionable', 'waiting')
        """,
        (scan_date,),
    ).fetchone()
    return int(row[0]) if row else 0


__all__ = [
    "DailyScanRow",
    "count_opportunities",
    "has_scan",
    "list_scan",
    "today_date",
    "upsert_scan_results",
]
