"""Build short, source-bound observation cards from existing read-only APIs."""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

_OPENER = build_opener(ProxyHandler({}))
_MAX_JSON_BYTES = 12_000_000  # 8028's historical dashboard is currently about 7.2 MB.
_STYLE_DATE = "2026-09-30"
_STYLE_SOURCE = "https://www.msci.com/documents/10199/255599/msci-world-momentum-index-usd-gross.pdf"

SOURCES = [
    {"id": "msci_momentum", "name": "MSCI World Momentum 月末事实表", "url": _STYLE_SOURCE},
    {"id": "msci_quality", "name": "MSCI World Quality 月末事实表", "url": "https://www.msci.com/documents/10199/255599/msci-world-quality-index.pdf"},
    {"id": "msci_value", "name": "MSCI World Value 月末事实表", "url": "https://www.msci.com/documents/10199/255599/msci-world-value-index.pdf"},
    {"id": "msci_minvol", "name": "MSCI World Minimum Volatility 月末事实表", "url": "https://www.msci.com/documents/10199/255599/msci-world-minimum-volatility-index.pdf"},
    {"id": "msci_method", "name": "MSCI 因子指数选用方法", "url": "https://www.msci.com/research-and-insights/blog-post/selecting-the-blend-of-factor-indexes"},
    {"id": "breadth_method", "name": "StockCharts 均线上方股票占比定义", "url": "https://chartschool.stockcharts.com/table-of-contents/index-and-market-indicator-catalog/stockcharts-percent-above-moving-average"},
    {"id": "cboe_vix", "name": "Cboe VIX 历史资料", "url": "https://www.cboe.com/tradable-products/vix/vix-historical-data/"},
    {"id": "fred_ice_oas", "name": "FRED / ICE BofA 美国高收益债利差", "url": "https://fred.stlouisfed.org/series/BAMLH0A0HYM2"},
    {"id": "strategy_portfolios", "name": "LeiSignal 策略组合聚合比较", "url": "http://127.0.0.1:8028/api/strategy-portfolios"},
]


def _sources_for(market: str) -> list[dict]:
    mid = "CN_ALL_A" if market == "cn" else "SP500"
    return [*SOURCES,
            {"id": "lei_breadth", "name": "LeiSignal 已保存的市场宽度", "url": f"http://127.0.0.1:8000/api/market-context/breadth-history?market_id={mid}&lookback_days=1260"},
            {"id": "lei_observations", "name": "LeiSignal 美国市场观察与来源", "url": "http://127.0.0.1:8000/api/fundamentals/observations?market=us"}]


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _valid_date(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 10:
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _get_json(url: str, *, timeout: float = 5.0) -> dict | None:
    """Bounded loopback GET only; errors become explicit missing facts."""
    try:
        with _OPENER.open(Request(url, headers={"Accept": "application/json"}), timeout=timeout) as response:
            if response.status != 200:
                return None
            payload = response.read(_MAX_JSON_BYTES + 1)
            if len(payload) > _MAX_JSON_BYTES:
                return None
            value = json.loads(payload)
            return value if isinstance(value, dict) else None
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError):
        return None


def _card(id: str, topic: str, fact: str, reading: str, watch: str, source_ids: list[str], *, data_date: str | None = None, available: bool = True) -> dict:
    return {"id": id, "topic": topic, "fact": fact, "reading": reading,
            "watch": watch, "source_ids": source_ids, "data_date": data_date,
            "available": available}


def _style_card() -> dict:
    # Fixed, limited 2026-09-30 public facts, never presented as current CN/US performance.
    return _card(
        "world_style", "style",
        "MSCI World 月末美元毛总回报：近3个月价值+3.97%、母指数+1.96%，动量−4.55%；但动量9月+3.64%。",
        "不同期限的表现并不一致；这是发达市场的旧月末资料，不能当作今天A股或美国单一市场的风格读数。",
        "月度新事实表发布后，同口径核对每类风格与自己的母指数；三个月的领先不说明切换会持续。",
        ["msci_momentum", "msci_value", "msci_method"],
        data_date=_STYLE_DATE,
    )


def _breadth_card(market: str, window_days: int, get_json) -> dict:
    mid = "CN_ALL_A" if market == "cn" else "SP500"
    # Same URL as the existing chart keeps its cache behavior. Apply requested
    # display window locally; the upstream currently returns its full series.
    payload = get_json(f"http://127.0.0.1:8000/api/market-context/breadth-history?market_id={mid}&lookback_days=1260")
    history = payload.get("history") if isinstance(payload, dict) else None
    rows = [row for row in history if isinstance(row, dict) and _valid_date(row.get("date"))] if isinstance(history, list) else []
    rows.sort(key=lambda row: row["date"])
    if not rows:
        return _card("breadth", "breadth", "市场宽度资料未取得。", "无法评价股票参与范围。", "恢复已保存的宽度序列，并核对有效股票数与日期。", ["lei_breadth", "breadth_method"], available=False)
    last = rows[-1]
    try:
        cutoff = (date.fromisoformat(last["date"]) - timedelta(days=window_days)).isoformat()
        rows = [row for row in rows if row["date"] >= cutoff]
    except ValueError:
        return _card("breadth", "breadth", "市场宽度日期格式不合格。", "无法评价股票参与范围。", "核对已保存历史日期。", ["lei_breadth", "breadth_method"], available=False)
    vals = [_finite(last.get(f"breadth_{n}")) for n in (20, 50, 200)]
    if any(value is None for value in vals):
        return _card("breadth", "breadth", f"宽度最近资料日 {last['date']}，20/50/200日口径不齐。", "缺值不填零，也不能把部分口径当完整参与度。", "等待同日三个口径及有效股票覆盖数。", ["lei_breadth", "breadth_method"], data_date=last["date"], available=False)
    b20, b50, b200 = vals
    previous = next((row for row in reversed(rows[:-1]) if all(_finite(row.get(f"breadth_{n}")) is not None for n in (20, 50, 200))), None)
    declining = previous is not None and all(vals[i] < _finite(previous.get(f"breadth_{n}")) for i, n in enumerate((20, 50, 200)))
    phrase = (f"较 {previous['date']} 三个期限的比例均下降，站上均线的股票范围收缩。" if declining
              else (f"较 {previous['date']} 三个期限未同时下降。" if previous else "没有可比的前次有效观察。"))
    label = "全A" if market == "cn" else "标普500"
    return _card("breadth", "breadth", f"{label} 已保存宽度截至 {last['date']}：站上20/50/200日均线的股票比例分别为 {b20:.1f}%、{b50:.1f}%、{b200:.1f}%。{phrase}",
                 "这描述股票是否位于各条均线之上，不等于当天上涨家数；接口未给逐日有效股票分母，日期落后时不能称当前市场。",
                 "核对下一次数据日、有效股票覆盖及指数变化；宽度收缩不预言反弹，也不生成买卖指令。",
                 ["lei_breadth", "breadth_method"], data_date=last["date"])


def _risk_card(market: str, get_json) -> dict:
    if market == "cn":
        return _card("risk", "risk", "尚无合格A股市场指数实际波动率读数。", "个股过去20天的波动和美国金融条件不能代替A股市场风险。", "取得带指数、窗口和资料日的市场波动序列后再比较。", [], available=False)
    observations = get_json("http://127.0.0.1:8000/api/fundamentals/observations?market=us")
    items = observations.get("items", []) if isinstance(observations, dict) else []
    found = {item.get("metric_id"): item for item in items if isinstance(item, dict)}
    vix, credit = found.get("vix"), found.get("hy_oas")
    readings = []
    for item, label in ((vix, "VIX"), (credit, "美国高收益债利差")):
        expected_unit = "指数点" if label == "VIX" else "%"
        if (isinstance(item, dict) and _finite(item.get("value")) is not None
                and _valid_date(item.get("observation_date"))
                and item.get("quality_status") in ("current", "stale", "time_unverified")
                and item.get("unit") == expected_unit):
            quality = {"current": "来源已核", "stale": "旧数据", "time_unverified": "可用时点待核"}[item["quality_status"]]
            readings.append(f"{label} {float(item['value']):.2f}{expected_unit}（{item['observation_date']}，{quality}）")
    if not readings:
        return _card("risk", "risk", "VIX和美国高收益债利差当前读数均未取得；NFCI尚未接入。", "无法据空值判断美国风险条件。", "待已有来源返回有效读数及日期后再读。", ["lei_observations", "cboe_vix", "fred_ice_oas"], available=False)
    return _card("risk", "risk", "；".join(readings) + "。NFCI尚未接入。",
                 "VIX是标普500期权预期波动，高收益债利差是债券风险补偿；两者单位与对象不同，不能相加或当独立证明。",
                 "分别核对更新日与变化；NFCI发布后再独立观察周频金融条件。",
                 ["lei_observations", "cboe_vix", "fred_ice_oas"])


def _strategy_card(market: str, get_json) -> dict:
    payload = get_json("http://127.0.0.1:8028/api/strategy-portfolios")
    markets = payload.get("markets", []) if isinstance(payload, dict) else []
    selected = next((row for row in markets if isinstance(row, dict) and row.get("id") == market.upper()), None) if isinstance(markets, list) else None
    comparison = selected.get("comparison", {}) if isinstance(selected, dict) else {}
    corr = _finite(comparison.get("return_correlation")) if isinstance(comparison, dict) else None
    overlap = _finite(comparison.get("holding_overlap")) if isinstance(comparison, dict) else None
    if corr is None and overlap is None:
        return _card("strategy", "strategy", "策略组合聚合比较未取得。", "无法评价两方案是否一起亏损或持仓重复。", "等待原策略组合服务提供有日期的聚合比较。", ["strategy_portfolios"], available=False)
    parts = []
    if corr is not None:
        parts.append(f"历史日收益相关程度 {corr:.3f}")
    if overlap is not None:
        parts.append(f"最后一次月度目标名单重合 {overlap * 100:.1f}%")
    accounts = selected.get("accounts", []) if isinstance(selected, dict) else []
    periods = []
    for account in accounts if isinstance(accounts, list) else []:
        if not isinstance(account, dict) or account.get("scheme") not in ("mv", "rv"):
            continue
        series = (account.get("history") or {}).get("series") or []
        days = [point.get("date") for point in series if isinstance(point, dict) and isinstance(point.get("date"), str)]
        if days:
            account_name = account.get("name") if isinstance(account.get("name"), str) else "策略方案"
            periods.append(f"{account_name}展示历史 {min(days)}至{max(days)}")
    period_text = "；".join(periods) if periods else "展示历史日期未取得"
    label = "A股" if market == "cn" else "美股"
    return _card("strategy", "strategy", f"{label} 两方案：" + "；".join(parts) + f"；{period_text}。",
                 "展示历史范围不等于计算相关程度时的共同有效日期；共同有效天数未核。目标名单不等于实际资金持仓，不能据此计算共同亏损金额。",
                 "继续看相同日期、相同资金和费用口径的共同下跌损失；缺真实持仓时保持缺项。",
                 ["strategy_portfolios"])


def build_evidence(market: str, window_days: int, *, get_json=_get_json) -> dict:
    cards = [_style_card(), _breadth_card(market, window_days, get_json),
             _risk_card(market, get_json), _strategy_card(market, get_json)]
    return {
        "asof": datetime.now(timezone.utc).isoformat(),
        "market": market,
        "window_days": window_days,
        "cards": cards,
        "sources": _sources_for(market),
        "limits": ["背景观察，不参与LEI技术判定或交易指令。", "MSCI World是发达市场月末样例，不是A股或美国单独市场。", "数据缺项及旧日期保留；模型只选已核短卡。"],
    }
