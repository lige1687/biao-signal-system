"""分析服务：TTL 缓存 + 并发批量 + 单标的失败隔离。

设计要点（与计划 R1/R6/R7 对应）：
- 单一层缓存：AnalysisResult 内含最新价（腾讯/东财/Yahoo 日线端点盘中返回
  当日形成中 bar），行情与信号永远来自同一份数据，不存在两层不一致。
- TTL 到期即重跑 analyze()：内部负责重新抓行情、写 Parquet 缓存、
  网络失败时回退缓存（cache_fallback_used=True 透出为 stale）。
  无后台调度——没人看就不抓，匹配「每天看 2-3 次」的使用频率。
- 错误条目用更短的 TTL，避免一次网络抖动把卡片锁死 15 分钟。
- 线程池并发按标的隔离：单个标的失败只产生 error 条目，不影响其他标的。
"""
from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime

from lei_signal.api import config, session as market_session
from lei_signal.api.realtime import CacheFirstProvider, IntradayOverlayProvider
from lei_signal.compose.pipeline import AnalysisResult, analyze
from lei_signal.data.calendar import DEFAULT_TRADING_CALENDAR, TradingCalendar
from lei_signal.data.providers import PriceProvider, _classify_error, default_provider
from lei_signal.data.symbols import is_a_share, resolve_symbol
from lei_signal.data.validation import DataUnavailableError
from lei_signal.storage.sqlite_store import EventIdentityConflictError

#: 与 compose.pipeline.analyze 同签名（可注入替身用于测试）。
AnalyzeFn = Callable[..., AnalysisResult]


@dataclass(frozen=True, slots=True)
class AnalysisEntry:
    """单标的分析快照：result 与 error 必有其一。

    ``persist_conflict`` 记录「分析成功但研究库拒绝写入」的情况
    （见 AnalysisService._run 中的 EventIdentityConflictError 处理）。
    """

    result: AnalysisResult | None
    error: str | None
    fetched_at: datetime
    persist_conflict: str | None = None


class AnalysisService:
    """按 symbol 缓存分析结果的进程内服务（单 uvicorn worker 前提）。"""

    def __init__(
        self,
        *,
        analyze_fn: AnalyzeFn | None = None,
        cache_root: str | None = None,
        sqlite_path: str | None = None,
        ttl_seconds: int | None = None,
        error_ttl_seconds: int = config.ERROR_TTL_SECONDS,
        calendar: TradingCalendar | None = None,
        max_workers: int = 4,
        provider: PriceProvider | None = None,
    ) -> None:
        self._analyze_fn: AnalyzeFn = analyze_fn or analyze
        self._cache_root = cache_root if cache_root is not None else config.cache_root()
        self._sqlite_path = sqlite_path if sqlite_path is not None else config.sqlite_path()
        self._ttl_seconds = ttl_seconds if ttl_seconds is not None else config.quote_ttl_seconds()
        self._error_ttl_seconds = error_ttl_seconds
        self._calendar = calendar or DEFAULT_TRADING_CALENDAR
        self._max_workers = max_workers
        # 海外指数路径：缓存优先（30min 避免 Yahoo 限流）→ 实时 bar 叠加。
        # A 股不包缓存优先：日线本就是当前 bar。
        # Streamlit 研究页仍走 analyze() 默认链路，不动。
        chain = default_provider()
        self._overseas_provider: PriceProvider = IntradayOverlayProvider(
            CacheFirstProvider(chain, cache_root=self._cache_root),
            cache_root=self._cache_root,
        )
        self._default_provider: PriceProvider = chain
        self._provider: PriceProvider = provider or self._default_provider
        self._entries: dict[str, AnalysisEntry] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    def _lock_for(self, symbol: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(symbol, threading.Lock())

    def _is_fresh(self, entry: AnalysisEntry, symbol: str) -> bool:
        now = datetime.now(UTC)
        # 错误条目始终用短 TTL：网络抖动不应被收盘长缓存锁死，尽快重试。
        if entry.error is not None:
            age = (now - entry.fetched_at).total_seconds()
            return age < self._error_ttl_seconds
        # A 股标的：收盘后数据不变，缓存到下一开盘；盘中沿用短 TTL。
        # 海外指数：保留原扁平短 TTL（它们有各自的缓存优先链路）。
        if self._is_a_share_symbol(symbol):
            return market_session.is_cache_fresh(
                self._calendar,
                entry.fetched_at,
                now=now,
                open_ttl=self._ttl_seconds,
            )
        age = (now - entry.fetched_at).total_seconds()
        return age < self._ttl_seconds

    def _is_a_share_symbol(self, symbol: str) -> bool:
        try:
            return is_a_share(resolve_symbol(symbol))
        except ValueError:
            return False

    def get(self, symbol: str, *, refresh: bool = False) -> AnalysisEntry:
        """取单标的分析（缓存新鲜则直接返回）。per-symbol 锁防并发重入。"""
        with self._lock_for(symbol):
            entry = self._entries.get(symbol)
            if entry is not None and not refresh and self._is_fresh(entry, symbol):
                return entry
            entry = self._run(symbol)
            self._entries[symbol] = entry
            return entry

    def get_many(
        self, symbols: list[str], *, refresh: bool = False
    ) -> dict[str, AnalysisEntry]:
        """并发批量取数。返回顺序无关；调用方按自己的符号顺序组装。"""
        if not symbols:
            return {}
        results: dict[str, AnalysisEntry] = {}
        with ThreadPoolExecutor(max_workers=min(self._max_workers, len(symbols))) as pool:
            futures = {pool.submit(self.get, s, refresh=refresh): s for s in symbols}
            for future, symbol in futures.items():
                try:
                    results[symbol] = future.result()
                except Exception as exc:  # get 内部已兜底，这里是双保险
                    results[symbol] = AnalysisEntry(
                        None, f"分析失败：{exc}", datetime.now(UTC)
                    )
        return results

    def evict(self, symbols: list[str] | None = None) -> None:
        """驱逐缓存条目（refresh 按钮）。None = 全部。"""
        with self._guard:
            if symbols is None:
                self._entries.clear()
                return
            for symbol in symbols:
                self._entries.pop(symbol, None)

    def _provider_for(self, symbol: str) -> PriceProvider:
        """海外指数走「缓存优先 + 实时叠加」；其他走默认链。"""
        try:
            is_overseas = not is_a_share(resolve_symbol(symbol))
        except ValueError:
            return self._default_provider
        return self._overseas_provider if is_overseas else self._default_provider

    def _run(self, symbol: str) -> AnalysisEntry:
        fetched_at = datetime.now(UTC)
        try:
            result = self._analyze_fn(
                symbol,
                provider=self._provider_for(symbol),
                cache_root=self._cache_root,
                sqlite_path=self._sqlite_path,
                run_id=f"api-{date.today().isoformat()}",
                calendar=self._calendar,
            )
            return AnalysisEntry(result=result, error=None, fetched_at=fetched_at)
        except EventIdentityConflictError as exc:
            # 研究库里的历史事件与本次重算的身份字段冲突（多为历史上用不同
            # 数据集/规则版本写库留下的污染）。核心刻意抛出而不静默覆盖——
            # 这是正确的：身份字段是不可变历史事实。
            #
            # 但看盘页只读当前信号，不依赖写库成功。因此这里**关闭持久化重算**：
            # 用户照常看到卡片与详情，同时把冲突原文透出到 persist_conflict，
            # 由界面标注「未写入研究库」，不假装已持久化。
            conflict = str(exc)
            try:
                result = self._analyze_fn(
                    symbol,
                    provider=self._provider_for(symbol),
                    cache_root=self._cache_root,
                    sqlite_path=None,
                    run_id=None,
                    calendar=self._calendar,
                )
            except DataUnavailableError as inner:
                return AnalysisEntry(
                    None, _classify_error(inner), fetched_at, persist_conflict=conflict
                )
            except Exception as inner:
                return AnalysisEntry(
                    None, f"分析失败：{inner}", fetched_at, persist_conflict=conflict
                )
            result.sqlite_persisted = False
            return AnalysisEntry(
                result=result,
                error=None,
                fetched_at=fetched_at,
                persist_conflict=conflict,
            )
        except DataUnavailableError as exc:
            return AnalysisEntry(
                result=None, error=_classify_error(exc), fetched_at=fetched_at
            )
        except Exception as exc:  # 分析异常不拖垮整页仪表盘
            return AnalysisEntry(
                result=None, error=f"分析失败：{exc}", fetched_at=fetched_at
            )
