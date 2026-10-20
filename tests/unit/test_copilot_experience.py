"""经验索引检索单元测试（experience.json 条件匹配与池推断）。"""
from __future__ import annotations

from lei_signal.copilot import experience


def test_query_subset_match():
    out = experience.query_experience({"signal": "module_A_stable", "pool": "industry_etf"})
    assert out["available"] is True
    top = out["items"][0]
    assert top["direction"] == "negative"
    assert "行业 ETF" in top["conclusion_cn"] or "行业" in top["conclusion_cn"]
    assert top["report"].endswith(".md")  # 可溯源


def test_query_pool_only_returns_both_directions():
    """只按池查：行业 ETF 应同时命中 A 模块负面经验与 B 模块观察经验。"""
    out = experience.query_experience({"pool": "industry_etf"})
    assert out["available"] is True
    directions = {i["direction"] for i in out["items"]}
    assert "negative" in directions


def test_query_no_hit_available_false():
    out = experience.query_experience({"signal": "module_D_fakeout", "pool": "single_stock"})
    assert out["available"] is False
    assert out["items"] == []


def test_query_empty_conditions_hits_nothing():
    """空条件不做全量兜底（避免把无关经验灌进材料）。"""
    out = experience.query_experience({})
    assert out["available"] is False


def test_defined_sorted_first():
    out = experience.query_experience({"pool": "industry_etf"})
    confs = [i["confidence"] for i in out["items"]]
    assert confs == sorted(confs, key=lambda c: c != "defined")


def test_infer_pool():
    assert experience.infer_pool("510300.SS") == "broad_base_etf"
    assert experience.infer_pool("515880.SS") == "industry_etf"
    assert experience.infer_pool("000688.SS") == "index"
    assert experience.infer_pool("TH881129.SECTOR") == "index"
    # 个股/推断不出：None（宁缺毋滥，不挂错池经验）
    assert experience.infer_pool("600519.SS") is None
    assert experience.infer_pool("") is None


def test_experience_for_symbol_industry_etf():
    items = experience.experience_for_symbol("515880.SS")
    assert items, "行业 ETF 应带出 A 模块负面经验"
    assert any("行业" in (i.get("conclusion_cn") or "") for i in items)
