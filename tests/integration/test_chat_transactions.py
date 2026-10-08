"""Isolated API integration of chat transaction guardrails; no live provider calls."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.integrations.chat_transactions import ChatTransactions, WorkflowError
from lei_signal.plans.sessions import append_message, create_session
from lei_signal.plans.store import create_plan
from lei_signal.portfolio.models import PortfolioGroup, PortfolioHolding
from lei_signal.portfolio.store import upsert_group, upsert_holding
from lei_signal.storage.sqlite_store import connect


@pytest.fixture
def flow(tmp_path, monkeypatch):
    import lei_signal.api.app as app_module
    import lei_signal.copilot.trades as trades
    import lei_signal.plans.llm as plans_llm

    monkeypatch.setattr(trades, "fetch_nav_history", lambda *a, **kw: [])
    monkeypatch.setattr(app_module, "_warm_a_share_breadth", lambda: None)
    monkeypatch.setattr(app_module, "start_preheat", lambda *a, **kw: None)
    monkeypatch.setattr(plans_llm, "load_ark_config", lambda: None)
    monkeypatch.setattr(
        plans_llm, "_llm_call", lambda *a, **kw: pytest.fail("LLM must stay offline")
    )
    path = str(tmp_path / "isolated.db")
    app = create_app(
        analysis_service=SimpleNamespace(
            get=lambda symbol: SimpleNamespace(result=None, error="isolated unavailable")
        )
    )
    app.state.plans_db_path = path
    app.state.portfolio_db_path = path
    app.state.watchlist_db_path = path
    with TestClient(app) as client:
        yield ChatTransactions(client), client, path


def test_real_trade_requires_explicit_date_and_confirmation_then_reads_back(flow):
    bridge, client, _ = flow
    pending = bridge.preview_trade("我买了 515880 一万元")
    assert pending["status"] == "pending"
    with pytest.raises(WorkflowError):
        bridge.record_trade(
            pending,
            {"confirmed": True, "request_id": "trade.0001", "fingerprint": pending["fingerprint"]},
        )
    card = bridge.preview_trade("2026-10-08 我买了 515880 10000 元")
    assert card["status"] == "confirmable", card
    confirmed = {"confirmed": True, "request_id": "trade.0001", "fingerprint": card["fingerprint"]}
    first = bridge.record_trade(card, confirmed)
    second = bridge.record_trade(card, confirmed)
    assert first["trade_id"] == second["trade_id"]
    assert first["amount"] == 10000 and first["trade_date"] == "2026-10-08"
    assert len(client.get("/api/copilot/trades").json()["trades"]) == 1


@pytest.mark.parametrize(
    "message",
    [
        "如果 2026-10-08 买了 515880 10000 元",
        "2026-10-08 我还没买 515880 10000 元",
        "2026-10-08 买卖 515880 10000 元",
        "2026-10-08 不要记我买了 515880 10000 元",
    ],
)
def test_hypothetical_negated_or_two_sided_reports_never_save(flow, message):
    bridge, client, _ = flow
    card = bridge.preview_trade(message)
    assert card["status"] == "pending"
    with pytest.raises(WorkflowError):
        bridge.record_trade(
            card,
            {"confirmed": True, "request_id": "trade.0002", "fingerprint": card["fingerprint"]},
        )
    assert client.get("/api/copilot/trades").json()["trades"] == []


def test_trade_card_change_and_request_conflict(flow):
    bridge, _, _ = flow
    card = bridge.preview_trade("2026-10-08 我卖了 515880 2000 元")
    assert card["side"] == "sell"
    with pytest.raises(WorkflowError):
        bridge.record_trade(
            card, {"confirmed": True, "request_id": "trade.0003", "fingerprint": "wrong"}
        )
    bridge.record_trade(
        card, {"confirmed": True, "request_id": "trade.0003", "fingerprint": card["fingerprint"]}
    )
    other = bridge.preview_trade("2026-10-08 我卖了 515880 3000 元")
    with pytest.raises(WorkflowError, match="409"):
        bridge.record_trade(
            other,
            {"confirmed": True, "request_id": "trade.0003", "fingerprint": other["fingerprint"]},
        )


def test_plan_draft_real_source_binding_idempotency_and_conformance_boundary(flow):
    bridge, client, path = flow
    with connect(path) as conn:
        session = create_session(conn, "000001.SS", "计划讨论")
        question = append_message(
            conn,
            session.session_id,
            "user",
            "请整理我的计划",
            True,
            {"discussion_v1": {"symbol": "000001.SS"}},
        )
    source = {
        "question_id": question.message_id,
        "session_id": session.session_id,
        "resolved_symbol": "000001.SS",
    }
    fields = {
        "symbol": "000001.SS",
        "module": "A",
        "direction": "long",
        "ruleset_version": "2.1.0",
        "reason": "用户原话待细化",
        "valid_until": "2099-12-31",
        "stop_plan_cn": "跌破失效位复核",
        "take_profit_plan_cn": "到达目标区复核",
    }
    card = bridge.save_plan_draft(fields, source, "plan.00001")
    repeated = bridge.save_plan_draft(fields, source, "plan.00001")
    assert card["plan"]["plan_id"] == repeated["plan"]["plan_id"]
    assert card["plan"]["state"] == "draft"
    assert card["conformance"]["can_confirm"] is False
    with pytest.raises(WorkflowError):
        bridge.confirm_plan(
            card["plan"]["plan_id"],
            {
                "confirmed": True,
                "plan_id": card["plan"]["plan_id"],
                "request_id": "plan.00001",
                "fingerprint": card["fingerprint"],
            },
            card["fingerprint"],
            "plan.00001",
        )
    assert client.get(f"/api/plans/{card['plan']['plan_id']}").json()["state"] == "draft"
    with pytest.raises(WorkflowError, match="409"):
        bridge.save_plan_draft(dict(fields, reason="changed"), source, "plan.00001")
    with pytest.raises(WorkflowError):
        bridge.save_plan_draft(dict(fields, symbol="510300.SH"), source, "plan.00002")


def test_actual_discussion_enrolls_source_then_idempotent_draft(flow):
    bridge, client, path = flow
    message = "请整理 512890.SS 的止损和止盈预案；条件还没有定好。"
    source = bridge.discuss_plan(message, "512890.SS", "discussion.0001")
    replay = bridge.discuss_plan(message, "512890.SS", "discussion.0001")
    assert source["question_id"] == replay["question_id"]
    assert source["session_id"] == replay["session_id"]
    fields = {
        "symbol": "512890.SS",
        "module": "A",
        "direction": "long",
        "ruleset_version": "2.1.0",
        "valid_until": "2099-12-31",
        "reason": "止盈与止损条件待用户补齐",
        "stop_plan_cn": "止损条件待补",
        "take_profit_plan_cn": "止盈条件待补",
    }
    first = bridge.save_plan_draft(fields, source, "draft.0001")
    second = bridge.save_plan_draft(fields, source, "draft.0001")
    assert first["source_question_id"] == source["question_id"]
    assert first["plan"]["plan_id"] == second["plan"]["plan_id"]
    assert first["plan"]["state"] == "draft"
    with connect(path) as conn:
        row = conn.execute(
            "SELECT question_id,session_id,plan_id FROM agent_plan_draft_bindings "
            "WHERE client_request_id=?",
            ("draft.0001",),
        ).fetchone()
        assert dict(row) == {
            "question_id": source["question_id"],
            "session_id": source["session_id"],
            "plan_id": first["plan"]["plan_id"],
        }
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM agent_messages WHERE message_id=?", (source["question_id"],)
            ).fetchone()[0]
            == 1
        )
    assert client.get(f"/api/plans/{first['plan']['plan_id']}").json()["state"] == "draft"


def test_entered_same_product_link_reads_workspace_and_rejects_mismatch(flow):
    from lei_signal.integrations.chat_transactions import fingerprint

    bridge, client, path = flow
    with connect(path) as conn:
        upsert_group(conn, PortfolioGroup("cn", "A股", "cn", 1, "观察"))
        upsert_holding(
            conn,
            PortfolioHolding(
                "holding-etf",
                "cn",
                "红利低波ETF华泰柏瑞",
                "512890",
                1200.0,
                None,
                as_of="2026-10-08",
            ),
        )
        conn.execute(
            "INSERT INTO watchlist_items (symbol,display_name,market,note,sort_order,added_at) "
            "VALUES (?,?,?,?,?,?)",
            ("512890.SS", "红利低波ETF", "cn", None, 1, "2026-10-01"),
        )
        plan = create_plan(
            conn,
            symbol="512890.SS",
            module="A",
            direction="long",
            ruleset_version="1.3.0",
            reason="已持有，只盯退出",
            valid_until="2099-12-31",
            take_profit_plan_cn="到目标区复核",
            stop_plan_cn="跌破失效位复核",
        )
        wrong = create_plan(
            conn,
            symbol="QQQ",
            module="A",
            direction="long",
            ruleset_version="1.3.0",
            reason="另一产品",
            valid_until="2099-12-31",
            take_profit_plan_cn="到目标区复核",
            stop_plan_cn="跌破失效位复核",
        )
        conn.execute(
            "UPDATE trade_plans SET state='entered' WHERE plan_id IN (?,?)",
            (plan.plan_id, wrong.plan_id),
        )
        conn.commit()
    shown = {"holding_id": "holding-etf", "plan_id": plan.plan_id}
    confirmation = {"confirmed": True, "fingerprint": fingerprint(shown)}
    first = bridge.link_holding("holding-etf", plan.plan_id, confirmation)
    second = bridge.link_holding("holding-etf", plan.plan_id, confirmation)
    assert first["plan"]["plan_id"] == second["plan"]["plan_id"] == plan.plan_id
    workspace = client.get("/api/portfolio/workspace").json()
    assert (
        next(x for x in workspace["items"] if x["holding_id"] == "holding-etf")["plan"]["plan_id"]
        == plan.plan_id
    )
    with connect(path) as conn:
        assert (
            conn.execute("SELECT COUNT(*) FROM portfolio_holding_plan_link_history").fetchone()[0]
            == 1
        )
    bad_shown = {"holding_id": "holding-etf", "plan_id": wrong.plan_id}
    with pytest.raises(WorkflowError, match="422"):
        bridge.link_holding(
            "holding-etf", wrong.plan_id, {"confirmed": True, "fingerprint": fingerprint(bad_shown)}
        )
    with connect(path) as conn:
        assert (
            conn.execute("SELECT COUNT(*) FROM portfolio_holding_plan_link_history").fetchone()[0]
            == 1
        )


def test_reconcile_is_read_only_and_marks_opening_basis_pending(flow):
    bridge, client, path = flow
    with connect(path) as conn:
        upsert_group(conn, PortfolioGroup("cn", "A股", "cn", 1, "观察"))
        upsert_holding(
            conn,
            PortfolioHolding(
                "holding-1", "cn", "测试基金", "515880", 12345.0, None, as_of="2026-10-08"
            ),
        )
        conn.commit()
    before = client.get("/api/copilot/trades").json()["trades"]
    preview = bridge.reconcile_holdings()
    after = client.get("/api/copilot/trades").json()["trades"]
    assert before == after == []
    assert preview["ledger_trade_count"] == 0
    assert len(preview["rows"]) == 1
    assert preview["rows"][0]["status"] == "needs_opening_basis"
    assert preview["rows"][0]["snapshot_value"] == 12345.0


def test_relative_date_product_name_and_bound_request(flow):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    bridge, client, _ = flow
    card = bridge.preview_trade("今天我买了515880 500元", request_id="relative-trade-01")
    assert card["status"] == "confirmable", card
    assert card["fund_name"] == "国泰中证全指通信设备ETF"
    assert card["trade_date"] == datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    with pytest.raises(WorkflowError, match="请求编号"):
        bridge.record_trade(
            card,
            {
                "confirmed": True,
                "request_id": "other-request-01",
                "fingerprint": card["fingerprint"],
            },
        )
    assert client.get("/api/copilot/trades").json()["trades"] == []


@pytest.mark.parametrize(
    "message",
    [
        "今天买了515880和512890共500元",
        "今天我买了515880，价格1.2元，支付500元",
        "今天买了515880 500份",
        "今天买了123456 500元",
        "2099-01-01买了515880 500元",
    ],
)
def test_product_amount_and_future_ambiguities_stay_pending(flow, message):
    bridge, client, _ = flow
    assert bridge.preview_trade(message)["status"] == "pending"
    assert client.get("/api/copilot/trades").json()["trades"] == []


def test_exact_product_name_can_resolve_without_user_typing_code(flow):
    bridge, _, _ = flow
    card = bridge.preview_trade(
        "今天我买了国泰中证全指通信设备ETF 500元", request_id="name-resolved-01"
    )
    assert card["status"] == "confirmable", card
    assert card["fund_code"] == "515880" and card["amount"] == 500
    assert card["original_message"] == "今天我买了国泰中证全指通信设备ETF 500元"
