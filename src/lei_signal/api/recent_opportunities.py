"""Compact recent technical events from a saved opportunity run and cached analysis."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import date
from pathlib import Path

from lei_signal.api.sell_signals import RECENCY_BARS
from lei_signal.copilot import opportunity_review
from lei_signal.domain.types import Provenance

_CURRENT_RULE_SOURCES = frozenset(
    {
        Provenance.LEI_EXPLICIT.value,
        Provenance.LEI_INFERRED.value,
        Provenance.EXISTING_BACKTEST.value,
    }
)


def latest_saved_run(db_path: str) -> dict | None:
    """Read the newest persisted board without creating a database or starting work."""
    path = Path(db_path).resolve()
    if not path.is_file():
        return None
    try:
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as conn:
            try:
                row = conn.execute(
                    "SELECT r.run_id FROM opportunity_review_current AS c "
                    "JOIN opportunity_review_runs AS r ON r.run_id=c.run_id "
                    "WHERE c.slot='current'"
                ).fetchone()
            except sqlite3.OperationalError as exc:
                if "no such table: opportunity_review_current" not in str(exc):
                    raise
                row = None
            if row is None:
                row = conn.execute(
                    "SELECT run_id FROM opportunity_review_runs "
                    "ORDER BY checked_at DESC, rowid DESC LIMIT 1"
                ).fetchone()
            return opportunity_review._run(conn, row[0], reused=True) if row else None
    except sqlite3.OperationalError as exc:
        if "no such table: opportunity_review_runs" in str(exc):
            return None
        raise


def _day(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed.isoformat() if parsed.isoformat() == value else None


def _subject(item: dict) -> tuple[str, str, str, str] | None:
    card = item.get("card") or {}
    subject = card.get("subject") or {}
    key = subject.get("key")
    kind = subject.get("kind")
    symbol = subject.get("id") if kind == "symbol" else subject.get("symbol")
    if not all(isinstance(x, str) and x for x in (key, symbol)):
        return None
    name = subject.get("name") or subject.get("display_name") or symbol
    return key, symbol, str(name), kind


def build_recent_opportunities(
    board: dict | None,
    snapshot_for_symbol: Callable[[str], dict | None],
) -> dict:
    """Use precomputed signal status; never infer a trigger from card wording."""
    result = {
        "schema_version": "recent-opportunities/1",
        "run_id": board.get("run_id") if board else None,
        "checked_at": board.get("checked_at") if board else None,
        "review_status": board.get("status") if board else "missing",
        "review_incomplete": bool(board and board.get("status") != "complete"),
        "cached_subjects": 0,
        "missing_cached_subjects": 0,
        "unverified_cached_subjects": 0,
        "items": [],
        "waiting": [],
        "cleared": [],
    }
    if not board:
        return result
    subjects: dict[str, tuple[str, str, str, str]] = {}
    for item in board.get("items") or []:
        if not isinstance(item, dict):
            continue
        subject = _subject(item)
        if subject is None:
            continue
        key, symbol, _, kind = subject
        previous = subjects.get(symbol)
        if previous is None or (kind == "holding" and previous[3] != "holding"):
            subjects[symbol] = subject
    seen: set[tuple[str, str, str]] = set()
    for symbol, (key, _, name, _) in subjects.items():
        technical = snapshot_for_symbol(symbol)
        if technical is None:
            result["missing_cached_subjects"] += 1
            continue
        result["cached_subjects"] += 1
        meta = technical.get("meta") or {}
        bar_date = _day(meta.get("last_bar_date"))
        if not bar_date or meta.get("freshness") != "current":
            result["unverified_cached_subjects"] += 1
            continue
        closed = meta.get("bar_status") == "closed" and not meta.get("is_intraday_forming")
        for signal in technical.get("signals") or []:
            if (
                not isinstance(signal, dict)
                or signal.get("provenance") not in _CURRENT_RULE_SOURCES
            ):
                continue
            side = signal.get("side")
            status = signal.get("status")
            event_date = _day(signal.get("event_date"))
            age = signal.get("age_bars")
            state_changed = _day(signal.get("state_changed_date"))
            state_age = signal.get("state_age_bars")
            is_cleared = status == "cleared"
            if (
                side not in {"buy", "sell"}
                or status not in {"new", "active", "waiting", "cleared"}
                or (not is_cleared and signal.get("is_recent") is not True)
                or (not is_cleared and (
                    not isinstance(age, int) or isinstance(age, bool) or age < 0
                ))
                or event_date is None
                or event_date > bar_date
                or (is_cleared and (
                    state_changed is None or state_changed < event_date
                    or state_changed > bar_date
                    or not isinstance(state_age, int) or isinstance(state_age, bool)
                    or not 0 <= state_age < RECENCY_BARS
                ))
            ):
                continue
            identity = (symbol, side, str(signal.get("id") or ""))
            if identity in seen:
                continue
            seen.add(identity)
            row = {
                "id": str(signal.get("id") or ""),
                "subject_key": key,
                "symbol": symbol,
                "name": technical.get("display_name") or name,
                "side": side,
                "title": str(signal.get("title") or ""),
                "summary": str(signal.get("summary") or signal.get("title") or ""),
                "provenance": signal["provenance"],
                "event_date": event_date,
                "bar_date": bar_date,
                "status": status if closed else "waiting_close",
                "age_bars": age,
                "state_changed_date": state_changed,
                "state_age_bars": (state_age if isinstance(state_age, int)
                                   and not isinstance(state_age, bool) else None),
                "next_step_cn": str(signal.get("next_step_cn") or ""),
                "invalidation_cn": str(signal.get("invalidation_cn") or ""),
            }
            if is_cleared:
                result["cleared"].append(row)
            elif closed and status in {"new", "active"}:
                result["items"].append(row)
            else:
                result["waiting"].append(row)

    def order(row: dict) -> tuple:
        return (row["event_date"], -row["age_bars"], row["name"], row["side"])

    result["items"].sort(key=order, reverse=True)
    result["waiting"].sort(key=order, reverse=True)
    result["cleared"].sort(
        key=lambda row: (row["state_changed_date"], -row["state_age_bars"],
                         row["name"], row["side"]),
        reverse=True,
    )
    return result
