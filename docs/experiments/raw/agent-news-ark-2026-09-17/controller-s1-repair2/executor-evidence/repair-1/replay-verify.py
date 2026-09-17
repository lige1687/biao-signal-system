#!/usr/bin/env python3
"""repair-1 重放验证（2026-09-17）：返修后代码 + 已保存真实响应，零网络。

- 材料：execution 1 受控采集保存的真实官方 feed（GMT/CDATA/BOM 实测）。
- 路径：fetcher 注入同一管线路径（run_pipeline，no_llm，临时库，不推送），
  其他源进程内置空——与 execution 1 受控采集同法，但不发任何 HTTP。
- 核对：R2（正式公告评分 6 仍可见、讲话不占位）、R3（书签真实时刻比较、
  真实材料 GMT 解析）、R4（评分异常落库收尾）在真实材料上的表现。

用法：python3 replay-verify.py；退出码 0=核对完成（结果见 JSON），1=自身异常。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "src"))

from lei_signal.newsfeed import pipeline  # noqa: E402
from lei_signal.newsfeed.event_context import build_event_reference  # noqa: E402
from lei_signal.newsfeed.service import NewsfeedService  # noqa: E402
from lei_signal.newsfeed.sources import fed  # noqa: E402
from lei_signal.newsfeed.store import NewsStore  # noqa: E402

RAW = Path(__file__).resolve().parent
XML = RAW.parent / "fed-press-monetary-live-2026-09-17.xml"
DB = Path("/tmp/agent-news-s1/repair1-replay.db")
OUT = RAW / "replay-verify-result.json"

_CFG = {
    "bili_ups": [], "rss_feeds": [], "gnews_queries": [], "symbols": [],
    "flash_keywords": {"macro": ["美联储"], "risk": [], "policy": [], "industry": []},
    "lookback_days": 7,
    "fed_press": {"enabled": True, "url": fed.FED_PRESS_URL},
}


def _neutralize() -> None:
    pipeline.collect_eastmoney = lambda since: ([], None)
    pipeline.collect_sina = lambda since: ([], None)
    pipeline.collect_rss = lambda q, *, is_gnews, since_iso: ([], None)
    pipeline.fetch_new_up_items = (
        lambda client, mid, name, since, lookback_iso=None, **kw: ([], None)
    )
    pipeline.BilibiliClient = lambda *a, **k: object()


def main() -> int:
    xml = XML.read_text("utf-8")
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    fed._default_fetch = lambda url, timeout: xml  # 重放：零网络
    _neutralize()
    report: dict = {"material": str(XML), "db_path": str(DB), "http": 0}

    # 1) 真实材料沿管线路径回放（repair 后代码）
    r1 = pipeline.run_pipeline(DB, config=_CFG, no_llm=True)
    r2 = pipeline.run_pipeline(DB, config=_CFG, no_llm=True)
    report["run1"] = {"status": r1["status"], "fed": r1["per_source"].get("fed"),
                      "stages": r1["stages"]}
    report["run2_idempotent"] = r2["inserted"] == 0

    # 2) 真实条目的阶段分类（GMT 实测材料）：声明=正式结果、纪要=评论
    store = NewsStore(DB)
    rows = [dict(r) for r in store.query_items(source="fed", limit=50)[0]]
    store.close()
    stages_seen = {}
    for r in rows:
        ref = build_event_reference(r)
        stages_seen[r["title"][:60]] = ref["event_stage"]
    report["event_stages"] = stages_seen

    # 3) R2：同一正式公告模拟评分 6 后仍可见
    store = NewsStore(DB)
    unscored = [dict(r) for r in store.fetch_unscored()]
    stmt = next(r for r in unscored if "FOMC statement" in r["title"])
    store.apply_scores([{"id": stmt["id"], "category": "industry", "importance": 6,
                         "direction": "neutral", "symbols": [], "note": "repair1 mock"}])
    store.close()
    svc = NewsfeedService(db_path=str(DB))
    brief = svc.major_events_brief(days=7)
    visible = [i for i in brief["items"] if "FOMC statement" in i["title"]]
    report["official_scored6_visible"] = len(visible) == 1
    report["official_scored6_importance"] = visible[0]["importance"] if visible else None

    # 4) R4：评分异常落库收尾（真实材料，模拟评分函数抛异常）
    real_score = pipeline._score_all

    def boom(store):
        raise RuntimeError("repair1 injected score failure")

    pipeline._score_all = boom
    r3 = pipeline.run_pipeline(DB, config=_CFG, no_llm=False)
    pipeline._score_all = real_score
    store = NewsStore(DB)
    row = dict(store.latest_run())
    store.close()
    stats = json.loads(row["stats_json"])
    report["score_exception"] = {
        "run_finalized": row["status"] != "running" and row["finished_at"] is not None,
        "score_stage": stats["stages"]["score"]["status"],
        "digest_stage": stats["stages"]["digest"]["status"],
        "push_stage": stats["stages"]["push"]["status"],
    }

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), "utf-8")
    print(json.dumps({
        "run1_status": r1["status"], "fed_inserted": r1["per_source"].get("fed"),
        "run2_idempotent": report["run2_idempotent"],
        "official_scored6_visible": report["official_scored6_visible"],
        "score_exception": report["score_exception"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
