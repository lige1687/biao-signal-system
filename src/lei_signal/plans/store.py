"""计划台账 SQLite CRUD + append-only 修订史 + 必填校验。

照 ``api/watchlist.py`` 的连接模式（函数取 ``conn: sqlite3.Connection``）。
``trade_plan_revisions`` 与 ``plan_annotations`` 只追加，永不 UPDATE；
``trade_plans`` 的当前值可在 within_playbook 修订后更新，但 revision_no=0 的
冻结快照永远不动。
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from datetime import UTC, datetime

from lei_signal.plans.models import (
    PLAN_ARMED,
    PLAN_DRAFT,
    PLAN_ENTERED,
    PLAN_KIND_ENTRY,
    PLAN_KIND_HOLDING_WATCH,
    PLAN_KINDS,
    PLAYBOOK_FIELDS,
    REQUIRED_FOR_HOLDING_WATCH,
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

#: 持仓盯盘额外允许 draft->entered（已在场内，不经 armed 入场判定）。
#: 只对 plan_kind=holding_watch 放开--普通入场计划仍必须走 armed，
#: 否则就能绕过五项预案必填校验直接落 entered。
_HOLDING_WATCH_EXTRA_TRANSITIONS: dict[str, frozenset[str]] = {
    PLAN_DRAFT: frozenset({PLAN_ENTERED}),
}

_FREEZABLE_FIELDS = ("invalidation_price", *PLAYBOOK_FIELDS)


def _split_rule_ids(raw: str | None) -> tuple[str, ...]:
    """逗号分隔 rule_id 串 -> tuple。空串/None -> ()。"""
    if not raw:
        return ()
    return tuple(part.strip() for part in str(raw).split(",") if part.strip())


def _join_rule_ids(rule_ids: tuple[str, ...] | list[str] | None) -> str:
    return ",".join(r.strip() for r in (rule_ids or ()) if r.strip())


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _gen_plan_id(symbol: str, created_at: str) -> str:
    """URL/回调安全的 plan_id：只含字母数字与下划线。

    ISO 时间戳里的 `.` `:` `-` `+` 都会进 URL 路径与飞书回调参数，必须清掉。
    """
    short = hashlib.sha1(
        f"{symbol}:{created_at}:{uuid.uuid4().hex}".encode()
    ).hexdigest()[:8]
    safe_symbol = re.sub(r"[^A-Za-z0-9]", "_", symbol)
    safe_time = re.sub(r"[^0-9]", "", created_at)[:14]  # YYYYMMDDHHMMSS
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
        plan_kind=row["plan_kind"],
        take_profit_price=row["take_profit_price"],
        stop_price=row["stop_price"],
        watch_signal_rule_ids=_split_rule_ids(row["watch_signal_rule_ids"]),
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
    plan_kind: str = PLAN_KIND_ENTRY,
    take_profit_price: float | None = None,
    stop_price: float | None = None,
    watch_signal_rule_ids: tuple[str, ...] | list[str] | None = None,
    plan_id: str | None = None,
) -> TradePlan:
    """创建 draft 计划。draft 阶段允许五项预案/valid_until/reason 为空。"""
    if direction not in ("long", "short"):
        raise ValueError(f"direction 必须为 long/short，得到 {direction}")
    if plan_kind not in PLAN_KINDS:
        raise ValueError(f"plan_kind 必须为 {PLAN_KINDS} 之一，得到 {plan_kind}")
    created_at = _now()
    plan_id = plan_id or _gen_plan_id(symbol, created_at)
    conn.execute(
        """
        INSERT INTO trade_plans (
            plan_id, symbol, module, direction, entry_rule_id, entry_lifecycle_id,
            entry_trigger_cn, entry_price_ref, invalidation_price, target_b_price,
            target_b_source, reward_risk_at_plan, valid_until, state, ruleset_version,
            reason, thesis_cn, invalidation_criteria_cn, drawdown_playbook_cn,
            take_profit_plan_cn, stop_plan_cn, plan_kind, take_profit_price,
            stop_price, watch_signal_rule_ids, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            plan_id, symbol, module, direction, entry_rule_id, entry_lifecycle_id,
            entry_trigger_cn, entry_price_ref, invalidation_price, target_b_price,
            target_b_source, reward_risk_at_plan, valid_until, PLAN_DRAFT, ruleset_version,
            reason, thesis_cn, invalidation_criteria_cn, drawdown_playbook_cn,
            take_profit_plan_cn, stop_plan_cn, plan_kind, take_profit_price,
            stop_price, _join_rule_ids(watch_signal_rule_ids), created_at, created_at,
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


def confirm_holding_watch(
    conn: sqlite3.Connection, plan_id: str, *, entered_on: str
) -> TradePlan:
    """持仓盯盘 draft -> entered（已在场内，不经 armed 入场判定）。

    必填（人类 2026-08-05 决定）：
      - 两项退出预案（take_profit_plan_cn / stop_plan_cn）--「什么逻辑退出」
        必须先写下来，否则价位到了仍会临场改主意；
      - valid_until；
      - 至少一个退出触发条件：止盈价 / 止损价 / 信号 rule_id。三者全空则无从监督。
    入场理由（五项里的另外三项、entry_rule_id、R/R）不强制--你已经在场内了。
    """
    plan = get_plan(conn, plan_id)
    if plan is None:
        raise KeyError(f"计划不存在: {plan_id}")
    if plan.plan_kind != PLAN_KIND_HOLDING_WATCH:
        raise ValueError(
            f"confirm_holding_watch 只接受 plan_kind=holding_watch，得到 {plan.plan_kind}"
        )
    if plan.state != PLAN_DRAFT:
        raise ValueError(f"只有 draft 可确认，当前 state={plan.state}")
    missing = [f for f in REQUIRED_FOR_HOLDING_WATCH if not getattr(plan, f)]
    if missing:
        raise ValueError(f"持仓盯盘必填字段为空: {missing}")
    if (
        plan.take_profit_price is None
        and plan.stop_price is None
        and not plan.watch_signal_rule_ids
    ):
        raise ValueError(
            "持仓盯盘至少需要一个退出触发条件：止盈价 / 止损价 / 信号 rule_id"
        )
    transition_state(conn, plan_id, PLAN_ENTERED)
    conn.execute(
        "UPDATE trade_plans SET entered_on = ?, updated_at = ? WHERE plan_id = ?",
        (entered_on, _now(), plan_id),
    )
    conn.commit()
    return get_plan(conn, plan_id)  # type: ignore[return-value]


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
    if plan.plan_kind == PLAN_KIND_HOLDING_WATCH:
        allowed = allowed | _HOLDING_WATCH_EXTRA_TRANSITIONS.get(plan.state, frozenset())
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


def set_exited(
    conn: sqlite3.Connection, plan_id: str, *, exited_on: str
) -> TradePlan:
    """entered -> exited，记 exited_on（仅日期，无数量金额）。

    与 set_entered 对称：EXIT 确认同样盖 exited_on，使计划时间线（持有时长、
    有效期）在入场/退出两侧口径一致。exited_on 取 EXIT 待办的 due_from（系统
    判定的可执行日），与 entered_on 取 ENTER 待办 due_from 同源。
    """
    transition_state(conn, plan_id, "exited")
    conn.execute(
        "UPDATE trade_plans SET exited_on = ?, updated_at = ? WHERE plan_id = ?",
        (exited_on, _now(), plan_id),
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


def count_open_action_items(conn: sqlite3.Connection) -> int:
    """全库未处理待办数（state=open），供监督待办顶栏红点。"""
    row = conn.execute(
        "SELECT COUNT(*) FROM plan_action_items WHERE state = 'open'"
    ).fetchone()
    return int(row[0]) if row else 0


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
    "confirm_holding_watch",
    "confirm_plan",
    "count_open_action_items",
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
    "set_exited",
    "transition_state",
    "update_action_item",
    "upsert_action_item",
]
