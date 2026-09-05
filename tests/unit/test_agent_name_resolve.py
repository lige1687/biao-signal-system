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
