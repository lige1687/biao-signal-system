"""行业板块趋势工作台 · API 组装服务（P2）。

只读：磁盘上的三份冻结快照（由 ``scripts/precompute_sector_trend.py`` 产出）。
所有判定标 ``research_proxy``（研究代理），不重算、不冒充 LEI 原始规则。

缓存：磁盘读走 TTL 300s（照抄 ``fundamentals.service._TtlCache``），``refresh=true``
仅强制重读磁盘（真正重算由 CLI 触发）。
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from lei_signal.fundamentals import sources
from lei_signal.market_context import sector_trend as st

_TTL = 300


class _TtlCache:
    """照抄 fundamentals.service._TtlCache（内存 TTL，线程安全）。"""

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

    def invalidate(self, prefix: str | None = None) -> None:
        with self._lock:
            if prefix is None:
                self._items.clear()
            else:
                for key in [k for k in self._items if k.startswith(prefix)]:
                    del self._items[key]


class SectorsService:
    def __init__(self) -> None:
        self._cache = _TtlCache()
        self.errors: list[str] = []

    # ── /trend ────────────────────────────────────────────────────────────
    def trend(self, *, refresh: bool = False, level: str = "all") -> dict[str, Any] | None:
        if refresh:
            self._cache.invalidate("snapshot")
        snap, _ = self._cache.get_or_load("snapshot", _TTL, st.load_snapshot)
        if not snap:
            return None
        boards = snap.get("boards", [])
        if level in ("l1", "l2", "l3"):
            lvl = int(level[1])
            boards = [b for b in boards if b.get("level") == lvl]
        return {**snap, "boards": boards}

    # ── /{code}/history ───────────────────────────────────────────────────
    def history(self, code: str, *, days: int = 250) -> dict[str, Any]:
        days = max(1, min(days, 1000))
        hist = st.load_history(limit_days=days)
        points: list[dict[str, Any]] = []
        for rec in hist:
            b = rec.get("boards", {}).get(code)
            if b is None:
                continue
            points.append(
                {
                    "date": rec.get("date"),
                    "close": b.get("close"),
                    "b50": b.get("b50"),
                    "rs_pctile": b.get("rs_pctile"),
                    "stage": b.get("stage"),
                }
            )
        return {"code": code, "points": points}

    # ── /{code}/members ───────────────────────────────────────────────────
    def members(self, code: str, *, limit: int = 50) -> dict[str, Any] | None:
        limit = max(1, min(limit, 500))
        cache = st.load_members_cache()
        if not cache:
            return None
        board = cache.get("boards", {}).get(code)
        if not board:
            return None

        symbols = list(board.get("members", []))[:limit]
        kset = st.kline_symbols()  # 离线安全：缺失则全 False

        # 当日 clist 行情（f3 涨跌幅 / f20 总市值），取数失败降级为 null
        quotes: dict[str, dict[str, Any]] = {}
        try:
            payload = sources._get_json(
                sources._CLIST_URLS,
                {
                    "pn": 1,
                    "pz": max(limit, 100),
                    "po": 1,
                    "np": 1,
                    "fltt": 2,
                    "invt": 2,
                    "fid": "f3",
                    "fs": f"b:{code}",
                    "fields": "f12,f14,f3,f20",
                },
            )
            for row in payload.get("data", {}).get("diff", []) or []:
                raw = str(row.get("f12") or "").strip()
                mv = row.get("f20")
                quotes[raw] = {
                    "name": row.get("f14"),
                    "pct_change": (None if mv is None else row.get("f3")),
                    "market_value_yi": (None if mv in (None, "") else float(mv) / 1e8),
                }
        except sources.FundamentalsSourceError as exc:
            self.errors.append(f"板块成分股行情: {exc}")

        out: list[dict[str, Any]] = []
        for sym in symbols:
            raw = sym[2:] if len(sym) > 2 and sym[:2] in ("sh", "sz", "bj") else sym
            q = quotes.get(raw, {})
            out.append(
                {
                    "symbol": sym,
                    "name": q.get("name"),
                    "pct_change": q.get("pct_change"),
                    "market_value_yi": q.get("market_value_yi"),
                    "in_kline_cache": sym in kset,
                }
            )
        return {
            "as_of": cache.get("as_of"),
            "code": code,
            "name": board.get("name"),
            "members": out,
        }
