"""我的持仓 REST 路由（持仓体检页）。

GET /api/portfolio 返回整份快照：分组 + 持仓 + 组合级提示 + 季报穿透
暴露 + 调仓建议（R1~R7）。汇总（组金额/占比/加权收益率）与建议判定
都在 Python 层完成，前端只做展示——与全站「UI 不重新计算」一致。
分组结论与穿透结果都是叙事标注层，不参与任何信号判定。

GET /api/portfolio/nav-series 返回若干只基金的全量净值（单位/累计/
当日增长率），供「涨跌幅视角」净值对比图使用：只是把外部数据搬进
系统换个更不易失真的画法，同样不参与信号判定。
"""
from __future__ import annotations

import time as time_mod
from contextlib import closing
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, Request

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.schemas import (
    FundNavErrorDTO,
    FundNavItemDTO,
    FundNavSeriesResponse,
    PortfolioAdviceDTO,
    PortfolioGroupDTO,
    PortfolioHoldingDTO,
    PortfolioResponse,
)
from lei_signal.portfolio.advisor import build_advices
from lei_signal.portfolio.funddata import fetch_nav_full
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

# 净值全量抓取的结果缓存（funddata 层有 0.8s/请求限速，净值一天只更新
# 一次，缓存能把「选 6 只基金」的二次加载从 ~5s 降到 0）。
_NAV_CACHE: dict[str, tuple[float, object]] = {}
_NAV_CACHE_TTL_OK = 6 * 3600.0
_NAV_CACHE_TTL_MISS = 10 * 60.0
_NAV_MAX_CODES = 8


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


def _cached_nav_full(code: str):
    """带 TTL 的模块级缓存（见 _NAV_CACHE 注释）；异常向上抛给调用方收集。"""
    hit = _NAV_CACHE.get(code)
    now = time_mod.monotonic()
    if hit is not None:
        ts, data = hit
        ttl = _NAV_CACHE_TTL_OK if data is not None else _NAV_CACHE_TTL_MISS
        if now - ts < ttl:
            return data
    data = fetch_nav_full(code)
    _NAV_CACHE[code] = (now, data)
    return data


@router.get("/portfolio/nav-series", response_model=FundNavSeriesResponse)
def get_nav_series(
    codes: str = Query(..., description="逗号分隔的基金代码（6 位数字）"),
    days: int = Query(1095, ge=0, le=4000, description="窗口天数；0 = 成立以来全量"),
) -> FundNavSeriesResponse:
    code_list: list[str] = []
    for raw in codes.split(","):
        c = raw.strip()
        if not c:
            continue
        if not (c.isdigit() and len(c) == 6):
            raise HTTPException(status_code=400, detail=f"基金代码应为 6 位数字：{c}")
        if c not in code_list:
            code_list.append(c)
    if not code_list:
        raise HTTPException(status_code=400, detail="未提供有效的基金代码")
    if len(code_list) > _NAV_MAX_CODES:
        raise HTTPException(
            status_code=400,
            detail=f"一次最多对比 {_NAV_MAX_CODES} 只基金（外部接口有限速）",
        )

    cutoff = (date.today() - timedelta(days=days)).isoformat() if days > 0 else ""
    items: list[FundNavItemDTO] = []
    errors: list[FundNavErrorDTO] = []
    for c in code_list:
        try:
            full = _cached_nav_full(c)
        except Exception as exc:  # noqa: BLE001 —— 单只失败不拖垮整批，收集原因
            errors.append(FundNavErrorDTO(
                code=c, reason_cn=f"取数失败（{type(exc).__name__}），稍后重试或检查代码"))
            continue
        if full is None:
            errors.append(FundNavErrorDTO(
                code=c,
                reason_cn="接口没有返回这只基金的净值数据（代码可能不对，或该基金暂无净值）"))
            continue
        start = 0
        if cutoff:
            for i, d in enumerate(full.dates):
                if d >= cutoff:
                    start = i
                    break
            else:
                start = len(full.dates) - 1  # 窗口内无数据时至少保留最新一天
        items.append(FundNavItemDTO(
            code=full.code, name=full.name,
            dates=full.dates[start:],
            unit_nav=full.unit_nav[start:],
            acc_nav=full.acc_nav[start:],
            day_pct=full.day_pct[start:],
        ))
    return FundNavSeriesResponse(days=days, items=items, errors=errors)
