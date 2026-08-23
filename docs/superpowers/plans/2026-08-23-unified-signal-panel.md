# 今日自选信号：统一买/卖点提醒面板 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 看盘主页（`/`）中栏顶部一条「今日自选信号」横幅，统一展示全自选买/卖信号（分级），点击行跳转标的并打开分析；11:35 / 14:45 / 15:05 三个时刻自动扫描落库。

**Architecture:** 卖点侧新增纯提取函数 `extract_sell_signals`（只汇总既有确定性输出，不做新判定）；统一扫描 `run_signal_scan` 复用 `run_opportunity_scan`（买点）+ 提取函数（卖点），买点写既有表 `daily_opportunity_scan`，卖点写新表 `signal_alerts`；新路由 `/api/signals/today` 合并两表；前端新组件 `TodaySignalBanner` 挂 WorkspacePage 中栏顶部。

**Tech Stack:** Python 3.11 + FastAPI + SQLite（WAL）；React 18 + Vite + TanStack Query；launchd 调度。

**设计文档:** `docs/superpowers/specs/2026-08-23-unified-signal-panel-design.md`

## Global Constraints（每个任务隐含遵守）

- **UI 只改 `web/`**：`src/lei_signal/ui/`（Streamlit）冻结目录零改动。
- **判定权在 Python 规则层**：卖点提取只读 `result.frame / events / structures / history`，数值取不到就留空，绝不推算，不发明第五种口径。
- **文案红线**：`exit_proxy` 必须标 `research_proxy`（研究代理）；顶部构造确认 / 关键性波动必须带「预警，不必然反向」限定语；数据失败显式 `DATA_UNAVAILABLE`，不静默为「无信号」。
- **工作区有 552 个无关未提交文件**：所有 `git add` 必须用精确路径，严禁 `git add -A` / `git add .`。
- pytest 从项目根目录跑：`cd ~/Desktop/lei-signal-lab && python3 -m pytest -q`。
- 前端构建验证：`cd web && npm run build`。
- recency 窗口统一 3 根 K 线（与买点侧 `RECENCY_BUSINESS_DAYS = 3` 一致）。

---

### Task 1: 卖点提取纯函数 `extract_sell_signals`

**Files:**
- Create: `src/lei_signal/api/sell_signals.py`
- Test: `tests/unit/test_sell_signals.py`

**Interfaces:**
- Consumes: 任何具备 `frame / events / structures / history` 属性的对象（duck typing，同 `tests/unit/test_macd_events.py` 的 SimpleNamespace 模式）。`structures` 元素有 `side / status / invalidated_date / invalidated_reason / c_price / confirmed_date / neckline`；`events` 元素有 `rule_id / available_date / evidence / reason_cn`；`history` 元素有 `day / color`。
- Produces: `SellSignal`（frozen dataclass：`kind / tier / kind_cn / title / reason_cn / is_new / key_prices / provenance / available_date`）与 `extract_sell_signals(result, *, recency_bars=3) -> list[SellSignal]`。kind 枚举：`structure_invalidated / exit_proxy / top_structure_confirmed / key_wave_black / color_black`；tier 枚举：`hard / warn / soft`。常量 `TIER_HARD / TIER_WARN / TIER_SOFT`、`EXIT_RULE_ID = "exit_ema20_costbasis"`、`KEY_WAVE_RULE_ID = "key_wave_black"`（Task 3、4 依赖）。

- [ ] **Step 1: 写失败测试**

```python
"""extract_sell_signals 四档口径门禁（纯提取，不做新判定）。

口径（docs/superpowers/specs/2026-08-23-unified-signal-panel-design.md §2）：
  hard  structure_invalidated    底部结构失效（trading-spec §2.3/§7）
  hard  exit_proxy               收盘同破 EMA20+20日抵扣价（A6①，research_proxy）
  warn  top_structure_confirmed  顶部构造确认（§7.4，预警不必然反向）
  warn  key_wave_black           反向关键性波动（§2.2，预警不必然反向）
  soft  color_black              三色转黑（生命周期状态机）
顶部结构失效（=创新高解除预警）是偏多事实，不得进卖点面板。
"""
from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from lei_signal.api.sell_signals import extract_sell_signals


def _frame(n: int = 3) -> pd.DataFrame:
    # bdate_range("2026-08-19", 3) -> 08-19(三) 08-20(四) 08-21(五)，today=08-21
    return pd.DataFrame(
        {"close": [10.0] * n},
        index=pd.bdate_range("2026-08-19", periods=n),
    )


def _bottom_invalidated(day, reason="跌破 C 点"):
    return SimpleNamespace(
        side="bottom", status="invalidated", invalidated_date=day,
        invalidated_reason=reason, c_price=9.5, confirmed_date=None, neckline=None,
    )


def _exit_event(day):
    return SimpleNamespace(
        rule_id="exit_ema20_costbasis", available_date=day,
        reason_cn="抵扣价退出触发：收盘同时跌破 EMA20 与 20 日抵扣价",
        evidence={"ema20": 10.5, "close_lag20": 10.8, "close": 10.1},
    )


def test_structure_invalidated_today_is_hard_and_new() -> None:
    today = _frame().index[-1].date()
    result = SimpleNamespace(
        frame=_frame(), events=[], structures=[_bottom_invalidated(today)], history=[],
    )
    sigs = extract_sell_signals(result)
    assert len(sigs) == 1
    s = sigs[0]
    assert s.kind == "structure_invalidated" and s.tier == "hard"
    assert s.is_new is True
    assert s.key_prices == {"invalidation_c": 9.5}
    assert "结构" in s.title


def test_structure_invalidated_three_bars_ago_is_continuing() -> None:
    # 3 根窗口的最早一天（仍在窗口内）但不是今天 -> is_new=False
    frame = _frame()
    oldest = frame.index[0].date()
    result = SimpleNamespace(
        frame=frame, events=[], structures=[_bottom_invalidated(oldest)], history=[],
    )
    sigs = extract_sell_signals(result)
    assert len(sigs) == 1 and sigs[0].is_new is False


def test_old_invalidation_outside_window_ignored() -> None:
    frame = _frame()
    old_day = pd.Timestamp("2026-07-01").date()
    result = SimpleNamespace(
        frame=frame, events=[], structures=[_bottom_invalidated(old_day)], history=[],
    )
    assert extract_sell_signals(result) == []


def test_top_side_invalidation_not_a_sell() -> None:
    today = _frame().index[-1].date()
    top_dead = SimpleNamespace(
        side="top", status="invalidated", invalidated_date=today,
        invalidated_reason="创新高解除", c_price=None, confirmed_date=None, neckline=None,
    )
    result = SimpleNamespace(frame=_frame(), events=[], structures=[top_dead], history=[])
    assert extract_sell_signals(result) == []


def test_exit_proxy_is_hard_research_proxy_with_prices() -> None:
    frame = _frame()
    today = frame.index[-1].date()
    result = SimpleNamespace(frame=frame, events=[_exit_event(today)], structures=[], history=[])
    sigs = extract_sell_signals(result)
    assert len(sigs) == 1
    s = sigs[0]
    assert s.kind == "exit_proxy" and s.tier == "hard" and s.is_new is True
    assert s.provenance == "research_proxy"
    assert s.key_prices == {"ema20": 10.5, "close_lag20": 10.8, "close": 10.1}


def test_top_structure_confirmed_is_warn_with_disclaimer() -> None:
    frame = _frame()
    today = frame.index[-1].date()
    top = SimpleNamespace(
        side="top", status="confirmed", confirmed_date=today, invalidated_date=None,
        invalidated_reason=None, c_price=None, neckline=11.2,
    )
    result = SimpleNamespace(frame=frame, events=[], structures=[top], history=[])
    sigs = extract_sell_signals(result)
    assert len(sigs) == 1
    s = sigs[0]
    assert s.kind == "top_structure_confirmed" and s.tier == "warn"
    assert "预警" in s.reason_cn and "不必然" in s.reason_cn
    assert s.key_prices == {"neckline": 11.2}


def test_key_wave_black_is_warn_with_disclaimer() -> None:
    frame = _frame()
    today = frame.index[-1].date()
    ev = SimpleNamespace(
        rule_id="key_wave_black", available_date=today, reason_cn="空头趋势中的向上关键波动",
        evidence={},
    )
    result = SimpleNamespace(frame=frame, events=[ev], structures=[], history=[])
    sigs = extract_sell_signals(result)
    assert len(sigs) == 1
    s = sigs[0]
    assert s.kind == "key_wave_black" and s.tier == "warn"
    assert "预警" in s.reason_cn and "不必然" in s.reason_cn


def test_color_black_transition_is_soft() -> None:
    frame = _frame()
    d1, d2 = frame.index[-2].date(), frame.index[-1].date()
    history = [
        SimpleNamespace(day=d1, color="gray"),
        SimpleNamespace(day=d2, color="black"),
    ]
    result = SimpleNamespace(frame=frame, events=[], structures=[], history=history)
    sigs = extract_sell_signals(result)
    assert len(sigs) == 1
    s = sigs[0]
    assert s.kind == "color_black" and s.tier == "soft" and s.is_new is True
    assert "灰转黑" in s.reason_cn


def test_black_to_black_is_not_a_transition() -> None:
    frame = _frame()
    d1, d2 = frame.index[-2].date(), frame.index[-1].date()
    history = [
        SimpleNamespace(day=d1, color="black"),
        SimpleNamespace(day=d2, color="black"),
    ]
    result = SimpleNamespace(frame=frame, events=[], structures=[], history=history)
    assert extract_sell_signals(result) == []


def test_empty_frame_returns_empty() -> None:
    result = SimpleNamespace(frame=pd.DataFrame(), events=[], structures=[], history=[])
    assert extract_sell_signals(result) == []
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest tests/unit/test_sell_signals.py -q`
Expected: FAIL，`ModuleNotFoundError: No module named 'lei_signal.api.sell_signals'`

- [ ] **Step 3: 写实现**

```python
"""全自选卖点信号提取（纯函数，不做新判定）。

四档口径（docs/superpowers/specs/2026-08-23-unified-signal-panel-design.md §2）：
  hard  structure_invalidated     底部结构失效（trading-spec §2.3 / §7）
  hard  exit_proxy                收盘同破 EMA20 + 20 日抵扣价（trading-spec A6①，research_proxy）
  warn  top_structure_confirmed   顶部构造确认（trading-spec §7.4，预警不必然反向）
  warn  key_wave_black            反向关键性波动（trading-spec §2.2，预警不必然反向）
  soft  color_black               三色转黑（Round 3 生命周期状态机）

只读 result.frame / result.events / result.structures / result.history 四个字段，
数值与文案全部来自既有确定性输出，取不到就留空，绝不推算。
顶部结构失效（=创新高解除预警）是偏多事实，不进卖点面板。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

EXIT_RULE_ID = "exit_ema20_costbasis"
KEY_WAVE_RULE_ID = "key_wave_black"

#: recency 窗口：最近 N 根 K 线内触发的卖点才进面板（与买点侧 3 交易日一致）
RECENCY_BARS = 3

TIER_HARD = "hard"
TIER_WARN = "warn"
TIER_SOFT = "soft"

_COLOR_CN = {"green": "绿", "gray": "灰", "black": "黑"}


def _color_name(color: Any) -> str:
    raw = getattr(color, "value", color)
    return _COLOR_CN.get(str(raw), str(raw))


@dataclass(frozen=True, slots=True)
class SellSignal:
    """一条卖点提醒（提取结果，不含任何新判定）。"""

    kind: str
    tier: str
    kind_cn: str
    title: str
    reason_cn: str
    is_new: bool
    key_prices: dict[str, float] = field(default_factory=dict)
    provenance: str = "system"
    available_date: str = ""


def _recent_dates(frame: Any, recency_bars: int) -> tuple[set[date], date]:
    """最近 N 根 K 线的日期集合与当前（最后一根）日期。"""
    dates = [ts.date() for ts in frame.index[-recency_bars:]]
    return set(dates), dates[-1]


def extract_sell_signals(result: Any, *, recency_bars: int = RECENCY_BARS) -> list[SellSignal]:
    """从既有分析结果提取四档卖点信号；无 frame 或无命中返回空列表。"""
    frame = getattr(result, "frame", None)
    if frame is None or len(frame.index) == 0:
        return []
    window, today = _recent_dates(frame, recency_bars)
    events = list(getattr(result, "events", []) or [])
    structures = list(getattr(result, "structures", []) or [])
    signals: list[SellSignal] = []

    # S1 结构失效：只收底部结构（顶部结构失效 = 创新高解除预警，偏多，不进卖点）
    dead_bottoms = [
        s for s in structures
        if getattr(s, "side", "") == "bottom"
        and str(getattr(s, "status", "")) == "invalidated"
        and getattr(s, "invalidated_date", None) in window
    ]
    if dead_bottoms:
        latest = max(s.invalidated_date for s in dead_bottoms)
        reason = "；".join(
            r for r in (getattr(s, "invalidated_reason", None) for s in dead_bottoms) if r
        )
        c_prices = [
            float(s.c_price) for s in dead_bottoms
            if getattr(s, "c_price", None) is not None
        ]
        signals.append(SellSignal(
            kind="structure_invalidated", tier=TIER_HARD, kind_cn="结构失效",
            title=f"{len(dead_bottoms)} 个底部结构失效",
            reason_cn=reason or "底部结构被破坏（进出同一逻辑：什么逻辑进场就什么逻辑退出）",
            is_new=latest == today,
            key_prices={"invalidation_c": c_prices[-1]} if c_prices else {},
            available_date=latest.isoformat(),
        ))

    # S2 退出代理（research_proxy）：收盘同破 EMA20 与 20 日抵扣价的上升沿事件
    exit_events = [
        e for e in events
        if getattr(e, "rule_id", "") == EXIT_RULE_ID
        and getattr(e, "available_date", None) in window
    ]
    if exit_events:
        ev = max(exit_events, key=lambda e: e.available_date)
        evd = dict(getattr(ev, "evidence", {}) or {})
        signals.append(SellSignal(
            kind="exit_proxy", tier=TIER_HARD, kind_cn="退出代理",
            title="收盘同破 EMA20 与 20 日抵扣价",
            reason_cn=f"{getattr(ev, 'reason_cn', '')}（研究代理）".strip(),
            is_new=ev.available_date == today,
            key_prices={
                k: float(evd[k]) for k in ("ema20", "close_lag20", "close") if k in evd
            },
            provenance="research_proxy",
            available_date=ev.available_date.isoformat(),
        ))

    # S3a 顶部构造确认（预警路牌）
    tops_confirmed = [
        s for s in structures
        if getattr(s, "side", "") == "top"
        and getattr(s, "confirmed_date", None) in window
    ]
    if tops_confirmed:
        latest = max(s.confirmed_date for s in tops_confirmed)
        necklines = [
            float(s.neckline) for s in tops_confirmed
            if getattr(s, "neckline", None) is not None
        ]
        signals.append(SellSignal(
            kind="top_structure_confirmed", tier=TIER_WARN, kind_cn="顶部路牌",
            title=f"{len(tops_confirmed)} 个顶部构造确认",
            reason_cn="顶部构造确认——预警路牌，不必然等于反向（trading-spec §7.4）",
            is_new=latest == today,
            key_prices={"neckline": necklines[-1]} if necklines else {},
            available_date=latest.isoformat(),
        ))

    # S3b 反向关键性波动（预警路牌）
    key_waves = [
        e for e in events
        if getattr(e, "rule_id", "") == KEY_WAVE_RULE_ID
        and getattr(e, "available_date", None) in window
    ]
    if key_waves:
        ev = max(key_waves, key=lambda e: e.available_date)
        signals.append(SellSignal(
            kind="key_wave_black", tier=TIER_WARN, kind_cn="顶部路牌",
            title="反向关键性波动",
            reason_cn=f"{getattr(ev, 'reason_cn', '')}——预警路牌，不必然等于反向",
            is_new=ev.available_date == today,
            available_date=ev.available_date.isoformat(),
        ))

    # S4 颜色转黑：绿/灰 → 黑 的转换日落在窗口内
    history = list(getattr(result, "history", []) or [])
    if len(history) >= 2:
        cur, prev = history[-1], history[-2]
        cur_black = str(getattr(cur, "color", "")) == "black"
        prev_not_black = str(getattr(prev, "color", "")) != "black"
        if cur_black and prev_not_black and getattr(cur, "day", None) in window:
            signals.append(SellSignal(
                kind="color_black", tier=TIER_SOFT, kind_cn="颜色转黑",
                title="LEI 颜色转黑",
                reason_cn=f"三色状态由{_color_name(prev.color)}转黑（长趋势转弱提醒）",
                is_new=cur.day == today,
                available_date=cur.day.isoformat(),
            ))

    return signals


__all__ = [
    "EXIT_RULE_ID",
    "KEY_WAVE_RULE_ID",
    "RECENCY_BARS",
    "SellSignal",
    "TIER_HARD",
    "TIER_SOFT",
    "TIER_WARN",
    "extract_sell_signals",
]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest tests/unit/test_sell_signals.py -q`
Expected: `10 passed`

- [ ] **Step 5: 提交**

```bash
cd ~/Desktop/lei-signal-lab
git add src/lei_signal/api/sell_signals.py tests/unit/test_sell_signals.py
git commit -m "feat(signals): 卖点四档口径提取纯函数 extract_sell_signals"
```

---

### Task 2: migration 016 `signal_alerts` 表 + CRUD

**Files:**
- Modify: `src/lei_signal/storage/sqlite_store.py`（`MIGRATIONS` 元组末尾追加 016 条目，位置在 `)` 收尾前，即 `015_daily_opportunity_scan` 条目之后）
- Create: `src/lei_signal/api/signal_alerts_store.py`
- Test: `tests/unit/test_signal_alerts_store.py`

**Interfaces:**
- Consumes: `lei_signal.storage.sqlite_store.connect`（自动应用迁移）。
- Produces（Task 3、4、5 依赖）：
  - `SignalAlertRow`（frozen dataclass：`scan_date / symbol / display_name / side / tier / kind / kind_cn / title / reason_cn / is_new / key_prices / provenance / available_date / error / generated_at`）
  - `upsert_signal_alerts(conn, scan_date: str, as_of: str, rows: list[SignalAlertRow]) -> int`（当日整体重写 + 写一条 `side='meta', kind='as_of'` 元信息行）
  - `list_signal_alerts(conn, scan_date: str, side: str = "sell") -> list[SignalAlertRow]`
  - `get_scan_as_of(conn, scan_date: str) -> str | None`
  - `count_sell_alerts(conn, scan_date: str, tiers=("hard", "warn")) -> int`（红点用）
  - 常量 `SIDE_SELL = "sell"`、`SIDE_UNAVAILABLE = "unavailable"`、`SIDE_META = "meta"`

- [ ] **Step 1: 写失败测试**

```python
"""signal_alerts 表 CRUD（migration 016）门禁。

当日重扫 = 整体重写（先 DELETE 当日再 INSERT，与 daily_opportunity_scan 同语义）；
as_of 通过 meta 行持久化，读 API 据此判断「今日是否扫过」与盘中/收盘口径。
"""
from __future__ import annotations

import sqlite3

from lei_signal.api.signal_alerts_store import (
    SIDE_SELL,
    SIDE_UNAVAILABLE,
    SignalAlertRow,
    count_sell_alerts,
    get_scan_as_of,
    list_signal_alerts,
    upsert_signal_alerts,
)
from lei_signal.storage.sqlite_store import connect


def _conn() -> sqlite3.Connection:
    return connect(":memory:")


def _sell_row(**kw) -> SignalAlertRow:
    base = dict(
        scan_date="2026-08-21", symbol="600519.SS", display_name="贵州茅台",
        side=SIDE_SELL, tier="hard", kind="exit_proxy", kind_cn="退出代理",
        title="收盘同破 EMA20 与 20 日抵扣价", reason_cn="x（研究代理）",
        is_new=True, key_prices={"ema20": 10.5}, provenance="research_proxy",
        available_date="2026-08-21",
    )
    base.update(kw)
    return SignalAlertRow(**base)


def test_upsert_writes_rows_and_as_of_meta() -> None:
    conn = _conn()
    n = upsert_signal_alerts(conn, "2026-08-21", "intraday", [_sell_row()])
    assert n == 2  # 1 条信号 + 1 条 meta
    assert get_scan_as_of(conn, "2026-08-21") == "intraday"
    rows = list_signal_alerts(conn, "2026-08-21", side=SIDE_SELL)
    assert len(rows) == 1
    assert rows[0].key_prices == {"ema20": 10.5}
    assert rows[0].is_new is True


def test_rescan_rewrites_day_and_updates_as_of() -> None:
    conn = _conn()
    upsert_signal_alerts(conn, "2026-08-21", "intraday", [_sell_row()])
    upsert_signal_alerts(conn, "2026-08-21", "close", [])  # 收盘版无卖点信号
    assert get_scan_as_of(conn, "2026-08-21") == "close"
    assert list_signal_alerts(conn, "2026-08-21", side=SIDE_SELL) == []


def test_meta_and_unavailable_not_in_sell_list() -> None:
    conn = _conn()
    unavailable = SignalAlertRow(
        scan_date="2026-08-21", symbol="bad.SS", display_name="bad.SS",
        side=SIDE_UNAVAILABLE, tier="hard", kind="data_unavailable",
        title="数据不可用", error="DATA_UNAVAILABLE: 行情获取失败",
    )
    upsert_signal_alerts(conn, "2026-08-21", "close", [unavailable])
    assert list_signal_alerts(conn, "2026-08-21", side=SIDE_SELL) == []
    unavailable_rows = list_signal_alerts(conn, "2026-08-21", side=SIDE_UNAVAILABLE)
    assert len(unavailable_rows) == 1
    assert unavailable_rows[0].error == "DATA_UNAVAILABLE: 行情获取失败"


def test_count_sell_alerts_hard_and_warn_only() -> None:
    conn = _conn()
    upsert_signal_alerts(conn, "2026-08-21", "close", [
        _sell_row(),
        _sell_row(symbol="000001.SZ", tier="warn", kind="key_wave_black"),
        _sell_row(symbol="300750.SZ", tier="soft", kind="color_black"),
    ])
    assert count_sell_alerts(conn, "2026-08-21") == 2  # hard + warn，soft 不计
    assert count_sell_alerts(conn, "2026-08-21", tiers=("hard",)) == 1


def test_no_scan_today_returns_none_and_zero() -> None:
    conn = _conn()
    assert get_scan_as_of(conn, "2026-08-21") is None
    assert count_sell_alerts(conn, "2026-08-21") == 0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest tests/unit/test_signal_alerts_store.py -q`
Expected: FAIL，`ModuleNotFoundError: No module named 'lei_signal.api.signal_alerts_store'`

- [ ] **Step 3a: 加 migration 016**

在 `src/lei_signal/storage/sqlite_store.py` 的 `MIGRATIONS` 元组中、`015_daily_opportunity_scan` 条目（约 `:567-596`）之后、收尾 `)` 之前插入：

```python
    (
        16,
        "016_signal_alerts",
        """
        -- 今日自选信号卖点表 (2026-08-23): 看盘主页「今日自选信号」横幅的数据源.
        -- 卖点行来自 extract_sell_signals (纯提取, 不做新判定);
        -- 买点行继续写 daily_opportunity_scan (既有表), 读 API 合并两表.
        -- 当日重扫 = 先 DELETE 当日再 INSERT (与 daily_opportunity_scan 同语义).
        -- side='meta' 的 as_of 行记录本次扫描口径 (intraday | close), 是"今日是否扫过"的唯一判据.
        CREATE TABLE IF NOT EXISTS signal_alerts (
            scan_date      TEXT NOT NULL,        -- YYYY-MM-DD (UTC date)
            symbol         TEXT NOT NULL,
            display_name   TEXT NOT NULL DEFAULT '',
            side           TEXT NOT NULL,        -- sell | unavailable | meta
            tier           TEXT NOT NULL,        -- hard | warn | soft | meta
            kind           TEXT NOT NULL,        -- structure_invalidated | exit_proxy | top_structure_confirmed | key_wave_black | color_black | data_unavailable | as_of
            kind_cn        TEXT NOT NULL DEFAULT '',
            title          TEXT NOT NULL DEFAULT '',
            reason_cn      TEXT NOT NULL DEFAULT '',
            is_new         INTEGER NOT NULL DEFAULT 0,
            key_prices     TEXT NOT NULL DEFAULT '{}',  -- JSON object {name: price}
            provenance     TEXT NOT NULL DEFAULT 'system',
            available_date TEXT NOT NULL DEFAULT '',
            error          TEXT,
            generated_at   TEXT NOT NULL,
            PRIMARY KEY (scan_date, symbol, side, kind)
        );
        CREATE INDEX IF NOT EXISTS idx_signal_alerts_date_side_tier
            ON signal_alerts(scan_date, side, tier);
        """,
    ),
```

- [ ] **Step 3b: 写 CRUD 模块**

```python
"""signal_alerts 表 CRUD (migration 016)。

设计语义（与 opportunity_scan.py 同模式）：
  launchd 11:35 / 14:45 / 15:05 扫全自选 -> upsert_signal_alerts 整体重写当日
  -> 看盘主页横幅 / 顶栏红点读表。不现场跑 scan（5-10s，轮询不可接受）。

as_of 通过一条 side='meta', kind='as_of' 的元信息行持久化（title 存口径值），
是「今日是否扫过」与「盘中临时 / 收盘」的唯一判据。
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime

SIDE_SELL = "sell"
SIDE_UNAVAILABLE = "unavailable"
SIDE_META = "meta"

_TIER_RANK = {"hard": 0, "warn": 1, "soft": 2}


@dataclass(frozen=True, slots=True)
class SignalAlertRow:
    """signal_alerts 一行（key_prices 已反序列化为 dict）。"""

    scan_date: str
    symbol: str
    display_name: str
    side: str
    tier: str
    kind: str
    kind_cn: str = ""
    title: str = ""
    reason_cn: str = ""
    is_new: bool = False
    key_prices: dict[str, float] = field(default_factory=dict)
    provenance: str = "system"
    available_date: str = ""
    error: str | None = None
    generated_at: str = ""


def _insert(conn: sqlite3.Connection, row: SignalAlertRow, generated_at: str) -> None:
    conn.execute(
        """
        INSERT INTO signal_alerts (
            scan_date, symbol, display_name, side, tier, kind, kind_cn,
            title, reason_cn, is_new, key_prices, provenance, available_date,
            error, generated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row.scan_date, row.symbol, row.display_name, row.side, row.tier,
            row.kind, row.kind_cn, row.title, row.reason_cn,
            1 if row.is_new else 0,
            json.dumps(dict(row.key_prices), ensure_ascii=False),
            row.provenance, row.available_date, row.error,
            row.generated_at or generated_at,
        ),
    )


def upsert_signal_alerts(
    conn: sqlite3.Connection,
    scan_date: str,
    as_of: str,
    rows: list[SignalAlertRow],
) -> int:
    """当日整体重写（含 meta 行），返回写入行数（含 meta）。"""
    conn.execute("DELETE FROM signal_alerts WHERE scan_date = ?", (scan_date,))
    generated_at = datetime.now(UTC).isoformat()
    for row in rows:
        _insert(conn, row, generated_at)
    _insert(
        conn,
        SignalAlertRow(
            scan_date=scan_date, symbol="", display_name="", side=SIDE_META,
            tier="meta", kind="as_of", title=as_of, generated_at=generated_at,
        ),
        generated_at,
    )
    conn.commit()
    return len(rows) + 1


def _row_to_signal(row: sqlite3.Row) -> SignalAlertRow:
    try:
        prices: dict[str, float] = json.loads(row["key_prices"] or "{}")
    except (json.JSONDecodeError, TypeError):
        prices = {}
    return SignalAlertRow(
        scan_date=row["scan_date"], symbol=row["symbol"],
        display_name=row["display_name"], side=row["side"], tier=row["tier"],
        kind=row["kind"], kind_cn=row["kind_cn"], title=row["title"],
        reason_cn=row["reason_cn"], is_new=bool(row["is_new"]),
        key_prices=prices, provenance=row["provenance"],
        available_date=row["available_date"], error=row["error"],
        generated_at=row["generated_at"],
    )


def list_signal_alerts(
    conn: sqlite3.Connection, scan_date: str, *, side: str = SIDE_SELL,
) -> list[SignalAlertRow]:
    """读当日指定 side 的行，按 tier 硬→软、新增优先、symbol 排序。"""
    rows = conn.execute(
        """
        SELECT * FROM signal_alerts
        WHERE scan_date = ? AND side = ?
        ORDER BY CASE tier
            WHEN 'hard' THEN 0
            WHEN 'warn' THEN 1
            WHEN 'soft' THEN 2
            ELSE 3
        END, is_new DESC, symbol
        """,
        (scan_date, side),
    ).fetchall()
    return [_row_to_signal(r) for r in rows]


def get_scan_as_of(conn: sqlite3.Connection, scan_date: str) -> str | None:
    """当日扫描口径（intraday | close）；未扫描返回 None。"""
    row = conn.execute(
        "SELECT title FROM signal_alerts WHERE scan_date = ? AND side = ? AND kind = 'as_of' LIMIT 1",
        (scan_date, SIDE_META),
    ).fetchone()
    return row["title"] if row else None


def count_sell_alerts(
    conn: sqlite3.Connection,
    scan_date: str,
    *,
    tiers: tuple[str, ...] = ("hard", "warn"),
) -> int:
    """当日卖点半数（红点用，默认只计 hard+warn，soft 不打扰）。"""
    placeholders = ",".join("?" for _ in tiers)
    row = conn.execute(
        f"SELECT COUNT(*) FROM signal_alerts WHERE scan_date = ? AND side = ? AND tier IN ({placeholders})",  # noqa: S608
        (scan_date, SIDE_SELL, *tiers),
    ).fetchone()
    return int(row[0]) if row else 0


__all__ = [
    "SIDE_META",
    "SIDE_SELL",
    "SIDE_UNAVAILABLE",
    "SignalAlertRow",
    "count_sell_alerts",
    "get_scan_as_of",
    "list_signal_alerts",
    "upsert_signal_alerts",
]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest tests/unit/test_signal_alerts_store.py -q`
Expected: `5 passed`

- [ ] **Step 5: 提交**

```bash
cd ~/Desktop/lei-signal-lab
git add src/lei_signal/storage/sqlite_store.py src/lei_signal/api/signal_alerts_store.py tests/unit/test_signal_alerts_store.py
git commit -m "feat(signals): signal_alerts 表 (migration 016) + CRUD"
```

---

### Task 3: 统一扫描 `run_signal_scan`

**Files:**
- Create: `src/lei_signal/api/signal_scan.py`
- Test: `tests/unit/test_signal_scan.py`

**Interfaces:**
- Consumes: Task 1 的 `extract_sell_signals`；Task 2 的 `SignalAlertRow / upsert_signal_alerts / SIDE_UNAVAILABLE`；既有 `run_opportunity_scan`（`routes/opportunities.py:523`）、`AnalysisService.get_many(symbols, refresh=)`、`AnalysisEntry`（`api/services.py`）、`upsert_scan_results`（`api/opportunity_scan.py`）。
- Produces（Task 4、5 依赖）：
  - `AS_OF_INTRADAY = "intraday"`、`AS_OF_CLOSE = "close"`
  - `run_signal_scan(service, db_path, *, symbols: list[str] | None = None, as_of: str = "close", refresh: bool = True, dry_run: bool = False) -> dict`，返回 `{"scan_date", "as_of", "scanned", "sell_rows", "unavailable", "generated_at"}`

**实现要点（写代码时遵守）：**
- 买点：直接调 `run_opportunity_scan(service, db_path, symbols=wanted, refresh=refresh, only_with_candidates=True)`，它内部 `get_many(refresh=True)` 刷新 TTL 缓存并写 `daily_opportunity_scan`——**不在此模块重复写买点表**。
- 卖点：紧接着 `service.get_many(wanted, refresh=False)` 纯读刚刷新的缓存（同进程同 service，不再抓网）。
- 失败标的（`entry is None or entry.result is None`）写 `side=SIDE_UNAVAILABLE` 行，`error` 原样透传（含 `DATA_UNAVAILABLE` 字样时不改写）。
- 自选为空时仍写 meta 行（as_of 落库，横幅显示「今日暂无信号」而非「尚未扫描」）。

- [ ] **Step 1: 写失败测试**

```python
"""run_signal_scan 统一扫描门禁：买点走既有链路，卖点从同缓存提取，失败显式落库。

build_review 被 monkeypatch 成恒返回 none-verdict（买点过滤掉），
单测聚焦：卖点行生成、unavailable 行生成、as_of meta 行、当日重写。
"""
from __future__ import annotations

from contextlib import closing
from datetime import UTC, datetime
from types import SimpleNamespace

import pandas as pd

from lei_signal.api.opportunity_scan import today_date
from lei_signal.api.services import AnalysisEntry
from lei_signal.api.signal_alerts_store import (
    SIDE_SELL,
    SIDE_UNAVAILABLE,
    get_scan_as_of,
    list_signal_alerts,
)
from lei_signal.api.signal_scan import AS_OF_INTRADAY, run_signal_scan
from lei_signal.storage.sqlite_store import connect


class _FakeService:
    def __init__(self, entries: dict[str, AnalysisEntry]):
        self._entries = entries
        self.get_many_calls: list[bool] = []

    def get_many(self, symbols, refresh=False):
        self.get_many_calls.append(refresh)
        return {s: self._entries[s] for s in symbols if s in self._entries}


def _entry(result=None, error=None) -> AnalysisEntry:
    return AnalysisEntry(result=result, error=error, fetched_at=datetime.now(UTC))


def _result_with_exit_event() -> SimpleNamespace:
    frame = pd.DataFrame(
        {"close": [10.0] * 3}, index=pd.bdate_range("2026-08-19", periods=3),
    )
    today = frame.index[-1].date()
    return SimpleNamespace(
        frame=frame,
        display_name="测试标的",
        events=[SimpleNamespace(
            rule_id="exit_ema20_costbasis", available_date=today,
            reason_cn="抵扣价退出触发", evidence={"ema20": 10.5, "close_lag20": 10.8, "close": 10.1},
        )],
        structures=[],
        history=[],
    )


def _none_review(monkeypatch, verdict="none"):
    review = SimpleNamespace(
        verdict=verdict, verdict_cn="", display_name="", has_active_plan=False,
        candidates=[], resonance_groups=[], watch_conditions=[], tradability=None,
    )
    monkeypatch.setattr(
        "lei_signal.api.routes.opportunities.build_review", lambda *a, **kw: review,
    )


def test_sell_and_unavailable_rows_persisted(monkeypatch, tmp_path) -> None:
    _none_review(monkeypatch)
    db = str(tmp_path / "lab.db")
    entries = {
        "600519.SS": _entry(result=_result_with_exit_event()),
        "bad.SS": _entry(error="DATA_UNAVAILABLE: 行情获取失败"),
    }
    service = _FakeService(entries)
    summary = run_signal_scan(service, db, symbols=list(entries), as_of=AS_OF_INTRADAY)

    assert summary["scanned"] == 2
    assert summary["sell_rows"] == 1
    assert summary["unavailable"] == 1
    with closing(connect(db)) as conn:
        assert get_scan_as_of(conn, today_date()) == AS_OF_INTRADAY
        sell = list_signal_alerts(conn, today_date(), side=SIDE_SELL)
        assert len(sell) == 1
        assert sell[0].symbol == "600519.SS"
        assert sell[0].kind == "exit_proxy" and sell[0].provenance == "research_proxy"
        unavailable = list_signal_alerts(conn, today_date(), side=SIDE_UNAVAILABLE)
        assert len(unavailable) == 1
        assert unavailable[0].symbol == "bad.SS"
        assert "DATA_UNAVAILABLE" in (unavailable[0].error or "")


def test_rescan_rewrites_same_day(monkeypatch, tmp_path) -> None:
    _none_review(monkeypatch)
    db = str(tmp_path / "lab.db")
    service = _FakeService({"600519.SS": _entry(result=_result_with_exit_event())})
    run_signal_scan(service, db, symbols=["600519.SS"], as_of=AS_OF_INTRADAY)
    # 第二轮换成无信号标的：当日卖点行必须被整体重写掉
    service2 = _FakeService({"600519.SS": _entry(result=SimpleNamespace(
        frame=pd.DataFrame({"close": [10.0] * 3}, index=pd.bdate_range("2026-08-19", periods=3)),
        display_name="测试标的", events=[], structures=[], history=[],
    ))})
    run_signal_scan(service2, db, symbols=["600519.SS"], as_of="close")
    with closing(connect(db)) as conn:
        assert list_signal_alerts(conn, today_date(), side=SIDE_SELL) == []
        assert get_scan_as_of(conn, today_date()) == "close"


def test_empty_watchlist_writes_meta_only(tmp_path) -> None:
    db = str(tmp_path / "lab.db")
    service = _FakeService({})
    summary = run_signal_scan(service, db, symbols=[], as_of="close")
    assert summary["scanned"] == 0
    with closing(connect(db)) as conn:
        assert get_scan_as_of(conn, today_date()) == "close"
        assert list_signal_alerts(conn, today_date(), side=SIDE_SELL) == []


def test_sell_uses_cached_entries_no_refetch(monkeypatch, tmp_path) -> None:
    """买点扫描刷新缓存后，卖点提取 refresh=False 复用缓存，不再二次抓网。"""
    _none_review(monkeypatch)
    db = str(tmp_path / "lab.db")
    service = _FakeService({"600519.SS": _entry(result=_result_with_exit_event())})
    run_signal_scan(service, db, symbols=["600519.SS"])
    assert service.get_many_calls == [True, False]  # run_opportunity_scan 一次 True，卖点一次 False
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest tests/unit/test_signal_scan.py -q`
Expected: FAIL，`ModuleNotFoundError: No module named 'lei_signal.api.signal_scan'`

- [ ] **Step 3: 写实现**

```python
"""统一信号扫描：买点（既有 verdict）+ 卖点（四档提取）一次落库。

买点复用 routes/opportunities.run_opportunity_scan（它写 daily_opportunity_scan）；
卖点紧接着用 refresh=False 读同一份 TTL 缓存做纯提取，写 signal_alerts。
数据不可用的标的显式写 unavailable 行，不静默为「无信号」。
"""
from __future__ import annotations

from contextlib import closing
from datetime import UTC, datetime
from typing import Any

from lei_signal.api.opportunity_scan import today_date
from lei_signal.api.routes.opportunities import run_opportunity_scan
from lei_signal.api.sell_signals import extract_sell_signals
from lei_signal.api.signal_alerts_store import (
    SIDE_SELL,
    SIDE_UNAVAILABLE,
    SignalAlertRow,
    upsert_signal_alerts,
)
from lei_signal.storage.sqlite_store import connect

AS_OF_INTRADAY = "intraday"
AS_OF_CLOSE = "close"


def run_signal_scan(
    service: Any,
    db_path: str,
    *,
    symbols: list[str] | None = None,
    as_of: str = AS_OF_CLOSE,
    refresh: bool = True,
    dry_run: bool = False,
) -> dict:
    """扫全自选（或指定 symbols）：买点 + 卖点 + 数据不可用，整体重写当日。"""
    if symbols:
        wanted = list(symbols)
    else:
        from lei_signal.api.watchlist import list_watchlist  # noqa: PLC0415

        with closing(connect(db_path)) as conn:
            wanted = [item.symbol for item in list_watchlist(conn)]
    scan_date = today_date()

    rows: list[SignalAlertRow] = []
    if wanted:
        run_opportunity_scan(
            service, db_path, symbols=wanted, refresh=refresh, only_with_candidates=True,
        )
        # 买点扫描刚刷新过 TTL 缓存，这里 refresh=False 纯读缓存，不再抓网
        entries = service.get_many(wanted, refresh=False)
        for symbol in wanted:
            entry = entries.get(symbol)
            if entry is None or entry.result is None:
                rows.append(SignalAlertRow(
                    scan_date=scan_date, symbol=symbol, display_name=symbol,
                    side=SIDE_UNAVAILABLE, tier="hard", kind="data_unavailable",
                    title="数据不可用",
                    error=(entry.error if entry else "分析不可用"),
                ))
                continue
            for sig in extract_sell_signals(entry.result):
                rows.append(SignalAlertRow(
                    scan_date=scan_date, symbol=symbol,
                    display_name=getattr(entry.result, "display_name", "") or symbol,
                    side=SIDE_SELL, tier=sig.tier, kind=sig.kind,
                    kind_cn=sig.kind_cn, title=sig.title, reason_cn=sig.reason_cn,
                    is_new=sig.is_new, key_prices=dict(sig.key_prices),
                    provenance=sig.provenance, available_date=sig.available_date,
                ))

    if not dry_run:
        with closing(connect(db_path)) as conn:
            upsert_signal_alerts(conn, scan_date, as_of, rows)

    return {
        "scan_date": scan_date,
        "as_of": as_of,
        "scanned": len(wanted),
        "sell_rows": sum(1 for r in rows if r.side == SIDE_SELL),
        "unavailable": sum(1 for r in rows if r.side == SIDE_UNAVAILABLE),
        "generated_at": datetime.now(UTC).isoformat(),
    }


__all__ = ["AS_OF_CLOSE", "AS_OF_INTRADAY", "run_signal_scan"]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest tests/unit/test_signal_scan.py -q`
Expected: `4 passed`

- [ ] **Step 5: 提交**

```bash
cd ~/Desktop/lei-signal-lab
git add src/lei_signal/api/signal_scan.py tests/unit/test_signal_scan.py
git commit -m "feat(signals): run_signal_scan 统一扫描（买点复用既有链路 + 卖点提取落库）"
```

---

### Task 4: API 路由 `/api/signals/today` + 红点计数升级

**Files:**
- Modify: `src/lei_signal/api/schemas.py`（在 `ScanResponse` 类之后追加 3 个 DTO）
- Create: `src/lei_signal/api/routes/signals.py`
- Modify: `src/lei_signal/api/app.py`（注册新 router，跟随既有 include_router 模式）
- Modify: `src/lei_signal/api/routes/plans.py:227-243`（summary 加卖点半数）
- Test: `tests/unit/test_signals_routes.py`

**Interfaces:**
- Consumes: Task 2/3 的 CRUD 与扫描；`routes/opportunities.py` 的 `_row_to_scan_item`、`list_scan`。
- Produces:
  - `GET /api/signals/today` → `SignalsTodayResponse`（前端 Task 6 依赖的字段：`scan_date / as_of / generated_at / scanned / actionable / waiting / blocked / sell_hard / sell_warn / sell_soft / unavailable`）
  - `POST /api/signals/today/refresh?as_of=intraday|close` → 同上
  - `PlansSummaryDTO.today_signal_total: int`（红点买卖合计，Task 6 TopNav 依赖）

- [ ] **Step 1: schemas.py 追加 DTO**（`ScanResponse` 类定义之后）

```python
class SignalAlertDTO(BaseModel):
    """统一信号面板的一行卖点提醒。"""

    symbol: str
    display_name: str = ""
    tier: str  # hard | warn | soft
    kind: str
    kind_cn: str = ""
    title: str = ""
    reason_cn: str = ""
    is_new: bool = False
    key_prices: dict[str, float] = {}
    provenance: str = "system"
    available_date: str | None = None


class UnavailableItemDTO(BaseModel):
    """数据不可用清单的一项（显式 DATA_UNAVAILABLE，不静默）。"""

    symbol: str
    error: str | None = None


class SignalsTodayResponse(BaseModel):
    """今日自选信号（买点 + 卖点合并响应，看盘主页横幅数据源）。"""

    scan_date: str
    as_of: str | None = None
    generated_at: str = ""
    scanned: int = 0
    actionable: list[ScanItemDTO] = []
    waiting: list[ScanItemDTO] = []
    blocked: list[ScanItemDTO] = []
    sell_hard: list[SignalAlertDTO] = []
    sell_warn: list[SignalAlertDTO] = []
    sell_soft: list[SignalAlertDTO] = []
    unavailable: list[UnavailableItemDTO] = []
```

同时给 `PlansSummaryDTO` 追加一个字段 `today_signal_total: int = 0`（找到该类定义处，在 `today_opportunities` 字段后加）。

- [ ] **Step 2: 写失败测试**

```python
"""/api/signals/today 路由 + 红点 today_signal_total 门禁。"""
from __future__ import annotations

from contextlib import closing
from types import SimpleNamespace

from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.opportunity_scan import today_date, upsert_scan_results
from lei_signal.api.schemas import ScanItemDTO
from lei_signal.api.signal_alerts_store import (
    SIDE_SELL,
    SIDE_UNAVAILABLE,
    SignalAlertRow,
    upsert_signal_alerts,
)
from lei_signal.storage.sqlite_store import connect


def _app(tmp_path):
    app = create_app(analysis_service=SimpleNamespace())  # GET 不触分析服务
    db = str(tmp_path / "lab.db")
    app.state.plans_db_path = db
    return app, db


def _write_today(db: str, *, sell_rows=(), unavailable=(), as_of="close") -> None:
    with closing(connect(db)) as conn:
        upsert_scan_results(conn, today_date(), [
            ScanItemDTO(symbol="600519.SS", verdict="actionable", verdict_cn="条件已成立"),
            ScanItemDTO(symbol="000001.SZ", verdict="waiting", verdict_cn="等待条件成立"),
        ])
        upsert_signal_alerts(conn, today_date(), as_of, [
            *sell_rows, *unavailable,
        ])


def _sell(symbol="600519.SS", tier="hard", kind="exit_proxy") -> SignalAlertRow:
    return SignalAlertRow(
        scan_date=today_date(), symbol=symbol, display_name=symbol,
        side=SIDE_SELL, tier=tier, kind=kind, kind_cn="退出代理",
        title="收盘同破 EMA20 与 20 日抵扣价", reason_cn="x（研究代理）",
        is_new=True, key_prices={"ema20": 10.5}, provenance="research_proxy",
        available_date=today_date(),
    )


def test_today_signals_merges_buy_and_sell(tmp_path) -> None:
    app, db = _app(tmp_path)
    _write_today(db, sell_rows=[_sell(), _sell("300750.SZ", "warn", "key_wave_black"),
                                _sell("000858.SZ", "soft", "color_black")],
                 unavailable=[SignalAlertRow(
                     scan_date=today_date(), symbol="bad.SS", display_name="bad.SS",
                     side=SIDE_UNAVAILABLE, tier="hard", kind="data_unavailable",
                     title="数据不可用", error="DATA_UNAVAILABLE: x",
                 )])
    with TestClient(app) as client:
        resp = client.get("/api/signals/today")
    assert resp.status_code == 200
    body = resp.json()
    assert body["as_of"] == "close"
    assert len(body["actionable"]) == 1 and len(body["waiting"]) == 1
    assert len(body["sell_hard"]) == 1 and len(body["sell_warn"]) == 1 and len(body["sell_soft"]) == 1
    assert body["sell_hard"][0]["provenance"] == "research_proxy"
    assert len(body["unavailable"]) == 1 and "DATA_UNAVAILABLE" in body["unavailable"][0]["error"]


def test_today_signals_empty_when_no_scan(tmp_path) -> None:
    app, _db = _app(tmp_path)
    with TestClient(app) as client:
        resp = client.get("/api/signals/today")
    assert resp.status_code == 200
    body = resp.json()
    assert body["as_of"] is None
    assert body["actionable"] == [] and body["sell_hard"] == []


def test_refresh_rejects_bad_as_of(tmp_path) -> None:
    app, _db = _app(tmp_path)
    with TestClient(app) as client:
        resp = client.post("/api/signals/today/refresh?as_of=whatever")
    assert resp.status_code == 422


def test_plans_summary_includes_signal_total(tmp_path) -> None:
    app, db = _app(tmp_path)
    _write_today(db, sell_rows=[_sell(), _sell("300750.SZ", "soft", "color_black")])
    with TestClient(app) as client:
        resp = client.get("/api/plans/summary")
    assert resp.status_code == 200
    body = resp.json()
    # 买点 2 (actionable+waiting) + 卖点 hard 1（soft 不计）= 3
    assert body["today_signal_total"] == 3
    assert body["today_opportunities"] == 2
```

注意：若 `create_app` 不接受 `analysis_service=SimpleNamespace()`，改传 `analysis_service=None` 会走默认构造（会抓网）——测试里必须传替身；`SimpleNamespace()` 缺 `get_many` 只有 POST refresh 会碰到，GET 请求不会。若 TestClient 触发 app lifespan 需要真实 service，参考 `tests/` 里既有 route 测试的构造方式（`grep -rl "TestClient" tests/unit/ | head`）并对齐。

- [ ] **Step 3: 跑测试确认失败**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest tests/unit/test_signals_routes.py -q`
Expected: FAIL（404 Not Found，路由不存在）

- [ ] **Step 4: 写路由 + 注册 + 红点**

`src/lei_signal/api/routes/signals.py`：

```python
"""今日自选信号：统一买/卖点面板（看盘主页横幅）的数据源。

GET 只读库（买点 daily_opportunity_scan + 卖点 signal_alerts 合并）；
POST refresh 现场重扫并落两表。不推通知（用户决策：只面板+红点）。
"""
from contextlib import closing
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.opportunity_scan import list_scan, today_date
from lei_signal.api.routes.opportunities import _row_to_scan_item
from lei_signal.api.schemas import (
    ScanItemDTO,
    SignalAlertDTO,
    SignalsTodayResponse,
    UnavailableItemDTO,
)
from lei_signal.api.signal_alerts_store import (
    SIDE_SELL,
    SIDE_UNAVAILABLE,
    get_scan_as_of,
    list_signal_alerts,
)
from lei_signal.storage.sqlite_store import connect

router = APIRouter(prefix="/api", tags=["signals"])

_TIER_GROUPS = {"hard": "sell_hard", "warn": "sell_warn", "soft": "sell_soft"}


def _db_path(request: Request) -> str:
    return getattr(request.app.state, "plans_db_path", None) or default_db()


def _service(request: Request):
    service = getattr(request.app.state, "analysis_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="分析服务不可用")
    return service


def _build_response(db_path: str) -> SignalsTodayResponse:
    scan_date = today_date()
    with closing(connect(db_path)) as conn:
        buy_rows = list_scan(conn, scan_date)
        sell_rows = list_signal_alerts(conn, scan_date, side=SIDE_SELL)
        unavailable_rows = list_signal_alerts(conn, scan_date, side=SIDE_UNAVAILABLE)
        as_of = get_scan_as_of(conn, scan_date)
    all_rows = buy_rows + sell_rows + unavailable_rows
    response = SignalsTodayResponse(
        scan_date=scan_date,
        as_of=as_of,
        generated_at=max((r.generated_at for r in all_rows), default=""),
        scanned=len({r.symbol for r in all_rows if r.symbol}),
    )
    for row in buy_rows:
        item: ScanItemDTO = _row_to_scan_item(row)
        if item.verdict == "actionable":
            response.actionable.append(item)
        elif item.verdict == "waiting":
            response.waiting.append(item)
        elif item.verdict == "blocked":
            response.blocked.append(item)
    for row in sell_rows:
        dto = SignalAlertDTO(
            symbol=row.symbol, display_name=row.display_name, tier=row.tier,
            kind=row.kind, kind_cn=row.kind_cn, title=row.title,
            reason_cn=row.reason_cn, is_new=row.is_new,
            key_prices=dict(row.key_prices), provenance=row.provenance,
            available_date=row.available_date or None,
        )
        group = _TIER_GROUPS.get(row.tier)
        if group is not None:
            getattr(response, group).append(dto)
    for row in unavailable_rows:
        response.unavailable.append(
            UnavailableItemDTO(symbol=row.symbol, error=row.error)
        )
    return response


@router.get("/signals/today", response_model=SignalsTodayResponse)
def today_signals(request: Request) -> SignalsTodayResponse:
    """今日自选信号（读库）：看盘主页横幅 + 顶栏红点合计的数据源。"""
    return _build_response(_db_path(request))


@router.post("/signals/today/refresh", response_model=SignalsTodayResponse)
def refresh_today_signals(request: Request, as_of: str = "close") -> SignalsTodayResponse:
    """立即重扫自选（买+卖）并整体重写当日两表。as_of: intraday | close。"""
    from lei_signal.api.signal_scan import (  # noqa: PLC0415
        AS_OF_CLOSE,
        AS_OF_INTRADAY,
        run_signal_scan,
    )

    if as_of not in (AS_OF_INTRADAY, AS_OF_CLOSE):
        raise HTTPException(status_code=422, detail="as_of 只能是 intraday 或 close")
    run_signal_scan(_service(request), _db_path(request), as_of=as_of, refresh=True)
    return _build_response(_db_path(request))


__all__ = ["refresh_today_signals", "router", "today_signals"]
```

`src/lei_signal/api/app.py` 注册（找到既有 `app.include_router(...)` 块，跟随同样写法加两行）：

```python
from lei_signal.api.routes import signals as signals_routes  # 与既有 routes import 放一起

    app.include_router(signals_routes.router)  # 与既有 include_router 放一起
```

`src/lei_signal/api/routes/plans.py:227-243` 的 `plans_summary` 改为：

```python
@router.get("/plans/summary", response_model=PlansSummaryDTO)
def plans_summary(request: Request) -> PlansSummaryDTO:
    """顶栏红点：未处理待办数 + 活跃计划数 + 今日机会数 + 买卖信号合计。"""
    from lei_signal.api.opportunity_scan import (  # noqa: PLC0415
        count_opportunities,
        today_date,
    )
    from lei_signal.api.signal_alerts_store import count_sell_alerts  # noqa: PLC0415

    with closing(connect(_db_path(request))) as conn:
        open_actions = count_open_action_items(conn)
        active = list_plans(conn, state="armed") + list_plans(conn, state="entered")
        today_opps = count_opportunities(conn, today_date())
        today_sell = count_sell_alerts(conn, today_date())
    return PlansSummaryDTO(
        open_actions=open_actions,
        active_plans=len(active),
        today_opportunities=today_opps,
        today_signal_total=today_opps + today_sell,
    )
```

- [ ] **Step 5: 跑测试确认通过**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest tests/unit/test_signals_routes.py -q`
Expected: `4 passed`

- [ ] **Step 6: 跑既有测试确认无回归**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest -q`
Expected: 全部通过（496 + 新增 ~23）

- [ ] **Step 7: 提交**

```bash
cd ~/Desktop/lei-signal-lab
git add src/lei_signal/api/schemas.py src/lei_signal/api/routes/signals.py src/lei_signal/api/app.py src/lei_signal/api/routes/plans.py tests/unit/test_signals_routes.py
git commit -m "feat(signals): /api/signals/today 统一信号 API + 红点买卖合计"
```

---

### Task 5: CLI 脚本 + launchd 调度 + 运维接线

**Files:**
- Create: `scripts/signal_scan.py`
- Create: `scripts/com.lei.signal.scan.plist`
- Modify: `scripts/install_app_autostart.sh:46-49`（`install_agent com.lei.sector.trend` 之后加一行）
- Modify: `scripts/biao-ctl.sh:26-34`（status 的 grep 正则加 `|signal`）
- Modify: `运维手册.md`（追加第 10 节）

**Interfaces:**
- Consumes: Task 3 的 `run_signal_scan / AS_OF_INTRADAY / AS_OF_CLOSE`；`AnalysisService`（V8 预热模式抄 `scripts/daily_scan.py:80-84`）。
- Produces: launchd agent `com.lei.signal.scan`，交易日 11:35 / 14:45 / 15:05 三次触发。

- [ ] **Step 1: 写 CLI 脚本**

```python
"""LEI 今日自选信号统一扫描 (launchd 交易日 11:35 / 14:45 / 15:05).

买点行 -> daily_opportunity_scan (既有表, /grid 面板同步受益);
卖点行 + 数据不可用 -> signal_alerts (看盘主页「今日自选信号」横幅读).
as_of 按触发时刻自动定: 15:00 及以后 = close (当日最终口径), 之前 = intraday (盘中临时).

**只写扫描结果, 不推通知** (用户决策: 只面板+红点).
判定权在 Python 规则层; 本脚本只编排 analyze + 落库 (与 daily_scan.py 同模式).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from lei_signal.api.config import sqlite_path  # noqa: E402
from lei_signal.api.signal_scan import (  # noqa: E402
    AS_OF_CLOSE,
    AS_OF_INTRADAY,
    run_signal_scan,
)
from lei_signal.api.watchlist import list_watchlist  # noqa: E402
from lei_signal.storage.sqlite_store import connect  # noqa: E402


def _default_as_of() -> str:
    return AS_OF_CLOSE if datetime.now().hour >= 15 else AS_OF_INTRADAY


def main() -> int:
    parser = argparse.ArgumentParser(description="LEI 今日自选信号统一扫描")
    parser.add_argument("--symbols", help="逗号分隔标的列表 (默认全部自选)")
    parser.add_argument(
        "--as-of", choices=[AS_OF_INTRADAY, AS_OF_CLOSE], default=None,
        help="口径 (默认按当前时间: >=15 点为 close)",
    )
    parser.add_argument("--dry-run", action="store_true", help="不写库, 只打印")
    parser.add_argument("--db", help="SQLite 路径 (默认 config.sqlite_path)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    db = args.db or os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path())

    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    else:
        with connect(db) as conn:
            symbols = [i.symbol for i in list_watchlist(conn)]
    if not symbols:
        print("完成: 自选为空, 无可扫描标的")
        return 0

    from lei_signal.api.services import AnalysisService  # noqa: PLC0415

    service = AnalysisService(max_workers=8)
    # 串行预热 V8 (与 daily_scan.py 同因: mini_racer 并发初始化会崩, 先跑一个标的)
    service.get(symbols[0], refresh=True)

    summary = run_signal_scan(
        service, db, symbols=symbols,
        as_of=args.as_of or _default_as_of(),
        refresh=True, dry_run=args.dry_run,
    )
    print(f"完成: {summary}")
    # mini_racer (V8) 进程退出清理崩溃, 工作已完成, 直接 _exit 跳过 teardown
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    raise SystemExit(main())
```

（上面代码可直接使用；`as_of` 参数默认按当前小时自动选 close/intraday，`--as-of` 可显式覆盖。）

- [ ] **Step 2: 写 plist**（`scripts/com.lei.signal.scan.plist`，三个时刻 × 周一到周五 = 15 个 dict，模式抄 `scripts/com.lei.daily_scan.plist`）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lei.signal.scan</string>

    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/python3</string>
        <string>scripts/signal_scan.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/yongbiaoli/Desktop/lei-signal-lab</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>/Users/yongbiaoli/Desktop/lei-signal-lab/src</string>
    </dict>

    <!-- 交易日 11:35 (上午收盘后) / 14:45 (盘中) / 15:05 (收盘最终版) 统一扫描.
         11:35/14:45 为 intraday 口径 (盘中临时), 15:05 为 close 口径覆盖当日.
         只写库不推通知 (用户决策). 14:45 与 intraday_check/watch_check 同时刻段,
         SQLite WAL 下读写不互斥. -->
    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>11</integer><key>Minute</key><integer>35</integer></dict>
        <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>11</integer><key>Minute</key><integer>35</integer></dict>
        <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>11</integer><key>Minute</key><integer>35</integer></dict>
        <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>11</integer><key>Minute</key><integer>35</integer></dict>
        <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>11</integer><key>Minute</key><integer>35</integer></dict>
        <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>14</integer><key>Minute</key><integer>45</integer></dict>
        <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>14</integer><key>Minute</key><integer>45</integer></dict>
        <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>14</integer><key>Minute</key><integer>45</integer></dict>
        <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>14</integer><key>Minute</key><integer>45</integer></dict>
        <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>14</integer><key>Minute</key><integer>45</integer></dict>
        <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>15</integer><key>Minute</key><integer>5</integer></dict>
        <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>15</integer><key>Minute</key><integer>5</integer></dict>
        <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>15</integer><key>Minute</key><integer>5</integer></dict>
        <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>15</integer><key>Minute</key><integer>5</integer></dict>
        <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>15</integer><key>Minute</key><integer>5</integer></dict>
    </array>

    <key>StandardOutPath</key>
    <string>/Users/yongbiaoli/Desktop/lei-signal-lab/logs/signal_scan.out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/yongbiaoli/Desktop/lei-signal-lab/logs/signal_scan.err.log</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

- [ ] **Step 3: 接线安装脚本**

`scripts/install_app_autostart.sh` 的 `install_agent com.lei.sector.trend`（`:49`）之后加：

```bash
install_agent com.lei.signal.scan
```

`scripts/biao-ctl.sh:34` 的 grep 正则改为：

```bash
    launchctl list 2>/dev/null | grep -E "com\.lei\.(backend|frontend|ashare|sector|signal)" || echo "  (无 com.lei.* 被 load —— 需先跑 install)"
```

- [ ] **Step 4: 运维手册追加第 10 节**（`运维手册.md` 文件末尾追加）

```markdown
---

## 10. 今日自选信号扫描（看盘主页横幅 / 顶栏红点）

看盘主页中栏顶部的「今日自选信号」横幅 + 顶栏红点，数据来自第五个 agent
`com.lei.signal.scan`，每个交易日 **11:35 / 14:45 / 15:05** 跑
`python scripts/signal_scan.py`：

| 时刻 | 口径 | 说明 |
|---|---|---|
| 11:35 | intraday（盘中临时） | 上午收盘后，当天还能操作 |
| 14:45 | intraday（盘中临时） | 尾盘前最后一眼 |
| 15:05 | close（收盘最终版） | 覆盖当日结论，为当日权威口径 |

- 买点行写 `daily_opportunity_scan`（卡片墙的今日机会雷达同步受益）；
  卖点行（结构失效 / 退出代理 / 顶部路牌预警 / 颜色转黑）写 `signal_alerts`。
- 横幅上的「盘中临时」徽标 = intraday 口径，收盘后以 15:05 版为准。
- 只写库不推通知（用户决策）。手动重扫：横幅 [刷新] 按钮，或
  `python3 scripts/signal_scan.py --as-of close`。

### 10.1 故障排查
| 现象 | 处理 |
|---|---|
| 横幅显示「今日尚未扫描」 | `biao status` 看 `com.lei.signal.scan` 是否 load；没有就 `biao install`；急用手动跑一次脚本 |
| 扫描报错 | 看 `logs/signal_scan.err.log`；多半是数据源临时不可用，下个时刻自动重试 |
| 某标的进「数据不可用」区 | 该标的 analyze 失败（DATA_UNAVAILABLE 显式展示，不静默）；确认代码格式是否正确、数据源是否可用 |
```

- [ ] **Step 5: 手动验证脚本可跑**

Run: `cd ~/Desktop/lei-signal-lab && python3 scripts/signal_scan.py --symbols sh000001 --as-of intraday --dry-run`
Expected: 打印 `完成: {...}`，`--dry-run` 不写库；再去掉 `--dry-run` 跑一次，然后
`curl -s http://127.0.0.1:8000/api/signals/today | head -c 400` 应返回 JSON（后端重启前的旧进程没有新路由，验证 SQL 落库用 `sqlite3 lab.db "SELECT scan_date, symbol, side, kind FROM signal_alerts ORDER BY generated_at DESC LIMIT 5"`）。

- [ ] **Step 6: 提交**

```bash
cd ~/Desktop/lei-signal-lab
git add scripts/signal_scan.py scripts/com.lei.signal.scan.plist scripts/install_app_autostart.sh scripts/biao-ctl.sh 运维手册.md
git commit -m "feat(signals): signal_scan CLI + launchd 11:35/14:45/15:05 调度 + 运维手册"
```

---

### Task 6: 前端横幅 + 红点升级

**Files:**
- Modify: `web/src/types.ts`（`PlansSummary` 的 `today_opportunities` 字段附近 + 文件内 TodayOpportunityResponse 类型附近追加新类型）
- Modify: `web/src/api/client.ts:257-259`（todayOpportunities 附近追加两个方法）
- Create: `web/src/components/TodaySignalBanner.tsx`
- Modify: `web/src/pages/WorkspacePage.tsx`（import + handler + 中栏挂载）
- Modify: `web/src/components/TopNav.tsx:18,25`（红点用合计数）
- Modify: `web/src/styles.css`（文件末尾追加 .sig-* 样式）

**Interfaces:**
- Consumes: Task 4 的 `GET/POST /api/signals/today`、`PlansSummary.today_signal_total`。
- Produces: `TodaySignalBanner`（props: `onPick: (symbol: string, side: "buy" | "sell") => void`）。

- [ ] **Step 1: types.ts 追加类型**（放在 TodayOpportunity 相关类型旁边）

```ts
export interface SignalAlert {
  symbol: string;
  display_name: string;
  tier: "hard" | "warn" | "soft" | string;
  kind: string;
  kind_cn: string;
  title: string;
  reason_cn: string;
  is_new: boolean;
  key_prices: Record<string, number>;
  provenance: string;
  available_date: string | null;
}

export interface UnavailableItem {
  symbol: string;
  error: string | null;
}

export interface SignalsToday {
  scan_date: string;
  as_of: string | null;
  generated_at: string;
  scanned: number;
  actionable: ScanItem[];
  waiting: ScanItem[];
  blocked: ScanItem[];
  sell_hard: SignalAlert[];
  sell_warn: SignalAlert[];
  sell_soft: SignalAlert[];
  unavailable: UnavailableItem[];
}
```

同时给 `PlansSummary` 接口（`types.ts:841` 附近）追加 `today_signal_total: number;`。

- [ ] **Step 2: client.ts 追加方法**（`refreshTodayOpportunities` 之后）

```ts
  signalsToday: () => request<SignalsToday>(`/signals/today`),
  refreshSignals: (asOf: "intraday" | "close" = "close") =>
    request<SignalsToday>(`/signals/today/refresh?as_of=${asOf}`, { method: "POST" }),
```

（顶部 import 补 `SignalsToday` 类型。）

- [ ] **Step 3: 写 TodaySignalBanner 组件**

```tsx
/** 今日自选信号横幅 -- 看盘主页中栏顶部.
 *
 *  数据源: GET /api/signals/today (launchd 11:35/14:45/15:05 写库, 60s 轮询).
 *  买点行 (actionable/waiting/blocked) + 卖点行 (hard/warn/soft 四档口径) 统一展示;
 *  点行 = 选中该标的 (不跳页): 买·行动自动打开买点分析抽屉, 卖点行展开右栏解释.
 *  [刷新] 调 POST /api/signals/today/refresh (按当前时间自动选 as_of).
 *  买·受阻默认折叠 (<details>); 数据不可用显式列出, 不静默.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ScanItem, SignalAlert } from "../types";

const TIER_LABEL: Record<string, string> = {
  hard: "卖·硬",
  warn: "卖·预警",
  soft: "卖·提醒",
};

const TIER_COLOR: Record<string, string> = {
  hard: "var(--danger, #e5484d)",
  warn: "var(--warn)",
  soft: "var(--text-faint)",
};

const BUY_LABEL: Record<string, string> = {
  actionable: "买·行动",
  waiting: "买·等待",
  blocked: "买·受阻",
};

const BUY_COLOR: Record<string, string> = {
  actionable: "var(--lei-green)",
  waiting: "var(--text-faint)",
  blocked: "var(--warn)",
};

function SellRow({
  it,
  onPick,
}: {
  it: SignalAlert;
  onPick: (symbol: string, side: "sell") => void;
}) {
  return (
    <li className="sig-row">
      <div className="sig-row-head">
        <button className="sig-symbol" onClick={() => onPick(it.symbol, "sell")}>
          {it.display_name || it.symbol}
        </button>
        <span
          className="sig-tier"
          style={{ background: TIER_COLOR[it.tier] ?? "var(--text-faint)" }}
        >
          {TIER_LABEL[it.tier] ?? it.tier}
        </span>
        <span className="sig-kind">{it.kind_cn}</span>
        {it.provenance === "research_proxy" && (
          <span className="sig-proxy">研究代理</span>
        )}
        {it.is_new ? (
          <span className="sig-new">新增</span>
        ) : (
          <span className="sig-cont">持续</span>
        )}
      </div>
      <div className="sig-title">{it.title}</div>
      <div className="sig-reason">{it.reason_cn}</div>
      {Object.keys(it.key_prices).length > 0 && (
        <div className="sig-prices">
          {Object.entries(it.key_prices).map(([k, v]) => (
            <span key={k}>
              {k} {v.toFixed(2)}
            </span>
          ))}
        </div>
      )}
    </li>
  );
}

function BuyRow({
  it,
  onPick,
}: {
  it: ScanItem;
  onPick: (symbol: string, side: "buy") => void;
}) {
  return (
    <li className="sig-row">
      <div className="sig-row-head">
        <button className="sig-symbol" onClick={() => onPick(it.symbol, "buy")}>
          {it.display_name || it.symbol}
        </button>
        <span
          className="sig-tier"
          style={{ background: BUY_COLOR[it.verdict] ?? "var(--text-faint)" }}
        >
          {BUY_LABEL[it.verdict] ?? it.verdict_cn}
        </span>
        {it.reward_risk_computable && it.reward_risk_ratio != null && (
          <span className="sig-kind">R/R {it.reward_risk_ratio.toFixed(1)}</span>
        )}
        {it.has_active_plan && <span className="sig-cont">已有计划</span>}
      </div>
      {it.best_scenario_cn && <div className="sig-title">{it.best_scenario_cn}</div>}
      {it.verdict === "blocked" && it.blocking_reasons.length > 0 && (
        <div className="sig-reason">阻断：{it.blocking_reasons.join("、")}</div>
      )}
      {it.verdict === "waiting" && it.missing_summary_cn && (
        <div className="sig-reason">缺：{it.missing_summary_cn}</div>
      )}
    </li>
  );
}

function Group({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="sig-group">
      <div className="sig-group-head">{title}</div>
      <ul className="sig-list">{children}</ul>
    </div>
  );
}

export default function TodaySignalBanner({
  onPick,
}: {
  onPick: (symbol: string, side: "buy" | "sell") => void;
}) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const { data } = useQuery({
    queryKey: ["signalsToday"],
    queryFn: () => api.signalsToday(),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
  const refresh = useMutation({
    mutationFn: () => {
      const hour = new Date().getHours();
      return api.refreshSignals(hour >= 15 ? "close" : "intraday");
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["signalsToday"] });
      qc.invalidateQueries({ queryKey: ["plansSummary"] });
    },
  });

  const asOf = data?.as_of ?? null;
  const scanned = asOf != null;
  const buyA = data?.actionable ?? [];
  const buyW = data?.waiting ?? [];
  const buyB = data?.blocked ?? [];
  const sellH = data?.sell_hard ?? [];
  const sellWarn = data?.sell_warn ?? [];
  const sellS = data?.sell_soft ?? [];
  const empty =
    buyA.length + buyW.length + buyB.length + sellH.length + sellWarn.length +
    sellS.length + (data?.unavailable.length ?? 0) === 0;

  return (
    <div className="sig-banner">
      <div className="sig-banner-head">
        <b>🔔 今日自选信号</b>
        {scanned && (
          <span className={`sig-asof${asOf === "intraday" ? " intraday" : ""}`}>
            {asOf === "intraday" ? "盘中临时" : "收盘"}
          </span>
        )}
        <span className="muted">
          {scanned
            ? `买·行动 ${buyA.length} · 买·等待 ${buyW.length} · 卖·硬 ${sellH.length} · 卖·预警 ${sellWarn.length} · 卖·提醒 ${sellS.length}`
            : "今日尚未扫描"}
        </span>
        <span className="sig-spacer" />
        <button
          className="btn small"
          disabled={refresh.isPending}
          onClick={() => refresh.mutate()}
        >
          {refresh.isPending ? "扫描中…" : "刷新"}
        </button>
        {scanned && (
          <button className="btn small" onClick={() => setOpen((v) => !v)}>
            {open ? "收起 ▲" : "展开 ▼"}
          </button>
        )}
      </div>
      {open && scanned && (
        <div className="sig-groups">
          {buyA.length > 0 && (
            <Group title={`✅ 买·行动 ${buyA.length}`}>
              {buyA.map((it) => (
                <BuyRow key={it.symbol} it={it} onPick={onPick} />
              ))}
            </Group>
          )}
          {sellH.length > 0 && (
            <Group title={`🔻 卖·硬信号 ${sellH.length}`}>
              {sellH.map((it) => (
                <SellRow key={`${it.symbol}-${it.kind}`} it={it} onPick={onPick} />
              ))}
            </Group>
          )}
          {buyW.length > 0 && (
            <Group title={`⏳ 买·等待 ${buyW.length}`}>
              {buyW.map((it) => (
                <BuyRow key={it.symbol} it={it} onPick={onPick} />
              ))}
            </Group>
          )}
          {sellWarn.length > 0 && (
            <Group title={`⚠️ 卖·预警（不必然反向） ${sellWarn.length}`}>
              {sellWarn.map((it) => (
                <SellRow key={`${it.symbol}-${it.kind}`} it={it} onPick={onPick} />
              ))}
            </Group>
          )}
          {sellS.length > 0 && (
            <Group title={`🌑 卖·提醒 ${sellS.length}`}>
              {sellS.map((it) => (
                <SellRow key={`${it.symbol}-${it.kind}`} it={it} onPick={onPick} />
              ))}
            </Group>
          )}
          {buyB.length > 0 && (
            <details className="sig-blocked">
              <summary className="sig-group-head">
                买·受阻 {buyB.length}（默认折叠）
              </summary>
              <ul className="sig-list">
                {buyB.map((it) => (
                  <BuyRow key={it.symbol} it={it} onPick={onPick} />
                ))}
              </ul>
            </details>
          )}
          {(data?.unavailable.length ?? 0) > 0 && (
            <div className="sig-group">
              <div className="sig-group-head">🚫 数据不可用</div>
              <ul className="sig-list">
                {data!.unavailable.map((u) => (
                  <li key={u.symbol} className="sig-row muted">
                    {u.symbol}：{u.error ?? "原因未知"}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {empty && <div className="muted sig-empty">当前窗口内无买卖信号。</div>}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: WorkspacePage 挂载**

`web/src/pages/WorkspacePage.tsx` 三处修改：

1. import 区（`TodayOverviewPanel` import 附近）加：
```tsx
import TodaySignalBanner from "../components/TodaySignalBanner";
```

2. `selectSymbol`（约 `:139-145`）之后加 handler：
```tsx
  const handleSignalPick = useCallback(
    (symbol: string, side: "buy" | "sell") => {
      selectSymbol(symbol);
      if (side === "buy") {
        setShowBuyPoint(true); // 买点行直接打开买点分析抽屉
      } else {
        setExpCollapsed(false); // 卖点行展开右栏解释
      }
    },
    [selectSymbol],
  );
```

3. `<main className="ws-center">`（`:388`）内、`{isLoading && ...}`（`:396`）之后、`{data && (`（`:398`）之前插入：
```tsx
        <TodaySignalBanner onPick={handleSignalPick} />
```

- [ ] **Step 5: TopNav 红点升级**

`web/src/components/TopNav.tsx:18` 改为：
```tsx
  const todayOpps = data?.today_signal_total ?? data?.today_opportunities ?? 0;
```
（`:7` 注释同步改为「看盘入口带红点（买卖信号合计 = 买点机会 + 卖点硬/预警）」。）

- [ ] **Step 6: styles.css 追加样式**（文件末尾）

```css
/* ---- 今日自选信号横幅 (TodaySignalBanner) ---- */
.sig-banner {
  border: 1px solid rgba(128, 128, 128, 0.35);
  border-radius: 8px;
  padding: 6px 10px;
  margin-bottom: 8px;
}
.sig-banner-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.sig-spacer { flex: 1; }
.sig-asof {
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--lei-green);
  color: #fff;
}
.sig-asof.intraday { background: var(--warn); }
.sig-groups { margin-top: 8px; display: grid; gap: 8px; }
.sig-group-head { font-weight: 600; margin: 4px 0; }
.sig-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
.sig-row { border-top: 1px dashed rgba(128, 128, 128, 0.35); padding: 4px 0; }
.sig-row-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.sig-symbol {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  font-weight: 600;
  text-decoration: underline;
}
.sig-tier { color: #fff; font-size: 12px; padding: 1px 6px; border-radius: 4px; }
.sig-kind { color: var(--text-faint); font-size: 12px; }
.sig-proxy {
  font-size: 12px;
  border: 1px solid var(--warn);
  color: var(--warn);
  border-radius: 4px;
  padding: 0 4px;
}
.sig-new { font-size: 12px; color: var(--danger, #e5484d); }
.sig-cont { font-size: 12px; color: var(--text-faint); }
.sig-title { font-size: 13px; margin-top: 2px; }
.sig-reason { font-size: 12px; color: var(--text-faint); margin-top: 2px; }
.sig-prices { font-size: 12px; margin-top: 2px; display: flex; gap: 8px; }
.sig-blocked summary { cursor: pointer; }
.sig-empty { padding: 4px 0; }
```

- [ ] **Step 7: 构建验证**

Run: `cd ~/Desktop/lei-signal-lab/web && npm run build`
Expected: `vite build` 成功，无 TypeScript 错误

- [ ] **Step 8: 提交**

```bash
cd ~/Desktop/lei-signal-lab
git add web/src/types.ts web/src/api/client.ts web/src/components/TodaySignalBanner.tsx web/src/pages/WorkspacePage.tsx web/src/components/TopNav.tsx web/src/styles.css
git commit -m "feat(signals): 看盘主页今日自选信号横幅 + 顶栏红点买卖合计"
```

---

### Task 7: 端到端验收

**Files:** 无新文件（验证 + 安装调度 + 收尾）

- [ ] **Step 1: 全量后端测试**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m pytest -q`
Expected: 全部通过，无回归

- [ ] **Step 2: lint 快检**

Run: `cd ~/Desktop/lei-signal-lab && python3 -m ruff check src/lei_signal/api/sell_signals.py src/lei_signal/api/signal_alerts_store.py src/lei_signal/api/signal_scan.py src/lei_signal/api/routes/signals.py scripts/signal_scan.py tests/unit/test_sell_signals.py tests/unit/test_signal_alerts_store.py tests/unit/test_signal_scan.py tests/unit/test_signals_routes.py`
Expected: 无 error（既有 13 项工程债不新增）

- [ ] **Step 3: 安装 launchd agent + 重启服务**

```bash
cd ~/Desktop/lei-signal-lab && bash scripts/install_app_autostart.sh
source ~/.zshrc 2>/dev/null; biao restart
```
Expected: install 输出包含 `com.lei.signal.scan`；`biao status` 里能看到它

- [ ] **Step 4: 真实扫描一次 + API 验证**

```bash
cd ~/Desktop/lei-signal-lab && python3 scripts/signal_scan.py --as-of intraday
curl -s http://127.0.0.1:8000/api/signals/today | python3 -m json.tool | head -40
curl -s http://127.0.0.1:8000/api/plans/summary | python3 -m json.tool
```
Expected: `/api/signals/today` 返回带 `as_of`、分组数组的 JSON；summary 含 `today_signal_total`

- [ ] **Step 5: 浏览器验收**

打开 `http://localhost:5173/`：看盘主页中栏顶部出现「🔔 今日自选信号」横幅；展开能看到分组；点买点行选中标的并弹出买点分析抽屉；点卖点行选中标的且右栏解释展开；顶栏「看盘」红点为买卖合计。`/grid` 卡片墙无回归。

- [ ] **Step 6: 验收结论回写**

把验收结果（扫描条数、横幅截图说明、红点数字）追加到设计文档 `docs/superpowers/specs/2026-08-23-unified-signal-panel-design.md` 末尾「验收记录」小节，并提交：

```bash
cd ~/Desktop/lei-signal-lab
git add docs/superpowers/specs/2026-08-23-unified-signal-panel-design.md
git commit -m "docs(signals): 今日自选信号面板验收记录"
```

---

## Self-Review 记录

- **Spec 覆盖**：§2 四档口径→Task 1；§3.1-3.3 后端→Task 1-4；§3.4 盘中口径→Task 3(as_of)+Task 5(时刻表)；§4 前端→Task 6；§5 调度→Task 5；§6 错误处理→Task 3(unavailable 行)+Task 4(空态 as_of=None)+Task 6(空态文案)；§7 测试→各任务 TDD + Task 7；§8 验收→Task 7。无遗漏。
- **占位符**：Task 5 Step 1 含一行防笔误说明（`as_of=args.as_of or _default_as_of()`），其余无 TBD/TODO。
- **类型一致性**：`SellSignal` 字段与 `SignalAlertRow`/`SignalAlertDTO`/TS `SignalAlert` 一一对应；`as_of` 常量名 Task 3/4/5 统一 `AS_OF_INTRADAY/AS_OF_CLOSE`；`count_sell_alerts` 默认 `("hard","warn")` 与红点语义一致。
- **风险提示**：Task 4 测试的 `create_app` 替身注入方式如与既有测试模式不符，以仓库既有 TestClient 测试写法为准调整（已注明查找命令）。
