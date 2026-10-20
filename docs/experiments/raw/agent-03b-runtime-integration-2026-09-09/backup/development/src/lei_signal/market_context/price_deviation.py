"""偏离度分位提醒：把「过热/超跌」从定性变成可回测的路牌（文主任增量 #3）。

口径（research_proxy，2026-09-05 文主任调研）：
  - 偏离度 = close/EMA(N) − 1（N=20/60/200，只用当日及此前数据）；
  - 换算 3 年/5 年滚动分位（点时可见，无前视）；样本不足如实标注；
  - 分位 ≥95% 或 ≤5% 视为极端日；连续极端 ≥3 天 → 落库一条提醒；
  - 参照初值（+15%/+13% 等）只进文案提示，不作触发条件（A 股是否成立待自测）。

性质（红线）：路牌——只预警、不必然反向；高偏离可磨 3-6 个月才回归，给不出
买卖点；不参与任何模块触发、不作反向信号、不进 tradability_gate。

数据/落库：本地指数 bars 缓存（无网络依赖）；提醒历史落 JSON 磁盘文件
（照 a_share_breadth 冻结快照模式，按 (date, symbol, ma_window) 去重追加）。
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from lei_signal.data.cache import DEFAULT_CACHE_DIR
from lei_signal.domain.rules_config import get_rule
from lei_signal.market_context.vulnerability import rolling_percentile

logger = logging.getLogger(__name__)

ROOT = Path(os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR)))
RULE_ID = "deviation_percentile_alert"

DISCLAIMER_CN = (
    "研究代理（文主任调研 2026-09-05）：偏离度=价格距离均线的远近，分位=当前"
    "偏离在近 3 年历史里排多高（95% 比近 3 年 95% 的时候都高）。分位极端只说明"
    "「历史上少见」，不构成买卖点——高偏离可以磨 3-6 个月才回归。只预警、"
    "不必然反向；阈值与参照初值待 A 股数据自测校准。"
)


@dataclass
class DeviationReading:
    """单个指数 × 单条均线的偏离读数。"""

    symbol: str
    name_cn: str
    ma_window: int
    as_of: str
    deviation_pct: float | None       # close/EMA(N)−1（%）
    percentile_3y: float | None       # 0-100；样本不足为 None
    percentile_5y: float | None
    consecutive_extreme_days: int     # 截至今日连续处于极端分位的天数
    extreme_direction: str | None     # high=过热警戒 / low=超跌机会 / None
    data_status: str                  # ok | partial | unavailable
    note_cn: str = ""


@dataclass
class DeviationAlert:
    """一条提醒（连续极端达标后落库）。"""

    date: str
    symbol: str
    name_cn: str
    ma_window: int
    direction: str                    # overheat / oversold
    percentile: float | None
    consecutive_days: int
    message_cn: str


def _params() -> dict:
    spec = get_rule(RULE_ID)
    symbols = list(spec.param("watch_symbols", ["000001.SS"]))
    names = list(spec.param("watch_names_cn", symbols))
    return {
        "ma_windows": [int(w) for w in spec.param("ma_windows", [20, 60, 200])],
        "percentile_windows": [int(w) for w in spec.param("percentile_windows", [756, 1260])],
        "percentile_min_periods": int(spec.param("percentile_min_periods", 250)),
        "extreme_high": float(spec.param("extreme_high", 0.95)),
        "extreme_low": float(spec.param("extreme_low", 0.05)),
        "consecutive_days_min": int(spec.param("consecutive_days_min", 3)),
        "watch": dict(zip(symbols, names, strict=True)),
        "overheat_reference_pct": dict(spec.param("overheat_reference_pct", {}) or {}),
    }


# ── 纯函数（单测覆盖对象）───────────────────────────────────────────────

def ema_deviation_series(close: pd.Series, window: int) -> pd.Series:
    """close/EMA(window)−1（小数）。与 features 层同 EMA 口径（首窗口 SMA 种子）。"""
    ema = close.ewm(span=window, adjust=False).mean()
    return close / ema - 1.0


def consecutive_extreme_days(
    pct_series: pd.Series, high: float, low: float
) -> tuple[int, str | None]:
    """从末尾往前数连续极端天数；方向由最后一日决定。

    pct_series 为 0-100 百分位序列（可能含 NaN，中断即止）。
    返回 (天数, 方向 high/low/None)。
    """
    if pct_series.empty or pd.isna(pct_series.iloc[-1]):
        return 0, None
    last = float(pct_series.iloc[-1])
    direction = "high" if last >= high * 100.0 else ("low" if last <= low * 100.0 else None)
    if direction is None:
        return 0, None
    days = 0
    for value in reversed(pct_series.tolist()):
        if pd.isna(value):
            break
        v = float(value)
        is_extreme = v >= high * 100.0 or v <= low * 100.0
        if not is_extreme:
            break
        days += 1
    return days, direction


def build_reading(
    close: pd.Series,
    *,
    symbol: str,
    name_cn: str,
    ma_window: int,
    params: dict,
) -> DeviationReading:
    """单指数单均线读数（含分位与连续极端天数）。"""
    if len(close) < ma_window + 1:
        return DeviationReading(
            symbol=symbol, name_cn=name_cn, ma_window=ma_window,
            as_of=str(close.index[-1].date()) if len(close) else "",
            deviation_pct=None, percentile_3y=None, percentile_5y=None,
            consecutive_extreme_days=0, extreme_direction=None,
            data_status="unavailable",
            note_cn=f"本地日线不足 {ma_window + 1} 根，无法计算",
        )
    dev = ema_deviation_series(close, ma_window) * 100.0
    windows = params["percentile_windows"]
    min_periods = params["percentile_min_periods"]
    pcts = {
        w: rolling_percentile(dev.dropna(), w, min_periods) for w in windows
    }
    # 主分位：3 年窗口优先，样本不足退 5 年（更长窗口反而更可能不足，此处按
    # 规则账本顺序取第一个可用；都不可用时极端天数=0）
    primary = pcts[windows[0]]
    if primary.dropna().empty and len(windows) > 1:
        primary = pcts[windows[1]]
    days, direction = consecutive_extreme_days(
        primary, params["extreme_high"], params["extreme_low"]
    )
    dev_last = float(dev.iloc[-1])
    usable = len(dev.dropna())
    notes: list[str] = []
    status = "ok"
    label_3y = f"{windows[0] // 252}年"
    if usable < windows[0]:
        status = "partial"
        notes.append(
            f"本地历史 {usable} 日不足{label_3y}窗口，分位按可用样本计算（参考性降低）"
        )
    return DeviationReading(
        symbol=symbol, name_cn=name_cn, ma_window=ma_window,
        as_of=str(close.index[-1].date()),
        deviation_pct=round(dev_last, 2),
        percentile_3y=(
            round(float(pcts[windows[0]].iloc[-1]), 1)
            if windows[0] in pcts and not pd.isna(pcts[windows[0]].iloc[-1]) else None
        ),
        percentile_5y=(
            round(float(pcts[windows[1]].iloc[-1]), 1)
            if len(windows) > 1 and windows[1] in pcts
            and not pd.isna(pcts[windows[1]].iloc[-1]) else None
        ),
        consecutive_extreme_days=days,
        extreme_direction=direction,
        data_status=status,
        note_cn="；".join(notes),
    )


def _alert_message(
    reading: DeviationReading, percentile: float | None, params: dict
) -> str:
    """说人话且方向感克制的提醒文案。"""
    window_cn = f"{reading.ma_window} 日线"
    if reading.extreme_direction == "high":
        ref = params["overheat_reference_pct"].get(reading.symbol)
        ref_cn = f"（文主任参照初值 +{ref:g}%，待校准）" if ref else ""
        return (
            f"{reading.name_cn}高于{window_cn}的偏离达到历史分位 "
            f"{percentile:.0f}%，已连续 {reading.consecutive_extreme_days} 天"
            f"{ref_cn}——历史上此状态常伴随阶段性过热，仅预警，不是卖点。"
        )
    return (
        f"{reading.name_cn}低于{window_cn}的偏离打到历史分位 "
        f"{percentile:.0f}% 的极端低位，已连续 {reading.consecutive_extreme_days} 天"
        "——历史上此状态接近超跌机会区，仅预警，不是买点。"
    )


def evaluate_alerts(
    readings: list[DeviationReading], params: dict
) -> list[DeviationAlert]:
    """连续极端天数达标（≥ consecutive_days_min）的读数 → 提醒。"""
    alerts: list[DeviationAlert] = []
    for r in readings:
        if r.consecutive_extreme_days < params["consecutive_days_min"]:
            continue
        pct = r.percentile_3y if r.percentile_3y is not None else r.percentile_5y
        direction = "overheat" if r.extreme_direction == "high" else "oversold"
        alerts.append(
            DeviationAlert(
                date=r.as_of, symbol=r.symbol, name_cn=r.name_cn,
                ma_window=r.ma_window, direction=direction, percentile=pct,
                consecutive_days=r.consecutive_extreme_days,
                message_cn=_alert_message(r, pct, params),
            )
        )
    return alerts


# ── 落库（JSON 磁盘，按 date+symbol+window 去重追加）────────────────────

def _alerts_path() -> Path:
    return ROOT / "price_deviation_alerts.json"


def load_alert_history(limit: int = 200) -> list[dict]:
    p = _alerts_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data[-limit:] if isinstance(data, list) else []
    except Exception:  # noqa: BLE001
        return []


def persist_alerts(alerts: list[DeviationAlert]) -> int:
    """追加提醒历史（同 date+symbol+ma_window 只保留一条）。返回新增条数。"""
    if not alerts:
        return 0
    existing = load_alert_history(limit=100000)
    seen = {(a.get("date"), a.get("symbol"), a.get("ma_window")) for a in existing}
    added = 0
    for alert in alerts:
        key = (alert.date, alert.symbol, alert.ma_window)
        if key in seen:
            continue
        existing.append(asdict(alert))
        seen.add(key)
        added += 1
    existing.sort(key=lambda a: (a.get("date", ""), a.get("symbol", "")))
    try:
        _alerts_path().parent.mkdir(parents=True, exist_ok=True)
        _alerts_path().write_text(
            json.dumps(existing, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("偏离度提醒落库失败: %s", exc)
        return 0
    return added


# ── 读取入口 ────────────────────────────────────────────────────────────

_TTL = 300.0
_cache: dict[str, tuple[float, dict]] = {}
_lock = threading.Lock()


def _load_index_close(symbol: str) -> pd.Series:
    path = ROOT / f"{symbol}.bars.parquet"
    if not path.exists():
        return pd.Series(dtype=float)
    try:
        df = pd.read_parquet(path)
        if "close" not in df.columns:
            return pd.Series(dtype=float)
        s = df["close"].astype(float)
        if isinstance(df.index, pd.DatetimeIndex):
            s.index = df.index
        return s.sort_index()
    except Exception as exc:  # noqa: BLE001
        logger.warning("指数日线读取失败 %s: %s", symbol, exc)
        return pd.Series(dtype=float)


def get_price_deviation(refresh: bool = False) -> dict:
    """当前全部监控指数的偏离读数 + 活跃提醒（+落库）。TTL 缓存。"""
    now = time.time()
    if not refresh:
        cached = _cache.get("v")
        if cached and now - cached[0] < _TTL:
            return cached[1]
    with _lock:
        if not refresh:
            cached = _cache.get("v")
            if cached and now - cached[0] < _TTL:
                return cached[1]
        params = _params()
        readings: list[DeviationReading] = []
        for symbol, name_cn in params["watch"].items():
            close = _load_index_close(symbol)
            if close.empty:
                readings.append(
                    DeviationReading(
                        symbol=symbol, name_cn=name_cn, ma_window=0,
                        as_of="", deviation_pct=None, percentile_3y=None,
                        percentile_5y=None, consecutive_extreme_days=0,
                        extreme_direction=None, data_status="unavailable",
                        note_cn="本地 bars 缓存无此指数日线",
                    )
                )
                continue
            for ma_window in params["ma_windows"]:
                readings.append(
                    build_reading(
                        close, symbol=symbol, name_cn=name_cn,
                        ma_window=ma_window, params=params,
                    )
                )
        alerts = evaluate_alerts(readings, params)
        persisted = persist_alerts(alerts)
        if persisted:
            logger.info("偏离度提醒落库 %d 条", persisted)
        payload = {
            "as_of": max((r.as_of for r in readings if r.as_of), default=""),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "readings": [asdict(r) for r in readings],
            "active_alerts": [asdict(a) for a in alerts],
            "alert_history": load_alert_history(limit=50),
            "disclaimer_cn": DISCLAIMER_CN,
        }
        _cache["v"] = (time.time(), payload)
        return payload


__all__ = [
    "DISCLAIMER_CN",
    "DeviationAlert",
    "DeviationReading",
    "build_reading",
    "consecutive_extreme_days",
    "ema_deviation_series",
    "evaluate_alerts",
    "get_price_deviation",
    "load_alert_history",
    "persist_alerts",
]
