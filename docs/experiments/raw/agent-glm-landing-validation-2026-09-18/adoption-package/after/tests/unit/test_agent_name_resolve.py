"""中文名称模糊解析：说「通信设备」能联动自选（DB名+静态表三层取名）。"""
from __future__ import annotations

from types import SimpleNamespace

from lei_signal.api.routes.agent import _resolve_symbol_by_name


def _watch(*pairs: tuple[str, str | None]) -> list:
    return [SimpleNamespace(symbol=s, display_name=n or None) for s, n in pairs]


WATCH = _watch(
    ("515880.SS", "通信ETF"),
    ("513100.SS", "纳指ETF"),
    ("518880.SS", "黄金ETF"),
    ("IGV", "iShares软件ETF"),
    # 生产库形态：display_name 为空，靠静态表取名
    ("931160.SS", None),        # INDEX_OVERRIDES -> 通信设备（中证）
    ("TH881121.SECTOR", None),  # THS_INDUSTRY_NAMES -> 半导体
)


def test_exact_and_substring_name_hit():
    assert _resolve_symbol_by_name("通信ETF 怎么看", WATCH) in (
        "515880.SS", "931160.SS",
    )
    assert _resolve_symbol_by_name("黄金怎么样", WATCH) == "518880.SS"


def test_partial_name_matches_via_lcs():
    assert _resolve_symbol_by_name("通信设备怎么看", WATCH) == "931160.SS"
    assert _resolve_symbol_by_name("纳指现在贵不贵", WATCH) == "513100.SS"


def test_static_table_fills_missing_display_name():
    assert _resolve_symbol_by_name("半导体走势", WATCH) == "TH881121.SECTOR"
    assert _resolve_symbol_by_name("通信设备", WATCH) == "931160.SS"


def test_stopwords_do_not_match():
    assert _resolve_symbol_by_name("今天怎么看", WATCH) is None
    assert _resolve_symbol_by_name("帮我看看", WATCH) is None
    assert _resolve_symbol_by_name("", WATCH) is None


def test_longest_match_wins():
    watch = _watch(("A", "通信"), ("B", "通信设备ETF"))
    assert _resolve_symbol_by_name("通信设备", watch) == "B"


def test_no_false_positive_on_unrelated_text():
    assert _resolve_symbol_by_name("市场环境怎么样", WATCH) is None
    assert _resolve_symbol_by_name("复盘一下这周", WATCH) is None


def test_payload_symbol_numbers_whitelists_codes():
    """板块/标的代码里的数字进白名单（glm-5.3 提代码不再被当编数字）。"""
    from lei_signal.api.routes.agent import _payload_symbol_numbers
    from lei_signal.plans.grounding import verify_numeric_grounding

    payload = {
        "context_kind": "symbol",
        "symbol": "TH881129.SECTOR",
        "display_name": "通信设备",
        "buy_point_review": {"candidates": [{"key_price": 9386.12}]},
    }
    allowed = frozenset({9386.12}) | frozenset(_payload_symbol_numbers(payload))
    ok, reason = verify_numeric_grounding(
        "TH881129 当前状态偏弱，筹码峰约 9386.12。", allowed
    )
    assert ok, reason


def test_catalog_layer_resolves_index_not_in_watchlist(monkeypatch):
    """目录搜索层：自选没有的也能按中文名/别名命中（科创 case）。

    主控裁决（2026-09-15）后的产品定义（原「科创板块→000688.SS」断言
    是名称轮引入的既有失败，非本轮引入；原失败记录见
    docs/experiments/raw/agent-ask-stability-2026-09-15/pre-existing-failures.md）：
    - 明确说「科创50」（即使句中另有「板块」二字）保留指数身份；
    - 「科创板块/科创板整体」无唯一可核实对象 → None（resolve 层澄清，
      科创50 只作可选观察参考，不代表整个科创板）。"""
    from lei_signal.api.routes import agent as agent_mod

    monkeypatch.setattr(
        "lei_signal.api.catalog.concept_boards", lambda **kw: []
    )
    # 明确指定的指数身份不被「板块」关键词截断
    assert agent_mod._resolve_symbol_by_catalog("科创50指数现在怎么看") == "000688.SS"
    assert agent_mod._resolve_symbol_by_catalog("科创50板块最近如何看") == "000688.SS"
    # 板块泛指没有唯一可核实对象：不静默映射到指数
    assert agent_mod._resolve_symbol_by_catalog("科创板块现在怎么看") is None
    assert agent_mod._resolve_symbol_by_catalog("科创板整体怎么看") is None
    # 目录名完整出现在话里：白酒 → TH 行业（真实板块不截断）。
    # 两条既有查找路径的身份写法不一致（板块专名路径带 .SECTOR 后缀，
    # 目录扫描路径不带；环境相关、名称轮之前即存在），此处只锁定
    # 「是白酒行业板块」这一产品身份。
    assert agent_mod._resolve_symbol_by_catalog("白酒板块现在怎么看") in (
        "TH881273", "TH881273.SECTOR")
    # 明确别名同样优先于板块二字（恒生科技指数）
    assert agent_mod._resolve_symbol_by_catalog("恒生科技板块现在怎么看") == "^HSTECH"
    # 无关文本不命中（曾把「市场环境」误配环保行业，模糊匹配已废）
    assert agent_mod._resolve_symbol_by_catalog("市场环境怎么样") is None
    assert agent_mod._resolve_symbol_by_catalog("大盘还能做吗") is None


def test_catalog_alias_longest_key_wins():
    """别名最长键优先（中概互联 不被 中概 截胡）；板块泛指不再进别名表
    （主控裁决 2026-09-15：「科创板」「聊聊科创」这类泛指不静默映射指数）。"""
    from lei_signal.api.routes import agent as agent_mod

    assert agent_mod._resolve_symbol_by_catalog("中概互联") == "513050.SS"
    assert agent_mod._resolve_symbol_by_catalog("科创板") is None
    assert agent_mod._resolve_symbol_by_catalog("聊聊科创") is None


def test_resolve_api_clarifies_sector_area_with_index_reference(tmp_path):
    """主控裁决（2026-09-15）：resolve 接口对「科创板块」给简短澄清——
    科创50 作为可选观察参考并明确不代表整个板块；「科创50指数」则直接
    解析为指数身份，无此澄清。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from lei_signal.api.routes import copilot as copilot_routes
    from lei_signal.storage.sqlite_store import connect

    db = str(tmp_path / "t.db")
    connect(db).close()
    app = FastAPI()
    app.state.plans_db_path = db
    app.state.watchlist_db_path = db
    app.include_router(copilot_routes.router)
    client = TestClient(app)

    r = client.post("/api/copilot/resolve", json={
        "message": "科创板块现在怎么看", "client_request_id": "cr-area-1",
        "session_id": None, "selected_symbol": None,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["resolved_symbol"] is None
    hits = [c for c in data["clarification"]
            if c["kind"] == "sector_ambiguous_index_reference"]
    assert hits, data["clarification"]
    text = hits[0]["question_cn"]
    assert "科创50" in text and "000688.SS" in text
    assert "不代表整个板块" in text  # 明确指数不等于板块整体

    r2 = client.post("/api/copilot/resolve", json={
        "message": "科创50指数现在怎么看", "client_request_id": "cr-area-2",
        "session_id": None, "selected_symbol": None,
    })
    data2 = r2.json()
    assert data2["resolved_symbol"] == "000688.SS"
    assert not [c for c in data2["clarification"]
                if c["kind"] == "sector_ambiguous_index_reference"]
