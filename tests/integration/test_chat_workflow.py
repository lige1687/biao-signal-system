"""Several complete records in isolated SQLite, with the actual domain stores."""

from dataclasses import asdict

import pytest

from lei_signal.copilot.trades import create_trade
from lei_signal.domain.rules_config import ruleset_version
from lei_signal.integrations.chat_transactions import WorkflowError
from lei_signal.integrations.chat_workflow import ConfirmedWorkflow, prepare_card
from lei_signal.plans import store
from lei_signal.plans.monitor import MonitorContext, evaluate_plan
from lei_signal.portfolio.models import PortfolioGroup, PortfolioHolding
from lei_signal.portfolio.store import list_holdings, upsert_group, upsert_holding
from lei_signal.storage.sqlite_store import connect


@pytest.fixture
def env(tmp_path):
    path = str(tmp_path / "local-workflow.db")
    conn = connect(path)
    upsert_group(conn, PortfolioGroup("cn", "国内基金", "cn", 1, "观察"))
    upsert_holding(
        conn, PortfolioHolding("h1", "cn", "测试通信ETF", "515880", 1000, 0, as_of="2026-09-30")
    )
    conn.execute(
        "INSERT INTO portfolio_holdings_nav VALUES(?,?,?,?,?,?,?,?,?)",
        ("h1", "515880", 1, "2026-09-30", 1000, 1000, 1.2, "2026-10-08", "2026-10-08"),
    )
    conn.commit()
    ctx = MonitorContext("2026-09-30", False, 1.0, 1.0, True, ruleset_version=ruleset_version())
    flow = ConfirmedWorkflow(path, context_loader=lambda symbol: ctx)
    yield flow, conn, ctx
    conn.close()


def apply(flow, kind, fields, rid):
    card = prepare_card(
        kind,
        fields,
        rid,
        original_message="隔离演练的明确确认",
        conversation_ref="isolated-test-only",
    )
    result = flow.confirm(
        card, {"confirmed": True, "request_id": rid, "fingerprint": card["fingerprint"]}
    )
    return card, result


def test_holding_watch_saved_confirmed_and_actual_stop_triggered(env):
    flow, conn, ctx = env
    fields = {
        "symbol": "515880.SS",
        "ruleset_version": ruleset_version(),
        "valid_until": "2099-12-31",
        "take_profit_plan_cn": "到1.5复核止盈",
        "stop_plan_cn": "低于0.9复核退出",
        "stop_price": 0.9,
        "take_profit_price": 1.5,
    }
    card, out = apply(flow, "holding_watch", fields, "watch-test-01")
    assert out["status"] == "draft"
    repeated = flow.confirm(
        card,
        {"confirmed": True, "request_id": card["request_id"], "fingerprint": card["fingerprint"]},
    )
    assert repeated == out
    pid = out["plan"]["plan_id"]
    read = flow.read_plan(pid)
    _, active = apply(
        flow,
        "activate_plan",
        {"plan_id": pid, "plan_fingerprint": read["fingerprint"]},
        "activate-watch-01",
    )
    assert active["status"] == "entered"
    from dataclasses import replace

    alerts = evaluate_plan(store.get_plan(conn, pid), replace(ctx, current_close=0.85))
    assert any(a.code == "STOP_PRICE_BREACHED" for a in alerts)
    assert (
        conn.execute("SELECT count(*) FROM trade_plan_versions WHERE plan_id=?", (pid,)).fetchone()[
            0
        ]
        == 1
    )


def test_existing_entry_plan_confirmation_uses_real_conformance(env):
    flow, conn, _ = env
    plan = store.create_plan(
        conn,
        symbol="515880.SS",
        module="A",
        direction="long",
        ruleset_version=ruleset_version(),
        valid_until="2099-12-31",
        reason="已明确的演练条件",
        entry_price_ref=1,
        invalidation_price=0.9,
        target_b_price=1.5,
        thesis_cn="观察上涨条件",
        invalidation_criteria_cn="失效价被破坏",
        drawdown_playbook_cn="未破条件仅复核",
        take_profit_plan_cn="目标处复核",
        stop_plan_cn="失效处复核",
    )
    _, result = apply(
        flow,
        "activate_plan",
        {"plan_id": plan.plan_id, "plan_fingerprint": flow.read_plan(plan.plan_id)["fingerprint"]},
        "activate-entry-01",
    )
    assert result["status"] == "armed"


def test_buy_sell_fill_and_confirmed_reconciliation_exactly_once(env):
    flow, conn, _ = env
    apply(
        flow,
        "holding_basis",
        {
            "holding_id": "h1",
            "code": "515880",
            "shares": 1000,
            "cost": 1000,
            "basis_date": "2026-09-30",
            "included_trade_ids": [],
            "evidence_ref": "隔离起始份额确认",
        },
        "basis-test-01",
    )
    buy = create_trade(
        conn,
        fund_code="515880",
        fund_name="测试通信ETF",
        side="buy",
        amount=500,
        trade_date="2026-10-08",
        request_id="buy-test-01",
    )
    sell = create_trade(
        conn,
        fund_code="515880",
        fund_name="测试通信ETF",
        side="sell",
        amount=120,
        trade_date="2026-10-08",
        request_id="sell-test-01",
    )
    conn.commit()
    before = asdict(list_holdings(conn)[0])
    assert flow.reconciliation("h1", 1.2, "2026-10-08")["status"] == "pending"
    assert asdict(list_holdings(conn)[0]) == before
    for trade, shares, rid in ((buy, 500, "fill-buy-01"), (sell, 100, "fill-sell-01")):
        apply(
            flow,
            "broker_fill",
            {
                "trade_id": trade.trade_id,
                "code": "515880",
                "shares": shares,
                "fee": 0,
                "fill_date": "2026-10-08",
                "evidence_ref": "隔离平台回执",
            },
            rid,
        )
    proposal = flow.reconciliation("h1", 1.2, "2026-10-08")
    assert proposal["status"] == "ready"
    assert proposal["shares"] == 1400 and proposal["cost"] == 1400
    card, result = apply(
        flow,
        "reconcile",
        {
            "holding_id": "h1",
            "nav": 1.2,
            "nav_date": "2026-10-08",
            "proposal_fingerprint": proposal["fingerprint"],
        },
        "reconcile-test-01",
    )
    assert result["holding"]["market_value"] == 1680
    assert result["holding"]["return_pct"] == 20
    assert result["holding"]["as_of"] == "2026-10-08"
    assert tuple(
        conn.execute(
            "SELECT implied_shares,cost_value FROM portfolio_holdings_nav WHERE holding_id='h1'"
        ).fetchone()
    ) == (1400, 1400)
    assert (
        flow.confirm(
            card,
            {
                "confirmed": True,
                "request_id": card["request_id"],
                "fingerprint": card["fingerprint"],
            },
        )
        == result
    )
    assert conn.execute("SELECT count(*) FROM fund_trades").fetchone()[0] == 2


def test_missing_confirmation_changed_card_and_changed_plan_refused(env):
    flow, conn, _ = env
    card = prepare_card(
        "holding_basis",
        {"holding_id": "h1"},
        "wrong-test-01",
        original_message="测试",
        conversation_ref="test",
    )
    with pytest.raises(WorkflowError):
        flow.confirm(card, {"confirmed": False})
    card["fields"]["cost"] = 1
    with pytest.raises(WorkflowError):
        flow.confirm(
            card,
            {
                "confirmed": True,
                "request_id": card["request_id"],
                "fingerprint": card["fingerprint"],
            },
        )
    assert conn.execute("SELECT count(*) FROM trade_plans").fetchone()[0] == 0


def test_wrong_product_and_excess_redemption_are_not_reconciled(env):
    flow, conn, _ = env
    with pytest.raises(WorkflowError):
        apply(
            flow,
            "holding_basis",
            {
                "holding_id": "h1",
                "code": "013403",
                "shares": 1,
                "cost": 1,
                "basis_date": "2026-09-30",
                "included_trade_ids": [],
                "evidence_ref": "测试",
            },
            "wrong-basis-01",
        )
    apply(
        flow,
        "holding_basis",
        {
            "holding_id": "h1",
            "code": "515880",
            "shares": 1,
            "cost": 1,
            "basis_date": "2026-09-30",
            "included_trade_ids": [],
            "evidence_ref": "测试",
        },
        "tiny-basis-01",
    )
    trade = create_trade(
        conn,
        fund_code="515880",
        fund_name="测试通信ETF",
        side="sell",
        amount=10,
        trade_date="2026-10-08",
        request_id="oversell-test-01",
    )
    conn.commit()
    apply(
        flow,
        "broker_fill",
        {
            "trade_id": trade.trade_id,
            "code": "515880",
            "shares": 10,
            "fee": 0,
            "fill_date": "2026-10-08",
            "evidence_ref": "测试",
        },
        "oversell-fill-01",
    )
    with pytest.raises(WorkflowError, match="超过"):
        flow.reconciliation("h1", 1.2, "2026-10-08")


def test_missing_fee_cash_changed_proposal_and_next_nav_refresh(env, monkeypatch):
    flow, conn, _ = env
    apply(
        flow,
        "holding_basis",
        {
            "holding_id": "h1",
            "code": "515880",
            "shares": 1000,
            "cost": 1000,
            "basis_date": "2026-09-30",
            "included_trade_ids": [],
            "evidence_ref": "隔离演练",
        },
        "fee-basis-01",
    )
    t = create_trade(
        conn,
        fund_code="515880",
        fund_name="测试通信ETF",
        side="buy",
        amount=500,
        trade_date="2026-10-08",
        request_id="fee-buy-01",
    )
    conn.commit()
    apply(
        flow,
        "broker_fill",
        {
            "trade_id": t.trade_id,
            "code": "515880",
            "shares": 495,
            "fee": 5,
            "fill_date": "2026-10-08",
            "evidence_ref": "隔离演练",
        },
        "fee-fill-01",
    )
    proposal = flow.reconciliation("h1", 1.2, "2026-10-08")
    assert proposal["status"] == "pending" and proposal["shares"] == 1000
    with pytest.raises(WorkflowError, match="资料不齐"):
        apply(
            flow,
            "reconcile",
            {
                "holding_id": "h1",
                "nav": 1.2,
                "nav_date": "2026-10-08",
                "proposal_fingerprint": proposal["fingerprint"],
            },
            "fee-reconcile-01",
        )
    assert list_holdings(conn)[0].market_value == 1000


def test_real_share_reconciliation_survives_normal_nav_update(env, monkeypatch):
    flow, conn, _ = env
    apply(
        flow,
        "holding_basis",
        {
            "holding_id": "h1",
            "code": "515880",
            "shares": 800,
            "cost": 900,
            "basis_date": "2026-09-30",
            "included_trade_ids": [],
            "evidence_ref": "平台实际份额",
        },
        "refresh-basis-01",
    )
    proposal = flow.reconciliation("h1", 1.2, "2026-10-08")
    fields = {
        "holding_id": "h1",
        "nav": 1.2,
        "nav_date": "2026-10-08",
        "proposal_fingerprint": proposal["fingerprint"],
    }
    conn.execute("UPDATE portfolio_holdings SET market_value=999 WHERE holding_id='h1'")
    conn.commit()
    with pytest.raises(WorkflowError, match="已变化"):
        apply(flow, "reconcile", fields, "refresh-refused-01")
    fields["proposal_fingerprint"] = flow.reconciliation("h1", 1.2, "2026-10-08")["fingerprint"]
    apply(flow, "reconcile", fields, "refresh-accepted-01")
    from lei_signal.portfolio import nav_update
    from lei_signal.portfolio.funddata import NavPoint

    monkeypatch.setattr(
        nav_update, "fetch_nav_history", lambda *a, **k: [NavPoint("2026-10-08", 1.3)]
    )
    nav_update.update_nav(conn)
    assert list_holdings(conn)[0].market_value == 1040
    assert conn.execute("SELECT cost_value FROM portfolio_holdings_nav").fetchone()[0] == 900


def test_new_holding_uses_actual_shares_cost_and_verified_same_product_nav(env):
    flow, conn, _ = env
    from lei_signal.portfolio.funddata import NavPoint

    flow.nav_loader = lambda code: [NavPoint("2026-10-08", 1.2)]
    fields = {
        "name": "隔离红利基金",
        "code": "512890",
        "group_key": "cn",
        "shares": 300,
        "cost": 320,
        "nav": 1.2,
        "basis_date": "2026-10-08",
        "included_trade_ids": [],
        "evidence_ref": "隔离平台记录",
    }
    _, result = apply(flow, "new_holding", fields, "new-holding-01")
    assert result["holding"]["market_value"] == 360
    hid = result["holding"]["holding_id"]
    assert flow.reconciliation(hid, 1.2, "2026-10-08")["cost"] == 320
    with pytest.raises(WorkflowError, match="已在持仓"):
        apply(flow, "new_holding", fields, "new-holding-02")
    with pytest.raises(WorkflowError, match="未来日期"):
        apply(
            flow,
            "holding_basis",
            {
                "holding_id": "h1",
                "code": "515880",
                "shares": 1,
                "cost": 1,
                "basis_date": "2099-01-01",
                "included_trade_ids": [],
                "evidence_ref": "测试",
            },
            "future-basis-01",
        )
