"""我的持仓 REST 路由（持仓体检页）。

GET /api/portfolio 返回整份快照：分组 + 持仓 + 组合级提示 + 季报穿透
暴露 + 调仓建议（R1~R7）。汇总（组金额/占比/加权收益率）与建议判定
都在 Python 层完成，前端只做展示——与全站「UI 不重新计算」一致。
分组结论与穿透结果都是叙事标注层，不参与任何信号判定。
"""
from __future__ import annotations

from contextlib import closing

from fastapi import APIRouter, Request

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.schemas import (
    PortfolioAdviceDTO,
    PortfolioGroupDTO,
    PortfolioHoldingDTO,
    PortfolioResponse,
)
from lei_signal.portfolio.advisor import build_advices
from lei_signal.portfolio.holdings_report import (
    group_real_market_share,
    load_exposures,
    load_sector_stages,
)
from lei_signal.portfolio.models import MARKETS
from lei_signal.portfolio.store import load_snapshot
from lei_signal.storage.sqlite_store import connect

router = APIRouter(prefix="/api", tags=["portfolio"])

_MARKET_CN = {"us": "海外", "cn": "A股", "hk": "港股", "other": "其他"}


def _db_path(request: Request) -> str:
    return getattr(request.app.state, "portfolio_db_path", None) or default_db()


@router.get("/portfolio", response_model=PortfolioResponse)
def get_portfolio(request: Request) -> PortfolioResponse:
    with closing(connect(_db_path(request))) as conn:
        snap = load_snapshot(conn)
        exposures = load_exposures(conn)
        sector_stages = load_sector_stages()

    holdings_by_group = snap["holdings_by_group"]
    all_holdings = [h for hs in holdings_by_group.values() for h in hs]
    total_value = sum(h.market_value for h in all_holdings) or 1.0

    # advisor 输入：轻量 dict（避免跨模块 dataclass 耦合）
    adv_groups = [
        {
            "group_key": g.group_key, "name": g.name, "market": g.market,
            "amount": sum(h.market_value for h in holdings_by_group.get(g.group_key, [])),
            "pct": sum(h.market_value for h in holdings_by_group.get(g.group_key, []))
            / total_value * 100,
            "holding_ids": [h.holding_id for h in holdings_by_group.get(g.group_key, [])],
        }
        for g in snap["groups"]
    ]
    holdings_by_id = {h.holding_id: h for h in all_holdings}
    adv_holdings = [
        {
            "holding_id": h.holding_id, "group_key": h.group_key, "name": h.name,
            "market_value": h.market_value, "pct": h.market_value / total_value * 100,
        }
        for h in all_holdings
    ]
    group_share = {
        g["group_key"]: group_real_market_share(
            exposures, holdings_by_id, g["holding_ids"])
        for g in adv_groups
    }
    advices = build_advices(
        groups=adv_groups,
        holdings=adv_holdings,
        exposures=exposures,
        group_market_share=group_share,
        sector_stages=sector_stages,
    )

    group_dtos: list[PortfolioGroupDTO] = []
    for g in snap["groups"]:
        hs = holdings_by_group.get(g.group_key, [])
        amount = sum(h.market_value for h in hs)
        share = group_share.get(g.group_key)
        group_dtos.append(PortfolioGroupDTO(
            group_key=g.group_key,
            name=g.name,
            market=g.market if g.market in MARKETS else "other",
            market_cn=_MARKET_CN.get(g.market, "其他"),
            amount=round(amount, 2),
            pct=round(amount / total_value * 100, 1) if total_value > 0 else 0.0,
            avg_return_pct=_weighted_return(hs, amount),
            verdict_cn=g.verdict_cn,
            verdict_basis=g.verdict_basis,
            real_market_share=share,
            holdings=[_to_holding_dto(h, exposures) for h in hs],
        ))

    # 分组已删但持仓残留：以「未分组」形式透出，不静默丢数据
    known_keys = {g.group_key for g in snap["groups"]}
    orphans = [h for k, hs in holdings_by_group.items() if k not in known_keys for h in hs]
    if orphans:
        amount = sum(h.market_value for h in orphans)
        group_dtos.append(PortfolioGroupDTO(
            group_key="__ungrouped__",
            name="未分组（分组缺失残留）",
            market="other",
            market_cn="其他",
            amount=round(amount, 2),
            pct=round(amount / total_value * 100, 1),
            avg_return_pct=_weighted_return(orphans, amount),
            verdict_cn="持仓数据引用的分组不存在，请检查 portfolio_groups 表。",
            holdings=[_to_holding_dto(h, exposures) for h in orphans],
        ))

    return PortfolioResponse(
        as_of=snap["as_of"],
        data_source_cn=snap["data_source_cn"],
        total_value=round(total_value, 2),
        holdings_count=len(all_holdings),
        observations=list(snap["observations"]),
        advices=[PortfolioAdviceDTO(**a.to_dict()) for a in advices],
        groups=group_dtos,
    )


def _to_holding_dto(h, exposures):  # noqa: ANN001
    exp = exposures.get(h.holding_id)
    return PortfolioHoldingDTO(
        holding_id=h.holding_id,
        name=h.name,
        code=h.code,
        market_value=round(h.market_value, 2),
        return_pct=h.return_pct,
        tags=list(h.tags),
        note=h.note,
        top10_total_pct=exp.top10_total_pct if exp else None,
        top10_by_market_pct=exp.by_market_pct if exp else {},
        report_quarter=exp.report_quarter if exp else None,
    )


def _weighted_return(hs, amount: float) -> float | None:  # noqa: ANN001
    """金额加权持有收益率：权重 = 当前市值。全部缺失时 None。

    近似口径（市值加权而非成本加权）：这里只做组间粗略对比展示，
    不是精确业绩归因；App 显示的逐只收益率才是精确口径。
    """
    valid = [(h.market_value, h.return_pct) for h in hs if h.return_pct is not None]
    if not valid or amount <= 0:
        return None
    weighted = sum(v * r for v, r in valid) / sum(v for v, _ in valid)
    return round(weighted, 2)
