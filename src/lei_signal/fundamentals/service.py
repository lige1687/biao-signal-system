"""基本面参考层组装服务：TTL 缓存 + 单项降级。

降级原则：任何一个数据源挂了，其余照常返回，失败项进 errors 列表，
页面局部可用 —— 参考层绝不能因为一个接口超时而整页空白。
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from lei_signal.fundamentals import sources

# 板块行情/资金流变化快，缓存 5 分钟；宏观指标月更，缓存 6 小时；国债 1 小时；VIX 30 分钟。
_BOARDS_TTL = 300
_MACRO_TTL = 6 * 3600
_FLOW_TTL = 300
_TREASURY_TTL = 3600
_VIX_TTL = 1800
_MARGIN_TTL = 3600
_COMMODITY_TTL = 1800
_ETF_TTL = 3600
_OVERLAY_TTL = 12 * 3600


class _TtlCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, tuple[float, Any]] = {}

    def get_or_load(self, key: str, ttl: int, loader: Callable[[], Any]) -> tuple[Any, bool]:
        """返回 (value, fresh)。fresh=True 表示本次是新拉取的。"""
        now = time.monotonic()
        with self._lock:
            hit = self._items.get(key)
        if hit is not None and now - hit[0] < ttl:
            return hit[1], False
        value = loader()
        with self._lock:
            self._items[key] = (now, value)
        return value, True

    def invalidate(self, prefix: str | None = None) -> None:
        with self._lock:
            if prefix is None:
                self._items.clear()
            else:
                for key in [k for k in self._items if k.startswith(prefix)]:
                    del self._items[key]


class FundamentalsService:
    def __init__(self) -> None:
        self._cache = _TtlCache()

    def overview(self, *, refresh: bool = False) -> dict[str, Any]:
        if refresh:
            self._cache.invalidate()
        errors: list[str] = []

        boards: list[dict[str, Any]] = []
        try:
            boards, _ = self._cache.get_or_load(
                "boards", _BOARDS_TTL, sources.fetch_industry_boards
            )
        except sources.FundamentalsSourceError as exc:
            errors.append(f"行业板块: {exc}")

        macro: list[dict[str, Any]] = []
        for key, loader in (
            ("pmi", sources.fetch_pmi),
            ("cpi", sources.fetch_cpi),
            ("ppi", sources.fetch_ppi),
        ):
            try:
                item, _ = self._cache.get_or_load(f"macro:{key}", _MACRO_TTL, loader)
                macro.append(item)
            except sources.FundamentalsSourceError as exc:
                errors.append(f"宏观 {key}: {exc}")

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "macro": macro,
            "boards": boards,
            "board_count": len(boards),
            "errors": errors,
            "disclaimer_cn": "基本面参考层：数据来自公开数据源，仅供研究参考，"
            "不参与 LEI 技术信号判定，不构成投资建议。",
        }

    def industry_flow(self, code: str, *, days: int = 20) -> dict[str, Any]:
        days = max(5, min(days, 60))
        points, _ = self._cache.get_or_load(
            f"flow:{code}:{days}", _FLOW_TTL, lambda: sources.fetch_industry_flow(code, days=days)
        )
        return {"code": code, "days": days, "points": points}

    def rates(self, *, refresh: bool = False) -> dict[str, Any]:
        """利率 + 资金面板：中美国债 + 中美利差 + VIX + 两融余额。单项失败降级。"""
        if refresh:
            self._cache.invalidate("treasury")
            self._cache.invalidate("vix")
            self._cache.invalidate("margin")
        errors: list[str] = []
        treasury: dict[str, Any] = {}
        try:
            treasury, _ = self._cache.get_or_load("treasury", _TREASURY_TTL, sources.fetch_treasury)
        except sources.FundamentalsSourceError as exc:
            errors.append(f"国债: {exc}")

        vix: dict[str, Any] | None = None
        try:
            vix, _ = self._cache.get_or_load("vix", _VIX_TTL, sources.fetch_vix)
        except sources.FundamentalsSourceError as exc:
            errors.append(f"VIX: {exc}")

        margin: dict[str, Any] | None = None
        try:
            margin, _ = self._cache.get_or_load("margin", _MARGIN_TTL, sources.fetch_margin)
        except sources.FundamentalsSourceError as exc:
            errors.append(f"两融: {exc}")

        return {
            "treasury": treasury,
            "vix": vix,
            "margin": margin,
            "errors": errors,
        }

    def rates_history(self, *, lookback_days: int = 730) -> dict[str, Any]:
        """宏观利率/VIX/两融 历史时间序列，供趋势图使用。单项失败降级。

        返回 {series: {key: {label, unit, dates[], values[]}}, errors[]}。
        各序列独立取数、独立降级——某一项拉不到不影响其余。
        """
        errors: list[str] = []
        treasury_hist: dict[str, dict[str, float | None]] = {}
        vix_hist: dict[str, float] = {}
        margin_hist: dict[str, dict[str, float | None]] = {}

        try:
            treasury_hist, _ = self._cache.get_or_load(
                "treasury_hist",
                _TREASURY_TTL,
                lambda: sources.fetch_treasury_history(lookback_days),
            )
        except sources.FundamentalsSourceError as exc:
            errors.append(f"国债历史: {exc}")
        try:
            vix_hist, _ = self._cache.get_or_load(
                "vix_hist", _VIX_TTL, lambda: sources.fetch_vix_history(lookback_days)
            )
        except sources.FundamentalsSourceError as exc:
            errors.append(f"VIX历史: {exc}")
        try:
            margin_hist, _ = self._cache.get_or_load(
                "margin_hist", _MARGIN_TTL, sources.fetch_margin_history
            )
        except sources.FundamentalsSourceError as exc:
            errors.append(f"两融历史: {exc}")

        def mk(label: str, unit: str, dvals: dict[str, float | None]) -> dict[str, Any]:
            items = sorted((d, v) for d, v in dvals.items() if v is not None)
            return {
                "label": label,
                "unit": unit,
                "dates": [d for d, _ in items],
                "values": [round(float(v), 2) for _, v in items],
            }

        us10 = {d: v.get("us_10y") for d, v in treasury_hist.items() if v.get("us_10y") is not None}
        cn10 = {d: v.get("cn_10y") for d, v in treasury_hist.items() if v.get("cn_10y") is not None}
        spread = {d: round(cn10[d] - us10[d], 2) for d in cn10 if d in us10}
        margin_series = {
            d: v.get("rzrqye_yi") for d, v in margin_hist.items() if v.get("rzrqye_yi") is not None
        }
        margin_zb_series = {
            d: v.get("rzyezb_pct")
            for d, v in margin_hist.items()
            if v.get("rzyezb_pct") is not None
        }

        series = {
            "us_10y": mk("美10Y", "%", us10),
            "cn_10y": mk("中10Y", "%", cn10),
            "cn_us_spread_10y": mk("中美10Y利差", "%", spread),
            "vix": mk("VIX", "", vix_hist),
            "margin_rzrqye": mk("两融余额", "亿", margin_series),
            "margin_rzyezb": mk("融资余额占流通市值比", "%", margin_zb_series),
        }
        as_of = max((s["dates"][-1] for s in series.values() if s["dates"]), default="")
        return {"as_of": as_of, "series": series, "errors": errors}

    def macro_history(self, *, page_size: int = 60) -> dict[str, Any]:
        """PMI/CPI/PPI 月度历史序列，供趋势图。单项失败降级。

        返回 {series: {key: {label, unit, dates[], values[]}}, errors[]}。
        """
        errors: list[str] = []
        series: dict[str, Any] = {}

        def mk(label: str, unit: str, points: list[dict[str, Any]]) -> dict[str, Any]:
            return {
                "label": label,
                "unit": unit,
                "dates": [p["date"] for p in points],
                "values": [round(float(p["value"]), 2) for p in points],
            }

        for key, label, unit, loader in (
            ("pmi", "制造业 PMI", "", sources.fetch_pmi_history),
            ("cpi", "CPI 同比", "%", sources.fetch_cpi_history),
            ("ppi", "PPI 同比", "%", sources.fetch_ppi_history),
        ):
            try:
                points, _ = self._cache.get_or_load(
                    f"macro_hist:{key}",
                    _MACRO_TTL,
                    lambda fn=loader: fn(page_size=page_size),
                )
                series[key] = mk(label, unit, points)
            except sources.FundamentalsSourceError as exc:
                errors.append(f"宏观历史 {key}: {exc}")

        as_of = max((s["dates"][-1] for s in series.values() if s["dates"]), default="")
        return {"as_of": as_of, "series": series, "errors": errors}

    def overlay_history(self, *, years: int = 20) -> dict[str, Any]:
        """长周期叠加序列：国债收益率 / 两融占比 × 股指（20 年级），单项失败降级。

        供「利率 × 股指」带 dataZoom 的大图：左轴指数、右轴收益率/占比。
        数据源：国债/两融沿用东财（翻页取全史），A 股指数腾讯、美指 FRED。
        日频全史 ~5000 点，缓存 12 小时。
        """
        years = max(1, min(int(years), 30))
        lookback = years * 365 + 30
        errors: list[str] = []
        series: dict[str, Any] = {}

        def mk(label: str, unit: str, dvals: dict[str, float]) -> dict[str, Any]:
            items = sorted(dvals.items())
            return {
                "label": label,
                "unit": unit,
                "dates": [d for d, _ in items],
                "values": [round(v, 2) for _, v in items],
            }

        def load(cache_key: str, loader: Callable[[], dict[str, float]]) -> dict[str, float]:
            data, _ = self._cache.get_or_load(f"overlay:{cache_key}:{years}", _OVERLAY_TTL, loader)
            return data

        # 国债（中/美 10Y，同一接口一次取出）
        try:
            treasury = load("treasury", lambda: sources.fetch_treasury_history(lookback))
            series["cn_10y"] = mk(
                "中国 10Y",
                "%",
                {d: v["cn_10y"] for d, v in treasury.items() if v.get("cn_10y") is not None},
            )
            series["us_10y"] = mk(
                "美国 10Y",
                "%",
                {d: v["us_10y"] for d, v in treasury.items() if v.get("us_10y") is not None},
            )
        except sources.FundamentalsSourceError as exc:
            errors.append(f"国债长史: {exc}")

        # 两融占比 + 绝对余额（全史约 3,977 交易日，2026-08 实测）
        try:
            margin = load("margin", lambda: sources.fetch_margin_history(min(lookback, 4000)))
            series["margin_rzyezb"] = mk(
                "融资余额占流通市值比",
                "%",
                {d: v["rzyezb_pct"] for d, v in margin.items() if v.get("rzyezb_pct") is not None},
            )
            series["margin_rzrqye"] = mk(
                "两融余额",
                "亿",
                {d: v["rzrqye_yi"] for d, v in margin.items() if v.get("rzrqye_yi") is not None},
            )
        except sources.FundamentalsSourceError as exc:
            errors.append(f"两融长史: {exc}")

        # A 股指数（腾讯）
        for key, label, code in (
            ("sse", "上证指数", sources.CN_INDEX_CODES["sse"]),
            ("hs300", "沪深300", sources.CN_INDEX_CODES["hs300"]),
        ):
            try:
                hist = load(f"idx:{key}", lambda c=code: sources.fetch_cn_index_history(c))
                series[key] = mk(label, "", hist)
            except sources.FundamentalsSourceError as exc:
                errors.append(f"指数 {label}: {exc}")

        # 美股指数（FRED）
        for key, label, sid in (
            ("sp500", "标普500", sources.FRED_INDEX_SERIES["sp500"]),
            ("nasdaq", "纳斯达克", sources.FRED_INDEX_SERIES["nasdaq"]),
        ):
            try:
                hist = load(f"idx:{key}", lambda s=sid: sources.fetch_fred_index_history(s))
                series[key] = mk(label, "", hist)
            except sources.FundamentalsSourceError as exc:
                errors.append(f"指数 {label}: {exc}")

        as_of = max((s["dates"][-1] for s in series.values() if s["dates"]), default="")
        return {"as_of": as_of, "series": series, "errors": errors}

    def commodities(self, *, refresh: bool = False) -> dict[str, Any]:
        """全球商品代理：铜金比 / 油金比。yfinance 失败返回 None。"""
        if refresh:
            self._cache.invalidate("commodity")
        data, _ = self._cache.get_or_load(
            "commodity", _COMMODITY_TTL, sources.fetch_commodity_ratios
        )
        return {"commodities": data}

    def etf_strength(self, *, refresh: bool = False) -> dict[str, Any]:
        """11 行业 ETF 相对强度（risk on/off）。yfinance 失败返回 None。"""
        if refresh:
            self._cache.invalidate("etf")
        data, _ = self._cache.get_or_load("etf", _ETF_TTL, sources.fetch_etf_strength)
        return {"etf": data}
