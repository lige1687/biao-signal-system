from copy import deepcopy
from pathlib import Path

from lei_signal.factor_workbench import intake


def test_new_reports_are_pending_and_do_not_promote_existing_research(monkeypatch):
    progress = {"reviewedAt": "2026-10-24T09:00:00+08:00", "sources": [{"path": "docs/experiments/known-2026-10-25.md"}],
                "cases": [{"id": "factor@1", "conclusion": {"state": "unsupported"}}]}
    before = deepcopy(progress)
    reports = [{"name": f"docs/experiments/{name}.md", "title": name, "category": "模块与信号", "date": "2099-01-01"}
               for name in ["known-2026-10-25", "new-2026-10-25", "old-2026-10-23", "undated", "same-day-2026-10-24"]]
    monkeypatch.setattr(intake, "scan_reports", lambda _: reports)
    result = intake.extend_intake(Path("."), progress)
    assert result["cases"] == before["cases"]
    assert progress == before
    assert [x["title"] for x in result["intake"]["items"]] == ["new-2026-10-25", "same-day-2026-10-24"]
    assert all(x["status"] == "pending_review" for x in result["intake"]["items"])
    assert result["intake"]["items"][0]["date"] == "2026-10-25"
