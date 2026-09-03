"""每日管线编排：抓取 → 粗筛 → 入库 → LLM 打分 → 今日简报。

单项降级：任一源失败记入 ``news_runs.errors_json`` 并继续；全部源失败
status=failed，部分失败 partial，全成 ok。LLM 失败保持未评分态。
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from lei_signal.data.cache import DEFAULT_CACHE_DIR
from lei_signal.newsfeed.config_loader import load_config
from lei_signal.newsfeed.llm_score import generate_digest, score_items
from lei_signal.newsfeed.models import NewsItem
from lei_signal.newsfeed.normalize import preclassify
from lei_signal.newsfeed.sources.bilibili import BilibiliClient, fetch_new_up_items
from lei_signal.newsfeed.sources.eastmoney import collect_eastmoney
from lei_signal.newsfeed.sources.rss import collect_rss
from lei_signal.newsfeed.sources.sina import collect_sina
from lei_signal.newsfeed.store import NewsStore

logger = logging.getLogger(__name__)

_SCORE_BATCH = 20
#: 批次字符预算：与 _SCORE_BATCH 双限制，防长字幕撑爆上下文。
_SCORE_CHAR_BUDGET = 30000
#: 允许 category=blogger 的源；其余源 LLM 判 blogger 时回落预分类。
_BLOGGER_SOURCES = frozenset({"bilibili", "rss", "wechat"})


def _lookback_iso(days: int) -> str:
    return (datetime.now().astimezone() - timedelta(days=days)).isoformat(timespec="seconds")


def _flash_filter(
    items: list[NewsItem], cfg: dict[str, Any]
) -> tuple[list[NewsItem], int]:
    """快讯粗筛：无类别命中的丢弃。返回（保留, 丢弃数）。"""
    keywords = cfg.get("flash_keywords") or {}
    symbols = cfg.get("symbols") or []
    kept: list[NewsItem] = []
    dropped = 0
    for it in items:
        text = f"{it.title}\n{it.summary or ''}"
        category = preclassify(text, keywords, symbols)
        if category is None:
            dropped += 1
            continue
        it.category = category
        kept.append(it)
    return kept, dropped


def _collect_all(
    store: NewsStore, cfg: dict[str, Any], *, full: bool, bili_client: BilibiliClient | None
) -> tuple[dict[str, int], list[dict]]:
    """跑全部源。返回（每源入库数, 错误列表）。"""
    stats: dict[str, int] = {}
    errors: list[dict] = []
    lookback = _lookback_iso(int(cfg.get("lookback_days") or 3))

    def _ingest(source_key: str, items: list[NewsItem], watermark: str | None) -> None:
        if watermark is not None:
            store.set_watermark(source_key, watermark)
        if not items:
            stats[source_key] = 0
            return
        inserted = store.insert_items([it.to_row() for it in items])
        stats[source_key] = inserted

    # ---- 东财快讯 ----
    try:
        wm_raw = store.get_watermark("eastmoney")
        since = None if (full or wm_raw is None) else int(wm_raw)
        items, wm = collect_eastmoney(since)
        if wm is not None and (full or wm_raw is None):
            items = [i for i in items if i.published_at >= lookback]
        kept, _dropped = _flash_filter(items, cfg)
        _ingest("eastmoney", kept, wm)
    except Exception as exc:  # noqa: BLE001 - 单项降级
        errors.append({"source": "eastmoney", "error": str(exc)[:200]})
        logger.warning("newsfeed eastmoney 失败: %s", exc)

    # ---- 新浪 7x24 ----
    try:
        wm_raw = store.get_watermark("sina")
        since = None if (full or wm_raw is None) else int(wm_raw)
        items, wm = collect_sina(since)
        if wm is not None and (full or wm_raw is None):
            items = [i for i in items if i.published_at >= lookback]
        kept, _dropped = _flash_filter(items, cfg)
        _ingest("sina", kept, wm)
    except Exception as exc:  # noqa: BLE001
        errors.append({"source": "sina", "error": str(exc)[:200]})
        logger.warning("newsfeed sina 失败: %s", exc)

    # ---- Google News 查询 ----
    for query in cfg.get("gnews_queries") or []:
        key = f"gnews:{query}"
        try:
            wm_raw = store.get_watermark(key)
            since = None if (full or wm_raw is None) else wm_raw
            items, wm = collect_rss(query, is_gnews=True, since_iso=since)
            for it in items:
                it.category = "industry"
            if wm is not None and (full or wm_raw is None):
                items = [i for i in items if i.published_at >= lookback]
            _ingest(key, items, wm)
        except Exception as exc:  # noqa: BLE001
            errors.append({"source": key, "error": str(exc)[:200]})
            logger.warning("newsfeed %s 失败: %s", key, exc)

    # ---- 通用 RSS（P2 公众号 wewe-rss）----
    for feed_url in cfg.get("rss_feeds") or []:
        key = f"rss:{feed_url}"
        try:
            wm_raw = store.get_watermark(key)
            since = None if (full or wm_raw is None) else wm_raw
            items, wm = collect_rss(feed_url, is_gnews=False, since_iso=since)
            for it in items:
                it.category = "blogger"
            _ingest(key, items, wm)
        except Exception as exc:  # noqa: BLE001
            errors.append({"source": key, "error": str(exc)[:200]})
            logger.warning("newsfeed %s 失败: %s", key, exc)

    # ---- B站 UP主 ----
    cookie_path = Path(DEFAULT_CACHE_DIR) / "newsfeed" / "bili_cookies.json"
    for up in cfg.get("bili_ups") or []:
        mid = int(up.get("mid") or 0)
        name = str(up.get("name") or mid)
        if not mid:
            continue
        key = f"bilibili:{mid}"
        try:
            client = bili_client or BilibiliClient(
                cookie_path, sessdata=os.environ.get("BILI_SESSDATA", "")
            )
            wm_raw = store.get_watermark(key)
            items, wm = fetch_new_up_items(
                client,
                mid,
                name,
                None if (full or wm_raw is None) else wm_raw,
                lookback_iso=lookback if (full or wm_raw is None) else None,
                title_blocklist=list(cfg.get("bili_title_blocklist") or ["直播回放"]),
                max_duration_sec=cfg.get("bili_max_duration_sec", 1800),
            )
            _ingest(key, items, wm)
        except Exception as exc:  # noqa: BLE001
            errors.append({"source": key, "error": str(exc)[:200]})
            logger.warning("newsfeed %s(%s) 失败: %s", key, name, exc)

    return stats, errors


def _score_all(store: NewsStore) -> int:
    """未评分条目分批打分。

    批次按"条数 ≤20 且累计字符 ≤30000"双限制切分：长字幕（直播回放）
    单条可达 2 万字，固定 20 条/批会撑爆模型上下文（2026-08-27 实测批
    80-94 两次失败）。批失败原样重试 1 次，仍失败放弃该批（保持未评分）。
    """
    total = 0
    rows = [dict(r) for r in store.fetch_unscored(limit=500)]

    def _row_weight(r: dict) -> int:
        return (
            len(r.get("title") or "")
            + len(r.get("summary") or "")
            + len(r.get("content") or "")
        )

    batch: list[dict] = []
    weight = 0
    failures = 0
    for row in rows:
        w = _row_weight(row)
        if batch and (len(batch) >= _SCORE_BATCH or weight + w > _SCORE_CHAR_BUDGET):
            if _run_score_batch(store, batch):
                total += len(batch)
            else:
                failures += 1
            batch, weight = [], 0
        batch.append(row)
        weight += w
    if batch:
        if _run_score_batch(store, batch):
            total += len(batch)
        else:
            failures += 1
    if failures:
        logger.warning("newsfeed 打分 %d 个批失败（保持未评分态）", failures)
    return total


def _run_score_batch(store: NewsStore, batch: list[dict]) -> bool:
    scores = score_items(batch)
    if scores is None:
        scores = score_items(batch)
    if not scores:
        logger.warning(
            "newsfeed 打分批 %d-%d 两次失败，跳过",
            batch[0].get("id"),
            batch[-1].get("id"),
        )
        return False
    # 「博主观点」只留给博主源（B站/公众号/RSS）：快讯与 gnews 的英文股评
    # 专栏常被 LLM 判成 blogger，回落到入库时的预分类，避免博主 tab 被稀释。
    by_id = {r["id"]: r for r in batch}
    for s in scores:
        if s.get("category") == "blogger":
            src = (by_id.get(s["id"]) or {}).get("source")
            if src not in _BLOGGER_SOURCES:
                s["category"] = (by_id.get(s["id"]) or {}).get("category") or "industry"
    store.apply_scores(scores)
    return True


def run_pipeline(
    db_path: str | Path,
    *,
    config: dict[str, Any] | None = None,
    full: bool = False,
    no_llm: bool = False,
    bili_client: BilibiliClient | None = None,
) -> dict[str, Any]:
    """整条管线。返回 run 摘要 dict（run_id/status/inserted/per_source/scored/digest/errors）。"""
    cfg = config or load_config()
    store = NewsStore(db_path)
    try:
        run_id = store.start_run()
        per_source, errors = _collect_all(store, cfg, full=full, bili_client=bili_client)
        scored = 0
        digest_ok = False
        if not no_llm:
            scored = _score_all(store)
            today = datetime.now().astimezone().strftime("%Y-%m-%d")
            digest_rows = [dict(r) for r in store.scored_rows_for_digest(today)]
            if digest_rows:
                digest = generate_digest(digest_rows)
                if digest is None:
                    # 推理模型 thinking 偶发吃满 token：原样重试 1 次。
                    digest = generate_digest(digest_rows)
                if digest is not None:
                    store.save_digest(today, digest)
                    digest_ok = True
        status = "ok"
        if errors and not per_source:
            status = "failed"
        elif errors:
            status = "partial"
        stats = {
            "inserted": sum(per_source.values()),
            "per_source": per_source,
            "scored": scored,
            "digest": digest_ok,
        }
        store.finish_run(run_id, status, stats, errors)
        return {"run_id": run_id, "status": status, **stats, "errors": errors}
    finally:
        store.close()


__all__ = ["run_pipeline"]
