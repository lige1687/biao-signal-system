from datetime import UTC, datetime, timedelta

from lei_signal.fundamentals import observations, sources


def test_cn_observations_keep_fund_scope_and_fixed_historical_turnover(monkeypatch):
    start = datetime(2026, 8, 31, tzinfo=UTC).date()
    hist = {(start + timedelta(days=i)).isoformat():
            {"rzye_yi": 100.0 + i / 10, "buy_yi": 4.0 + i / 20}
            for i in range(21)}
    monkeypatch.setattr(sources, "fetch_margin_history", lambda _: hist)
    out = observations.build_observations("cn", lambda _key, fn: fn())
    by_id = {x["metric_id"]: x for x in out["items"]}
    assert by_id["margin_balance"]["value"] == 102.0
    assert by_id["margin_balance"]["change"] == 2.0
    assert "可能含基金" in by_id["margin_balance"]["universe"]
    turnover = by_id["stock_turnover"]
    assert turnover["value"] == 14108.03
    assert turnover["change"] == -24.63
    assert turnover["change_unit"] == "%"
    assert turnover["comparison_period"] == "相对此前20个完整交易日均值"
    assert turnover["observation_date"] == "2026-09-29"
    assert turnover["quality_status"] == "time_unverified"
    assert turnover["published_at"] is None and turnover["fetched_at"] is None
    assert turnover["observation_count"] == 21


def test_us_independent_failure_and_required_fields(monkeypatch, tmp_path):
    today = datetime.now(UTC).date().isoformat()
    monkeypatch.setattr(sources, "fetch_vix_history", lambda _: {today: 20.0})

    def fake_fred(sid, *, cosd):
        if sid == "DFII10":
            raise sources.FundamentalsSourceError("offline")
        return {today: 2.4}

    monkeypatch.setattr(sources, "_fetch_fred_series", fake_fred)
    monkeypatch.setenv("LEI_SENTIMENT_ROOT", str(tmp_path))
    out = observations.build_observations("us", lambda _key, fn: fn())
    by_id = {x["metric_id"]: x for x in out["items"]}
    assert by_id["vxn"]["value"] == 2.4
    assert by_id["real_yield_10y"]["value"] is None
    assert by_id["hy_oas"]["value"] == 2.4
    assert any("real_yield_10y" in x for x in out["errors"])
    required = {"metric_id", "label", "market", "universe", "value", "unit", "change",
                "comparison_period", "observation_date", "published_at",
                "publication_precision", "fetched_at", "source_name", "source_url",
                "source_access", "definition_version", "quality_status", "quality_reason",
                "history_start", "history_end", "observation_count", "valid_count",
                "eligible_count", "reading", "limitations", "evidence_refs"}
    assert all(required <= x.keys() for x in out["items"])


def test_old_auto_naaim_week_is_not_presented_as_latest(monkeypatch, tmp_path):
    (tmp_path / "naaim.csv").write_text(
        "survey_week,available_at,exposure_index,source,license_status,publication_delay_days\n"
        "2026-09-21,2026-09-24T07:00:00,98.59,auto:naaim.org,licensed,3\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LEI_SENTIMENT_ROOT", str(tmp_path))
    items, errors = [], []
    observations._surveys(items, errors, datetime.now(UTC).isoformat())
    naaim = next(x for x in items if x["metric_id"] == "naaim")
    assert naaim["value"] is None
    assert naaim["quality_status"] == "missing"
    assert "推测调查周" in naaim["quality_reason"]


def test_nan_source_does_not_break_other_source_or_json_route(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from lei_signal.api.routes import fundamentals
    from lei_signal.fundamentals.service import FundamentalsService

    today = datetime.now(UTC).date().isoformat()
    monkeypatch.setattr(sources, "fetch_vix_history", lambda _: {today: float("nan")})
    monkeypatch.setattr(sources, "_fetch_fred_series", lambda sid, *, cosd: {today: 2.4})
    monkeypatch.setenv("LEI_SENTIMENT_ROOT", str(tmp_path))
    app = FastAPI()
    app.state.fundamentals_service = FundamentalsService()
    app.include_router(fundamentals.router)
    response = TestClient(app).get("/api/fundamentals/observations?market=us")
    assert response.status_code == 200
    by_id = {item["metric_id"]: item for item in response.json()["items"]}
    assert by_id["vix"]["value"] is None
    assert by_id["vix"]["quality_status"] == "missing"
    assert by_id["vxn"]["value"] == 2.4


def test_survey_reference_uses_original_module_e_parameters_and_units(monkeypatch):
    from lei_signal.domain import rules_config

    class AlternativeLedger:
        def param(self, name):
            return {"aaii_extreme": [-0.11, 0.12], "naaim_extreme": [0.33, 1.04]}[name]

    monkeypatch.setattr(rules_config, "get_rule", lambda rule_id: AlternativeLedger())
    notes = observations._survey_reference_notes()
    assert "≤-11或≥12个百分点" in notes["aaii"]
    assert "≤33%或≥104%" in notes["naaim"]
    assert "尚未证明" in notes["aaii"]
