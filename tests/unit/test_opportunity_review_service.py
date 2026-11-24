"""Isolated persistence and source-grounding checks for automatic reviews."""

from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.copilot import opportunity_review as review


def _card(*, opposite: bool = True, text: str = "原规则支持观察") -> dict:
    evidence = [
        {"id": "s1", "role": "support", "text": text, "source": "原规则", "date": "2026-10-14"},
        {"id": "u1", "role": "unknown", "text": "成交时点未核实", "source": "系统", "date": None},
    ]
    if opposite:
        evidence.append(
            {
                "id": "o1",
                "role": "opposition",
                "text": "已有风险路牌",
                "source": "原规则",
                "date": "2026-10-14",
            }
        )
    return {
        "candidate_key": "symbol:510300:buy",
        "subject": {"key": "symbol:510300", "kind": "symbol", "id": "510300", "name": "沪深300ETF"},
        "intent": "buy",
        "status": "candidate",
        "headline": "存在观察机会",
        "agent_eligible": True,
        "data_as_of": "2026-10-14",
        "evidence": evidence,
        "searches": [{"name": "技术冲突", "status": "checked", "detail": "已核"}],
        "limitations": [],
    }


def _snapshot(card: dict, checked: str = "2026-10-15T00:00:00+08:00") -> dict:
    return {
        "as_of": "2026-10-15",
        "checked_at": checked,
        "coverage": {"review_candidates": 1},
        "limitations": [],
        "items": [card],
    }


def _second_card() -> dict:
    card = _card()
    card["candidate_key"] = "symbol:159915:buy"
    card["subject"] = {
        "key": "symbol:159915",
        "kind": "symbol",
        "id": "159915",
        "name": "创业板ETF",
    }
    for item in card["evidence"]:
        item["id"] = item["id"][0] + "2"
    return card


def _same_product_sell_card() -> dict:
    card = _second_card()
    card["subject"] = dict(_card()["subject"])
    card["candidate_key"] = "symbol:510300:sell"
    card["intent"] = "sell"
    return card


def _model(ids: list[str], _: str) -> str:
    return json.dumps(
        {
            "reviews": [
                {
                    "review_id": rid,
                    "support_ids": ["s1"],
                    "opposition_ids": ["o1"],
                    "unknown_ids": ["u1"],
                    "condition_ids": [],
                    "lead_ids": [],
                }
                for rid in ids
            ]
        }
    )


def test_same_input_reuses_card_and_model_once(tmp_path):
    path = tmp_path / "review.sqlite"
    calls = []
    with sqlite3.connect(path) as conn:
        board, work = review.ensure_board(conn, _snapshot(_card()))
        assert work and board["status"] == "pending"

    def fake(ids, prompt):
        calls.append((ids, prompt))
        return _model(ids, prompt)

    review.process_run(str(path), board["run_id"], model=fake)
    with sqlite3.connect(path) as conn:
        replay, work = review.ensure_board(conn, _snapshot(_card(), "2026-10-15T00:01:00+08:00"))
        assert replay["run_id"] == board["run_id"]
        assert replay["reused"] is True
        assert replay["checked_at"] == "2026-10-15T00:00:00+08:00"
        assert replay["status"] == "complete"
        assert not work
        assert replay["items"][0]["audit"]["opposition_ids"] == ["o1"]
        assert not conn.execute(
            "SELECT name FROM sqlite_master WHERE name='decision_records'"
        ).fetchone()
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("status", "lease_until", "expected_work"),
    [
        ("pending", None, True),
        ("running", "2000-01-01T00:00:00+00:00", True),
        ("failed", None, False),
    ],
)
def test_same_run_ensure_reads_through_other_connection_write_lock(
    tmp_path, status, lease_until, expected_work
):
    path = tmp_path / "review.sqlite"
    original = _snapshot(_card())
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, original)
        conn.execute(
            "UPDATE opportunity_review_cards SET status=?,lease_until=?,failure_code=?",
            (status, lease_until, "existing_failure" if status == "failed" else ""),
        )
        conn.commit()
    with sqlite3.connect(path, timeout=0) as holder, sqlite3.connect(path, timeout=0) as reader:
        holder.execute("BEGIN IMMEDIATE")
        replay, work = review.ensure_board(
            reader, _snapshot(_card(), "2026-10-15T00:01:00+08:00")
        )
        assert replay["run_id"] == board["run_id"]
        assert replay["reused"] is True
        assert replay["checked_at"] == original["checked_at"]
        assert replay["items"][0]["audit"]["status"] == (
            "failed" if status == "running" else status
        )
        assert work is expected_work
        holder.rollback()
    with sqlite3.connect(path) as conn:
        assert conn.execute(
            "SELECT status,failure_code FROM opportunity_review_cards"
        ).fetchone() == (status, "existing_failure" if status == "failed" else "")
        assert conn.execute(
            "SELECT checked_at FROM opportunity_review_runs"
        ).fetchone()[0] == original["checked_at"]


def test_evidence_change_creates_immutable_new_card(tmp_path):
    with sqlite3.connect(tmp_path / "review.sqlite") as conn:
        first, _ = review.ensure_board(conn, _snapshot(_card()))
        second, _ = review.ensure_board(conn, _snapshot(_card(text="新的原始依据")))
        assert first["items"][0]["review_id"] != second["items"][0]["review_id"]
        assert (
            review.get_card(conn, first["items"][0]["review_id"])["card"]["evidence"][0]["text"]
            == "已有风险路牌"
        )


def test_wrong_role_or_omitted_opposition_fails_only_that_card(tmp_path):
    path = tmp_path / "review.sqlite"
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, _snapshot(_card()))

    def bad(ids, prompt):
        answer = json.loads(_model(ids, prompt))
        answer["reviews"][0]["opposition_ids"] = ["s1"]
        return json.dumps(answer)

    review.process_run(str(path), board["run_id"], model=bad)
    with sqlite3.connect(path) as conn:
        failed = review.get_run(conn, board["run_id"])
        assert failed["status"] == "partial"
        assert failed["items"][0]["audit"]["status"] == "failed"
        assert review.ensure_board(conn, _snapshot(_card()))[1] is False
        row = conn.execute(
            "SELECT raw_attempt,failure_code FROM opportunity_review_cards"
        ).fetchone()
        assert '"s1"' in row[0] and "unsupported_source_id" in row[1]


def test_explicit_retry_and_no_opposition_requires_unknown(tmp_path):
    path = tmp_path / "review.sqlite"
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, _snapshot(_card(opposite=False)))

    def no_unknown(ids, prompt):
        answer = json.loads(_model(ids, prompt))
        answer["reviews"][0]["opposition_ids"] = []
        answer["reviews"][0]["unknown_ids"] = []
        return json.dumps(answer)

    review.process_run(str(path), board["run_id"], model=no_unknown)
    with sqlite3.connect(path) as conn:
        assert review.ensure_board(conn, _snapshot(_card(opposite=False)))[1] is False
        retried, work = review.ensure_board(
            conn, _snapshot(_card(opposite=False)), retry_failed=True
        )
        assert work and retried["items"][0]["audit"]["status"] == "pending"


def test_concurrent_claim_single_owner_and_lease_recovery(tmp_path):
    path = tmp_path / "review.sqlite"
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, _snapshot(_card()))
    rid = board["items"][0]["review_id"]
    with sqlite3.connect(path) as a, sqlite3.connect(path) as b:
        assert review._claim(a, rid) is not None
        assert review._claim(b, rid) is None
        a.execute(
            "UPDATE opportunity_review_cards SET lease_until='2000-01-01T00:00:00+00:00' "
            "WHERE review_id=?",
            (rid,),
        )
        a.commit()
        assert review._claim(b, rid) is not None


def test_same_run_has_one_worker(tmp_path):
    path = tmp_path / "review.sqlite"
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, _snapshot(_card()))
    with sqlite3.connect(path) as a, sqlite3.connect(path) as b:
        assert review._claim_worker(a, board["run_id"])
        assert review._claim_worker(b, board["run_id"]) is None


def test_two_cards_one_model_call_and_per_card_validation(tmp_path):
    path = tmp_path / "review.sqlite"
    snapshot = _snapshot(_card())
    snapshot["items"].append(_same_product_sell_card())
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snapshot)
    calls = []

    def grouped(ids, prompt):
        calls.append(ids)
        assert len(json.loads(prompt)["reviews"]) == 2
        return json.dumps(
            {
                "reviews": [
                    {
                        "review_id": ids[0],
                        "support_ids": ["s1"],
                        "opposition_ids": ["o1"],
                        "unknown_ids": ["u1"],
                        "condition_ids": [],
                        "lead_ids": [],
                    },
                    {
                        "review_id": ids[1],
                        "support_ids": ["s2"],
                        "opposition_ids": ["o1"],
                        "unknown_ids": ["u2"],
                        "condition_ids": [],
                        "lead_ids": [],
                    },
                ]
            }
        )

    review.process_run(str(path), board["run_id"], model=grouped)
    with sqlite3.connect(path) as conn:
        done = review.get_run(conn, board["run_id"])
        assert [x["audit"]["status"] for x in done["items"]] == ["complete", "failed"]
        assert conn.execute("SELECT count(*) FROM opportunity_review_attempts").fetchone()[0] == 2
    assert len(calls) == 1


def test_cross_run_same_card_does_not_duplicate_model_call(tmp_path):
    path = tmp_path / "review.sqlite"
    with sqlite3.connect(path) as conn:
        first, _ = review.ensure_board(conn, _snapshot(_card()))
        snap = _snapshot(_card())
        snap["limitations"] = ["另一批次"]
        second, _ = review.ensure_board(conn, snap)
    calls = []

    def nested(ids, prompt):
        calls.append(ids)
        review.process_run(str(path), second["run_id"], model=lambda ids, prompt: calls.append(ids))
        return _model(ids, prompt)

    review.process_run(str(path), first["run_id"], model=nested)
    assert len(calls) == 1


def test_missing_or_duplicate_group_ids_fail_affected_card(tmp_path):
    path = tmp_path / "review.sqlite"
    snapshot = _snapshot(_card())
    snapshot["items"].append(_same_product_sell_card())
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snapshot)

    def partial(ids, prompt):
        answer = json.loads(_model([ids[0]], prompt))
        return json.dumps(answer)

    review.process_run(str(path), board["run_id"], model=partial)
    with sqlite3.connect(path) as conn:
        done = review.get_run(conn, board["run_id"])
        assert [x["audit"]["status"] for x in done["items"]] == ["complete", "failed"]
        assert (
            "missing_review_id"
            in conn.execute(
                "SELECT failure_code FROM opportunity_review_cards WHERE review_id=?",
                (done["items"][1]["review_id"],),
            ).fetchone()[0]
        )


def test_product_batches_never_mix_ids_and_retry_only_failed_product(tmp_path, monkeypatch):
    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "product-batches.sqlite"
    first_buy = _with_public_context()
    first_sell = json.loads(json.dumps(first_buy))
    first_sell["intent"] = "sell"
    first_sell["candidate_key"] = first_buy["subject"]["key"] + ":sell"
    second_buy = json.loads(json.dumps(first_buy))
    second_buy["subject"].update(key="symbol:159915", id="159915", name="创业板ETF")
    second_buy["candidate_key"] = "symbol:159915:buy"
    second_sell = json.loads(json.dumps(second_buy))
    second_sell["intent"] = "sell"
    second_sell["candidate_key"] = "symbol:159915:sell"
    snap = _snapshot(first_buy)
    snap["items"].extend([second_buy, first_sell, second_sell])
    calls = []
    fail_second_once = {"value": True}

    def call(prompt, **kwargs):
        rows = json.loads(prompt)["reviews"]
        subjects = {row["subject"]["product_id"] for row in rows}
        assert len(subjects) == 1 and len(rows) <= 2
        product = next(iter(subjects))
        stage = "counter" if "intent" in rows[0] else "context"
        calls.append((stage, product, [row["review_id"] for row in rows]))
        response = _production_reply(prompt, **kwargs)
        if stage == "counter" and product.endswith(":159915") and fail_second_once["value"]:
            fail_second_once["value"] = False
            payload = json.loads(response["text"])
            for row in payload["reviews"]:
                point = row["analysis"]["points"][0]
                row["analysis"]["points"] = [point, point, point]
            response["text"] = json.dumps(payload)
        return response

    monkeypatch.setattr(opportunity_transport, "call_model", call)
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snap)
    review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        result = review.get_run(conn, board["run_id"])
        assert [item["audit"]["status"] for item in result["items"]].count("complete") == 2
        assert [item["audit"]["status"] for item in result["items"]].count("failed") == 2
        assert review.ensure_board(conn, snap, retry_failed=True)[1]
    review.process_run(str(path), board["run_id"], retry_failed=True)
    with sqlite3.connect(path) as conn:
        assert review.get_run(conn, board["run_id"])["status"] == "complete"
    assert sum(stage == "context" for stage, _, _ in calls) == 2
    assert sum(stage == "counter" for stage, _, _ in calls) == 3
    assert all(len(ids) == (1 if stage == "context" else 2) for stage, _, ids in calls)
    assert sum(product.endswith(":510300") for _, product, _ in calls) == 2
    assert "本输入这一卡" in review._retry_feedback(
        "unsupported_analysis_source", agent="counter"
    )
    feedback = review._retry_feedback("invalid_batch_json:private details", agent="counter")
    assert "{reviews:[{review_id,analysis}]}" in feedback
    assert "private details" not in feedback


def test_get_before_schema_is_missing(tmp_path):
    with sqlite3.connect(tmp_path / "empty.sqlite") as conn:
        assert review.get_card(conn, "ocr_missing") is None
        assert review.get_run(conn, "orb_missing") is None


def test_api_get_before_schema_returns_404(tmp_path):
    from lei_signal.api.routes import opportunity_reviews as route

    app = FastAPI()
    app.state.plans_db_path = str(tmp_path / "empty.sqlite")
    app.include_router(route.router)
    with TestClient(app) as client:
        assert client.get("/api/opportunity-reviews/runs/orb_missing").status_code == 404
        assert client.get("/api/opportunity-reviews/cards/ocr_missing").status_code == 404


def test_model_cannot_omit_present_support_condition_or_unknown():
    card = _card()
    card["evidence"].append({"id": "c1", "role": "condition", "text": "待收盘", "source": "系统"})
    rid = "ocr_test"
    claimed = {rid: (card, "token")}
    base = json.loads(_model([rid], ""))
    base["reviews"][0]["condition_ids"] = ["c1"]
    for field in ("support_ids", "condition_ids", "unknown_ids"):
        bad = json.loads(json.dumps(base))
        bad["reviews"][0][field] = []
        result = review._batch_results(json.dumps(bad), claimed)
        assert result[rid][1] == "failed"


def test_normalization_rejects_duplicate_ids_and_excludes_check_time():
    card = _card()
    assert review.normalized_card(card)["review_version"] == "context-counter/3"
    first = review.input_fingerprint(card)
    card["checked_at"] = "2026-10-15T00:00:00+08:00"
    assert review.input_fingerprint(card) == first
    card["evidence"].append(dict(card["evidence"][0]))
    try:
        review.normalized_card(card)
    except ValueError as exc:
        assert "重复" in str(exc)
    else:
        raise AssertionError("duplicate ID was accepted")


def test_missing_opposition_is_explicit_unknown():
    card = _card(opposite=False)
    card["evidence"] = [e for e in card["evidence"] if e["role"] != "unknown"]
    normalized = review.normalized_card(card)
    assert any(e["role"] == "unknown" and "反面" in e["text"] for e in normalized["evidence"])
    assert any(e["id"] == "s1" for e in normalized["evidence"])


def test_api_ensure_poll_card_without_financial_writes(tmp_path, monkeypatch):
    from lei_signal.api import opportunity_evidence
    from lei_signal.api.routes import opportunity_reviews as route

    path = tmp_path / "review.sqlite"
    app = FastAPI()
    app.state.plans_db_path = str(path)
    app.include_router(route.router)
    monkeypatch.setattr(opportunity_evidence, "build_snapshot", lambda request: _snapshot(_card()))
    original = review.process_run
    monkeypatch.setattr(
        review, "process_run", lambda db_path, run_id: original(db_path, run_id, model=_model)
    )
    with TestClient(app) as client:
        first = client.post("/api/opportunity-reviews/ensure").json()
        again = client.post("/api/opportunity-reviews/ensure").json()
        assert again["reused"] is True
        assert first["run_id"] == again["run_id"]
        poll = client.get("/api/opportunity-reviews/runs/" + first["run_id"]).json()
        assert poll["status"] == "complete"
        card = client.get("/api/opportunity-reviews/cards/" + first["items"][0]["review_id"]).json()
        assert card["audit"]["opposition_ids"] == ["o1"]
    with sqlite3.connect(path) as conn:
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        for name in ("decision_records", "trade_plans"):
            if name in tables:
                assert conn.execute(f"SELECT count(*) FROM {name}").fetchone()[0] == 0


def test_automatic_model_excludes_private_context(tmp_path):
    card = _card()
    card["evidence"].append(
        {
            "id": "private",
            "role": "context",
            "text": "PRIVATE_HOLDING_NOTE_AND_PLAN",
            "source": "原持仓备注",
        }
    )
    path = tmp_path / "private.sqlite"
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, _snapshot(card))

    def model(ids, prompt):
        assert "PRIVATE_HOLDING_NOTE_AND_PLAN" not in prompt
        return _model(ids, prompt)

    review.process_run(str(path), board["run_id"], model=model)
    with sqlite3.connect(path) as conn:
        result = review.get_run(conn, board["run_id"])
    assert result["status"] == "complete"
    assert any(e["id"] == "private" for e in result["items"][0]["card"]["evidence"])


def test_expired_worker_displays_failure_and_can_resume(tmp_path):
    path = tmp_path / "expired.sqlite"
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, _snapshot(_card()))
        rid = board["items"][0]["review_id"]
        review._claim(conn, rid)
        conn.execute("UPDATE opportunity_review_cards SET lease_until='2000-01-01T00:00:00+00:00'")
        conn.commit()
        result = review.get_run(conn, board["run_id"])
        assert result["status"] == "partial"
        assert result["items"][0]["audit"]["status"] == "failed"
        _, work = review.ensure_board(conn, _snapshot(_card()), retry_failed=True)
        assert work
    calls = []

    def model(ids, prompt):
        calls.append(ids)
        return _model(ids, prompt)

    review.process_run(str(path), board["run_id"], model=model)
    with sqlite3.connect(path) as conn:
        recovered = review.get_run(conn, board["run_id"])
        assert recovered["items"][0]["audit"]["failure_code"] == "storage_interrupted"
        assert recovered["items"][0]["audit"]["status"] == "failed"
    assert calls == []
    review.process_run(str(path), board["run_id"], model=model, retry_failed=True)
    with sqlite3.connect(path) as conn:
        assert review.get_run(conn, board["run_id"])["status"] == "complete"
    assert calls == [[rid]]


def test_explicit_retry_resumes_orphan_recovered_in_same_process_run(tmp_path):
    path = tmp_path / "orphan-retry.sqlite"
    snap = _snapshot(_card())
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snap)
        rid = board["items"][0]["review_id"]
        review._claim(conn, rid)
        conn.execute(
            "UPDATE opportunity_review_cards SET lease_until='2000-01-01T00:00:00+00:00' "
            "WHERE review_id=?",
            (rid,),
        )
        conn.commit()
        assert review.ensure_board(conn, snap, retry_failed=True)[1]
    calls = []

    def model(ids, prompt):
        calls.append(ids)
        return _model(ids, prompt)

    review.process_run(str(path), board["run_id"], model=model, retry_failed=True)
    with sqlite3.connect(path) as conn:
        item = review.get_run(conn, board["run_id"])["items"][0]
        assert item["audit"]["status"] == "complete"
        attempts = conn.execute(
            "SELECT status,failure_code FROM opportunity_review_attempts WHERE review_id=? "
            "ORDER BY attempt_id",
            (rid,),
        ).fetchall()
        assert [tuple(row) for row in attempts] == [
            ("failed", "storage_interrupted"),
            ("complete", ""),
        ]
    assert calls == [[rid]]


def test_orphaned_running_context_is_marked_interrupted_without_model_call(tmp_path):
    path = tmp_path / "orphaned-context.sqlite"
    snap = _snapshot(_with_public_context())
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snap)
        rid = board["items"][0]["review_id"]
        card = review._claim(conn, rid)[0]
        conn.execute(
            "INSERT INTO opportunity_context_reviews(context_key,status,result_json,lease_until) "
            "VALUES(?,'running','{}','2099-01-01T00:00:00+00:00')",
            (review._context_key(card),),
        )
        conn.commit()
    calls = []
    review.process_run(str(path), board["run_id"], model=lambda ids, prompt: calls.append(ids))
    assert calls == []
    with sqlite3.connect(path) as conn:
        item = review.get_run(conn, board["run_id"])["items"][0]
        assert item["audit"]["failure_code"] == "storage_interrupted"
        assert item["audit"]["agents"]["context"]["failure_code"] == "storage_interrupted"
        assert tuple(
            conn.execute(
                "SELECT lease_token,lease_until FROM opportunity_review_cards WHERE review_id=?",
                (rid,),
            ).fetchone()
        ) == (None, None)
        assert tuple(
            conn.execute(
                "SELECT status,lease_until FROM opportunity_context_reviews WHERE context_key=?",
                (review._context_key(card),),
            ).fetchone()
        ) == ("failed", None)
        assert review.ensure_board(conn, snap, retry_failed=True)[1]


def test_orphan_recovery_waits_while_another_run_worker_is_live(tmp_path):
    path = tmp_path / "active-other-worker.sqlite"
    snap = _snapshot(_with_public_context())
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snap)
        rid = board["items"][0]["review_id"]
        card = review._claim(conn, rid)[0]
        conn.execute(
            "INSERT INTO opportunity_context_reviews(context_key,status,result_json,lease_until) "
            "VALUES(?,'running','{}','2099-01-01T00:00:00+00:00')",
            (review._context_key(card),),
        )
        conn.execute(
            "INSERT INTO opportunity_review_workers(run_id,token,lease_until) "
            "VALUES('another-run','other-token','2099-01-01T00:00:00+00:00')"
        )
        conn.commit()
    review.process_run(
        str(path),
        board["run_id"],
        model=lambda ids, prompt: pytest.fail("unexpected model"),
        retry_failed=True,
    )
    with sqlite3.connect(path) as conn:
        assert conn.execute(
            "SELECT status FROM opportunity_review_cards WHERE review_id=?", (rid,)
        ).fetchone()[0] == "running"
        assert conn.execute(
            "SELECT status FROM opportunity_context_reviews WHERE context_key=?",
            (review._context_key(card),),
        ).fetchone()[0] == "running"
        assert conn.execute(
            "SELECT token FROM opportunity_review_workers WHERE run_id='another-run'"
        ).fetchone()[0] == "other-token"


def test_recovery_failure_releases_new_run_worker(tmp_path, monkeypatch):
    path = tmp_path / "recovery-failure.sqlite"
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, _snapshot(_card()))
    monkeypatch.setattr(
        review,
        "_recover_orphaned_run",
        lambda *args: (_ for _ in ()).throw(sqlite3.OperationalError("database is locked")),
    )
    with pytest.raises(sqlite3.OperationalError, match="database is locked"):
        review.process_run(str(path), board["run_id"], model=_model)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM opportunity_review_workers").fetchone()[0] == 0


def test_receipt_busy_retry_does_not_repeat_model_call(tmp_path, monkeypatch):
    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "busy-once.sqlite"
    original_receipt = review._agent_receipt
    calls = []

    class BusyOnce:
        def __init__(self, conn):
            self.conn = conn
            self.busy = True

        def execute(self, sql, params=()):
            if sql == "BEGIN IMMEDIATE" and self.busy:
                self.busy = False
                raise sqlite3.OperationalError("database is locked")
            return self.conn.execute(sql, params)

        def commit(self):
            return self.conn.commit()

        def rollback(self):
            return self.conn.rollback()

    monkeypatch.setattr(
        review,
        "_agent_receipt",
        lambda conn, agent, key, result: original_receipt(BusyOnce(conn), agent, key, result),
    )

    def call(prompt, **kwargs):
        calls.append("counter" if "intent" in json.loads(prompt)["reviews"][0] else "context")
        return _production_reply(prompt, **kwargs)

    monkeypatch.setattr(opportunity_transport, "call_model", call)
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, _snapshot(_with_public_context()))
    review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        assert review.get_run(conn, board["run_id"])["status"] == "complete"
        assert conn.execute("SELECT COUNT(*) FROM opportunity_agent_attempts").fetchone()[0] == 2
    assert calls == ["context", "counter"]


def test_receipt_failure_marks_owned_card_failed_and_releases_lease(tmp_path, monkeypatch):
    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "receipt-failure.sqlite"
    calls = []
    monkeypatch.setattr(
        review,
        "_agent_receipt",
        lambda *args: (_ for _ in ()).throw(sqlite3.OperationalError("database is locked")),
    )

    def call(prompt, **kwargs):
        calls.append("model")
        return _production_reply(prompt, **kwargs)

    monkeypatch.setattr(opportunity_transport, "call_model", call)
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, _snapshot(_with_public_context()))
    with pytest.raises(sqlite3.OperationalError, match="database is locked"):
        review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        item = review.get_run(conn, board["run_id"])["items"][0]
        assert item["audit"]["failure_code"] == "storage_locked"
        assert item["audit"]["agents"]["context"]["failure_code"] == "storage_locked"
        assert conn.execute("SELECT COUNT(*) FROM opportunity_review_workers").fetchone()[0] == 0
        assert tuple(
            conn.execute("SELECT lease_token,lease_until FROM opportunity_review_cards").fetchone()
        ) == (None, None)
    assert calls == ["model"]


def test_abandoned_pending_run_does_not_poll_forever(tmp_path):
    with sqlite3.connect(tmp_path / "abandoned.sqlite") as conn:
        board, _ = review.ensure_board(conn, _snapshot(_card(), "2000-01-01T00:00:00+00:00"))
        result = review.get_run(conn, board["run_id"])
        assert result["status"] == "partial"
        assert all(
            stage["status"] not in {"running", "pending"}
            for item in result["items"]
            for stage in item["audit"]["agents"].values()
        )
        _, work = review.ensure_board(conn, _snapshot(_card()), retry_failed=True)
        assert work


def _with_public_context():
    card = _card()
    card["evidence"].extend(
        [
            {
                "id": "f1",
                "role": "context",
                "category": "fundamentals",
                "public": True,
                "text": "报告期为2026-06-30，披露部分股票，当前构成未知",
                "date": "2026-06-30",
                "source": "公开报告",
                "source_ref": "https://issuer.example/report",
                "provenance": "disclosed",
            },
            {
                "id": "private1",
                "role": "context",
                "category": "fundamentals",
                "public": False,
                "text": "PRIVATE_ACCOUNT_NOTE",
                "source": "原持仓备注",
                "date": None,
            },
        ]
    )
    return card


def _production_reply(prompt, *, system_prompt, config=None):
    data = json.loads(prompt)
    values = []
    for row in data["reviews"]:
        ids = [e["id"] for e in row["evidence"]]
        analysis = {
            "summary": "只读已给证据",
            "points": [
                {"text": "报告仍有时点或覆盖缺口", "evidence_ids": [ids[0]], "stance": "unknown"}
            ],
            "gaps": ["需要核对当前资料"],
        }
        if "intent" in row:
            answer = {"review_id": row["review_id"]}
            for key, role in review._FIELDS.items():
                answer[key] = [e["id"] for e in row["evidence"] if e["role"] == role][:1]
            answer["analysis"] = analysis
        else:
            answer = {"review_id": row["review_id"], **analysis}
        values.append(answer)
    return {
        "text": json.dumps({"reviews": values}),
        "error_code": "",
        "model": "isolated-test",
        "attempts": 1,
        "usage": {},
        "finish_reason": "end_turn",
        "elapsed_ms": 1,
    }


def test_production_two_roles_receive_public_context_and_reuse_both_directions(
    tmp_path, monkeypatch
):
    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "two-roles.sqlite"
    calls = []
    card = _with_public_context()
    sell = json.loads(json.dumps(card))
    sell["intent"] = "sell"
    sell["candidate_key"] = card["subject"]["key"] + ":sell"
    snap = _snapshot(card)
    snap["items"].append(sell)

    def call(prompt, **kwargs):
        assert "PRIVATE_ACCOUNT_NOTE" not in prompt
        assert "private1" not in prompt
        calls.append(json.loads(prompt))
        return _production_reply(prompt, **kwargs)

    monkeypatch.setattr(opportunity_transport, "call_model", call)
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snap)
    review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        result = review.get_run(conn, board["run_id"])
        assert result["status"] == "complete"
        assert all(x["audit"]["agents"]["context"]["status"] == "complete" for x in result["items"])
        assert all(x["audit"]["agents"]["counter"]["status"] == "complete" for x in result["items"])
        assert conn.execute("SELECT count(*) FROM opportunity_context_reviews").fetchone()[0] == 1
        assert review.ensure_board(conn, snap)[1] is False
    assert len(calls) == 2
    assert len(calls[0]["reviews"]) == 1
    assert all(r["context_analysis"]["status"] == "complete" for r in calls[1]["reviews"])
    for row in calls[1]["reviews"]:
        assert row["allowed_selection_ids"] == {
            "support_ids": ["s1"],
            "opposition_ids": ["o1"],
            "unknown_ids": ["u1"],
            "condition_ids": [],
            "lead_ids": [],
        }


def test_complete_json_fence_accepted_by_context_and_counter(tmp_path, monkeypatch):
    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "fenced-model.sqlite"
    calls = []

    def call(prompt, **kwargs):
        response = _production_reply(prompt, **kwargs)
        response["text"] = "```json\n" + response["text"] + "\n```"
        calls.append("counter" if "intent" in json.loads(prompt)["reviews"][0] else "context")
        return response

    monkeypatch.setattr(opportunity_transport, "call_model", call)
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, _snapshot(_with_public_context()))
    review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        result = review.get_run(conn, board["run_id"])
        assert result["status"] == "complete"
        assert result["items"][0]["audit"]["agents"]["context"]["status"] == "complete"
        assert result["items"][0]["audit"]["agents"]["counter"]["status"] == "complete"
    assert calls == ["context", "counter"]


def test_json_fence_rejects_outside_text_and_multiple_blocks():
    content = '{"reviews":[]}'
    valid = "```json\n" + content + "\n```"
    for raw in ("Explanation\n" + valid, valid + "\nExplanation", valid + "\n" + valid):
        with pytest.raises(ValueError):
            review._parse_model_json(raw)


def test_fenced_reply_cannot_use_news_or_context_as_unknown_or_condition():
    card = _with_public_context()
    card["evidence"].append(
        {"id": "n1", "role": "lead", "public": True, "text": "未核实标题", "source": "新闻搜索"}
    )
    allowed = review._material("ocr_test", card)["allowed_selection_ids"]
    assert allowed == {
        "support_ids": ["s1"],
        "opposition_ids": ["o1"],
        "unknown_ids": ["u1"],
        "condition_ids": [],
        "lead_ids": ["n1"],
    }
    claimed = {"ocr_test": (card, "token")}
    answer = json.loads(_model(["ocr_test"], ""))
    answer["reviews"][0]["lead_ids"] = ["n1"]
    for field, wrong_id in (("unknown_ids", "n1"), ("condition_ids", "f1")):
        wrong = json.loads(json.dumps(answer))
        wrong["reviews"][0][field] = [wrong_id]
        raw = "```json\n" + json.dumps(wrong) + "\n```"
        result = review._batch_results(raw, claimed)
        assert result["ocr_test"][1:] == ("failed", "unsupported_source_id")


def test_analysis_only_reply_uses_server_selected_original_roles():
    card = _with_public_context()
    card["evidence"].extend(
        {"id": f"s{n}", "role": "support", "text": "原规则", "source": "系统"}
        for n in range(2, 6)
    )
    card["evidence"].append(
        {"id": "n1", "role": "lead", "public": True, "text": "未核实标题", "source": "新闻搜索"}
    )
    rid = "ocr_test"
    analysis = {
        "summary": "资料中有尚未核实的时点",
        "points": [{"text": "成交时点未核实", "evidence_ids": ["u1"], "stance": "unknown"}],
        "gaps": [],
    }
    compact = {"reviews": [{"review_id": rid, "analysis": analysis}]}
    selected, status, failure = review._batch_results(
        json.dumps(compact), {rid: (card, "token")}, require_analysis=True
    )[rid]
    assert (status, failure) == ("complete", "")
    assert selected["support_ids"] == ["s1", "s2", "s3"]
    assert selected["opposition_ids"] == ["o1"]
    assert selected["unknown_ids"] == ["u1"]
    assert selected["condition_ids"] == []
    assert selected["lead_ids"] == ["n1"]
    assert selected["analysis"]["status"] == "complete"

    legacy_wrong = {"review_id": rid, **{field: selected[field] for field in review._FIELDS}}
    legacy_wrong["unknown_ids"] = ["n1"]
    legacy_wrong["analysis"] = analysis
    result = review._batch_results(
        json.dumps({"reviews": [legacy_wrong]}), {rid: (card, "token")}, require_analysis=True
    )
    assert result[rid][1:] == ("failed", "unsupported_source_id")


def test_production_accepts_analysis_only_counter_reply(tmp_path, monkeypatch):
    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "analysis-only.sqlite"

    def call(prompt, **kwargs):
        response = _production_reply(prompt, **kwargs)
        if "intent" in json.loads(prompt)["reviews"][0]:
            for row in json.loads(prompt)["reviews"]:
                assert row["allowed_selection_ids"]["condition_ids"] == []
            payload = json.loads(response["text"])
            response["text"] = json.dumps(
                {
                    "reviews": [
                        {"review_id": row["review_id"], "analysis": row["analysis"]}
                        for row in payload["reviews"]
                    ]
                }
            )
        return response

    monkeypatch.setattr(opportunity_transport, "call_model", call)
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, _snapshot(_with_public_context()))
    review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        item = review.get_run(conn, board["run_id"])["items"][0]
        assert item["audit"]["status"] == "complete"
        assert item["audit"]["unknown_ids"] == ["u1"]
        assert item["audit"]["condition_ids"] == []


def test_context_provider_failure_skips_counter_and_retry_recovers(tmp_path, monkeypatch):
    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "stage-failure.sqlite"
    calls = []
    fail = {"context": True}

    def call(prompt, **kwargs):
        stage = "counter" if "intent" in json.loads(prompt)["reviews"][0] else "context"
        calls.append(stage)
        if stage == "context" and fail["context"]:
            return {"text": None, "error_code": "timeout", "model": "isolated-test"}
        return _production_reply(prompt, **kwargs)

    monkeypatch.setattr(opportunity_transport, "call_model", call)
    snap = _snapshot(_with_public_context())
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snap)
    review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        item = review.get_run(conn, board["run_id"])["items"][0]
        assert item["audit"]["status"] == "failed"
        assert item["audit"]["failure_code"] == "context_timeout"
        assert item["audit"]["agents"]["context"]["failure_code"] == "timeout"
        assert item["audit"]["agents"]["counter"]["status"] == "unavailable"
        assert calls == ["context"]
        assert conn.execute(
            "SELECT count(*) FROM opportunity_agent_attempts WHERE agent='counter'"
        ).fetchone()[0] == 0
        assert not review.ensure_board(conn, snap)[1]
        review.ensure_board(conn, snap, retry_failed=True)
    fail["context"] = False
    review.process_run(str(path), board["run_id"], retry_failed=True)
    with sqlite3.connect(path) as conn:
        assert review.get_run(conn, board["run_id"])["status"] == "complete"
    assert calls.count("context") == 2
    assert calls.count("counter") == 1


def test_context_local_validation_failure_still_allows_counter(tmp_path, monkeypatch):
    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "context-local-failure.sqlite"
    calls = []

    def call(prompt, **kwargs):
        stage = "counter" if "intent" in json.loads(prompt)["reviews"][0] else "context"
        calls.append(stage)
        if stage == "context":
            return {"text": "invalid json", "error_code": "", "model": "isolated-test"}
        assert json.loads(prompt)["reviews"][0]["context_analysis"]["status"] == "failed"
        return _production_reply(prompt, **kwargs)

    monkeypatch.setattr(opportunity_transport, "call_model", call)
    snap = _snapshot(_with_public_context())
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snap)
    review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        item = review.get_run(conn, board["run_id"])["items"][0]
        assert item["audit"]["status"] == "failed"
        assert item["audit"]["agents"]["context"]["failure_code"] == "invalid_context_reply"
        assert item["audit"]["agents"]["counter"]["status"] == "complete"
    assert calls == ["context", "counter"]


def test_counter_provider_failure_keeps_context_for_explicit_retry(tmp_path, monkeypatch):
    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "counter-failure.sqlite"
    calls = []
    fail_counter = {"value": True}

    def call(prompt, **kwargs):
        stage = "counter" if "intent" in json.loads(prompt)["reviews"][0] else "context"
        calls.append(stage)
        if stage == "counter" and fail_counter["value"]:
            return {"text": None, "error_code": "timeout", "model": "isolated-test"}
        return _production_reply(prompt, **kwargs)

    monkeypatch.setattr(opportunity_transport, "call_model", call)
    snap = _snapshot(_with_public_context())
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snap)
    review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        item = review.get_run(conn, board["run_id"])["items"][0]
        assert item["audit"]["status"] == "failed"
        assert item["audit"]["agents"]["context"]["status"] == "complete"
        assert item["audit"]["agents"]["counter"]["failure_code"] == "timeout"
        assert review.ensure_board(conn, snap, retry_failed=True)[1]
    fail_counter["value"] = False
    review.process_run(str(path), board["run_id"], retry_failed=True)
    with sqlite3.connect(path) as conn:
        item = review.get_run(conn, board["run_id"])["items"][0]
        assert item["audit"]["status"] == "complete"
        assert item["audit"]["agents"]["context"]["status"] == "complete"
    assert calls == ["context", "counter", "counter"]


def test_explicit_retry_sends_point_limit_feedback_and_reuses_successful_context(
    tmp_path, monkeypatch
):
    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "retry-points.sqlite"
    calls = []

    def call(prompt, **kwargs):
        row = json.loads(prompt)["reviews"][0]
        stage = "counter" if "intent" in row else "context"
        calls.append((stage, row.get("retry_feedback")))
        response = _production_reply(prompt, **kwargs)
        if stage == "counter" and sum(name == "counter" for name, _ in calls) == 1:
            payload = json.loads(response["text"])
            point = payload["reviews"][0]["analysis"]["points"][0]
            payload["reviews"][0]["analysis"]["points"] = [point, point, point]
            response["text"] = json.dumps(payload)
        return response

    monkeypatch.setattr(opportunity_transport, "call_model", call)
    snap = _snapshot(_with_public_context())
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snap)
    review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        item = review.get_run(conn, board["run_id"])["items"][0]
        assert item["audit"]["agents"]["context"]["status"] == "complete"
        assert item["audit"]["agents"]["counter"]["failure_code"] == "invalid_analysis_points"
        assert "条数不合" in item["audit"]["agents"]["counter"]["failure_message"]
        assert review.ensure_board(conn, snap, retry_failed=True)[1]
    review.process_run(str(path), board["run_id"], retry_failed=True)
    with sqlite3.connect(path) as conn:
        assert review.get_run(conn, board["run_id"])["status"] == "complete"
        assert not review.ensure_board(conn, snap, retry_failed=True)[1]
    review.process_run(str(path), board["run_id"], retry_failed=True)
    assert [stage for stage, _ in calls] == ["context", "counter", "counter"]
    assert calls[0][1] is None and calls[1][1] is None
    assert "1—2条" in calls[2][1]


def test_explicit_retry_news_role_feedback_does_not_recalculate_context(tmp_path, monkeypatch):
    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "retry-news.sqlite"
    card = _with_public_context()
    card["evidence"].append(
        {
            "id": "n1",
            "role": "lead",
            "public": True,
            "text": "未核实新闻标题",
            "provenance": "unverified_news",
            "category": "news",
        }
    )
    calls = []

    def call(prompt, **kwargs):
        row = json.loads(prompt)["reviews"][0]
        stage = "counter" if "intent" in row else "context"
        calls.append((stage, row.get("retry_feedback")))
        response = _production_reply(prompt, **kwargs)
        if stage == "counter" and sum(name == "counter" for name, _ in calls) == 1:
            payload = json.loads(response["text"])
            point = payload["reviews"][0]["analysis"]["points"][0]
            point["evidence_ids"] = ["n1"]
            point["stance"] = "risk"
            response["text"] = json.dumps(payload)
        return response

    monkeypatch.setattr(opportunity_transport, "call_model", call)
    snap = _snapshot(card)
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snap)
    review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        item = review.get_run(conn, board["run_id"])["items"][0]
        assert item["audit"]["agents"]["counter"]["failure_code"] == "news_lead_promoted_to_fact"
        assert "未核实新闻" in item["audit"]["agents"]["counter"]["failure_message"]
        review.ensure_board(conn, snap, retry_failed=True)
    review.process_run(str(path), board["run_id"], retry_failed=True)
    assert [stage for stage, _ in calls] == ["context", "counter", "counter"]
    assert "stance必须为unknown" in calls[-1][1]


def test_explicit_retry_context_feedback_uses_saved_stage_code(tmp_path, monkeypatch):
    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "retry-context.sqlite"
    calls = []

    def call(prompt, **kwargs):
        row = json.loads(prompt)["reviews"][0]
        stage = "counter" if "intent" in row else "context"
        calls.append((stage, row.get("retry_feedback")))
        response = _production_reply(prompt, **kwargs)
        if stage == "context" and sum(name == "context" for name, _ in calls) == 1:
            payload = json.loads(response["text"])
            point = payload["reviews"][0]["points"][0]
            payload["reviews"][0]["points"] = [point] * 4
            response["text"] = json.dumps(payload)
        return response

    monkeypatch.setattr(opportunity_transport, "call_model", call)
    snap = _snapshot(_with_public_context())
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snap)
    review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        item = review.get_run(conn, board["run_id"])["items"][0]
        assert item["audit"]["agents"]["context"]["failure_code"] == "invalid_analysis_points"
        review.ensure_board(conn, snap, retry_failed=True)
    review.process_run(str(path), board["run_id"], retry_failed=True)
    assert [stage for stage, _ in calls] == ["context", "counter", "context", "counter"]
    assert calls[0][1] is None and "1—3条" in calls[2][1]
    assert "该point引用证据" in review._retry_feedback(
        "unsupported_analysis_number", agent="counter"
    )
    assert review._retry_feedback("private arbitrary failure text", agent="counter") is None


def test_exact_symbol_identity_separates_same_named_context():
    first = _with_public_context()
    second = json.loads(json.dumps(first))
    second["subject"]["id"] = "159915"
    second["subject"]["key"] = "symbol:159915"
    assert review._context_key(first) != review._context_key(second)


def test_news_summary_cannot_promote_unverified_headline():
    card = {
        "evidence": [
            {
                "id": "n1",
                "role": "lead",
                "public": True,
                "category": "news",
                "provenance": "unverified_news",
                "text": "标题线索",
                "source": "聚合搜索",
            }
        ]
    }
    answer = {
        "summary": "事件已核实，盈利已经改善",
        "points": [{"text": "事件已核实", "evidence_ids": ["n1"], "stance": "unknown"}],
        "gaps": [],
    }
    accepted = review._validate_analysis(answer, card)
    assert "盈利已经改善" not in accepted["summary"]
    assert accepted["points"][0]["text"] == "待核实线索：标题线索"
    answer["points"][0]["stance"] = "support"
    import pytest

    with pytest.raises(ValueError, match="news_lead_promoted"):
        review._validate_analysis(answer, card)


def test_counter_rejects_unanchored_buy_and_sell_numbers():
    card = {
        "evidence": [
            {"id": "ev_21f5", "role": "support", "text": "灰色背景与路牌待核"},
            {"id": "ev_9133", "role": "support", "text": "价格67.2"},
            {"id": "ev_bottom", "role": "opposition", "text": "底部30结构"},
            {"id": "ev_price", "role": "support", "text": "价格528.1503"},
        ]
    }

    def analysis(text, refs):
        return {
            "summary": "只解释原件",
            "points": [{"text": text, "evidence_ids": refs, "stance": "risk"}],
            "gaps": [],
        }

    with pytest.raises(ValueError, match="unsupported_analysis_number"):
        review._validate_analysis(
            analysis("买入点67.2/528.1503仍待核", ["ev_21f5", "ev_9133"]),
            card,
            counter=True,
        )
    with pytest.raises(ValueError, match="unsupported_analysis_number"):
        review._validate_analysis(
            analysis("卖出点有30结构", ["ev_21f5"]), card, counter=True
        )
    assert review._validate_analysis(
        analysis("买入点67.2/528.1503仍待核", ["ev_9133", "ev_price"]),
        card,
        counter=True,
    )["status"] == "complete"
    assert review._validate_analysis(
        analysis("卖出点有30结构", ["ev_bottom"]), card, counter=True
    )["status"] == "complete"


def test_analysis_numbers_accept_date_and_thousands_formats_but_not_url_digits():
    card = {
        "evidence": [
            {
                "id": "s1",
                "role": "support",
                "text": "原文数值1,234.50",
                "date": "2026-10-15",
                "report_date": "2026/06/30",
                "source_ref": "https://example.test/528.1503",
            }
        ]
    }

    def analysis(text):
        return {
            "summary": "原件日期可核",
            "points": [{"text": text, "evidence_ids": ["s1"], "stance": "risk"}],
            "gaps": [],
        }

    accepted = review._validate_analysis(
        analysis("2026年10月15日核查值1234.5，报告期2026.06.30"), card, counter=True
    )
    assert accepted["status"] == "complete"
    with pytest.raises(ValueError, match="unsupported_analysis_number"):
        review._validate_analysis(analysis("参考528.1503"), card, counter=True)
    with pytest.raises(ValueError, match="unsupported_analysis_number"):
        review._validate_analysis(analysis("报告期2026年06月29日"), card, counter=True)


def test_analysis_explicit_year_can_use_cited_date_without_loosening_other_numbers():
    card = {"evidence": [{
        "id": "industry", "role": "context", "public": True,
        "text": "前8个月电信业务收入同比下降2.2%，业务总量增长7.6%",
        "date": "2026-09-28", "report_date": "2026-08-31",
    }]}

    def analysis(text):
        return {"summary": "按原件核对", "points": [{
            "text": text, "evidence_ids": ["industry"], "stance": "risk",
        }], "gaps": []}

    accepted = review._validate_analysis(
        analysis("2026年前8个月收入同比下降2.2%，业务总量增长7.6%"), card
    )
    assert accepted["status"] == "complete"
    for text in (
        "2025年前8个月收入同比下降2.2%",  # wrong year
        "统计编号2026：前8个月收入同比下降2.2%",  # ordinary number
        "2026年前8个月收入下降2.2%，利润2026亿元",  # same digits are not another year
        "2026年前8个月收入同比下降2.3%",  # unsupported percentage
    ):
        with pytest.raises(ValueError, match="unsupported_analysis_number"):
            review._validate_analysis(analysis(text), card)


def test_half_year_report_year_must_match_same_point_report_date():
    card = {"evidence": [
        {"id": "report", "role": "context", "public": True,
         "text": "半年报说明业务变化", "report_date": "2026-06-30"},
        {"id": "other", "role": "context", "public": True,
         "text": "另一份报告", "report_date": "2025-06-30"},
    ]}

    def analysis(text, refs):
        return {"summary": "报告期已核", "points": [
            {"text": text, "evidence_ids": refs, "stance": "neutral"},
        ], "gaps": []}

    assert review._validate_analysis(
        analysis("2026半年报说明业务变化", ["report"]), card
    )["status"] == "complete"
    for text, refs in (
        ("2025半年报说明业务变化", ["report"]),
        ("2026半年报说明业务变化", ["other"]),
        ("业务收入为2026万元", ["report"]),
    ):
        with pytest.raises(ValueError, match="unsupported_analysis_number"):
            review._validate_analysis(analysis(text, refs), card)


def test_month_day_must_match_same_point_full_date():
    card = {"evidence": [
        {"id": "trigger", "role": "support", "text": "触发日期 2026-10-15"},
        {"id": "other", "role": "support", "text": "另一事件 2026-10-16"},
    ]}

    def analysis(text, refs):
        return {"summary": "日期已核", "points": [
            {"text": text, "evidence_ids": refs, "stance": "risk"},
        ], "gaps": []}

    assert review._validate_analysis(
        analysis("10月15日触发提醒", ["trigger"]), card, counter=True
    )["status"] == "complete"
    for text, refs in (
        ("10月16日触发提醒", ["trigger"]),
        ("10月15日触发提醒", ["other"]),
        ("2025年10月15日触发提醒", ["trigger"]),
        ("2026年10月16日触发提醒", ["trigger"]),
    ):
        with pytest.raises(ValueError, match="unsupported_analysis_number"):
            review._validate_analysis(analysis(text, refs), card, counter=True)


def test_analysis_rejects_internal_ids_in_user_text_and_news_source_numbers_survive():
    card = {
        "evidence": [
            {
                "id": "ev_news",
                "role": "lead",
                "text": "标题含67.2，仅为线索",
                "provenance": "unverified_news",
            }
        ]
    }
    answer = {
        "summary": "仅有新闻线索",
        "points": [{"text": "标题待核", "evidence_ids": ["ev_news"], "stance": "unknown"}],
        "gaps": [],
    }
    accepted = review._validate_analysis(answer, card, counter=True)
    assert "67.2" in accepted["points"][0]["text"]
    for field in ("summary", "points", "gaps"):
        leaked = json.loads(json.dumps(answer))
        if field == "points":
            leaked["points"][0]["text"] = "见ev_9133"
        elif field == "gaps":
            leaked["gaps"] = ["见ev_9133"]
        else:
            leaked["summary"] = "见ev_9133"
        with pytest.raises(ValueError, match="internal_evidence_id_leaked"):
            review._validate_analysis(leaked, card, counter=True)
    assert "原件未对上" in review._stage("failed", failure="unsupported_analysis_number")[
        "failure_message"
    ]
    assert "内部证据编号" in review._stage("failed", failure="internal_evidence_id_leaked")[
        "failure_message"
    ]


def test_counter_qualifies_proxy_support_and_does_not_invent_user_thesis():
    card = {
        "evidence": [
            {
                "id": "proxy",
                "role": "context",
                "public": True,
                "provenance": "research_proxy",
                "text": "筹码近支撑估计，仅供参考",
            },
            {
                "id": "legacy_proxy",
                "role": "context",
                "public": True,
                "provenance": "existing_rule",
                "source": "技术规则",
                "text": (
                    "接近代理支撑密集区（筹码分布代理）；下方5%区间代理量占比 21.9%；"
                    "规则 volume_profile_proxy"
                ),
            },
            {"id": "rule", "role": "support", "text": "原规则仅支持观察"},
        ]
    }

    def analysis(text, ref="proxy", *, summary="原件需核", gaps=None):
        return {
            "summary": summary,
            "points": [{"text": text, "evidence_ids": [ref], "stance": "risk"}],
            "gaps": [] if gaps is None else gaps,
        }

    with pytest.raises(ValueError, match="unqualified_proxy_claim"):
        review._validate_analysis(analysis("即存在支撑密集区"), card, counter=True)
    with pytest.raises(ValueError, match="unqualified_proxy_claim"):
        review._validate_analysis(
            analysis(
                "技术数据显示下方5%区间代理量占比21.9%，即存在支撑密集区，"
                "这并不代表无下跌风险，但材料中没有已核实的价格突破或趋势确认来支持卖出逻辑。",
                "legacy_proxy",
            ),
            card,
            counter=True,
        )
    assert review._validate_analysis(
        analysis("研究代理估计附近有支撑密集区，仅供参考"), card, counter=True
    )["status"] == "complete"
    assert review._validate_analysis(
        analysis("代理估计提示附近可能有支撑密集区", "legacy_proxy"), card, counter=True
    )["status"] == "complete"
    assert review._validate_analysis(
        analysis("若考虑卖出，需核对技术背景", "rule"), card, counter=True
    )["status"] == "complete"
    assert review._validate_analysis(
        analysis("若考虑买入，应核对支撑密集区", "rule"), card, counter=True
    )["status"] == "complete"

    for text in ("买入逻辑引用的标题", "你的买入理由", "用户认为已有机会"):
        with pytest.raises(ValueError, match="assumed_user_thesis"):
            review._validate_analysis(analysis(text, "rule"), card, counter=True)
    with pytest.raises(ValueError, match="assumed_user_thesis"):
        review._validate_analysis(
            analysis("原规则仍需核", "rule", gaps=["用户认为已有机会"]), card, counter=True
        )
    assert "研究代理" in review._stage("failed", failure="unqualified_proxy_claim")[
        "failure_message"
    ]
    assert "编造" in review._stage("failed", failure="assumed_user_thesis")["failure_message"]
    assert "research_proxy" in review._retry_feedback("unqualified_proxy_claim", agent="counter")
    assert "用户原话" in review._retry_feedback("assumed_user_thesis", agent="counter")
    assert "自动机会卡没有用户主张" in review._SYSTEM_PROMPT


def test_concurrent_runs_share_context_before_counter(tmp_path, monkeypatch):
    import time
    from concurrent.futures import ThreadPoolExecutor

    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "concurrent-context.sqlite"
    calls = []
    first = _with_public_context()
    second = json.loads(json.dumps(first))
    second["intent"] = "sell"
    second["candidate_key"] = first["subject"]["key"] + ":sell"

    def call(prompt, **kwargs):
        data = json.loads(prompt)
        is_context = "intent" not in data["reviews"][0]
        calls.append("context" if is_context else "counter")
        if is_context:
            time.sleep(0.08)
        else:
            assert all(x["context_analysis"]["status"] == "complete" for x in data["reviews"])
        return _production_reply(prompt, **kwargs)

    monkeypatch.setattr(opportunity_transport, "call_model", call)
    with sqlite3.connect(path) as conn:
        a, _ = review.ensure_board(conn, _snapshot(first))
        b, _ = review.ensure_board(conn, _snapshot(second))
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(review.process_run, str(path), r["run_id"]) for r in (a, b)]
        for job in jobs:
            job.result(timeout=5)
    with sqlite3.connect(path) as conn:
        assert all(review.get_run(conn, r["run_id"])["status"] == "complete" for r in (a, b))
    assert calls.count("context") == 1


def test_production_counter_requires_analysis(tmp_path, monkeypatch):
    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "strict-counter.sqlite"
    monkeypatch.setattr(
        opportunity_transport,
        "call_model",
        lambda prompt, **kwargs: {
            "text": _model([r["review_id"] for r in json.loads(prompt)["reviews"]], prompt),
            "error_code": "",
            "model": "isolated-test",
        },
    )
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, _snapshot(_card()))
    review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        item = review.get_run(conn, board["run_id"])["items"][0]
        assert item["audit"]["status"] == "failed"
        assert item["audit"]["agents"]["counter"]["failure_code"] == "invalid_analysis_shape"


@pytest.mark.parametrize("failure_code", ["timeout", "http_error", "insufficient_balance"])
def test_provider_failure_stops_remaining_queue_and_explicit_retry_recovers(
    tmp_path, monkeypatch, failure_code
):
    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "provider-unavailable.sqlite"
    snap = _snapshot(_with_public_context())
    for index in range(1, 16):
        card = json.loads(json.dumps(snap["items"][0]))
        card["subject"].update(id=f"symbol{index}", key=f"symbol:symbol{index}")
        card["candidate_key"] = f"symbol:symbol{index}:buy"
        snap["items"].append(card)
    calls = []

    def unavailable(prompt, **kwargs):
        calls.append(prompt)
        return {"text": None, "error_code": failure_code, "attempts": 2}

    monkeypatch.setattr(opportunity_transport, "call_model", unavailable)
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snap)
    review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        result = review.get_run(conn, board["run_id"])
        assert result["status"] == "partial"
        assert all(x["audit"]["status"] == "failed" for x in result["items"])
        assert any(x["audit"]["failure_code"] == "provider_unavailable" for x in result["items"])
        assert len(calls) <= 2
        assert conn.execute(
            "SELECT count(*) FROM opportunity_agent_attempts WHERE agent='counter'"
        ).fetchone()[0] == 0
        new_snap = json.loads(json.dumps(snap))
        new_snap["items"][0]["headline"] = "更新后的观察资料"
        newer, _ = review.ensure_board(conn, new_snap)
    call_count = len(calls)
    review.process_run(str(path), newer["run_id"])
    assert len(calls) == call_count  # Changed inputs do not repeatedly hit an unavailable provider.
    with sqlite3.connect(path) as conn:
        review.ensure_board(conn, snap, retry_failed=True)
    monkeypatch.setattr(opportunity_transport, "call_model", _production_reply)
    review.process_run(str(path), board["run_id"], retry_failed=True)
    with sqlite3.connect(path) as conn:
        assert review.get_run(conn, board["run_id"])["status"] == "complete"


def test_verbatim_news_clipping_does_not_invent_an_unanchored_number():
    card = {"evidence": [{
        "id": "news", "role": "lead", "provenance": "unverified_news",
        "public": True, "text": "a" * 219 + "123456789",
    }]}
    value = {"summary": "待核实新闻", "points": [{
        "text": "标题尚未核实", "evidence_ids": ["news"], "stance": "unknown",
    }], "gaps": []}
    assert review._validate_analysis(value, card)["status"] == "complete"


def test_retry_schema_feedback_is_bounded_and_numeric_guidance_forbids_derivation():
    assert "stance" in review._retry_feedback("invalid_point", agent="context")
    assert "最多3条" in review._retry_feedback("invalid_analysis_gaps", agent="context")
    assert "加总" in review._retry_feedback("unsupported_analysis_number", agent="context")


def test_context_input_keeps_product_focus_and_excludes_indirect_business_statistics():
    from lei_signal.copilot import opportunity_review as service
    focus = {"kind": "sector", "label": "通信设备与光互联", "market": "cn", "topics": ["光模块"]}
    card = {"subject": {"kind": "symbol", "id": "515880.SS", "name": "通信ETF国泰"},
        "narrative_focus": focus, "evidence": [
            {"id": "direct", "public": True, "category": "industry", "role": "context",
             "text": "成分公司光互联业务", "narrative_kind": "industry", "relevance": "direct"},
            {"id": "indirect", "public": True, "category": "industry", "role": "context",
             "text": "电信运营商统计", "narrative_kind": "industry", "relevance": "indirect"}]}
    material = service._context_material(card)
    assert material["narrative_focus"] == focus
    assert [row["id"] for row in material["evidence"]] == ["direct"]
    assert material["evidence"][0]["narrative_kind"] == "industry"


@pytest.mark.parametrize(
    ("field", "limit", "error"),
    [("summary", 90, "invalid_summary"), ("first_point", 90, "invalid_point_text"),
     ("point", 130, "invalid_point_text"),
     ("gap", 90, "invalid_analysis_gaps")],
)
def test_generated_analysis_length_boundaries_reject_without_truncation(field, limit, error):
    def answer(length):
        value = {"summary": "原件可核", "points": [
            {"text": "原件可核", "evidence_ids": ["s1"], "stance": "risk"}
        ], "gaps": []}
        if field == "summary":
            value["summary"] = "文" * length
        elif field == "first_point":
            value["points"][0]["text"] = "文" * length
        elif field == "point":
            value["points"].append(
                {"text": "文" * length, "evidence_ids": ["s1"], "stance": "risk"}
            )
        else:
            value["gaps"] = ["文" * length]
        return value

    assert review._validate_analysis(answer(limit), _card())["status"] == "complete"
    too_long = answer(limit + 1)
    original = json.loads(json.dumps(too_long))
    with pytest.raises(ValueError, match=error):
        review._validate_analysis(too_long, _card())
    assert too_long == original


def test_analysis_gaps_trim_and_deduplicate_exact_text():
    value = {"summary": "原件可核", "points": [
        {"text": "原件可核", "evidence_ids": ["s1"], "stance": "risk"}
    ], "gaps": [" 缺最新原件 ", "缺最新原件", "缺持仓覆盖比例"]}
    assert review._validate_analysis(value, _card())["gaps"] == ["缺最新原件", "缺持仓覆盖比例"]


def test_long_subsequent_cited_point_keeps_full_text_without_expanding_summary():
    text = "文" * 130
    value = {"summary": "原件可核", "points": [
        {"text": "首条已核事实", "evidence_ids": ["s1"], "stance": "risk"},
        {"text": text, "evidence_ids": ["s1"], "stance": "risk"}
    ], "gaps": []}
    accepted = review._validate_analysis(value, _card())
    assert len(accepted["summary"]) <= 90
    assert accepted["points"][1]["text"] == text
    assert accepted["summary"] == "首条已核事实"


def test_news_source_replacement_preserves_verbatim_source_beyond_generated_text_limit():
    text = "标题原件" * 60 + "123456789"
    card = {"evidence": [{"id": "news", "role": "lead", "provenance": "unverified_news",
                          "public": True, "text": text}]}
    value = {"summary": "待核实新闻", "points": [
        {"text": "标题尚未核实", "evidence_ids": ["news"], "stance": "unknown"}
    ], "gaps": []}
    accepted = review._validate_analysis(value, card)
    assert accepted["points"][0]["text"] == "待核实线索：" + text
    assert len(accepted["summary"]) <= 90
    value["points"][0]["text"] = "文" * 131
    with pytest.raises(ValueError, match="invalid_point_text"):
        review._validate_analysis(value, card)


def test_duplicate_summary_remains_accepted_and_repair_guidance_matches_limits():
    value = {"summary": "原件可核", "points": [
        {"text": "原件可核", "evidence_ids": ["s1"], "stance": "risk"}
    ], "gaps": []}
    assert review._validate_analysis(value, _card())["status"] == "complete"
    assert "90" in review._retry_feedback("invalid_summary", agent="context")
    assert "130" in review._retry_feedback("invalid_point_text", agent="context")
    assert "90" in review._retry_feedback("invalid_analysis_gaps", agent="context")
    assert "余额不足" in review._stage("failed", failure="insufficient_balance")["failure_message"]


def test_first_verified_point_after_news_also_obeys_summary_limit():
    card = _card()
    card["evidence"].append({"id": "news", "role": "lead", "provenance": "unverified_news",
                             "public": True, "text": "未核实标题"})
    value = {"summary": "待核资料", "points": [
        {"text": "标题尚未核实", "evidence_ids": ["news"], "stance": "unknown"},
        {"text": "文" * 91, "evidence_ids": ["s1"], "stance": "risk"},
    ], "gaps": []}
    with pytest.raises(ValueError, match="invalid_point_text"):
        review._validate_analysis(value, card)


def test_actual_partial_holdings_do_not_support_first_largest_holding_claim():
    card = {"evidence": [
        {"id": "company", "role": "context", "public": True,
         "text": "上半年光互联产品收入同比增长100.59%；公司将收入增长与AI算力投资发展联系。"},
        {"id": "holdings", "role": "context", "public": True,
         "text": "2026年6月30日披露持仓：新易盛占基金净值15.60%、中际旭创14.61%、工业富联9.12%、"
                 "亨通光电6.89%、天孚通信6.33%。这些是报告期持仓，当前权重及披露后调仓未知。"},
    ]}
    value = {"summary": "报告期持仓业务增长", "points": [{
        "text": "新易盛半年报披露上半年光互联产品收入同比增长100.59%，公司将增长与AI算力投资联系；"
                "该股是通信ETF报告期第一大持仓，占净值15.60%。",
        "evidence_ids": ["company", "holdings"], "stance": "support",
    }], "gaps": []}
    with pytest.raises(ValueError, match="unsupported_business_rank"):
        review._validate_analysis(value, card)


@pytest.mark.parametrize("rank", ["第一大持仓", "最大持仓", "行业龙头", "光模块龙头"])
def test_business_rank_requires_explicit_same_point_source_wording(rank):
    value = {"summary": "核对原件", "points": [{
        "text": f"该公司为{rank}", "evidence_ids": ["s1"], "stance": "neutral",
    }], "gaps": []}
    with pytest.raises(ValueError, match="unsupported_business_rank"):
        review._validate_analysis(value, _card())
    card = _card(text=f"原件明确列明该公司为{rank}")
    assert review._validate_analysis(value, card)["status"] == "complete"
    card["evidence"].append({"id": "not-cited", "role": "context", "public": True,
                             "text": f"原件明确列明该公司为{rank}"})
    card["evidence"][0]["text"] = "只给业务资料，没有排名"
    with pytest.raises(ValueError, match="unsupported_business_rank"):
        review._validate_analysis(value, card)


@pytest.mark.parametrize(
    "text", ["无法确认第一大持仓", "尚未确认其是否为最大持仓", "该公司并非行业龙头",
             "缺少第一大持仓的明确排名资料"]
)
def test_business_rank_uncertainty_or_negation_is_not_a_positive_rank_claim(text):
    value = {"summary": "排名未核", "points": [{
        "text": text, "evidence_ids": ["s1"], "stance": "unknown",
    }], "gaps": []}
    assert review._validate_analysis(value, _card())["status"] == "complete"


def test_rank_negation_applies_only_to_the_nearby_claim():
    def analysis(text):
        return {"summary": "排名待核", "points": [
            {"text": text, "evidence_ids": ["s1"], "stance": "unknown"},
        ], "gaps": []}

    card = _card()
    for text in ("不能据此推断第一大持仓", "不据此推断行业龙头",
                 "不能据此认定第一大持仓或行业龙头"):
        assert review._validate_analysis(analysis(text), card)["status"] == "complete"
    for text in ("该公司是第一大持仓", "不能据此推断第一大持仓，但它是行业龙头",
                 "不能据此推断第一大持仓，该公司是行业龙头"):
        with pytest.raises(ValueError, match="unsupported_business_rank"):
            review._validate_analysis(analysis(text), card)


def test_each_claimed_holding_industry_needs_same_point_company_evidence():
    coverage = {"id": "coverage", "role": "context", "public": True,
                "category": "fundamentals", "provenance": "disclosed",
                "text": "已披露股票覆盖基金净值43.49%，行业全貌未知。"}
    holdings = [
        {"id": "h_ai", "role": "context", "public": True,
         "category": "fundamentals", "provenance": "disclosed",
         "text": "披露股票：寒武纪（688256）。"},
        {"id": "h_optical", "role": "context", "public": True,
         "category": "fundamentals", "provenance": "disclosed",
         "text": "披露股票：中际旭创（300308）。"},
        {"id": "h_fab", "role": "context", "public": True,
         "category": "fundamentals", "provenance": "disclosed",
         "text": "披露股票：华虹宏力（688347）。"},
    ]
    business = [
        {"id": "b_ai", "role": "context", "public": True,
         "category": "industry", "provenance": "business_reference",
         "text": "寒武纪（688256）已核业务行业：人工智能芯片。"},
        {"id": "b_optical", "role": "context", "public": True,
         "category": "industry", "provenance": "business_reference",
         "text": "中际旭创（300308）已核业务行业：光通信设备与器件。"},
        {"id": "b_fab", "role": "context", "public": True,
         "category": "industry", "provenance": "business_reference",
         "text": "华虹宏力（688347）已核业务行业：半导体晶圆制造。"},
    ]
    card = {"evidence": [coverage, *holdings, *business]}
    text = (
        "基金持仓披露显示配置AI芯片、光通信与半导体制造公司，"
        "但披露股票仅覆盖净值43.49%，行业全貌未知。"
    )

    def analysis(refs, wording=text):
        return {"summary": "持仓行业待核", "points": [
            {"text": wording, "evidence_ids": refs, "stance": "neutral"},
        ], "gaps": []}

    with pytest.raises(ValueError, match="industry_attribution_unproven"):
        review._validate_analysis(analysis(["coverage", "h_ai", "h_optical"]), card)
    assert review._validate_analysis(analysis([
        "coverage", "h_ai", "h_optical", "h_fab", "b_ai", "b_optical", "b_fab"
    ]), card)["status"] == "complete"
    with pytest.raises(ValueError, match="industry_attribution_unproven"):
        review._validate_analysis(analysis([
            "coverage", "h_ai", "h_optical", "b_ai", "b_optical", "b_fab"
        ]), card)  # The cited fab business is not paired with a cited holding.
    direct = {"id": "direct", "role": "context", "public": True,
              "category": "fundamentals", "provenance": "disclosed",
              "text": "披露持仓：寒武纪，业务为AI芯片公司。"}
    card["evidence"].append(direct)
    assert review._validate_analysis(analysis(
        ["direct"], "基金持仓配置AI芯片公司。"
    ), card)["status"] == "complete"
    assert review._validate_analysis(analysis(
        ["b_ai"], "寒武纪从事人工智能芯片业务，未核本基金是否持有。"
    ), card)["status"] == "complete"
    assert review._validate_analysis(analysis(
        ["b_optical"], "行业政策涉及光通信公司，未核本基金持仓变化。"
    ), card)["status"] == "complete"


def test_counter_rejects_explicit_reversal_of_only_technical_opposition():
    card = {"intent": "sell", "evidence": [
        {"id": "long_trend", "role": "opposition", "category": "technical",
         "text": "长周期背景支持或改善中；日线与周线方向不同。"},
        {"id": "exit", "role": "support", "category": "technical",
         "text": "已有退出提醒。"},
    ]}

    def analysis(text, refs):
        return {"summary": "核对原技术证据", "points": [
            {"text": text, "evidence_ids": refs, "stance": "risk"},
        ], "gaps": []}

    with pytest.raises(ValueError, match="counter_role_reinterpretation"):
        review._validate_analysis(analysis(
            "材料中该技术支持项实为退出方向证据：长周期仍改善。", ["long_trend"]
        ), card, counter=True)
    assert review._validate_analysis(analysis(
        "长周期仍改善，不应将该项作为退出证据。", ["long_trend"]
    ), card, counter=True)["status"] == "complete"
    assert review._validate_analysis(analysis(
        "已有退出提醒可作为卖出依据，但仍须核对计划。", ["exit"]
    ), card, counter=True)["status"] == "complete"
    card["intent"] = "buy"
    with pytest.raises(ValueError, match="counter_role_reinterpretation"):
        review._validate_analysis(analysis(
            "该反向技术项实为买入方向证据。", ["long_trend"]
        ), card, counter=True)


def test_cached_provider_failure_stays_local_without_retry_or_blocking_new_products(
    tmp_path, monkeypatch
):
    from threading import Event

    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "cached-provider-failure.sqlite"
    cached = _with_public_context()
    cached["subject"].update(id="000cached", key="symbol:000cached")
    cached["candidate_key"] = "symbol:000cached:buy"
    cached_sell = json.loads(json.dumps(cached))
    cached_sell.update(intent="sell", candidate_key="symbol:000cached:sell")
    snap = _snapshot(cached)
    snap["items"].append(cached_sell)
    for index in range(1, 7):
        card = _with_public_context()
        card["subject"].update(id=f"{index:03d}new", key=f"symbol:{index:03d}new")
        card["candidate_key"] = f"symbol:{index:03d}new:buy"
        snap["items"].append(card)
    old_failure = review._stage("failed", failure="http_error")
    # Populated metadata must not be used to guess whether a call is current.
    old_failure.update(generated_at=review._now(), model="cached-provider")
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snap)
        conn.execute(
            "INSERT INTO opportunity_context_reviews(context_key,status,result_json,generated_at) "
            "VALUES(?, 'failed', ?, ?)",
            (review._context_key(cached), json.dumps(old_failure), review._now()),
        )
    calls = []
    cached_finished = Event()
    process_claimed = review._process_claimed

    def finish_cached(*args, **kwargs):
        stopped = process_claimed(*args, **kwargs)
        if any(card[0]["subject"]["id"] == "000cached" for card in args[1].values()):
            cached_finished.set()
        return stopped

    def success(prompt, **kwargs):
        assert cached_finished.wait(5)
        rows = json.loads(prompt)["reviews"]
        stage = "counter" if "intent" in rows[0] else "context"
        calls.extend((stage, row["subject"]["product_id"]) for row in rows)
        return _production_reply(prompt, **kwargs)

    monkeypatch.setattr(opportunity_transport, "call_model", success)
    monkeypatch.setattr(review, "_process_claimed", finish_cached)
    review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        result = review.get_run(conn, board["run_id"])
        old_items = [x for x in result["items"] if x["card"]["subject"]["id"] == "000cached"]
        new_items = [x for x in result["items"] if x["card"]["subject"]["id"] != "000cached"]
        assert len(new_items) == 6
        assert all(x["audit"]["status"] == "complete" for x in new_items)
        assert all(x["audit"]["failure_code"] == "context_http_error" for x in old_items)
        assert all(x["audit"]["agents"]["counter"]["status"] == "unavailable" for x in old_items)
        assert all(x["audit"]["agents"]["context"] == old_failure for x in old_items)
        assert conn.execute(
            "SELECT count(*) FROM opportunity_review_provider_state"
        ).fetchone()[0] == 0
        saved = conn.execute(
            "SELECT result_json FROM opportunity_context_reviews WHERE context_key=?",
            (review._context_key(cached),),
        ).fetchone()[0]
        assert json.loads(saved) == old_failure
    assert len(calls) == 12
    assert not any(product == "symbol:000cached" for _, product in calls)


def test_cached_and_fresh_contexts_in_one_product_batch_are_processed_separately(
    tmp_path, monkeypatch
):
    from lei_signal.copilot import opportunity_transport

    path = tmp_path / "mixed-contexts.sqlite"
    buy = _with_public_context()
    sell = json.loads(json.dumps(buy))
    sell.update(intent="sell", candidate_key="symbol:510300:sell")
    for evidence in sell["evidence"]:
        if evidence.get("public") and evidence.get("category") == "fundamentals":
            evidence["text"] += "；另一个方向使用较新公开资料"
    assert review._context_key(buy) != review._context_key(sell)
    snap = _snapshot(buy)
    snap["items"].append(sell)
    with sqlite3.connect(path) as conn:
        board, _ = review.ensure_board(conn, snap)
        conn.execute(
            "INSERT INTO opportunity_context_reviews(context_key,status,result_json) "
            "VALUES(?, 'failed', ?)",
            (review._context_key(buy), json.dumps(review._stage("failed", failure="http_error"))),
        )
    calls = []

    def success(prompt, **kwargs):
        rows = json.loads(prompt)["reviews"]
        calls.append(rows)
        return _production_reply(prompt, **kwargs)

    monkeypatch.setattr(opportunity_transport, "call_model", success)
    review.process_run(str(path), board["run_id"])
    with sqlite3.connect(path) as conn:
        items = review.get_run(conn, board["run_id"])["items"]
        by_side = {item["card"]["intent"]: item for item in items}
        assert by_side["buy"]["audit"]["failure_code"] == "context_http_error"
        assert by_side["buy"]["audit"]["agents"]["counter"]["status"] == "unavailable"
        assert by_side["sell"]["audit"]["status"] == "complete"
        assert conn.execute(
            "SELECT raw_attempt FROM opportunity_review_cards WHERE review_id=?",
            (by_side["buy"]["review_id"],),
        ).fetchone()[0] == ""
        assert conn.execute(
            "SELECT count(*) FROM opportunity_review_provider_state"
        ).fetchone()[0] == 0
    assert len(calls) == 2
    assert [row["review_id"] for row in calls[0]] == [review._context_key(sell)]
    assert [row["review_id"] for row in calls[1]] == [by_side["sell"]["review_id"]]
