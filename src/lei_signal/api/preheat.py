"""看盘缓存后台预热调度。

为什么需要
------------
``AnalysisService`` 是纯内存缓存：盘中 TTL 900s，过期后第一个打开页面的请求
要现场把全部自选股走一遍完整 ``analyze()``（实测 24 只 ≈ 2 分钟）。launchd
KeepAlive 重启后缓存清零，同样由重启后的首个请求买单。

用户时效性要求（2026-08 对话确认）：

- 固定看盘时间：中午收盘后（~12:00）与 14:45，打开必须命中缓存秒开；
- 其余时间 15–30 分钟后台拉一次数据无异议；
- 基本面页面每天更新一次即可。

调度规则（北京时间，全部由 ``due_actions`` 纯函数判定，便于测试）：

- **冷启动**：本进程从未全量刷过 → 立即刷一次，覆盖 launchd 重启场景；
- **交易日盘中** 09:30–15:00（含午休，口径同 ``session.is_open``）：距上次
  全量 ≥12 分钟则强刷。12 < 15 分钟 TTL，缓存永不过期，任何时刻打开都命中；
- **交易日收盘窗** 15:00–15:20：距上次 ≥5 分钟则补刷收盘最终 bar。此后
  A 股条目由时段感知新鲜度直接持有到次日开盘，不再重复拉；
- **其余时段**（收盘后/夜间/周末）：默认大盘指数组按 12 分钟间隔强刷。
  海外指数夜里仍在交易，走「磁盘缓存 + 实时叠加」链路，开销低；
- **非 A 股自选保温**（其余时段生效）：自选里的非 A 股标的（美股 ETF /
  板块代理）走 900s 扁平 TTL，夜间（美股盘中）过期后首个用户请求要
  现场等一轮抓取（Yahoo 慢/限流时可达分钟级）。故按 12 分钟后台保温，
  同样 12 < 15 分钟 TTL，任何时刻打开都命中缓存。A 股自选收盘后数据
  不变，由时段感知新鲜度持有到次日开盘，不在此档重复拉；
- **基本面**：每天 15:35 之后刷一次（距上次 ≥11h），或距上次 ≥20h 兜底。
  配合 fundamentals TTL 放宽到 12–24h，页面全天命中缓存。

线程每 60s 醒一次重算调度（顺带自愈系统睡眠/时钟漂移：醒来后年龄超限即刷）。
任何一轮刷新失败只记日志、不更新时间戳，下一轮自动重试。
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from datetime import time as dtime

from lei_signal.api import config, session
from lei_signal.api.routes.dashboard import dashboard_symbols
from lei_signal.data.calendar import DEFAULT_TRADING_CALENDAR, TradingCalendar
from lei_signal.data.symbols import is_a_share, resolve_symbol

logger = logging.getLogger(__name__)

#: 盘中全量刷新间隔。必须 < AnalysisService 盘中 TTL(900s)，留出抓取耗时
#: 与 60s tick 抖动的余量，保证条目年龄永远不越过 TTL（缓存永不过期）。
INTRADAY_INTERVAL = timedelta(minutes=12)
#: 收盘窗补刷间隔：15:00–15:20 内距上次全量超过它就再刷一次收盘最终 bar。
CLOSING_INTERVAL = timedelta(minutes=5)
#: 非盘中时段指数组刷新间隔（同样略小于海外指数的 15 分钟扁平 TTL）。
INDEX_INTERVAL = timedelta(minutes=12)
#: 非 A 股自选（美股 ETF / 板块代理）保温间隔。必须 < 900s 扁平 TTL：这些
#: 标的夜间（美股盘中）过期后，首个用户请求会同步等一轮现场抓取。
OVERSEAS_INTERVAL = timedelta(minutes=12)
#: 基本面每日锚点：收盘数据（两融/国债等）落地后刷新。
FUNDAMENTALS_PIN = dtime(15, 35)
#: 基本面固定时刻触发的最小年龄（避免 20h 兜底刚刷过又重复刷）。
FUNDAMENTALS_PIN_MIN_AGE = timedelta(hours=11)
#: 基本面兜底最大年龄：哪怕固定时刻一直没命中（如进程长期不重启），到点也刷。
FUNDAMENTALS_MAX_AGE = timedelta(hours=20)

#: 调度重算周期。60s 足够（间隔以分钟计），且睡眠唤醒后能立即自愈。
_TICK_SECONDS = 60.0

#: 刷新范围。full = 默认大盘 + 自选全量；index = 仅默认大盘；
#: overseas = 仅非 A 股自选（非盘中保温档）；fundamentals = 基本面。
Scope = str

_CLOSING_WINDOW_END = dtime(15, 20)


@dataclass
class PreheatState:
    """各范围最近一次成功刷新时刻（UTC）。None = 本进程尚未刷过。"""

    full: datetime | None = None
    index: datetime | None = None
    overseas: datetime | None = None
    fundamentals: datetime | None = None
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


def due_actions(
    state: PreheatState, *, now: datetime | None = None, calendar: TradingCalendar | None = None
) -> list[Scope]:
    """计算当前时刻应刷新的范围（纯函数，不执行抓取）。

    返回顺序稳定：full → index → overseas → fundamentals。full 已 due 时
    index/overseas 跳过（全量覆盖指数组与非 A 股自选）。
    """
    calendar = calendar or DEFAULT_TRADING_CALENDAR
    now = now or datetime.now(UTC)
    sh = now.astimezone(session.SHANGHAI)
    t = sh.time()
    trading_day = calendar.is_trading_day(sh.date())
    due: list[Scope] = []

    age_full = None if state.full is None else now - state.full
    if (
        age_full is None
        or (session.is_open(calendar, now=now) and age_full >= INTRADAY_INTERVAL)
        or (
            trading_day
            and session.CLOSE <= t < _CLOSING_WINDOW_END
            and age_full >= CLOSING_INTERVAL
        )
    ):
        due.append("full")

    if "full" not in due:
        age_index = None if state.index is None else now - state.index
        if age_index is None or age_index >= INDEX_INTERVAL:
            due.append("index")

        age_overseas = None if state.overseas is None else now - state.overseas
        if age_overseas is None or age_overseas >= OVERSEAS_INTERVAL:
            due.append("overseas")

    age_fund = None if state.fundamentals is None else now - state.fundamentals
    if (
        age_fund is None
        or age_fund >= FUNDAMENTALS_MAX_AGE
        or (t >= FUNDAMENTALS_PIN and age_fund >= FUNDAMENTALS_PIN_MIN_AGE)
    ):
        due.append("fundamentals")

    return due


def preheat_allowed(env: dict[str, str] | None = None) -> bool:
    """外部开关：LEI_PREHEAT_DISABLED 为真值时关闭预热线程。"""
    env = env if env is not None else os.environ
    return env.get("LEI_PREHEAT_DISABLED", "").lower() not in ("1", "true", "yes")


def default_symbols_fn(db_path: str) -> Callable[[], list[str]]:
    """全量范围取数：默认大盘 + 自选（每轮重读 DB，自选增删即时生效）。"""

    def _fn() -> list[str]:
        indices, watchlist = dashboard_symbols(db_path)
        return [symbol for symbol, _ in indices] + [item.symbol for item in watchlist]

    return _fn


def _refresh_full(
    analysis_service: object, symbols_fn: Callable[[], list[str]]
) -> list[str]:
    symbols = symbols_fn()
    analysis_service.get_many(symbols, refresh=True)  # type: ignore[attr-defined]
    return symbols


def _refresh_index(analysis_service: object) -> list[str]:
    symbols = [idx.symbol for idx in config.DASHBOARD_INDICES]
    analysis_service.get_many(symbols, refresh=True)  # type: ignore[attr-defined]
    return symbols


def _is_overseas(symbol: str) -> bool:
    """是否非 A 股标的（美股 ETF / 海外指数 / 板块代理）。解析失败视为否。"""
    try:
        return not is_a_share(resolve_symbol(symbol))
    except ValueError:
        return False


def _overseas_watchlist_symbols(symbols_fn: Callable[[], list[str]]) -> list[str]:
    """非 A 股自选清单：默认大盘 + 自选里剔除 A 股与指数组（指数组由 index 档覆盖）。"""
    index_symbols = {idx.symbol for idx in config.DASHBOARD_INDICES}
    return [s for s in symbols_fn() if s not in index_symbols and _is_overseas(s)]


def _refresh_overseas(
    analysis_service: object, symbols_fn: Callable[[], list[str]]
) -> list[str]:
    """非盘中保温档：只刷非 A 股自选（美股 ETF / 板块代理）。

    这些标的走 900s 扁平 TTL，夜间（美股盘中）过期后首个用户请求要现场
    等一轮抓取（Yahoo 慢/限流时可达分钟级），由后台按间隔保温后秒开。
    """
    symbols = _overseas_watchlist_symbols(symbols_fn)
    if symbols:
        analysis_service.get_many(symbols, refresh=True)  # type: ignore[attr-defined]
    return symbols


def _refresh_fundamentals(fundamentals_service: object) -> None:
    """基本面页卡片数据：refresh=False 让 TTL 到期自然重拉（12–24h 一次）。"""
    fundamentals_service.overview()  # type: ignore[attr-defined]
    fundamentals_service.rates()  # type: ignore[attr-defined]
    fundamentals_service.commodities()  # type: ignore[attr-defined]
    fundamentals_service.etf_strength()  # type: ignore[attr-defined]


def _run_loop(
    stop: threading.Event,
    *,
    analysis_service: object,
    fundamentals_service: object,
    symbols_fn: Callable[[], list[str]],
    calendar: TradingCalendar | None,
    state: PreheatState,
) -> None:
    while not stop.is_set():
        now = datetime.now(UTC)
        try:
            for scope in due_actions(state, now=now, calendar=calendar):
                started = time.monotonic()
                if scope == "full":
                    symbols = _refresh_full(analysis_service, symbols_fn)
                    # 全量覆盖指数组与非 A 股自选：两个时钟一并归零。
                    with state.lock:
                        state.full = state.index = state.overseas = now
                elif scope == "index":
                    symbols = _refresh_index(analysis_service)
                    with state.lock:
                        state.index = now
                elif scope == "overseas":
                    symbols = _refresh_overseas(analysis_service, symbols_fn)
                    with state.lock:
                        state.overseas = now
                else:
                    _refresh_fundamentals(fundamentals_service)
                    symbols = []
                logger.info(
                    "预热 %s 完成（%d 个标的，耗时 %.1fs）",
                    scope,
                    len(symbols),
                    time.monotonic() - started,
                )
        except Exception:  # noqa: BLE001 - 预热失败不影响服务，下轮重试
            logger.warning("预热本轮失败，将在下个 tick 重试", exc_info=True)
        stop.wait(_TICK_SECONDS)


def start_preheat(
    analysis_service: object,
    fundamentals_service: object,
    symbols_fn: Callable[[], list[str]],
    *,
    calendar: TradingCalendar | None = None,
) -> threading.Event | None:
    """启动后台预热线程，返回 stop 事件（可用于停机）。

    pytest 环境或 ``LEI_PREHEAT_DISABLED`` 为真值时不启动，返回 None
    （与 ``app._warm_a_share_breadth`` 的跳过约定一致，避免单测发网络请求）。
    """
    if "pytest" in sys.modules or not preheat_allowed():
        return None
    # uvicorn 默认日志配置不接管应用 logger（INFO 会被丢弃），单独挂一个
    # stderr handler，让「预热 xx 完成」落到 launchd 的 backend.err.log 里。
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    stop = threading.Event()
    threading.Thread(
        target=_run_loop,
        kwargs={
            "stop": stop,
            "analysis_service": analysis_service,
            "fundamentals_service": fundamentals_service,
            "symbols_fn": symbols_fn,
            "calendar": calendar,
            "state": PreheatState(),
        },
        daemon=True,
        name="dashboard-preheat",
    ).start()
    return stop


__all__ = [
    "CLOSING_INTERVAL",
    "FUNDAMENTALS_MAX_AGE",
    "FUNDAMENTALS_PIN",
    "FUNDAMENTALS_PIN_MIN_AGE",
    "INDEX_INTERVAL",
    "INTRADAY_INTERVAL",
    "OVERSEAS_INTERVAL",
    "PreheatState",
    "default_symbols_fn",
    "due_actions",
    "preheat_allowed",
    "start_preheat",
]
