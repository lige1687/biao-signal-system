"""基本面参考层：service 降级与缓存行为的单元测试（不打真实网络）。"""
from __future__ import annotations

import pytest

from lei_signal.fundamentals import sources
from lei_signal.fundamentals.service import FundamentalsService


def _board(code: str = "BK0475") -> dict:
    return {
        "code": code,
        "name": "银行Ⅱ",
        "latest": 100.0,
        "pct_change": 1.5,
        "turnover_rate": 0.8,
        "total_mv_yi": 1000.0,
        "main_net_inflow_yi": 2.5,
        "main_net_inflow_pct": 3.0,
        "up_count": 30,
        "down_count": 5,
    }


def _macro(key: str) -> dict:
    return {"key": key, "name_cn": key.upper(), "period": "2026年07月份", "value": 50.0, "yoy": None, "note_cn": ""}


def test_overview_assembles_macro_and_boards(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources, "fetch_industry_boards", lambda: [_board()])
    monkeypatch.setattr(sources, "fetch_pmi", lambda: _macro("pmi"))
    monkeypatch.setattr(sources, "fetch_cpi", lambda: _macro("cpi"))
    monkeypatch.setattr(sources, "fetch_ppi", lambda: _macro("ppi"))

    result = FundamentalsService().overview()

    assert result["board_count"] == 1
    assert [m["key"] for m in result["macro"]] == ["pmi", "cpi", "ppi"]
    assert result["errors"] == []
    assert "参考层" in result["disclaimer_cn"]


def test_overview_degrades_when_one_source_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> list[dict]:
        raise sources.FundamentalsSourceError("timeout")

    monkeypatch.setattr(sources, "fetch_industry_boards", boom)
    monkeypatch.setattr(sources, "fetch_pmi", lambda: _macro("pmi"))
    monkeypatch.setattr(sources, "fetch_cpi", boom)
    monkeypatch.setattr(sources, "fetch_ppi", lambda: _macro("ppi"))

    result = FundamentalsService().overview()

    # 板块挂了 → 空列表但页面其余部分照常；CPI 挂了 → 其余两个宏观指标保留。
    assert result["boards"] == []
    assert [m["key"] for m in result["macro"]] == ["pmi", "ppi"]
    assert len(result["errors"]) == 2


def test_overview_uses_cache_within_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def fetch() -> list[dict]:
        calls["n"] += 1
        return [_board()]

    monkeypatch.setattr(sources, "fetch_industry_boards", fetch)
    monkeypatch.setattr(sources, "fetch_pmi", lambda: _macro("pmi"))
    monkeypatch.setattr(sources, "fetch_cpi", lambda: _macro("cpi"))
    monkeypatch.setattr(sources, "fetch_ppi", lambda: _macro("ppi"))

    svc = FundamentalsService()
    svc.overview()
    svc.overview()
    assert calls["n"] == 1  # 第二次命中缓存

    svc.overview(refresh=True)
    assert calls["n"] == 2  # refresh 强制重拉


def test_industry_flow_clamps_days(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, int] = {}

    def fetch(code: str, *, days: int) -> list[dict]:
        seen["days"] = days
        return [{"date": "2026-08-07", "main_yi": -1.0}]

    monkeypatch.setattr(sources, "fetch_industry_flow", fetch)

    result = FundamentalsService().industry_flow("BK0475", days=500)
    assert seen["days"] == 60  # 上限钳制
    assert result["points"][0]["date"] == "2026-08-07"
