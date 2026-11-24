"""Read-only, server-bound holding context for user-initiated agent questions."""
from __future__ import annotations

import hashlib
import json

from fastapi import HTTPException, Request


def scope_token(holding_id: str | None) -> str:
    """Opaque internal session identity, never used as a market symbol."""
    if holding_id is None:
        return "portfolio:all"
    return "portfolio:holding:" + hashlib.sha256(holding_id.encode("utf-8")).hexdigest()


def build_portfolio_context(request: Request, holding_id: str | None) -> dict:
    from lei_signal.api.portfolio_workspace import build_workspace

    workspace = build_workspace(request)
    items = workspace.get("items") or []
    if holding_id is not None:
        items = [item for item in items if item.get("holding_id") == holding_id]
        if not items:
            raise HTTPException(status_code=404, detail="持仓不存在或已不在当前持仓中")
    # Limit material to the selected scope. A candidate is not an approved plan.
    selected = []
    for item in items:
        selected.append({key: item.get(key) for key in (
            "holding_id", "name", "code", "group_name", "market_value",
            "weight_pct", "return_pct", "holding_as_of", "original_note", "nav", "symbol",
            "disclosure", "industry_reference",
            "status", "title_cn", "reason_cn", "next_step_cn", "gaps",
            "technical", "plan", "plan_candidates", "alerts",
        )})
    material = {
        "scope": "single" if holding_id is not None else "all",
        "portfolio_holding_id": holding_id,
        "generated_at": workspace.get("generated_at"),
        "review_date": workspace.get("review_date"),
        "holding_as_of": workspace.get("as_of"),
        "coverage": workspace.get("coverage"),
        "items": selected,
        "note_cn": (
            "只解释这里列出的真实持仓及系统已有判断。original_note 是用户原有备注，"
            "只能解释其历史持有理由，不能当成已确认交易计划或当前操作建议。计划候选不是已关联计划；"
            "原计划提醒以 alerts 的 data_as_of 和 actionable_from 分别说明资料日期和最早可处理时间，"
            "不得自行推算日期或把提醒当作已执行交易；"
            "无计划或技术行情缺失时，不能声称原计划安全、已满足或本轮无新触发。"
            "净值日期与刷新时间分别说明。group_name和original_note不是行业证据；"
            "disclosure仅按准确基金代码匹配的历史披露，必须同时说明报告截止日、来源、"
            "前十覆盖比例和未核实比例。联接基金/FOF不能以直接股票前十代替完整穿透。"
            "成分及行业只用于解释持仓，不参与技术信号或交易判定。"
            "industry_reference是经公司身份与业务核对的有限行业ETF参照。技术状态只属于该ETF，"
            "不能据此断言持仓基金已触及退出位；stale或盘中未完成的ETF状态不能当作当前收盘判断。"
            "fundamentals中的基金经理观点只代表标明日期的观点，"
            "不当作今天的盈利事实。先说明基金卖出条件能否判断，再解释行业风险及基本面，缺资料保留未知。"
            "不得创建计划、成交或自动交易。"
        ),
    }
    return {
        "context_kind": "portfolio",
        "portfolio": material,
        "evidence_card": {"portfolio": material},
    }


def frozen_portfolio_context(snapshot: dict, holding_id: str | None) -> dict:
    """Resume only the original question's exact material and scope."""
    material = snapshot.get("portfolio")
    if not isinstance(material, dict) or material.get("portfolio_holding_id") != holding_id:
        raise HTTPException(status_code=409, detail="原问题持仓范围或已保存资料无法核实")
    return {"context_kind": "portfolio", "portfolio": material,
            "evidence_card": {"portfolio": material}}


def snapshot_digest(material: dict) -> str:
    return hashlib.sha256(json.dumps(material, ensure_ascii=False, sort_keys=True,
                                     default=str).encode("utf-8")).hexdigest()
