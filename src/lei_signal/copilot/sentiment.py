"""情绪面数据提供者（Agent 超级入口 §4.I 插槽，research_proxy）。

定位：叙事标注层——只标注、只作排序参考，永不硬过滤信号、不参与技术判定
（docs/plan-agent-superentry-v1.md §1 / AGENTS.md 红线）。

数据源（三层独立降级，任一缺失不阻塞）：
1. 板块散户热度：读 sector_trend_snapshot.json 的 heat 字段（磁盘快照，
   口径与阈值见 rules.v2.yaml retail_heat 段）；
2. 标的→板块映射：sector_members.json 反向索引（个股可属多板块，
   取热度状态最极端的板块作标注；ETF/未覆盖标的返回 None 不冒充）；
3. 大盘融资环境：东财两融余额 20 日变化率（散户杠杆扩张/收缩期，
   独立情绪源；网络失败返回 None）。

措辞纪律（回测阈值未定案期间）：过热/冰点只作中性提示，不得声称
「大概率下跌/上涨」；阈值终案后由 rules.v2.yaml 驱动更新文案。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from lei_signal.domain.rules_config import get_rule

_CACHE = Path(os.environ.get("LEI_CACHE_ROOT", Path.home() / ".lei_signal_lab/cache"))

_HEAT_STATE_CN = {
    "warning": "散户情绪过热（{}分位），波动可能加大",
    "hot": "散户情绪偏热（{}分位）",
    "cold": "散户情绪冰点（{}分位），短期或有惯性压力",
    "neutral": "散户情绪中性（{}分位）",
}


def _heat_version() -> str:
    try:
        return str(get_rule("retail_heat").version)
    except Exception:  # noqa: BLE001 - 账本未登记不阻塞标注
        return "default"


def load_sector_sentiment() -> dict:
    """板块情绪面数据包（读快照，磁盘 only，无网络）。"""
    snap_path = _CACHE / "sector_trend_snapshot.json"
    try:
        snap = json.loads(snap_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"available": False, "reason": "板块快照缺失", "by_board": {}}
    meta = snap.get("heat") or {}
    by_board: dict[str, dict] = {}
    hot, cold = [], []
    for b in snap.get("boards", []):
        pct = b.get("heat_pctile")
        if pct is None:
            continue
        if b.get("heat_warning"):
            state = "warning"
        elif b.get("heat_hot"):
            state = "hot"
        elif b.get("heat_cold"):
            state = "cold"
        else:
            state = "neutral"
        rec = {
            "name": b.get("name"),
            "level": b.get("level"),
            "stage": b.get("stage"),
            "heat_pctile": pct,
            "state": state,
            "state_cn": _HEAT_STATE_CN[state].format(round(pct)),
            "note_cn": b.get("heat_note_cn"),
        }
        by_board[b.get("code", "")] = rec
        if state == "warning" and len(hot) < 8:
            hot.append(rec)
        elif state == "cold" and len(cold) < 8:
            cold.append(rec)
    return {
        "available": bool(by_board),
        "as_of": snap.get("as_of"),
        "heat_meta": {
            "metric": meta.get("metric"),
            "window_days": meta.get("window_days"),
            "rule_version": meta.get("rule_version", _heat_version()),
            "n_pool": meta.get("n_pool"),
        },
        "by_board": by_board,
        "hot_boards": hot,
        "cold_boards": cold,
        "note_cn": "资金面叙事标注（research_proxy）：热度=小单−超大单分化，"
                   "只提示不判定、不构成买卖点。",
    }


def build_symbol_index(sentiment: dict | None = None) -> dict[str, dict]:
    """个股代码 → 所属板块中热度状态最极端的一条（用于推荐卡标注）。"""
    sentiment = sentiment or load_sector_sentiment()
    if not sentiment.get("available"):
        return {}
    members_path = _CACHE / "sector_members.json"
    try:
        members = json.loads(members_path.read_text(encoding="utf-8"))["boards"]
    except (OSError, json.JSONDecodeError, KeyError):
        return {}
    by_board = sentiment["by_board"]
    idx: dict[str, dict] = {}
    for code, info in members.items():
        rec = by_board.get(code)
        if not rec:
            continue
        for sym in info.get("members", []):
            cur = idx.get(sym)
            if cur is None or _severity(rec) > _severity(cur):
                idx[sym] = {**rec, "board": code}
    return idx


def _severity(rec: dict) -> int:
    return {"warning": 3, "hot": 2, "cold": 1, "neutral": 0}.get(rec.get("state"), 0)


def symbol_sentiment_cn(symbol: str, index: dict[str, dict] | None = None) -> str | None:
    """单标的情绪标注文案（如「电子（所属板块：散户情绪偏热）」）。None=未覆盖。"""
    index = index if index is not None else build_symbol_index()
    rec = index.get(symbol)
    if not rec:
        return None
    return f"{rec['name']}：{rec['state_cn']}"


def margin_regime_cn() -> dict | None:
    """大盘融资环境（散户杠杆扩张/收缩期）。失败返回 None 不阻塞。"""
    try:
        from lei_signal.fundamentals import sources

        hist = sources.fetch_margin_history(lookback_days=60)
        series = sorted(
            (d, v.get("rzye_yi")) for d, v in hist.items() if v.get("rzye_yi") is not None
        )
        if len(series) < 25:
            return None
        now = series[-1][1]
        past = series[-21][1]
        chg = (now / past - 1.0) * 100 if past else None
        if chg is None:
            return None
        return {
            "rzye_yi": round(now, 0),
            "chg_20d_pct": round(chg, 2),
            "regime": "expansion" if chg > 0 else "contraction",
            "regime_cn": "融资扩张期（散户借钱加仓意愿上升）" if chg > 0
                         else "融资收缩期（散户去杠杆）",
        }
    except Exception:  # noqa: BLE001 - 情绪面缺数据不阻塞主流程
        return None
