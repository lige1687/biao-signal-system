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
    """目录搜索层：自选没有的也能按中文名/别名命中（科创 case）。"""
    from lei_signal.api.routes import agent as agent_mod

    monkeypatch.setattr(
        "lei_signal.api.catalog.concept_boards", lambda **kw: []
    )
    # 别名表：科创 → 科创50 指数
    assert (
        agent_mod._resolve_symbol_by_catalog("科创板块现在怎么看")
        == "000688.SS"
    )
    # 目录名完整出现在话里：白酒 → TH 行业
    assert agent_mod._resolve_symbol_by_catalog("白酒板块现在怎么看") == "TH881273"
    # 无关文本不命中（曾把「市场环境」误配环保行业，模糊匹配已废）
    assert agent_mod._resolve_symbol_by_catalog("市场环境怎么样") is None
    assert agent_mod._resolve_symbol_by_catalog("大盘还能做吗") is None


def test_catalog_alias_longest_key_wins():
    from lei_signal.api.routes import agent as agent_mod

    # 「科创板」比「科创」长，两者都指向同一标的，此处验证不截胡不崩
    assert agent_mod._resolve_symbol_by_catalog("科创板") == "000688.SS"
    assert agent_mod._resolve_symbol_by_catalog("聊聊科创") == "000688.SS"
