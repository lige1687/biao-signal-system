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
                "fields": "f12,f14,f2,f3,f8,f20,f62,f184,f104,f105",
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


def _fetch_macro_report(report_name: str, *, page_size: int = 1) -> dict[str, Any]:
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
    return rows[0]


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
