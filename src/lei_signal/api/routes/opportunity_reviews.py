"""Source-bound opportunity reviews with a bounded, exact-symbol cache preparation."""

from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
import threading
import time
import traceback
import uuid
from contextlib import closing
from datetime import UTC, date, datetime, timedelta
from datetime import time as clock_time
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from lei_signal.api.config import sqlite_path
from lei_signal.copilot import opportunity_review as review
from lei_signal.storage.sqlite_store import connect

router = APIRouter(prefix="/api/opportunity-reviews", tags=["opportunity-reviews"])
_INIT_LOCK = threading.Lock()
_PREPARATION_TIMEOUT = 600.0
_PREPARATION_COOLDOWN = 60.0


class EnsureRequest(BaseModel):
    retry_failed: bool = False


def _technical_freshness(
    *, symbol: str, last_bar: date | None, timezone: str | None,
    bar_status: str, now: datetime,
) -> tuple[str, str]:
    """Compare this bar with the exchange's latest expected weekday bar."""
    from lei_signal.api.portfolio_workspace import _expected_bar_date, _fund_suffix
    from lei_signal.data.calendar import DEFAULT_TRADING_CALENDAR

    if timezone not in {"Asia/Shanghai", "Asia/Hong_Kong", "America/New_York"}:
        return "unknown", "无法核实交易所时区"
    if (timezone == "Asia/Shanghai" and not symbol.endswith((".SS", ".SZ"))
            or timezone == "Asia/Hong_Kong" and not symbol.endswith(".HK")
            or timezone == "America/New_York" and "." in symbol):
        return "unknown", "产品代码与交易所时区不一致"
    if last_bar is None or now.tzinfo is None:
        return "unknown", "缺少可核对的行情日期或查看时间"
    local = now.astimezone(ZoneInfo(timezone))
    close = clock_time(15) if timezone == "Asia/Shanghai" else clock_time(16)
    end = local.date() if local.time() >= close else local.date() - timedelta(days=1)
    expected_ts = DEFAULT_TRADING_CALENDAR.last_trading_day_in_range(
        end - timedelta(days=30), end
    )
    if expected_ts is None:
        return "unknown", "无法核实最近应有的交易日"
    expected = expected_ts.date()
    # Reuse the portfolio calendar contract where its symbol inference matches
    # the verified exchange. Its CN inference covers funds but not all stocks.
    if (timezone == "America/New_York"
            or timezone == "Asia/Shanghai" and _fund_suffix(symbol.partition(".")[0])):
        existing = _expected_bar_date(symbol, now)
        if existing is None or existing != expected.isoformat():
            return "unknown", "行情日期与现有交易日口径不一致"
    if last_bar > local.date():
        return "unknown", "行情日期晚于交易所当地日期"
    if last_bar < expected:
        return "stale", f"最近日 K 为{last_bar.isoformat()}，应至少覆盖{expected.isoformat()}"
    if bar_status == "unknown":
        return "unknown", "无法确认这根日 K 的来源和收盘状态"
    return "current", "行情日期覆盖最近应有交易日"


@router.get("/technical/{symbol}")
def technical_signals(request: Request, symbol: str) -> dict:
    """One exact-symbol analysis snapshot for its K line and dated signals."""
    return _technical_snapshot(request, symbol, cached_only=False)


def _technical_snapshot(
    request: Request, symbol: str, *, cached_only: bool, include_chart: bool = True,
) -> dict:
    """Build the same checked DTO; brief reads never fetch or queue analysis."""
    from lei_signal.api.bar_status import assess_bar_status
    from lei_signal.api.config import DETAIL_MAX_BARS
    from lei_signal.api.opportunity_signals import build_signal_rows
    from lei_signal.api.routes.opportunities import build_review
    from lei_signal.api.routes.symbols import _assessment_dto
    from lei_signal.copilot.subjects import display_name
    from lei_signal.domain.types import LONG_TREND_CN

    service = getattr(request.app.state, "analysis_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="技术分析服务不可用")
    if cached_only:
        entry = getattr(service, "_entries", {}).get(symbol)
        if entry is None:
            raise HTTPException(
                status_code=503, detail="该产品技术资料尚未读取，需先读取技术行情再查看简报"
            )
    else:
        entry = service.get(symbol)
    result = getattr(entry, "result", None)
    if result is None or getattr(entry, "error", None):
        raise HTTPException(status_code=503, detail="该产品技术资料不可用")
    if result.symbol != symbol:
        raise HTTPException(status_code=502, detail="技术资料产品身份不一致")
    if result.frame is None or len(result.frame.index) == 0:
        raise HTTPException(status_code=503, detail="该产品 K 线资料不可用")
    assessment = _assessment_dto(result)
    name = display_name(symbol, getattr(result, "display_name", None)) or symbol
    review = build_review(result, symbol=symbol, display_name=name)
    chart = None
    if include_chart:
        from lei_signal.ui.echarts_kline import serialize_result

        chart = serialize_result(result, color_mode="red_green", max_bars=DETAIL_MAX_BARS)
    report = result.price_data.report
    bar = assess_bar_status(
        last_date=report.last_date, fetched_at=getattr(entry, "fetched_at", None),
        timezone=getattr(result.price_data.info, "timezone", None),
        cache_fallback_used=bool(getattr(result, "cache_fallback_used", False)),
    )
    fetched = getattr(entry, "fetched_at", None)
    fetched_iso = fetched.isoformat() if fetched is not None else None
    last_bar = report.last_date.date().isoformat() if report.last_date is not None else None
    freshness, freshness_reason = _technical_freshness(
        symbol=symbol,
        last_bar=report.last_date.date() if report.last_date is not None else None,
        timezone=getattr(result.price_data.info, "timezone", None),
        bar_status=bar.status, now=datetime.now(UTC),
    )
    if last_bar != result.frame.index[-1].date().isoformat():
        freshness, freshness_reason = "unknown", "行情报告日期与图表最后一根日 K 不一致"
    snapshot_id = hashlib.sha256(
        f"{symbol}|{last_bar}|{fetched_iso}".encode()
    ).hexdigest()[:20]
    limitations = []
    if bar.status != "closed":
        limitations.append(
            "最后一根日 K 尚未确认为已收盘"
            if bar.status == "intraday"
            else "无法确认最后一根日 K 是否已收盘"
        )
    if freshness != "current":
        limitations.append(freshness_reason)
    if getattr(result, "cache_fallback_used", False):
        limitations.append("行情使用了旧缓存")
    if getattr(review, "degraded_cn", None):
        limitations.append(review.degraded_cn)
    weekly = getattr(result, "weekly_trend", None)
    weekly_state = None
    if weekly is not None and not weekly.empty and "long_trend" in weekly.columns:
        visible = weekly.loc[weekly.index <= result.frame.index[-1]]
        if not visible.empty:
            weekly_state = LONG_TREND_CN.get(str(visible["long_trend"].iloc[-1]))
    return {
        "symbol": symbol, "display_name": name,
        "as_of": assessment.as_of, "snapshot_id": snapshot_id,
        "generated_at": fetched_iso,
        "meta": {
            "provider": report.provider, "adjusted": report.adjusted,
            "data_time": fetched_iso, "last_bar_date": last_bar,
            "is_intraday_forming": bar.status == "intraday",
            "bar_status": bar.status, "status_reason": bar.reason,
            "freshness": freshness, "freshness_reason": freshness_reason,
        },
        "chart": chart,
        "trend": {
            "color": assessment.color, "color_cn": assessment.color_cn,
            "daily": assessment.stage_cn,
            "weekly": weekly_state,
        },
        "signals": build_signal_rows(result, review),
        "limitations": limitations,
    }


def _db_path(request: Request) -> str:
    return getattr(request.app.state, "plans_db_path", None) or sqlite_path()


def _select_current(db_path: str, run_id: str) -> None:
    with closing(connect(db_path)) as conn:
        review.select_current_run(conn, run_id)


def _process_review_and_select(db_path: str, run_id: str, *, retry_failed: bool = False) -> None:
    try:
        review.process_run(db_path, run_id, retry_failed=retry_failed)
    finally:
        # A failed review still has a saved partial board that the home page must show.
        _select_current(db_path, run_id)


@router.get("/recent")
def recent(request: Request, run_id: str | None = None) -> dict:
    """Read a selected board (or the latest for home) using existing cache only."""
    from lei_signal.api.recent_opportunities import (
        build_recent_opportunities,
        latest_saved_run,
    )

    if run_id is not None:
        if not re.fullmatch(r"orb_[a-f0-9]{16,64}", run_id):
            raise HTTPException(422, "审查批次编号无效")
        board = _saved_summary_board(request, run_id)
    else:
        board = latest_saved_run(_db_path(request))

    def cached(symbol: str) -> dict | None:
        try:
            return _technical_snapshot(request, symbol, cached_only=True, include_chart=False)
        except HTTPException:
            return None

    result = build_recent_opportunities(board, cached)
    # Holdings stay local. Their disclosed business links never turn a related
    # ETF event into a signal on the fund, or enter the external model payload.
    from lei_signal.api.opportunity_connections import build_opportunity_connections
    from lei_signal.api.portfolio_workspace import build_workspace

    try:
        workspace = build_workspace(request)
        result["related_holdings"] = build_opportunity_connections(
            result, workspace.get("items") or [],
            as_of=datetime.now(ZoneInfo("Asia/Shanghai")).date(),
        )
        result["connections_status"] = "available"
        result["connections_error"] = None
    except (HTTPException, sqlite3.Error, OSError, ValueError, KeyError, TypeError):
        result["related_holdings"] = {}
        result["connections_status"] = "unavailable"
        result["connections_error"] = "持仓关联资料暂未取得；已保留同产品技术事件"
    return result


def _registry(request: Request) -> tuple[threading.Lock, dict]:
    with _INIT_LOCK:
        registry = getattr(request.app.state, "opportunity_preparations", None)
        if registry is None:
            registry = (threading.Lock(), {})
            request.app.state.opportunity_preparations = registry
    return registry


def _closed(symbol: str, now: datetime) -> bool:
    cn = symbol.endswith((".SS", ".SZ"))
    local = now.astimezone(ZoneInfo("Asia/Shanghai" if cn else "America/New_York"))
    return local.time() >= (clock_time(15) if cn else clock_time(16))


def _targets(request: Request, snapshot: dict) -> list[str]:
    """Use only identities already selected by this board or a fund disclosure."""
    from lei_signal.api.portfolio_workspace import build_workspace

    symbols = {
        card["subject"]["id"]
        for card in snapshot.get("items") or []
        if card.get("intent") == "buy"
        and card.get("subject", {}).get("kind") == "symbol"
        and card["subject"].get("id")
    }
    try:
        holdings = build_workspace(request).get("items") or []
    except Exception:
        holdings = []  # The original snapshot already exposes the portfolio gap.
    for holding in holdings:
        if holding.get("symbol"):
            symbols.add(holding["symbol"])
        for reference in (holding.get("industry_reference") or {}).get("references") or []:
            if reference.get("symbol"):
                symbols.add(reference["symbol"])
    return sorted(symbols)


def _needs_fetch(request: Request, symbol: str, now: datetime) -> tuple[bool, bool]:
    """Return (fetch, force_refresh). A forming bar alone waits for the close."""
    from lei_signal.api.opportunity_evidence import _INTRADAY_GAP, _technical

    service = request.app.state.analysis_service
    entry = getattr(service, "_entries", {}).get(symbol)
    if entry is None:
        return True, False
    if getattr(entry, "error", None):
        fresh = getattr(service, "_is_fresh", None)
        return (not fresh(entry, symbol), False) if callable(fresh) else (False, False)
    _, _, problems = _technical(request, symbol, now)
    if not problems:
        fresh = getattr(service, "_is_fresh", None)
        return (not fresh(entry, symbol), False) if callable(fresh) else (False, False)
    if problems == [_INTRADAY_GAP] and not _closed(symbol, now):
        fresh = getattr(service, "_is_fresh", None)
        return (not fresh(entry, symbol), False) if callable(fresh) else (False, False)
    if set(problems).issubset({_INTRADAY_GAP, "技术资料使用旧缓存"}) and not _closed(symbol, now):
        return False, False
    if problems == ["技术资料使用旧缓存"]:
        # Repeated provider fallback cannot be improved by polling this page.
        return False, False
    return True, True


def _prepare(
    request: Request,
    preparation_id: str,
    symbols: list[str],
    db_path: str,
    retry_failed: bool = False,
) -> None:
    from lei_signal.api.opportunity_evidence import build_snapshot

    lock, registry = _registry(request)
    phase = "technical"
    try:
        service = request.app.state.analysis_service
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        ordinary, forced = [], []
        for symbol in symbols:
            needed, refresh = _needs_fetch(request, symbol, now)
            if needed:
                (forced if refresh else ordinary).append(symbol)
        if ordinary:
            service.get_many(ordinary, refresh=False, background=False)
        if forced:
            service.get_many(forced, refresh=True, background=False)
        snapshot = build_snapshot(request)
        from lei_signal.api.opportunity_context import macro_markets, prepare_context
        from lei_signal.api.opportunity_macro import prepare_macro

        phase = "macro"
        prepare_macro(request, macro_markets(snapshot))
        # One shared background refresh. Failure is recorded separately and must
        # not block the technical review or trigger a retry of successful agents.
        phase = "news"
        with lock:
            registry[preparation_id]["phase"] = phase
        if snapshot.get("items"):
            try:
                from lei_signal.api.opportunity_news import refresh_news
                from lei_signal.api.opportunity_summary_context import news_profiles

                refresh_news(db_path, profiles=news_profiles(snapshot))
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "opportunity news refresh: %s", type(exc).__name__
                )
                with lock:
                    registry[preparation_id]["news_error"] = type(exc).__name__

        while True:
            with lock:
                retry_failed = retry_failed or registry[preparation_id].get(
                    "retry_requested", False
                )
            phase = "context"
            prepare_context(request, snapshot, retry_failed=retry_failed)
            snapshot = build_snapshot(request)
            phase = "save_review"
            with closing(connect(db_path)) as conn:
                board, work = review.ensure_board(conn, snapshot, retry_failed=retry_failed)
            with lock:
                row = registry[preparation_id]
                if row["status"] != "running":
                    return
                # A retry arriving while the board was saved must run before review.
                if row.get("retry_requested") and not retry_failed:
                    continue
                row["run_id"] = board["run_id"]
                row["phase"] = "review"
            if work:
                phase = "review"
                if retry_failed:
                    review.process_run(db_path, board["run_id"], retry_failed=True)
                else:
                    review.process_run(db_path, board["run_id"])
            with lock:
                row = registry[preparation_id]
                if row["status"] != "running":
                    return
                if row.get("retry_requested") and not retry_failed:
                    continue
                row["phase"] = "select_current"
            phase = "select_current"
            _select_current(db_path, board["run_id"])
            with lock:
                row = registry[preparation_id]
                if row["status"] != "running":
                    return
                row.update(status="complete", finished=time.monotonic())
                break
    except Exception as exc:
        # Keep stack locations for diagnosis without logging account data or source responses.
        logging.getLogger(__name__).error(
            "opportunity preparation failed: %s (%s) at %s",
            type(exc).__name__,
            getattr(exc, "sqlite_errorname", "unclassified"),
            " -> ".join(
                f"{frame.name}:{frame.lineno}"
                for frame in traceback.extract_tb(exc.__traceback__)
            ),
        )
        if phase == "review":
            try:
                _select_current(db_path, registry[preparation_id]["run_id"])
            except Exception:
                logging.getLogger(__name__).exception("failed to select saved opportunity run")
        with lock:
            row = registry[preparation_id]
            row.update(
                error_phase=phase,
                error_code=getattr(exc, "sqlite_errorname", type(exc).__name__),
            )
            if phase == "review" and row.get("run_id"):
                row.update(
                    status="complete",
                    review_error=(
                        "资料已准备，模型审查未完成；本次已停止，请查看保留的事实与失败原因"
                    ),
                    finished=time.monotonic(),
                )
            elif row["status"] == "running":
                message = (
                    "公开资料保存暂未成功，已停止本次准备；已保存结果仍可查看"
                    if phase == "context"
                    and getattr(exc, "sqlite_errorname", "").startswith("SQLITE_BUSY")
                    else "资料准备未完成，请稍后重试"
                )
                row.update(
                    status="failed", error=message, finished=time.monotonic()
                )
    finally:
        with lock:
            row = registry[preparation_id]
            row["active_worker"] = False
            if row["status"] == "failed":
                row["finished"] = time.monotonic()


def _preparation(request: Request, preparation_id: str) -> dict | None:
    lock, registry = _registry(request)
    with lock:
        row = registry.get(preparation_id)
        if row is None:
            return None
        if (row["status"] == "running" and row.get("phase") not in {"review", "select_current"}
                and time.monotonic() - row["started"] >= _PREPARATION_TIMEOUT):
            row.update(status="failed", error="资料准备超时，请稍后重试", finished=time.monotonic())
        return {field: row[field] for field in (
            "id", "status", "run_id", "error", "error_phase", "error_code", "review_error",
        ) if field in row}


@router.post("/ensure")
def ensure(
    request: Request, background_tasks: BackgroundTasks, body: EnsureRequest | None = None
) -> dict:
    from lei_signal.api.opportunity_evidence import build_snapshot

    snapshot = build_snapshot(request)
    db_path = _db_path(request)
    retry_failed = bool(body and body.retry_failed)
    with closing(connect(db_path)) as conn:
        board, work = review.ensure_board(conn, snapshot)
    service = getattr(request.app.state, "analysis_service", None)
    if service is not None and callable(getattr(service, "get_many", None)):
        from lei_signal.api.opportunity_context import macro_markets, needs_context
        from lei_signal.api.opportunity_macro import read_macro

        symbols = _targets(request, snapshot)
        key = hashlib.sha256(
            (snapshot["as_of"] + "\n" + "\n".join(symbols)).encode()
        ).hexdigest()
        lock, registry = _registry(request)
        with lock:
            active = next(
                (r for r in reversed(list(registry.values()))
                 if r["key"] == key and r["active_worker"]), None
            )
            if active is not None:
                if retry_failed:
                    active["retry_requested"] = True
                board["preparation_id"] = active["id"]
                return board
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        needed = [symbol for symbol in symbols if _needs_fetch(request, symbol, now)[0]]
        macro_missing = any(
            read_macro(request, market, now)["status"] == "missing"
            for market in macro_markets(snapshot)
        )
        from lei_signal.api.opportunity_news import news_due
        from lei_signal.api.opportunity_summary_context import news_profiles

        news_missing = bool(snapshot.get("items")) and news_due(
            db_path, profiles=news_profiles(snapshot)
        )
        if needed or macro_missing or news_missing or needs_context(
            request, snapshot, retry_failed=retry_failed
        ) or work or retry_failed:
            with lock:
                prior = next(
                    (r for r in reversed(list(registry.values())) if r["key"] == key), None
                )
                if (
                    prior
                    and prior["status"] == "running"
                    and time.monotonic() - prior["started"] >= _PREPARATION_TIMEOUT
                ):
                    prior.update(
                        status="failed", error="资料准备超时，请稍后重试", finished=time.monotonic()
                    )
                if prior and prior["active_worker"]:
                    preparation_id = prior["id"]
                    if retry_failed:
                        prior["retry_requested"] = True
                elif (
                    prior
                    and not retry_failed
                    and time.monotonic() - prior.get("finished", 0) < _PREPARATION_COOLDOWN
                ):
                    preparation_id = prior["id"] if prior["status"] == "failed" else None
                else:
                    preparation_id = "opr_" + uuid.uuid4().hex
                    registry[preparation_id] = {
                        "id": preparation_id,
                        "key": key,
                        "status": "running",
                        "run_id": None,
                        "error": None,
                        "started": time.monotonic(),
                        "active_worker": True,
                    }
                    background_tasks.add_task(
                        _prepare,
                        request,
                        preparation_id,
                        symbols,
                        db_path,
                        retry_failed,
                    )
            if preparation_id:
                board["preparation_id"] = preparation_id
                if prior and preparation_id == prior["id"] and prior["status"] == "failed" and work:
                    if retry_failed:
                        background_tasks.add_task(
                            _process_review_and_select, db_path, board["run_id"], retry_failed=True
                        )
                    else:
                        background_tasks.add_task(
                            _process_review_and_select, db_path, board["run_id"]
                        )
                return board
    if retry_failed:
        with closing(connect(db_path)) as conn:
            board, work = review.ensure_board(conn, snapshot, retry_failed=True)
    if work:
        if retry_failed:
            background_tasks.add_task(
                _process_review_and_select, db_path, board["run_id"], retry_failed=True
            )
        else:
            background_tasks.add_task(_process_review_and_select, db_path, board["run_id"])
    else:
        _select_current(db_path, board["run_id"])
    return board


@router.get("/preparations/{preparation_id}")
def preparation(request: Request, preparation_id: str) -> dict:
    row = _preparation(request, preparation_id)
    if row is None:
        raise HTTPException(404, "机会资料准备记录不存在，请重新读取")
    return row


@router.get("/runs/{run_id}")
def run(request: Request, run_id: str) -> dict:
    with closing(connect(_db_path(request))) as conn:
        board = review.get_run(conn, run_id)
    if board is None:
        raise HTTPException(404, "机会复核批次不存在")
    lock, registry = _registry(request)
    with lock:
        rows = [row for row in registry.values() if row.get("run_id") == run_id]
        latest = rows[-1] if rows else None
        if (latest and latest.get("review_error")
                and not any(row.get("active_worker") for row in rows)):
            board["review_error"] = latest["review_error"]
    return board


def _saved_summary_board(request: Request, run_id: str) -> dict:
    # Summary reads must not run the main storage schema migrations.
    import sqlite3
    from pathlib import Path

    path = Path(_db_path(request)).resolve()
    if not path.is_file():
        raise HTTPException(404, "机会复核批次不存在")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
        board = review.get_run(conn, run_id)
    if board is None:
        raise HTTPException(404, "机会复核批次不存在")
    lock, registry = _registry(request)
    with lock:
        rows = [row for row in registry.values() if row.get("run_id") == run_id]
        # A stopped preparation can still provide saved facts. Never infer a
        # stop from pending status alone, or while another worker is active.
        stopped = rows[-1] if rows else None
        if (stopped and stopped.get("review_error")
                and not any(row.get("active_worker") for row in rows)):
            board["review_stopped"] = True
            board["review_error"] = stopped["review_error"]
    return board


def _summary_input(request: Request, run_id: str) -> tuple[dict, dict]:
    from lei_signal.api.opportunity_summary import _material

    if not re.fullmatch(r"orb_[a-f0-9]{16,64}", run_id):
        raise HTTPException(422, "审查批次编号无效")
    board = _saved_summary_board(request, run_id)

    def cached(symbol: str) -> dict | None:
        try:
            return _technical_snapshot(request, symbol, cached_only=True, include_chart=False)
        except HTTPException:
            return None

    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    return _material(
        board, cached, narrative_as_of=today, market_watch=_market_watch(request, board, today),
        compact=True
    )


def _market_watch(request: Request, board: dict, today: date) -> dict:
    from lei_signal.api.opportunity_market_watch import build_market_watch
    from lei_signal.api.opportunity_news import read_news
    from lei_signal.api.opportunity_summary_context import news_profiles, recent_news_watch

    local_now = datetime.now(ZoneInfo("Asia/Shanghai"))
    completed = today if local_now.time() >= clock_time(15) else today - timedelta(days=1)
    result = build_market_watch(as_of=today, db_path=_db_path(request), completed_through=completed)
    news = recent_news_watch(
        board, today, automated=read_news(_db_path(request), today, news_profiles(board))
    )
    lock, registry = _registry(request)
    with lock:
        news["news_update"]["refreshing"] = any(r.get("active_worker") for r in registry.values())
    result.update(news)
    result["limitations"] = list(
        dict.fromkeys(result.get("limitations", []) + news["news_limitations"])
    )
    return result


@router.post("/runs/{run_id}/market-watch/refresh")
def refresh_market_news(request: Request, run_id: str) -> dict:
    """An explicit bounded source refresh; no technical/model/trading writes."""
    from lei_signal.api.opportunity_news import refresh_news
    from lei_signal.api.opportunity_summary_context import news_profiles

    if not re.fullmatch(r"orb_[a-f0-9]{16,64}", run_id):
        raise HTTPException(422, "审查批次编号无效")
    board = _saved_summary_board(request, run_id)
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    refreshed = refresh_news(_db_path(request), today, news_profiles(board), force=True)
    result = _market_watch(request, board, today)
    result["news_update"]["refresh"] = refreshed.get("refresh", {})
    return result


@router.get("/runs/{run_id}/market-watch")
def market_watch(request: Request, run_id: str) -> dict:
    """One shared five-day view; cached public data only, no model or data refresh."""
    if not re.fullmatch(r"orb_[a-f0-9]{16,64}", run_id):
        raise HTTPException(422, "审查批次编号无效")
    board = _saved_summary_board(request, run_id)
    return _market_watch(request, board, datetime.now(ZoneInfo("Asia/Shanghai")).date())


@router.get("/runs/{run_id}/summary")
def get_summary(request: Request, run_id: str) -> dict:
    """Poll a saved Agent summary without starting work or writing a database."""
    from lei_signal.api.opportunity_summary import read

    material, _ = _summary_input(request, run_id)
    return read(_db_path(request), run_id, material)


@router.post("/runs/{run_id}/summary")
def post_summary(request: Request, run_id: str) -> dict:
    """Explicitly request one bounded Agent call for this saved input."""
    from lei_signal.api.opportunity_summary import start

    material, local = _summary_input(request, run_id)
    if (material["review_status"] not in {"complete", "partial"}
            and not material.get("review_stopped")):
        raise HTTPException(409, "本批审查仍在进行，请等本批结果保存后再总结")
    try:
        return start(_db_path(request), run_id, material, local)
    except RuntimeError as exc:
        if str(exc) == "summary_busy":
            raise HTTPException(503, "已有一项机会总结正在进行，请稍后重试") from exc
        raise


@router.get("/cards/{review_id}")
def card(request: Request, review_id: str) -> dict:
    with closing(connect(_db_path(request))) as conn:
        found = review.get_card(conn, review_id)
    if found is None:
        raise HTTPException(404, "机会复核卡不存在")
    return found


@router.get("/runs/{run_id}/brief")
def product_brief(request: Request, run_id: str, subject_key: str) -> dict:
    """One read-only product view shared by the web page and query Skill."""
    from lei_signal.api.opportunity_brief import build_product_brief

    if not re.fullmatch(r"orb_[a-f0-9]{16,64}", run_id):
        raise HTTPException(422, "审查批次编号无效")
    if not re.fullmatch(r"(?:symbol:[A-Za-z0-9.^_-]{1,32}|holding:[a-f0-9]{12})", subject_key):
        raise HTTPException(422, "产品身份无效")
    board = run(request, run_id)
    selected = next(
        (item for item in board["items"] if item["card"]["subject"]["key"] == subject_key),
        None,
    )
    if selected is None:
        raise HTTPException(404, "本批审查没有这个产品")
    subject = selected["card"]["subject"]
    symbol = subject.get("id") if subject.get("kind") == "symbol" else subject.get("symbol")
    technical, market, errors = None, None, {}
    if symbol:
        try:
            technical = _technical_snapshot(request, symbol, cached_only=True)
        except HTTPException as exc:
            errors["technical"] = str(exc.detail)
    if subject.get("kind") == "holding":
        try:
            market = holding_market(request, subject["id"])
        except HTTPException as exc:
            errors["market"] = str(exc.detail)
    return build_product_brief(
        board, subject_key, technical=technical, market=market, errors=errors,
    )


@router.get("/market/holdings/{holding_id}")
def holding_market(request: Request, holding_id: str, refresh: bool = False) -> dict:
    """Read one holding's NAV line and disclosed industry references on demand."""
    from lei_signal.api.opportunity_market import market_holding

    return market_holding(request, holding_id, refresh=refresh)
