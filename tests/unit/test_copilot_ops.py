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
        # 总控决定 1（2026-09-08）：技术 entry 确认必须有明确失效价；
        # 本用例断言的是 EXIT 待办排序，与失效价无关，故补齐合法值
        invalidation_price=1.0,
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


# ---- dca 状态块（2026-09-20 接入，V1 状态位）三态组装测试 ----
# 真实数据禁碰：证据账本用 tmp_path 临时文件，行情/宽度全部构造注入。


def _fake_bars(n: int = 260):
    import pandas as pd

    idx = pd.bdate_range("2025-01-01", periods=n)
    close = [100.0 + i * 0.1 for i in range(n)]
    return pd.DataFrame({"close": close}, index=idx)


def _fake_breadth(market: str):
    from lei_signal.dca.state import BreadthReading

    return BreadthReading(market, 50.0, "test-source", "2026-09-18",
                          "2026-09-18", None, "unknown",
                          "测试注入（发布节奏未核实）")


def _missing_breadth(_market: str):
    raise RuntimeError("测试注入：宽度文件缺失")


def _write_evidence(tmp_path):
    import json

    p = tmp_path / "dca_evidence.json"
    p.write_text(json.dumps({
        "version": "test-v1",
        "state_expectations": {},
    }, ensure_ascii=False), encoding="utf-8")
    return p


def test_dca_block_with_data(tmp_path):
    block = ops._build_dca_block(
        evidence_path=_write_evidence(tmp_path),
        loader=lambda s: _fake_bars(),
        breadth_reader=_fake_breadth,
        symbols=[("TEST1", "测试指数")],
    )
    assert block.available is True
    assert block.evidence_available is True
    assert block.evidence_version == "test-v1"
    assert block.reason_cn == ""
    assert block.states and block.states[0]["symbol"] == "TEST1"
    st = block.states[0]
    assert st["state_status"] == "ok"
    assert st["deep20"] is False and st["bottom_zone"] is False  # 上升序列未触发
    assert block.breadth["cn"]["health"] == "unknown"
    assert block.breadth["us"]["market"] == "sp500"


def test_dca_block_degrades_when_evidence_missing(tmp_path):
    block = ops._build_dca_block(
        evidence_path=tmp_path / "missing.json",
        loader=lambda s: None,
        breadth_reader=_missing_breadth,
    )
    assert block.available is False
    assert block.evidence_available is False
    assert "不存在" in block.reason_cn
    # 逐状态仍如实给出：跟踪池全 insufficient_data（缺数据=null），不编数
    assert block.states
    assert all(s["state_status"] == "insufficient_data" for s in block.states)
    assert block.breadth == {"cn": None, "us": None}


def test_dca_block_partial_breadth_missing(tmp_path):
    block = ops._build_dca_block(
        evidence_path=_write_evidence(tmp_path),
        loader=lambda s: _fake_bars(),
        breadth_reader=_missing_breadth,
        symbols=[("TEST1", "测试指数")],
    )
    # 证据账本可读、价格可判 → 块整体可用；宽度缺席只降级依赖它的状态
    assert block.available is True
    assert block.breadth == {"cn": None, "us": None}
    st = block.states[0]
    assert st["deep20"] is False        # 深超跌只依赖价格：仍可判
    assert st["bottom_zone"] is None    # 底部区域依赖宽度：无法判定（null≠false）


def test_ops_card_wires_dca_block_without_touching_sentiment(conn, tmp_path):
    block = ops._build_dca_block(
        evidence_path=_write_evidence(tmp_path),
        loader=lambda s: _fake_bars(),
        breadth_reader=_fake_breadth,
        symbols=[("TEST1", "测试指数")],
    )
    card_with = ops.build_ops_today(
        conn, run_date="2026-09-20", recommend_card=None,
        dca_reader=lambda: block,
    )
    card_none = ops.build_ops_today(
        conn, run_date="2026-09-20", recommend_card=None,
        dca_reader=lambda: None,
    )
    assert card_with.dca is block and card_with.dca.available is True
    assert card_none.dca is None
    # dca 接入对情绪面块零影响：同库同参数两次组装，情绪面逐字段一致
    assert card_with.sentiment is not None
    assert card_with.sentiment == card_none.sentiment


def test_ops_card_survives_dca_reader_failure(conn):
    def _boom():
        raise RuntimeError("测试注入：读取器失败")

    card = ops.build_ops_today(
        conn, run_date="2026-09-20", recommend_card=None, dca_reader=_boom,
    )
    assert card.dca is None
    assert card.push_summary_cn
