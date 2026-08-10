"""基本面参考层组装服务：TTL 缓存 + 单项降级。

降级原则：任何一个数据源挂了，其余照常返回，失败项进 errors 列表，
页面局部可用 —— 参考层绝不能因为一个接口超时而整页空白。
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from lei_signal.fundamentals import sources

# 板块行情/资金流变化快，缓存 5 分钟；宏观指标月更，缓存 6 小时。
_BOARDS_TTL = 300
_MACRO_TTL = 6 * 3600
_FLOW_TTL = 300


class _TtlCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, tuple[float, Any]] = {}

    def get_or_load(self, key: str, ttl: int, loader: Callable[[], Any]) -> tuple[Any, bool]:
        """返回 (value, fresh)。fresh=True 表示本次是新拉取的。"""
        now = time.monotonic()
        with self._lock:
            hit = self._items.get(key)
        if hit is not None and now - hit[0] < ttl:
            return hit[1], False
        value = loader()
        with self._lock:
            self._items[key] = (now, value)
        return value, True

    def invalidate(self, prefix: str | None = None) -> None:
        with self._lock:
            if prefix is None:
                self._items.clear()
            else:
                for key in [k for k in self._items if k.startswith(prefix)]:
                    del self._items[key]


class FundamentalsService:
    def __init__(self) -> None:
        self._cache = _TtlCache()

    def overview(self, *, refresh: bool = False) -> dict[str, Any]:
        if refresh:
            self._cache.invalidate()
        errors: list[str] = []

        boards: list[dict[str, Any]] = []
        try:
            boards, _ = self._cache.get_or_load(
                "boards", _BOARDS_TTL, sources.fetch_industry_boards
            )
        except sources.FundamentalsSourceError as exc:
            errors.append(f"行业板块: {exc}")

        macro: list[dict[str, Any]] = []
        for key, loader in (
            ("pmi", sources.fetch_pmi),
            ("cpi", sources.fetch_cpi),
            ("ppi", sources.fetch_ppi),
        ):
            try:
                item, _ = self._cache.get_or_load(f"macro:{key}", _MACRO_TTL, loader)
                macro.append(item)
            except sources.FundamentalsSourceError as exc:
                errors.append(f"宏观 {key}: {exc}")

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "macro": macro,
            "boards": boards,
            "board_count": len(boards),
            "errors": errors,
            "disclaimer_cn": "基本面参考层：数据来自公开数据源，仅供研究参考，"
            "不参与 LEI 技术信号判定，不构成投资建议。",
        }

    def industry_flow(self, code: str, *, days: int = 20) -> dict[str, Any]:
        days = max(5, min(days, 60))
        points, _ = self._cache.get_or_load(
            f"flow:{code}:{days}", _FLOW_TTL, lambda: sources.fetch_industry_flow(code, days=days)
        )
        return {"code": code, "days": days, "points": points}
