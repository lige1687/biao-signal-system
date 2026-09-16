"""研究层路由：信号含金量表等研究展示（判定权仍在规则层，这里只读展示）。

- GET /api/research/signal-edge  路牌+触发事件的历史胜率/赔率 vs 无条件基准

数据来自 AnalysisService（TTL 缓存，与看盘页同一份分析结果），跨标的池化
统计（research/signpost_stats.py）。本路由不改任何判定逻辑。
"""
from __future__ import annotations

import logging
from contextlib import closing
from typing import Any

from fastapi import APIRouter, Query, Request

from lei_signal.api.schemas import (
    SignalEdgeHorizonDTO,
    SignalEdgeResponse,
    SignalEdgeRowDTO,
)
from lei_signal.research.signpost_stats import build_signal_edge_report
from lei_signal.storage.sqlite_store import connect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])


def _default_symbols(request: Request) -> list[str]:
    """默认统计池 = 当前自选（有界，且都是用户真实看的标的）。"""
    from lei_signal.api.watchlist import list_watchlist

    try:
        with closing(connect(request.app.state.watchlist_db_path)) as conn:
            return [item.symbol for item in list_watchlist(conn)]
    except Exception as exc:  # noqa: BLE001 - 自选读不到不炸接口
        logger.warning("signal-edge 自选列表读取失败: %s", exc)
        return []


@router.get("/signal-edge", response_model=SignalEdgeResponse)
def get_signal_edge(
    request: Request,
    symbols: str | None = Query(
        None, description="逗号分隔标的列表；缺省=当前自选"
    ),
    refresh: bool = Query(False, description="true=绕过分析缓存强制重算"),
) -> SignalEdgeResponse:
    """信号含金量表：事件出现后 N 日的胜率/收益/盈亏比 vs 无条件基准。

    研究展示层——统计结果不回写判定、不做过滤器（任务书 #1 红线）。
    """
    wanted = (
        [s.strip() for s in symbols.split(",") if s.strip()]
        if symbols
        else _default_symbols(request)
    )
    wanted = list(dict.fromkeys(wanted))[:60]  # 有界：单次最多 60 只
    if not wanted:
        return SignalEdgeResponse(
            disclaimer_cn="自选列表为空，无法统计。请先在自选里加入标的。",
        )

    service = request.app.state.analysis_service
    entries = service.get_many(wanted, refresh=refresh)

    samples = []
    used: list[str] = []
    failed: list[str] = []
    for symbol in wanted:
        entry = entries.get(symbol)
        if entry is None or entry.result is None:
            failed.append(symbol)
            continue
        result = entry.result
        if getattr(result, "frame", None) is None or len(result.frame.index) == 0:
            failed.append(symbol)
            continue
        samples.append((result.frame, result.events))
        used.append(symbol)

    report = build_signal_edge_report(samples)
    if report is None:
        return SignalEdgeResponse(
            symbols_failed=failed,
            disclaimer_cn="没有任何标的能完成分析（行情缺失或数据不足）。",
        )

    rows = [
        SignalEdgeRowDTO(
            key=row.key,
            label_cn=row.label_cn,
            group=row.group,
            direction_cn=row.direction_cn,
            total_signals=row.total_signals,
            horizons=[
                SignalEdgeHorizonDTO(
                    horizon=h.horizon,
                    sample_count=h.sample_count,
                    incomplete_count=h.incomplete_count,
                    win_rate=h.win_rate,
                    baseline_win_rate=h.baseline_win_rate,
                    excess_win_rate=h.excess_win_rate,
                    mean_return=h.mean_return,
                    baseline_mean_return=h.baseline_mean_return,
                    excess_mean_return=h.excess_mean_return,
                    payoff=h.payoff,
                    baseline_payoff=h.baseline_payoff,
                )
                for h in row.horizons
            ],
        )
        for row in report.rows
    ]
    response = SignalEdgeResponse(
        n_symbols=report.n_symbols,
        start_date=report.start_date,
        end_date=report.end_date,
        symbols_used=used,
        symbols_failed=failed,
        disclaimer_cn=report.disclaimer_cn,
        rows=rows,
    )
    return response


__all__: list[Any] = ["router"]
