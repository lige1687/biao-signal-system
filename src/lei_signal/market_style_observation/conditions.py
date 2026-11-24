"""Descriptive market risk, with the existing realized-volatility definition."""

from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from lei_signal.research.definitions import realized_volatility

OVERLAY_URL = "http://127.0.0.1:8000/api/fundamentals/overlay-history?years=20"
NFCI_SOURCE = "https://fred.stlouisfed.org/series/NFCI"
NFCI_METHOD = "https://www.chicagofed.org/research/data/nfci/current-data"
NFCI_HISTORY = Path(__file__).resolve().parents[3] / "web/public/research/observation-library-20261026/reused-series.json"

# Fallback only: five published observations read on 2026-10-21.
NFCI = {
    "dates": ["2026-09-11", "2026-09-18", "2026-09-25", "2026-10-02", "2026-10-09"],
    "values": [-0.536, -0.527, -0.517, -0.507, -0.499],
    "observation_date": "2026-10-09",
    "published_at": "2026-10-15T12:36:00Z",
    "verified_at": "2026-10-21",
    "source_url": NFCI_SOURCE,
    "method_url": NFCI_METHOD,
    "coverage": "仅已核的最近5周；完整历史与自动更新尚未接通，历史可能修订。",
    "reading": "仍低于历史平均水平，近四周上升0.037：条件相对平均仍宽松，但向收紧方向移动。",
}


def nfci_observation() -> dict:
    """Read the two-year FRED NFCI snapshot maintained with the observation cards."""
    try:
        series = json.loads(NFCI_HISTORY.read_text())["series"]["nfci"]
        points = series["points"]
        if len(points) < 52:
            return NFCI
        dates = [point["date"] for point in points]
        values = [float(point["value"]) for point in points]
        latest, previous = points[-1], points[-2]
        published = date.fromisoformat(latest["date"]) + timedelta(days=5)
        return {
            **NFCI,
            "dates": dates,
            "values": values,
            "observation_date": latest["date"],
            "published_at": f"{published.isoformat()}T12:30:00Z",
            "verified_at": series.get("verifiedAt", date.today().isoformat()),
            "coverage": f"近两年周频 {dates[0]} 至 {dates[-1]}（{len(dates)}周）；历史会修订。",
            "reading": f"最新 {latest['value']:.3f}，较上周 {latest['value'] - previous['value']:+.3f}；负值表示相对长期平均偏宽松。",
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return NFCI


def market_volatility(payload: dict | None, market: str) -> dict:
    key, label = ("sse", "上证指数") if market == "cn" else ("sp500", "标普500")
    source = (payload or {}).get("series", {}).get(key, {})
    dates, prices = source.get("dates", []), source.get("values", [])
    result = {"name": label, "unit": "%", "dates": [], "rv20": [], "rv60": [],
              "source_url": OVERLAY_URL, "available": False,
              "definition": "每日简单收益的样本标准差 × √252；20/60个日收益，需21/61个收盘价。沿用本系统既有计算。",
              "limitation": "价格指数的已实现波动，不是未来预测或全市场个股平均；缺值不填补，交易日完整性未另核。"}
    if len(dates) != len(prices) or len(dates) < 21:
        return result
    try:
        if any(not isinstance(d, str) or date.fromisoformat(d).isoformat() != d for d in dates):
            return result
    except (ValueError, TypeError):
        return result
    if dates != sorted(set(dates)):
        return result
    clean = [float(v) if isinstance(v, (int, float)) and not isinstance(v, bool)
             and math.isfinite(v) and v > 0 else math.nan for v in prices]
    index = pd.Series(clean, index=dates, dtype=float)
    def values(window):
        # The shared definition removes invalid prices. Mask windows against the
        # original dated observations so this display never bridges a missing day.
        complete = index.notna().rolling(window + 1, min_periods=window + 1).sum().eq(window + 1)
        measured = realized_volatility(index, window=window).where(complete)
        return [float(v) * 100 if math.isfinite(v) else None
                for v in measured]
    v20, v60 = values(20), values(60)
    # Three years displayed; calculations retain preceding observations.
    cutoff = (date.fromisoformat(dates[-1]).toordinal() - 1095)
    first = next(i for i, d in enumerate(dates) if date.fromisoformat(d).toordinal() >= cutoff)
    result.update(dates=dates[first:], rv20=v20[first:], rv60=v60[first:],
                  observation_date=dates[-1], available=v20[-1] is not None,
                  latest20=v20[-1], latest60=v60[-1])
    return result
