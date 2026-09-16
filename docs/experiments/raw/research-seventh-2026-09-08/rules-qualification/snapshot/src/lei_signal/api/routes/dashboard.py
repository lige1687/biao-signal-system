"""仪表盘批量卡片端点 + 卡片组装（供 refresh 端点复用）。"""
from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime

from fastapi import APIRouter, Request

from lei_signal.api import config
from lei_signal.api.card_mapper import build_card
from lei_signal.api.schemas import CardDTO, DashboardResponse
from lei_signal.api.services import AnalysisEntry, AnalysisService
from lei_signal.api.watchlist import WatchlistItem, list_watchlist
from lei_signal.data.symbols import MARKET_CN
from lei_signal.storage.sqlite_store import connect

router = APIRouter(prefix="/api", tags=["dashboard"])

# 友好名（ETF/股票中文名）几乎不变，进程内永久缓存，避免每次 dashboard 都对
# 每只标的串行发 HTTP 抓名。命中缓存零成本，未命中才走网络。
_FRIENDLY_NAME_CACHE: dict[str, str] = {}
_FRIENDLY_NAME_LOCK = threading.Lock()


def _cached_friendly_name(
    provider: Callable[[str], str | None], symbol: str
) -> str | None:
    """带永久缓存的友好名查找。命中直接返回；未命中调 provider 后存入。"""
    with _FRIENDLY_NAME_LOCK:
        cached = _FRIENDLY_NAME_CACHE.get(symbol)
    if cached is not None:
        return cached
    try:
        name = provider(symbol)
    except Exception:  # noqa: BLE001
        return None
    if name and name != symbol:
        with _FRIENDLY_NAME_LOCK:
            _FRIENDLY_NAME_CACHE[symbol] = name
        return name
    return None


def _service(request: Request) -> AnalysisService:
    return request.app.state.analysis_service


def _db_path(request: Request) -> str:
    return request.app.state.watchlist_db_path


def load_watchlist(db_path: str) -> list[WatchlistItem]:
    with closing(connect(db_path)) as conn:
        return list_watchlist(conn)


def dashboard_symbols(db_path: str) -> tuple[list[tuple[str, str]], list[WatchlistItem]]:
    """(默认大盘 (symbol, group), 自选股)。自选中与大盘重复的符号跳过，避免卡片重复。"""
    indices = [(idx.symbol, "index") for idx in config.DASHBOARD_INDICES]
    index_symbols = {symbol for symbol, _ in indices}
    watchlist = [item for item in load_watchlist(db_path) if item.symbol not in index_symbols]
    return indices, watchlist


def _resolve_display(
    symbol: str,
    stored: WatchlistItem | None,
    entry: AnalysisEntry,
) -> tuple[str, str]:
    """展示名与市场标签：大盘覆盖 > 海外中文名 > 分析结果 > 自选股存储 > 符号本身。

    注意顺序：自选股即便有 stored.display_name（可能为空或陈旧），
    也**优先用最新一次成功分析得到的名称**——一来 ETF 名称本来就
    由 provider 给出（如「创业板ETF易方达」），二来可顺带回填到存储。

    海外指数/ETF（Yahoo 只给英文 longName）套用 ``OVERSEAS_NAME_CN``
    的「中文名 + 缩写」，如 QQQ → 「纳指100 QQQ」。
    """
    override = config.INDEX_OVERRIDES.get(symbol)
    if override is not None:
        return override.display_name, override.market_cn
    overseas_cn = config.OVERSEAS_NAME_CN.get(symbol)
    if overseas_cn is not None:
        market_cn = (
            entry.result.price_data.info.market_cn
            if entry.result is not None
            else (MARKET_CN.get(stored.market, stored.market) if stored else "美股")
        )
        return overseas_cn, market_cn
    if entry.result is not None:
        name = entry.result.display_name
        # 缓存兜底时 display_name 会退回 symbol；板块在此回填中文名
        if name == symbol and symbol.startswith("TH"):
            from lei_signal.api.labels import THS_INDUSTRY_NAMES
            code = symbol[2:8]
            name = THS_INDUSTRY_NAMES.get(code, symbol)
        return name, entry.result.price_data.info.market_cn
    if stored is not None:
        # 无分析结果时退回存储名（可能为 None → 显示 symbol）
        name = stored.display_name or symbol
        return name, MARKET_CN.get(stored.market, stored.market)
    return symbol, ""




def assemble_dashboard(
    service: AnalysisService,
    db_path: str,
    *,
    refresh: bool = False,
    friendly_name_provider: Callable[[str], str | None] | None | bool = None,
    group: str | None = None,
) -> DashboardResponse:
    """``friendly_name_provider``：

    - None（默认）：用进程内 ``TencentQuoteProvider`` 抓 A 股友好名。
    - callable：注入实例（测试或未来用其他源）。
    - callable 返回 None/抛异常：该标的不覆盖。

    友好名仅在「分析结果没有中文名」时才会去抓：要么 ``display_name`` 仍是
    符号本身，要么名字是纯英文（Yahoo v8 ``longName``）。前两个判断都通过
    时（真的没名或名是英文），才用 ``TencentQuoteProvider`` 抓 A 股友好名。
    海外指数不在范围（A 股 ETF/股票才有中文名），大盘 override 优先。
    """
    indices, watchlist = dashboard_symbols(db_path)
    # group 过滤：前端拆指数/自选两个请求时只算一组，先到先渲染。
    if group == "index":
        watchlist = []
    elif group == "watchlist":
        indices = []
    symbols = [symbol for symbol, _ in indices] + [item.symbol for item in watchlist]
    entries = service.get_many(symbols, refresh=refresh)

    if friendly_name_provider is None or friendly_name_provider is True:
        # 默认行为：用 TencentQuoteProvider 抓 A 股 ETF/股票友好名。
        from lei_signal.api.quotes import TencentQuoteProvider

        quote_source = TencentQuoteProvider()

        def default_lookup(symbol: str) -> str | None:
            try:
                snap = quote_source.fetch(symbol)
            except Exception:  # noqa: BLE001
                return None
            return snap.display_name if snap and snap.display_name else None

        name_provider: Callable[[str], str | None] = default_lookup
    elif friendly_name_provider is False:

        def _disabled_lookup(_symbol: str) -> str | None:
            # 显式禁用：单测中不发起真实网络
            return None

        name_provider = _disabled_lookup
    else:
        name_provider = friendly_name_provider

    # 收集需要补中文名的标的（已有中文名或大盘 override 的跳过），再并发抓取。
    # A 股 ETF 常因 Yahoo v8 兜底拿到英文 longName，此时问腾讯要中文名。
    # 串行循环曾是首页最大延迟源（N 只 = N 次顺序 HTTP），改并发 + 缓存后
    # 首次最多 8 路并发，之后命中缓存零成本。
    candidates: list[str] = []
    for symbol in symbols:
        if config.INDEX_OVERRIDES.get(symbol) is not None:
            continue
        # 海外指数/ETF 已有中文名覆盖表，不必问腾讯（它只认 A 股，必然失败）
        if config.OVERSEAS_NAME_CN.get(symbol) is not None:
            continue
        entry = entries.get(symbol)
        current = (
            entry.result.display_name
            if (entry is not None and entry.result is not None)
            else symbol
        )
        if current and current != symbol and any(
            "一" <= ch <= "鿿" for ch in current
        ):
            continue
        candidates.append(symbol)

    name_overrides: dict[str, str] = {}
    if candidates:
        with ThreadPoolExecutor(max_workers=min(8, len(candidates))) as pool:
            future_map = {
                pool.submit(_cached_friendly_name, name_provider, s): s
                for s in candidates
            }
            for fut, sym in future_map.items():
                name = fut.result()
                if name and name != sym:
                    name_overrides[sym] = name

    cards: list[CardDTO] = []
    for symbol, group in indices:
        entry = entries[symbol]
        name, market_cn = _resolve_display(symbol, None, entry)
        if symbol in name_overrides and not (
            name and any("一" <= ch <= "鿿" for ch in name)
        ):
            # 分析拿到的名是英文（Yahoo v8 longName）→ 替换为中文友好名。
            name = name_overrides[symbol]
        cards.append(
            build_card(
                symbol=symbol,
                display_name=name,
                market_cn=market_cn,
                group=group,
                result=entry.result,
                error=entry.error,
                data_time=entry.fetched_at,
                persist_warning=entry.persist_conflict,
            )
        )
    for item in watchlist:
        entry = entries[item.symbol]
        name, market_cn = _resolve_display(item.symbol, item, entry)
        if item.symbol in name_overrides and not (
            name and any("一" <= ch <= "鿿" for ch in name)
        ):
            name = name_overrides[item.symbol]
        cards.append(
            build_card(
                symbol=item.symbol,
                display_name=name,
                market_cn=market_cn,
                group="watchlist",
                result=entry.result,
                error=entry.error,
                data_time=entry.fetched_at,
                persist_warning=entry.persist_conflict,
            )
        )

    return DashboardResponse(
        generated_at=datetime.now(UTC).isoformat(),
        quote_ttl_seconds=service.ttl_seconds,
        cards=cards,
        disclaimer_cn=config.DISCLAIMER_CN,
    )


@router.get("/dashboard/cards", response_model=DashboardResponse)
def dashboard_cards(
    request: Request, refresh: bool = False, group: str | None = None
) -> DashboardResponse:
    """仪表盘卡片。

    ``group``: ``index`` 只返回大盘、``watchlist`` 只返回自选、缺省全部。
    前端拆成两个请求时用，先到先渲染。

    友好名获取源通过 ``app.state.friendly_name_provider`` 注入：
    - 未设置（attribute missing）：默认用 TencentQuoteProvider（A 股友好名）。
    - callable：注入实例（测试或未来用其他源）。
    - 显式 ``True``：等价于未设置（默认），写出来便于自文档。
    - 显式 ``False``：禁用友好名回退（单测，避免真实网络）。
    """
    if not hasattr(request.app.state, "friendly_name_provider"):
        provider: Callable[[str], str | None] | bool | None = True  # 默认
    else:
        provider = request.app.state.friendly_name_provider
    return assemble_dashboard(
        _service(request),
        _db_path(request),
        refresh=refresh,
        friendly_name_provider=provider,
        group=group,
    )
