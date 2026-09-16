"""调仓建议引擎 + 基金数据解析器单元测试（纯函数，无网络）。"""
from __future__ import annotations

from lei_signal.portfolio.advisor import build_advices
from lei_signal.portfolio.funddata import (
    FundStockHolding,
    classify_market,
    normalize_fund_name,
)
from lei_signal.portfolio.holdings_report import FundExposure


def _base_inputs():
    groups = [
        {"group_key": "us_tech_active", "name": "海外·全球科技主动", "market": "us",
         "amount": 34600.0, "pct": 40.4, "holding_ids": ["f1"]},
        {"group_key": "cn_info", "name": "A股·信息产业", "market": "cn",
         "amount": 22431.0, "pct": 26.2, "holding_ids": ["f2"]},
    ]
    holdings = [
        {"holding_id": "f1", "group_key": "us_tech_active", "name": "富国全球科技互联网股票(QDII)C",
         "market_value": 17182.0, "pct": 20.1},
        {"holding_id": "f2", "group_key": "cn_info", "name": "易方达信息产业混合A",
         "market_value": 16558.0, "pct": 19.3},
        {"holding_id": "f3", "group_key": "cn_info", "name": "嘉实中证主要消费ETF发起联接C",
         "market_value": 4.49, "pct": 0.0},
    ]
    return groups, holdings


def test_r1_fires_without_broad_base():
    groups, holdings = _base_inputs()
    advices = build_advices(
        groups=groups, holdings=holdings, exposures={}, group_market_share={},
        sector_stages={},
    )
    r1 = [a for a in advices if a.advice_id == "R1_no_broad_base"]
    assert r1 and r1[0].strength == "certified"
    # 有宽基组就不发
    groups[1]["group_key"] = "cn_broad"
    advices2 = build_advices(
        groups=groups, holdings=holdings, exposures={}, group_market_share={},
        sector_stages={},
    )
    assert not [a for a in advices2 if a.advice_id == "R1_no_broad_base"]


def test_r2_single_fund_concentration():
    groups, holdings = _base_inputs()
    advices = build_advices(
        groups=groups, holdings=holdings, exposures={}, group_market_share={},
        sector_stages={},
    )
    r2 = [a for a in advices if a.advice_id == "R2_single_fund_concentration"]
    # fixture 里最大单一持仓是富国（17182/33744 = 51%）
    biggest = max(holdings, key=lambda h: h["market_value"])["name"]
    assert r2 and biggest in r2[0].title_cn


def test_r3_fake_global_and_asia_exclusion():
    groups, holdings = _base_inputs()
    holdings.append({"holding_id": "f4", "group_key": "us_growth_em",
                     "name": "国富亚洲机会股票(QDII)A", "market_value": 935.98, "pct": 1.1})
    groups.append({"group_key": "us_growth_em", "name": "海外·全球成长", "market": "us",
                   "amount": 935.98, "pct": 1.1, "holding_ids": ["f4"]})
    exposures = {
        # 富国全球科技：前十大 47.5%，A股19+港股6 -> 53% ≥ 40 触发
        "f1": FundExposure("f1", "2026Q2", 47.5, {"cn": 19.0, "us": 18.0, "hk": 6.0}),
        # 亚洲基金 A股+港股 占比高但名字含「亚洲」——不触发
        "f4": FundExposure("f4", "2026Q2", 41.7, {"cn": 17.0, "hk": 3.0, "us": 7.0}),
    }
    advices = build_advices(
        groups=groups, holdings=holdings, exposures=exposures,
        group_market_share={}, sector_stages={},
    )
    r3 = [a for a in advices if a.advice_id == "R3_real_exposure_correction"]
    assert r3 and "富国全球科技" in r3[0].title_cn
    assert "亚洲机会" not in r3[0].detail_cn


def test_r4_tiny_positions():
    groups, holdings = _base_inputs()
    advices = build_advices(
        groups=groups, holdings=holdings, exposures={}, group_market_share={},
        sector_stages={},
    )
    r4 = [a for a in advices if a.advice_id == "R4_tiny_positions"]
    assert r4 and "嘉实中证主要消费" in r4[0].detail_cn


def test_r7_stage_mapping_prefers_worst():
    groups, holdings = _base_inputs()
    stages = {
        "通信设备": {"stage": "distribution", "rs_pctile": 95.16, "close": 100.0},
        "半导体": {"stage": "decline", "rs_pctile": 96.77, "close": 100.0},
        "_as_of": "2026-09-04 17:03",
    }
    advices = build_advices(
        groups=groups, holdings=holdings, exposures={}, group_market_share={},
        sector_stages=stages,
    )
    r7 = [a for a in advices if a.advice_id == "R7_cn_info_stage"]
    assert r7 and "下降" in r7[0].title_cn and "减仓提示" in r7[0].title_cn
    assert r7[0].strength == "candidate"
    # 无板块数据 -> R7 静默跳过（不瞎编）
    advices0 = build_advices(
        groups=groups, holdings=holdings, exposures={}, group_market_share={},
        sector_stages={},
    )
    assert not [a for a in advices0 if a.advice_id.startswith("R7_")]


def test_r5_r6_info_cards():
    groups, holdings = _base_inputs()
    advices = build_advices(
        groups=groups, holdings=holdings, exposures={}, group_market_share={},
        sector_stages={},
    )
    assert [a for a in advices if a.advice_id == "R5_overseas_hold_discipline"]
    groups.append({"group_key": "hk_tech", "name": "港股·恒生科技", "market": "hk",
                   "amount": 2114.0, "pct": 2.5, "holding_ids": []})
    advices2 = build_advices(
        groups=groups, holdings=holdings, exposures={}, group_market_share={},
        sector_stages={},
    )
    assert [a for a in advices2 if a.advice_id == "R6_hk_unverified_zone"]


def test_classify_market():
    assert classify_market("603986") == "cn"
    assert classify_market("000001") == "cn"
    assert classify_market("300750") == "cn"
    assert classify_market("00522") == "hk"
    assert classify_market("00700") == "hk"
    assert classify_market("AAPL") == "us"
    assert classify_market("SNDK") == "us"
    assert classify_market("BRK.B") == "us"


def test_normalize_fund_name_keeps_share_class():
    assert normalize_fund_name("国富全球科技互联混合(QDII)人民币C") == "国富全球科技互联混合(QDII)C"
    assert normalize_fund_name("摩根标普500指数(QDII)A") == "摩根标普500指数(QDII)A"
    # A/C 份额字母绝不能被规范化掉
    assert normalize_fund_name("富国全球科技互联网股票(QDII)A") != normalize_fund_name(
        "富国全球科技互联网股票(QDII)C")


def test_jjcc_row_parser_shape():
    """解析器行结构（网络函数已在线上验证，这里锁数据类形状与市场分类联动）。"""
    row = FundStockHolding("00522", "ASMPT", classify_market("00522"), 5.62)
    assert row.market == "hk" and row.weight_pct == 5.62
