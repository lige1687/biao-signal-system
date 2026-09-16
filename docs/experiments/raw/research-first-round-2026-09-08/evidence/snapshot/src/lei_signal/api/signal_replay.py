"""历史交易日信号回放：analyze(as_of=day) 截断行情后重跑既有规则，落两表。

设计（docs/superpowers/specs/2026-08-23-signal-replay-design.md）：
- 无前视由 pipeline.analyze 的 as_of 截断保证（pipeline.py:217-218），本模块零判定；
- 绕过 AnalysisService TTL 缓存（key 不含日期），直接调 pipeline.analyze；
- 回放不显示「已有计划」（active_plan_ids=()，计划是当下事实）；
- 写 signal_alerts + daily_opportunity_scan 两表 scan_date=day, as_of='close'，幂等重写；
- 快照优先：GET 侧有快照秒开，本模块只负责补算。
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, date, datetime
from typing import Any

from lei_signal.api import config
from lei_signal.api.opportunity_scan import (
    upsert_scan_results,
)
from lei_signal.api.routes.opportunities import (
    VERDICT_NONE,
    build_review,
)
from lei_signal.api.schemas import ScanItemDTO
from lei_signal.api.sell_signals import extract_sell_signals
from lei_signal.api.signal_alerts_store import (
    SIDE_SELL,
    SIDE_UNAVAILABLE,
    SignalAlertRow,
    upsert_signal_alerts,
)
from lei_signal.api.signal_scan import AS_OF_CLOSE
from lei_signal.compose.pipeline import analyze
from lei_signal.storage.sqlite_store import connect


def _replay_one(
    symbol: str, day: date, db_path: str,
) -> tuple[ScanItemDTO | None, list[SignalAlertRow], SignalAlertRow | None]:
    """单标的回放：返回 (买点行或None, 卖点行, 不可用行或None)。"""
    try:
        result = analyze(
            symbol, as_of=day,
            cache_root=config.cache_root(), sqlite_path=db_path,
        )
    except Exception as exc:  # noqa: BLE001  单标的失败不影响整体
        return None, [], SignalAlertRow(
            scan_date=day.isoformat(), symbol=symbol, display_name=symbol,
            side=SIDE_UNAVAILABLE, tier="hard", kind="data_unavailable",
            title="数据不可用", error=f"{type(exc).__name__}: {exc}",
        )
    if result is None or getattr(result, "frame", None) is None or len(result.frame.index) == 0:
        return None, [], SignalAlertRow(
            scan_date=day.isoformat(), symbol=symbol, display_name=symbol,
            side=SIDE_UNAVAILABLE, tier="hard", kind="data_unavailable",
            title="数据不可用", error="分析结果为空",
        )
    display_name = getattr(result, "display_name", "") or symbol
    review = build_review(result, symbol=symbol, display_name=display_name, active_plan_ids=())
    buy: ScanItemDTO | None = None
    if review.verdict != VERDICT_NONE:
        best = review.candidates[0] if review.candidates else None
        if best is None and review.resonance_groups:
            best = review.resonance_groups[0].candidates[0]
        missing = "；".join(w.text_cn for w in review.watch_conditions[:2])
        buy = ScanItemDTO(
            symbol=symbol, display_name=review.display_name,
            verdict=review.verdict, verdict_cn=review.verdict_cn,
            best_scenario_cn=best.scenario_cn if best else None,
            best_state=best.state if best else None,
            reward_risk_ratio=best.reward_risk_ratio if best else None,
            reward_risk_computable=bool(best.reward_risk_computable) if best else False,
            blocking_reasons=(
                list(review.tradability.blocking_reasons) if review.tradability else []
            ),
            missing_summary_cn=missing, has_active_plan=False,
        )
    sell = [
        SignalAlertRow(
            scan_date=day.isoformat(), symbol=symbol, display_name=display_name,
            side=SIDE_SELL, tier=s.tier, kind=s.kind, kind_cn=s.kind_cn,
            title=s.title, reason_cn=s.reason_cn, is_new=s.is_new,
            key_prices=dict(s.key_prices), provenance=s.provenance,
            available_date=s.available_date,
        )
        for s in extract_sell_signals(result)
    ]
    return buy, sell, None


def run_signal_replay(
    db_path: str,
    day: date,
    *,
    symbols: list[str] | None = None,
    max_workers: int = 4,
) -> dict:
    """回放 day 交易日：当前自选 × 截断行情，整体重写两表。"""
    if symbols is None:
        from lei_signal.api.watchlist import list_watchlist  # noqa: PLC0415

        with closing(connect(db_path)) as conn:
            symbols = [i.symbol for i in list_watchlist(conn)]
    wanted = list(symbols)
    day_str = day.isoformat()

    outcomes: dict[str, Any] = {}
    if wanted:
        # 首标的串行预热 V8（mini_racer 并发初始化会崩, 同 daily_scan.py 规避）
        outcomes[wanted[0]] = _replay_one(wanted[0], day, db_path)
        if len(wanted) > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    s: pool.submit(_replay_one, s, day, db_path) for s in wanted[1:]
                }
                for s, fut in futures.items():
                    outcomes[s] = fut.result()

    buy_items: list[ScanItemDTO] = []
    sell_rows: list[SignalAlertRow] = []
    for s in wanted:
        buy, sells, unavailable = outcomes.get(s, (None, [], None))
        if unavailable is not None:
            buy_items.append(ScanItemDTO(
                symbol=s, verdict=VERDICT_NONE, verdict_cn="当前无机会",
                error=unavailable.error,
            ))
            sell_rows.append(unavailable)
            continue
        if buy is not None:
            buy_items.append(buy)
        sell_rows.extend(sells)

    with closing(connect(db_path)) as conn:
        upsert_scan_results(conn, day_str, buy_items)
        upsert_signal_alerts(conn, day_str, AS_OF_CLOSE, sell_rows)

    return {
        "scan_date": day_str,
        "as_of": AS_OF_CLOSE,
        "scanned": len(wanted),
        "buy_rows": sum(1 for it in buy_items if not it.error),
        "sell_rows": sum(1 for r in sell_rows if r.side == SIDE_SELL),
        "unavailable": sum(1 for r in sell_rows if r.side == SIDE_UNAVAILABLE),
        "generated_at": datetime.now(UTC).isoformat(),
    }


__all__ = ["run_signal_replay"]
