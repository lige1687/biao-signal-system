"""P0 地基与数据模型门禁：migration 010 / store 往返 / 必填校验 / append-only / 日历。"""
from __future__ import annotations

from datetime import date

import pytest

from lei_signal.data.calendar import DEFAULT_TRADING_CALENDAR, weekday_calendar
from lei_signal.plans import store
from lei_signal.plans.models import (
    PLAN_ARMED,
    PLAN_DRAFT,
    VERDICT_SNAPSHOT,
    VERDICT_WITHIN_PLAYBOOK,
)
from lei_signal.storage.sqlite_store import MIGRATIONS, connect

RULESET = "1.3.0"


# ---------------------------------------------------------------- 日历


def test_next_trading_day_skips_weekend() -> None:
    # 2025-01-03 是周五 -> 下一个交易日是周一 01-06
    nxt = DEFAULT_TRADING_CALENDAR.next_trading_day(date(2025, 1, 3))
    assert nxt.date() == date(2025, 1, 6)


def test_next_trading_day_skips_injected_holidays() -> None:
    cal = weekday_calendar({date(2025, 1, 6)})  # 周一放假
    nxt = cal.next_trading_day(date(2025, 1, 3))  # 周五
    assert nxt.date() == date(2025, 1, 7)  # 跳到周二


def test_next_trading_day_midweek() -> None:
    assert DEFAULT_TRADING_CALENDAR.next_trading_day(date(2025, 1, 7)).date() == date(2025, 1, 8)


# ---------------------------------------------------------------- migration


def test_migration_010_registered() -> None:
    names = [name for _, name, _ in MIGRATIONS]
    assert "010_trade_plans" in names


def test_migration_010_applies_on_fresh_db(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "fresh.db")
    tables = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    for table in ("trade_plans", "trade_plan_revisions", "plan_action_items", "plan_annotations"):
        assert table in tables, f"缺少表 {table}"
    # 再开一次：幂等，不重复 apply
    conn2 = connect(tmp_path / "fresh.db")
    conn2.close()
    conn.close()


# ---------------------------------------------------------------- store 往返


def _draft_kwargs(**overrides):
    return {
        "symbol": "000001.SS", "module": "A", "direction": "long",
        "ruleset_version": RULESET, "reason": "周线多头回调", "valid_until": "2026-12-31",
        "entry_rule_id": "first_ma_pullback", "entry_lifecycle_id": "lc:1",
        "entry_trigger_cn": "站回 SMA20", "entry_price_ref": 3800.0,
        "invalidation_price": 3650.0, "target_b_price": 4200.0,
        "target_b_source": "swing_high", "reward_risk_at_plan": 3.5,
        "thesis_cn": "冲周线多头回调", "invalidation_criteria_cn": "收盘跌破 3650",
        "drawdown_playbook_cn": "回踩 SMA60 正常", "take_profit_plan_cn": "到 B1 分批",
        "stop_plan_cn": "收盘跌破失效价下一日开盘出",
        **overrides,
    }


def test_create_draft_confirm_armed_roundtrip(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "rt.db")
    plan = store.create_plan(conn, **_draft_kwargs())
    assert plan.state == PLAN_DRAFT
    assert plan.invalidation_price == 3650.0

    armed = store.confirm_plan(conn, plan.plan_id)
    assert armed.state == PLAN_ARMED

    # revision_no=0 快照存在
    snap = store.frozen_snapshot(conn, plan.plan_id)
    assert snap is not None
    assert snap["invalidation_price"] == 3650.0
    assert snap["thesis_cn"] == "冲周线多头回调"

    # 追加一条 within_playbook 收紧修订（上移失效价），同步更新当前值
    rev = store.append_revision(
        conn, plan.plan_id, changed_field="invalidation_price",
        old_value="3650.0", new_value="3700.0",
        verdict=VERDICT_WITHIN_PLAYBOOK, verdict_reason_cn="移动止盈收紧",
        changed_by="user", apply_change=True,
    )
    assert rev.revision_no == 1
    assert rev.verdict == VERDICT_WITHIN_PLAYBOOK

    refreshed = store.get_plan(conn, plan.plan_id)
    assert refreshed.invalidation_price == 3700.0  # 当前值已更新
    revisions = store.list_revisions(conn, plan.plan_id)
    assert [r.revision_no for r in revisions] == [0, 1]
    assert revisions[0].verdict == VERDICT_SNAPSHOT
    conn.close()


def test_armed_requires_all_playbook_fields(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "req.db")
    # 五项预案留空 -> draft 可建，confirm 必失败
    plan = store.create_plan(conn, **_draft_kwargs(thesis_cn="", valid_until=""))
    assert plan.state == PLAN_DRAFT
    with pytest.raises(ValueError, match="必填字段为空"):
        store.confirm_plan(conn, plan.plan_id)
    conn.close()


def test_revision_no_zero_frozen_after_revisions(tmp_path) -> None:  # noqa: ANN001
    """任意修订后 revision_no=0 的失效价与五项预案逐字不变。"""
    conn = connect(tmp_path / "frz.db")
    plan = store.create_plan(conn, **_draft_kwargs())
    snap_before = store.frozen_snapshot(conn, plan.plan_id)

    # 多次修订（放宽失败价 -> needs_review 不 apply；收紧 -> apply）
    store.append_revision(
        conn, plan.plan_id, changed_field="invalidation_price",
        old_value="3650.0", new_value="3600.0", verdict="needs_review",
        verdict_reason_cn="放宽需复议", changed_by="user", apply_change=False,
    )
    store.append_revision(
        conn, plan.plan_id, changed_field="invalidation_price",
        old_value="3650.0", new_value="3750.0", verdict=VERDICT_WITHIN_PLAYBOOK,
        verdict_reason_cn="收紧", changed_by="user", apply_change=True,
    )
    snap_after = store.frozen_snapshot(conn, plan.plan_id)
    assert snap_after == snap_before  # revision_no=0 完全不变
    assert snap_after["invalidation_price"] == 3650.0
    # 当前值被最后一次 apply 改了
    assert store.get_plan(conn, plan.plan_id).invalidation_price == 3750.0
    conn.close()


def test_illegal_state_transition_rejected(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "st.db")
    plan = store.create_plan(conn, **_draft_kwargs())
    with pytest.raises(ValueError, match="非法状态迁移"):
        store.transition_state(conn, plan.plan_id, "entered")  # draft 不能直接 entered
    conn.close()


def test_set_entered_and_set_exited_stamp_dates(tmp_path) -> None:  # noqa: ANN001
    """set_entered / set_exited 对称盖 entered_on / exited_on（仅日期，无数量金额）。"""
    conn = connect(tmp_path / "dates.db")
    plan = store.create_plan(conn, **_draft_kwargs())
    store.confirm_plan(conn, plan.plan_id)
    entered = store.set_entered(conn, plan.plan_id, entered_on="2026-08-04")
    assert entered.state == "entered"
    assert entered.entered_on == "2026-08-04"
    assert entered.exited_on is None
    exited = store.set_exited(conn, plan.plan_id, exited_on="2026-08-05")
    assert exited.state == "exited"
    assert exited.exited_on == "2026-08-05"
    assert exited.entered_on == "2026-08-04"  # 入场日不被退出覆盖
    conn.close()


def test_annotations_append_only(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "ann.db")
    plan = store.create_plan(conn, **_draft_kwargs())
    a1 = store.add_annotation(
        conn, plan.plan_id, ref_kind="revision", ref_id="rev1",
        kind="defer_reason", reason_cn="等回踩 SMA60", author="user",
    )
    a2 = store.add_annotation(
        conn, plan.plan_id, ref_kind="action", ref_id="act1",
        kind="afterthought", reason_cn="事后复盘", author="user",
    )
    anns = store.list_annotations(conn, plan.plan_id)
    assert [a.annotation_id for a in anns] == [a1.annotation_id, a2.annotation_id]
    conn.close()


def test_action_item_upsert_idempotent(tmp_path) -> None:  # noqa: ANN001
    conn = connect(tmp_path / "act.db")
    plan = store.create_plan(conn, **_draft_kwargs())
    store.confirm_plan(conn, plan.plan_id)
    item = store.upsert_action_item(
        conn, plan_id=plan.plan_id, kind="ENTER",
        source_alert_code="ENTRY_CONDITIONS_MET", state="open", due_from="2026-08-05",
    )
    # 再次 upsert 同 kind -> 幂等（同 action_id，不新增行）
    item2 = store.upsert_action_item(
        conn, plan_id=plan.plan_id, kind="ENTER",
        source_alert_code="ENTRY_CONDITIONS_MET", state="open", due_from="2026-08-05",
    )
    assert item.action_id == item2.action_id
    assert len(store.list_action_items(conn, plan.plan_id)) == 1
    # 全库 open 待办计数（顶栏红点）：1 个 open。
    assert store.count_open_action_items(conn) == 1
    store.update_action_item(conn, item.action_id, state="done", close_kind="done")
    assert store.count_open_action_items(conn) == 0
    conn.close()
