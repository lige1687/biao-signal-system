"""分标的×模块历史胜率查询（标注层参考，不参与技术判定）。

数据资产：docs/experiments/module_winrate.json（scripts/build_module_winrate.py
从回测 run 明细聚合，同日同标去重，全期+近两年双窗口）。
用户口径（2026-09-06）：给当前信号时结合历史经验报「这笔胜率怎么样」，
Agent 据此给倾向——胜率是叙事参考；样本 <3 笔时如实标注样本过小。
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

_PATHS = [
    Path(__file__).resolve().parents[3] / "docs" / "experiments" / "module_winrate.json",
    Path(__file__).resolve().parents[2] / "docs" / "experiments" / "module_winrate.json",
]
_lock = threading.Lock()
_cache: dict[str, Any] | None = None
_mtime: float | None = None


def _load() -> dict[str, Any]:
    global _cache, _mtime
    path = next((p for p in _PATHS if p.exists()), None)
    if path is None:
        return {"entries": {}}
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = None
    with _lock:
        if _cache is not None and mtime is not None and _mtime == mtime:
            return _cache
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = _cache or {"entries": {}}
        _cache, _mtime = data, mtime
        return data


def _fmt(stats: dict) -> str:
    n = stats.get("n") or 0
    win = round((stats.get("win_rate") or 0) * 100)
    avg = stats.get("avg_r")
    return f"{n}笔、胜率{win}%、平均每笔{avg:+g}倍风险金"


def winrate_for(symbol: str, module: str | None = None) -> dict[str, Any] | None:
    """查该标的（可指定模块）的历史成绩。

    返回 {winrate_cn, modules: {模块: {winrate_cn, n, win_rate, avg_r}}, note_cn}
    或 None（无任何样本——如实说无，不硬凑）。样本 <3 标注样本过小。
    """
    entries: dict = _load().get("entries") or {}
    mine = {
        k.split("|")[1]: v
        for k, v in entries.items()
        if k.startswith(f"{symbol}|")
    }
    if module is not None:
        mine = {m: v for m, v in mine.items() if m == module}
    if not mine:
        return None
    mods: dict[str, Any] = {}
    for m, v in mine.items():
        stats = v.get("recent") or v.get("all") or {}
        n = stats.get("n") or 0
        if n == 0:
            continue
        cn = _fmt(stats)
        if n < 3:
            cn += "（样本过小，仅供参考）"
        mods[m] = {
            "winrate_cn": cn,
            "n": n,
            "win_rate": stats.get("win_rate"),
            "avg_r": stats.get("avg_r"),
        }
    if not mods:
        return None
    if len(mods) == 1:
        m, v = next(iter(mods.items()))
        summary = f"{m}模块历史：{v['winrate_cn']}"
    else:
        parts = "；".join(f"{m}模块{v['winrate_cn']}" for m, v in mods.items())
        summary = f"该标的历史成绩——{parts}"
    return {
        "winrate_cn": summary,
        "modules": mods,
        "note_cn": "历史胜率标注（回测统计，样本有限，叙事参考不构成判定）",
    }


__all__ = ["winrate_for"]
