import json
from pathlib import Path

import pytest

from lei_signal.fundamentals import sources, turnover_snapshot


def _snapshot(tmp_path: Path) -> tuple[dict, Path]:
    data = json.loads(turnover_snapshot.SNAPSHOT_PATH.read_text())
    path = tmp_path / "stock-turnover.json"
    path.write_text(json.dumps(data, ensure_ascii=False))
    return data, path


def test_fixed_snapshot_excludes_target_from_prior_mean():
    item = turnover_snapshot.load_turnover_snapshot()
    assert item["value"] == 14108.03
    assert item["change"] == -24.63
    assert item["observation_date"] == "2026-09-29"
    assert item["history_start"] == "2026-08-31"
    assert item["history_end"] == "2026-09-29"
    assert item["published_at"] is None and item["fetched_at"] is None
    assert len(item["evidence_refs"]) == 4


@pytest.mark.parametrize("damage", [
    lambda data: data["daily"].pop(0),
    lambda data: data["daily"].__setitem__(1, data["daily"][0].copy()),
    lambda data: data["daily"][-1].__setitem__("sse_a_yi", "NaN"),
    lambda data: data["daily"][-1].__setitem__("sse_a_yi", "9999.99"),
    lambda data: data["daily"][-1].__setitem__("sse_raw_sha256", "0" * 64),
    lambda data: data.__setitem__("observation_date", "2026-09-30"),
])
def test_damaged_or_new_date_snapshot_is_rejected(tmp_path, damage):
    data, path = _snapshot(tmp_path)
    damage(data)
    path.write_text(json.dumps(data, ensure_ascii=False))
    with pytest.raises(sources.FundamentalsSourceError):
        turnover_snapshot.load_turnover_snapshot(path)


@pytest.mark.parametrize("content", ["{invalid", "{}", '{"daily": NaN}'])
def test_broken_json_is_rejected(tmp_path, content):
    path = tmp_path / "bad.json"
    path.write_text(content)
    with pytest.raises(sources.FundamentalsSourceError):
        turnover_snapshot.load_turnover_snapshot(path)


def test_missing_snapshot_only_downgrades_turnover(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from lei_signal.api.routes import fundamentals
    from lei_signal.fundamentals.service import FundamentalsService

    monkeypatch.setattr(turnover_snapshot, "SNAPSHOT_PATH", tmp_path / "absent.json")
    monkeypatch.setattr(sources, "fetch_margin_history", lambda _: {
        "2026-09-29": {"rzye_yi": 100.0, "buy_yi": 4.0},
    })
    app = FastAPI()
    app.state.fundamentals_service = FundamentalsService()
    app.include_router(fundamentals.router)
    response = TestClient(app).get("/api/fundamentals/observations?market=cn")
    assert response.status_code == 200
    output = response.json()
    items = {item["metric_id"]: item for item in output["items"]}
    assert items["margin_buy"]["value"] == 4.0
    assert items["stock_turnover"]["value"] is None
    assert items["stock_turnover"]["quality_status"] == "missing"
    assert any(error.startswith("stock_turnover:") for error in output["errors"])
