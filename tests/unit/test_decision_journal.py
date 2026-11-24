"""Decision review uses isolated SQLite and a fake agent, never market access."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import agent, decisions
from lei_signal.api.schemas import AgentChatReply
from lei_signal.copilot import decision_journal as journal
from lei_signal.storage.sqlite_store import connect


@pytest.fixture()
def env(tmp_path, monkeypatch):
    path = str(tmp_path / "decisions.sqlite")
    connect(path).close()
    app = FastAPI()
    app.state.plans_db_path = path
    app.include_router(decisions.router)
    today = date.today().isoformat()
    workspace = {
        "items": [
            {
                "holding_id": "h1",
                "name": "甲基金",
                "code": "510300",
                "holding_as_of": today,
                "status": "incomplete",
                "gaps": ["未关联计划"],
                "nav": {"value": 1.2, "date": today},
                "plan": None,
                "technical": None,
            }
        ],
        "as_of": today,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    monkeypatch.setattr(
        "lei_signal.api.portfolio_workspace.build_workspace", lambda request: workspace
    )
    calls = []
    mode = {"grounded": True, "date": today}

    def fake_agent_chat(request, body):
        calls.append(body)
        with connect(path) as conn:
            claim = conn.execute(
                "SELECT * FROM agent_chat_requests WHERE client_request_id=?",
                (body.client_request_id,),
            ).fetchone()
            if claim:
                qid = claim["question_id"]
                answer_id = claim["answer_message_id"]
                answer = conn.execute(
                    "SELECT content FROM agent_messages WHERE message_id=?", (answer_id,)
                ).fetchone()["content"]
                session_id = claim["session_id"]
            else:
                session_id = "sess_test"
                conn.execute(
                    "INSERT OR IGNORE INTO agent_sessions VALUES (?,?,?,?,?)",
                    (session_id, "portfolio:h1", "测试", today, today),
                )
                material = {
                    "portfolio_holding_id": "h1",
                    "items": [workspace["items"][0]],
                    "holding_as_of": mode["date"],
                }
                snap = {
                    "discussion_v1": {
                        "context_kind": "portfolio",
                        "portfolio_holding_id": "h1",
                        "portfolio": material,
                    }
                }
                cur = conn.execute(
                    "INSERT INTO agent_messages("
                    "session_id,role,content,grounded,meta_json,created_at) "
                    "VALUES (?,?,?,?,?,?)",
                    (session_id, "user", body.message, 1, json.dumps(snap), today),
                )
                qid = cur.lastrowid
                answer = "支持：有基金净值；反对：缺少已确认计划；未知：当前卖出条件。"
                card = {
                    "portfolio": {
                        "portfolio_holding_id": "h1",
                        "items": [workspace["items"][0]],
                        "holding_as_of": mode["date"],
                    }
                }
                cur = conn.execute(
                    "INSERT INTO agent_messages("
                    "session_id,role,content,grounded,meta_json,created_at,question_id) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (
                        session_id,
                        "assistant",
                        answer,
                        int(mode["grounded"]),
                        json.dumps({"evidence_card": card}),
                        today,
                        qid,
                    ),
                )
                answer_id = cur.lastrowid
                conn.execute(
                    "INSERT INTO agent_chat_requests("
                    "client_request_id,session_id,question_id,request_hash,created_at,"
                    "answer_message_id,answer_state,state_at) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        body.client_request_id,
                        session_id,
                        qid,
                        "test",
                        today,
                        answer_id,
                        "answered",
                        today,
                    ),
                )
                conn.commit()
        card = {
            "portfolio": {
                "portfolio_holding_id": "h1",
                "items": [workspace["items"][0]],
                "holding_as_of": mode["date"],
            }
        }
        return AgentChatReply(
            session_id=session_id,
            reply=answer,
            grounded=mode["grounded"],
            question_id=qid,
            answer_state="answered",
            evidence_card=card,
        )

    monkeypatch.setattr(agent, "agent_chat", fake_agent_chat)
    with TestClient(app) as client:
        yield client, path, workspace, calls, mode


def _review(client, cid="r1", decision_id=None, thought="我想卖出甲基金"):
    return client.post(
        "/api/decisions/reviews",
        json={
            "subject_key": "holding:h1",
            "intent": "sell",
            "thought": thought,
            "watch_for": "净值跌破原计划失效位",
            "client_request_id": cid,
            "decision_id": decision_id,
        },
    )


def _confirm(client, review, cid="c1", choice="observe"):
    return client.post(
        "/api/decisions/confirm",
        json={
            "review_id": review["review_id"],
            "fingerprint": review["fingerprint"],
            "choice": choice,
            "decision_note": "先观察",
            "client_request_id": cid,
            "confirmed": True,
        },
    )


def _opportunity_fixture(env, monkeypatch):
    from lei_signal.copilot import opportunity_review as opportunities

    client, path, workspace, calls, mode = env
    card = {
        "candidate_key": "holding:h1:sell",
        "subject": {
            "key": "holding:h1",
            "kind": "holding",
            "id": "h1",
            "name": "甲基金",
            "code": "510300",
        },
        "intent": "sell",
        "status": "unknown",
        "headline": "原计划未知，先核对事实",
        "agent_eligible": False,
        "data_as_of": mode["date"],
        "evidence": [
            {
                "id": "e1",
                "role": "unknown",
                "text": "原退出条件尚未记录",
                "source": "同产品计划检查",
                "source_ref": "/portfolio",
                "date": None,
                "object_name": "甲基金",
                "scope": "same_product",
                "provenance": "coverage_gap",
            }
        ],
        "searches": [],
        "limitations": [],
    }
    snapshot = {
        "as_of": mode["date"],
        "checked_at": "2026-10-15T00:00:00+08:00",
        "coverage": {"holdings": 1},
        "limitations": [],
        "items": [card],
    }
    monkeypatch.setattr("lei_signal.api.opportunity_evidence.build_snapshot", lambda _: snapshot)
    with connect(path) as conn:
        board, _ = opportunities.ensure_board(conn, snapshot)
    rid = board["items"][0]["review_id"]
    body = {
        "subject_key": "holding:h1",
        "intent": "sell",
        "thought": "  我的真实原话  ",
        "watch_for": "",
        "client_request_id": "from-opportunity",
        "opportunity_review_id": rid,
    }
    return card, body, rid


def test_opportunity_adoption_preserves_reference_and_exact_user_thought(env, monkeypatch):
    client, path, workspace, calls, _ = env
    card, body, rid = _opportunity_fixture(env, monkeypatch)
    result = client.post("/api/decisions/reviews", json=body)
    assert result.status_code == 200
    review = result.json()
    assert review["thought"] == "  我的真实原话  "
    assert review["opportunity_reference"]["review_id"] == rid
    assert review["opportunity_reference"]["card"]["headline"] == card["headline"]
    assert "不代表我的个人观点" in calls[-1].message
    assert "原退出条件尚未记录" in calls[-1].message
    assert client.get("/api/decisions").json()["items"] == []
    saved = _confirm(client, review).json()
    card["headline"] = "后来的资料已变"
    followup = {**body, "client_request_id": "followup-origin", "decision_id": saved["decision_id"]}
    follow = client.post("/api/decisions/reviews", json=followup)
    assert follow.status_code == 200
    assert follow.json()["opportunity_reference"] == review["opportunity_reference"]


@pytest.mark.parametrize("change", ["direction", "source", "tamper"])
def test_opportunity_adoption_rejects_mismatch_before_agent(env, monkeypatch, change):
    client, path, _, calls, _ = env
    card, body, rid = _opportunity_fixture(env, monkeypatch)
    if change == "direction":
        body["intent"] = "buy"
    elif change == "source":
        card["evidence"][0]["text"] = "资料内容已变化"
    else:
        with connect(path) as conn:
            conn.execute(
                "UPDATE opportunity_review_cards SET card_json=? WHERE review_id=?",
                (json.dumps({**card, "headline": "被改写"}), rid),
            )
            conn.commit()
    response = client.post("/api/decisions/reviews", json=body)
    assert response.status_code == 409
    assert calls == []


def test_confirm_replay_history_and_no_plan_trade_write(env):
    client, path, workspace, calls, mode = env
    first = _review(client)
    assert first.status_code == 200, first.text
    review = first.json()
    assert review["can_confirm"] is True
    assert review["thought"] == "我想卖出甲基金"
    assert review["answer"]["question_id"] > 0
    assert [f["key"] for f in review["facts"]] == ["holding_status", "holding_code", "nav"]
    assert _review(client).json() == review
    assert len(calls) == 1
    assert _review(client, thought="我要买入").status_code == 409
    saved = _confirm(client, review)
    assert saved.status_code == 200, saved.text
    root = saved.json()
    did = root["decision_id"]
    assert root["thought"] == "我想卖出甲基金"
    assert root["history"][0]["review"]["review_id"] == review["review_id"]
    assert _confirm(client, review).json()["decision_id"] == did
    assert _confirm(client, review, cid="receipt-lost").json()["decision_id"] == did
    assert _confirm(client, review, cid="different-choice", choice="pass").status_code == 409
    assert _confirm(client, review, cid="c1", choice="pass").status_code == 409
    workspace["items"][0]["nav"] = {
        "value": 1.3,
        "date": (date.today() + timedelta(days=1)).isoformat(),
    }
    # A future-dated observation cannot be called a current change.
    follow = _review(client, cid="r2", decision_id=did)
    assert follow.status_code == 200, follow.text
    assert follow.json()["changes"] == []
    assert _confirm(client, follow.json(), cid="c2").status_code == 200
    detail = client.get(f"/api/decisions/{did}").json()
    assert len(detail["history"]) == 2
    assert detail["thought"] == "我想卖出甲基金"
    assert detail["watch_for"] == "净值跌破原计划失效位"
    assert detail["current_check"]["status"] == "unknown"
    assert len(client.get("/api/decisions").json()["items"]) == 1
    with connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM trade_plans").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM fund_trades").fetchone()[0] == 0


def test_reject_wrong_subject_fingerprint_and_fallback(env):
    client, _, _, calls, mode = env
    mode["grounded"] = False
    failed = _review(client)
    assert failed.status_code == 200
    assert failed.json()["can_confirm"] is False
    assert _confirm(client, failed.json()).status_code == 409
    mode["grounded"] = True
    assert _review(client).json() == failed.json()  # Original failure remains auditable.
    recovered = _review(client, cid="new-review-after-failure").json()
    assert recovered["can_confirm"] is True
    assert len(calls) == 2
    other = client.post(
        "/api/decisions/reviews",
        json={
            "subject_key": "holding:wrong",
            "intent": "buy",
            "thought": "考虑买",
            "client_request_id": "bad",
        },
    )
    assert other.status_code == 422


def test_tampered_answer_and_disappeared_holding(env):
    client, path, workspace, _, _ = env
    review = _review(client).json()
    with connect(path) as conn:
        conn.execute("UPDATE agent_messages SET question_id=999 WHERE role='assistant'")
        conn.commit()
    assert _confirm(client, review).status_code == 409
    with connect(path) as conn:
        conn.execute(
            "UPDATE agent_messages SET question_id=? WHERE role='assistant'",
            (review["answer"]["question_id"],),
        )
        conn.commit()
    did = _confirm(client, review).json()["decision_id"]
    workspace["items"].clear()
    follow = _review(client, cid="gone", decision_id=did).json()
    assert follow["can_confirm"] is False
    assert "当前资料未知" in " ".join(follow["limitations"])
    assert client.get(f"/api/decisions/{did}").json()["thought"] == review["thought"]


def test_later_comparable_nav_is_a_dated_change(env):
    client, _, workspace, calls, mode = env
    prior = (date.today() - timedelta(days=1)).isoformat()
    workspace["items"][0]["nav"]["date"] = prior
    workspace["items"][0]["holding_as_of"] = prior
    mode["date"] = prior
    initial = _review(client).json()
    did = _confirm(client, initial).json()["decision_id"]
    workspace["items"][0]["nav"] = {"value": 1.3, "date": date.today().isoformat()}
    workspace["items"][0]["holding_as_of"] = date.today().isoformat()
    follow = _review(client, cid="later", decision_id=did).json()
    assert "卖出想法" in calls[-1].message
    assert "上一次用户确认的选择" in calls[-1].message
    assert "上次保存的材料" in calls[-1].message
    assert follow["changes"] == [
        {
            "label": "基金净值",
            "before": "1.2",
            "after": "1.3",
            "note": f"同一资料口径：{prior} → {date.today().isoformat()}；仅说明记录变化",
        }
    ]
    saved = _confirm(client, follow, cid="later-confirm").json()
    assert saved["current_check"]["status"] == "unknown"  # POST does no current fetch.
    assert saved["history"][-1]["review"]["changes"] == follow["changes"]


def test_current_check_reads_workspace_without_writing_history(env):
    client, path, workspace, _, mode = env
    prior = (date.today() - timedelta(days=1)).isoformat()
    workspace["items"][0]["nav"]["date"] = prior
    workspace["items"][0]["holding_as_of"] = prior
    mode["date"] = prior
    review = _review(client).json()
    did = _confirm(client, review).json()["decision_id"]
    workspace["items"][0].update(
        status="no_trigger",
        gaps=[],
        nav={"value": 1.3, "date": date.today().isoformat()},
        holding_as_of=date.today().isoformat(),
    )
    before = client.get(f"/api/decisions/{did}").json()
    assert before["current_check"]["status"] == "changed"
    assert [x["label"] for x in before["current_check"]["changes"]] == ["基金净值"]
    assert len(before["history"]) == 1
    workspace["items"][0]["status"] = "waiting"
    waiting = client.get(f"/api/decisions/{did}").json()["current_check"]
    assert waiting["status"] == "changed"  # Dated NAV remains comparable.
    assert "计划变化未知" in waiting["note"]
    workspace["items"].clear()
    assert client.get(f"/api/decisions/{did}").json()["current_check"]["status"] == "unknown"
    with connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM decision_confirmations").fetchone()[0] == 1


def test_same_dated_conflicting_cache_is_unknown(env):
    client, _, workspace, _, _ = env
    review = _review(client).json()
    did = _confirm(client, review).json()["decision_id"]
    same = client.get(f"/api/decisions/{did}").json()["current_check"]
    assert same["status"] == "unchanged"
    assert "同日同值只说明已读缓存一致" in same["note"]
    workspace["items"][0].update(
        status="no_trigger", gaps=[], nav={"value": 1.3, "date": date.today().isoformat()}
    )
    current = client.get(f"/api/decisions/{did}").json()["current_check"]
    assert current["status"] == "unknown"
    assert current["changes"] == []


def test_old_holding_date_new_nav_with_stale_technical(env):
    client, _, workspace, _, mode = env
    old_holding_day = (date.today() - timedelta(days=90)).isoformat()
    prior_nav_day = (date.today() - timedelta(days=2)).isoformat()
    workspace["items"][0]["holding_as_of"] = old_holding_day
    workspace["items"][0]["nav"] = {"value": 1.2, "date": prior_nav_day}
    mode["date"] = old_holding_day
    review = _review(client).json()
    did = _confirm(client, review).json()["decision_id"]
    workspace["items"][0]["nav"] = {"value": 1.3, "date": date.today().isoformat()}
    workspace["items"][0]["technical"] = {
        "assessment": {"as_of": prior_nav_day, "stage_cn": "旧阶段"},
        "meta": {
            "last_bar_date": prior_nav_day,
            "data_time": prior_nav_day + "T10:00:00+08:00",
            "cache_fallback_used": True,
            "is_intraday_forming": True,
        },
    }
    current = client.get(f"/api/decisions/{did}").json()["current_check"]
    assert current["status"] == "changed"
    assert [x["label"] for x in current["changes"]] == ["基金净值"]
    assert "技术变化未知" in current["note"]
    assert "计划变化未知" in current["note"]


def test_followup_cannot_change_intent_or_original_condition(env):
    client, _, _, calls, _ = env
    review = _review(client).json()
    did = _confirm(client, review).json()["decision_id"]
    body = {
        "subject_key": "holding:h1",
        "intent": "buy",
        "thought": review["thought"],
        "watch_for": review["watch_for"],
        "client_request_id": "wrong-intent",
        "decision_id": did,
    }
    assert client.post("/api/decisions/reviews", json=body).status_code == 409
    body.update(intent="sell", watch_for="另一条条件", client_request_id="wrong-condition")
    assert client.post("/api/decisions/reviews", json=body).status_code == 409
    assert len(calls) == 1


def test_pending_same_request_does_not_generate_second_answer(env):
    client, path, _, calls, _ = env
    payload = {
        "subject_key": "holding:h1",
        "intent": "sell",
        "thought": "我想卖出甲基金",
        "watch_for": "净值跌破原计划失效位",
        "client_request_id": "r1",
        "decision_id": None,
    }
    with connect(path) as conn:
        journal.ensure_schema(conn)
        assert journal.claim_review(conn, "r1", journal.digest(payload))
    assert _review(client).status_code == 409
    assert calls == []


def test_facts_match_server_symbol_and_holding_card_shapes():
    day = date.today().isoformat()
    symbol = {"key": "symbol:000300.SS", "kind": "symbol", "id": "000300.SS", "name": "沪深300"}
    card = {
        "facts": {
            "symbol": "000300.SS",
            "display_name": "沪深300",
            "as_of": day,
            "verdict_cn": "等待条件成立",
            "buy_point_candidate_n": 2,
        },
        "history_and_scope": {},
        "pending_conditions": [],
    }
    facts, gaps = decisions._facts(card, symbol)
    assert gaps == []
    assert [(f["key"], f["date"]) for f in facts] == [
        ("technical_verdict", day),
        ("buy_candidates", day),
    ]
    holding = {"key": "holding:h1", "kind": "holding", "id": "h1", "name": "甲基金"}
    material = {
        "portfolio_holding_id": "h1",
        "holding_as_of": day,
        "items": [
            {
                "holding_id": "h1",
                "code": "510300",
                "status": "no_trigger",
                "holding_as_of": day,
                "gaps": [],
                "nav": {"value": 1.23, "date": day},
                "plan": {"plan_id": "p1"},
                "technical": {
                    "assessment": {
                        "as_of": day,
                        "stage_cn": "发展阶段",
                        "risk_state_cn": "待观察",
                        "color_cn": "绿色",
                    },
                    "meta": {
                        "last_bar_date": day,
                        "cache_fallback_used": False,
                        "is_intraday_forming": False,
                    },
                },
            }
        ],
    }
    facts, gaps = decisions._facts({"portfolio": material}, holding)
    assert gaps == []
    assert {f["key"] for f in facts} == {
        "holding_status",
        "holding_code",
        "plan_id",
        "nav",
        "technical_stage",
        "technical_risk",
        "technical_color",
    }


def test_symbol_current_check_only_uses_analysis_cache(monkeypatch):
    day = date.today()
    old = (day - timedelta(days=1)).isoformat()
    subject = {"key": "symbol:000300.SS", "kind": "symbol", "id": "000300.SS", "name": "沪深300"}
    past, _ = decisions._facts(
        {
            "facts": {
                "symbol": subject["id"],
                "as_of": old,
                "verdict_cn": "等待条件成立",
                "buy_point_candidate_n": 1,
            }
        },
        subject,
    )
    result = SimpleNamespace(assessment=SimpleNamespace(as_of=day), cache_fallback_used=False)
    entry = SimpleNamespace(result=result, fetched_at=datetime.now(UTC))
    service = SimpleNamespace(
        _entries={subject["id"]: entry}, get=lambda *_a, **_k: pytest.fail("不得读取行情服务")
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(analysis_service=service)))
    monkeypatch.setattr(
        "lei_signal.api.portfolio_workspace._expected_bar_date", lambda symbol, now: day.isoformat()
    )
    monkeypatch.setattr(
        "lei_signal.api.portfolio_workspace._forming", lambda result, symbol, entry, now: False
    )
    monkeypatch.setattr(
        "lei_signal.api.routes.opportunities.build_review",
        lambda result, symbol, display_name: SimpleNamespace(
            as_of=day.isoformat(), verdict_cn="条件已成立", candidates=[1, 2]
        ),
    )
    check = decisions._cache_check(request, {"subject": subject, "latest_review": {"facts": past}})
    assert check["status"] == "changed"
    assert {c["label"] for c in check["changes"]} == {"买点审阅", "候选买点数"}
    entry.fetched_at = datetime.now(UTC) - timedelta(days=1)
    assert (
        decisions._cache_check(request, {"subject": subject, "latest_review": {"facts": past}})[
            "status"
        ]
        == "unknown"
    )


def test_subjects_exclude_sector_proxies(env, monkeypatch):
    from types import SimpleNamespace

    client, path, *_ = env
    client.app.state.watchlist_db_path = path
    monkeypatch.setattr(
        decisions,
        "list_watchlist",
        lambda conn: [
            SimpleNamespace(symbol="TH881121.SECTOR", display_name="半导体行业"),
            SimpleNamespace(symbol="BK001.SECTOR", display_name="旧行业代理"),
            SimpleNamespace(symbol="IGV", display_name="北美软件ETF"),
        ],
    )
    items = client.get("/api/decisions/subjects").json()["items"]
    assert all(not item["id"].endswith(".SECTOR") for item in items)
    assert any(item["key"] == "symbol:IGV" for item in items)
    assert any(item["key"] == "holding:h1" for item in items)


def test_prompt_includes_server_clock_without_changing_original(env):
    client, _, _, calls, _ = env
    reply = _review(client, thought="  合成原话\n").json()
    assert reply["thought"] == "  合成原话\n"
    assert "本次审核时间：" in calls[-1].message
    assert "提问时间与资料日期分别核对" in calls[-1].message
    assert "不新增材料没有支持的价格条件" in calls[-1].message


def test_normal_review_wrapper_does_not_route_to_factor_only(env):
    from lei_signal.copilot.factor_product_context import is_product_factor_question
    from lei_signal.copilot.factor_readonly import is_factor_question

    client, _, _, calls, _ = env
    _review(client)
    assert not is_product_factor_question(calls[-1].message)
    assert not is_factor_question(calls[-1].message)


def test_changed_fund_code_rejects_followup_before_model(env):
    client, _, workspace, calls, _ = env
    first = _review(client).json()
    saved = _confirm(client, first).json()
    count = len(calls)
    workspace["items"][0]["code"] = "512480"
    review = _review(client, cid="different-product", decision_id=saved["decision_id"]).json()
    assert not review["can_confirm"]
    assert len(calls) == count
    assert any("基金代码" in note for note in review["limitations"])


def test_changed_saved_evidence_rejects_confirmation(env):
    client, path, *_ = env
    review = _review(client).json()
    with connect(path) as conn:
        conn.execute("UPDATE agent_messages SET meta_json='{}' WHERE role='assistant'")
        conn.commit()
    response = _confirm(client, review)
    assert response.status_code == 409
    assert "依据已变化" in response.json()["detail"]


def test_resume_after_answer_saved_keeps_exact_original_prompt(env, monkeypatch):
    client, path, _, calls, _ = env
    save = journal.save_review

    def interrupted(*args, **kwargs):
        raise RuntimeError("synthetic interruption after answer")

    monkeypatch.setattr(journal, "save_review", interrupted)
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        _review(client)
    original_prompt = calls[-1].message
    with connect(path) as conn:
        conn.execute("UPDATE agent_chat_requests SET request_message=?", (original_prompt,))
        conn.execute(
            "UPDATE decision_review_claims SET updated_at=?",
            ((datetime.now(UTC) - timedelta(minutes=11)).isoformat(),),
        )
        conn.commit()
    monkeypatch.setattr(journal, "save_review", save)
    resumed = _review(client)
    assert resumed.status_code == 200
    assert resumed.json()["can_confirm"]
    assert calls[-1].message == original_prompt
