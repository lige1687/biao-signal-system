"""定投状态计算：标的状态（三色/距年线/回撤/深度乖离）与市场宽度档位。

口径全部沿第十一/十五轮归档（point-in-time，无未来函数）；阈值读账本
（rules.v2 dca_state_thresholds / breadth_position，缺段回退实验原值并记录）。

数据状态按依赖分开（总控 R02 / 契约 v1.2 §2）：
- deep20（深超跌）只依赖该标的**价格**；
- bottom_zone（底部区域）还依赖**市场宽度**——宽度缺失时 bottom_zone=null
  （无法判定），不是 false（未触发），也不得拖累 deep20；
- 价格尾行 NaN：裁到最后一根有效收盘，state_status=degraded 并注明；
- 滚动窗口缺值（年线/回撤算不出）：对应字段 null，相关状态 null；
- 任何 NaN 不进 JSON（严格序列化合法）。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from lei_signal.data_provenance import (
    MarketDataRef,
    SourcePolicy,
    assess_freshness,
    file_generated_at,
    reference_calendar,
)
from lei_signal.domain.rules_config import get_rule


def _breadth_lines() -> tuple[float, float]:
    """宽度档位线：rules.v2 breadth_position.low_line/high_line（宽容回退）。"""
    try:
        rule = get_rule("breadth_position")
        low = float(rule.param("low_line"))
        high = float(rule.param("high_line"))
        if low < high:
            return low, high
    except Exception:  # noqa: BLE001 — 账本缺段回退实验默认
        pass
    return 43.3, 56.7


def _dca_thresholds() -> tuple[float, float]:
    """deep20/bottom_zone 阈值：rules.v2 dca_state_thresholds（宽容回退原值）。"""
    try:
        rule = get_rule("dca_state_thresholds")
        deep = float(rule.param("deep20_gap"))
        dd = float(rule.param("bottom_zone_dd2y"))
        if deep < 0 and dd < 0:
            return deep, dd
    except Exception:  # noqa: BLE001 — 账本缺段回退实验原值
        pass
    return -0.20, -0.15


@dataclass(frozen=True)
class TargetState:
    symbol: str
    name: str
    as_of: str                    # 最后一根有效收盘的日期
    close: float | None
    color: str | None             # green / gray / black / None（数据不足）
    ma200_gap: float | None       # 距年线（小数）；窗口不足=None
    dd2y: float | None            # 两年回撤（负小数）；窗口不足=None
    tier: str | None              # low / mid / high；宽度缺失=None
    deep20: bool | None           # 深超跌；价格不可判=None（≠False）
    bottom_zone: bool | None      # 底部区域；宽度/窗口缺=None（≠False）
    b200: float | None
    state_status: str = "ok"      # ok / insufficient_data / degraded
    window_note: str = ""         # 窗口缺值原因（P1：active=null 时说明缺什么）

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol, "name": self.name, "as_of": self.as_of,
            "close": self.close, "color": self.color,
            "ma200_gap": self.ma200_gap, "dd2y": self.dd2y,
            "tier": self.tier, "deep20": self.deep20,
            "bottom_zone": self.bottom_zone, "b200": self.b200,
            "state_status": self.state_status, "window_note": self.window_note,
        }


def compute_state(
    symbol: str,
    name: str,
    bars: pd.DataFrame | None,
    b200: float | None,
) -> TargetState:
    """由行情序列与全市场宽度 b200 计算单标的状态（口径见模块 docstring）。

    缺值处理（P1）：**只裁尾部无效值**；中间缺值保留原日期位——滚动窗口
    按日期位置计算，缺值窗口不出值（rolling(200) 默认 min_periods=200，
    窗口内有 NaN 即 NaN→None），绝不把 200 个有效值冒充 200 个交易日；
    无缺口数据与原计算逐值一致。依赖窗口缺值 → 对应状态 null 并在
    window_note 给原因。
    """
    if bars is None or len(bars) < 1 or "close" not in bars.columns:
        return TargetState(symbol, name, "", None, None, None, None, None,
                           None, None, b200, "insufficient_data")
    close_all = bars["close"].astype(float)
    # 尾部 NaN 裁剪（重复日期已在加载层去重 keep=last）；中间缺值保留
    n_tail_nan = 0
    for v in reversed(close_all.tolist()):
        if pd.isna(v):
            n_tail_nan += 1
        else:
            break
    close = close_all.iloc[: len(close_all) - n_tail_nan] if n_tail_nan else close_all
    n_valid = int(close.notna().sum())
    if n_valid < 220:
        # 有效收盘不足 220 根：什么都判不了（deep20/bottom_zone 全 null）
        return TargetState(symbol, name, "", None, None, None, None, None,
                           None, None, b200, "insufficient_data")
    notes: list[str] = []
    status = "degraded" if n_tail_nan > 0 else "ok"
    last = float(close.iloc[-1])
    ema20 = close.ewm(span=20, adjust=False).mean()
    # 200 日线：窗口内任一缺值 → NaN（min_periods=200 按**非缺值计数**，
    # 中间缺值使窗口不足 200 个有效收盘 → 不出值，不压缩窗口）
    win200 = close.iloc[-200:]
    n_gap_200 = int(win200.isna().sum())
    ma200_raw = close.rolling(200).mean().iloc[-1]
    ma200 = float(ma200_raw) if pd.notna(ma200_raw) else None
    if ma200 is None and n_gap_200 > 0:
        notes.append(f"200日窗口缺 {n_gap_200} 个收盘，年线/距年线不可判")
    dd2y_raw = close.rolling(500, min_periods=100).max().iloc[-1]
    dd2y = (float(last / dd2y_raw - 1.0)
            if pd.notna(dd2y_raw) and dd2y_raw else None)
    if dd2y is None:
        notes.append("两年回撤窗口有效值不足 100，不可判")
    gap = float(last / ma200 - 1.0) if ma200 else None
    prev20_raw = close.iloc[-21] if len(close) > 21 else None
    prev20 = (float(prev20_raw)
              if prev20_raw is not None and pd.notna(prev20_raw) else None)
    if prev20 is not None and pd.notna(ema20.iloc[-1]):
        if last > ema20.iloc[-1] and last > prev20:
            color = "green"
        elif last < ema20.iloc[-1] and last < prev20:
            color = "black"
        else:
            color = "gray"
    else:
        color = None
        if prev20 is None:
            notes.append("20日前收盘缺值，三色不可判")
    low, high = _breadth_lines()
    if b200 is None:
        tier = None
    elif b200 < low:
        tier = "low"
    elif b200 > high:
        tier = "high"
    else:
        tier = "mid"
    deep_thr, dd_thr = _dca_thresholds()
    deep20 = bool(gap is not None and gap <= deep_thr) if gap is not None else None
    if tier is None or dd2y is None or gap is None:
        bottom = None      # 宽度或窗口缺失：无法判定（null），不是未触发
    else:
        bottom = bool(tier == "low" and dd2y <= dd_thr and gap < 0)
    if notes:
        status = "degraded"
    return TargetState(symbol, name, str(close.index[-1].date()), last, color,
                       gap, dd2y, tier, deep20, bottom, b200, status,
                       "；".join(notes))


def default_data_loader() -> Callable[[str], pd.DataFrame | None]:
    """默认行情加载：timing 缓存（与定投实验同口径）；失败返回 None 不阻断。"""
    from lei_signal.timing_backtest.data import load_index_bars

    def _load(symbol: str) -> pd.DataFrame | None:
        try:
            return load_index_bars(symbol)
        except Exception:  # noqa: BLE001 — 缺数据标的状态置空，不阻断接口
            return None
    return _load


@dataclass(frozen=True)
class BreadthReading:
    """宽度读数 + 元信息：值与它的日期、健康状况一起走，值不裸奔。"""

    market: str                # cn_all / sp500（timing 缓存市场键）
    value: float | None        # 最后有效 b200（NaN 尾行不冒充有效值）
    source: str
    observed_at: str | None    # 文件最后一行日期（可能是 NaN 行）
    last_valid_at: str | None  # 最后有效值日期（口径基准）
    generated_at: str | None
    health: str                # fresh/stale/incomplete/missing/unknown
    reason: str = ""
    reference_lag_trading_days: int | None = None
    calendar_ref: dict | None = None
    as_of_cutoff: str | None = None

    def meta(self, instrument_id: str | None = None) -> MarketDataRef:
        return MarketDataRef(
            source_id=self.source,
            instrument_id=instrument_id or f"MKT:{self.market}",
            market=self.market,
            observed_at=self.observed_at,
            available_at=None,   # 来源发布可用时间未核实（01D 审计后登记）
            generated_at=self.generated_at,
            last_valid_at=self.last_valid_at,
            health=self.health,
            reason=self.reason,
            calendar_ref=self.calendar_ref,
            as_of_cutoff=self.as_of_cutoff,
            source_policy_ref=None,  # 无已核实发布策略
            reference_lag_trading_days=self.reference_lag_trading_days,
            extra={"market_key": self.market, "value": self.value},
        )


def read_breadth(
    market: str = "cn_all",
    cache_dir=None,
    *,
    policy: SourcePolicy | None = None,
    now=None,
) -> BreadthReading:
    """读全市场宽度 b200：值取最后有效行（跳过 NaN 尾行），日期与值一起返回。

    - 尾行 NaN：value 用最后一个有效值，observed_at ≠ last_valid_at 可识别；
    - 尾部长期 NaN（>=5 行）：health=incomplete（数据形状缺陷，单列）；
    - 文件缺失/列缺失：health=missing，value=None；
    - 新鲜度按 assess_freshness（无已核实发布策略时=unknown，不默认当前）。
    """
    from lei_signal.timing_backtest import data as timing_data

    file_name = timing_data.BREADTH_FILES.get(market, f"breadth_{market}.parquet")
    path = (Path(cache_dir) if cache_dir else timing_data.TIMING_CACHE_DIR) / file_name
    cal_market = "us" if market == "sp500" else "cn"
    if not path.is_file():
        return BreadthReading(market, None, file_name, None, None, None,
                              "missing", "宽度文件缺失")
    try:
        df = timing_data.load_breadth(market, cache_dir=cache_dir)
        s = df["b200"] if "b200" in df.columns else None
        if s is None:
            return BreadthReading(market, None, file_name, None, None,
                                  file_generated_at(path), "missing",
                                  "宽度文件无 b200 列")
        observed = str(df.index[-1].date()) if len(df.index) else None
        valid = s.dropna()
        if valid.empty:
            return BreadthReading(market, None, file_name, observed, None,
                                  file_generated_at(path), "incomplete",
                                  "整列无有效值")
        last_valid = str(valid.index[-1].date())
        value = float(valid.iloc[-1])
        assessment = assess_freshness(
            last_valid, cal_market, now=now, policy=policy,
            calendar=reference_calendar(cal_market))
        health, reason = assessment.health, assessment.reason
        tail_nan = 0
        for v in reversed(s.tolist()):
            if pd.isna(v):
                tail_nan += 1
            else:
                break
        if tail_nan >= 5:
            health = "incomplete"
            reason = f"尾部连续 {tail_nan} 行 NaN（有效值停在 {last_valid}）；{reason}"
        elif tail_nan > 0:
            reason = f"尾部 {tail_nan} 行 NaN（值取 {last_valid}）；{reason}"
        return BreadthReading(
            market, value, file_name, observed, last_valid,
            file_generated_at(path), health, reason,
            assessment.reference_lag_trading_days,
            assessment.calendar.to_dict() if assessment.calendar else None,
            assessment.as_of_cutoff)
    except Exception as e:  # noqa: BLE001 — 读失败按 missing 降级，不阻断接口
        return BreadthReading(market, None, file_name, None, None, None,
                              "missing", f"读取失败: {e}")


def latest_breadth(market: str = "cn_all") -> float | None:
    """全市场宽度 b200 最新有效读数（只回值；带日期请用 read_breadth）。"""
    return read_breadth(market).value
