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
from datetime import datetime, timedelta
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
                "main_yi": (lambda v: round(v / 1e8, 2) if v is not None else None)(_num(parts[1])),
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
    return fetch_macro_history("RPT_ECONOMY_PMI", value_field="MAKE_INDEX", page_size=page_size)


def fetch_cpi_history(*, page_size: int = 60) -> list[dict[str, Any]]:
    """CPI 同比月度历史（0 = 通胀/通缩分界）。"""
    return fetch_macro_history("RPT_ECONOMY_CPI", value_field="NATIONAL_SAME", page_size=page_size)


def fetch_ppi_history(*, page_size: int = 60) -> list[dict[str, Any]]:
    """PPI 同比月度历史。"""
    return fetch_macro_history("RPT_ECONOMY_PPI", value_field="BASE_SAME", page_size=page_size)


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


# ── 资金面：两融余额（东财数据中心，沪深合计）─────────────────────────────
# 注意：曾用金十 fs_1.json，实测仅覆盖沪市（约为全国 51%）却标注"沪深"，
# 已改用东财 RPTA_RZRQ_LSHJ（沪深交易所合计），且自带 RZYEZB（融资余额
# 占流通市值比%）——这是不随市值膨胀漂移的标准风险口径。

_MARGIN_DC_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"


def _fetch_margin_rows(page_size: int = 1) -> list[dict[str, Any]]:
    """东财 RPTA_RZRQ_LSHJ，按日期倒序返回最近 page_size 个交易日。

    接口单页上限 800 行，超过则翻页拼接（2026-08 实测：全史 3,977 行）。
    """
    want = min(int(page_size), 4000)
    rows: list[dict[str, Any]] = []
    page = 1
    while len(rows) < want:
        params = {
            "reportName": "RPTA_RZRQ_LSHJ",
            "columns": "DIM_DATE,RZRQYE,RZYE,RQYE,RZMRE,RZYEZB",
            "sortColumns": "DIM_DATE",
            "sortTypes": "-1",
            "pageNumber": str(page),
            "pageSize": str(min(800, want - len(rows))),
        }
        payload = _get_json(_MARGIN_DC_URL, params)
        batch = (payload.get("result") or {}).get("data") or []
        rows.extend(batch)
        if len(batch) < int(params["pageSize"]):
            break  # 到底了
        page += 1
        time.sleep(0.15)  # 翻页限速
    if not rows:
        raise FundamentalsSourceError("两融余额无数据")
    return rows[:want]


def _margin_row(row: dict[str, Any]) -> dict[str, Any]:
    def yi(key: str) -> float | None:
        v = _num(row.get(key))
        return round(v / 1e8, 2) if v is not None else None

    zb = _num(row.get("RZYEZB"))
    return {
        "date": (row.get("DIM_DATE") or "")[:10],
        "rzye_yi": yi("RZYE"),  # 融资余额（亿）
        "rqye_yi": yi("RQYE"),  # 融券余额（亿）
        "rzrqye_yi": yi("RZRQYE"),  # 融资融券余额（亿）
        "buy_yi": yi("RZMRE"),  # 融资买入额（亿）
        "rzyezb_pct": round(zb, 3) if zb is not None else None,  # 融资余额占流通市值比（%）
    }


def fetch_margin() -> dict[str, Any]:
    """沪深融资融券余额汇总（东财数据中心，日频，含占流通市值比）。"""
    return _margin_row(_fetch_margin_rows(1)[0])


# ── 宏观指标历史序列（供趋势图使用）────────────────────────────────────────
# 复用既有数据源取历史，不引新依赖：
# - 国债（中/美 2/5/10/30Y + 利差）：东财 RPTA_WEB_TREASURYYIELD，放大 ps 取多日序列
# - VIX：yfinance ^VIX.history()
# - 两融余额：东财 RPTA_RZRQ_LSHJ 放大 pageSize 取多日序列


def fetch_treasury_history(lookback_days: int = 730) -> dict[str, dict[str, float | None]]:
    """中美国债收益率历史（按交易日），返回 {date: {cn_2y, cn_5y, ..., us_10y, ...}}。

    与 fetch_treasury 同接口，翻页取满 lookback（接口单页上限 500 行，
    2026-08 实测全史 9,321 行、最早 1990-12）。
    """
    out: dict[str, dict[str, float | None]] = {}
    max_pages = max(1, int(lookback_days) // 500 + 2)
    for page in range(1, max_pages + 1):
        params = {
            "type": "RPTA_WEB_TREASURYYIELD",
            "sty": "ALL",
            "st": "SOLAR_DATE",
            "sr": "-1",
            "token": _TREASURY_TOKEN,
            "p": str(page),
            "ps": "500",
            "pageNo": str(page),
            "pageNum": str(page),
        }
        payload = _get_json(_TREASURY_URL, params)
        rows = (payload.get("result") or {}).get("data") or []
        for row in rows:
            date = (row.get("SOLAR_DATE") or "")[:10]
            if not date:
                continue
            out[date] = {name: _num(row.get(code)) for code, name in _TREASURY_FIELDS.items()}
        if len(rows) < 500 or len(out) >= int(lookback_days):
            break
        time.sleep(0.15)  # 翻页限速
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
        out = {str(d.date()): round(float(v), 2) for d, v in hist["Close"].dropna().items()}
        if not out:
            raise FundamentalsSourceError("yfinance VIX 无可用数据")
        return out
    except Exception as exc:  # noqa: BLE001
        raise FundamentalsSourceError(f"VIX 历史: {exc}") from exc


def fetch_margin_history(lookback_days: int = 730) -> dict[str, dict[str, float | None]]:
    """沪深融资融券余额历史（东财数据中心，日频，含占流通市值比）。

    _fetch_margin_rows 自动翻页；两融 2010-03 开闸，全史约 3,977 个交易日。
    """
    out: dict[str, dict[str, float | None]] = {}
    for row in _fetch_margin_rows(min(int(lookback_days), 4000)):
        parsed = _margin_row(row)
        if parsed["date"]:
            out[parsed["date"]] = parsed
    if not out:
        raise FundamentalsSourceError("两融余额历史为空")
    return out


# ── 长周期叠加：股指日线（腾讯 ifzq / 美联储 FRED）───────────────────────
#
# 数据源选择（2026-08 实测）：
# - A股指数：腾讯 ifzq kline（东财 push2his 对连续抓取会整段空响应；
#   腾讯稳定，单页上限 800 根，按结束日期向前翻页拼全史）
# - 美股指数：FRED 官方 CSV（美联储圣路易斯联储）。NASDAQCOM 全史（1971 起）；
#   SP500 因标普授权仅最近 10 年——前端已注明。

_TENCENT_KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"
_FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

CN_INDEX_CODES: dict[str, str] = {
    "sse": "sh000001",  # 上证指数
    "hs300": "sh000300",  # 沪深300
}
FRED_INDEX_SERIES: dict[str, str] = {
    "nasdaq": "NASDAQCOM",  # 纳斯达克综合
    "sp500": "SP500",  # 标普500（FRED 授权仅近 10 年）
}


def fetch_cn_index_history(code: str, lookback_days: int = 5200) -> dict[str, float]:
    """A 股指数收盘日线（腾讯 ifzq），升序 {date: close}。

    单页上限 800 根：先取最新一页，再以本页最旧一根的前一日为 end 向前翻页。
    """
    out: dict[str, float] = {}
    end = ""
    for _ in range(int(lookback_days) // 800 + 2):
        param = f"{code},day,,{end},800" if end else f"{code},day,,,800"
        payload = _get_json(_TENCENT_KLINE_URL, {"param": param})
        node = (payload.get("data") or {}).get(code) or {}
        days = node.get("day") or []
        if not days:
            break
        for row in days:
            v = _num(row[2]) if len(row) > 2 else None  # [date, open, close, ...]
            if row[0] and v is not None:
                out[str(row[0])[:10]] = v
        oldest = str(days[0][0])[:10]
        if len(days) < 800 or len(out) >= int(lookback_days):
            break
        end = (datetime.strptime(oldest, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        time.sleep(0.2)  # 翻页限速
    if not out:
        raise FundamentalsSourceError(f"指数历史 {code} 无数据")
    return dict(sorted(out.items()))


def fetch_fred_index_history(series_id: str) -> dict[str, float]:
    """FRED 官方 CSV -> 升序 {date: value}（美联储圣路易斯联储）。"""
    try:
        resp = requests.get(
            _FRED_CSV_URL,
            params={"id": series_id},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise FundamentalsSourceError(f"FRED {series_id}: {exc}") from exc
    out: dict[str, float] = {}
    for i, line in enumerate(resp.text.splitlines()):
        if i == 0 or "," not in line:
            continue  # 表头 / 空行
        date, _, raw = line.partition(",")
        v = _num(raw.strip().strip('"'))
        if v is not None and date:
            out[date] = v
    if not out:
        raise FundamentalsSourceError(f"FRED {series_id} 无数据")
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
