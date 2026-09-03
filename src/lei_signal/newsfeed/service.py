"""newsfeed API 服务层：查询/简报/状态/手动触发（后台线程 + 互斥）。"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta
from typing import Any

from lei_signal.api import config as api_config
from lei_signal.newsfeed.pipeline import run_pipeline
from lei_signal.newsfeed.store import NewsStore


def _row_to_dict(row: Any) -> dict:
    d = dict(row)
    d["symbols"] = json.loads(d.get("symbols") or "[]")
    return d


class NewsfeedService:
    """无 TTL 缓存（数据日更，SQLite 直查毫秒级）。管线在 daemon 线程跑。"""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or api_config.sqlite_path()
        self._run_lock = threading.Lock()
        self._last_trigger: dict[str, Any] = {}

    def _store(self) -> NewsStore:
        return NewsStore(self._db_path)

    # ---------------- 查询 ----------------

    def items(self, params: dict[str, Any]) -> dict[str, Any]:
        def _opt(name: str, cast=str):
            raw = params.get(name)
            return cast(raw) if raw not in (None, "") else None

        limit = min(int(_opt("limit", int) or 50), 200)
        offset = max(int(_opt("offset", int) or 0), 0)
        store = self._store()
        try:
            rows, total = store.query_items(
                category=_opt("category"),
                q=_opt("q"),
                source=_opt("source"),
                symbol=_opt("symbol"),
                direction=_opt("direction"),
                date_from=_opt("from"),
                date_to=_opt("to"),
                scored=(_opt("scored") or "all"),
                min_importance=_opt("min_importance", int),
                limit=limit,
                offset=offset,
            )
            return {"items": [_row_to_dict(r) for r in rows], "total": total}
        finally:
            store.close()

    # ---------------- 自选雷达聚合 ----------------

    @staticmethod
    def _matches(entry: dict, title: str, row_symbols: list[str]) -> bool:
        """标的匹配：LLM 提取的 symbols 双向包含，或标题出现标的/简称。"""
        t = title.lower()
        for m in entry["matchers"]:
            if len(m) < 2:
                continue
            if m in t:
                return True
            for s in row_symbols:
                s = s.strip().lower()
                if not s or len(s) < 2:
                    continue
                if m in s or s in m:
                    return True
        return False

    def watchlist_brief(
        self, watch_items: list[dict[str, Any]], days: int = 3
    ) -> dict[str, Any]:
        """自选标的 × 近 N 天消息聚合 + 全局多空温度（参考层，非交易信号）。

        watch_items 由路由层从 watchlist 表读取（跨模块取数不进 service）。
        只统计已评分条目（direction 只在打分后才有意义），零消息标的不返回。
        """
        days = max(1, min(int(days), 30))
        date_from = (
            datetime.now().astimezone() - timedelta(days=days)
        ).isoformat(timespec="seconds")
        entries: list[dict[str, Any]] = []
        for w in watch_items:
            matchers = {w["symbol"].lower()}
            name = (w.get("display_name") or "").strip()
            if name:
                matchers.add(name.lower())
            entries.append(
                {
                    "symbol": w["symbol"],
                    "display_name": w.get("display_name"),
                    "market": w.get("market"),
                    "matchers": sorted(matchers),
                    "count": 0,
                    "bullish": 0,
                    "bearish": 0,
                    "neutral": 0,
                    "latest_at": None,
                    "top": None,
                }
            )
        mood = {"bullish": 0, "bearish": 0, "neutral": 0, "top_bullish": [], "top_bearish": []}
        store = self._store()
        try:
            for row in store.scored_recent(date_from):
                d = _row_to_dict(row)
                direction = d.get("direction")
                if direction not in ("bullish", "bearish", "neutral"):
                    direction = "neutral"
                mood[direction] = mood.get(direction, 0) + 1
                if (d.get("importance") or 0) >= 6:
                    key = "top_bullish" if direction == "bullish" else (
                        "top_bearish" if direction == "bearish" else None
                    )
                    if key:
                        mood[key].append({"title": d["title"], "importance": d["importance"]})
                for e in entries:
                    if not self._matches(e, d["title"], d["symbols"]):
                        continue
                    e["count"] += 1
                    e[direction] = e.get(direction, 0) + 1
                    if not e["latest_at"] or d["published_at"] > e["latest_at"]:
                        e["latest_at"] = d["published_at"]
                    if e["top"] is None or (d.get("importance") or 0) >= (e["top"]["importance"] or 0):
                        e["top"] = {
                            "id": d["id"],
                            "title": d["title"],
                            "direction": d.get("direction"),
                            "importance": d.get("importance"),
                            "published_at": d["published_at"],
                            "url": d.get("url"),
                            "llm_note": d.get("llm_note"),
                        }
        finally:
            store.close()
        mood["top_bullish"] = mood["top_bullish"][:5]
        mood["top_bearish"] = mood["top_bearish"][:5]
        hits = [
            {k: v for k, v in e.items() if k != "matchers"}
            for e in entries
            if e["count"] > 0
        ]
        # 有消息的标的排前：利空/利多的净绝对值大的更靠前，再按消息数。
        hits.sort(
            key=lambda e: (
                abs(e["bullish"] - e["bearish"]),
                e["count"],
                e["latest_at"] or "",
            ),
            reverse=True,
        )
        return {"days": days, "items": hits, "mood": mood}

    def digests(self, limit: int = 7) -> list[dict]:
        store = self._store()
        try:
            out = []
            for row in store.digests(min(limit, 30)):
                d = dict(row)
                d["payload"] = json.loads(d.pop("payload_json") or "{}")
                out.append(d)
            return out
        finally:
            store.close()

    def status(self) -> dict[str, Any]:
        store = self._store()
        try:
            run = store.latest_run()
            last_run = None
            if run is not None:
                last_run = dict(run)
                last_run["stats"] = json.loads(last_run.pop("stats_json") or "{}")
                last_run["errors"] = json.loads(last_run.pop("errors_json") or "[]")
            return {
                "last_run": last_run,
                "counts": store.counts(),
                "trigger": dict(self._last_trigger),
            }
        finally:
            store.close()

    # ---------------- 触发 ----------------

    def trigger_run(self, *, full: bool = False) -> dict[str, Any]:
        """后台线程跑管线；已在跑时直接返回 running。"""
        if not self._run_lock.acquire(blocking=False):
            return {"run": "already_running"}
        try:

            def _work() -> None:
                try:
                    result = run_pipeline(self._db_path, full=full)
                    self._last_trigger = {
                        "finished_at": result.get("status"),
                        "result": result,
                    }
                except Exception as exc:  # noqa: BLE001 - 线程兜底
                    self._last_trigger = {"finished_at": "failed", "result": str(exc)}
                finally:
                    self._run_lock.release()

            threading.Thread(target=_work, daemon=True, name="newsfeed-run").start()
            return {"run": "started"}
        except Exception:
            self._run_lock.release()
            raise


__all__ = ["NewsfeedService"]
