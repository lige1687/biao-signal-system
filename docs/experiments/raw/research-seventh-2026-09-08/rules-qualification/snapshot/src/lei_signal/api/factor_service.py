"""因子观测台 · API 组装服务。

只读磁盘冻结快照（由 ``scripts/precompute_factor_panel.py`` 产出），
判定标 ``research_proxy``，不重算、不出买卖点（照 sectors_service 模式）。
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from lei_signal.market_context import factor_panel

_TTL = 300


class _TtlCache:
    """照抄 sectors_service._TtlCache（内存 TTL，线程安全）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, tuple[float, Any]] = {}

    def get_or_load(self, key: str, ttl: int, loader: Callable[[], Any]) -> tuple[Any, bool]:
        now = time.monotonic()
        with self._lock:
            hit = self._items.get(key)
        if hit is not None and now - hit[0] < ttl:
            return hit[1], False
        value = loader()
        with self._lock:
            self._items[key] = (now, value)
        return value, True

    def invalidate(self) -> None:
        with self._lock:
            self._items.clear()


class FactorPanelService:
    def __init__(self) -> None:
        self._cache = _TtlCache()

    def panel(self, *, refresh: bool = False) -> dict[str, Any] | None:
        if refresh:
            self._cache.invalidate()
        snap, _ = self._cache.get_or_load("panel", _TTL, factor_panel.load_panel)
        return snap
