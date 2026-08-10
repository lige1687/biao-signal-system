"""提醒订阅 CRUD（migration 013 的 watch_subscriptions 表）。

设计语义见
    /Users/yongbiaoli/.claude/plans/fancy-bouncing-beacon.md
状态机:
  active -> pending_confirmation (checker 命中)
  pending_confirmation -> promoted (Step 3 落计划后回填 promoted_plan_id)
  pending_confirmation -> dismissed (人放弃)
  active -> dismissed (人主动取消)
 重复订阅: 同一 (symbol, level, source_rule_id, watch_kind) 在
 active/pending_confirmation 状态下视为同一订阅, 返回已有行 (200),
 不开新行.
"""
from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from lei_signal.storage.sqlite_store import connect

logger = logging.getLogger("lei_signal.watch_subscriptions")

# 状态机常量
WATCH_ACTIVE = "active"
WATCH_PENDING = "pending_confirmation"
WATCH_PROMOTED = "promoted"
WATCH_DISMISSED = "dismissed"

WATCH_STATES: tuple[str, ...] = (
    WATCH_ACTIVE, WATCH_PENDING, WATCH_PROMOTED, WATCH_DISMISSED,
)
#: 视为"还活着"的状态, 用来判定重复订阅.
WATCH_LIVE_STATES: tuple[str, ...] = (WATCH_ACTIVE, WATCH_PENDING)


@dataclass(frozen=True, slots=True)
class WatchSubscription:
    watch_id: str
    symbol: str
    direction: str
    module: str
    source_candidate_id: str | None
    source_rule_id: str | None
    level: float | None
    watch_kind: str
    watch_text_cn: str
    as_signal_rule_ids: tuple[str, ...]
    state: str
    created_at: str
    last_checked_at: str | None
    triggered_at: str | None
    triggered_price: float | None
    triggered_reason_cn: str | None
    promoted_plan_id: str | None
    dismissed_at: str | None
    dismissed_reason: str | None


def _split_rule_ids(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(part.strip() for part in str(raw).split(",") if part.strip())


def _join_rule_ids(rule_ids: tuple[str, ...] | list[str] | None) -> str:
    return ",".join(r.strip() for r in (rule_ids or ()) if r.strip())


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _gen_watch_id(symbol: str, created_at: str) -> str:
    """URL/回调安全的 watch_id: 只含字母数字与下划线."""
    short = hashlib.sha1(
        f"{symbol}:{created_at}:{uuid.uuid4().hex}".encode()
    ).hexdigest()[:8]
    safe_symbol = re.sub(r"[^A-Za-z0-9]", "_", symbol)
    safe_time = re.sub(r"[^0-9]", "", created_at)[:14]
    return f"ws_{safe_symbol}_{safe_time}_{short}"


def _row_to_watch(row: sqlite3.Row) -> WatchSubscription:
    return WatchSubscription(
        watch_id=row["watch_id"],
        symbol=row["symbol"],
        direction=row["direction"],
        module=row["module"],
        source_candidate_id=row["source_candidate_id"],
        source_rule_id=row["source_rule_id"],
        level=row["level"],
        watch_kind=row["watch_kind"],
        watch_text_cn=row["watch_text_cn"],
        as_signal_rule_ids=_split_rule_ids(row["as_signal_rule_ids"]),
        state=row["state"],
        created_at=row["created_at"],
        last_checked_at=row["last_checked_at"],
        triggered_at=row["triggered_at"],
        triggered_price=row["triggered_price"],
        triggered_reason_cn=row["triggered_reason_cn"],
        promoted_plan_id=row["promoted_plan_id"],
        dismissed_at=row["dismissed_at"],
        dismissed_reason=row["dismissed_reason"],
    )


def create_watch(
    conn: sqlite3.Connection,
    *,
    symbol: str,
    direction: str,
    module: str,
    watch_kind: str,
    watch_text_cn: str,
    level: float | None,
    source_candidate_id: str | None = None,
    source_rule_id: str | None = None,
    as_signal_rule_ids: tuple[str, ...] | list[str] = (),
) -> WatchSubscription:
    """创建订阅. 重复订阅 (symbol/level/source_rule_id/watch_kind 在 live 状态)
    返回已有行, 不开新行 (决策: 用户误点 [设提醒] 不应产生噪音).
    """
    if watch_kind not in ("price", "state"):
        raise ValueError(f"watch_kind 必须是 price/state, 实得 {watch_kind!r}")
    if watch_kind == "price" and level is None:
        raise ValueError("kind=price 时 level 必填")
    # 重复订阅判定: 同 (symbol, level, source_rule_id, watch_kind) 在 live 状态
    existing = _find_live_watch(
        conn, symbol=symbol, level=level,
        source_rule_id=source_rule_id, watch_kind=watch_kind,
    )
    if existing is not None:
        return existing

    created_at = _now()
    watch_id = _gen_watch_id(symbol, created_at)
    conn.execute(
        """
        INSERT INTO watch_subscriptions (
            watch_id, symbol, direction, module, source_candidate_id,
            source_rule_id, level, watch_kind, watch_text_cn,
            as_signal_rule_ids, state, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            watch_id, symbol, direction, module, source_candidate_id,
            source_rule_id, level, watch_kind, watch_text_cn,
            _join_rule_ids(as_signal_rule_ids), WATCH_ACTIVE, created_at,
        ),
    )
    conn.commit()
    return _row_to_watch(
        conn.execute(
            "SELECT * FROM watch_subscriptions WHERE watch_id = ?",
            (watch_id,),
        ).fetchone()
    )


def _find_live_watch(
    conn: sqlite3.Connection,
    *,
    symbol: str,
    level: float | None,
    source_rule_id: str | None,
    watch_kind: str,
) -> WatchSubscription | None:
    """在 live 状态 (active/pending_confirmation) 里找相同订阅."""
    clauses = [
        "symbol = ?", "watch_kind = ?", "state IN (?, ?)",
    ]
    params: list[object] = [symbol, watch_kind, WATCH_ACTIVE, WATCH_PENDING]
    if level is None:
        clauses.append("level IS NULL")
    else:
        clauses.append("level = ?")
        params.append(level)
    if source_rule_id is None:
        clauses.append("source_rule_id IS NULL")
    else:
        clauses.append("source_rule_id = ?")
        params.append(source_rule_id)
    sql = f"SELECT * FROM watch_subscriptions WHERE {' AND '.join(clauses)} LIMIT 1"
    row = conn.execute(sql, params).fetchone()
    return _row_to_watch(row) if row else None


def list_watches(
    conn: sqlite3.Connection,
    *,
    filter_states: tuple[str, ...] | list[str] | None = None,
    symbol: str | None = None,
) -> list[WatchSubscription]:
    """列出订阅. 默认只列 live 状态 (active/pending_confirmation)."""
    clauses: list[str] = []
    params: list[object] = []
    if filter_states is None:
        clauses.append(f"state IN ({','.join('?' for _ in WATCH_LIVE_STATES)})")
        params.extend(WATCH_LIVE_STATES)
    else:
        states = list(filter_states)
        for s in states:
            if s not in WATCH_STATES:
                raise ValueError(f"未知 state: {s!r}")
        clauses.append(f"state IN ({','.join('?' for _ in states)})")
        params.extend(states)
    if symbol:
        clauses.append("symbol = ?")
        params.append(symbol)
    sql = "SELECT * FROM watch_subscriptions"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created_at DESC"
    return [_row_to_watch(r) for r in conn.execute(sql, params).fetchall()]


def get_watch(
    conn: sqlite3.Connection, watch_id: str
) -> WatchSubscription | None:
    row = conn.execute(
        "SELECT * FROM watch_subscriptions WHERE watch_id = ?", (watch_id,)
    ).fetchone()
    return _row_to_watch(row) if row else None


def mark_checked(
    conn: sqlite3.Connection, watch_id: str, *, now_iso: str | None = None,
) -> None:
    """记录 checker 跑过. 只更新 last_checked_at, state 不变."""
    conn.execute(
        "UPDATE watch_subscriptions SET last_checked_at = ? WHERE watch_id = ?",
        (now_iso or _now(), watch_id),
    )
    conn.commit()


def mark_triggered(
    conn: sqlite3.Connection,
    watch_id: str,
    *,
    triggered_price: float,
    triggered_reason_cn: str,
    now_iso: str | None = None,
) -> WatchSubscription | None:
    """active -> pending_confirmation, 写 triggered_* 字段.
    triggered_at / triggered_price / triggered_reason_cn 都只记首次命中,
    二次跑到不覆盖 (决策: 命中是有信号意义的一次性事件).
    """
    now = now_iso or _now()
    row = conn.execute(
        "SELECT state, triggered_at FROM watch_subscriptions WHERE watch_id = ?",
        (watch_id,),
    ).fetchone()
    if row is None:
        return None
    if row["state"] != WATCH_ACTIVE:
        # pending/promoted/dismissed 都不再触发
        return get_watch(conn, watch_id)
    # 二次跑到 (state 仍为 active 但 triggered_at 已存在): 写 triggered_* 但
    # 用 COALESCE 保护原值不被覆盖, 同时只更新 last_checked_at.
    conn.execute(
        """
        UPDATE watch_subscriptions SET
            state = ?,
            last_checked_at = ?,
            triggered_at = COALESCE(triggered_at, ?),
            triggered_price = COALESCE(triggered_price, ?),
            triggered_reason_cn = COALESCE(triggered_reason_cn, ?)
        WHERE watch_id = ?
        """,
        (
            WATCH_PENDING, now, now, triggered_price, triggered_reason_cn, watch_id,
        ),
    )
    conn.commit()
    return get_watch(conn, watch_id)


def mark_dismissed(
    conn: sqlite3.Connection,
    watch_id: str,
    *,
    reason: str,
    now_iso: str | None = None,
) -> WatchSubscription | None:
    """active/pending -> dismissed. 不动 promoted/dismissed 终态."""
    now = now_iso or _now()
    row = conn.execute(
        "SELECT state FROM watch_subscriptions WHERE watch_id = ?",
        (watch_id,),
    ).fetchone()
    if row is None:
        return None
    if row["state"] not in (WATCH_ACTIVE, WATCH_PENDING):
        return get_watch(conn, watch_id)
    conn.execute(
        """
        UPDATE watch_subscriptions SET
            state = ?, dismissed_at = ?, dismissed_reason = ?
        WHERE watch_id = ?
        """,
        (WATCH_DISMISSED, now, reason, watch_id),
    )
    conn.commit()
    return get_watch(conn, watch_id)


def mark_promoted(
    conn: sqlite3.Connection,
    watch_id: str,
    *,
    plan_id: str,
    now_iso: str | None = None,
) -> WatchSubscription | None:
    """Step 3 落计划后回填: pending -> promoted."""
    now = now_iso or _now()
    row = conn.execute(
        "SELECT state FROM watch_subscriptions WHERE watch_id = ?",
        (watch_id,),
    ).fetchone()
    if row is None:
        return None
    if row["state"] != WATCH_PENDING:
        return get_watch(conn, watch_id)
    conn.execute(
        """
        UPDATE watch_subscriptions SET
            state = ?, promoted_plan_id = ?, last_checked_at = ?
        WHERE watch_id = ?
        """,
        (WATCH_PROMOTED, plan_id, now, watch_id),
    )
    conn.commit()
    return get_watch(conn, watch_id)


__all__ = [
    "PRICE_TOLERANCE",
    "WATCH_ACTIVE",
    "WATCH_DISMISSED",
    "WATCH_LIVE_STATES",
    "WATCH_PENDING",
    "WATCH_PROMOTED",
    "WATCH_STATES",
    "CheckReport",
    "WatchSubscription",
    "create_watch",
    "evaluate_hit",
    "get_watch",
    "list_watches",
    "mark_checked",
    "mark_dismissed",
    "mark_promoted",
    "mark_triggered",
    "run_intraday_check",
]


# ========================================================================
# 14:45 命中检查 (供 API /check-now 与 scripts/watch_check.py 共用)
# ========================================================================

#: 命中容差. 0.5% 给盘中噪音留余地.
PRICE_TOLERANCE: float = 0.005


def evaluate_hit(
    watch: "WatchSubscription", intraday_price: float,
) -> tuple[bool, str]:
    """判定命中. 返回 (hit, reason_cn).

    v1 只接 kind=price.
    long:  intraday_price <= level * (1 + tol) 命中
    short: intraday_price >= level * (1 - tol) 命中
    """
    if watch.watch_kind != "price" or watch.level is None:
        return False, f"v1 不接 kind={watch.watch_kind} 的命中判定 (TODO)"
    level = float(watch.level)
    if watch.direction == "long":
        threshold = level * (1 + PRICE_TOLERANCE)
        if intraday_price <= threshold:
            return True, (
                f"长: 14:45 价 {intraday_price:.2f} ≤ level {level:.2f}×"
                f"(1+{PRICE_TOLERANCE})={threshold:.2f}"
            )
    elif watch.direction == "short":
        threshold = level * (1 - PRICE_TOLERANCE)
        if intraday_price >= threshold:
            return True, (
                f"短: 14:45 价 {intraday_price:.2f} ≥ level {level:.2f}×"
                f"(1-{PRICE_TOLERANCE})={threshold:.2f}"
            )
    return False, f"未命中 (14:45 价 {intraday_price:.2f}, 阈值 {level:.2f})"


@dataclass(frozen=True, slots=True)
class CheckReport:
    """单次 checker 跑的报告."""
    total_active: int
    triggered: list[str]          # 被命中的 watch_id
    skipped: list[tuple[str, str]]   # (watch_id, reason)
    checked_at: str               # 本次跑的 UTC iso


def run_intraday_check(
    db_path: str,
    *,
    quote_provider=None,
    dry_run: bool = False,
) -> CheckReport:
    """对所有 active watch 跑一次命中判定.

    quote_provider: 注入便于测试; 默认 TencentQuoteProvider.
    dry_run=True: 不写库, 只打印 + 跳过 mark_checked/mark_triggered.
    """
    from lei_signal.api.quotes import TencentQuoteProvider  # noqa: PLC0415

    if quote_provider is None:
        quote_provider = TencentQuoteProvider()

    conn = connect(db_path)
    now_iso = _now()
    triggered: list[str] = []
    skipped: list[tuple[str, str]] = []
    try:
        active = list_watches(conn, filter_states=(WATCH_ACTIVE,))
        total = len(active)
        for w in active:
            try:
                quote = quote_provider.fetch(w.symbol)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[%s] 取盘中价失败: %s", w.symbol, exc)
                skipped.append((w.watch_id, f"取价失败: {exc}"))
                if not dry_run:
                    mark_checked(conn, w.watch_id, now_iso=now_iso)
                continue
            if quote is None or quote.price is None:
                skipped.append((w.watch_id, "盘中价不可用"))
                if not dry_run:
                    mark_checked(conn, w.watch_id, now_iso=now_iso)
                continue
            intraday = float(quote.price)
            hit, reason = evaluate_hit(w, intraday)
            if dry_run:
                logger.info(
                    "[DRY] %s (%s %s level=%s 14:45=%s) -> %s",
                    w.symbol, w.watch_kind, w.direction, w.level, intraday, reason,
                )
                continue
            if hit:
                mark_triggered(
                    conn, w.watch_id,
                    triggered_price=intraday,
                    triggered_reason_cn=reason,
                    now_iso=now_iso,
                )
                triggered.append(w.watch_id)
                logger.info(
                    "[HIT] %s watch_id=%s level=%s 14:45=%s reason=%s",
                    w.symbol, w.watch_id, w.level, intraday, reason,
                )
            else:
                mark_checked(conn, w.watch_id, now_iso=now_iso)
    finally:
        conn.close()
    return CheckReport(
        total_active=total, triggered=triggered, skipped=skipped, checked_at=now_iso,
    )
