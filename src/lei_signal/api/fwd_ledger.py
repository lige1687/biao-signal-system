"""前向验证成绩单（Web 展示层，只读）。

把两套前向存证账本的到期对账成绩聚合成一个只读视图：
- A 情绪线：``sentiment_signal_journal.json`` 的 review 结果，四桶
  （冰点机会/强热警报 × 10/20 日），口径与 ``scripts/sentiment_journal.py``
  的 review 输出一致（n / 胜率=收益>0 占比 / 均值）；
- B 推荐线：``recommendation_journal`` 表 outcome（按标的 × T+1/5/20 涨跌）。

本模块不做任何判定、不写任何账本；数据缺失时返回 available=false + 原因，
不编造数据。
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from lei_signal.copilot import journal as copilot_journal

#: 与 scripts/sentiment_journal.py 同一相对路径（LEI_CACHE_ROOT 优先）。
SENTIMENT_JOURNAL_NAME = "sentiment_signal_journal.json"

#: 四桶定义：key 对齐账本 review 字段，对外 key 用 pick/alarm 命名，label 对齐 review 打印文案。
_SENTIMENT_BUCKETS: tuple[tuple[str, str, str, int], ...] = (
    ("t10", "pick10", "冰点机会·10日", 10),
    ("t20", "pick20", "冰点机会·20日", 20),
    ("a10", "alarm10", "强热警报·10日", 10),
    ("a20", "alarm20", "强热警报·20日", 20),
)

#: B 线对账档位（对齐 score_journal_outcomes 默认 horizons）。
_HORIZONS: tuple[tuple[str, int], ...] = (("t1", 1), ("t5", 5), ("t20", 20))


def sentiment_journal_path() -> Path:
    """情绪账本 JSON 路径（与 scripts/sentiment_journal.py 的定位规则一致）。"""
    from lei_signal.data.cache import DEFAULT_CACHE_DIR

    cache = Path(os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR)))
    return cache / SENTIMENT_JOURNAL_NAME


def _bucket_stats(values: list[float], *, scale: float) -> dict[str, Any] | None:
    """胜率=收益>0 占比；均值按 scale 换算成百分点（情绪线存分数×100，推荐线本就是百分点×1）。"""
    if not values:
        return None
    return {
        "n": len(values),
        "winRatePct": round(sum(1 for v in values if v > 0) / len(values) * 100, 1),
        "meanPct": round(sum(values) / len(values) * scale, 2),
    }


def build_sentiment_stats(journal: dict) -> dict[str, Any]:
    """聚合情绪账本四桶成绩（纯函数，入参为已加载的账本 dict）。"""
    records = journal.get("records") or []
    buckets: list[dict[str, Any]] = []
    for key, out_key, label, horizon in _SENTIMENT_BUCKETS:
        values = [v for rec in records for v in ((rec.get("review") or {}).get(key) or [])]
        stats = _bucket_stats(values, scale=100.0)
        buckets.append({
            "key": out_key,
            "labelCn": label,
            "horizonDays": horizon,
            **({"n": stats["n"], "winRatePct": stats["winRatePct"],
                "meanPct": stats["meanPct"]} if stats else {"n": 0}),
        })
    done = sum(1 for rec in records if (rec.get("review") or {}).get("done"))
    return {
        "records": len(records),
        "reviewedRecords": done,
        "buckets": buckets,
    }


def load_sentiment_stats(path: Path) -> dict[str, Any]:
    """读情绪账本并聚合；缺席/损坏/无到期样本时明确降级，不编数据。"""
    if not path.exists():
        return {"available": False, "reason": "账本文件不存在（情绪信号尚未存证过）"}
    try:
        journal = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"available": False, "reason": f"账本文件不可读：{exc}"}
    if not isinstance(journal, dict) or not journal.get("records"):
        return {"available": False, "reason": "账本为空（还没有存证记录）"}
    stats = build_sentiment_stats(journal)
    if not any(b["n"] > 0 for b in stats["buckets"]):
        return {"available": False, "reason": "有存证记录但尚无到期对账样本（信号触发后 10/20 个交易日才到期）",
                **stats}
    return {"available": True, "reason": "", **stats}


def build_recommendation_stats(conn: sqlite3.Connection, *, limit: int = 120) -> dict[str, Any]:
    """聚合推荐账本 outcome：按标的 × T+1/5/20 的样本数/均值/胜率（只读）。"""
    rows = conn.execute(
        "SELECT run_date, payload, outcome FROM recommendation_journal "
        "WHERE outcome IS NOT NULL ORDER BY run_date DESC LIMIT ?",
        (limit,),
    ).fetchall()
    if not rows:
        return {"available": False, "reason": "推荐账本尚无任何到期对账结果"}
    names: dict[str, str] = {}
    by_symbol: dict[str, dict[str, list[float]]] = {}
    for row in rows:
        try:
            outcome = json.loads(row["outcome"])
        except (TypeError, ValueError):
            continue
        if not isinstance(outcome, dict):
            continue
        # 名称从存证 payload 里尽力解析（占位行解析失败即跳过，不影响成绩）
        try:
            card = copilot_journal.load_recommendation(conn, row["run_date"])
            for item in card.items or []:
                if item.symbol and item.display_name:
                    names.setdefault(item.symbol, item.display_name)
        except Exception:  # noqa: BLE001  payload 缺失/占位时名称留空
            pass
        for symbol, changes in outcome.items():
            if not isinstance(changes, dict):
                continue
            per_symbol = by_symbol.setdefault(symbol, {k: [] for k, _ in _HORIZONS})
            for key, horizon in _HORIZONS:
                v = changes.get(f"chg_{horizon}d")
                if isinstance(v, (int, float)):
                    per_symbol[key].append(float(v))

    symbols = []
    for symbol, per in sorted(by_symbol.items()):
        entry: dict[str, Any] = {
            "symbol": symbol,
            "nameCn": names.get(symbol) or None,
            "samples": sum(len(v) for v in per.values()),
        }
        for key, _ in _HORIZONS:
            stats = _bucket_stats(per[key], scale=1.0)
            entry[key] = stats if stats else None
        if entry["samples"] > 0:
            symbols.append(entry)
    if not symbols:
        return {"available": False, "reason": "对账结果存在但无任何有效涨跌样本"}
    return {
        "available": True,
        "reason": "",
        "scoredDates": len(rows),
        "latestDate": rows[0]["run_date"],
        "horizonsCn": {"t1": "次日", "t5": "5日", "t20": "20日"},
        "bySymbol": symbols,
    }


__all__ = [
    "SENTIMENT_JOURNAL_NAME",
    "build_sentiment_stats",
    "build_recommendation_stats",
    "load_sentiment_stats",
    "sentiment_journal_path",
]
