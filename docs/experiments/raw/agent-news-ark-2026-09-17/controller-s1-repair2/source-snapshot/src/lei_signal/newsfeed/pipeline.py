"""每日管线编排：抓取 → 粗筛 → 入库 → LLM 打分 → 今日简报。

单项降级：任一源失败记入 ``news_runs.errors_json`` 并继续；全部源失败
status=failed，部分失败 partial，全成 ok。LLM 失败保持未评分态。

阶段留痕（2026-09-17 S1）：run.status 保持「采集结果」口径不变（兼容旧
消费方）；stats_json 新增 ``stages``（collect/score/digest/push 各自的
status/finished_at/errors）与 ``sources``（每源尝试时间/成败），让
「旧 ok 但评分失败」「no_llm 跳过」「部分源失败」可以事后核对，不再
只靠日志 warning。
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from lei_signal.data.cache import DEFAULT_CACHE_DIR
from lei_signal.newsfeed.config_loader import load_config
from lei_signal.newsfeed.llm_score import (
    generate_blogger_summaries,
    generate_digest,
    score_items,
)
from lei_signal.newsfeed.models import NewsItem
from lei_signal.newsfeed.normalize import preclassify
from lei_signal.newsfeed.sources import NewsSourceError
from lei_signal.newsfeed.sources.bilibili import BilibiliClient, fetch_new_up_items
from lei_signal.newsfeed.sources.eastmoney import collect_eastmoney
from lei_signal.newsfeed.sources.fed import FED_PRESS_URL, collect_fed_press
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


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


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
) -> tuple[dict[str, int], list[dict], dict[str, dict]]:
    """跑全部源。返回（每源入库数, 错误列表, 每源尝试记录）。"""
    stats: dict[str, int] = {}
    errors: list[dict] = []
    attempts: dict[str, dict] = {}
    lookback = _lookback_iso(int(cfg.get("lookback_days") or 3))

    def _ingest(source_key: str, items: list[NewsItem], watermark: str | None) -> None:
        # 先写库、后推进水位（2026-09-17 S1 修复，原顺序相反）：写库失败时
        # 水位不动，下次重抓，dedupe 保证不重复插入；不提前推进水位漏新闻。
        if not items:
            stats[source_key] = 0
            if watermark is not None:
                store.set_watermark(source_key, watermark)
            return
        inserted = store.insert_items([it.to_row() for it in items])
        stats[source_key] = inserted
        if watermark is not None:
            store.set_watermark(source_key, watermark)

    def _attempt(source_key: str, fn, *, warn_prefix: str | None = None) -> None:
        """单源执行 + 尝试留痕（attempted_at/ok/error），失败不阻断其他源。"""
        attempted_at = _now_iso()
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - 单项降级
            msg = str(exc)[:200]
            errors.append({"source": source_key, "error": msg})
            attempts[source_key] = {"attempted_at": attempted_at, "ok": False, "error": msg}
            logger.warning("newsfeed %s 失败: %s", warn_prefix or source_key, exc)
        else:
            attempts[source_key] = {"attempted_at": attempted_at, "ok": True, "error": None}

    # ---- 东财快讯 ----
    def _eastmoney() -> None:
        wm_raw = store.get_watermark("eastmoney")
        since = None if (full or wm_raw is None) else int(wm_raw)
        items, wm = collect_eastmoney(since)
        if wm is not None and (full or wm_raw is None):
            items = [i for i in items if i.published_at >= lookback]
        kept, _dropped = _flash_filter(items, cfg)
        _ingest("eastmoney", kept, wm)

    _attempt("eastmoney", _eastmoney)

    # ---- 新浪 7x24 ----
    def _sina() -> None:
        wm_raw = store.get_watermark("sina")
        since = None if (full or wm_raw is None) else int(wm_raw)
        items, wm = collect_sina(since)
        if wm is not None and (full or wm_raw is None):
            items = [i for i in items if i.published_at >= lookback]
        kept, _dropped = _flash_filter(items, cfg)
        _ingest("sina", kept, wm)

    _attempt("sina", _sina)

    # ---- 美联储官方货币政策公告（2026-09-17 S1，config 显式启用才接入）----
    fed_cfg = cfg.get("fed_press") or {}
    if fed_cfg.get("enabled"):

        def _fed() -> None:
            wm_raw = store.get_watermark("fed")
            since = None if (full or wm_raw is None) else wm_raw
            diag: dict = {}
            items, wm = collect_fed_press(
                url=str(fed_cfg.get("url") or FED_PRESS_URL), since_iso=since,
                diagnostics=diag,
            )
            if wm is not None and (full or wm_raw is None):
                items = [i for i in items if i.published_at >= lookback]
            invalid = diag.get("invalid") or []
            # 主控复核 R6：混合响应中合法条目保留，但本次读取不完整——
            # 不推进书签（修正后的漏项下次重试可补进，dedupe 防重复），
            # 并把数量/原因记入运行记录（部分失败，不冒充全正常）。
            _ingest("fed", items, None if invalid else wm)
            if invalid:
                brief = "；".join(
                    f"{(d.get('title') or '?')[:24]}:{d.get('reason')}"
                    for d in invalid[:3]
                )
                raise NewsSourceError(
                    f"fed {diag.get('invalid_count')} 条公告不可用（{brief}）；"
                    "合法条目已保留，本次未推进书签"
                )

        _attempt("fed", _fed)

    # ---- Google News 查询 ----
    for query in cfg.get("gnews_queries") or []:
        key = f"gnews:{query}"

        def _gnews(q: str = query, k: str = key) -> None:
            wm_raw = store.get_watermark(k)
            since = None if (full or wm_raw is None) else wm_raw
            items, wm = collect_rss(q, is_gnews=True, since_iso=since)
            for it in items:
                it.category = "industry"
            if wm is not None and (full or wm_raw is None):
                items = [i for i in items if i.published_at >= lookback]
            _ingest(k, items, wm)

        _attempt(key, _gnews)

    # ---- 通用 RSS（P2 公众号 wewe-rss）----
    for feed_url in cfg.get("rss_feeds") or []:
        key = f"rss:{feed_url}"

        def _rss(u: str = feed_url, k: str = key) -> None:
            wm_raw = store.get_watermark(k)
            since = None if (full or wm_raw is None) else wm_raw
            items, wm = collect_rss(u, is_gnews=False, since_iso=since)
            for it in items:
                it.category = "blogger"
            _ingest(k, items, wm)

        _attempt(key, _rss)

    # ---- B站 UP主 ----
    cookie_path = Path(DEFAULT_CACHE_DIR) / "newsfeed" / "bili_cookies.json"
    for up in cfg.get("bili_ups") or []:
        mid = int(up.get("mid") or 0)
        name = str(up.get("name") or mid)
        if not mid:
            continue
        key = f"bilibili:{mid}"

        def _bili(m: int = mid, n: str = name, k: str = key) -> None:
            client = bili_client or BilibiliClient(
                cookie_path, sessdata=os.environ.get("BILI_SESSDATA", "")
            )
            wm_raw = store.get_watermark(k)
            items, wm = fetch_new_up_items(
                client,
                m,
                n,
                None if (full or wm_raw is None) else wm_raw,
                lookback_iso=lookback if (full or wm_raw is None) else None,
                title_blocklist=list(cfg.get("bili_title_blocklist") or ["直播回放"]),
                max_duration_sec=cfg.get("bili_max_duration_sec", 1800),
            )
            _ingest(k, items, wm)

        _attempt(key, _bili, warn_prefix=f"{key}({name})")

    return stats, errors, attempts


def _score_all(store: NewsStore) -> tuple[int, list[dict]]:
    """未评分条目分批打分。返回（成功打分数, 失败记录列表）。

    批次按"条数 ≤20 且累计字符 ≤30000"双限制切分：长字幕（直播回放）
    单条可达 2 万字，固定 20 条/批会撑爆模型上下文（2026-08-27 实测批
    80-94 两次失败）。批失败原样重试 1 次，仍失败放弃该批（保持未评分）。
    失败记录进 stats.stages.score.errors（2026-09-17 S1），不只日志 warning。
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
    failures: list[dict] = []

    def _flush(b: list[dict]) -> None:
        nonlocal total
        if _run_score_batch(store, b):
            total += len(b)
        else:
            failures.append({
                "stage": "score",
                "error": f"打分批 {b[0].get('id')}-{b[-1].get('id')} 两次失败（保持未评分态）",
            })

    for row in rows:
        w = _row_weight(row)
        if batch and (len(batch) >= _SCORE_BATCH or weight + w > _SCORE_CHAR_BUDGET):
            _flush(batch)
            batch, weight = [], 0
        batch.append(row)
        weight += w
    if batch:
        _flush(batch)
    if failures:
        logger.warning("newsfeed 打分 %d 个批失败（保持未评分态）", len(failures))
    return total, failures


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
        per_source, errors, attempts = _collect_all(
            store, cfg, full=full, bili_client=bili_client
        )
        collect_status = "ok"
        if errors and not per_source:
            collect_status = "failed"
        elif errors:
            collect_status = "partial"
        stages: dict[str, dict] = {
            "collect": {
                "status": collect_status,
                "finished_at": _now_iso(),
                "errors": list(errors),
            }
        }
        # 内容保留队列：字幕/正文大字段保留 7 天（2026-09-05 用户口径），
        # 过期清理；评分元数据保留。放在抓取后、打分前（打分只读近期条目）。
        store.clear_old_content(days=7)
        scored = 0
        digest_ok = False
        pushed = 0
        if no_llm:
            # 明确记 skipped：不误写 failed，也不冒充全 ok（2026-09-17 S1）。
            stages["score"] = {
                "status": "skipped", "finished_at": None, "errors": [], "reason": "no_llm",
            }
            stages["digest"] = {
                "status": "skipped", "finished_at": None, "errors": [], "reason": "no_llm",
            }
            stages["push"] = {
                "status": "skipped", "finished_at": None, "errors": [], "reason": "no_llm",
            }
        else:
            # 阶段异常收尾（2026-09-17 主控复核 R4）：评分/简报抛异常也要把
            # 已完成的采集成果与失败阶段落库——不能让任务永远停在 running。
            score_ok = False
            try:
                scored, score_errors = _score_all(store)
                stages["score"] = {
                    "status": "failed" if score_errors else "ok",
                    "finished_at": _now_iso(),
                    "errors": score_errors,
                }
                score_ok = True
            except Exception as exc:  # noqa: BLE001 — 阶段失败落库后继续收尾
                logger.warning("newsfeed 评分阶段异常: %s", exc)
                scored = 0
                stages["score"] = {
                    "status": "failed",
                    "finished_at": _now_iso(),
                    "errors": [{
                        "stage": "score",
                        "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                    }],
                }
            if not score_ok:
                # 下游未执行明确记录（不假装跑过，也不触发外发）。
                stages["digest"] = {
                    "status": "skipped", "finished_at": None, "errors": [],
                    "reason": "upstream_failed",
                }
                stages["push"] = {
                    "status": "skipped", "finished_at": None, "errors": [],
                    "reason": "upstream_failed",
                }
            else:
                try:
                    today = datetime.now().astimezone().strftime("%Y-%m-%d")
                    digest_rows = [dict(r) for r in store.scored_rows_for_digest(today)]
                    if digest_rows:
                        digest = generate_digest(digest_rows)
                        if digest is None:
                            # 推理模型 thinking 偶发吃满 token：原样重试 1 次。
                            digest = generate_digest(digest_rows)
                        if digest is not None:
                            # 博主立场小结并入当日简报 payload（失败不阻断简报保存）。
                            blogger_rows = [dict(r) for r in store.blogger_rows_recent(7)]
                            if blogger_rows:
                                bloggers = generate_blogger_summaries(blogger_rows)
                                if bloggers:
                                    digest["bloggers"] = bloggers
                            store.save_digest(today, digest)
                            digest_ok = True
                            stages["digest"] = {
                                "status": "ok", "finished_at": _now_iso(), "errors": [],
                            }
                        else:
                            stages["digest"] = {
                                "status": "failed",
                                "finished_at": _now_iso(),
                                "errors": [{
                                    "stage": "digest", "error": "简报生成两次失败，未保存",
                                }],
                            }
                    else:
                        stages["digest"] = {
                            "status": "skipped", "finished_at": None, "errors": [],
                            "reason": "no_items",
                        }
                except Exception as exc:  # noqa: BLE001 — 简报异常同样落库
                    logger.warning("newsfeed 简报阶段异常: %s", exc)
                    digest_ok = False
                    stages["digest"] = {
                        "status": "failed",
                        "finished_at": _now_iso(),
                        "errors": [{
                            "stage": "digest",
                            "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                        }],
                    }
                # 重大事件推送（宏观线；参考层，best-effort 不阻断管线）
                try:
                    from lei_signal.newsfeed.push import push_daily_brief

                    pushed = push_daily_brief(db_path)
                    stages["push"] = {
                        "status": "ok", "finished_at": _now_iso(), "errors": [],
                    }
                except Exception as exc:  # noqa: BLE001 — 推送失败不影响抓取/打分
                    logger.warning("消息面推送失败: %s", exc)
                    stages["push"] = {
                        "status": "failed",
                        "finished_at": _now_iso(),
                        "errors": [{"stage": "push", "error": str(exc)[:200]}],
                    }
        # run.status 保持「采集结果」口径（兼容旧消费方）；评分/简报/推送
        # 成败只在 stages 里表达，不再被综合 ok 掩盖。
        status = collect_status
        stats = {
            "inserted": sum(per_source.values()),
            "per_source": per_source,
            "scored": scored,
            "digest": digest_ok,
            "pushed": pushed,
            "stages": stages,
            "sources": attempts,
        }
        store.finish_run(run_id, status, stats, errors)
        return {"run_id": run_id, "status": status, **stats, "errors": errors}
    finally:
        store.close()


__all__ = ["run_pipeline"]
