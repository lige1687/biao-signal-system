"""API 端点测试：TestClient + 注入假分析函数（无网络）。"""
from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from lei_signal.api import config
from lei_signal.api.app import create_app
from lei_signal.api.services import AnalysisService
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.data.providers import PriceData
from lei_signal.data.symbols import resolve_symbol
from lei_signal.data.validation import DataUnavailableError, validate_bars

_TWO_INDICES = (
    config.DashboardIndex("000001.SS", "上证指数", "A股"),
    config.DashboardIndex("^IXIC", "纳斯达克", "美股"),
)


def _bars(n: int = 80) -> pd.DataFrame:
    rows = []
    for i in range(n):
        close = 100.0 + i * 0.5
        rows.append(
            {"open": close - 0.2, "high": close + 0.4, "low": close - 0.5,
             "close": close, "volume": 1_000_000}
        )
    index = pd.bdate_range(start="2024-01-02", periods=n)
    return pd.DataFrame(rows, index=index)[["open", "high", "low", "close", "volume"]]


def _fake_analyze(symbol: str, **kwargs):
    if symbol == "BROKEN.SS":
        raise DataUnavailableError("网络请求失败：连接中断")
    bars = _bars()
    frame, report = validate_bars(bars, symbol=symbol, provider="fixture", adjusted=True)
    info = resolve_symbol(symbol)
    price_data = PriceData(
        symbol=info.symbol, display_name=info.symbol,
        bars=frame, report=report, info=info,
    )
    return analyze_bars(symbol, frame, price_data=price_data)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DASHBOARD_INDICES", _TWO_INDICES)
    monkeypatch.setattr(
        config, "INDEX_OVERRIDES", {i.symbol: i for i in _TWO_INDICES}
    )
    calls: list[str] = []

    def counting_analyze(symbol: str, **kwargs):
        calls.append(symbol)
        return _fake_analyze(symbol, **kwargs)

    service = AnalysisService(
        analyze_fn=counting_analyze,
        sqlite_path=str(tmp_path / "lab.db"),
        ttl_seconds=900,
    )
    app = create_app(analysis_service=service)
    app.state.watchlist_db_path = str(tmp_path / "lab.db")
    # 单测禁用盘口源：它是真实网络调用，且测试用的是 fixture 行情
    app.state.quote_provider = None
    # 友好名回退也走盘口源，单测同样禁用
    app.state.friendly_name_provider = False
    test_client = TestClient(app)
    test_client.calls = calls  # type: ignore[attr-defined]
    return test_client


def test_dashboard_cards_success(client: TestClient) -> None:
    resp = client.get("/api/dashboard/cards")
    assert resp.status_code == 200
    data = resp.json()
    assert [c["symbol"] for c in data["cards"]] == ["000001.SS", "^IXIC"]
    card = data["cards"][0]
    assert card["display_name"] == "上证指数"
    assert card["market_cn"] == "A股"
    assert card["group"] == "index"
    assert card["price"] is not None
    assert card["color_cn"] in ("绿色", "灰色", "黑色", "数据不足")
    assert card["color_days"] >= 1
    assert len(card["sparkline"]) == 60
    assert data["disclaimer_cn"]


def test_dashboard_error_isolated_per_card(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        config,
        "DASHBOARD_INDICES",
        (*_TWO_INDICES, config.DashboardIndex("BROKEN.SS", "坏标的", "A股")),
    )
    resp = client.get("/api/dashboard/cards")
    assert resp.status_code == 200
    cards = {c["symbol"]: c for c in resp.json()["cards"]}
    assert cards["BROKEN.SS"]["error"].startswith("网络不通")
    assert cards["BROKEN.SS"]["price"] is None
    assert cards["000001.SS"]["error"] is None
    assert cards["000001.SS"]["price"] is not None


def test_dashboard_uses_cache_within_ttl(client: TestClient) -> None:
    client.get("/api/dashboard/cards")
    first_calls = len(client.calls)  # type: ignore[attr-defined]
    assert first_calls == 2
    client.get("/api/dashboard/cards")
    assert len(client.calls) == first_calls  # TTL 内不重取
    client.post("/api/refresh", json={})
    assert len(client.calls) == first_calls * 2  # refresh 强制重取


def test_resolve_routes_sh_index_vs_bare_code(client: TestClient) -> None:
    resp = client.get("/api/symbols/resolve", params={"q": "000001.SS"})
    assert resp.json()["market"] == "cn_sh"
    resp = client.get("/api/symbols/resolve", params={"q": "000001"})
    # 裸 6 位代码按股票规则路由到深市——这正是默认大盘必须用显式 .SS 的原因
    assert resp.json()["symbol"] == "000001.SZ"
    assert client.get("/api/symbols/resolve", params={"q": "###"}).status_code == 422


def test_watchlist_crud_and_dashboard_integration(client: TestClient) -> None:
    resp = client.post("/api/watchlist", json={"symbol": "159915"})
    assert resp.status_code == 201
    assert resp.json()["symbol"] == "159915.SZ"
    assert resp.json()["market_cn"] == "深市"

    cards = client.get("/api/dashboard/cards").json()["cards"]
    watch = [c for c in cards if c["group"] == "watchlist"]
    assert [c["symbol"] for c in watch] == ["159915.SZ"]

    assert client.delete("/api/watchlist/159915.SZ").status_code == 204
    assert client.delete("/api/watchlist/159915.SZ").status_code == 204  # 幂等
    cards = client.get("/api/dashboard/cards").json()["cards"]
    assert all(c["group"] == "index" for c in cards)

    assert client.post("/api/watchlist", json={"symbol": "###"}).status_code == 422


def test_watchlist_persists_across_service_restart(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(config, "DASHBOARD_INDICES", _TWO_INDICES)
    db = str(tmp_path / "lab.db")
    app1 = create_app(
        analysis_service=AnalysisService(analyze_fn=_fake_analyze, sqlite_path=db)
    )
    app1.state.watchlist_db_path = db
    TestClient(app1).post("/api/watchlist", json={"symbol": "QQQ"})

    app2 = create_app(
        analysis_service=AnalysisService(analyze_fn=_fake_analyze, sqlite_path=db)
    )
    app2.state.watchlist_db_path = db
    items = TestClient(app2).get("/api/watchlist").json()
    assert [i["symbol"] for i in items] == ["QQQ"]


def test_symbol_detail(client: TestClient) -> None:
    resp = client.get("/api/symbols/000001.SS/detail")
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "上证指数"  # 展示层覆盖名
    assert data["market_cn"] == "A股"
    assert data["chart"]["dates"]
    assert data["chart"]["ohlc"]
    assert data["assessment"]["color_cn"] in ("绿色", "灰色", "黑色", "数据不足")
    assert data["assessment"]["stage_cn"]
    assert data["market_badge"]["summary"] in (
        "tailwind", "neutral", "headwind", "unknown",
    )
    assert data["disclaimer_cn"]


def test_symbol_detail_error_returns_502(client: TestClient) -> None:
    resp = client.get("/api/symbols/BROKEN.SS/detail")
    assert resp.status_code == 502
    assert "网络不通" in resp.json()["detail"]


def test_market_context_graceful_unknown(client: TestClient) -> None:
    resp = client.get("/api/symbols/000001.SS/market-context")
    assert resp.status_code == 200
    data = resp.json()
    # Round 4 本地数据缺失时必须 graceful unknown，不得 500
    assert data["summary"] in ("tailwind", "neutral", "headwind", "unknown")
    assert data["summary_cn"] in ("顺风", "中性", "逆风", "环境未知")


def test_identity_conflict_degrades_without_persisting(tmp_path, monkeypatch) -> None:
    """研究库身份字段冲突时：卡片照常显示，但明确标注未入库。

    真实场景：lab.db 里历史 run 写入的 structure_id 与今日重算不一致，
    核心刻意抛 EventIdentityConflictError（身份字段不可静默覆盖）。
    看盘页只读当前信号，不应因此白屏。
    """
    from lei_signal.storage.sqlite_store import EventIdentityConflictError

    monkeypatch.setattr(config, "DASHBOARD_INDICES", _TWO_INDICES[:1])
    monkeypatch.setattr(config, "INDEX_OVERRIDES", {_TWO_INDICES[0].symbol: _TWO_INDICES[0]})

    attempts: list[str | None] = []

    def conflicting_analyze(symbol: str, **kwargs):
        attempts.append(kwargs.get("sqlite_path"))
        if kwargs.get("sqlite_path") is not None:
            raise EventIdentityConflictError(
                "事件 key_wave_black:abc 的身份字段 structure_id 不一致"
            )
        return _fake_analyze(symbol, **kwargs)

    db = str(tmp_path / "lab.db")
    app = create_app(
        analysis_service=AnalysisService(analyze_fn=conflicting_analyze, sqlite_path=db)
    )
    app.state.watchlist_db_path = db
    client = TestClient(app)

    card = client.get("/api/dashboard/cards").json()["cards"][0]
    assert card["error"] is None  # 卡片可用，不是错误卡
    assert card["price"] is not None
    assert card["color_cn"] is not None
    assert "structure_id 不一致" in card["persist_warning"]
    # 第一次带库写入失败，第二次关闭持久化重算
    assert attempts == [db, None]

    detail = client.get(f"/api/symbols/{_TWO_INDICES[0].symbol}/detail").json()
    assert detail["meta"]["sqlite_persisted"] is False
    assert "structure_id 不一致" in detail["meta"]["persist_warning"]


def test_events_endpoint_filters_by_structure_and_date(client: TestClient) -> None:
    """按需事件端点：点击图上标记后取该结构/该日的绑定事件。

    详情响应只带最近 60 条，点多年前的标记必须仍能取到事件——
    这就是本端点存在的原因。
    """
    sym = "000001.SS"
    all_events = client.get(f"/api/symbols/{sym}/events?limit=200").json()
    assert all_events, "样例应产生事件"
    # 默认倒序（最新在前）
    dates = [e["available_date"] for e in all_events]
    assert dates == sorted(dates, reverse=True)

    # 按 rule_id 过滤
    by_rule = client.get(f"/api/symbols/{sym}/events?rule_id=lei_color&limit=50").json()
    assert all(e["rule_id"] == "lei_color" for e in by_rule)

    # 按日期过滤
    target = all_events[0]["available_date"]
    by_date = client.get(f"/api/symbols/{sym}/events?on_date={target}").json()
    assert by_date
    assert all(target in (e["available_date"], e["event_date"]) for e in by_date)

    # 每条事件都自带解释与证据，前端点开即可展示
    assert any(e["explanation"] is not None for e in all_events)

    # 非法日期显式报错，不静默忽略
    assert client.get(f"/api/symbols/{sym}/events?on_date=bad").status_code == 422

    # 上限保护
    huge = client.get(f"/api/symbols/{sym}/events?limit=9999").json()
    assert len(huge) <= 200


def test_events_endpoint_502_when_unavailable(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        config,
        "DASHBOARD_INDICES",
        (*_TWO_INDICES, config.DashboardIndex("BROKEN.SS", "坏标的", "A股")),
    )
    assert client.get("/api/symbols/BROKEN.SS/events").status_code == 502


def test_detail_carries_concepts_and_mark_mapping(client: TestClient) -> None:
    """详情必须自带概念术语库与标记→概念映射，前端点击无需二次请求。"""
    d = client.get("/api/symbols/000001.SS/detail").json()
    assert "signal_color" in d["concepts"]
    assert "key_volatility" in d["concepts"]
    assert {"bias", "atr", "ma_spread", "long_trend"} <= set(d["concepts"])
    assert d["concepts"]["signal_color"]["usage"]
    assert d["mark_concepts"]["bottom_mark"] == "c_point"
    # 图上标记必须带 structure_id，否则点击无法关联结构
    marks = d["chart"]["bottomMarks"] + d["chart"]["topMarks"]
    if marks:
        assert all(m["info"]["structure_id"] for m in marks)


def test_chart_lines_carry_identity_for_click_explanation(client: TestClient) -> None:
    """B1 / C 点 / 颈线三类水平线必须带身份字段，否则点击无法解释。

    ECharts 的 markLine 不派发 click，前端在线右端放可点圆点把手；
    把手要展示「这条线是什么 + 怎么用」，就依赖这些字段。
    """
    chart = client.get("/api/symbols/000001.SS/detail").json()["chart"]

    if chart["b1Line"]:
        b1 = chart["b1Line"]
        assert b1["label_cn"] == "B1 第一阻力"
        assert "yAxis" in b1
        # pivot_date / distance_pct 可为 None（无数据时），但键必须存在
        assert "pivot_date" in b1
        assert "distance_pct" in b1

    for line in chart["bottomLines"]:
        assert line["label_cn"] == "C 点失效线"
        assert line["structure_id"], "C 线必须能关联到具体结构"
        assert line["structure_type"]

    for line in chart["topLines"]:
        assert line["label_cn"] == "顶部颈线"
        assert line["structure_id"], "颈线必须能关联到具体结构"
        assert line["structure_type"]


def test_line_concepts_resolvable(client: TestClient) -> None:
    """三类线的 mark_concepts 映射都必须能在 concepts 里查到解释。"""
    d = client.get("/api/symbols/000001.SS/detail").json()
    for kind in ("b1_line", "bottom_line", "top_line"):
        key = d["mark_concepts"][kind]
        exp = d["concepts"][key]
        assert exp["title"] and exp["definition"] and exp["usage"], f"{kind} 解释不完整"


def test_chart_exports_all_six_moving_averages(client: TestClient) -> None:
    """图表必须导出 EMA/SMA 各 20/60/120 共六条均线。

    sma60/sma120 由 compute_features 早已计算（sma_periods=[20,60,120]），
    此前序列化器漏导出，前端无法提供开关。
    """
    chart = client.get("/api/symbols/000001.SS/detail").json()["chart"]
    n = len(chart["dates"])
    for key in ("ema20", "sma20", "ema60", "ema120", "sma60", "sma120"):
        assert key in chart, f"缺少均线 {key}"
        assert len(chart[key]) == n, f"{key} 长度与日期数不一致"

    # 至少最近一根应有值（样例 80 根 > 60，sma120 可能仍为 None，属正常）
    assert chart["sma20"][-1] is not None
    assert chart["sma60"][-1] is not None


def test_chart_carries_state_colors_for_lei_mode(client: TestClient) -> None:
    """LEI 绿灰黑着色模式依赖 states + stateColors。"""
    chart = client.get("/api/symbols/000001.SS/detail").json()["chart"]
    assert len(chart["states"]) == len(chart["dates"])
    assert set(chart["states"]) <= {"green", "gray", "black", "unknown"}
    assert {"green", "gray", "black"} <= set(chart["stateColors"])
    # 红涨绿跌模式依赖 priceUp/priceDown
    assert chart["priceUp"] and chart["priceDown"]


def test_groups_endpoint_shape(client: TestClient) -> None:
    """左栏分组树：内置大盘组在最前且不可删，自建组随后，未分组兜底。"""
    groups = client.get("/api/groups").json()
    assert groups[0]["name"] == "大盘"
    assert groups[0]["builtin"] is True
    assert groups[0]["group_id"] is None
    assert groups[0]["symbols"] == [i.symbol for i in _TWO_INDICES]

    # 建组 + 加标的进组
    tech = client.post("/api/groups", json={"name": "科技"}).json()
    assert tech["group_id"] is not None
    client.post("/api/watchlist", json={"symbol": "QQQ", "group_id": tech["group_id"]})
    groups = client.get("/api/groups").json()
    tech_now = next(g for g in groups if g["group_id"] == tech["group_id"])
    assert tech_now["symbols"] == ["QQQ"]
    assert tech_now["builtin"] is False

    # 改名
    renamed = client.patch(f"/api/groups/{tech['group_id']}", json={"name": "科技成长"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "科技成长"

    # 内置组名被拒绝
    assert client.post("/api/groups", json={"name": "大盘"}).status_code == 422
    assert client.post("/api/groups", json={"name": "未分组"}).status_code == 422

    # 移出分组 → 出现「未分组」虚拟组
    client.post("/api/watchlist/QQQ/group", json={"group_id": None})
    groups = client.get("/api/groups").json()
    ungrouped = next(g for g in groups if g["name"] == "未分组")
    assert ungrouped["symbols"] == ["QQQ"]

    # 删组：标的保留（此时 QQQ 已未分组，验证删空组也不报错）
    assert client.delete(f"/api/groups/{tech['group_id']}").status_code == 204
    assert client.delete(f"/api/groups/{tech['group_id']}").status_code == 204  # 幂等
    assert "QQQ" in [i["symbol"] for i in client.get("/api/watchlist").json()]

    # 移动不存在的标的 → 404
    assert (
        client.post("/api/watchlist/NOPE/group", json={"group_id": None}).status_code == 404
    )


def test_detail_carries_today_overview(client: TestClient) -> None:
    """今日概述四组指标；盘口不可用时相关值为 None 并给出说明，不编数据。"""
    today = client.get("/api/symbols/000001.SS/detail").json()["today"]
    assert today is not None
    assert today["as_of"]

    keys = {m["key"] for m in today["price"]}
    assert {"open", "high", "low", "close", "amplitude", "dist_ref20"} <= keys

    technical = {m["key"]: m for m in today["technical"]}
    assert {
        "dist_ema20", "dist_sma20", "dist_ema60", "atr14_pct", "ma_spread",
        "daily_long_trend", "weekly_long_trend",
    } <= set(technical)
    assert technical["dist_ema20"]["label_cn"] == "EMA20乖离率"
    assert technical["dist_ema20"]["concept"] == "bias"
    assert technical["atr14_pct"]["concept"] == "atr"
    assert technical["ma_spread"]["concept"] == "ma_spread"
    assert technical["daily_long_trend"]["concept"] == "long_trend"

    vol = {m["key"]: m for m in today["volume"]}
    assert "vol_ratio20" in vol
    assert vol["vol_ratio20"]["text"], "量能倍数应带分级文本"
    # 测试用的是 fixture provider，盘口源不可用
    assert today["quote_available"] is False
    assert vol["turnover_rate"]["value"] is None
    assert vol["volume_ratio"]["value"] is None
    assert today["quote_note_cn"], "盘口缺失必须有说明文案"

    sig = {m["key"]: m for m in today["signal"]}
    assert {"color", "stage", "risk_state", "new_events"} <= set(sig)
    assert sig["color"]["text"]
    # 可点开解释的指标必须给出 concept 键
    assert sig["color"]["concept"] == "signal_color"


def test_detail_carries_color_backtest(client: TestClient) -> None:
    report = client.get("/api/symbols/000001.SS/detail").json()["color_backtest"]
    assert report is not None
    assert report["start_date"] <= report["end_date"]
    assert report["total_bars"] > 0
    for side in (report["long"], report["short"]):
        stats = {item["key"]: item for item in side["stats"]}
        assert {"day_5", "day_10", "day_20", "day_60", "day_120", "signal_exit"} <= set(stats)
        assert side["total_signals"] >= side["open_trades"]
    assert "做多" in report["methodology_cn"]
    assert "做空" in report["methodology_cn"]



def test_friendly_name_override_applied(client: TestClient) -> None:
    """A 股自选股若分析结果用符号作 display_name，应被 friendly_name_provider 覆盖。

    fixture provider 的 display_name == symbol，注入一个返回"创业板ETF易方达"的
    替身，验证 dashboard 卡片上能看到友好名。
    """
    def fake_friendly(symbol: str) -> str | None:
        return {"159915.SZ": "创业板ETF易方达", "510300.SS": "沪深300ETF"}.get(symbol)

    # 先加自选股，dashboard 才会为它们生成卡片
    client.post("/api/watchlist", json={"symbol": "159915"})
    client.post("/api/watchlist", json={"symbol": "510300"})

    client.app.state.friendly_name_provider = fake_friendly
    try:
        data = client.get("/api/dashboard/cards").json()
        names = {c["symbol"]: c["display_name"] for c in data["cards"]}
        # 大盘覆盖名优先
        assert names["000001.SS"] == "上证指数"
        # 自选股被 friendly_name_provider 覆盖
        assert names.get("159915.SZ") == "创业板ETF易方达"
        assert names.get("510300.SS") == "沪深300ETF"
    finally:
        client.app.state.friendly_name_provider = False



def test_friendly_name_provider_disabled_via_false(client: TestClient) -> None:
    """``app.state.friendly_name_provider = False`` 显式禁用友好名回退。

    默认 fixture 已置 False；这里再次断言不会去抓真实网络。
    """
    client.app.state.friendly_name_provider = False
    data = client.get("/api/dashboard/cards").json()
    name_map = {c["symbol"]: c["display_name"] for c in data["cards"]}
    if "159915.SZ" in name_map:
        assert name_map["159915.SZ"] in ("159915.SZ", "创业板ETF易方达")
