"""Skill entry behavior: bounded output, GET-only resume, no duplicate generation."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / ".agents/skills/lei-system-chat/scripts/query.py"
spec = importlib.util.spec_from_file_location("lei_skill_query", SCRIPT)
query = importlib.util.module_from_spec(spec)
spec.loader.exec_module(query)

RUN = "orb_" + "a" * 64
PREP = "opr_" + "b" * 32


class FakeClient:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    def call(self, path, method="GET"):
        self.calls.append((method, path))
        return next(self.replies)


def args(*words):
    return query.parser().parse_args(words)


def test_prepare_failure_keeps_ids_and_does_not_start_another_run():
    client = FakeClient(
        [
            {"status": "ok"},
            {"run_id": RUN, "status": "pending", "preparation_id": PREP, "items": []},
            {"id": PREP, "status": "failed", "error": "SQLITE_BUSY", "run_id": None},
        ]
    )
    result = query.opportunity_query(client, args("opportunities", "--generate"))
    assert result["generation_complete"] is False
    assert result["errors"] == {"preparation": "SQLITE_BUSY"}
    assert result["resume"] == {"preparation_id": PREP, "run_id": RUN}
    assert [method for method, _ in client.calls].count("POST") == 1
    assert len(client.calls) == 3


def test_resume_uses_prepared_run_and_never_posts():
    prepared_run = "orb_" + "c" * 64
    client = FakeClient(
        [
            {"id": PREP, "status": "complete", "run_id": prepared_run},
            {"run_id": prepared_run, "status": "partial", "items": []},
        ]
    )
    result = query.opportunity_query(client, args("opportunities", "--preparation-id", PREP))
    assert client.calls == [
        ("GET", "/api/opportunity-reviews/preparations/" + PREP),
        ("GET", "/api/opportunity-reviews/runs/" + prepared_run),
    ]
    assert result["review_terminal"] is True
    assert result["generation_complete"] is False


def test_pending_returns_immediately_without_retry():
    client = FakeClient([{"run_id": RUN, "status": "pending", "items": []}])
    result = query.opportunity_query(client, args("opportunities", "--run-id", RUN))
    assert len(client.calls) == 1
    assert result["review_terminal"] is False
    assert result["generation_complete"] is False


def test_complete_is_read_back_not_assumed_from_ensure():
    client = FakeClient(
        [
            {"status": "ok"},
            {"run_id": RUN, "status": "pending", "items": []},
            {"run_id": RUN, "status": "complete", "items": []},
        ]
    )
    result = query.opportunity_query(client, args("opportunities", "--generate"))
    assert result["generation_complete"] is True
    assert client.calls[-1] == ("GET", "/api/opportunity-reviews/runs/" + RUN)


def test_no_healthy_service_means_no_post():
    client = FakeClient([{"status": "unavailable"}])
    result = query.opportunity_query(client, args("opportunities", "--generate"))
    assert result["available"] is False
    assert len(client.calls) == 1


def test_no_run_after_complete_preparation_is_failure():
    result = query.opportunity_query(
        FakeClient([{"status": "complete", "run_id": None}]),
        args("opportunities", "--preparation-id", PREP),
    )
    assert result["available"] is False
    assert result["errors"]["run"]


def test_compaction_preserves_sources_errors_dates_and_reports_omissions():
    source = {"packet_date": "2026-10-08", "source_ref": "https://example.com/source"}
    value = {
        "sources": source,
        "errors": {"source": "stale"},
        "limitations": ["old"] * 12,
        "data": {
            "items": [
                {
                    "name": "甲基金",
                    "date": "2026-10-08",
                    "content": "x" * 100000,
                    "video_content": {"segments": []},
                }
            ]
            * 8
        },
    }
    omitted = []
    result = query.compact(value, 2, omitted=omitted)
    assert len(result["data"]["items"]) == 2
    assert result["sources"] == source
    assert result["errors"] == {"source": "stale"}
    assert len(result["limitations"]) == 12
    assert result["data"]["items"][0]["date"] == "2026-10-08"
    assert "content" not in result["data"]["items"][0]
    assert any(x.get("total") == 8 for x in omitted)
    assert any(x["path"].endswith("content") for x in omitted)


def test_filtered_board_keeps_batch_counts_and_conflicting_roles():
    rows = []
    for symbol, status in (("515880.SS", "failed"), ("XLK", "complete")):
        rows.append(
            {
                "card": {
                    "subject": {"id": symbol, "name": symbol},
                    "intent": "sell",
                    "evidence": [
                        {"role": "support", "text": "上涨"},
                        {"role": "opposition", "text": "下跌"},
                    ],
                },
                "audit": {"status": status},
            }
        )
    result = query.compact_board({"items": rows}, args("opportunities", "--symbol", "515880.SS"))
    assert result["matching_cards"] == 1
    assert result["audit_counts"] == {"failed": 1, "complete": 1}
    assert set(result["items"][0]["evidence_by_role"]) == {"support", "opposition"}


def test_watchlist_names_use_exact_identity_and_preserve_unresolved_rows():
    rows = [
        {"symbol": "515880.SS", "display_name": None},
        {"symbol": "KNOWN.SS", "display_name": "自选名称"},
        {"symbol": "UNKNOWN.SS", "display_name": "UNKNOWN"},
    ]
    result = query.named_watchlist(
        {"items": rows, "count": 3}, {"515880.SS": "通信ETF", "KNOWN.SS": "目录名称"}
    )
    assert [r["display_name"] for r in result["items"]] == ["通信ETF", "自选名称", "名称待核对"]
    assert result["name_counts"] == {"local_product_catalog": 1, "watchlist": 1, "unresolved": 1}
    assert result["items"][2]["symbol"] == "UNKNOWN.SS"
    assert rows[0]["display_name"] is None


@pytest.mark.parametrize(
    "words",
    [
        ("portfolio", "--generate"),
        ("opportunities", "--generate", "--run-id", RUN),
        ("opportunities", "--run-id", "../../plans"),
        ("technical", "--symbol", "XLK/../../plans"),
        ("technical",),
        ("holding-market",),
        ("portfolio", "--code", "001513/"),
        ("brief", "--symbol", "515880.SS"),
        ("brief", "--run-id", RUN),
        ("brief", "--run-id", RUN, "--symbol", "515880.SS", "--holding-id", "5045587e5cff"),
    ],
)
def test_invalid_selection_cannot_call_api(words):
    with pytest.raises(ValueError):
        query.validate(args(*words))


def test_transport_rejects_unlisted_and_financial_write_paths():
    class NoTransport:
        base_url = "http://127.0.0.1:8000"

    client = query.Client(NoTransport())
    for path, method in (
        ("/api/plans", "POST"),
        ("/api/health", "POST"),
        ("/api/opportunity-reviews/ensure?retry_failed=true", "POST"),
    ):
        with pytest.raises(ValueError):
            client.call(path, method)


def test_brief_transport_only_reads_exact_selected_product():
    import io
    from types import SimpleNamespace

    calls = []

    class Opener:
        def open(self, request, timeout):
            calls.append((request.get_method(), request.full_url))
            return io.BytesIO(b'{"schema_version":"opportunity-brief/1"}')

    client = query.Client(SimpleNamespace(base_url="http://127.0.0.1:8000", _opener=Opener()))
    path = "/api/opportunity-reviews/runs/" + RUN + "/brief?subject_key=symbol%3A515880.SS"
    assert client.call(path)["schema_version"] == "opportunity-brief/1"
    assert calls == [("GET", "http://127.0.0.1:8000" + path)]
    for invalid in (path + "&refresh=true", path + "/../../plans"):
        with pytest.raises(ValueError):
            client.call(invalid)


def test_review_start_error_stops_pending_poll_without_second_ensure(monkeypatch):
    client = FakeClient(
        [
            {"status": "ok"},
            {"run_id": RUN, "status": "pending", "preparation_id": PREP},
            {"id": PREP, "status": "complete", "run_id": RUN},
            {"run_id": RUN, "status": "pending", "items": [], "review_error": "模型启动失败"},
        ]
    )
    monkeypatch.setattr(query.time, "sleep", lambda *_: pytest.fail("must stop polling"))
    result = query.opportunity_query(
        client, args("opportunities", "--generate", "--wait-seconds", "45")
    )
    assert result["generation_complete"] is False
    assert result["errors"] == {"review": "模型启动失败"}
    assert len(client.calls) == 4
    assert [method for method, _ in client.calls].count("POST") == 1


def test_terminal_run_stops_before_wait_deadline(monkeypatch):
    client = FakeClient([{"run_id": RUN, "status": "complete", "items": []}])
    monkeypatch.setattr(query.time, "sleep", lambda *_: pytest.fail("terminal run must not wait"))
    result = query.opportunity_query(
        client, args("opportunities", "--run-id", RUN, "--wait-seconds", "45")
    )
    assert result["generation_complete"] is True
    assert len(client.calls) == 1
