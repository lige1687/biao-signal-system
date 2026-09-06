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
        "market_structure": market_mood.market_structure(),
        "disclaimer_cn": (
            "情绪面为叙事标注层（research_proxy）：只描述环境与状态，"
            "不参与技术判定、不构成买卖点。阈值来源在各项内标注"
            "（本系统回测 / 外部实证引用）。"
        ),
    }


@router.get("/board/{code}")
def board_profile(code: str) -> dict:
    """单板块情绪画像：自身热度/相对热度/趋势档位/信号 + 语义读法。"""
    return market_mood.board_profile(code)


@router.get("/confidence")
def confidence() -> dict:
    """证据账本：全部信号的 条件胜率/样本量/验证状态/适用边界 + 证伪清单。

    供 AI（超级入口等）引用信号时的置信度依据——按账本约定，引用任何
    信号必须同时给出条件胜率、样本量与适用边界。
    """
    import json as _json
    from pathlib import Path as _Path

    from lei_signal.data.cache import DEFAULT_CACHE_DIR as _DC

    p = _Path(__file__).resolve().parents[4] / "configs" / "sentiment_evidence.json"
    if not p.exists():
        return {"available": False}
    return _json.loads(p.read_text(encoding="utf-8"))
