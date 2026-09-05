"""今日推荐流水线（纯函数，零 IO、零 LLM）。

资格门（技术）：只有扫描 verdict ∈ {actionable, waiting} 能上榜——这是
既有判定结果，本模块不产生新判定。
综合排序：verdict 档位分 + 盈亏比分 + 消息面热度加分。**排序只影响展示
顺序**，被排后的标的技术结论不变（设计定稿 §4.A）。
消息面/基本面/情绪面是叙事标注层：永不硬过滤信号（AGENTS.md 红线）。
"""
from __future__ import annotations

from lei_signal.api.routes.opportunities import VERDICT_ACTIONABLE, VERDICT_WAITING
from lei_signal.api.schemas import (
    RecommendCardDTO,
    RecommendItemDTO,
    ScanItemDTO,
    SectorPickDTO,
)
from lei_signal.portfolio.advisor import STAGE_CN

_VERDICT_BASE = {VERDICT_ACTIONABLE: 3.0, VERDICT_WAITING: 1.5}
_STAGE_RANK = {"markup": 0, "accumulation": 1, "distribution": 2, "decline": 3}
#: 消息面加分上限：热度 clamp 到 [-2, 2] 后 × 系数，只够影响同档内部排序。
_NEWS_COEF = 0.2
_NEWS_CLAMP = 2


def extract_news_heat(news_brief: dict | None, symbol: str) -> tuple[int, list[str]]:
    """从消息面简报里取该标的的多空热度。返回 (热度, 标注文案列表)。

    news_brief 的真实键名由 NewsfeedService 版本决定，这里做**容错适配**：
    兼容 items 列表（bull_count/bear_count）与 symbols 映射（bull/bear）两种
    形态；取不到一律 (0, [])，绝不妨碍技术结论上榜。
    """
    if not isinstance(news_brief, dict):
        return 0, []
    bull = bear = None
    items = news_brief.get("items")
    if isinstance(items, list):
        for row in items:
            if isinstance(row, dict) and row.get("symbol") == symbol:
                bull = row.get("bull_count", row.get("bull"))
                bear = row.get("bear_count", row.get("bear"))
                break
    if bull is None and isinstance(news_brief.get("symbols"), dict):
        row = news_brief["symbols"].get(symbol)
        if isinstance(row, dict):
            bull = row.get("bull", row.get("bull_count"))
            bear = row.get("bear", row.get("bear_count"))
    try:
        bull_i, bear_i = int(bull or 0), int(bear or 0)
    except (TypeError, ValueError):
        return 0, []
    heat = max(-_NEWS_CLAMP, min(_NEWS_CLAMP, bull_i - bear_i))
    tags: list[str] = []
    if bull_i or bear_i:
        tags.append(f"近3天消息偏{'多' if heat >= 0 else '空'}（多{bull_i}/空{bear_i}）")
    return heat, tags


def pick_sectors(sector_rows: list[dict] | None, top_n: int) -> list[SectorPickDTO]:
    """板块推荐：阶段快照直读排序（markup > accumulation > …），只排序不判定。"""
    if not sector_rows:
        return []
    ranked = sorted(
        (r for r in sector_rows if isinstance(r, dict) and r.get("code")),
        key=lambda r: _STAGE_RANK.get(str(r.get("stage", "")), 9),
    )
    out: list[SectorPickDTO] = []
    for row in ranked[:top_n]:
        stage = str(row.get("stage", "") or "")
        heat_parts = []
        for flag_key, label in (("heat_hot", "过热警示"), ("heat_cold", "冰点")):
            if row.get(flag_key):
                heat_parts.append(label)
        pctile = row.get("heat_pctile")
        if pctile is not None:
            heat_parts.append(f"{pctile}分位" if not heat_parts else f"{pctile}分位")
        out.append(SectorPickDTO(
            code=str(row.get("code", "")),
            name=str(row.get("name", "") or ""),
            stage=stage,
            stage_cn=STAGE_CN.get(stage, stage or "未知"),
            heat_state_cn="、".join(heat_parts) or None,
            note="阶段快照直读；排序不构成判定（plan-agent-superentry §4.A）",
        ))
    return out


def build_recommendation(
    scan_items: list[ScanItemDTO],
    *,
    run_date: str,
    sector_rows: list[dict] | None = None,
    news_brief: dict | None = None,
    sentiment_index: dict | None = None,
    sentiment_available: bool = False,
    generated_at: str = "",
    top_symbols: int = 5,
    top_sectors: int = 3,
) -> RecommendCardDTO:
    items: list[RecommendItemDTO] = []
    for it in scan_items:
        base = _VERDICT_BASE.get(it.verdict)
        if base is None:  # blocked / none 不上榜（资格门，技术判定直读）
            continue
        rr = it.reward_risk_ratio if it.reward_risk_computable else None
        rr_bonus = (min(rr, 5.0) / 5.0) if rr is not None else 0.0
        heat, tags = extract_news_heat(news_brief, it.symbol)
        score = base + rr_bonus + heat * _NEWS_COEF
        reasons = [
            f"{it.verdict_cn or it.verdict}（扫描判定直读）",
            *([f"盈亏比 {rr}"] if rr is not None else ["盈亏比不可计算"]),
            *tags,
        ]
        if it.missing_summary_cn:
            reasons.append(f"还缺：{it.missing_summary_cn}")
        # 情绪面：只标注不评分（回测阈值未定案，定案后是否参与排序另行决策）
        sentiment_cn = None
        if sentiment_index:
            from lei_signal.copilot import sentiment as sentiment_mod  # noqa: PLC0415

            sentiment_cn = sentiment_mod.symbol_sentiment_cn(it.symbol, sentiment_index)
        items.append(RecommendItemDTO(
            symbol=it.symbol,
            display_name=it.display_name or it.symbol,
            verdict=it.verdict,
            verdict_cn=it.verdict_cn,
            best_scenario_cn=it.best_scenario_cn,
            reward_risk_ratio=rr,
            reward_risk_computable=it.reward_risk_computable,
            news_heat=heat,
            news_tags=tags,
            sentiment_cn=sentiment_cn,
            score=round(score, 3),
            reasons=reasons,
        ))
    items.sort(key=lambda x: -x.score)
    return RecommendCardDTO(
        run_date=run_date,
        generated_at=generated_at,
        items=items[:top_symbols],
        sectors=pick_sectors(sector_rows, top_sectors),
        sentiment_status=(
            "已接入（只标注不评分）" if sentiment_available
            else "数据累积中（约需 20 个交易日资金流）"
        ),
    )
