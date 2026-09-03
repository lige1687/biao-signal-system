"""添加目录与符号解析统一化：/api/sectors 四组清单 + 中证指数登记。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lei_signal.api import catalog, config
from lei_signal.api.app import create_app
from lei_signal.api.services import AnalysisService


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    """仅服务 /api/sectors 与 resolve：分析函数注入假实现，目录拉取打桩。"""
    monkeypatch.setattr(
        catalog,
        "concept_boards",
        lambda **_: [
            {"code": "BK1128", "name": "CPO概念", "symbol": "BK1128"},
            {"code": "BK1137", "name": "存储芯片", "symbol": "BK1137"},
        ],
    )
    service = AnalysisService(
        analyze_fn=lambda symbol, **_: pytest.fail("本测试不应触发分析"),
        sqlite_path=str(tmp_path / "lab.db"),
        ttl_seconds=900,
    )
    app = create_app(analysis_service=service)
    app.state.watchlist_db_path = str(tmp_path / "lab.db")
    return TestClient(app)


def test_sectors_catalog_returns_four_groups(client: TestClient) -> None:
    resp = client.get("/api/sectors")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data) == {"sectors", "indices", "us_etfs", "concepts"}

    ths = {item["symbol"]: item["name"] for item in data["sectors"]}
    assert ths["TH881129"] == "通信设备"

    indices = {item["symbol"]: item["name"] for item in data["indices"]}
    assert indices["931160.SS"] == "通信设备（中证）"
    assert indices["000905.SS"] == "中证500"

    concepts = {item["symbol"]: item["name"] for item in data["concepts"]}
    assert concepts["BK1128"] == "CPO概念"

    assert any(item["symbol"] == "QQQ" for item in data["us_etfs"])


def test_concept_boards_degrades_to_empty_on_source_error(monkeypatch) -> None:
    """东财清单拉取失败必须降级为空列表，不能把对话框目录整个打挂。"""
    from lei_signal.fundamentals import sources

    def _boom() -> list[dict[str, str]]:
        raise sources.FundamentalsSourceError("东财不可达")

    monkeypatch.setattr(catalog, "_fetch_concept_boards", _boom)
    assert catalog.concept_boards(refresh=True) == []


def test_strategy_indices_are_in_index_overrides() -> None:
    """策略指数必须进显示覆盖表：加自选后直接显示中文名与「A股」，而非「沪市」。"""
    override = config.INDEX_OVERRIDES["931160.SS"]
    assert override.display_name == "通信设备（中证）"
    assert override.market_cn == "A股"
    assert "000905.SS" in config.INDEX_OVERRIDES
    # 大盘指数覆盖仍在
    assert config.INDEX_OVERRIDES["000001.SS"].display_name == "上证指数"


def test_resolve_reports_csi_index_with_override(client: TestClient) -> None:
    """/api/sectors 登记的中证指数在 resolve 里有中文名（probe=false 不发网络请求）。"""
    resp = client.get("/api/symbols/resolve", params={"q": "931160.CSI"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "931160.SS"
    assert data["display_name"] == "通信设备（中证）"
    assert data["market_cn"] == "A股"
