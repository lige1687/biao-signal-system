"""市场宽度只读模块（超级入口叙事标注层）。

数据通道（2026-09-05 勘察）：
- A股：``~/.lei_signal_lab/cache/a_share_ma_breadth_history.json``（1261 日历史，
  每日更新，站上 MA20/50/200 个股占比）。SQLite 的 market_breadth_snapshots
  管道自建成起未成功产出 A 股数据（仅 8 月初试验写入 1-2 行），不走。
- 美股：market_breadth_snapshots 表 SP500 有 1986→2026-08-14 完整历史
  （data_status='complete'），8-14 后因成分股行情源限流断档——如实标注断档
  日期，不用旧数据冒充当下。

红线：只做叙事标注（直读百分比+大白话描述），不打分、不定阈值、不参与
技术判定；所有输出标 research_proxy。
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

_BREADTH_JSON = Path.home() / ".lei_signal_lab" / "cache" / "a_share_breadth_history.json"
_US_DB = Path.home() / ".lei_signal_lab" / "lab.db"


_PCT_WORDS = ("不到一成", "约一成", "约两成", "约三成", "约四成",
              "约一半", "约六成", "约七成", "约八成", "约九成")


def _pct_cn(v: float) -> str:
    """百分比四舍五入到成数再转大白话（49.96%→约一半），不做档位判定。"""
    tenths = round(v / 10)
    if tenths >= 10:
        return "接近全部"
    if tenths <= 0:
        return _PCT_WORDS[0]
    return _PCT_WORDS[tenths]


def a_share_breadth() -> dict:
    """A股宽度：JSON 通道直读最新值，附 5 日变化方向（叙事标注）。"""
    try:
        rows = json.loads(_BREADTH_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"available": False, "note_cn": "A股宽度文件缺失或不可读"}
    if not isinstance(rows, list) or not rows:
        return {"available": False, "note_cn": "A股宽度文件为空"}
    latest = rows[-1]
    prev = rows[-6] if len(rows) >= 6 else rows[0]
    out = {
        "available": True,
        "as_of": latest.get("date"),
        "ma20_pct": latest.get("ma20_pct"),
        "ma50_pct": latest.get("ma50_pct"),
        "ma200_pct": latest.get("ma200_pct"),
        "note_cn": "叙事标注（research_proxy）：站上均线的个股占比，只描述不判定",
    }
    deltas = {}
    for key in ("ma20_pct", "ma50_pct", "ma200_pct"):
        cur, old = latest.get(key), prev.get(key)
        if isinstance(cur, (int, float)) and isinstance(old, (int, float)):
            deltas[key] = round(float(cur) - float(old), 2)
    out["chg_5d"] = deltas or None
    return out


def us_breadth() -> dict:
    """美股宽度：表内最新 complete 行；断档时如实标注，不冒充当下。"""
    if not _US_DB.exists():
        return {"available": False, "note_cn": "美股宽度库缺失"}
    try:
        conn = sqlite3.connect(f"file:{_US_DB}?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT as_of, breadth_20, breadth_50 FROM market_breadth_snapshots "
            "WHERE market_id='SP500' AND breadth_20 IS NOT NULL "
            "ORDER BY as_of DESC LIMIT 1"
        ).fetchone()
        conn.close()
    except sqlite3.Error:
        return {"available": False, "note_cn": "美股宽度读取失败"}
    if row is None:
        return {"available": False, "note_cn": "美股宽度无数据"}
    return {
        "available": True,
        "as_of": row["as_of"],
        "breadth_20": row["breadth_20"],
        "breadth_50": row["breadth_50"],
        "note_cn": f"数据截至 {row['as_of']}（成分股行情源限流断档中）",
    }


def a_share_breadth_cn(pack: dict | None = None) -> str | None:
    """A股宽度一句话（大白话直读，无阈值无档位）。"""
    p = pack if pack is not None else a_share_breadth()
    if not p.get("available"):
        return None
    parts = []
    for key, label in (("ma20_pct", "20日线"), ("ma50_pct", "50日线"),
                       ("ma200_pct", "200日线")):
        v = p.get(key)
        if isinstance(v, (int, float)):
            parts.append(f"{_pct_cn(float(v))}的个股在{label}上方（{v:.0f}%）")
    if not parts:
        return None
    return "A股宽度：" + "，".join(parts)


def us_breadth_cn(pack: dict | None = None) -> str | None:
    p = pack if pack is not None else us_breadth()
    if not p.get("available"):
        return None
    b20 = p.get("breadth_20")
    if not isinstance(b20, (int, float)):
        return None
    return (
        f"美股宽度：{_pct_cn(float(b20))}的标普成分股在20日线上方"
        f"（{b20:.0f}%，截至 {p.get('as_of')}）"
    )


__all__ = [
    "a_share_breadth",
    "us_breadth",
    "a_share_breadth_cn",
    "us_breadth_cn",
]
