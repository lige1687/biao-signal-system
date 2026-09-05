"""中文名称模糊解析：说「通信设备」能带出自选里的通信ETF。"""
from __future__ import annotations

from types import SimpleNamespace

from lei_signal.api.routes.agent import _resolve_symbol_by_name


class _NoNameService:
    """display_name 缺失时的取名服务：返回固定名。"""

    def __init__(self, mapping: dict[str, str]):
        self._m = mapping

    def get(self, symbol, refresh=False):
        name = self._m.get(symbol)
        if name is None:
            return SimpleNamespace(result=None)
        return SimpleNamespace(result=SimpleNamespace(display_name=name))


def _svc_none():
    return _NoNameService({})


def _watch(*pairs: tuple[str, str]) -> list:
    return [SimpleNamespace(symbol=s, display_name=n or None) for s, n in pairs]


WATCH = _watch(
    ("515880.SS", "通信ETF"),
    ("513100.SS", "纳指ETF"),
    ("518880.SS", "黄金ETF"),
    ("IGV", "iShares软件ETF"),
)


def test_exact_and_substring_name_hit():
    assert _resolve_symbol_by_name("通信ETF 怎么看", WATCH, _svc_none()) == "515880.SS"
    assert _resolve_symbol_by_name("黄金怎么样", WATCH, _svc_none()) == "518880.SS"


def test_partial_name_matches_via_lcs():
    # 「通信设备」与「通信ETF」公共子串「通信」=2，≥ 4//2 → 命中
    assert _resolve_symbol_by_name("通信设备怎么看", WATCH, _svc_none()) == "515880.SS"
    # 带尾巴的口语也能命中：「纳指现在贵不贵」公共「纳指」2字
    assert _resolve_symbol_by_name("纳指现在贵不贵", WATCH, _svc_none()) == "513100.SS"


def test_stopwords_do_not_match():
    assert _resolve_symbol_by_name("今天怎么看", WATCH, _svc_none()) is None
    assert _resolve_symbol_by_name("帮我看看", WATCH, _svc_none()) is None
    assert _resolve_symbol_by_name("", WATCH, _svc_none()) is None


def test_longest_match_wins():
    watch = _watch(("A", "通信"), ("B", "通信设备ETF"))
    assert _resolve_symbol_by_name("通信设备", watch, _svc_none()) == "B"


def test_no_false_positive_on_unrelated_text():
    assert _resolve_symbol_by_name("市场环境怎么样", WATCH, _svc_none()) is None
    assert _resolve_symbol_by_name("复盘一下这周", WATCH, _svc_none()) is None


def test_falls_back_to_service_display_name():
    """生产库 display_name 为空时，从分析结果取名后仍能命中。"""
    watch = _watch(("TH881278.SECTOR", ""), ("515880.SS", ""))
    svc = _NoNameService({"TH881278.SECTOR": "通信设备", "515880.SS": "通信ETF"})
    assert _resolve_symbol_by_name("通信设备怎么看", watch, svc) in (
        "TH881278.SECTOR", "515880.SS",
    )
    assert _resolve_symbol_by_name("通信设备", watch, svc) == "TH881278.SECTOR"
