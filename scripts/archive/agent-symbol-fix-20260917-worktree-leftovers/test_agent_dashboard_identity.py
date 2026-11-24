"""Agent 目录识别与显示名：DASHBOARD_INDICES 全量参数化（大盘指数身份同源）。

根因（2026-09-18）：目录扫描层只拼了 TH 行业/STRATEGY_INDICES/美股ETF/概念，
漏了 DASHBOARD_INDICES——「沪深300」「上证指数」「科创100」落空后沿用旧选中
ETF；copilot/subjects.catalog_names 同样漏目录，显示名落空。修复 = 复用既有
精确 display_name→symbol，不新增模糊别名、不复制手写代码表。
"""
from __future__ import annotations

import pytest

from lei_signal.api.config import DASHBOARD_INDICES, STRATEGY_INDICES, US_ETFS
from lei_signal.api.labels import THS_INDUSTRY_NAMES
from lei_signal.copilot import subjects


@pytest.fixture(autouse=True)
def _offline_catalog(monkeypatch, tmp_path):
    """概念板块是联网数据源，测试内替换为空；缓存根指到临时目录，零真实接触。"""
    monkeypatch.setattr("lei_signal.api.catalog.concept_boards", lambda *a, **kw: [])
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))


@pytest.mark.parametrize("idx", DASHBOARD_INDICES, ids=lambda i: i.symbol)
def test_dashboard_index_name_resolves_by_catalog(idx):
    from lei_signal.api.routes.agent import _resolve_symbol_by_catalog

    assert _resolve_symbol_by_catalog(f"{idx.display_name}最近如何看") == idx.symbol


@pytest.mark.parametrize(
    "message,symbol",
    [
        ("沪深300现在怎么看", "000300.SS"),
        ("上证指数今天走势如何", "000001.SS"),
        ("科创50指数现在怎么看", "000688.SS"),
        ("科创100怎么样", "000698.SS"),
    ],
)
def test_required_dashboard_positives(message, symbol):
    from lei_signal.api.routes.agent import _resolve_symbol_by_catalog

    assert _resolve_symbol_by_catalog(message) == symbol


@pytest.mark.parametrize("idx", DASHBOARD_INDICES, ids=lambda i: i.symbol)
def test_dashboard_display_name_comes_from_catalog(idx):
    """显示名与目录同源：会话列表/resolve 取名都从 catalog_names 出，不另抄表。"""
    assert subjects.catalog_names()[idx.symbol] == idx.display_name
    assert subjects.display_name(idx.symbol) == idx.display_name
    assert idx.display_name in subjects.subject_label(idx.symbol)


def test_no_conflicting_names_across_static_catalogs():
    """同名不同符号 = 冲突；静态目录内必须唯一（冲突须停下处理，不静默择一）。"""
    name_map: dict[str, set[str]] = {}
    entries = [(x.symbol, x.display_name)
               for x in (*DASHBOARD_INDICES, *STRATEGY_INDICES, *US_ETFS)]
    entries += list(THS_INDUSTRY_NAMES.items())
    for _sym, name in entries:
        name_map.setdefault(name, set()).add(_sym)
    conflicts = {n: sorted(s) for n, s in name_map.items() if len(s) > 1}
    assert conflicts == {}


@pytest.mark.parametrize(
    "message,expected",
    [
        ("ATR止损怎么设", None),                    # 指标词不算证券（收口一）
        ("科创板块现在怎么看", None),               # 板块泛指不映射指数（2026-09-15 裁决）
        ("科创板整体怎么看", None),
        ("那失效位呢", None),                       # 继续追问不解析出新标的
        ("市场环境怎么样", None),                   # 无关文本不命中
        ("纳斯达克100怎么看", "^NDX"),              # 长名不被短名「纳斯达克」截走
        ("恒生科技板块现在怎么看", "^HSTECH"),      # 别名路径不回退
        ("白酒板块现在怎么看", "TH881273"),         # 行业板块身份不变（后缀两种写法见既有测试）
    ],
)
def test_existing_boundaries_do_not_regress(message, expected):
    from lei_signal.api.routes.agent import _resolve_symbol_by_catalog

    got = _resolve_symbol_by_catalog(message)
    if message == "白酒板块现在怎么看":
        assert got in ("TH881273", "TH881273.SECTOR")
    else:
        assert got == expected


def test_dashboard_names_stay_out_of_sector_and_product_layer():
    """大盘指数名不进板块专名/ETF 专名层：resolve 由目录扫描层按指数身份处理。"""
    assert subjects.named_subject("沪深300板块怎么看") is None
    assert subjects.named_subject("上证指数怎么看") is None
