"""行业板块趋势 API 测试（P2.2）：TestClient + 磁盘假快照，零网络。

覆盖：/trend（命中/404/level 过滤）、/{code}/history（days 钳制）、
/{code}/members（命中/404/行情降级/in_kline_cache）。
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.routes import sectors as sectors_route
from lei_signal.market_context import sector_trend as st

SNAP = {
    "as_of": "2026-08-14 16:45",
    "date": "2026-08-14",
    "trading_day": "2026-08-14",
    "bench": {"all_equal_close": 1000.0, "hs300_close": 4000.0},
    "boards": [
        {
            "code": "BK0001", "name": "行业一", "level": 1, "parent": None,
            "aliases": [], "member_count": 5, "hit_count": 5, "stage": "markup",
            "stage_basis": ["价格 > SMA60", "SMA60 斜率向上", "RS 强于等权基准"],
            "rs_pctile": 80.0, "rs_pctile_delta_20": 5.0, "rs_chg_20": 10.0,
            "rs_chg_60": 20.0, "rs_above_ma20": True, "b20": 50.0, "b50": 60.0,
            "b200": None, "nh60": 10.0, "breadth_divergence": False,
            "signal_color": "green", "signal_color_cn": "绿", "ema20_slope_pct": 0.5,
            "long_trend_cn": "多头", "macd_status": "多头扩散",
            "macd_label_cn": "红柱扩张", "macd_detail_cn": "DIF>0 且柱扩张",
            "macd_dimension": "trend", "alignment_cn": "多头排列", "close": 1100.0,
            "pct_change": 1.2, "pe_ttm": 20.0, "main_net_inflow_yi": 3.5,
            "up_count": 30, "down_count": 10, "total_mv_yi": 5000.0,
            "provenance": "research_proxy",
        },
        {
            "code": "BK0002", "name": "子行业", "level": 2, "parent": "BK0001",
            "aliases": [], "member_count": 3, "hit_count": 3, "stage": "accumulation",
            "stage_basis": ["RS 强于等权基准", "EMA20 斜率 ≥ 0", "价格 ≤ SMA60"],
            "rs_pctile": 40.0, "rs_pctile_delta_20": -2.0, "rs_chg_20": -3.0,
            "rs_chg_60": 5.0, "rs_above_ma20": True, "b20": 33.0, "b50": 40.0,
            "b200": None, "nh60": 5.0, "breadth_divergence": False,
            "signal_color": "gray", "signal_color_cn": "灰", "ema20_slope_pct": 0.1,
            "long_trend_cn": "震荡", "macd_status": "空头收敛", "macd_label_cn": "绿柱收敛",
            "macd_detail_cn": "DIF<0 但柱收敛", "macd_dimension": "trend",
            "alignment_cn": "均线纠结", "close": 980.0, "pct_change": -0.5,
            "pe_ttm": 15.0, "main_net_inflow_yi": -1.0, "up_count": 10,
            "down_count": 20, "total_mv_yi": 2000.0, "provenance": "research_proxy",
        },
    ],
    "warnings": [], "errors": [],
    "research_proxy_note": "板块趋势判定为研究代理（research_proxy）……",
}

HISTORY = [
    {"date": "2026-08-13", "boards": {"BK0001": {"stage": "markup", "rs_pctile": 75.0, "b50": 58.0, "close": 1090.0}}},
    {"date": "2026-08-14", "boards": {"BK0001": {"stage": "markup", "rs_pctile": 80.0, "b50": 60.0, "close": 1100.0}}},
]

MEMBERS = {
    "as_of": "2026-08-14 16:45", "date": "2026-08-14",
    "boards": {
        "BK0001": {"name": "行业一", "members": ["sh600000", "sh600001", "sh600002"]},
        "BK0002": {"name": "子行业", "members": ["sh600000"]},
    },
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(st, "ROOT", tmp_path)
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    # 行情取数降级：成员行情接口不可达时返回空（不阻断 members 端点）
    import lei_signal.fundamentals.sources as sources

    def _boom(*a, **k):
        raise sources.FundamentalsSourceError("网络不可达（测试）")

    monkeypatch.setattr(sources, "_get_json", _boom)

    (tmp_path / "sector_trend_snapshot.json").write_text(
        json.dumps(SNAP, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "sector_trend_history.json").write_text(
        json.dumps(HISTORY, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "sector_members.json").write_text(
        json.dumps(MEMBERS, ensure_ascii=False), encoding="utf-8"
    )
    app = create_app()
    return TestClient(app)


def test_trend_ok(client):
    r = client.get("/api/sectors/trend")
    assert r.status_code == 200
    body = r.json()
    assert body["date"] == "2026-08-14"
    assert len(body["boards"]) == 2
    assert "research_proxy_note" in body
    # 关键红线：响应含 provenance 研究代理声明
    assert all(b["provenance"] == "research_proxy" for b in body["boards"])


def test_trend_level_filter(client):
    r = client.get("/api/sectors/trend?level=l2")
    assert r.status_code == 200
    codes = [b["code"] for b in r.json()["boards"]]
    assert codes == ["BK0002"]


def test_trend_not_precomputed(tmp_path, monkeypatch):
    monkeypatch.setattr(st, "ROOT", tmp_path)
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    app = create_app()
    c = TestClient(app)
    r = c.get("/api/sectors/trend")
    assert r.status_code == 404
    assert "尚未运行预计算" in r.json()["detail"]


def test_history_days_clamp(client):
    # days 上限钳制到 1000，不应报错
    r = client.get("/api/sectors/BK0001/history?days=99999")
    assert r.status_code == 200
    pts = r.json()["points"]
    assert len(pts) == 2
    assert pts[0]["date"] == "2026-08-13"
    assert pts[0]["close"] == 1090.0
    assert set(pts[0].keys()) == {"date", "close", "b50", "rs_pctile", "stage"}


def test_members_ok_and_quote_degrade(client):
    r = client.get("/api/sectors/BK0001/members?limit=50")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == "BK0001"
    assert len(body["members"]) == 3
    # 行情取数降级 → pct_change / market_value_yi 为 null
    assert body["members"][0]["pct_change"] is None
    assert body["members"][0]["market_value_yi"] is None
    # 无 K线缓存 → in_kline_cache 全 False
    assert all(m["in_kline_cache"] is False for m in body["members"])


def test_members_404_unknown(client):
    r = client.get("/api/sectors/BK9999/members")
    assert r.status_code == 404
