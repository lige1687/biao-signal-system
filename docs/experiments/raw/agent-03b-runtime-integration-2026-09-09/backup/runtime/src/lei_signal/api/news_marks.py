"""K 线消息标记（Web 端展示层，参考层）。

把该标的的重要消息（已评分、importance≥6）按发布日聚合成 K 线标记点，
供前端在主图上打「📰 消息日」标记——消息面与技术面同屏对照：利空出来
那天价格跌没跌、利多后有没有跟上。

红线（与 newsfeed 模块一致）：
- 判定权在量价规则层；本模块只做「消息 → 日期」的展示对齐，不产生
  任何交易信号、不给操作建议。
- 只取已评分条目（direction/importance 是 LLM 结构化工序的产物）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lei_signal.newsfeed.store import NewsStore

#: 上图的最低重要性：低于 6 的常规消息不打点（K 线标记预算有限）。
MIN_IMPORTANCE = 6

_DIR_CN = {"bullish": "利多↑", "bearish": "利空↓", "neutral": "中性"}


def build_news_marks(
    db_path: str | Path,
    *,
    symbol: str,
    display_name: str | None,
    dates: list[str],
    limit: int = 100,
) -> list[dict[str, Any]]:
    """按 K 线交易日聚合该标的的重要消息（时间升序）。

    只返回 date 命中 ``dates``（交易日列表）的聚合点——非交易日消息
    归不到 K 线上，丢弃（次日通常会有后续报道覆盖）。
    板块代码（TH…SECTOR）配展示名双匹配，与 /api/news/items 口径一致。
    """
    if not dates:
        return []
    match = f"{symbol},{display_name}" if display_name else symbol
    date_set = set(dates)
    store = NewsStore(db_path)
    try:
        rows, _total = store.query_items(
            symbol=match,
            scored="scored",
            min_importance=MIN_IMPORTANCE,
            date_from=dates[0],
            limit=limit,
        )
    finally:
        store.close()
    by_day: dict[str, dict[str, Any]] = {}
    for r in rows:
        day = str(r["published_at"])[:10]
        if day not in date_set:
            continue
        importance = r["importance"] or 0
        direction = r["direction"] if r["direction"] in _DIR_CN else "neutral"
        agg = by_day.get(day)
        if agg is None:
            agg = {
                "date": day,
                "direction": direction,
                "importance": importance,
                "count": 1,
                "titles": [str(r["title"] or "")[:40]],
            }
            by_day[day] = agg
        else:
            agg["count"] += 1
            if importance > agg["importance"]:
                agg["importance"] = importance
                agg["direction"] = direction
            if len(agg["titles"]) < 3:
                agg["titles"].append(str(r["title"] or "")[:40])
    return [by_day[d] for d in sorted(by_day)]


__all__ = ["MIN_IMPORTANCE", "build_news_marks"]
