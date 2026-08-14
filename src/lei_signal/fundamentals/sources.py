"""东方财富公开 JSON 接口取数（与 data/providers.py 同一哲学：requests 直连，不引 akshare）。

三个数据源：
- 行业板块全景：push2 clist（行情 + 主力资金 + 涨跌家数）
- 行业资金流历史：push2his fflow daykline（主力/超大/大/中/小单净流入）
- 宏观指标：datacenter-web（PMI / CPI / PPI，国家统计局口径）

所有函数只负责"取回原始 JSON 并整型为 dict"，失败抛 FundamentalsSourceError，
由 service 层决定降级策略（单项失败不影响其他项）。
"""
from __future__ import annotations

import time
from typing import Any

import requests

_TIMEOUT = 10
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
}

# 主站被限流时回落到延时行情站（同 schema，行情延时 ~15 分钟，参考层可接受）。
_CLIST_URLS = (
    "https://push2.eastmoney.com/api/qt/clist/get",
    "https://push2delay.eastmoney.com/api/qt/clist/get",
)
_FLOW_URLS = (
    "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get",
    "https://push2delay.eastmoney.com/api/qt/stock/fflow/daykline/get",
)
_DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
# 中美国债收益率：东财旧版 datacenter 接口（带公开 token），中美同源。
_TREASURY_URL = "https://datacenter.eastmoney.com/api/data/get"
_TREASURY_TOKEN = "894050c76af8597a853f5b408b759f5d"
# 东财国债字段码 -> 标准名（与 akshare bond_zh_us_rate 同口径）
_TREASURY_FIELDS = {
    "EMM00588704": "cn_2y",
    "EMM00166462": "cn_5y",
    "EMM00166466": "cn_10y",
    "EMM00166469": "cn_30y",
    "EMM01276014": "cn_10_2_spread",
    "EMG00001306": "us_2y",
    "EMG00001308": "us_5y",
    "EMG00001310": "us_10y",
    "EMG00001312": "us_30y",
    "EMG01339436": "us_10_2_spread",
}


class FundamentalsSourceError(RuntimeError):
    """单个数据源取数失败。"""


def _get_json(urls: str | tuple[str, ...], params: dict[str, Any]) -> dict[str, Any]:
    """GET JSON：逐 host 尝试，每个 host 瞬断重试一次（东财对高频访问会短时空响应）。"""
    if isinstance(urls, str):
        urls = (urls,)
    last_exc: Exception | None = None
    for url in urls:
        for attempt in range(2):
            if attempt:
                time.sleep(1.5)
            try:
                resp = requests.get(url, params=params, headers=_HEADERS, timeout=_TIMEOUT)
                resp.raise_for_status()
                payload = resp.json()
            except Exception as exc:  # noqa: BLE001 —— 网络/解析错误统一收口
                last_exc = exc
                continue
            if not isinstance(payload, dict):
                last_exc = FundamentalsSourceError(f"{url}: 非 JSON 对象响应")
                continue
            return payload
    raise FundamentalsSourceError(f"{urls[0]}: {last_exc}")


def _num(value: Any) -> float | None:
    """东财空值是 '-'，统一转 None。"""
    if value is None or value == "-" or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_industry_boards() -> list[dict[str, Any]]:
    """东财行业板块全景（含细分行业，约 500 个）。

    fs=m:90+t:2+f:!50 与 akshare stock_board_industry_name_em 同口径。
    """
    # pz 上限 100，500 个板块要翻页拉全。
    diff: list[dict[str, Any]] = []
    for page in range(1, 7):
        payload = _get_json(
            _CLIST_URLS,
            {
                "pn": page,
                "pz": 100,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": "m:90+t:2+f:!50",
                "fields": "f12,f14,f2,f3,f8,f9,f20,f62,f184,f104,f105",
            },
        )
        data = payload.get("data") or {}
        batch = data.get("diff") or []
        diff.extend(batch)
        if len(diff) >= (data.get("total") or 0) or not batch:
            break
    boards: list[dict[str, Any]] = []
    for row in diff:
        boards.append(
            {
                "code": row.get("f12"),
                "name": row.get("f14"),
                "latest": _num(row.get("f2")),
                "pct_change": _num(row.get("f3")),
                "turnover_rate": _num(row.get("f8")),
                # f9 动态市盈率（亏损为负，参考层用绝对值看贵贱）
                "pe_ttm": _num(row.get("f9")),
                # f20 总市值（元）→ 亿元
                "total_mv_yi": (lambda v: round(v / 1e8, 1) if v is not None else None)(
                    _num(row.get("f20"))
                ),
                # f62 主力净流入（元）→ 亿元
                "main_net_inflow_yi": (lambda v: round(v / 1e8, 2) if v is not None else None)(
                    _num(row.get("f62"))
                ),
                "main_net_inflow_pct": _num(row.get("f184")),
                "up_count": row.get("f104"),
                "down_count": row.get("f105"),
            }
        )
    if not boards:
        raise FundamentalsSourceError("行业板块列表为空")
    return boards


def fetch_industry_flow(code: str, *, days: int = 20) -> list[dict[str, Any]]:
    """单个行业板块的资金流历史（日级）。

    fields2 顺序：f51 日期, f52 主力净流入, f53 小单, f54 中单, f55 大单, f56 超大单。
    """
    payload = _get_json(
        _FLOW_URLS,
        {
            "lmt": days,
            "klt": 101,
            "secid": f"90.{code}",
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56",
        },
    )
    klines = (payload.get("data") or {}).get("klines") or []
    points: list[dict[str, Any]] = []
    for line in klines:
        parts = line.split(",")
        if len(parts) < 6:
            continue
        points.append(
            {
                "date": parts[0],
                "main_yi": (lambda v: round(v / 1e8, 2) if v is not None else None)(
                    _num(parts[1])
                ),
                "small_yi": (lambda v: round(v / 1e8, 2) if v is not None else None)(
                    _num(parts[2])
                ),
                "medium_yi": (lambda v: round(v / 1e8, 2) if v is not None else None)(
                    _num(parts[3])
                ),
                "large_yi": (lambda v: round(v / 1e8, 2) if v is not None else None)(
                    _num(parts[4])
                ),
                "super_large_yi": (
                    (lambda v: round(v / 1e8, 2) if v is not None else None)(_num(parts[5]))
                    if len(parts) > 5
                    else None
                ),
            }
        )
    if not points:
        raise FundamentalsSourceError(f"行业 {code} 资金流历史为空")
    return points


def _fetch_macro_rows(report_name: str, *, page_size: int = 1) -> list[dict[str, Any]]:
    """东财 datacenter 宏观报告原始行（按 REPORT_DATE 降序）。"""
    payload = _get_json(
        _DATACENTER_URL,
        {
            "reportName": report_name,
            "columns": "ALL",
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "pageSize": page_size,
            "pageNumber": 1,
            "source": "WEB",
            "client": "WEB",
        },
    )
    rows = (payload.get("result") or {}).get("data") or []
    if not rows:
        raise FundamentalsSourceError(f"宏观报告 {report_name} 无数据")
    return rows


def _fetch_macro_report(report_name: str, *, page_size: int = 1) -> dict[str, Any]:
    return _fetch_macro_rows(report_name, page_size=page_size)[0]


def _fmt(value: float | None, *, signed: bool = False, suffix: str = "") -> str:
    if value is None:
        return "-"
    return f"{value:+.1f}{suffix}" if signed else f"{value:.1f}{suffix}"


def fetch_pmi() -> dict[str, Any]:
    """制造业 PMI 最新一期（含非制造业 PMI 作注）。"""
    row = _fetch_macro_report("RPT_ECONOMY_PMI")
    return {
        "key": "pmi",
        "name_cn": "制造业 PMI",
        "period": row.get("TIME"),
        "value": _num(row.get("MAKE_INDEX")),
        "yoy": _num(row.get("MAKE_SAME")),
        "note_cn": "荣枯线 50；非制造业 " + _fmt(_num(row.get("NMAKE_INDEX"))),
    }


def fetch_cpi() -> dict[str, Any]:
    """CPI 最新一期（value=同比，note 里带环比）。"""
    row = _fetch_macro_report("RPT_ECONOMY_CPI")
    return {
        "key": "cpi",
        "name_cn": "CPI 同比",
        "period": row.get("TIME"),
        "value": _num(row.get("NATIONAL_SAME")),
        "yoy": None,
        "note_cn": "单位 %；环比 "
        + _fmt(_num(row.get("NATIONAL_SEQUENTIAL")), signed=True, suffix="%"),
    }


def fetch_ppi() -> dict[str, Any]:
    """PPI 最新一期（value=同比）。"""
    row = _fetch_macro_report("RPT_ECONOMY_PPI")
    return {
        "key": "ppi",
        "name_cn": "PPI 同比",
        "period": row.get("TIME"),
        "value": _num(row.get("BASE_SAME")),
        "yoy": None,
        "note_cn": "单位 %；基数 " + _fmt(_num(row.get("BASE"))),
    }


def fetch_macro_history(
    report_name: str, *, value_field: str, page_size: int = 60
) -> list[dict[str, Any]]:
    """宏观报告月度历史序列，升序（最早在前），供趋势图。

    返回 [{date, value}, ...]。date 截到 YYYY-MM-DD，跳过空值。
    """
    rows = _fetch_macro_rows(report_name, page_size=page_size)
    points: list[dict[str, Any]] = []
    for row in rows:
        date = str(row.get("REPORT_DATE") or row.get("TIME") or "")[:10]
        value = _num(row.get(value_field))
        if value is not None and date:
            points.append({"date": date, "value": value})
    points.reverse()  # API 返回降序，翻成升序便于绘图
    return points


def fetch_pmi_history(*, page_size: int = 60) -> list[dict[str, Any]]:
    """制造业 PMI 月度历史（荣枯线 50）。"""
    return fetch_macro_history(
        "RPT_ECONOMY_PMI", value_field="MAKE_INDEX", page_size=page_size
    )


def fetch_cpi_history(*, page_size: int = 60) -> list[dict[str, Any]]:
    """CPI 同比月度历史（0 = 通胀/通缩分界）。"""
    return fetch_macro_history(
        "RPT_ECONOMY_CPI", value_field="NATIONAL_SAME", page_size=page_size
    )


def fetch_ppi_history(*, page_size: int = 60) -> list[dict[str, Any]]:
    """PPI 同比月度历史。"""
    return fetch_macro_history(
        "RPT_ECONOMY_PPI", value_field="BASE_SAME", page_size=page_size
    )


# ── 利率类：中美国债 + VIX ──────────────────────────────────────────────


def fetch_treasury() -> dict[str, Any]:
    """中美国债收益率（2/5/10/30 年 + 10-2 利差）。

    美国侧东财数据滞后约 1 个交易日，取最近 N 天里各自最新非空行。
    """
    payload = _get_json(
        _TREASURY_URL,
        {
            "type": "RPTA_WEB_TREASURYYIELD",
            "sty": "ALL",
            "st": "SOLAR_DATE",
            "sr": "-1",
            "token": _TREASURY_TOKEN,
            "p": "1",
            "ps": "15",
            "pageNo": "1",
            "pageNum": "1",
        },
    )
    rows = (payload.get("result") or {}).get("data") or []
    if not rows:
        raise FundamentalsSourceError("国债收益率无数据")

    cn_row = us_row = None
    for row in rows:
        if cn_row is None and row.get("EMM00166466") is not None:
            cn_row = row
        if us_row is None and row.get("EMG00001310") is not None:
            us_row = row
        if cn_row and us_row:
            break

    def pick(row: dict | None, prefix: str) -> dict[str, float | None]:
        out: dict[str, float | None] = {}
        for code, name in _TREASURY_FIELDS.items():
            if name.startswith(prefix):
                out[name] = _num(row.get(code)) if row else None
        return out

    cn = pick(cn_row, "cn_")
    us = pick(us_row, "us_")
    cn10 = cn.get("cn_10y")
    us10 = us.get("us_10y")
    spread = round(cn10 - us10, 2) if cn10 is not None and us10 is not None else None
    return {
        "as_of_cn": (cn_row or {}).get("SOLAR_DATE", "")[:10] or None,
        "as_of_us": (us_row or {}).get("SOLAR_DATE", "")[:10] or None,
        "cn": cn,
        "us": us,
        # 中美 10 年利差（中国 - 美国），为负即美债收益率更高、资本外流压力侧。
        "cn_us_spread_10y": spread,
    }


def fetch_vix() -> dict[str, Any] | None:
    """CBOE VIX 指数（恐慌指数），via yfinance。失败返回 None，由 service 降级。"""
    try:
        import yfinance as yf

        hist = yf.Ticker("^VIX").history(period="5d")
        if hist.empty:
            return None
        last = hist["Close"].dropna().iloc[-1]
        as_of = str(hist.index[-1].date())
        return {"value": round(float(last), 2), "as_of": as_of}
    except Exception:  # noqa: BLE001 -- yfinance 限流/网络错误统一降级为"暂不可用"
        return None


# ── 资金面：两融余额（金十数据，沪深合计）─────────────────────────────────

_MARGIN_URL = "https://cdn.jin10.com/data_center/reports/fs_1.json"


def fetch_margin() -> dict[str, Any]:
    """沪深融资融券余额汇总（金十数据，日频）。

    金十返回 {keys:[字段名...], values:{日期:[值...]}}，keys 顺序固定为
    融资买入额/融资余额/融券卖出量/融券余量/融券余额/融资融券余额。
    """
    payload = _get_json(_MARGIN_URL, {})
    keys = payload.get("keys") or []
    values = payload.get("values") or {}
    if not values:
        raise FundamentalsSourceError("两融余额无数据")
    latest_date = max(values.keys())
    row = values[latest_date]
    idx = {k["name"]: i for i, k in enumerate(keys)} if keys and isinstance(keys[0], dict) else {}

    def pick(name: str) -> float | None:
        i = idx.get(name)
        if i is None or i >= len(row):
            return None
        v = _num(row[i])
        return round(v / 1e8, 2) if v is not None else None

    return {
        "date": latest_date,
        "rzye_yi": pick("融资余额"),      # 融资余额（亿）
        "rqye_yi": pick("融券余额"),      # 融券余额（亿）
        "rzrqye_yi": pick("融资融券余额"),  # 融资融券余额（亿）
        "buy_yi": pick("融资买入额"),     # 融资买入额（亿）
    }


# ── 宏观指标历史序列（供趋势图使用）────────────────────────────────────────
# 复用既有数据源取历史，不引新依赖：
# - 国债（中/美 2/5/10/30Y + 利差）：东财 RPTA_WEB_TREASURYYIELD，放大 ps 取多日序列
# - VIX：yfinance ^VIX.history()
# - 两融余额：金十 values 本就是 {日期: 行}，直接全量读

def fetch_treasury_history(lookback_days: int = 730) -> dict[str, dict[str, float | None]]:
    """中美国债收益率历史（按交易日），返回 {date: {cn_2y, cn_5y, ..., us_10y, ...}}。

    与 fetch_treasury 同接口，仅放大 ps 取回多日序列（原接口只取最新 15 行）。
    """
    params = {
        "type": "RPTA_WEB_TREASURYYIELD",
        "sty": "ALL",
        "st": "SOLAR_DATE",
        "sr": "-1",
        "token": _TREASURY_TOKEN,
        "p": "1",
        "ps": str(min(int(lookback_days), 1200)),
        "pageNo": "1",
        "pageNum": "1",
    }
    payload = _get_json(_TREASURY_URL, params)
    rows = (payload.get("result") or {}).get("data") or []
    out: dict[str, dict[str, float | None]] = {}
    for row in rows:
        date = (row.get("SOLAR_DATE") or "")[:10]
        if not date:
            continue
        out[date] = {name: _num(row.get(code)) for code, name in _TREASURY_FIELDS.items()}
    if not out:
        raise FundamentalsSourceError("国债收益率历史无数据")
    return out


def fetch_vix_history(lookback_days: int = 730) -> dict[str, float]:
    """CBOE VIX 历史日线（恐慌指数），via yfinance。失败抛错。"""
    try:
        import yfinance as yf

        hist = yf.Ticker("^VIX").history(period=f"{min(int(lookback_days), 1500)}d")
        if hist.empty:
            raise FundamentalsSourceError("yfinance VIX 历史返回空")
        out = {
            str(d.date()): round(float(v), 2)
            for d, v in hist["Close"].dropna().items()
        }
        if not out:
            raise FundamentalsSourceError("yfinance VIX 无可用数据")
        return out
    except Exception as exc:  # noqa: BLE001
        raise FundamentalsSourceError(f"VIX 历史: {exc}") from exc


def fetch_margin_history() -> dict[str, dict[str, float | None]]:
    """沪深融资融券余额历史（金十数据）。

    金十 payload.values 本就是 {日期: [字段值...]}，原 fetch_margin 只取最新一天；
    这里全量读出，得到日频历史序列。
    """
    payload = _get_json(_MARGIN_URL, {})
    keys = payload.get("keys") or []
    values = payload.get("values") or {}
    if not values:
        raise FundamentalsSourceError("两融余额历史无数据")
    idx = {k["name"]: i for i, k in enumerate(keys)} if keys and isinstance(keys[0], dict) else {}
    out: dict[str, dict[str, float | None]] = {}

    def pick(row: list, name: str) -> float | None:
        i = idx.get(name)
        if i is None or i >= len(row):
            return None
        v = _num(row[i])
        return round(v / 1e8, 2) if v is not None else None

    for date, row in values.items():
        if not isinstance(row, list):
            continue
        out[date] = {
            "rzye_yi": pick(row, "融资余额"),
            "rqye_yi": pick(row, "融券余额"),
            "rzrqye_yi": pick(row, "融资融券余额"),
            "buy_yi": pick(row, "融资买入额"),
        }
    if not out:
        raise FundamentalsSourceError("两融余额历史为空")
    return out


# ── 全球商品代理：铜金比 / 油金比（thememo 消费类，抽象化全球经济）─────────

def _yf_last(tickers: list[str], period: str = "3mo") -> dict[str, dict[str, float]]:
    """yf.download 一批 ticker，返回 {ticker: {last, prev_month}}。失败抛错。"""
    import pandas as pd
    import yfinance as yf

    data = yf.download(tickers, period=period, interval="1d", progress=False, group_by="ticker")
    if data.empty:
        raise FundamentalsSourceError("yfinance 返回空")
    multi = isinstance(data.columns, pd.MultiIndex)
    out: dict[str, dict[str, float]] = {}
    for t in tickers:
        try:
            s = data[t]["Close"].dropna() if multi else data["Close"].dropna()
            if len(s) < 2:
                continue
            out[t] = {
                "last": float(s.iloc[-1]),
                "prev_month": float(s.iloc[-22]) if len(s) >= 22 else float(s.iloc[0]),
            }
        except Exception:  # noqa: BLE001
            continue
    if not out:
        raise FundamentalsSourceError("yfinance 无可用收盘价")
    return out


def fetch_commodity_ratios() -> dict[str, Any] | None:
    """铜金比 / 油金比（铜/原油相对黄金）。

    thememo：铜金比反映工业需求与避险的角力，油金比反映通胀与避险，
    二者 + 国债 + PMI 可抽象化把握全球经济。via yfinance，失败返回 None。
    """
    try:
        px = _yf_last(["HG=F", "GC=F", "CL=F"], period="3mo")
        cu = px.get("HG=F", {}).get("last")
        gold = px.get("GC=F", {}).get("last")
        crude = px.get("CL=F", {}).get("last")
        if cu is None or gold is None or crude is None:
            return None
        return {
            "copper_gold": round(cu / gold, 4),
            "crude_gold": round(crude / gold, 4),
            "copper": cu,
            "gold": gold,
            "crude": crude,
        }
    except Exception:  # noqa: BLE001
        return None


# ── 11 行业 ETF 相对强度（thememo 市场类，risk on/off）────────────────────

# SPDR 11 行业 ETF：必选消费/医疗/公用事业领涨 = risk-off；可选消费/科技领涨 = risk-on。
_ETF_SECTORS: list[tuple[str, str, str]] = [
    ("XLY", "可选消费", "risk_on"),
    ("XLP", "必选消费", "risk_off"),
    ("XLV", "医疗", "risk_off"),
    ("XLU", "公用事业", "risk_off"),
    ("XLE", "能源", "neutral"),
    ("XLF", "金融", "neutral"),
    ("XLI", "工业", "neutral"),
    ("XLB", "材料", "neutral"),
    ("XLK", "科技", "risk_on"),
    ("XLC", "通信", "risk_on"),
    ("XLRE", "地产", "neutral"),
]


def fetch_etf_strength() -> dict[str, Any] | None:
    """11 行业 ETF 相对 SPY 的 1 月相对强度，按强度排序。

    risk_off 类（必选/医疗/公用）排在前列 = 市场避险；risk_on 类排在前列 = 风险偏好上升。
    via yfinance，失败返回 None。
    """
    try:
        tickers = [t for t, _, _ in _ETF_SECTORS] + ["SPY"]
        px = _yf_last(tickers, period="3mo")
        spy = px.get("SPY")
        if not spy:
            return None
        spy_1m = spy["last"] / spy["prev_month"] - 1
        items: list[dict[str, Any]] = []
        for code, name, bias in _ETF_SECTORS:
            p = px.get(code)
            if not p:
                continue
            etf_1m = p["last"] / p["prev_month"] - 1
            items.append(
                {
                    "code": code,
                    "name": name,
                    "bias": bias,
                    "ret_1m": round(etf_1m * 100, 2),
                    "rel_1m": round((etf_1m - spy_1m) * 100, 2),
                }
            )
        items.sort(key=lambda x: x["rel_1m"], reverse=True)
        off_avg = sum(i["rel_1m"] for i in items if i["bias"] == "risk_off") / max(
            1, sum(1 for i in items if i["bias"] == "risk_off")
        )
        regime = "risk_off" if off_avg > 0 else "risk_on"
        return {"items": items, "regime": regime, "spy_1m": round(spy_1m * 100, 2)}
    except Exception:  # noqa: BLE001
        return None
