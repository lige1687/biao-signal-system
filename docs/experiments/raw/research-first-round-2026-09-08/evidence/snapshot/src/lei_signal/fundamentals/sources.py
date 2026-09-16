"""东方财富公开 JSON 接口取数（与 data/providers.py 同一哲学：requests 直连，不引 akshare）。

三个数据源：
- 行业板块全景：push2 clist（行情 + 主力资金 + 涨跌家数）
- 行业资金流历史：push2his fflow daykline（主力/超大/大/中/小单净流入）
- 宏观指标：datacenter-web（PMI / CPI / PPI，国家统计局口径）

所有函数只负责"取回原始 JSON 并整型为 dict"，失败抛 FundamentalsSourceError，
由 service 层决定降级策略（单项失败不影响其他项）。
"""

from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime, timedelta
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
    # 教训（2026-09-05 实测）：push2test 备用集群看似可用但数据质量不合格——
    # 日期稀疏（约 2/3 交易日）且部分日子数值与主源偏差/翻转（9-01 主力
    # -98.6 vs 主源 -121.0），禁止用于历史回填。被封时宁可等解封或走每日
    # clist 快照通道累积。
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


def _get_json(
    urls: str | tuple[str, ...],
    params: dict[str, Any],
    *,
    trust_env: bool = True,
) -> dict[str, Any]:
    """GET JSON：逐 host 尝试，每个 host 瞬断重试一次（东财对高频访问会短时空响应）。

    ``trust_env=False`` 用独立 Session 绕过系统代理直连——本机代理为白名单模式，
    push2his 被拒（ProxyError）而直连可达；默认 True 保持既有行为不变。
    """
    if isinstance(urls, str):
        urls = (urls,)
    session = requests.Session()
    session.trust_env = trust_env
    last_exc: Exception | None = None
    for url in urls:
        for attempt in range(2):
            if attempt:
                time.sleep(1.5)
            try:
                resp = session.get(url, params=params, headers=_HEADERS, timeout=_TIMEOUT)
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


def fetch_industry_flow(
    code: str, *, days: int = 20, prefer_direct: bool = True
) -> list[dict[str, Any]]:
    """单个行业板块的资金流历史（日级）。

    fields2 顺序：f51 日期, f52 主力净流入, f53 小单, f54 中单, f55 大单, f56 超大单。

    取数顺序：先 **直连 push2his**（绕系统代理；白名单代理会拒 push2his，而 delay
    镜像只返最近 1 日）；``prefer_direct=False`` 跳过直连（调用方已探明直连不可用），
    直接走常规路径（代理 → push2delay，仅最近 1 日，用于每日增量累积）。
    """
    params = {
        "lmt": days,
        "klt": 101,
        "secid": f"90.{code}",
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56",
    }
    payload: dict[str, Any] | None = None
    if prefer_direct:
        try:
            payload = _get_json(_FLOW_URLS[:1], params, trust_env=False)
        except FundamentalsSourceError:
            payload = None
        if payload is None:
            payload = _get_json(_FLOW_URLS, params)
    else:
        # 调用方已探明直连不可用：只走 delay，避免对 push2his 的无效重试拖慢整体
        payload = _get_json(_FLOW_URLS[1:], params)
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


# VIX 走 Yahoo 公开 v8 图表 API（query1），**不走 yfinance 库**。
# 原因同 data/providers.py:YahooV8PriceProvider：yfinance 用 query2 端点 +
# cookie/crumb 机制，在共享 IP 段上会持续触发 IP 级 429（Too Many Requests，
# 一次几十分钟）；query1 的 v8 图表端点限流阈值宽松得多，实测稳定可用。
_YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"
_YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json,text/plain,*/*",
}


def _fetch_yahoo_closes(symbol: str, params: dict[str, Any]) -> dict[str, float]:
    """Yahoo v8 图表 API 取日线收盘价，返回 {date: close}（已剔除 null bar）。

    失败统一抛 FundamentalsSourceError，由调用方决定降级策略。
    """
    url = f"{_YAHOO_CHART_URL}{requests.utils.quote(symbol)}"
    try:
        resp = requests.get(url, params=params, headers=_YAHOO_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        raise FundamentalsSourceError(f"Yahoo v8 请求失败：{exc}") from exc
    except ValueError as exc:  # JSON 解析失败
        raise FundamentalsSourceError(f"Yahoo v8 返回非 JSON：{exc}") from exc

    chart = payload.get("chart") or {}
    if chart.get("error"):
        desc = (chart["error"] or {}).get("description", "unknown")
        raise FundamentalsSourceError(f"Yahoo v8 错误：{desc}")
    results = chart.get("result") or []
    if not results:
        raise FundamentalsSourceError(f"Yahoo v8 无数据：{symbol}")

    result = results[0]
    stamps = result.get("timestamp") or []
    quotes = (result.get("indicators") or {}).get("quote") or [{}]
    closes = (quotes[0] or {}).get("close") or []
    out: dict[str, float] = {}
    # strict=False：两数组长度理论上一致，万一 Yahoo 返回不齐也只截到较短的，
    # 不因数据异常打挂整个面板（本模块一贯的降级风格）。
    for stamp, close in zip(stamps, closes, strict=False):
        if stamp is None or close is None:
            continue  # 停牌/未成交 bar
        date = datetime.fromtimestamp(int(stamp), tz=UTC).date().isoformat()
        out[date] = round(float(close), 2)
    if not out:
        raise FundamentalsSourceError(f"Yahoo v8 无可用收盘价：{symbol}")
    return out


def fetch_vix() -> dict[str, Any] | None:
    """CBOE VIX 指数（恐慌指数），via Yahoo v8 图表 API。失败抛错，由 service 降级。

    注意：以前这里把所有异常吞成 None，导致前端只显示"暂不可用"而 errors[]
    为空——分不清限流、断网还是代码坏了。现在统一抛错让原因可见。
    """
    closes = _fetch_yahoo_closes("^VIX", {"interval": "1d", "range": "5d"})
    as_of = max(closes)
    return {"value": closes[as_of], "as_of": as_of}


# ── 股权风险溢价 ERP（盈利收益率 − 10Y 国债）─────────────────────────────
# ERP = Earnings Yield (1/PE_TTM × 100) − 10Y 国债收益率。
# 美股盈利收益率 via multpl.com（S&P500 Earnings Yield，日频）；
# A股盈利收益率 = 1 / 沪深300 PE_TTM × 100，PE via yfinance（000300.SS）。
# 国债 10Y 复用 fetch_treasury()（东财 RPTA_WEB_TREASURYYIELD，中/美同源）。
# ERP 升高 = 股票相对债券性价比提升（机会），转负 = 债券相对更具吸引力（股票偏贵）。

_MULTIPL_EY_URL = "https://www.multpl.com/s-p-500-earnings-yield"
_FRED_EY_SERIES = "SP500EY"  # FRED S&P500 Earnings Yield，作为 multpl 的 fallback


def _fetch_multpl_earnings_yield() -> float:
    """multpl.com S&P500 盈利收益率（%），带超时重试。解析首页 'Earnings Yield is X.XX%'。"""
    last_exc: Exception | None = None
    for attempt in range(3):
        if attempt:
            time.sleep(1.5)
        try:
            resp = requests.get(
                _MULTIPL_EY_URL,
                headers={**_HEADERS, "Referer": "https://www.multpl.com/"},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            last_exc = exc
            continue
        m = re.search(r"Earnings Yield is\s*([\d.]+)%", resp.text)
        if m:
            return float(m.group(1))
        last_exc = FundamentalsSourceError("multpl.com 未能解析盈利收益率")
    raise FundamentalsSourceError(f"multpl.com: {last_exc}")


def _fetch_fred_latest(series_id: str) -> float:
    """FRED CSV 取最新非空值（官方序列，日频/月频均可）。"""
    try:
        resp = requests.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv",
            params={"id": series_id},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise FundamentalsSourceError(f"FRED {series_id}: {exc}") from exc
    for line in reversed(resp.text.splitlines()):
        if "," not in line:
            continue
        date, _, raw = line.partition(",")
        v = _num(raw.strip().strip('"'))
        if v is not None and date:
            return v
    raise FundamentalsSourceError(f"FRED {series_id} 无数据")


def _yf_pe(symbol: str) -> float:
    """yfinance 取 trailingPE。失败抛 FundamentalsSourceError（含限流 429）。"""
    import yfinance as yf

    try:
        info = yf.Ticker(symbol).info
        pe = info.get("trailingPE")
    except Exception as exc:  # noqa: BLE001 —— yfinance 限流抛 YFRateLimitError 等
        raise FundamentalsSourceError(f"yfinance {symbol}: {exc}") from exc
    if pe is None:
        raise FundamentalsSourceError(f"yfinance {symbol} 无 trailingPE")
    return float(pe)


def fetch_us_erp(treasury: dict[str, Any] | None = None) -> dict[str, Any]:
    """美股股权风险溢价 ERP = S&P500 盈利收益率 − 美债 10Y（%）。

    盈利收益率先尝试 multpl.com（日频，快），失败则 fallback 到 FRED SP500EY。
    treasury 可由调用方传入（避免重复取数）；缺省时自取 fetch_treasury()。
    """
    if treasury is None:
        treasury = fetch_treasury()
    us10 = (treasury.get("us") or {}).get("us_10y")
    if us10 is None:
        raise FundamentalsSourceError("美债10Y缺失，无法计算美股ERP")
    try:
        ey = _fetch_multpl_earnings_yield()
        ey_source = "multpl.com S&P500 Earnings Yield"
    except FundamentalsSourceError:
        ey = _fetch_fred_latest(_FRED_EY_SERIES)
        ey_source = f"FRED {_FRED_EY_SERIES}"
    return {
        "earnings_yield": round(ey, 2),
        "risk_free": round(float(us10), 2),
        "erp": round(ey - float(us10), 2),
        "as_of": (treasury.get("as_of_us") or None),
        "ey_source": ey_source,
    }


# 东财估值接口（公开 token，与 akshare 同源）取指数最新 PE_TTM。
_DCFM_VALUATION_URL = "http://dcfm.eastmoney.com/em_mutisvcexpandinterface/api/js/get"


def _fetch_hs300_pe_dcfm() -> float:
    """东财 dcfm 指数估值接口取沪深300最新 PE_TTM（HTTP/HTTPS 双源 + 重试）。"""
    params = {
        "st": "TDATE",
        "sr": "-1",
        "ps": "1",
        "p": "1",
        "type": "GZFX_SCTJ",
        "token": "70f12f2f4f091e459a279469fe49eca5",
        "source": "WEB",
        "js": "(x)",
        "filter": "(MKTCODE='000300')",
    }
    # HTTP 是公开接口原始协议；部分网络环境强制 HTTPS，故 HTTPS 作 fallback。
    urls = (_DCFM_VALUATION_URL, _DCFM_VALUATION_URL.replace("http://", "https://"))
    last_exc: Exception | None = None
    for url in urls:
        for attempt in range(2):
            if attempt:
                time.sleep(1.5)
            try:
                resp = requests.get(url, params=params, headers=_HEADERS, timeout=_TIMEOUT)
                resp.raise_for_status()
                text = resp.text.strip()
                # js=(x) 可能返回被括号包裹的 JSON：([{...}]) 或 ({...})
                if text.startswith("(") and text.endswith(")"):
                    text = text[1:-1]
                payload = json.loads(text)
            except requests.RequestException as exc:
                last_exc = exc
                continue
            except ValueError as exc:
                last_exc = FundamentalsSourceError(f"东财指数估值返回非 JSON：{exc}")
                continue
            if not isinstance(payload, list) or not payload:
                last_exc = FundamentalsSourceError("东财指数估值返回空")
                continue
            row = payload[0]
            # 不同字段名兼容：公开接口常见 PE9（TTM）/ PE / 市盈率(TTM)
            pe = _num(
                row.get("PE9") or row.get("PE") or row.get("PE_TTM") or row.get("市盈率(TTM)")
            )
            if pe is None:
                keys = list(row.keys())[:20]
                last_exc = FundamentalsSourceError(f"东财指数估值无 PE 字段：{keys}")
                continue
            return float(pe)
    raise FundamentalsSourceError(f"东财指数估值: {last_exc}")


def _fetch_hs300_pe_akshare() -> float:
    """akshare 乐咕乐股取沪深300最新滚动市盈率（可选依赖，未安装时直接抛错）。"""
    try:
        import akshare as ak
    except ImportError as exc:
        raise FundamentalsSourceError(f"akshare 未安装：{exc}") from exc
    try:
        df = ak.stock_index_pe_lg(symbol="沪深300")
        pe = _num(df.iloc[-1].get("滚动市盈率"))
    except Exception as exc:  # noqa: BLE001
        raise FundamentalsSourceError(f"akshare 沪深300 PE: {exc}") from exc
    if pe is None:
        raise FundamentalsSourceError("akshare 沪深300 无滚动市盈率")
    return float(pe)


def _fetch_hs300_pe() -> tuple[float, str]:
    """沪深300 PE_TTM 多源链：东财 dcfm → akshare（如已装）→ yfinance。"""
    try:
        return _fetch_hs300_pe_dcfm(), "东财 dcfm 沪深300 PE_TTM"
    except FundamentalsSourceError:
        pass
    try:
        return _fetch_hs300_pe_akshare(), "akshare 乐咕乐股 沪深300 滚动市盈率"
    except FundamentalsSourceError:
        pass
    return _yf_pe("000300.SS"), "yfinance 000300.SS trailingPE"


def fetch_cn_erp(treasury: dict[str, Any] | None = None) -> dict[str, Any]:
    """A股股权风险溢价 ERP = 沪深300 盈利收益率 − 中债 10Y（%）。

    沪深300 PE_TTM 多源降级：东财 dcfm（无额外依赖）→ akshare（如环境已装）
    → yfinance（共享 IP 常触发 429，兜底）。
    """
    if treasury is None:
        treasury = fetch_treasury()
    cn10 = (treasury.get("cn") or {}).get("cn_10y")
    if cn10 is None:
        raise FundamentalsSourceError("中债10Y缺失，无法计算A股ERP")
    pe, ey_source = _fetch_hs300_pe()
    ey = round(100.0 / float(pe), 2)
    return {
        "earnings_yield": ey,
        "risk_free": round(float(cn10), 2),
        "erp": round(ey - float(cn10), 2),
        "as_of": (treasury.get("as_of_cn") or None),
        "pe_ttm": round(float(pe), 2),
        "ey_source": ey_source,
    }


# ── ERP 历史走势（股债性价比长序列）────────────────────────────────────────
# 口径：ERP = 盈利收益率(1/PE_TTM×100) − 10Y 国债收益率，与上方现值一致。
# 历史：A股取乐咕乐股沪深300 PE_TTM 全史（2005-04 起，日频，与中证指数公司
# 官方口径一致）；美股取 multpl.com 月度盈利收益率（溯源自 Robert Shiller
# 耶鲁数据，1871 起），按 as-of 前向填充对齐到国债日频。


def fetch_hs300_pe_history() -> dict[str, float]:
    """沪深300 PE_TTM 全史日频（乐咕乐股，via akshare），升序 {date: pe}。

    与现值链的 akshare 分支同源同口径（滚动市盈率），保证卡片与趋势图衔接一致。
    akshare 未安装或接口失败时抛错，由 service 层降级。
    """
    try:
        import akshare as ak
    except ImportError as exc:
        raise FundamentalsSourceError(f"akshare 未安装：{exc}") from exc
    try:
        df = ak.stock_index_pe_lg(symbol="沪深300")
    except Exception as exc:  # noqa: BLE001
        raise FundamentalsSourceError(f"akshare 沪深300 PE 历史: {exc}") from exc
    out: dict[str, float] = {}
    # strict=False：akshare 表格行与列对齐由其内部保证，长度不齐时截到较短侧。
    for d, pe in zip(df["日期"], df["滚动市盈率"], strict=False):
        pe = _num(pe)
        if pe is not None and pe > 0:
            out[str(d)] = float(pe)
    if not out:
        raise FundamentalsSourceError("沪深300 PE 历史无数据")
    return out


def fetch_cn_erp_history(
    lookback_days: int = 730,
    treasury_hist: dict[str, dict[str, float | None]] | None = None,
) -> dict[str, float]:
    """A股 ERP 历史日频 = 1/沪深300 PE_TTM×100 − 中债 10Y。

    PE 与国债取交集日期（两侧都是交易日序列）；treasury_hist 可由调用方
    传入避免重复翻页取数。
    """
    if treasury_hist is None:
        treasury_hist = fetch_treasury_history(lookback_days)
    cn10 = {d: v.get("cn_10y") for d, v in treasury_hist.items() if v.get("cn_10y") is not None}
    if not cn10:
        raise FundamentalsSourceError("中债10Y历史缺失，无法计算A股ERP历史")
    pe_hist = fetch_hs300_pe_history()
    out: dict[str, float] = {}
    for d, pe in pe_hist.items():
        r10 = cn10.get(d)
        if r10 is not None:
            out[d] = round(100.0 / pe - r10, 2)
    if not out:
        raise FundamentalsSourceError("A股ERP历史无交集日期")
    return _tail_days(out, lookback_days)


_MULTIPL_EY_TABLE_URL = "https://www.multpl.com/s-p-500-earnings-yield/table/by-month"
_MULTIPL_CAPE_TABLE_URL = "https://www.multpl.com/shiller-pe/table/by-month"
_MONTH_ABBR = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def _fetch_multpl_monthly(url: str, *, require_percent: bool) -> dict[str, float]:
    """抓 multpl.com 月度表格页，返回升序 {月初日期: 数值}。失败重试 3 次后抛错。

    require_percent=True 时只接收带 ``%`` 的单元格（盈利收益率等百分比序列），
    False 时接收裸数值（CAPE 等倍数序列）。

    值单元格形如 ``<td>\\n&#x2002;\\n42.35\\n</td>``——**必须先剥 HTML 实体**：
    em space 的实体写法 ``&#x2002;`` 本身含数字 2002，不剥的话裸数值正则会把
    2002 当成读数抓走（实测整表变成同一个值 2002.0）。带 ``%`` 的序列因为正则
    要求百分号而侥幸躲过，裸数值序列则必踩。
    """
    last_exc: Exception | None = None
    for attempt in range(3):
        if attempt:
            time.sleep(1.5)
        try:
            resp = requests.get(
                url,
                headers={**_HEADERS, "Referer": "https://www.multpl.com/"},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            last_exc = exc
            continue
        rows = re.findall(r"<td[^>]*>([^<]+)</td>\s*<td[^>]*>([^<]+)</td>", resp.text)
        out: dict[str, float] = {}
        for dstr, vstr in rows:
            m = re.match(r"([A-Z][a-z]{2}) \d{1,2}, (\d{4})", dstr.strip())
            if not m or m.group(1) not in _MONTH_ABBR:
                continue
            if require_percent:
                v = re.search(r"(-?[\d.]+)%", vstr)
            else:
                clean = re.sub(r"&#x[0-9a-fA-F]+;|&\w+;", " ", vstr).replace(",", "")
                v = re.search(r"(-?\d+\.?\d*)", clean)
            if not v:
                continue
            month = _MONTH_ABBR[m.group(1)]
            out[f"{m.group(2)}-{month:02d}-01"] = float(v.group(1))
        if out:
            return dict(sorted(out.items()))
        last_exc = FundamentalsSourceError("multpl.com 月度表未能解析")
    raise FundamentalsSourceError(f"multpl.com 月度表 {url}: {last_exc}")


def fetch_us_ey_history() -> dict[str, float]:
    """S&P500 盈利收益率月度全史（multpl.com 表格页），升序 {月初日期: ey%}。

    multpl 的 EPS 序列溯源自 Robert Shiller（耶鲁）1871 年起的数据；月频是
    盈利收益率的学术标准频率（EPS 随财报季跳变，价格月内波动平滑掉）。
    """
    return _fetch_multpl_monthly(_MULTIPL_EY_TABLE_URL, require_percent=True)


def fetch_us_cape_history() -> dict[str, float]:
    """S&P500 CAPE（Shiller PE）月度全史（multpl.com），升序 {月初日期: cape}。

    CAPE = 实际价格 / 过去 10 年通胀调整后实际盈利均值（Robert Shiller，耶鲁）。
    用 10 年平均盈利做分母，正是为了绕开 PE_TTM / Fed Model 口径在盈利拐点处的
    失真——2009-03 金融危机大底 TTM 盈利崩塌快于股价，股债收益差误报「贵」，
    而 CAPE 当月 13.3（全史 P66）正确指向便宜。作为不受利率水平污染的估值对照。
    """
    return _fetch_multpl_monthly(_MULTIPL_CAPE_TABLE_URL, require_percent=False)


def _tail_days(series: dict[str, float], lookback_days: int) -> dict[str, float]:
    """按自然日从尾部截取 lookback_days 天（各历史接口的统一口径）。"""
    if not series:
        return series
    cutoff = (datetime.now(UTC) - timedelta(days=int(lookback_days))).date().isoformat()
    return {d: v for d, v in series.items() if d >= cutoff}


# ── 估值分位对照（不受利率水平污染）──────────────────────────────────────────
# 存在理由：股债收益差（Fed Model 口径，即本模块 fetch_*_erp）在 1990 年后与
# 名义 10Y 的相关系数实测 -0.83（R²≈0.69）——它有约七成方差由债券端解释，
# 是「股债比价」而非「股票贵不贵」。这里补两个纯估值分位做对照：
#   · 美股 CAPE（Shiller PE，10 年平均实际盈利，避开盈利拐点失真）
#   · A股 沪深300 PE_TTM 自身分位（中债 10Y 区间窄，A股股债差 96% 由股票端
#     驱动，故 PE 分位与之相关但仍能揭示「利率下行推高股债差」的假机会）
# 两者与股债收益差**同时到极值**才是强信号；打架时说明「股票贵但债券更贵」，
# 那是配置结论而非择时结论。

#: 分位标定窗口起点。刻意不用全史——理由随各自序列注明，且两个数值都返回，
#: 由前端同时披露，避免「分位是取样窗口的函数」这一点被藏起来。
_CAPE_CALIB_FROM = "1950-01-01"
_CN_PE_CALIB_FROM = "2010-01-01"


def percentile_rank(values: list[float], x: float) -> float:
    """x 在 values 中的百分位（≤x 的占比，0–100）。空序列返回 nan。"""
    if not values:
        return float("nan")
    return round(100.0 * sum(1 for v in values if v <= x) / len(values), 1)


def _valuation_snapshot(hist: dict[str, float], calib_from: str) -> dict[str, Any]:
    """把「全史序列」压成一个估值分位快照。

    percentile 用标定窗口（可比口径），percentile_full 用全史（长周期背景）；
    两个都返回，前端并列展示——分位随取样窗口漂移是这类指标最大的坑，
    只报一个数就等于把坑藏起来。
    """
    if not hist:
        raise FundamentalsSourceError("估值历史为空")
    as_of = max(hist)
    value = float(hist[as_of])
    calib = [v for d, v in hist.items() if d >= calib_from]
    full = list(hist.values())
    return {
        "value": round(value, 2),
        "as_of": as_of,
        "percentile": percentile_rank(calib, value),
        "percentile_full": percentile_rank(full, value),
        "calib_from": calib_from[:4],
        "calib_n": len(calib),
        "full_from": min(hist)[:4],
        "full_n": len(full),
    }


def fetch_us_cape(hist: dict[str, float] | None = None) -> dict[str, Any]:
    """美股 CAPE 现值 + 分位快照。hist 可复用已取到的全史避免重复抓取。

    标定窗口取 1950 年起：战后现代会计与指数编制口径，且涵盖 1970s 滞胀高利率、
    2000 泡沫、2009 危机等多种利率/通胀环境（920 个月）。1871–1949 段口径不可比，
    但仍保留在 percentile_full 里作长周期背景。
    """
    if hist is None:
        hist = fetch_us_cape_history()
    return _valuation_snapshot(hist, _CAPE_CALIB_FROM)


def fetch_cn_pe(hist: dict[str, float] | None = None) -> dict[str, Any]:
    """A股 沪深300 PE_TTM 现值 + 分位快照。hist 可复用已取到的全史。

    标定窗口取 2010 年起：股权分置改革后全流通基本完成，与 2005–2007 小流通盘
    时代的 PE 口径不可比——全史 P95≈34 几乎全部由 2007 泡沫单独贡献，用全史标定
    会把「不贵」的门槛抬到失去分辨力。
    """
    if hist is None:
        hist = fetch_hs300_pe_history()
    return _valuation_snapshot(hist, _CN_PE_CALIB_FROM)


def fetch_us_erp_history(
    lookback_days: int = 730,
    treasury_hist: dict[str, dict[str, float | None]] | None = None,
) -> dict[str, float]:
    """美股 ERP 历史 = S&P500 盈利收益率(月频) − 美债 10Y(日频)。

    EY 是月频，按 as-of 前向填充对齐到国债日频日期：日度 ERP 变动来自利率端，
    EY 随财报季月度跳变。这与 Fed Model 研究的标准做法一致。注意月度表滞后
    于现值卡片的主页日频值（2026-08 实测约滞后数月），图末端与卡片可能有小差。
    """
    if treasury_hist is None:
        treasury_hist = fetch_treasury_history(lookback_days)
    us10 = {d: v.get("us_10y") for d, v in treasury_hist.items() if v.get("us_10y") is not None}
    if not us10:
        raise FundamentalsSourceError("美债10Y历史缺失，无法计算美股ERP历史")
    ey_hist = fetch_us_ey_history()
    ey_dates = sorted(ey_hist)
    out: dict[str, float] = {}
    # 双指针 as-of join：ey_dates 与 us10 均升序。
    i = -1
    for d in sorted(us10):
        while i + 1 < len(ey_dates) and ey_dates[i + 1] <= d:
            i += 1
        if i >= 0:
            out[d] = round(ey_hist[ey_dates[i]] - us10[d], 2)
    if not out:
        raise FundamentalsSourceError("美股ERP历史无交集日期")
    return _tail_days(out, lookback_days)


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
# - VIX：Yahoo v8 图表 API（query1，period1/period2 取日线，不走 yfinance）
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
    """CBOE VIX 历史日线（恐慌指数），via Yahoo v8 图表 API。失败抛错。

    用 period1/period2 时间戳而非 range，两个原因：

    1. ``range=730d`` 被 Yahoo 解释为 730 **根 K 线**（交易日），不是 730 个
       自然日——实测返回 2023-10-30 起共 730 行，约 2.8 个自然年。这与国债/
       两融历史的自然日口径不一致。改用时间戳后 lookback_days 就是字面意思。
    2. ``range=max`` 会被 Yahoo 静默降频到**月线**（实测 dataGranularity=1mo，
       1990-2026 仅 440 行），没法喂日频叠加图；而 period1/period2 在同样
       20 年跨度上仍返回日线（实测 5,379 行，granularity=1d）。
    """
    # 用 aware UTC：naive utcnow().timestamp() 会被按本地时区解释
    # （UTC+8 下偏 8 小时），跨零点时可能少算一天。
    days = max(5, int(lookback_days))
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    return _fetch_yahoo_closes(
        "^VIX",
        {
            "interval": "1d",
            "period1": int(start.timestamp()),
            "period2": int(end.timestamp()),
        },
    )


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

    翻页拉全史：先取最新一页，再以本页最旧一根的前一日为 end 向前翻页。
    腾讯返回为「最新在前」，故用 min/max 兼容排序，避免翻页方向算反导致只拿到近期一页。
    """
    out: dict[str, float] = {}
    end = ""
    for _ in range(max(12, int(lookback_days) // 250 + 5)):
        param = f"{code},day,,{end},800" if end else f"{code},day,,,800"
        payload = _get_json(_TENCENT_KLINE_URL, {"param": param})
        node = (payload.get("data") or {}).get(code) or {}
        days = node.get("day") or []
        if not days:
            break
        page_dates: list[str] = []
        for row in days:
            v = _num(row[2]) if len(row) > 2 else None  # [date, open, close, ...]
            if row[0] and v is not None:
                d = str(row[0])[:10]
                out[d] = v
                page_dates.append(d)
        if len(out) >= int(lookback_days):
            break
        oldest = min(page_dates)
        # 没有更早期数据（端点忽略 end 或已到头）则停止翻页，避免空转
        if end and oldest >= end:
            break
        end = (datetime.strptime(oldest, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        time.sleep(0.15)  # 翻页限速
    if not out:
        raise FundamentalsSourceError(f"指数历史 {code} 无数据")
    return dict(sorted(out.items()))


def _parse_fred_csv(text: str, series_id: str) -> dict[str, float]:
    """FRED CSV 文本 -> 升序 {date: value}。缺值 '.' 跳过。"""
    out: dict[str, float] = {}
    for i, line in enumerate(text.splitlines()):
        if i == 0 or "," not in line:
            continue  # 表头 / 空行
        date, _, raw = line.partition(",")
        v = _num(raw.strip().strip('"'))
        if v is not None and date:
            out[date] = v
    if not out:
        raise FundamentalsSourceError(f"FRED {series_id} 无数据")
    return out


def _fetch_fred_series(series_id: str, *, cosd: str | None = None) -> dict[str, float]:
    """FRED 官方 CSV -> 升序 {date: value}（美联储圣路易斯联储，无需 API key）。

    cosd 限定起始日期控制拉取量；FRED 对连续请求会限流（HTTP 404/挑战页），
    失败退避 4 秒重试一次。
    """
    params: dict[str, Any] = {"id": series_id}
    if cosd:
        params["cosd"] = cosd
    last_exc: Exception | None = None
    for attempt in range(2):
        if attempt:
            time.sleep(4.0)
        try:
            resp = requests.get(_FRED_CSV_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT)
            resp.raise_for_status()
            return _parse_fred_csv(resp.text, series_id)
        except (requests.RequestException, FundamentalsSourceError) as exc:
            last_exc = exc
    raise FundamentalsSourceError(f"FRED {series_id}: {last_exc}")


def fetch_fred_index_history(series_id: str) -> dict[str, float]:
    """FRED 官方 CSV -> 升序 {date: value}（美联储圣路易斯联储）。"""
    return _fetch_fred_series(series_id)


# ── 美国宏观（FRED 公开 CSV，无需 API key）──────────────────────────────
# 对齐 themarketmemo「20 charts」缺口：就业（初请/续请/非农）、成屋销售、
# Case-Shiller 房价、汽车销量、WEI 周经济指数、美国 PPI/CPI 同比（配铜金比/
# 油金比）、耐用品订单（ISM PMI 因授权问题已从 FRED 下架——NAPM 404 实测，
# 以耐用品订单同比替代「制造业订单&采购」视角）、高收益债利差（信用风险，
# 搭配 VIX 评估系统性风险）。全部为公开序列，周/月频，缓存 6 小时。

_FRED_PAUSE = 1.2  # 序列间限速，避免触发 FRED 连发限流

# transform: level=原值 | ma4=4 周滚动均值（初请平滑）| yoy=同比 %
_US_MACRO_SPEC: list[dict[str, Any]] = [
    {
        "key": "icwa",
        "series": "ICSA",
        "cosd": "2020-01-01",
        "name_cn": "初请失业金",
        "label": "初请失业金（4 周均值）",
        "unit": "人",
        "freq": "周",
        "transform": "ma4",
    },
    {
        "key": "ccwa",
        "series": "CCSA",
        "cosd": "2020-01-01",
        "name_cn": "续请失业金",
        "label": "续请失业金",
        "unit": "人",
        "freq": "周",
        "transform": "level",
    },
    {
        "key": "payems_yoy",
        "series": "PAYEMS",
        "cosd": "2014-01-01",
        "name_cn": "非农就业同比",
        "label": "非农就业同比",
        "unit": "%",
        "freq": "月",
        "transform": "yoy",
    },
    {
        "key": "hsales",
        "series": "HSN1F",
        "cosd": "2014-01-01",
        "name_cn": "新屋销售",
        "label": "新屋销售（折年率）",
        "unit": "千套",
        "freq": "月",
        "transform": "level",
    },
    {
        "key": "cshpi_yoy",
        "series": "CSUSHPINSA",
        "cosd": "2014-01-01",
        "name_cn": "Case-Shiller 房价同比",
        "label": "Case-Shiller 房价同比",
        "unit": "%",
        "freq": "月",
        "transform": "yoy",
    },
    {
        "key": "altsa",
        "series": "TOTALSA",
        "cosd": "2014-01-01",
        "name_cn": "汽车销量",
        "label": "汽车销量（折年率）",
        "unit": "百万辆",
        "freq": "月",
        "transform": "level",
    },
    {
        "key": "wei",
        "series": "WEI",
        "cosd": "2020-01-01",
        "name_cn": "WEI 周经济指数",
        "label": "WEI 周经济指数",
        "unit": "%",
        "freq": "周",
        "transform": "level",
    },
    {
        "key": "ppiaco_yoy",
        "series": "PPIFIS",
        "cosd": "2014-01-01",
        "name_cn": "美 PPI 同比",
        "label": "美国 PPI 同比（最终需求）",
        "unit": "%",
        "freq": "月",
        "transform": "yoy",
    },
    {
        "key": "cpiaucsl_yoy",
        "series": "CPIAUCSL",
        "cosd": "2014-01-01",
        "name_cn": "美 CPI 同比",
        "label": "美国 CPI 同比",
        "unit": "%",
        "freq": "月",
        "transform": "yoy",
    },
    {
        "key": "dgorder_yoy",
        "series": "DGORDER",
        "cosd": "2014-01-01",
        "name_cn": "耐用品订单同比",
        "label": "耐用品订单（新订单）同比",
        "unit": "%",
        "freq": "月",
        "transform": "yoy",
    },
    {
        "key": "hy_oas",
        "series": "BAMLH0A0HYM2",
        "cosd": "2020-01-01",
        "name_cn": "高收益债利差",
        "label": "高收益债 OAS 利差",
        "unit": "%",
        "freq": "日",
        "transform": "level",
    },
]

_US_NOTES: dict[str, str] = {
    "icwa": "取 4 周均值过滤周度杂音；趋势持续上行 = 就业恶化先行信号",
    "ccwa": "初请之后第二道风向标：持续攀升 = 失业周期拉长",
    "payems_yoy": "同比转负为就业萎缩信号；月度净增骤降是衰退前兆",
    "hsales": "折年率；成屋销售受 NAR 授权 FRED 仅存近一年，改用 Census 新屋销售（全史）",
    "cshpi_yoy": "全国房价指数（发布滞后约 2 个月）；财富效应支撑消费",
    "altsa": "折年率；大件可选消费风向标",
    "wei": "纽约联储周频 GDP 同步代理（11 项周度指标合成），0 为增长/收缩分界",
    "ppiaco_yoy": "最终需求口径（PPIFIS），配铜金比看工业品通胀",
    "cpiaucsl_yoy": "配油金比看整体通胀",
    "dgorder_yoy": "ISM PMI 因授权未上 FRED，以耐用品订单同比看制造业订单景气",
    "hy_oas": "高收益债相对国债利差，搭配 VIX 评估系统性风险；>6% 历史警戒",
}


def _yoy_pct(points: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """月度序列转同比 %（索引距离 12 = 12 个月）。"""
    return [
        (d, round((v / points[i - 12][1] - 1) * 100, 2))
        for i, (d, v) in enumerate(points)
        if i >= 12
    ]


def _ma4(points: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """周度序列转 4 周滚动均值。"""
    return [
        (d, round(sum(v for _, v in points[i - 3 : i + 1]) / 4, 1))
        for i, (d, _v) in enumerate(points)
        if i >= 3
    ]


def _build_us_macro_item(
    spec: dict[str, Any], raw: dict[str, float]
) -> tuple[dict[str, Any], dict[str, Any]]:
    points = sorted(raw.items())
    transform = spec["transform"]
    if transform == "ma4":
        derived = _ma4(points)
    elif transform == "yoy":
        derived = _yoy_pct(points)
    else:
        derived = [(d, round(v, 2)) for d, v in points]
    if not derived:
        raise FundamentalsSourceError(f"FRED {spec['series']} 派生序列为空")
    note = _US_NOTES.get(spec["key"], "")
    if spec["key"] == "icwa" and points:
        note = f"本周 {points[-1][1] / 1e4:.1f} 万 · " + note
    if spec["key"] == "payems_yoy" and len(points) >= 2:
        # PAYEMS 单位千人：月净增 = 本月 - 上月
        net = points[-1][1] - points[-2][1]
        note = f"月净增 {net / 10:.1f} 万 · 总 {points[-1][1] / 1e5:.2f} 亿人 · " + note
    item = {
        "key": spec["key"],
        "name_cn": spec["name_cn"],
        "freq": spec["freq"],
        "date": derived[-1][0],
        "value": derived[-1][1],
        "note_cn": note,
    }
    series = {
        "label": spec["label"],
        "unit": spec["unit"],
        "dates": [d for d, _ in derived],
        "values": [v for _, v in derived],
    }
    return item, series


def fetch_us_macro() -> dict[str, Any]:
    """美国宏观批量取数（FRED，就业/房产/汽车/WEI/物价/订单/信用利差）。

    单序列失败只进 errors，其余照常返回；序列间 sleep 限速。
    """
    items: list[dict[str, Any]] = []
    series: dict[str, Any] = {}
    errors: list[str] = []
    for spec in _US_MACRO_SPEC:
        try:
            raw = _fetch_fred_series(spec["series"], cosd=spec["cosd"])
            item, ser = _build_us_macro_item(spec, raw)
            items.append(item)
            series[spec["key"]] = ser
        except FundamentalsSourceError as exc:
            errors.append(f"美国宏观 {spec['name_cn']}: {exc}")
        time.sleep(_FRED_PAUSE)
    as_of = max((it["date"] for it in items if it["date"]), default=None)
    return {"as_of": as_of, "items": items, "series": series, "errors": errors}


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


def _yf_closes(tickers: list[str], period: str = "6mo") -> dict[str, list[tuple[str, float]]]:
    """yf.download 一批 ticker 的日线收盘，返回 {ticker: [(date, close), ...]} 升序。"""
    import pandas as pd
    import yfinance as yf

    data = yf.download(tickers, period=period, interval="1d", progress=False, group_by="ticker")
    if data.empty:
        raise FundamentalsSourceError("yfinance 返回空")
    multi = isinstance(data.columns, pd.MultiIndex)
    out: dict[str, list[tuple[str, float]]] = {}
    for t in tickers:
        try:
            s = (data[t]["Close"] if multi else data["Close"]).dropna()
            if len(s) < 2:
                continue
            out[t] = [(str(d.date()), float(v)) for d, v in s.items()]
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
    """11 行业 ETF 相对 SPY 的相对强度线图 + 1 月相对强度排序。

    每个行业一条「相对净值线」：ETF/SPY 比价以窗口起点归一为 100，
    线在 100 上方 = 期间跑赢 SPY。risk_off 类（必选/医疗/公用）整体在上方
    = 市场避险；risk_on 类在上方 = 风险偏好上升。另给可选/必选消费比价
    XLY/XLP：升 = 风险偏好、降 = 避险。via yfinance，失败返回 None。
    """
    try:
        tickers = [t for t, _, _ in _ETF_SECTORS] + ["SPY"]
        closes = _yf_closes(tickers, period="6mo")
        if "SPY" not in closes:
            return None
        px = {t: dict(pts) for t, pts in closes.items()}
        # 对齐到所有行业的公共交易日（美股 ETF 交易日历一致，交集≈全集）
        common = sorted(
            set(px["SPY"]).intersection(*(px[t] for t, _, _ in _ETF_SECTORS if t in px))
        )
        n = len(common)
        if n < 25:
            return None
        spy_line = [px["SPY"][d] for d in common]
        spy_1m = spy_line[-1] / spy_line[n - 22] - 1

        items: list[dict[str, Any]] = []
        for code, name, bias in _ETF_SECTORS:
            if code not in px:
                continue
            line = [px[code][d] for d in common]
            base = line[0] / spy_line[0]
            etf_1m = line[-1] / line[n - 22] - 1
            items.append(
                {
                    "code": code,
                    "name": name,
                    "bias": bias,
                    "ret_1m": round(etf_1m * 100, 2),
                    "rel_1m": round((etf_1m - spy_1m) * 100, 2),
                    "rel_line": [
                        round(v / s / base * 100, 2)
                        for v, s in zip(line, spy_line, strict=True)
                    ],
                }
            )
        items.sort(key=lambda x: x["rel_1m"], reverse=True)
        off_avg = sum(i["rel_1m"] for i in items if i["bias"] == "risk_off") / max(
            1, sum(1 for i in items if i["bias"] == "risk_off")
        )
        regime = "risk_off" if off_avg > 0 else "risk_on"
        xly_xlp: dict[str, Any] | None = None
        if "XLY" in px and "XLP" in px:
            xly_line = [px["XLY"][d] for d in common]
            xlp_line = [px["XLP"][d] for d in common]
            ratio = xly_line[-1] / xlp_line[-1]
            q3 = max(0, n - 63)

            def chg(idx: int) -> float:
                return (ratio / (xly_line[idx] / xlp_line[idx]) - 1) * 100

            xly_xlp = {
                "ratio": round(ratio, 3),
                "chg_1m": round(chg(n - 22), 2),
                "chg_3m": round(chg(q3), 2),
            }
        return {
            "dates": common,
            "items": items,
            "regime": regime,
            "spy_1m": round(spy_1m * 100, 2),
            "xly_xlp": xly_xlp,
        }
    except Exception:  # noqa: BLE001
        return None
