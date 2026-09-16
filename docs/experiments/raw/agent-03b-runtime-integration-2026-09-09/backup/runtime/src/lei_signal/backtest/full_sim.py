"""三层串联完整账户模拟器的纯函数层：信号去重 + 宽度→仓位上限。

依据 docs/handoff-full-stack-sim-prompt.md（2026-08-27）与
docs/experiments/breadth-position-report-2026-08-27.md 附录接口约定。
分层（规格 4.2：市场层在交易层之前）：

- 定闸层（宽度）：A 股全市场 B200（站上 200 日线占比）→ position_cap，
  档位取宽度报告已验证的 B200 版（V1 判定档 / V2 报告推荐档）。
  周频刷新（每周最后交易日收盘信号，次一交易日生效），缺数据日 cap=1.0
  （缺数据不挡交易，与基本面「叙事层不硬过滤」同一纪律）。
- 定重层（资金）：portfolio.PortfolioConfig.cap_fn 接入——单笔预算
  ×cap，并发/池上限 ceil(×cap) 下限 1；只缩新仓，不平旧仓。
- 定点层（信号）：去重后的 A（ETF cm0.5+shrink+门禁）+ B'（个股
  cb30/cl3% breakout a6_1）流；全模块（A+B'+C+D）口径另做去重对账。

信号去重规则（任务一，事前写死）：
1. 同标的同时刻只允许一笔在场信号：新信号到达日（signal_date）落在
   上一笔已接受信号的生命周期 [signal_date, exit_date] 内 → 丢弃（计数）。
2. 同标的同日多模块信号按优先级 A > B' > C > D 取一，其余丢弃（计数）。
3. 完全重复（symbol+signal_date+entry_date 相同）只计一次。

本模块不生成信号、不做 I/O 之外的判定；宽度 json 读取仅限路径展开。
"""
from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping, Sequence
from datetime import date as date_cls
from pathlib import Path

DEFAULT_BREADTH_JSON = Path(
    "~/.lei_signal_lab/cache/a_share_ma_breadth_history.json")

#: 档位表：[(阈值上界(含), 仓位)]，宽度 ≤ 阈值取该档（宽度报告 2026-08-27）。
TIERS_V1 = ((20, 1.0), (40, 0.8), (60, 0.6), (85, 0.4), (999, 0.2))
TIERS_V2 = ((20, 1.0), (40, 0.7), (60, 0.4), (85, 0.2), (999, 0.1))

#: 同日多模块优先级（任务一规则 2）。
MODULE_PRIORITY = ("A", "B'", "B", "C", "D")


def tier_cap(breadth_pct: float, tiers: Sequence[tuple[float, float]]) -> float:
    """宽度（百分数）→ 目标仓位档位。缺数据（None/NaN）→ 1.0（不挡交易）。"""
    if breadth_pct is None or (isinstance(breadth_pct, float)
                               and math.isnan(breadth_pct)):
        return 1.0
    for th, w in tiers:
        if breadth_pct <= th:
            return w
    return tiers[-1][1]


def load_b200_series(path: Path | str = DEFAULT_BREADTH_JSON) -> dict[str, float]:
    """A 股全市场 B200 宽度：{iso_date: 百分数}。"""
    rows = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    return {r["date"][:10]: float(r["ma200_pct"]) for r in rows}


def position_cap_map(
    breadth: Mapping[str, float],
    tiers: Sequence[tuple[float, float]] = TIERS_V2,
    *,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, float]:
    """周频宽度信号 → {生效日: cap}。

    信号日 = 每周（ISO 周）最后一个有宽度数据的交易日；生效日 = 下一个
    交易日（t+1 防前视）。返回的 map 是「生效日→cap」稀疏表，配合
    :func:`cap_fn_from_map` 前向填充使用。start/end 限定回放窗口。
    """
    days = sorted(d for d in breadth if (start is None or d >= start)
                  and (end is None or d <= end))
    caps: dict[str, float] = {}
    last_week = None
    for i, d in enumerate(days):
        y, w, _ = date_cls.fromisoformat(d).isocalendar()
        week = (y, w)
        is_last_of_week = (i + 1 >= len(days)) or (
            date_cls.fromisoformat(days[i + 1]).isocalendar()[:2] != week)
        if is_last_of_week and week != last_week:
            last_week = week
            if i + 1 < len(days):
                caps[days[i + 1]] = tier_cap(breadth[d], tiers)
    return caps


def cap_fn_from_map(cap_map: Mapping[str, float]) -> Callable[[str], float]:
    """稀疏生效日表 → 前向填充的 cap_fn（portfolio.PortfolioConfig 用）。

    首个生效日之前 → 1.0（宽度样本起点晚，不追溯缩放历史段）。
    """
    starts = sorted(cap_map)

    def cap_fn(day: str) -> float:
        if not starts or day < starts[0]:
            return 1.0
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= day:
                lo = mid
            else:
                hi = mid - 1
        return cap_map[starts[lo]]

    return cap_fn


# ---------------------------------------------------------------- 去重

def dedup_signals(
    trades: list[dict],
    *,
    priority: Sequence[str] = MODULE_PRIORITY,
) -> tuple[list[dict], dict]:
    """任务一规则：同标的在场唯一 + 同日模块优先级 + 完全重复去一。

    输入 trades 需含 symbol/signal_date/entry_date/exit_date/r_net，
    可选 module（无 module 视为同组，规则 2 退化为先到先得）。
    返回 (保留信号, 统计)；保留信号按 (signal_date, symbol) 稳定排序。
    """
    stats = {"input": len(trades), "dup_exact": 0, "same_day_module": 0,
             "overlap_open": 0}
    # 规则 3：完全重复只留一笔
    seen_exact: set[tuple[str, str, str]] = set()
    stage1: list[dict] = []
    for t in trades:
        key = (str(t["symbol"]), str(t.get("signal_date") or "")[:10],
               str(t.get("entry_date") or "")[:10])
        if key in seen_exact:
            stats["dup_exact"] += 1
            continue
        seen_exact.add(key)
        stage1.append(t)

    # 规则 2：同标的同日（signal_date）多模块按优先级取一
    by_key: dict[tuple[str, str], list[dict]] = {}
    for t in stage1:
        by_key.setdefault((str(t["symbol"]), str(t.get("signal_date"))[:10]),
                          []).append(t)
    stage2: list[dict] = []
    for (_, _), group in sorted(by_key.items()):
        if len(group) == 1:
            stage2.append(group[0])
            continue
        group.sort(key=lambda t: (priority.index(t.get("module", "?"))
                                  if t.get("module", "?") in priority
                                  else len(priority), str(t.get("seq", 0))))
        stage2.append(group[0])
        stats["same_day_module"] += len(group) - 1

    # 规则 1：同标的在场唯一（按 signal_date 顺序推进，生命周期不重叠）
    stage2.sort(key=lambda t: (str(t.get("signal_date"))[:10],
                               str(t["symbol"])))
    last_exit: dict[str, str] = {}
    kept: list[dict] = []
    for t in stage2:
        sym = str(t["symbol"])
        sig_d = str(t.get("signal_date"))[:10]
        exit_d = str(t.get("exit_date"))[:10] if t.get("exit_date") else "9999"
        if sym in last_exit and sig_d <= last_exit[sym]:
            stats["overlap_open"] += 1
            continue
        kept.append(t)
        if exit_d > last_exit.get(sym, ""):
            last_exit[sym] = exit_d
    stats["kept"] = len(kept)
    stats["dropped_total"] = stats["input"] - len(kept)
    kept.sort(key=lambda t: (str(t.get("signal_date"))[:10], str(t["symbol"])))
    return kept, stats


def reconcile(trades: list[dict], label: str) -> dict:
    """去重前后 R 对账（全期 / 分年 / 2026）。"""
    kept, st = dedup_signals(trades)

    def cum(ts):
        return round(sum(float(t["r_net"]) for t in ts
                         if t.get("r_net") is not None), 3)

    def by_year(ts):
        agg: dict[str, list[dict]] = {}
        for t in ts:
            if t.get("r_net") is not None:
                agg.setdefault(str(t.get("signal_date", ""))[:4], []).append(t)
        return {y: {"n": len(v), "cumR": round(
            sum(float(t["r_net"]) for t in v), 3)} for y, v in sorted(agg.items())}

    before_all, after_all = cum(trades), cum(kept)
    y26_b = [t for t in trades if str(t.get("signal_date", ""))[:4] == "2026"
             and t.get("r_net") is not None]
    y26_a = [t for t in kept if str(t.get("signal_date", ""))[:4] == "2026"
             and t.get("r_net") is not None]
    return {
        "label": label,
        "before": {"n": len(trades), "cumR": before_all, "by_year": by_year(trades)},
        "after": {"n": len(kept), "cumR": after_all, "by_year": by_year(kept)},
        "water_pct": round((before_all - after_all) / abs(before_all) * 100, 1)
        if before_all else None,
        "r2026_before": cum(y26_b), "r2026_after": cum(y26_a),
        "dedup_stats": st,
    }


# ---------------------------------------------------------------- 板块过滤

def filter_by_sector(
    trades: list[dict],
    sector_pass: Callable[[str, str], bool],
) -> tuple[list[dict], dict]:
    """板块选股层：信号进入队列前的板块入选判定（三层串联用）。

    ``sector_pass(signal_date, symbol) -> bool`` 为外部纯函数（板块时钟/
    RS 截面在信号日的入选判定，无未来函数），False 的信号剔除并计数。
    未映射标的是否放行由调用方的 sector_pass 决定（本函数不持有映射表）。
    """
    kept: list[dict] = []
    stats = {"input": len(trades), "dropped_sector": 0,
             "dropped_by_symbol": {}}
    for t in trades:
        if sector_pass(str(t.get("signal_date"))[:10], str(t["symbol"])):
            kept.append(t)
        else:
            stats["dropped_sector"] += 1
            sym = str(t["symbol"])
            stats["dropped_by_symbol"][sym] = stats["dropped_by_symbol"].get(sym, 0) + 1
    stats["kept"] = len(kept)
    return kept, stats


__all__ = [
    "TIERS_V1",
    "TIERS_V2",
    "MODULE_PRIORITY",
    "tier_cap",
    "load_b200_series",
    "position_cap_map",
    "cap_fn_from_map",
    "dedup_signals",
    "reconcile",
    "filter_by_sector",
]
