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
        "sector_boards": market_mood.sector_boards_view(),
        "market_structure": market_mood.market_structure(),
        "action": market_mood.build_action(),
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


@router.get("/light")
def light() -> dict:
    """状态灯（读冻结快照，无网络，供顶部导航轮询）。"""
    a = market_mood.build_action()
    return {"light": a.get("light", "gray"),
            "n_picks": len(a.get("opportunity_cards") or []),
            "n_alarms": len(a.get("alarm_cards") or []),
            "holding_danger": sum(1 for h in a.get("holding_risk") or [] if h["state"] == "danger"),
            "available": a.get("available", False)}

@router.get("/alerts")
def alerts() -> dict:
    """全局情绪信号横幅（2026-09-06 用户口径：打开系统第一眼可见）。

    只在信号激活时返回条目（平时空列表，前端不渲染横幅）：
    - 冰点环境（全A三票冷）→ warn 级横幅（黄金坑前提，附宽度佐证）；
    - 热警报（需板块热度数据）→ alert 级横幅；
    纯叙事标注层（research_proxy），不构成买卖点；点击跳 /ops 看详情。
    """
    from lei_signal.copilot import breadth as breadth_mod

    out: list[dict] = []
    try:
        cn = market_mood.cn_mood() or {}
        if str(cn.get("state")) == "cold":
            breadth_note = ""
            try:
                b = breadth_mod.a_share_breadth() or {}
                if b.get("available"):
                    breadth_note = (
                        f"；宽度佐证：200日线上方 {b.get('ma200_pct', 0):.0f}%"
                    )
            except Exception:  # noqa: BLE001
                pass
            out.append({
                "level": "warn",
                "key": "icepoint",
                "title_cn": "❄ 全A情绪冰点出现",
                "body_cn": (
                    f"{cn.get('state_cn') or '三票冷'}{breadth_note}"
                    "——冰点机会信号的环境前提成立（历史 10 日超额 +6~8%、"
                    "154 例 92% 板块同向），点开今日操作查看板块明细"
                ),
            })
        heat = market_mood.sector_heat_boards() or {}
        for b in (heat.get("boards") or []):
            sig = str(b.get("signal") or "")
            if sig in ("heat_alarm", "strong_heat_alarm"):
                out.append({
                    "level": "alert",
                    "key": f"heat-{b.get('code', '')}",
                    "title_cn": f"⚠ 散户热警报：{b.get('name', '')}",
                    "body_cn": (
                        "全面强势板块出现散户涌入（历史 29 例无一板块幸免、"
                        "10 日平均 -9%）——追高风险，详情见今日操作"
                    ),
                })
    except Exception:  # noqa: BLE001 — 情绪缺席横幅不出现
        pass
    return {"alerts": out[:4], "note_cn": "叙事标注层信号横幅（research_proxy）"}
