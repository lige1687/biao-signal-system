"""计划台账 SQLite CRUD + append-only 修订史 + 必填校验。

照 ``api/watchlist.py`` 的连接模式（函数取 ``conn: sqlite3.Connection``）。
``trade_plan_revisions`` 与 ``plan_annotations`` 只追加，永不 UPDATE；
``trade_plans`` 的当前值可在 within_playbook 修订后更新，但 revision_no=0 的
冻结快照永远不动。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import UTC, datetime

from lei_signal.plans.models import (
    PLAN_ARMED,
    PLAN_DRAFT,
    PLAYBOOK_FIELDS,
    VERDICT_SNAPSHOT,
    ActionItem,
    Annotation,
    PlanRevision,
    TradePlan,
)

# 允许的状态迁移（draft->armed 由 confirm_plan 校验必填后执行）
_TRANSITIONS: dict[str, frozenset[str]] = {
    PLAN_DRAFT: frozenset({PLAN_ARMED, "abandoned"}),
    PLAN_ARMED: frozenset({"entered", "invalidated", "superseded", "abandoned"}),
    "entered": frozenset({"exited", "invalidated"}),
}

_FREEZABLE_FIELDS = ("invalidation_price", *PLAYBOOK_FIELDS)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _gen_plan_id(symbol: str, created_at: str) -> str:
    short = hashlib.sha1(
        f"{symbol}:{created_at}:{uuid.uuid4().hex}".encode()
    ).hexdigest()[:8]
    safe_symbol = symbol.replace(".", "_")
    safe_time = created_at.replace(":", "").replace("-", "")
    return f"plan_{safe_symbol}_{safe_time}_{short}"


def _row_to_plan(row: sqlite3.Row) -> TradePlan:
    return TradePlan(
        plan_id=row["plan_id"],
        symbol=row["symbol"],
        module=row["module"],
        direction=row["direction"],
        entry_rule_id=row["entry_rule_id"],
        entry_lifecycle_id=row["entry_lifecycle_id"],
        entry_trigger_cn=row["entry_trigger_cn"],
        entry_price_ref=row["entry_price_ref"],
        invalidation_price=row["invalidation_price"],
        target_b_price=row["target_b_price"],
        target_b_source=row["target_b_source"],
        reward_risk_at_plan=row["reward_risk_at_plan"],
        valid_until=row["valid_until"],
        state=row["state"],
        ruleset_version=row["ruleset_version"],
        reason=row["reason"],
        thesis_cn=row["thesis_cn"],
        invalidation_criteria_cn=row["invalidation_criteria_cn"],
        drawdown_playbook_cn=row["drawdown_playbook_cn"],
        take_profit_plan_cn=row["take_profit_plan_cn"],
        stop_plan_cn=row["stop_plan_cn"],
        entered_on=row["entered_on"],
        exited_on=row["exited_on"],
        exit_reason_rule_id=row["exit_reason_rule_id"],
        superseded_by=row["superseded_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_revision(row: sqlite3.Row) -> PlanRevision:
    return PlanRevision(
        revision_id=row["revision_id"],
        plan_id=row["plan_id"],
        revision_no=row["revision_no"],
        changed_field=row["changed_field"],
        old_value=row["old_value"],
        new_value=row["new_value"],
        verdict=row["verdict"],
        verdict_reason_cn=row["verdict_reason_cn"],
        changed_at=row["changed_at"],
        changed_by=row["changed_by"],
    )


def _row_to_action(row: sqlite3.Row) -> ActionItem:
    return ActionItem(
        action_id=row["action_id"],
        plan_id=row["plan_id"],
        kind=row["kind"],
        source_alert_code=row["source_alert_code"],
        state=row["state"],
        due_from=row["due_from"],
        nag_count=row["nag_count"],
        last_nagged_bar_date=row["last_nagged_bar_date"],
        resume_on=row["resume_on"],
        closed_on=row["closed_on"],
        close_kind=row["close_kind"],
        created_at=row["created_at"],
    )


def _row_to_annotation(row: sqlite3.Row) -> Annotation:
    return Annotation(
        annotation_id=row["annotation_id"],
        plan_id=row["plan_id"],
        ref_kind=row["ref_kind"],
        ref_id=row["ref_id"],
        kind=row["kind"],
        reason_cn=row["reason_cn"],
        created_at=row["created_at"],
        author=row["author"],
    )


# ---------------------------------------------------------------- 计划主体


def create_plan(
    conn: sqlite3.Connection,
    *,
    symbol: str,
    module: str,
    direction: str,
    ruleset_version: str,
    reason: str = "",
    valid_until: str = "",
    entry_rule_id: str | None = None,
    entry_lifecycle_id: str | None = None,
    entry_trigger_cn: str | None = None,
    entry_price_ref: float | None = None,
    invalidation_price: float | None = None,
    target_b_price: float | None = None,
    target_b_source: str | None = None,
    reward_risk_at_plan: float | None = None,
    thesis_cn: str = "",
    invalidation_criteria_cn: str = "",
    drawdown_playbook_cn: str = "",
    take_profit_plan_cn: str = "",
    stop_plan_cn: str = "",
    plan_id: str | None = None,
) -> TradePlan:
    """创建 draft 计划。draft 阶段允许五项预案/valid_until/reason 为空。"""
    if direction not in ("long", "short"):
        raise ValueError(f"direction 必须为 long/short，得到 {direction}")
    created_at = _now()
    plan_id = plan_id or _gen_plan_id(symbol, created_at)
    conn.execute(
        """
        INSERT INTO trade_plans (
            plan_id, symbol, module, direction, entry_rule_id, entry_lifecycle_id,
            entry_trigger_cn, entry_price_ref, invalidation_price, target_b_price,
            target_b_source, reward_risk_at_plan, valid_until, state, ruleset_version,
            reason, thesis_cn, invalidation_criteria_cn, drawdown_playbook_cn,
            take_profit_plan_cn, stop_plan_cn, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            plan_id, symbol, module, direction, entry_rule_id, entry_lifecycle_id,
            entry_trigger_cn, entry_price_ref, invalidation_price, target_b_price,
            target_b_source, reward_risk_at_plan, valid_until, PLAN_DRAFT, ruleset_version,
            reason, thesis_cn, invalidation_criteria_cn, drawdown_playbook_cn,
            take_profit_plan_cn, stop_plan_cn, created_at, created_at,
        ),
    )
    # revision_no=0 创建快照：冻结原始失效价与五项预案
    snapshot = {f: _snapshot_value(f, invalidation_price, thesis_cn,
                                    invalidation_criteria_cn, drawdown_playbook_cn,
                                    take_profit_plan_cn, stop_plan_cn)
                for f in _FREEZABLE_FIELDS}
    _insert_revision(
        conn, plan_id=plan_id, revision_no=0, changed_field="__snapshot__",
        old_value=None, new_value=json.dumps(snapshot, ensure_ascii=False),
        verdict=VERDICT_SNAPSHOT, verdict_reason_cn="创建快照", changed_by="system",
    )
    conn.commit()
    return get_plan(conn, plan_id)  # type: ignore[return-value]


def _snapshot_value(field: str, invalidation_price: float | None, thesis_cn: str,
                    invalidation_criteria_cn: str, drawdown_playbook_cn: str,
                    take_profit_plan_cn: str, stop_plan_cn: str) -> object:
    if field == "invalidation_price":
        return invalidation_price
    return {
        "thesis_cn": thesis_cn,
        "invalidation_criteria_cn": invalidation_criteria_cn,
        "drawdown_playbook_cn": drawdown_playbook_cn,
        "take_profit_plan_cn": take_profit_plan_cn,
        "stop_plan_cn": stop_plan_cn,
    }[field]


def confirm_plan(conn: sqlite3.Connection, plan_id: str) -> TradePlan:
    """draft -> armed。armed 必须五项预案 + reason + valid_until 全部非空。"""
    plan = get_plan(conn, plan_id)
    if plan is None:
        raise KeyError(f"计划不存在: {plan_id}")
    if plan.state != PLAN_DRAFT:
        raise ValueError(f"只有 draft 可确认，当前 state={plan.state}")
    missing = [f for f in (PLAYBOOK_FIELDS + ("reason", "valid_until")) if not getattr(plan, f)]
    if missing:
        raise ValueError(f"armed 必填字段为空: {missing}")
    return transition_state(conn, plan_id, PLAN_ARMED)


def get_plan(conn: sqlite3.Connection, plan_id: str) -> TradePlan | None:
    row = conn.execute(
        "SELECT * FROM trade_plans WHERE plan_id = ?", (plan_id,)
    ).fetchone()
    return _row_to_plan(row) if row else None


def list_plans(
    conn: sqlite3.Connection,
    *,
    symbol: str | None = None,
    state: str | None = None,
) -> list[TradePlan]:
    sql = "SELECT * FROM trade_plans"
    clauses: list[str] = []
    params: list[object] = []
    if symbol:
        clauses.append("symbol = ?")
        params.append(symbol)
    if state:
        clauses.append("state = ?")
        params.append(state)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_plan(row) for row in rows]


def transition_state(
    conn: sqlite3.Connection, plan_id: str, new_state: str
) -> TradePlan:
    """状态机迁移。非法迁移即报错。"""
    plan = get_plan(conn, plan_id)
    if plan is None:
        raise KeyError(f"计划不存在: {plan_id}")
    allowed = _TRANSITIONS.get(plan.state, frozenset())
    if new_state not in allowed:
        raise ValueError(f"非法状态迁移: {plan.state} -> {new_state}")
    conn.execute(
        "UPDATE trade_plans SET state = ?, updated_at = ? WHERE plan_id = ?",
        (new_state, _now(), plan_id),
    )
    conn.commit()
    return get_plan(conn, plan_id)  # type: ignore[return-value]


def set_entered(
    conn: sqlite3.Connection, plan_id: str, *, entered_on: str
) -> TradePlan:
    """armed -> entered，记 entered_on（仅日期，无数量金额）。"""
    transition_state(conn, plan_id, "entered")
    conn.execute(
        "UPDATE trade_plans SET entered_on = ?, updated_at = ? WHERE plan_id = ?",
        (entered_on, _now(), plan_id),
    )
    conn.commit()
    return get_plan(conn, plan_id)  # type: ignore[return-value]


def mark_superseded(
    conn: sqlite3.Connection, plan_id: str, *, by_plan_id: str
) -> TradePlan:
    """armed -> superseded，记 superseded_by（决策 5）。"""
    transition_state(conn, plan_id, "superseded")
    conn.execute(
        "UPDATE trade_plans SET superseded_by = ?, updated_at = ? WHERE plan_id = ?",
        (by_plan_id, _now(), plan_id),
    )
    conn.commit()
    return get_plan(conn, plan_id)  # type: ignore[return-value]


# ---------------------------------------------------------------- 修订史（append-only）


def _insert_revision(
    conn: sqlite3.Connection,
    *,
    plan_id: str,
    revision_no: int,
    changed_field: str,
    old_value: str | None,
    new_value: str | None,
    verdict: str,
    verdict_reason_cn: str | None,
    changed_by: str,
) -> PlanRevision:
    revision_id = f"rev_{plan_id}_{revision_no}_{changed_field}_{uuid.uuid4().hex[:6]}"
    changed_at = _now()
    conn.execute(
        """
        INSERT INTO trade_plan_revisions (
            revision_id, plan_id, revision_no, changed_field, old_value, new_value,
            verdict, verdict_reason_cn, changed_at, changed_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (revision_id, plan_id, revision_no, changed_field, old_value, new_value,
         verdict, verdict_reason_cn, changed_at, changed_by),
    )
    return PlanRevision(
        revision_id=revision_id, plan_id=plan_id, revision_no=revision_no,
        changed_field=changed_field, old_value=old_value, new_value=new_value,
        verdict=verdict, verdict_reason_cn=verdict_reason_cn,
        changed_at=changed_at, changed_by=changed_by,
    )


def append_revision(
    conn: sqlite3.Connection,
    plan_id: str,
    *,
    changed_field: str,
    old_value: str | None,
    new_value: str | None,
    verdict: str,
    verdict_reason_cn: str | None,
    changed_by: str,
    apply_change: bool = False,
) -> PlanRevision:
    """追加修订记录（append-only）。apply_change=True 时同步更新 trade_plans 当前值。

    revision_no 自增；revision_no=0 永不触碰。verdict 由 drift.py 判定传入。
    """
    if changed_field == "__snapshot__":
        raise ValueError("不得手动追加 __snapshot__ 修订")
    row = conn.execute(
        "SELECT COALESCE(MAX(revision_no), 0) AS n FROM trade_plan_revisions WHERE plan_id = ?",
        (plan_id,),
    ).fetchone()
    revision_no = int(row["n"]) + 1
    rev = _insert_revision(
        conn, plan_id=plan_id, revision_no=revision_no, changed_field=changed_field,
        old_value=old_value, new_value=new_value, verdict=verdict,
        verdict_reason_cn=verdict_reason_cn, changed_by=changed_by,
    )
    if apply_change and changed_field in _FREEZABLE_FIELDS:
        # within_playbook 的收紧可更新当前值；冻结的 revision_no=0 不动
        _update_plan_field(conn, plan_id, changed_field, new_value)
    conn.commit()
    return rev


def _update_plan_field(
    conn: sqlite3.Connection, plan_id: str, field: str, value: str | None
) -> None:
    """更新 trade_plans 当前值（仅 within_playbook 收紧调用，非 append-only 表）。"""
    if field not in _FREEZABLE_FIELDS:
        raise ValueError(f"不支持更新字段: {field}")
    if field == "invalidation_price":
        conn.execute(
            f"UPDATE trade_plans SET {field} = ?, updated_at = ? WHERE plan_id = ?",
            (float(value) if value not in (None, "") else None, _now(), plan_id),
        )
    else:
        conn.execute(
            f"UPDATE trade_plans SET {field} = ?, updated_at = ? WHERE plan_id = ?",
            (value or "", _now(), plan_id),
        )


def list_revisions(conn: sqlite3.Connection, plan_id: str) -> list[PlanRevision]:
    rows = conn.execute(
        "SELECT * FROM trade_plan_revisions WHERE plan_id = ? ORDER BY revision_no, changed_field",
        (plan_id,),
    ).fetchall()
    return [_row_to_revision(row) for row in rows]


def frozen_snapshot(conn: sqlite3.Connection, plan_id: str) -> dict | None:
    """读取 revision_no=0 的冻结快照（原始失效价 + 五项预案）。"""
    row = conn.execute(
        "SELECT new_value FROM trade_plan_revisions "
        "WHERE plan_id = ? AND revision_no = 0 AND changed_field = '__snapshot__'",
        (plan_id,),
    ).fetchone()
    if row is None:
        return None
    return json.loads(row["new_value"])


# ---------------------------------------------------------------- 注解（append-only）


def add_annotation(
    conn: sqlite3.Connection,
    plan_id: str,
    *,
    ref_kind: str,
    ref_id: str | None,
    kind: str,
    reason_cn: str,
    author: str,
) -> Annotation:
    annotation_id = f"ann_{plan_id}_{uuid.uuid4().hex[:8]}"
    created_at = _now()
    conn.execute(
        """
        INSERT INTO plan_annotations (
            annotation_id, plan_id, ref_kind, ref_id, kind, reason_cn, created_at, author
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (annotation_id, plan_id, ref_kind, ref_id, kind, reason_cn, created_at, author),
    )
    conn.commit()
    return Annotation(
        annotation_id=annotation_id, plan_id=plan_id, ref_kind=ref_kind, ref_id=ref_id,
        kind=kind, reason_cn=reason_cn, created_at=created_at, author=author,
    )


def list_annotations(conn: sqlite3.Connection, plan_id: str) -> list[Annotation]:
    rows = conn.execute(
        "SELECT * FROM plan_annotations WHERE plan_id = ? ORDER BY created_at",
        (plan_id,),
    ).fetchall()
    return [_row_to_annotation(row) for row in rows]


# ---------------------------------------------------------------- 待办（P2 用，表在 P0 建好）


def upsert_action_item(
    conn: sqlite3.Connection,
    *,
    plan_id: str,
    kind: str,
    source_alert_code: str,
    state: str,
    due_from: str | None,
    action_id: str | None = None,
    resume_on: str | None = None,
) -> ActionItem:
    """按 (plan_id, kind) 幂等 upsert 待办。"""
    existing = conn.execute(
        "SELECT * FROM plan_action_items WHERE plan_id = ? AND kind = ?",
        (plan_id, kind),
    ).fetchone()
    created_at = existing["created_at"] if existing else _now()
    if existing:
        action_id = action_id or existing["action_id"]
    else:
        action_id = action_id or f"act_{plan_id}_{kind}_{uuid.uuid4().hex[:6]}"
    if existing:
        nag_count = existing["nag_count"]
        last_nagged = existing["last_nagged_bar_date"]
        closed_on = existing["closed_on"]
        close_kind = existing["close_kind"]
        resume = existing["resume_on"] if resume_on is None else resume_on
    else:
        nag_count = 0
        last_nagged = None
        closed_on = None
        close_kind = None
        resume = resume_on
    conn.execute(
        """
        INSERT OR REPLACE INTO plan_action_items (
            action_id, plan_id, kind, source_alert_code, state, due_from,
            nag_count, last_nagged_bar_date, resume_on, closed_on, close_kind, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (action_id, plan_id, kind, source_alert_code, state, due_from,
         nag_count, last_nagged, resume, closed_on, close_kind, created_at),
    )
    conn.commit()
    return ActionItem(
        action_id=action_id, plan_id=plan_id, kind=kind,
        source_alert_code=source_alert_code, state=state, due_from=due_from,
        nag_count=nag_count, last_nagged_bar_date=last_nagged, resume_on=resume,
        closed_on=closed_on, close_kind=close_kind, created_at=created_at,
    )


def list_action_items(
    conn: sqlite3.Connection, plan_id: str, *, state: str | None = None
) -> list[ActionItem]:
    sql = "SELECT * FROM plan_action_items WHERE plan_id = ?"
    params: list[object] = [plan_id]
    if state:
        sql += " AND state = ?"
        params.append(state)
    sql += " ORDER BY created_at"
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_action(row) for row in rows]


def get_action_item(conn: sqlite3.Connection, action_id: str) -> ActionItem | None:
    row = conn.execute(
        "SELECT * FROM plan_action_items WHERE action_id = ?", (action_id,)
    ).fetchone()
    return _row_to_action(row) if row else None


def update_action_item(
    conn: sqlite3.Connection,
    action_id: str,
    *,
    state: str | None = None,
    nag_count: int | None = None,
    last_nagged_bar_date: str | None = None,
    resume_on: str | None = None,
    closed_on: str | None = None,
    close_kind: str | None = None,
) -> ActionItem | None:
    item = get_action_item(conn, action_id)
    if item is None:
        return None
    conn.execute(
        """
        UPDATE plan_action_items SET
            state = ?, nag_count = ?, last_nagged_bar_date = ?, resume_on = ?,
            closed_on = ?, close_kind = ?
        WHERE action_id = ?
        """,
        (
            state if state is not None else item.state,
            nag_count if nag_count is not None else item.nag_count,
            last_nagged_bar_date if last_nagged_bar_date is not None else item.last_nagged_bar_date,
            resume_on if resume_on is not None else item.resume_on,
            closed_on if closed_on is not None else item.closed_on,
            close_kind if close_kind is not None else item.close_kind,
            action_id,
        ),
    )
    conn.commit()
    return get_action_item(conn, action_id)


__all__ = [
    "add_annotation",
    "append_revision",
    "confirm_plan",
    "create_plan",
    "frozen_snapshot",
    "get_action_item",
    "get_plan",
    "list_action_items",
    "list_annotations",
    "list_plans",
    "list_revisions",
    "mark_superseded",
    "set_entered",
    "transition_state",
    "update_action_item",
    "upsert_action_item",
]
