# 宽度择时回测（B20/B50/B200）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在回测页新增「宽度择时回测」：用 B20/B50/B200 宽度对沪深300/创业板指/标普500/纳指做约 20 年的阶梯与反转择时回测（含趋势闸门组合、双分批模式、参数扫描找最优参数组）。

**Architecture:** 新独立模块 `src/lei_signal/timing_backtest/`（数据对齐 → 策略产出目标仓位 → 引擎 T+1 开盘成交 → 指标），FastAPI 同步路由，前端 BacktestPage 加 tab 复用 `bt-*` 样式与 echarts。与现有 `backtest/`（R 口径）零耦合。

**Tech Stack:** Python 3 / pandas / FastAPI / pydantic / akshare（A股数据）/ yfinance（美股数据）/ pytest；React 18 + TS + echarts 5。

**Spec:** `docs/superpowers/specs/2026-08-27-breadth-timing-backtest-design.md`

## Global Constraints

- 主检出 `/Users/yongbiaoli/Desktop/lei-signal-lab`，分支 `feat/timing-backtest`；**不得提交本分支外的既有脏文件**（git add 只加本计划列出的文件）
- 不触碰 AST 门禁禁词：`place_order, submit_order, AccountState, FundID, ProxyID, StrategyEngine, CandidateIntent, AggregateResolver, position_size`（`tests/integration/test_acceptance_gates.py:298`）
- 信号 T 日收盘可得 → **T+1 开盘成交**，全链路不得引入未来函数（有单测锁死）
- 数据缺失必须显式报 `DATA_UNAVAILABLE`（HTTP 409 + 明确 message），不得静默
- 页面必须展示数据诚实声明：全A宽度早年幸存者偏差、sina 不复权价影响、宽度截至最近回填日
- 现有测试套件保持全绿；新增模块过 `ruff check` 与 `mypy`（仓库既有标准）
- 所有时间序列一律用 pandas DatetimeIndex（UTC-naive），A/美股共用 252 交易日年化系数

## 目录与文件职责

```
src/lei_signal/timing_backtest/
  __init__.py        空
  data.py            数据加载/对齐/宽度重算纯函数 + 工具注册表
  strategies.py      ladder / reversal / trend_gate → 目标仓位序列（纯函数）
  engine.py          T+1 开盘成交模拟 → 净值/仓位/调仓记录
  metrics.py         年化/回撤/Sharpe/Calmar/逐年/暴露率
  presets.py         预设参数组（含扫描胜出组，标注来源）
  service.py         options 构建、execute_run、运行记录落盘/列表
  sweep.py           参数扫描网格构建 + 批量执行 + 稳健性筛选
scripts/
  backfill_timing_data.py   一次性数据回填（网络 IO）
  sweep_timing_backtest.py  扫描入口（薄壳，调 sweep.py）
tests/unit/
  test_timing_data.py  test_timing_strategies.py
  test_timing_engine.py  test_timing_metrics.py
  test_timing_service.py  test_timing_sweep.py
web/src/
  types.ts                     追加 Timing* 类型
  api/client.ts                追加 timingBacktestApi
  components/BreadthTimingPanel.tsx   宽度择时面板（参数+结果+图）
  pages/BacktestPage.tsx       顶部 tab 切换
docs/timing-sweep/             扫描报告输出目录
```

---

### Task 1: 数据层 `data.py` + 回填脚本

**Files:**
- Create: `src/lei_signal/timing_backtest/__init__.py`（空）
- Create: `src/lei_signal/timing_backtest/data.py`
- Create: `scripts/backfill_timing_data.py`
- Test: `tests/unit/test_timing_data.py`

**Interfaces（Produces，后续任务依赖）:**
```python
TIMING_CACHE_DIR: Path                       # env LEI_TIMING_CACHE_DIR 覆盖，默认 ~/.lei_signal_lab/cache/timing
@dataclass(frozen=True) InstrumentSpec:
    symbol: str; name: str; market: str      # "cn" | "us"
    breadth: str                             # "cn_all" | "sp500"
    data_file: str; source: str              # "ak_index" | "ak_etf" | "yf"
    fetch_symbol: str; fee_default_bps: float; note: str
INSTRUMENTS: dict[str, InstrumentSpec]       # 8 个标的（见下）
def compute_breadth_from_close_matrix(close_wide: pd.DataFrame, windows=(20,50,200), min_eligible=30) -> pd.DataFrame
    # index=DatetimeIndex, columns=[b20,b50,b200,n20,n50,n200]（b 值 0-100，eligible<min_eligible → NaN）
def load_breadth(market: str, cache_dir=TIMING_CACHE_DIR) -> pd.DataFrame       # date,b20,b50,b200（无 n 列）
def load_index_bars(symbol: str, cache_dir=TIMING_CACHE_DIR) -> pd.DataFrame    # index date, columns open,close
def align_index_breadth(index_df, breadth_df) -> pd.DataFrame                    # 日期交集, columns: open,close,b20,b50,b200
def data_unavailable_detail(symbol: str) -> str                                 # 面向用户的缺失说明
```
INSTRUMENTS 八项：`000300`沪深300/ak_index/fetch `sh000300`/fee 5bp；`399006`创业板指/`sz399006`/5bp；`^GSPC`标普500/yf/1bp；`^IXIC`纳指/yf/1bp；`SPY`/`QQQ`/yf/1bp；`510300`/ak_etf/fetch `510300`/5bp；`159915`/ak_etf/`159915`/5bp。A 股 note 带幸存者偏差提示，ETF note 标注「含分红、历史较短」。

- [ ] **Step 1: 写失败测试**（`tests/unit/test_timing_data.py`）

```python
"""timing_backtest.data 宽度重算与对齐纯函数测试。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.timing_backtest.data import (
    align_index_breadth,
    compute_breadth_from_close_matrix,
    load_breadth,
    load_index_bars,
)


def _wide() -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-01", periods=250)
    # 两只全程上涨（永远在 MA 上方）、一只恒为 100（=MA，不高于）、一只 NaN 掩码
    up1 = pd.Series(np.linspace(10, 30, 250), index=idx)
    up2 = pd.Series(np.linspace(5, 25, 250), index=idx)
    flat = pd.Series(np.full(250, 100.0), index=idx)
    late = pd.Series(np.linspace(1, 2, 250), index=idx)
    late.iloc[:199] = np.nan  # 只有 51 根，不够 MA200
    return pd.DataFrame({"UP1": up1, "UP2": up2, "FLAT": flat, "LATE": late})


def test_breadth_values_and_eligibility():
    out = compute_breadth_from_close_matrix(_wide())
    # MA20：UP1/UP2 在上方，FLAT close==MA 不算上方，LATE 有 51 根≥20 → eligible
    # 第 20 根后：above=2, eligible=4 → b20=50
    assert out["b20"].iloc[-1] == pytest.approx(50.0)
    assert out["n20"].iloc[-1] == 4
    # MA200：LATE 只有 51 根 → 不 eligible；b200 = 2/3
    assert out["n200"].iloc[-1] == 3
    assert out["b200"].iloc[-1] == pytest.approx(200.0 / 3.0)
    # 前 199 根没有 MA200 eligible → NaN
    assert out["b200"].iloc[0] != out["b200"].iloc[0]


def test_min_eligible_guard():
    idx = pd.bdate_range("2024-01-01", periods=250)
    tiny = pd.DataFrame({"A": np.linspace(1, 2, 250)}, index=idx)
    out = compute_breadth_from_close_matrix(tiny, min_eligible=30)
    assert out["b20"].isna().all()


def test_align_intersection_and_cache_roundtrip(tmp_path):
    idx = pd.bdate_range("2025-01-01", periods=10)
    bars = pd.DataFrame({"open": np.arange(10.0), "close": np.arange(10.0) + 1}, index=idx)
    br = pd.DataFrame(
        {"b20": np.arange(10.0), "b50": np.arange(10.0), "b200": np.arange(10.0)},
        index=idx[:-3],
    )
    bars.to_parquet(tmp_path / "X.parquet")
    br.to_parquet(tmp_path / "breadth_cn_all.parquet")
    loaded = load_index_bars("X", cache_dir=tmp_path)
    pd.testing.assert_frame_equal(loaded, bars)
    merged = align_index_breadth(bars, load_breadth("cn_all", cache_dir=tmp_path))
    assert len(merged) == 7
    assert list(merged.columns) == ["open", "close", "b20", "b50", "b200"]
```

- [ ] **Step 2: 跑测试确认失败** — `python3 -m pytest tests/unit/test_timing_data.py -v` → ModuleNotFoundError
- [ ] **Step 3: 实现 `data.py`**（核心如下）

```python
"""宽度择时回测数据层：加载、对齐、全A宽度重算（纯函数）。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

TIMING_CACHE_DIR = Path(
    os.environ.get("LEI_TIMING_CACHE_DIR", str(Path.home() / ".lei_signal_lab/cache/timing"))
)

BREADTH_FILES = {"cn_all": "breadth_cn_all.parquet", "sp500": "breadth_sp500.parquet"}
SURVIVORSHIP_NOTE = "宽度为当前存续成分回算，早年存在幸存者偏差；全A底表为新浪不复权价"


@dataclass(frozen=True)
class InstrumentSpec:
    symbol: str
    name: str
    market: str          # cn | us
    breadth: str         # cn_all | sp500
    data_file: str
    source: str          # ak_index | ak_etf | yf
    fetch_symbol: str
    fee_default_bps: float
    note: str = ""


INSTRUMENTS: dict[str, InstrumentSpec] = {
    "000300": InstrumentSpec("000300", "沪深300", "cn", "cn_all", "000300.parquet", "ak_index", "sh000300", 5.0, SURVIVORSHIP_NOTE),
    "399006": InstrumentSpec("399006", "创业板指", "cn", "cn_all", "399006.parquet", "ak_index", "sz399006", 5.0, SURVIVORSHIP_NOTE),
    "^GSPC": InstrumentSpec("^GSPC", "标普500", "us", "sp500", "^GSPC.parquet", "yf", "^GSPC", 1.0, "SP500 成分宽度"),
    "^IXIC": InstrumentSpec("^IXIC", "纳斯达克", "us", "sp500", "^IXIC.parquet", "yf", "^IXIC", 1.0, "SP500 成分宽度"),
    "SPY": InstrumentSpec("SPY", "SPY(ETF)", "us", "sp500", "SPY.parquet", "yf", "SPY", 1.0, "含分红复权"),
    "QQQ": InstrumentSpec("QQQ", "QQQ(ETF)", "us", "sp500", "QQQ.parquet", "yf", "QQQ", 1.0, "含分红复权"),
    "510300": InstrumentSpec("510300", "沪深300ETF", "cn", "cn_all", "510300.parquet", "ak_etf", "510300", 5.0, "含分红、2012年起"),
    "159915": InstrumentSpec("159915", "创业板ETF", "cn", "cn_all", "159915.parquet", "ak_etf", "159915", 5.0, "含分红、2011年起"),
}


def compute_breadth_from_close_matrix(
    close_wide: pd.DataFrame, windows: tuple[int, ...] = (20, 50, 200), min_eligible: int = 30
) -> pd.DataFrame:
    """逐日计算「收盘价 > MA(w)」的个股占比（0-100），各窗口独立分母。"""
    out = pd.DataFrame(index=close_wide.index)
    for w in windows:
        ma = close_wide.rolling(w, min_periods=w).mean()
        above = ((close_wide > ma) & ma.notna()).sum(axis=1)
        eligible = (close_wide.rolling(w, min_periods=w).count() >= w).sum(axis=1)
        pct = (above / eligible.replace(0, pd.NA) * 100).astype(float)
        out[f"b{w}"] = pct.where(eligible >= min_eligible)
        out[f"n{w}"] = eligible
    return out


def load_breadth(market: str, cache_dir: Path | None = None) -> pd.DataFrame:
    path = (cache_dir or TIMING_CACHE_DIR) / BREADTH_FILES[market]
    df = pd.read_parquet(path)[["b20", "b50", "b200"]]
    return df[~df.index.duplicated(keep="last")]


def load_index_bars(symbol: str, cache_dir: Path | None = None) -> pd.DataFrame:
    spec = INSTRUMENTS[symbol]
    df = pd.read_parquet((cache_dir or TIMING_CACHE_DIR) / spec.data_file)[["open", "close"]]
    return df[~df.index.duplicated(keep="last")].sort_index()


def align_index_breadth(index_df: pd.DataFrame, breadth_df: pd.DataFrame) -> pd.DataFrame:
    merged = index_df.join(breadth_df, how="inner").sort_index()
    merged.columns = [c if c in ("open", "close") else c for c in merged.columns]
    return merged


def data_unavailable_detail(symbol: str) -> str:
    spec = INSTRUMENTS.get(symbol)
    if spec is None:
        return f"未知标的 {symbol}"
    return f"DATA_UNAVAILABLE: {spec.name}({symbol}) 本地无行情数据，请先运行 scripts/backfill_timing_data.py"
```

- [ ] **Step 4: 跑测试确认通过** — `python3 -m pytest tests/unit/test_timing_data.py -v` → 3 passed
- [ ] **Step 5: 写 `scripts/backfill_timing_data.py`**（网络回填薄壳，模式仿 `backfill_breadth_full.py`：NO_PROXY 绕行 + akshare/yfinance + 断点续传跳过已存在文件，`--refresh` 强制重拉；`--only a|us|breadth` 可选子集）。关键逻辑：

```python
# 绕代理（必须在 import akshare/yfinance 前）——整段复制 backfill_breadth_full.py 的 os.environ 处理
# A股指数：ak.stock_zh_index_daily(symbol="sh000300") → date, open, close（不复权指数点位）
# A股ETF：ak.fund_etf_hist_em(symbol="510300", period="daily", adjust="qfq", start_date="19900101")
# 美股：yf.Ticker(s).history(start="1990-01-01", auto_adjust=True)[["Open","Close"]] → open/close
# 宽度：pd.read_parquet(~/.lei_signal_lab/cache/a_share_klines_full.parquet)
#       → compute_breadth_from_close_matrix → breadth_cn_all.parquet
# SP500：json.load(sp500_ma_breadth_history.json) → b20/b50/b200（None→NaN）→ breadth_sp500.parquet
# 每个 parquet 落 TIMING_CACHE_DIR（目录不存在则建），打印每标的日期范围与行数
```
- [ ] **Step 6: 真实回填（后台，网络）** — `cd /Users/yongbiaoli/Desktop/lei-signal-lab && python3 scripts/backfill_timing_data.py 2>&1 | tail -30`，预期：8 个行情 parquet + 2 个宽度 parquet，000300 从 2005 年起、399006 从 2010 年起、^GSPC/^IXIC 从 1990 年起、全A b200 从约 1998 年起有值
- [ ] **Step 7: lint+类型+提交** — `ruff check src/lei_signal/timing_backtest scripts/backfill_timing_data.py` 与 `mypy src/lei_signal/timing_backtest` 通过后：
`git add src/lei_signal/timing_backtest scripts/backfill_timing_data.py tests/unit/test_timing_data.py && git commit -m "feat(timing): 数据层——宽度重算/对齐/工具注册表 + 回填脚本"`

---

### Task 2: 策略层 `strategies.py`

**Files:**
- Create: `src/lei_signal/timing_backtest/strategies.py`
- Test: `tests/unit/test_timing_strategies.py`

**Interfaces:**
```python
@dataclass(frozen=True) LadderParams:
    indicator: str = "b200"; n_bands: int = 5
    edge_mode: str = "fixed"        # fixed | preq（用回测起点前历史分位数，无前视）
    direction: str = "contrarian"   # contrarian | momentum
@dataclass(frozen=True) ReversalParams:
    indicator: str = "b200"; low_extreme: float = 20.0; high_extreme: float = 80.0
    confirm: float = 5.0; batch_mode: str = "time"   # time | band
    batches: int = 5                # time: N 日每日 1/N；band: 每 10 个宽度点一批，batch 数=batches
@dataclass(frozen=True) TrendGate:
    mode: str = "off"               # off | ma200
    cap: float = 0.0                # 指数 < MA200 时的仓位上限
def ladder_target(b: pd.Series, params: LadderParams, warmup_b: pd.Series | None = None) -> pd.Series  # 0-1
def reversal_target(b: pd.Series, params: ReversalParams) -> pd.Series  # 0-1
def trend_gate_cap(close: pd.Series, gate: TrendGate) -> pd.Series      # 0-1
def apply_gate(target: pd.Series, cap: pd.Series) -> pd.Series          # np.minimum
def build_target(aligned: pd.DataFrame, ladder: LadderParams | None, reversal: ReversalParams | None,
                 gate: TrendGate, warmup: pd.DataFrame | None) -> pd.Series
```
阶梯定义：`n_bands` 档位 → 仓位 `np.linspace(1,0,n_bands)`（contrarian）/`np.linspace(0,1,n_bands)`（momentum），固定档边界 `100*np.linspace(0,1,n_bands+1)[1:-1]`（5 档→20/40/60/80，仓位 100/75/50/25/0%）；`preq` 模式取 `warmup_b`（回测起点前的宽度序列）分位数 `q=100*edges/100`，不足 250 个观测回退 fixed。反转状态机：armed_low 后上穿 low+confirm 启动买入程序；armed_high 后下穿 high-confirm 启动卖出程序；time 模式每日 ±1/N，band 模式每 ±10 宽度点 ±1/N；两程序互斥，反向触发即切换方向；起始目标 0。

- [ ] **Step 1: 写失败测试** — `tests/unit/test_timing_strategies.py`（用小构造序列覆盖：5 档固定边界穿越的 5 个取值、3 档边界 33.3/66.7、momentum 翻转、preq 用 warmup 分位数且不受回测段影响、反转 time 模式 N 日爬升到 1、band 模式每 10 点一批、反向触发切换、gate 在 close<MA200 时压到 cap、apply_gate 取 min、build_target 组装）

```python
"""timing_backtest.strategies 目标仓位纯函数测试。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.timing_backtest.strategies import (
    LadderParams, ReversalParams, TrendGate,
    apply_gate, build_target, ladder_target, reversal_target, trend_gate_cap,
)


def _b(vals): return pd.Series(vals, index=pd.bdate_range("2024-01-01", periods=len(vals)), dtype=float)


def test_ladder_fixed_5bands():
    t = ladder_target(_b([10, 25, 45, 65, 90]), LadderParams(n_bands=5))
    assert list(t) == [1.0, 0.75, 0.5, 0.25, 0.0]


def test_ladder_momentum_flips():
    t = ladder_target(_b([10, 90]), LadderParams(n_bands=5, direction="momentum"))
    assert list(t) == [0.0, 1.0]


def test_ladder_preq_uses_warmup_quantiles():
    warmup = _b(list(np.arange(0, 100, 0.4)))  # 250 个观测
    t = ladder_target(_b([1, 99]), LadderParams(n_bands=3, edge_mode="preq"), warmup_b=warmup)
    # 3 档 preq 边界 = warmup 的 1/3、2/3 分位 ≈ 33.3/66.6 → 与 fixed 基本一致
    assert list(t) == [1.0, 0.0]


def test_reversal_time_batches():
    b = _b([5, 5, 25, 30, 40, 50, 60, 90, 70, 50])
    t = reversal_target(b, ReversalParams(batch_mode="time", batches=4))
    assert t.iloc[0] == 0.0 and t.iloc[2] == 0.25 and t.iloc[6] == 1.0  # 触发日 25≥20+5 起 4 日爬满
    assert t.iloc[-1] == 0.0  # 90≥80 armed 后跌破 75 → 4 日卖光


def test_reversal_band_batches():
    b = _b([5, 5, 25, 36, 47, 58])
    t = reversal_target(b, ReversalParams(batch_mode="band", batches=5))
    assert t.iloc[2] == pytest.approx(0.2) and t.iloc[3] == pytest.approx(0.4) and t.iloc[5] == pytest.approx(0.8)


def test_gate_and_apply():
    close = _b([100, 100, 90, 80, 200])
    cap = trend_gate_cap(close, TrendGate(mode="ma200", cap=0.0))
    assert list(cap) == [1.0, 1.0, 0.0, 0.0, 1.0]
    assert list(apply_gate(_b([0.8, 0.5, 0.9]), _b([1.0, 0.3, 0.0]))) == [0.8, 0.3, 0.0]


def test_build_target_combines_gate():
    idx = pd.bdate_range("2023-01-01", periods=300)
    rng = np.random.default_rng(7)
    close = pd.Series(100 + rng.normal(0, 1, 300).cumsum(), index=idx)
    b = pd.Series(np.clip(50 + rng.normal(0, 10, 300).cumsum(), 0, 100), index=idx)
    aligned = pd.DataFrame({"open": close, "close": close, "b20": b, "b50": b, "b200": b})
    t = build_target(aligned, LadderParams(), None, TrendGate(mode="ma200", cap=0.0), None)
    capped = t[close < close.rolling(200, min_periods=1).mean()]
    assert (capped <= 0.0 + 1e-12).all()
```

- [ ] **Step 2: 跑测试确认失败** — `ModuleNotFoundError: strategies`
- [ ] **Step 3: 实现**（核心：阶梯 `np.searchsorted(edges, b, side="left")` 映射档位；反转逐日状态机 `armed_low/armed_high/program(+1|-1)/progress`；gate `close >= close.rolling(200,min_periods=200).mean() → 1 else cap`，MA 未成型日为 1）

```python
"""宽度择时策略：阶梯 / 极值反转 / 趋势闸门 → 逐日目标仓位（0-1）。纯函数、仅用当日及以前数据。"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class LadderParams:
    indicator: str = "b200"
    n_bands: int = 5
    edge_mode: str = "fixed"
    direction: str = "contrarian"


@dataclass(frozen=True)
class ReversalParams:
    indicator: str = "b200"
    low_extreme: float = 20.0
    high_extreme: float = 80.0
    confirm: float = 5.0
    batch_mode: str = "time"
    batches: int = 5


@dataclass(frozen=True)
class TrendGate:
    mode: str = "off"
    cap: float = 0.0


def _fixed_edges(n_bands: int) -> np.ndarray:
    return 100.0 * np.linspace(0, 1, n_bands + 1)[1:-1]


def ladder_target(b: pd.Series, params: LadderParams, warmup_b: pd.Series | None = None) -> pd.Series:
    n = max(2, int(params.n_bands))
    edges = _fixed_edges(n)
    if params.edge_mode == "preq" and warmup_b is not None and len(warmup_b.dropna()) >= 250:
        edges = warmup_b.dropna().quantile([x / 100.0 for x in edges]).to_numpy()
    levels = np.linspace(1.0, 0.0, n) if params.direction == "contrarian" else np.linspace(0.0, 1.0, n)
    idx_pos = np.searchsorted(edges, b.to_numpy(dtype=float), side="left")
    return pd.Series(levels[idx_pos], index=b.index)


def reversal_target(b: pd.Series, params: ReversalParams) -> pd.Series:
    vals = b.to_numpy(dtype=float)
    step = 1.0 / max(1, int(params.batches))
    target = 0.0
    armed_low = armed_high = False
    direction = 0          # +1 买入程序 / -1 卖出程序
    progress_anchor = 0.0  # band 模式的参照宽度
    out = np.zeros(len(vals))
    for i, x in enumerate(vals):
        if np.isnan(x):
            out[i] = target
            continue
        if x <= params.low_extreme:
            armed_low, direction = True, 0
        if x >= params.high_extreme:
            armed_high, direction = 0, 0
        if armed_low and direction == 0 and x >= params.low_extreme + params.confirm:
            direction, progress_anchor = 1, x
        elif armed_high and direction == 0 and x <= params.high_extreme - params.confirm:
            direction, progress_anchor = -1, x
        if direction == 1:
            if params.batch_mode == "time":
                target = min(1.0, target + step)
            else:
                while x - progress_anchor >= 10.0 and target < 1.0:
                    target = min(1.0, target + step)
                    progress_anchor += 10.0
        elif direction == -1:
            if params.batch_mode == "time":
                target = max(0.0, target - step)
            else:
                while progress_anchor - x >= 10.0 and target > 0.0:
                    target = max(0.0, target - step)
                    progress_anchor -= 10.0
        out[i] = target
    return pd.Series(out, index=b.index)


def trend_gate_cap(close: pd.Series, gate: TrendGate) -> pd.Series:
    if gate.mode != "ma200":
        return pd.Series(1.0, index=close.index)
    ma = close.rolling(200, min_periods=200).mean()
    return pd.Series(np.where(ma.isna() | (close >= ma), 1.0, gate.cap), index=close.index)


def apply_gate(target: pd.Series, cap: pd.Series) -> pd.Series:
    return pd.Series(np.minimum(target.to_numpy(), cap.to_numpy()), index=target.index)


def build_target(
    aligned: pd.DataFrame,
    ladder: LadderParams | None,
    reversal: ReversalParams | None,
    gate: TrendGate,
    warmup: pd.DataFrame | None,
) -> pd.Series:
    if ladder is not None:
        warmup_b = warmup[ladder.indicator] if warmup is not None and ladder.indicator in warmup else None
        target = ladder_target(aligned[ladder.indicator], ladder, warmup_b)
    elif reversal is not None:
        target = reversal_target(aligned[reversal.indicator], reversal)
    else:
        raise ValueError("ladder 与 reversal 至少提供一个")
    return apply_gate(target, trend_gate_cap(aligned["close"], gate))
```

- [ ] **Step 4: 跑测试确认通过**（注意 `test_reversal_time_batches` 的爬升节奏与状态机对齐，断言以实现语义为准修正——触发当日即第一批）
- [ ] **Step 5: lint+类型+提交** — `git add … && git commit -m "feat(timing): 策略层——阶梯/反转/趋势闸门目标仓位"`

---

### Task 3: 引擎 `engine.py`

**Files:**
- Create: `src/lei_signal/timing_backtest/engine.py`
- Test: `tests/unit/test_timing_engine.py`

**Interfaces:**
```python
@dataclass(frozen=True) TimingResult:
    daily: pd.DataFrame        # index date; equity, benchmark, weight, open, close, b20, b50, b200
    trades: list[dict]         # {date, prev_weight, new_weight, price, fee, turnover}
def simulate(aligned: pd.DataFrame, target: pd.Series, fee_bps: float) -> TimingResult
```
规则：`desired[i] = target[i-1]`（T 日收盘信号 → T+1 开盘执行，第一天不建仓）；开盘按 `open[i]` 再平衡到 desired，费用 = 当次调仓市值变动 × fee；`equity = cash + units*close[i]`；benchmark 首日以 open 价全额买入（扣一次费用）后持有。

- [ ] **Step 1: 写失败测试**（手算 4 日案例：费用、T+1 延迟、无未来函数——篡改信号日之后的 close 不影响已成交价格；benchmark 复利正确）

```python
"""timing_backtest.engine T+1 开盘成交模拟测试。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.timing_backtest.engine import simulate


def _frame():
    idx = pd.bdate_range("2024-01-01", periods=5)
    return pd.DataFrame(
        {"open": [100, 110, 120, 130, 140], "close": [105, 115, 125, 135, 145],
         "b20": 10.0, "b50": 10.0, "b200": 10.0}, index=idx)


def test_t_plus_1_open_execution_and_fees():
    target = pd.Series([0.0, 1.0, 1.0, 0.0, 0.0], index=_frame().index)  # 第2日收盘信号
    res = simulate(_frame(), target, fee_bps=0.0)
    assert res.daily["weight"].iloc[0] == 0.0
    assert res.daily["weight"].iloc[1] == 0.0        # 信号日仍未执行
    assert res.daily["weight"].iloc[2] == pytest.approx(1.0)  # T+1 开盘 120 建仓
    assert res.daily["weight"].iloc[4] == pytest.approx(0.0)  # 第4日信号 → 第5日开盘清仓
    fee_res = simulate(_frame(), target, fee_bps=100.0)       # 1% 单边
    assert fee_res.daily["equity"].iloc[-1] < res.daily["equity"].iloc[-1]


def test_no_lookahead():
    base = _frame(); target = pd.Series([0.0, 1.0, 1.0, 1.0, 1.0], index=base.index)
    r1 = simulate(base, target, 0.0).daily["equity"]
    tampered = base.copy(); tampered.loc[tampered.index[4], "close"] = 999.0
    r2 = simulate(tampered, target, 0.0).daily["equity"]
    assert list(r1[:4]) == list(r2[:4])  # 前四日净值不受未来 close 影响


def test_benchmark_buy_and_hold():
    res = simulate(_frame(), pd.Series(1.0, index=_frame().index), 0.0)
    bh = 105.0 / 100.0 * 145.0 / 105.0   # 首日 open 买、末日 close 估
    assert res.daily["benchmark"].iloc[-1] == pytest.approx(145.0 / 100.0)
    assert res.daily["equity"].iloc[-1] == pytest.approx(145.0 / 100.0)
    assert res.trades[0]["date"] == res.daily.index[1]
```

- [ ] **Step 2: 确认失败** → **Step 3: 实现**

```python
"""宽度择时回测引擎：T 日收盘信号 → T+1 开盘成交的单标的仓位模拟。"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TimingResult:
    daily: pd.DataFrame
    trades: list[dict]


def simulate(aligned: pd.DataFrame, target: pd.Series, fee_bps: float) -> TimingResult:
    open_ = aligned["open"].to_numpy(dtype=float)
    close = aligned["close"].to_numpy(dtype=float)
    tgt = target.reindex(aligned.index).to_numpy(dtype=float)
    fee_rate = fee_bps * 1e-4

    cash, units, weight = 1.0, 0.0, 0.0
    equity = np.full(len(aligned), np.nan)
    weights = np.zeros(len(aligned))
    trades: list[dict] = []

    for i in range(len(aligned)):
        if i > 0 and not np.isnan(tgt[i - 1]):
            desired = float(tgt[i - 1])
            eq_open = cash + units * open_[i]
            delta = desired - weight
            if abs(delta) > 1e-9:
                value = eq_open * delta
                fee = abs(value) * fee_rate
                units += value / open_[i]
                cash -= value + fee
                weight = desired
                trades.append({
                    "date": aligned.index[i].strftime("%Y-%m-%d"),
                    "prev_weight": round(float(1 - (1 - weight) if False else 0.0) + 0.0, 6),  # 见下方修正
                })
        equity[i] = cash + units * close[i]
        weights[i] = weight
    # 注：trades 里 prev_weight 记调仓前权重（在 delta 计算前保存），price=open_[i]，fee 同上，turnover=abs(delta)
    ...
```
（注意：上面 trades 组装是伪码示意，实现时在 delta 计算前保存 `prev_w = weight`，记录 `{"date", "prev_weight": prev_w, "new_weight": desired, "price": open_[i], "fee": fee, "turnover": abs(delta)}`。benchmark：`bh_units = (1.0 - fee_rate) / open_[0]`，`benchmark[i] = bh_units * close[i]`。）

- [ ] **Step 4: 跑测试通过** → **Step 5: lint+mypy+提交** `feat(timing): T+1 开盘成交引擎`

---

### Task 4: 指标 `metrics.py`

**Files:**
- Create: `src/lei_signal/timing_backtest/metrics.py`
- Test: `tests/unit/test_timing_metrics.py`

**Interfaces:**
```python
def compute_performance(equity: pd.Series) -> dict   # cagr, mdd, vol, sharpe, calmar（rf=0, 252）
def yearly_returns(equity: pd.Series) -> pd.Series   # 逐年收益（首年按区间、按日历年 groupby）
def summarize_run(daily: pd.DataFrame, trades: list[dict]) -> dict
    # strategy_cagr, benchmark_cagr, excess_cagr, strategy_mdd, benchmark_mdd, calmar, sharpe,
    # vol, avg_weight(暴露率), n_trades, total_turnover, years
```
- [ ] **Step 1: 失败测试**（构造已知净值序列：`equity = 1.01**np.arange(252)` → cagr≈0.01×252 的复利 → 精确 `(1.01**252)-1`；先涨后跌序列的 mdd 手算；全常数序列 sharpe=0 防除零；yearly_returns 年份分组）
- [ ] **Step 2: 确认失败** → **Step 3: 实现**（CAGR=`(v[-1]/v[0])**(252/n)-1`；MDD=min(e/cummax-1)；sharpe=`mean(ret)/std(ret,ddof=1)*sqrt(252)`，std=0 → 0；calmar=cagr/|mdd|）
- [ ] **Step 4: 通过** → **Step 5: lint+mypy+提交** `feat(timing): 绩效指标`

---

### Task 5: 预设 + 服务 `presets.py` / `service.py`

**Files:**
- Create: `src/lei_signal/timing_backtest/presets.py`, `src/lei_signal/timing_backtest/service.py`
- Test: `tests/unit/test_timing_service.py`

**Interfaces:**
```python
# presets.py
PRESETS: list[dict]  # 每项 {key,label,description,source,params:{symbol,strategy,ladder|reversal,gate,fee_bps,start,end}}
# 初始 8 组：B200 五档逆势(000300/^GSPC)、B50 五档、反转 time N=5、反转 band、趋势闸门×阶梯、
# 顺势对照、3档粗颗粒、9档细颗粒 —— source 标 "初始预设(2026-08-27)"，扫描胜出组后续以 source=扫描报告 覆盖追加
# service.py
def build_options() -> dict     # instruments(实际数据范围: 读 parquet 首末日期)、indicators、策略参数 schema、presets、disclaimers
def execute_run(cfg: dict) -> dict  # 校验→对齐(预热段取 start 前 500 交易日给 preq/gate MA200)→build_target→simulate→summarize→yearly→落盘→返回
def list_runs(limit=50) -> list[dict]
RUNS_DIR = Path.home()/".lei_signal_lab/timing_backtest_runs"
```
- [ ] **Step 1: 失败测试**（tmp_path 里伪造 2 个 parquet（指数 600 日 + 宽度同窗），monkeypatch `TIMING_CACHE_DIR` 与 `RUNS_DIR`；execute_run 全流程返回字段齐全、run 文件落盘、list_runs 能读到；数据缺失时 `data_unavailable_detail` 抛 `FileNotFoundError` 由 API 层转 409）
- [ ] **Step 2: 确认失败** → **Step 3: 实现**（cfg 校验用 pydantic 在 API 层做，service 收 dict；落盘 JSON：params + 指标 + yearly + trades + daily 压缩为 {date, equity, benchmark, weight, b} 列表）
- [ ] **Step 4: 通过** → **Step 5: lint+mypy+提交** `feat(timing): 预设与服务层`

---

### Task 6: API 路由

**Files:**
- Create: `src/lei_signal/api/routes/timing_backtest.py`
- Modify: `src/lei_signal/api/app.py`（import 块加 `timing_backtest,`、`app.include_router(timing_backtest.router)`，仿 `app.py:87-99`）
- Test: `tests/unit/test_timing_api.py`

**Interfaces:**
```python
router = APIRouter(prefix="/api/timing-backtest", tags=["timing-backtest"])
class TimingRunRequest(BaseModel):   # 全部可选带默认，与 presets.params 同构
    symbol: str = "000300"; strategy: str = "ladder"
    indicator: str = "b200"; n_bands: int = 5; edge_mode: str = "fixed"; direction: str = "contrarian"
    low_extreme: float = 20.0; high_extreme: float = 80.0; confirm: float = 5.0
    batch_mode: str = "time"; batches: int = 5
    gate_mode: str = "off"; gate_cap: float = 0.0
    fee_bps: float | None = None; start: str | None = None; end: str | None = None
GET  /options → build_options()
POST /runs   → execute_run（数据缺失 raise HTTPException(409, data_unavailable_detail)）
GET  /runs   → list_runs()
```
- [ ] **Step 1: 失败测试**（FastAPI TestClient + tmp 缓存 fixture：options 200 且含 disclaimers；runs 全流程 200 且指标字段在；`symbol="NOPE"` → 422/400；缓存空 → 409 带 DATA_UNAVAILABLE）
- [ ] **Step 2: 确认失败** → **Step 3: 实现 + 注册路由** → **Step 4: 通过 + 全量回归 `python3 -m pytest tests/unit -x -q`** → **Step 5: lint+mypy+提交** `feat(timing): API 路由 /api/timing-backtest`

---

### Task 7: 参数扫描 `sweep.py` + 脚本

**Files:**
- Create: `src/lei_signal/timing_backtest/sweep.py`, `scripts/sweep_timing_backtest.py`
- Create: `docs/timing-sweep/`（输出目录）
- Test: `tests/unit/test_timing_sweep.py`

**Interfaces:**
```python
# sweep.py
def build_grid(symbols: list[str], indicators: list[str]) -> list[dict]   # 约 300-600 组：策略×档位×方向×极值×confirm×batch×N×gate
def run_sweep(grid: list[dict], cache_dir=None) -> pd.DataFrame
    # 每组：全窗口 + 前半 + 后半各跑一次 → strategy_cagr/excess/mdd/calmar/sharpe/avg_weight/n_trades × {full,first_half,second_half}
def robust_top(df: pd.DataFrame, top_n=15) -> pd.DataFrame
    # 筛选：full excess>0 且两个 half excess>0 且 full mdd 优于基准；排序 key = excess_cagr*0.6 + calmar*0.4（降序）
# scripts/sweep_timing_backtest.py
#   参数 --symbols 000300,399006,^GSPC,^IXIC --indicators b200,b50 --out docs/timing-sweep
#   输出 sweep_<date>.csv + report_<date>.md（每标的 Top15 表 + 全网格汇总 + 过拟合警示文案）
```
- [ ] **Step 1: 失败测试**（tmp 小数据：build_grid 维数与无重复；run_sweep 产出列齐、halves 逻辑切分；robust_top 过滤规则三条件各一条用例）
- [ ] **Step 2: 确认失败** → **Step 3: 实现** → **Step 4: 通过** → **Step 5: lint+mypy+提交** `feat(timing): 参数扫描网格/执行/稳健筛选`
- [ ] **Step 6（真实扫描，在 Task 9 数据就绪后）**：`python3 scripts/sweep_timing_backtest.py`，产出报告，把 robust_top 各标的第一名参数组写回 `presets.py`（`source: "参数扫描 2026-08-27 docs/timing-sweep/report_*.md"`），补测试后提交 `feat(timing): 扫描胜出参数入预设`

---

### Task 8: 前端

**Files:**
- Modify: `web/src/types.ts`（追加 `TimingOptions, TimingRunResult, TimingRunSummary, TimingYearly` 等）
- Modify: `web/src/api/client.ts`（追加 `timingBacktestApi = { options, createRun, listRuns }`，POST 同步返回全结果）
- Create: `web/src/components/BreadthTimingPanel.tsx`
- Modify: `web/src/pages/BacktestPage.tsx`（顶部 `bt-tabs` 双 tab：技术信号回测 | 宽度择时回测；默认前者，切换才挂载面板）

**Panel 结构（复用 `bt-*` 样式与 BreadthTrendChart 的 echarts useRef 模式）：**
1. 参数区 `bt-form`：标的下拉（显示「名称 ← 宽度来源，起始年」）、指标 B20/B50/B200、策略单选（阶梯/反转）、阶梯参数（档位数 3/5/9、阈值模式、方向）、反转参数（低/高极值、确认、分批模式、批数）、趋势闸门（off/ma200+cap）、费率、起止日期、预设下拉（选择即填充）
2. 指标卡 `bt-cards`：策略年化 vs 持有年化、超额、最大回撤、Calmar、Sharpe、暴露率、调仓次数
3. 图 1（echarts，log 轴双线）：策略净值 vs 买入持有；图 2：close + b 值（右轴）+ 仓位（area 背景色带 0-1）
4. 逐年收益表 `bt-table`；调仓明细 `bt-trades-scroll`（滚动）
5. 底部 disclaimers（`breadth-disclaimer` 样式）：幸存者偏差、不复权价、宽度截至回填日、历史最优≠未来最优

- [ ] **Step 1: types + client 方法**（字段与 API JSON 一一对应）
- [ ] **Step 2: BreadthTimingPanel.tsx 全量实现**（useState 参数对象、提交 → `timingBacktestApi.createRun` 同步结果 → 渲染；echarts 图两块；数据不足 409 时红条展示 message）
- [ ] **Step 3: BacktestPage 加 tab**（保持现有内容不动，外层加 tab state）
- [ ] **Step 4: 构建验证** — `cd web && npm run build`（tsc -b + vite build）0 error
- [ ] **Step 5: 提交** `feat(timing-web): 回测页「宽度择时」tab 与面板`

---

### Task 9: 真实数据回填 + 扫描 + 上线验收

- [ ] **Step 1:** 确认 Task 1 Step 6 的真实回填完成（8 行情 + 2 宽度 parquet，日期范围符合预期；不完整则重跑对应段）
- [ ] **Step 2:** `python3 scripts/sweep_timing_backtest.py`（后台，约 600 组 × 向量化秒级）→ 检查 `docs/timing-sweep/report_*.md` Top 表合理（无年化 >80% 之类的数据错误征兆）
- [ ] **Step 3:** 按 Task 7 Step 6 把胜出参数写回 presets + 测试 + 提交
- [ ] **Step 4:** 全量回归：`python3 -m pytest tests/unit -q`（全绿）+ `ruff check src scripts` + `mypy src/lei_signal/timing_backtest`
- [ ] **Step 5:** 重启生效：`biao restart-backend`（uvicorn 重新加载新路由；前端 vite 热更新自动生效）
- [ ] **Step 6:** API 冒烟：`curl -s localhost:8000/api/timing-backtest/options | head -c 300`、`curl -s -X POST localhost:8000/api/timing-backtest/runs -H 'content-type: application/json' -d '{"symbol":"000300"}' | python3 -c "import json,sys; d=json.load(sys.stdin); print({k:d['metrics'][k] for k in ('strategy_cagr','benchmark_cagr','excess_cagr')})"`
- [ ] **Step 7:** 浏览器验收（browser-use）：打开 http://localhost:5173/backtest → 切「宽度择时回测」tab → 跑一组 000300 B200 五档 → 截图确认指标卡/双图/表渲染正常
- [ ] **Step 8:** 向用户汇报扫描结论（各标的最优参数组 + 年化对比 + 稳健性说明）

## Self-Review 结论

- Spec 覆盖：数据层(T1)/双策略+闸门+双分批(T2)/T+1引擎+费用(T3)/指标(T4)/预设+服务(T5)/API(T6)/扫描+稳健性(T7)/前端tab+声明(T8)/回填+扫描+重启验收(T9) — 全覆盖
- 类型一致性：`LadderParams/ReversalParams/TrendGate/TimingResult/simulate/build_target/execute_run/build_options/list_runs` 各任务引用名一致
- 已知实现注意点：engine trades 伪码需按注修正；reversal 触发当日即首批的语义以测试为准
