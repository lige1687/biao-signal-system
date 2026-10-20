"""危机管理状态机事件（V4 刚崩警示 / V3 出清企稳）——环境层参考事件。

口径出处（全部为研究实证，非拍脑袋阈值）：
- ``docs/research-round5-cross-market.md`` R1-3 状态机：
  * V4 刚崩警示：``dev60 < -5%`` ∧ 宽度 20 日降幅 > 30pp → 历史后 60 日
    均值 -15%/胜率 24%，语义「补跌未完成，回避窗口 20 日」；
  * V3 出清企稳：``dev60 < -5%`` ∧ 宽度 1 年分位 ≤5% ∧ 5 日走平 → 中小盘
    后 60 日 +5~9%/胜率 67-70%，语义「出清完成，高贝塔行情，买弹性标的」。
- 宽度口径 = 全市场 %above MA50（真全A，非指数成分）。
- ``docs/research-round7-integration.md`` F3：事件类信号必须日频扫描次日
  执行——本模块在 API 请求时现算（数据均为本地日更文件），满足日频。

口径选择登记（研究文档未定量处，落地时拍板并记录）：
1. 「5 日走平」研究原文只有定性描述，落成 ``|ma50_pct 近 5 日变化| ≤ 3pp``
   （与 round5 阈值邻域网格的地底档 3pp 一致）；
2. 「1 年分位」= 近 252 个交易日点时分位（最少 120 日）；
3. V3/V4 同日同时满足时 V4 优先（更保守：先回避再看企稳）；
4. 指数范围 = 本地 K 线缓存已具备的指数（当前上证/沪深300），创业板/
   中证1000 等待缓存补齐后加入 ``CRISIS_INDEXES`` 即自动纳入。

红线：只发事件与读数，不参与 summary、不挡技术信号、不给仓位指令
（对标 ``vol_regime`` 先例）。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from lei_signal.data.cache import DEFAULT_CACHE_DIR


def _cache_root() -> Path:
    """与 a_share_breadth 同规则：LEI_CACHE_ROOT 覆盖，默认 data.cache 目录。"""
    import os

    return Path(os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR)))

#: dev60 深跌阈值（收盘相对 60 日均线偏离）。
DEV60_THRESHOLD = -5.0  # %
#: 宽度 20 日降幅阈值（pp）。
BREADTH_DROP_20 = -30.0
#: 宽度 1 年分位「地底」阈值（%）。
BREADTH_PCTILE_FLOOR = 5.0
#: 「5 日走平」判据：近 5 日宽度变化绝对值上限（pp，口径选择登记见模块注释）。
BREADTH_FLAT_5 = 3.0
#: 分位窗口（交易日）与最少样本。
_PCTILE_WINDOW = 252
_PCTILE_MIN = 120

#: 参与判定的指数（symbol → 展示名）。仅用本地 K 线缓存，缺失自动跳过。
CRISIS_INDEXES: dict[str, str] = {
    "000001.SS": "上证指数",
    "000300.SS": "沪深300",
    # 数据源补齐后加入：399006.SZ 创业板指 / 000852.SS 中证1000 / 000905.SS 中证500
    # （V3 效力随市值下沉递增——创业板 +8.58%/70% 最强，见 round5 市值梯度）。
}

_TTL_SECONDS = 300
_cache: dict[str, Any] = {"ts": 0.0, "value": None}


def _load_breadth_series() -> pd.Series | None:
    path = _cache_root() / "a_share_ma_breadth_history.json"
    if not path.is_file():
        return None
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    data = {str(r["date"]): r.get("ma50_pct") for r in rows if r.get("ma50_pct") is not None}
    if len(data) < _PCTILE_MIN:
        return None
    s = pd.Series(data, dtype=float)
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def _load_index_close(symbol: str) -> pd.Series | None:
    path = _cache_root() / f"{symbol}.bars.parquet"
    if not path.is_file():
        return None
    try:
        df = pd.read_parquet(path)
    except Exception:  # noqa: BLE001 — 单指数缺失跳过，不影响其他指数
        return None
    if "close" not in df.columns or len(df) < 60:
        return None
    s = df["close"].astype(float)
    if not isinstance(s.index, pd.DatetimeIndex):
        s.index = pd.to_datetime(s.index)
    return s.sort_index().dropna()


def _pctile_now(series: pd.Series) -> float | None:
    """最新值在近 N 日窗口内的点时分位（0-100）。"""
    window = series.dropna().iloc[-_PCTILE_WINDOW:]
    if len(window) < _PCTILE_MIN:
        return None
    current = float(window.iloc[-1])
    rank = (window <= current).sum() / len(window) * 100.0
    return round(rank, 1)


def evaluate_crisis_states() -> dict[str, Any] | None:
    """逐指数计算 V4/V3 状态。任何数据缺口返回 None（前端不显示，不报错）。"""
    breadth = _load_breadth_series()
    if breadth is None:
        return None
    b_now = float(breadth.iloc[-1])
    b20 = breadth.iloc[-21] if len(breadth) >= 21 else None
    b5 = breadth.iloc[-6] if len(breadth) >= 6 else None
    delta_20 = round(b_now - float(b20), 1) if b20 is not None and not pd.isna(b20) else None
    delta_5 = round(b_now - float(b5), 1) if b5 is not None and not pd.isna(b5) else None
    pctile = _pctile_now(breadth)
    breadth_date = breadth.index[-1].strftime("%Y-%m-%d")

    readings: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    for symbol, name in CRISIS_INDEXES.items():
        close = _load_index_close(symbol)
        if close is None:
            continue
        if len(close) < 60:
            continue
        ma60 = float(close.iloc[-60:].mean())
        last = float(close.iloc[-1])
        dev60 = round((last / ma60 - 1.0) * 100.0, 2)
        state = "none"
        deep = dev60 < DEV60_THRESHOLD
        if deep and delta_20 is not None and delta_20 < BREADTH_DROP_20:
            state = "crash_warning"  # V4 优先（口径选择 3）
        elif (
            deep
            and pctile is not None
            and pctile <= BREADTH_PCTILE_FLOOR
            and delta_5 is not None
            and abs(delta_5) <= BREADTH_FLAT_5
        ):
            state = "capitulation_rebound"
        idx_date = close.index[-1].strftime("%Y-%m-%d")
        readings.append(
            {
                "symbol": symbol,
                "name": name,
                "as_of": idx_date,
                "dev60_pct": dev60,
                "breadth_ma50_now": round(b_now, 1),
                "breadth_delta_20": delta_20,
                "breadth_pctile_1y": pctile,
                "breadth_delta_5": delta_5,
                "breadth_as_of": breadth_date,
                "state": state,
            }
        )
        if state == "crash_warning":
            alerts.append(
                {
                    "level": "danger",
                    "type": "crash_warning",
                    "title": f"V4 刚崩警示 · {name}",
                    "symbol": symbol,
                    "desc": (
                        f"深跌（dev60={dev60}%）∧ 宽度20日急坠 {delta_20}pp。"
                        "历史后60日均值约-15%、胜率24%——补跌未完成，回避窗口20日。"
                        "（研究代理，提示不挡信号）"
                    ),
                }
            )
        elif state == "capitulation_rebound":
            alerts.append(
                {
                    "level": "opportunity",
                    "type": "capitulation_rebound",
                    "title": f"V3 出清企稳 · {name}",
                    "symbol": symbol,
                    "desc": (
                        f"深跌（dev60={dev60}%）∧ 宽度1年分位仅{pctile}% ∧ 近5日走平。"
                        "历史后60日中小盘+5~9%、胜率67-70%——出清完成，高贝塔行情，"
                        "关注弹性标的。（研究代理，提示不挡信号）"
                    ),
                }
            )
    if not readings:
        return None
    return {"readings": readings, "alerts": alerts}


def get_crisis_states() -> dict[str, Any] | None:
    """TTL 缓存包装（300s）：global-strip 高频轮询路径上避免重复读文件。"""
    now = time.monotonic()
    if _cache["value"] is not None and now - _cache["ts"] < _TTL_SECONDS:
        return _cache["value"]
    value = evaluate_crisis_states()
    _cache["ts"] = now
    _cache["value"] = value
    return value


__all__ = ["CRISIS_INDEXES", "evaluate_crisis_states", "get_crisis_states"]
