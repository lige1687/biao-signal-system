#!/usr/bin/env python3
"""S1 受控采集（2026-09-17）：仅美联储官方源、临时库、1 次 HTTP、no_llm、不推送。

- 东财/新浪/gnews/B站采集器在本进程内替换为空返回，保证全程只有 fed 一次
  真实 HTTP（20s 超时）；这是受控验证，不是生产管线默认行为。
- 临时库路径显式：/tmp/agent-news-s1/newsfeed-s1.db（不碰真实库）。
- 保存：原始响应 XML、运行结果 JSON、重放核对结果，供主控复核。
- 重放用已保存响应（fetcher 注入），不再消耗网络预算。

用法：python3 controlled_collect.py
退出码：0=采集与重放核对完成（含源失败被记录的情形）；2=脚本自身异常。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from lei_signal.newsfeed import pipeline  # noqa: E402
from lei_signal.newsfeed.sources import fed  # noqa: E402
from lei_signal.newsfeed.store import NewsStore  # noqa: E402

RAW = Path(__file__).resolve().parent
DB = Path("/tmp/agent-news-s1/newsfeed-s1.db")
XML_OUT = RAW / "fed-press-monetary-live-2026-09-17.xml"
RESULT_OUT = RAW / "controlled-collect-result.json"

_CFG = {
    "bili_ups": [],
    "rss_feeds": [],
    "gnews_queries": [],
    "symbols": [],
    "flash_keywords": {"macro": ["美联储", "Federal Reserve"], "risk": [],
                       "policy": [], "industry": []},
    "lookback_days": 7,
    "fed_press": {"enabled": True, "url": fed.FED_PRESS_URL},
}


def _neutralize_other_sources() -> None:
    """其他源改空返回：全程仅 fed 一次真实 HTTP（受控，非生产行为）。"""
    pipeline.collect_eastmoney = lambda since: ([], None)
    pipeline.collect_sina = lambda since: ([], None)
    pipeline.collect_rss = lambda q, *, is_gnews, since_iso: ([], None)
    pipeline.fetch_new_up_items = (
        lambda client, mid, name, since, lookback_iso=None, **kw: ([], None)
    )
    pipeline.BilibiliClient = lambda *a, **k: object()


def main() -> int:
    DB.parent.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "db_path": str(DB),
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "http_attempts": [],
    }

    # 包装默认 fetch 以落存原始响应（凭据无关，公开 feed）。
    captured: dict[str, str] = {}
    real_fetch = fed._default_fetch

    def capture(url: str, timeout: int) -> str:
        report["http_attempts"].append({
            "url": url, "timeout_sec": timeout,
            "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        })
        text = real_fetch(url, timeout)
        captured["xml"] = text
        return text

    fed._default_fetch = capture
    _neutralize_other_sources()

    run_error: str | None = None
    try:
        result = pipeline.run_pipeline(DB, config=_CFG, no_llm=True)
    except Exception as exc:  # noqa: BLE001 — 保留失败，不宣称恢复
        run_error = f"{type(exc).__name__}: {exc}"
        result = None
    report["run_error"] = run_error
    report["pipeline_result"] = result

    if captured.get("xml"):
        XML_OUT.write_text(captured["xml"], "utf-8")

    # ---- 重放核对（已保存响应，零网络）：同一材料沿同一管线路径重跑必须幂等 ----
    replay: dict = {"skipped": True}
    if captured.get("xml") and DB.exists() and result is not None:
        xml = captured["xml"]
        fed._default_fetch = lambda url, timeout: xml  # 重放不再打网络
        store = NewsStore(DB)
        before = store.counts()["total"]
        store.close()
        replay_result = pipeline.run_pipeline(DB, config=_CFG, no_llm=True)
        store = NewsStore(DB)
        after = store.counts()["total"]
        agg = store.health_aggregates()
        store.close()
        replay = {
            "skipped": False,
            "inserted_on_replay": replay_result["inserted"],
            "per_source_fed": (replay_result.get("per_source") or {}).get("fed"),
            "total_before": before,
            "total_after": after,
            "idempotent": replay_result["inserted"] == 0 and before == after,
            "run_status": replay_result["status"],
            "health_aggregates": agg,
        }
    report["replay"] = replay

    RESULT_OUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), "utf-8"
    )
    print(json.dumps({
        "status": (result or {}).get("status"),
        "fed_inserted": ((result or {}).get("per_source") or {}).get("fed"),
        "stages": (result or {}).get("stages"),
        "replay_idempotent": replay.get("idempotent"),
        "http_attempts": len(report["http_attempts"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
