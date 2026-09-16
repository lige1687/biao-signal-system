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

    # ── /watchlist ───────────────────────────────────────────────────────
    def watchlist(self, *, top_n: int = 5) -> dict[str, Any] | None:
        """今日板块观察（道路层分组，research_proxy）。

        只对快照字段做确定性分组/排序，不重算、不新造判定条件：
        - ``markup``：上升阶段（道路向上），按 RS 百分位排。
        - ``near_upgrade``：筑底/未定且「道路确立三条件」已满足 ≥2 条，
          按缺口数、距 SMA60 距离排（回答「离升级最近的板块」）。
        - ``accumulation``：其余筑底观察中，按 RS 百分位排。
        - ``distribution`` / ``decline``：派发 / 下降，按 RS 百分位排。
        - ``momentum``：RS 百分位 20 日变化 >0 的前 N（轮动方向参考）。
        """
        snap = self.trend()
        if not snap:
            return None
        boards = [b for b in snap.get("boards", []) if b.get("parent") is None]

        def item(b: dict[str, Any]) -> dict[str, Any]:
            return {
                "code": b.get("code"),
                "name": b.get("name"),
                "level": b.get("level"),
                "stage": b.get("stage"),
                "rs_pctile": b.get("rs_pctile"),
                "rs_pctile_delta_20": b.get("rs_pctile_delta_20"),
                "b50": b.get("b50"),
                "dist_to_sma60_pct": b.get("dist_to_sma60_pct"),
                "next_watch": b.get("next_watch"),
                "next_watch_kind": b.get("next_watch_kind"),
                "stage_basis": b.get("stage_basis"),
                # 资金流交叉验证（单据规模代理，research_proxy）
                "flow_20d_main_yi": b.get("flow_20d_main_yi"),
                "flow_20d_retail_yi": b.get("flow_20d_retail_yi"),
                "flow_vs_stage": b.get("flow_vs_stage"),
                "flow_vs_stage_cn": b.get("flow_vs_stage_cn"),
                "flow_note_cn": b.get("flow_note_cn"),
            }

        def unmet_count(b: dict[str, Any]) -> int:
            return sum(1 for c in b.get("checkpoints") or [] if not c.get("met"))

        markup = sorted(
            (b for b in boards if b.get("stage") == "markup"),
            key=lambda b: -(b.get("rs_pctile") or 0),
        )
        candidates = [b for b in boards if b.get("stage") in ("accumulation", None)]
        near = sorted(
            (b for b in candidates if unmet_count(b) <= 1),
            key=lambda b: (
                unmet_count(b),
                abs(b.get("dist_to_sma60_pct") or 999),
            ),
        )
        rest_acc = sorted(
            (b for b in candidates if unmet_count(b) > 1),
            key=lambda b: -(b.get("rs_pctile") or 0),
        )
        dist = sorted(
            (b for b in boards if b.get("stage") == "distribution"),
            key=lambda b: -(b.get("rs_pctile") or 0),
        )
        decline = sorted(
            (b for b in boards if b.get("stage") == "decline"),
            key=lambda b: -(b.get("rs_pctile") or 0),
        )
        momentum = sorted(
            (b for b in boards if (b.get("rs_pctile_delta_20") or 0) > 0),
            key=lambda b: -(b.get("rs_pctile_delta_20") or 0),
        )

        groups = [
            {
                "key": "markup",
                "title": "上升（道路向上）",
                "desc": "三条件已确立；观察跌破 SMA60 与宽度背离的转弱信号",
                "items": [item(b) for b in markup[:top_n]],
            },
            {
                "key": "near_upgrade",
                "title": "临近升级（差 1 条）",
                "desc": "道路确立三条件只差一条，多为「价格上穿 SMA60」",
                "items": [item(b) for b in near[:top_n]],
            },
            {
                "key": "accumulation",
                "title": "筑底观察中",
                "desc": "RS 相对强但条件缺口 ≥2 条，按 RS 百分位排",
                "items": [item(b) for b in rest_acc[:top_n]],
            },
            {
                "key": "momentum",
                "title": "相对动能改善最快",
                "desc": "RS 百分位 20 日变化前 N，轮动方向参考（跨阶段）",
                "items": [item(b) for b in momentum[:top_n]],
            },
            {
                "key": "distribution",
                "title": "派发（高处转弱）",
                "desc": "价格仍在 SMA60 上方但斜率/宽度转弱",
                "items": [item(b) for b in dist[:top_n]],
            },
            {
                "key": "decline",
                "title": "下降（道路向下）",
                "desc": "观察 RS 修复与 EMA20 转正的筑底前兆",
                "items": [item(b) for b in decline[:top_n]],
            },
        ]
        return {
            "as_of": snap.get("as_of"),
            "trading_day": snap.get("trading_day"),
            "groups": groups,
            "research_proxy_note": snap.get("research_proxy_note"),
        }

    # ── /{code}/history ───────────────────────────────────────────────────
    def history(self, code: str, *, days: int = 250) -> dict[str, Any]:
        days = max(1, min(days, 1000))
        # 回填后历史文件较大且 RRG 尾迹会并发打 ~120 次请求：整文件走 TTL 缓存
        hist, _ = self._cache.get_or_load("history", _TTL, lambda: st.load_history(limit_days=1000))
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
                    "rs_pctile_delta_20": b.get("rs_pctile_delta_20"),
                    "stage": b.get("stage"),
                }
            )
        return {"code": code, "points": points[-days:]}

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
