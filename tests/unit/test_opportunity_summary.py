"""Agent summary remains source-bound and an explicit, cached action."""

from __future__ import annotations

import json
import time
from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api import opportunity_summary as summary


def _board(*, checked_at: str = "2026-10-18T10:00:00+08:00") -> dict:
    return {
        "run_id": "orb_" + "a" * 64,
        "as_of": "2026-10-18",
        "checked_at": checked_at,
        "status": "complete",
        "limitations": [],
        "items": [
            {
                "card": {
                    "subject": {
                        "key": "holding:private123",
                        "kind": "holding",
                        "id": "private123",
                        "symbol": "515880.SS",
                        "name": "通信ETF",
                        "amount": "9000",
                    },
                    "intent": "buy",
                    "evidence": [
                        {
                            "id": "public-one",
                            "public": True,
                            "role": "context",
                            "text": "2026年通信设备收入增长3%",
                            "source": "公司公告",
                            "source_ref": "https://example.com/report",
                            "date": "2026-10-16",
                        },
                        {
                            "id": "private-one",
                            "public": False,
                            "role": "context",
                            "text": "账户金额9000元",
                            "source": "已关联原持仓计划",
                            "source_ref": "https://example.com/private",
                        },
                        {
                            "id": "macro-one",
                            "public": True,
                            "role": "context",
                            "category": "fundamentals",
                            "provenance": "local_macro_observation",
                            "narrative_kind": "macro",
                            "text": "截至2026-10-16，国债收益率为2%。",
                            "source": "宏观源",
                            "source_ref": "https://example.com/macro",
                            "date": "2026-10-16",
                            "report_date": "2026-10-16",
                        },
                        {
                            "id": "sentiment-one",
                            "public": True,
                            "role": "context",
                            "category": "fundamentals",
                            "provenance": "local_macro_observation",
                            "narrative_kind": "macro",
                            "text": "截至2026-10-16，VIX为20点。",
                            "source": "情绪源",
                            "source_ref": "https://example.com/sentiment",
                            "date": "2026-10-16",
                            "report_date": "2026-10-16",
                        },
                        {
                            "id": "news-one",
                            "public": True,
                            "role": "context",
                            "category": "industry",
                            "provenance": "verified_public_source",
                            "text": "行业公开报告称设备订单增加，盈利仍未核实。",
                            "source": "行业源",
                            "source_ref": "https://example.com/news",
                            "date": "2026-10-15",
                            "published_at": "2026-10-15",
                        },
                    ],
                    "original_plan": "私人买入理由",
                },
                "audit": {
                    "agents": {
                        "context": {
                            "status": "complete",
                            "points": [
                                {"text": "收入增长3%", "evidence_ids": ["public-one"]},
                                {"text": "账户金额9000元", "evidence_ids": ["private-one"]},
                            ],
                        },
                        "counter": {"status": "failed", "points": []},
                    }
                },
            }
        ],
    }


def _snapshot(*, status: str = "new", recent: bool = True) -> dict:
    return {
        "display_name": "通信ETF",
        "meta": {
            "last_bar_date": "2026-10-16",
            "freshness": "current",
            "bar_status": "closed",
            "is_intraday_forming": False,
        },
        "signals": [
            {
                "id": "rule-one",
                "side": "buy",
                "title": "阶段转强",
                "summary": "收盘后阶段转强",
                "provenance": "lei_explicit",
                "event_date": "2026-10-16",
                "status": status,
                "age_bars": 0,
                "is_recent": recent,
                "next_step_cn": "继续核对原触发条件",
                "invalidation_cn": "跌破原失效位",
                "missing_conditions": ["等待收盘"],
            }
        ],
    }


def _material():
    return summary._material(
        _board(), lambda symbol: _snapshot(), source_path=Path("/no-such-source.json")
    )


def _good(material):
    tech = material["recent"][0]["source_id"]
    contexts = []
    for kind, meaning, counterpoint in (
        ("macro", "利率可能影响未来盈利的估值。", "只见单期读数，方向未知。"),
        ("sentiment", "预期波动可作为风险环境参考。", "不能判断价格方向。"),
        ("news", "行业需求或与产品相关。", "产品当前持仓和盈利未核实。"),
    ):
        source = material["products"][0]["context_slots"][kind]["sources"][0]
        contexts.append(
            {
                "kind": kind,
                "impact": "unknown",
                "fact_source_id": source["id"],
                "meaning": meaning,
                "counterpoint": counterpoint,
                "citation_ids": [source["id"]],
            }
        )
    return {
        "overview": "通信ETF有近期技术事件",
        "items": [
            {
                "source_id": tech,
                "observation": "收盘后阶段转强",
                "reason": "公开资料仅解释背景",
                "citation_ids": [tech],
                "contexts": contexts,
            }
        ],
    }


def test_prompt_selects_fact_source_and_binds_technical_source_in_service():
    material, _ = _material()
    assert material["prompt_version"] == "source-bound/10"
    assert "不要输出fact文本" in summary._SYSTEM
    assert "fact_source_id" in summary._SYSTEM
    assert "技术来源由系统按source_id固定绑定" in summary._SYSTEM
    assert "还须同时引用方法来源" in summary._SYSTEM
    assert "一般机制" in summary._SYSTEM
    assert "不能只重复" in summary._SYSTEM
    assert "即使写否定句也不用" in summary._SYSTEM


def test_input_omits_private_holding_identity_and_checked_at_is_not_a_change():
    material, local = _material()
    encoded = json.dumps(material, ensure_ascii=False)
    for secret in ("private123", "holding:", "9000", "私人买入理由", "private-one"):
        assert secret not in encoded
    assert list(local["recent"].values())[0]["subject_key"] == "holding:private123"
    assert "subject_key" not in encoded
    other, _ = summary._material(
        _board(checked_at="2026-10-18T10:01:00+08:00"),
        lambda symbol: _snapshot(),
        source_path=Path("/no-such-source.json"),
    )
    assert summary.fingerprint(material) == summary.fingerprint(other)


def test_old_or_cleared_event_is_not_promoted_to_recent():
    for snapshot in (_snapshot(status="cleared"), _snapshot(recent=False)):
        material, local = summary._material(_board(), lambda symbol, value=snapshot: value)
        assert material["recent"] == []
        assert local["recent"] == {}
        assert material["coverage"]["recent_products"] == 0
        assert any("缺少" in text or "没有可核实" in text for text in material["limitations"])


def test_output_rejects_wrong_product_unknown_source_and_unbacked_numbers():
    material, local = _material()
    good = _good(material)
    overview, rows = summary._parse_output(json.dumps(good, ensure_ascii=False), material, local)
    assert overview and rows[0]["side"] == "buy"
    assert rows[0]["subject_key"] == "holding:private123"
    assert rows[0]["watch"] == "继续核对原触发条件"
    assert "跌破原失效位" in rows[0]["sources"][0]["text"]
    assert [x["status"] for x in rows[0]["contexts"]] == ["available"] * 3
    numbered = deepcopy(good)
    numbered["overview"] = "1个产品有近期技术事件"
    assert summary._parse_output(json.dumps(numbered, ensure_ascii=False), material, local)[
        0
    ].startswith("在已核对")
    bad = deepcopy(good)
    bad["items"][0]["source_id"] = "ev_missing"
    with pytest.raises(ValueError, match="unsupported_focus"):
        summary._parse_output(json.dumps(bad), material, local)
    bad = deepcopy(good)
    bad["items"][0]["observation"] = "目标收益99%"
    bad["items"][0]["reason"] = "报告期持仓与当前权重未知"
    _, fixed = summary._parse_output(json.dumps(bad), material, local)
    assert fixed[0]["observation"] == material["recent"][0]["text"]
    assert fixed[0]["reason"] == ""
    assert "99%" not in fixed[0]["observation"]
    bad = deepcopy(good)
    bad["overview"] = "今天可以买入99%仓位"
    with pytest.raises(ValueError, match="unsupported_overview_number"):
        summary._parse_output(json.dumps(bad), material, local)


def test_context_contract_rejects_missing_kind_direction_fake_fact_and_private_amount():
    material, local = _material()
    good = _good(material)
    bad = deepcopy(good)
    del bad["items"][0]["contexts"]
    with pytest.raises(ValueError, match="invalid_contexts"):
        summary._parse_output(json.dumps(bad), material, local)
    bad = deepcopy(good)
    bad["items"][0]["contexts"][0]["impact"] = "negative"
    with pytest.raises(ValueError, match="unsupported_context_direction"):
        summary._parse_output(json.dumps(bad), material, local)
    bad = deepcopy(good)
    bad["items"][0]["contexts"][0]["fact"] = "国债收益率已连续上升"
    with pytest.raises(ValueError, match="model_fact_not_allowed"):
        summary._parse_output(json.dumps(bad), material, local)
    bad = deepcopy(good)
    bad["items"][0]["contexts"][0]["citation_ids"] = bad["items"][0]["contexts"][1]["citation_ids"]
    with pytest.raises(ValueError, match="cross_kind_citation"):
        summary._parse_output(json.dumps(bad), material, local)
    bad = deepcopy(good)
    bad["items"][0]["contexts"][2]["meaning"] = "持仓金额9000元说明盈利"
    with pytest.raises(ValueError, match="invalid_context_meaning"):
        summary._parse_output(json.dumps(bad), material, local)


def test_fact_source_must_be_cited_observation_from_same_product_and_kind():
    material, local = _material()
    good = _good(material)
    bad = deepcopy(good)
    bad["items"][0]["contexts"][0]["fact_source_id"] = "ev_unlisted"
    with pytest.raises(ValueError, match="invalid_fact_source"):
        summary._parse_output(json.dumps(bad), material, local)
    foreign = "ev_foreign"
    local["sources"][foreign] = {
        "id": foreign,
        "symbol": "SOXX",
        "text": "公开观察",
        "date": "2026-10-16",
        "evidence_type": "observation",
    }
    bad["items"][0]["contexts"][0]["fact_source_id"] = foreign
    with pytest.raises(ValueError, match="cross_product_citation"):
        summary._parse_output(json.dumps(bad), material, local)
    method = "ev_method"
    source = {
        "id": method,
        "symbol": "515880.SS",
        "text": "一般解释方法",
        "date": None,
        "evidence_type": "method",
    }
    material["products"][0]["context_slots"]["macro"]["sources"].append(source)
    local["sources"][method] = source
    bad = deepcopy(good)
    bad["items"][0]["contexts"][0]["citation_ids"].append(method)
    bad["items"][0]["contexts"][0]["fact_source_id"] = method
    with pytest.raises(ValueError, match="invalid_fact_source"):
        summary._parse_output(json.dumps(bad), material, local)


def test_fact_is_short_source_excerpt_and_full_original_remains_cited():
    material, local = _material()
    source = material["products"][0]["context_slots"]["macro"]["sources"][0]
    original = "截至2026-10-16，" + "利率观察背景" * 25 + "。"
    source["text"] = original
    local["sources"][source["id"]]["text"] = original
    _, rows = summary._parse_output(
        json.dumps(_good(material), ensure_ascii=False), material, local
    )
    context = rows[0]["contexts"][0]
    assert len(context["fact"]) <= 80 and context["fact"].endswith("…")
    assert original.startswith(context["fact"][:-1])
    assert context["sources"][0]["text"] == original


def test_model_cannot_replace_or_expand_fixed_technical_citation():
    material, local = _material()
    bad = _good(material)
    bad["items"][0]["citation_ids"] += ["x1", "x2", "x3", "x4"]
    _, rows = summary._parse_output(json.dumps(bad), material, local)
    assert [source["id"] for source in rows[0]["sources"]] == [material["recent"][0]["source_id"]]
    assert len(rows[0]["sources"]) == 1


def test_overview_cannot_renew_an_older_event_with_relative_time():
    material, local = _material()
    value = _good(material)
    value["overview"] = "今天公布的行业报告值得关注"
    with pytest.raises(ValueError, match="relative_event_date"):
        summary._parse_output(json.dumps(value), material, local)


def test_context_with_no_sources_is_service_marked_missing():
    material, local = _material()
    missing = deepcopy(material)
    missing["products"][0]["context_slots"]["news"]["sources"] = []
    good = _good(material)
    good["items"][0]["contexts"][2] = {
        "kind": "news",
        "impact": "unknown",
        "fact_source_id": None,
        "meaning": "",
        "counterpoint": "",
        "citation_ids": [],
    }
    _, items = summary._parse_output(json.dumps(good, ensure_ascii=False), missing, local)
    assert items[0]["contexts"][2]["status"] == "missing"
    assert items[0]["contexts"][2]["sources"] == []
    bad = deepcopy(good)
    bad["items"][0]["contexts"][2]["meaning"] = "最新新闻利好"
    with pytest.raises(ValueError, match="invented_context"):
        summary._parse_output(json.dumps(bad, ensure_ascii=False), missing, local)


def test_explicit_start_reuses_complete_and_failed_without_extra_model_call(tmp_path, monkeypatch):
    db_path = str(tmp_path / "saved.sqlite")
    material, local = _material()
    calls = []

    def model(prompt, *, system_prompt):
        calls.append(json.loads(prompt))
        return {
            "text": json.dumps(
                {
                    "overview": "通信ETF有近期技术事件",
                    "items": _good(material)["items"],
                },
                ensure_ascii=False,
            ),
            "model": "test-double",
            "attempts": 1,
            "usage": {"input_tokens": 5},
        }

    monkeypatch.setattr(summary, "call_model", model)
    assert summary.read(db_path, "orb_saved", material)["status"] == "missing"
    first = summary.start(db_path, "orb_saved", material, local)
    assert first["status"] == "running"
    for _ in range(100):
        done = summary.read(db_path, "orb_saved", material)
        if done["status"] == "complete":
            break
        time.sleep(0.01)
    assert done["status"] == "complete"
    assert done["model"] == "test-double"
    assert done["attempts"] == 1
    assert done["items"][0]["sources"][0]["source"] == "本系统近期技术事件"
    assert "raw_attempt" not in done and "input_json" not in done
    with summary.connect(db_path) as conn:
        stored = conn.execute(
            "SELECT input_json,raw_attempt FROM opportunity_summaries WHERE summary_id=?",
            (done["summary_id"],),
        ).fetchone()
        assert json.loads(stored["input_json"])["prompt_version"] == summary._PROMPT_VERSION
        assert json.loads(stored["raw_attempt"])["overview"] == "通信ETF有近期技术事件"
    assert summary.start(db_path, "orb_saved", material, local)["reused"] is True
    assert summary.read(db_path, "orb_other", material)["status"] == "missing"
    assert len(calls) == 1

    failed_material = deepcopy(material)
    failed_material["limitations"].append("新资料")
    monkeypatch.setattr(
        summary,
        "call_model",
        lambda *a, **kw: {"text": None, "error_code": "rate_limited", "attempts": 2},
    )
    summary.start(db_path, "orb_saved", failed_material, local)
    for _ in range(100):
        failed = summary.read(db_path, "orb_saved", failed_material)
        if failed["status"] == "failed":
            break
        time.sleep(0.01)
    assert failed["error"] == "rate_limited"
    assert summary.start(db_path, "orb_saved", failed_material, local)["status"] == "failed"


def test_expired_running_is_a_read_only_failure(tmp_path):
    db_path = str(tmp_path / "saved.sqlite")
    material, _ = _material()
    with summary.connect(db_path) as conn:
        summary._schema(conn)
        conn.execute(
            "INSERT INTO opportunity_summaries"
            "(summary_id,input_fingerprint,run_id,status,created_at,lease_until) "
            "VALUES (?,?,?,?,?,?)",
            (
                "ops_expired",
                summary._cache_key("orb_saved", material),
                "orb_saved",
                "running",
                "2020-01-01T00:00:00+00:00",
                "2020-01-01T00:01:00+00:00",
            ),
        )
    result = summary.read(db_path, "orb_saved", material)
    assert result["status"] == "failed" and result["error"] == "timeout"
    assert summary.start(db_path, "orb_saved", material, {})["status"] == "failed"


def test_summary_routes_do_not_prepare_or_fetch_and_get_does_not_write(tmp_path, monkeypatch):
    from lei_signal.api.routes import opportunity_reviews as route

    app = FastAPI()
    app.include_router(route.router)
    db_path = tmp_path / "routes.sqlite"
    app.state.plans_db_path = str(db_path)
    monkeypatch.setattr(route, "_saved_summary_board", lambda request, run_id: _board())
    snapshots = []

    def cached(request, symbol, *, cached_only, include_chart):
        assert cached_only is True and include_chart is False
        snapshots.append(symbol)
        return _snapshot()

    monkeypatch.setattr(route, "_technical_snapshot", cached)
    monkeypatch.setattr(route, "holding_market", lambda *a, **kw: pytest.fail("market fetch"))
    client = TestClient(app)
    run_id = _board()["run_id"]
    missing = client.get(f"/api/opportunity-reviews/runs/{run_id}/summary")
    assert missing.status_code == 200 and missing.json()["status"] == "missing"
    assert not db_path.exists()
    assert snapshots == ["515880.SS"]
    bad = client.get("/api/opportunity-reviews/runs/bad/summary")
    assert bad.status_code == 422


def test_waiting_signal_does_not_count_as_confirmed_buy():
    material, _ = summary._material(_board(), lambda symbol: _snapshot(status="waiting"))
    assert material["coverage"]["buy"] == 0
    assert material["coverage"]["waiting"] == 1


def test_saved_summary_board_uses_read_only_database(tmp_path, monkeypatch):
    import sqlite3
    from types import SimpleNamespace

    from lei_signal.api.routes import opportunity_reviews as route

    path = tmp_path / "original.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE marker (value TEXT)")
    before = path.read_bytes()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(plans_db_path=str(path))))

    def read(conn, run_id):
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("INSERT INTO marker VALUES ('unexpected')")
        return _board()

    monkeypatch.setattr(route.review, "get_run", read)
    assert route._saved_summary_board(request, _board()["run_id"])["status"] == "complete"
    assert path.read_bytes() == before
    _, registry = route._registry(request)
    registry["stopped"] = {
        "run_id": _board()["run_id"], "review_error": "保存占用后停止", "active_worker": False,
    }
    assert route._saved_summary_board(request, _board()["run_id"])["review_stopped"] is True
    registry["active"] = {"run_id": _board()["run_id"], "active_worker": True}
    assert not route._saved_summary_board(request, _board()["run_id"]).get("review_stopped")
    assert path.read_bytes() == before
    registry["active"]["active_worker"] = False
    registry["active"]["status"] = "complete"
    assert not route._saved_summary_board(request, _board()["run_id"]).get("review_stopped")


def test_news_without_publication_is_not_promoted_and_industry_reference_is_not_ownership():
    board = _board()
    for evidence in board["items"][0]["card"]["evidence"]:
        if evidence.get("id") == "news-one":
            evidence["published_at"] = None
    material, _ = summary._material(board, lambda symbol: _snapshot())
    assert material["products"][0]["context_slots"]["news"]["sources"] == []
    material, local = _material()
    for source in material["products"][0]["context_slots"]["news"]["sources"]:
        source["relevance"] = "industry_reference"
        local["sources"][source["id"]]["relevance"] = "industry_reference"
    value = _good(material)
    value["items"][0]["contexts"][2]["meaning"] = "ETF持有台积电，因此受益。"
    with pytest.raises(ValueError, match="industry_holding_unproven"):
        summary._parse_output(json.dumps(value, ensure_ascii=False), material, local)


def test_legacy_report_period_label_is_clarified_without_mutating_frozen_evidence():
    board = _board()
    evidence = next(e for e in board["items"][0]["card"]["evidence"] if e["id"] == "news-one")
    original = "2026年6月30日披露持仓：公司甲占净值15%。这些是报告期持仓。"
    evidence.update(text=original, report_date="2026-06-30", published_at="2026-08-31")
    material, _ = summary._material(board, lambda symbol: _snapshot(), source_path=Path("/none"))
    assert material["products"][0]["context_slots"]["news"]["sources"] == []
    material, _ = summary._material(
        board,
        lambda symbol: _snapshot(),
        source_path=Path("/none"),
        narrative_as_of=date(2026, 9, 2),
    )
    source = material["products"][0]["context_slots"]["news"]["sources"][0]
    assert source["text"].startswith("报告期截至2026年6月30日的持仓")
    assert source["published_at"] == "2026-08-31"
    assert source["report_date"] == "2026-06-30"
    assert board["items"][0]["card"]["evidence"][-1]["text"] == original


def test_stopped_review_keeps_pending_status_and_explicit_limitations():
    board = _board()
    board.update(status="pending", review_stopped=True)
    material, _ = summary._material(board, lambda symbol: _snapshot())
    assert material["review_status"] == "pending"
    assert material["review_stopped"] is True
    assert any("已停止且未完成" in text for text in material["limitations"])


def test_summary_accepts_only_verified_stop_not_pending_alone(monkeypatch):
    from types import SimpleNamespace

    from fastapi import HTTPException

    from lei_signal.api.routes import opportunity_reviews as route

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(plans_db_path=":memory:")))
    material = {"review_status": "pending", "review_stopped": False}
    monkeypatch.setattr(route, "_summary_input", lambda *args: (material, {}))
    calls = []
    monkeypatch.setattr(summary, "start", lambda *args: calls.append(args) or {"status": "running"})
    with pytest.raises(HTTPException) as error:
        route.post_summary(request, "orb_saved")
    assert error.value.status_code == 409 and not calls
    material["review_stopped"] = True
    assert route.post_summary(request, "orb_saved")["status"] == "running"
    assert len(calls) == 1



def test_compact_summary_binds_facts_and_rejects_model_rewriting():
    material, local = summary._material(_board(), lambda symbol: _snapshot(), compact=True)
    assert material["summary_mode"] == "focus_only"
    assert all(set(product) == {"symbol", "name"} for product in material["products"])
    assert "context_slots" not in json.dumps(material)
    source_id = material["recent"][0]["source_id"]
    payload = {
        "overview": "先核对近期技术事件，继续观察原有条件。",
        "items": [{"source_id": source_id}],
    }
    _, items = summary._parse_output(json.dumps(payload, ensure_ascii=False), material, local)
    assert items[0]["observation"] == local["recent"][source_id]["text"]
    assert items[0]["event_date"] == local["recent"][source_id]["event_date"]
    assert items[0]["contexts"] == []
    assert items[0]["sources"][0]["id"] == source_id
    payload["items"][0]["contexts"] = [{"kind": "news", "meaning": "无依据的消息"}]
    with pytest.raises(ValueError, match="unexpected_focus_fields"):
        summary._parse_output(json.dumps(payload, ensure_ascii=False), material, local)
    payload["items"] = [{"source_id": "foreign-product"}]
    with pytest.raises(ValueError, match="unsupported_focus"):
        summary._parse_output(json.dumps(payload, ensure_ascii=False), material, local)
    payload["items"] = [{"source_id": source_id}]
    payload["overview"] = "预计上涨9999%。"
    with pytest.raises(ValueError, match="unsupported_overview_number"):
        summary._parse_output(json.dumps(payload, ensure_ascii=False), material, local)


def test_compact_input_has_one_leading_event_per_product(monkeypatch):
    original = summary.build_recent_opportunities

    def with_two_events(*args, **kwargs):
        recent = original(*args, **kwargs)
        event = deepcopy(recent["items"][0])
        event.update(id="second-event", title="另一个已保存事件", status="active",
                     event_date="2026-10-15", age_bars=1)
        recent["items"].append(event)
        return recent

    monkeypatch.setattr(summary, "build_recent_opportunities", with_two_events)
    material, local = summary._material(_board(), lambda symbol: _snapshot(), compact=True)
    assert len(local["recent"]) == 2
    assert len(material["recent"]) == 1
    assert material["recent"][0]["event_date"] == "2026-10-16"
    kept = material["recent"][0]["source_id"]
    excluded = next(source_id for source_id in local["recent"] if source_id != kept)
    payload = {"overview": "核对原有条件。", "items": [{"source_id": excluded}]}
    with pytest.raises(ValueError, match="unsupported_focus"):
        summary._parse_output(json.dumps(payload, ensure_ascii=False), material, local)
