"""newsfeed API 服务层：查询/简报/状态/手动触发（后台线程 + 互斥）。"""
from __future__ import annotations

import json
import threading
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
