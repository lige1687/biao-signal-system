"""统一添加目录的动态部分：东财概念板块清单（静态部分见 labels.py / config.py）。

为什么单独拉概念板块：THS 881xxx 只覆盖 90 个行业，概念（CPO、存储芯片……）
是东财 BK 概念体系（约 500 个），行情走 ``EastmoneySectorProvider`` 的
``secid=90.BKxxxx``，代码直输一直可用，这里只是让选择器能搜到。

口径决策（2026-08 用户确认）：概念板块进目录；BK 行业不进（与 THS 90 个行业
同名重叠，行业口径统一用 THS）；SW 申万不进（与 THS 重叠），两者保留直输。

降级：清单拉取失败返回空列表——添加目录的行业/指数/美股 ETF 三块是静态的，
不受影响，对话框照常可用。
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from lei_signal.fundamentals import sources

_TTL = 3600  # 清单一天变不了几次；每次打开对话框都打东财不划算


class _TtlCache:
    """同 fundamentals.service._TtlCache（内存 TTL，线程安全）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, tuple[float, Any]] = {}

    def get_or_load(self, key: str, ttl: int, loader: Callable[[], Any]) -> Any:
        now = time.monotonic()
        with self._lock:
            hit = self._items.get(key)
        if hit is not None and now - hit[0] < ttl:
            return hit[1]
        value = loader()
        with self._lock:
            self._items[key] = (now, value)
        return value

    def invalidate(self) -> None:
        with self._lock:
            self._items.clear()


_CACHE = _TtlCache()


def _fetch_concept_boards() -> list[dict[str, str]]:
    """东财概念板块全景（fs=m:90+t:3+f:!50，与 akshare 同口径，约 500 个）。

    pz 上限 100，翻页拉全；失败抛 FundamentalsSourceError，由上层降级。
    """
    diff: list[dict[str, Any]] = []
    for page in range(1, 7):
        payload = sources._get_json(
            sources._CLIST_URLS,
            {
                "pn": page,
                "pz": 100,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": "m:90+t:3+f:!50",
                "fields": "f12,f14",
            },
        )
        data = payload.get("data") or {}
        batch = data.get("diff") or []
        diff.extend(batch)
        if len(diff) >= (data.get("total") or 0) or not batch:
            break

    boards: list[dict[str, str]] = []
    for row in diff:
        code = str(row.get("f12") or "").strip()
        name = str(row.get("f14") or "").strip()
        if code.startswith("BK") and name:
            boards.append({"code": code, "name": name, "symbol": code})
    boards.sort(key=lambda b: b["name"])
    return boards


def concept_boards(*, refresh: bool = False) -> list[dict[str, str]]:
    """概念板块清单（TTL 1h）。拉取失败降级为空列表，不抛异常。"""
    if refresh:
        _CACHE.invalidate()
    try:
        return list(_CACHE.get_or_load("concepts", _TTL, _fetch_concept_boards))
    except sources.FundamentalsSourceError:
        return []


__all__ = ["concept_boards"]
