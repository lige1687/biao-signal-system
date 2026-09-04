"""操作清单组装：待办/持仓处理/推荐/观察触发四段。"""
from __future__ import annotations

import pytest

from lei_signal.api.schemas import RecommendCardDTO
from lei_signal.copilot import ops
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    yield c
    c.close()


def test_empty_db_honest_empty_sections(conn):
    card = ops.build_ops_today(conn, run_date="2026-09-05", recommend_card=None)
    assert card.plan_todos == []
    assert card.recommendations is None
    assert card.push_summary_cn


def test_waiting_scan_rows_become_watch_triggers(conn):
    from lei_signal.api.opportunity_scan import today_date

    conn.execute(
        "INSERT OR REPLACE INTO daily_opportunity_scan "
        "(scan_date, symbol, display_name, verdict, verdict_cn, best_scenario_cn, "
        " best_state, reward_risk_ratio, reward_risk_computable, blocking_reasons, "
        " missing_summary_cn, has_active_plan, generated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (today_date(), "515880", "通信ETF", "waiting", "等待条件成立",
         "A·回调", "watch", 2.5, 1, "[]", "站上EMA20", 0, "x"),
    )
    conn.commit()
    card = ops.build_ops_today(
        conn, run_date=today_date(),
        recommend_card=RecommendCardDTO(run_date=today_date()),
    )
    assert any(t.symbol == "515880" for t in card.watch_triggers)


def test_exit_todo_ranked_first(conn):
    from lei_signal.plans.store import confirm_plan, create_plan

    plan = create_plan(
        conn,
        symbol="515880", module="A", direction="long",
        ruleset_version="test",
        reason="t", valid_until="2026-10-01",
        thesis_cn="t", invalidation_criteria_cn="t", drawdown_playbook_cn="t",
        take_profit_plan_cn="t", stop_plan_cn="t",
    )
    confirm_plan(conn, plan.plan_id)
    conn.execute(
        "INSERT INTO plan_action_items (action_id, plan_id, kind, state, due_from, "
        "nag_count, source_alert_code, created_at) VALUES (?,?,?,?,?,?,?,?)",
        ("a1", plan.plan_id, "EXIT", "open", "2026-09-05", 3,
         "INVALIDATION_BREACHED", "2026-09-05T00:00:00"),
    )
    conn.commit()
    card = ops.build_ops_today(conn, run_date="2026-09-05", recommend_card=None)
    assert card.plan_todos and card.plan_todos[0].kind == "EXIT"
    assert card.plan_todos[0].nag_count == 3
    assert "退出" in card.push_summary_cn or "EXIT" in card.push_summary_cn
    assert any("退出待办" in h.text_cn for h in card.holdings_actions)
