"""情绪仪表盘 API（/api/sentiment/*，research_proxy）。

一切输出为叙事标注：只标注环境与状态，不硬过滤、不出买卖点。
阈值来源两类并明确标注：本系统回测（rules.v2.yaml retail_heat）与
外部实证引用（us_survey_sentiment）。
"""
from __future__ import annotations

from fastapi import APIRouter

from lei_signal.market_context import market_mood

router = APIRouter(prefix="/api/sentiment", tags=["sentiment"])


@router.get("/dashboard")
def dashboard() -> dict:
    cn = market_mood.cn_mood()
    return {
        "cn_mood": cn,
        "us_mood": {
            "breadth": market_mood.us_breadth(),
            "vix": market_mood.vix_level(),
            "risk_appetite": market_mood.us_risk_appetite(),
        },
        "us_survey": market_mood.us_survey_latest(),
        "sector_heat": market_mood.sector_heat_boards(),
        "disclaimer_cn": (
            "情绪面为叙事标注层（research_proxy）：只描述环境与状态，"
            "不参与技术判定、不构成买卖点。阈值来源在各项内标注"
            "（本系统回测 / 外部实证引用）。"
        ),
    }
