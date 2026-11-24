"""Output boundaries: unavailable evidence cannot become directional evidence."""

import pytest

from lei_signal.copilot import opportunity_review as review


@pytest.mark.parametrize("stance", ["risk", "support"])
def test_missing_material_is_not_directional_evidence(stance):
    card = {
        "evidence": [
            {
                "id": "gap",
                "role": "unknown",
                "public": True,
                "text": "缺少同产品近期技术资料",
                "source": "资料检查",
            }
        ]
    }
    value = {
        "summary": "同产品技术资料尚未取得",
        "points": [{"text": "同产品技术资料尚未取得", "evidence_ids": ["gap"], "stance": stance}],
        "gaps": [],
    }
    with pytest.raises(ValueError, match="missing_evidence_direction"):
        review._validate_analysis(value, card, counter=True)
    value["points"][0]["stance"] = "unknown"
    assert review._validate_analysis(value, card, counter=True)["status"] == "complete"


def test_missing_material_retry_explains_the_specific_direction_error():
    feedback = review._retry_feedback("missing_evidence_direction", agent="counter")
    assert "role=unknown" in feedback
    assert "stance=unknown" in feedback
    assert "不能改为risk" in feedback


def test_actual_adverse_fact_with_a_gap_remains_usable():
    card = {
        "evidence": [
            {
                "id": "risk",
                "role": "opposition",
                "public": True,
                "text": "公司披露订单减少",
                "source": "公司报告",
            },
            {
                "id": "gap",
                "role": "unknown",
                "public": True,
                "text": "后续订单未知",
                "source": "资料检查",
            },
        ]
    }
    value = {
        "summary": "公司披露订单减少，后续订单未知",
        "points": [
            {
                "text": "公司披露订单减少，后续订单未知",
                "evidence_ids": ["risk", "gap"],
                "stance": "risk",
            }
        ],
        "gaps": [],
    }
    assert review._validate_analysis(value, card, counter=True)["status"] == "complete"


@pytest.mark.parametrize("point", [None, "bad", [["text", "bad"]]])
def test_point_must_be_an_object(point):
    with pytest.raises(ValueError, match="invalid_point"):
        review._validate_analysis({"summary": "资料待核", "points": [point], "gaps": []}, {})


def _analysis_point(card, text, stance, refs):
    return review._validate_analysis(
        {
            "summary": text,
            "points": [{"text": text, "evidence_ids": refs, "stance": stance}],
            "gaps": [],
        },
        card,
    )


@pytest.mark.parametrize("stance", ["support", "risk"])
def test_coverage_gap_cannot_be_directional_without_a_fact(stance):
    coverage = {"id": "coverage", "role": "context", "public": True,
                "source": "天天基金公开持仓表", "text": "已披露股票覆盖43%，未覆盖57%"}
    gap = {"id": "gap", "role": "unknown", "public": True,
           "source": "资料检查", "text": "当前权重未知"}
    adverse = {"id": "adverse", "role": "opposition", "public": True,
               "source": "公司报告", "text": "公司披露订单减少"}
    card = {"evidence": [coverage, gap, adverse]}
    with pytest.raises(ValueError, match="coverage_not_directional"):
        _analysis_point(card, "披露范围不足", stance, ["coverage", "gap"])
    assert _analysis_point(card, "披露范围不足", "neutral", ["coverage"])["status"] == "complete"
    assert _analysis_point(card, "披露范围待核", "unknown", ["coverage"])["status"] == "complete"
    assert (
        _analysis_point(card, "公司披露订单减少", "risk", ["coverage", "adverse"])["status"]
        == "complete"
    )


def test_counter_coverage_retry_distinguishes_stale_disclosure_from_adverse_fact():
    feedback = review._retry_feedback("coverage_not_directional", agent="counter")
    assert "报告期较早" in feedback
    assert "不能代表当前持仓" in feedback
    assert "stance=unknown" in feedback
    assert "不要改用neutral" in feedback
    assert "同一点另引明确负面事实" in feedback
    assert "错误示例" in review._SYSTEM_PROMPT
    assert "正确示例：同一句资料缺口标unknown" in review._SYSTEM_PROMPT
    # Context may use neutral; the counter-specific feedback must not change it.
    assert "用neutral或unknown" in review._retry_feedback(
        "coverage_not_directional", agent="context"
    )


@pytest.mark.parametrize("stance", ["support", "risk"])
def test_macro_numbers_alone_cannot_be_directional(stance):
    card = {"evidence": [
        {"id": "macro", "role": "context", "public": True,
         "source": "FRED", "text": "CPI同比4%", "provenance": "local_macro_observation"},
        {"id": "event", "role": "opposition", "public": True,
         "source": "公司报告", "text": "公司披露订单减少", "provenance": "verified_public_source"},
    ]}
    with pytest.raises(ValueError, match="macro_direction_unproven"):
        _analysis_point(card, "宏观读数有压力", stance, ["macro"])
    assert _analysis_point(card, "宏观读数待核", "neutral", ["macro"])["status"] == "complete"
    assert (
        _analysis_point(card, "公司披露订单减少", "risk", ["macro", "event"])["status"]
        == "complete"
    )


def test_express_source_attribution_requires_cited_manual():
    holdings = {"id": "holding", "role": "context", "public": True,
                "source": "天天基金公开持仓表", "text": "披露股票：某公司"}
    manual = {"id": "manual", "role": "context", "public": True,
              "source": "基金产品说明书", "text": "主要投资成份股"}
    card = {"evidence": [holdings, manual]}
    with pytest.raises(ValueError, match="source_attribution_unproven"):
        _analysis_point(card, "按产品说明书这是该基金的持仓资料", "neutral", ["holding"])
    assert _analysis_point(card, "缺少说明书，待核", "unknown", ["holding"])["status"] == "complete"
    assert (
        _analysis_point(card, "按产品说明书投资成份股", "neutral", ["manual"])["status"]
        == "complete"
    )


def test_disclosed_holding_claim_needs_holding_evidence():
    business = {
        "id": "business", "role": "context", "public": True,
        "source": "公司业务公开资料", "text": "某公司业务涉及芯片",
        "provenance": "business_reference",
    }
    holding = {
        "id": "holding", "role": "context", "public": True,
        "source": "天天基金公开持仓表", "text": "披露股票：某公司",
        "provenance": "disclosed",
    }
    card = {"evidence": [business, holding]}
    with pytest.raises(ValueError, match="holding_link_unproven"):
        _analysis_point(card, "已披露持仓含芯片业务公司", "neutral", ["business"])
    assert (
        _analysis_point(card, "某公司业务涉及芯片", "neutral", ["business"])["status"]
        == "complete"
    )
    assert (
        _analysis_point(
            card, "已披露持仓含芯片业务公司", "neutral", ["business", "holding"]
        )["status"]
        == "complete"
    )
