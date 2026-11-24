"""Official live incremental refresh for A-share margin buy share."""

from __future__ import annotations

import copy
import datetime as dt
import json
import os
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from lei_signal.fundamentals.erp_refresh import _atomic
from lei_signal.market_context import microstructure_funding as mf

_MAIN_CARD_ID = "cn-margin-buy-share-a-stocks"
_MA20_CARD_ID = "cn-margin-buy-share-a-stocks-ma20"
_LIVE_FILENAME = "cn_funding_live.json"
_FROZEN_RELATIVE = Path("web/public/research/microstructure-observations-20261108/funding.json")
_DEFAULT_CACHE = Path.home() / ".lei_signal_lab" / "cache"


def _frozen_packet_path() -> Path:
    for base in (Path(__file__).resolve(), Path.cwd().resolve()):
        for parent in (base, *base.parents):
            candidate = parent / _FROZEN_RELATIVE
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(f"Frozen funding baseline not found: {_FROZEN_RELATIVE}")


def _live_packet_path(cache: Path | None = None) -> Path:
    return (cache or _DEFAULT_CACHE) / _LIVE_FILENAME


def _sse_detail_url(compact_date: str, page: int) -> str:
    query = urlencode(
        {
            "isPagination": "true",
            "tabType": "mxtype",
            "detailsDate": compact_date,
            "pageHelp.pageSize": "5000",
            "pageHelp.pageNo": str(page),
            "pageHelp.beginPage": str(page),
            "pageHelp.cacheSize": "1",
            "pageHelp.endPage": str(page),
        }
    )
    return f"{mf.SSE_DETAIL_URL}?{query}"


def _sse_turnover_url(compact_date: str) -> str:
    query = urlencode(
        {
            "sqlId": "COMMON_SSE_SJ_GPSJ_CJGK_MRGK_C",
            "PRODUCT_CODE": "01,03",
            "type": "inParams",
            "SEARCH_DATE": compact_date,
            "jsonCallBack": "callback",
        }
    )
    return f"{mf.SSE_TURNOVER_URL}?{query}"


def _szse_margin_url(day: str) -> str:
    query = urlencode(
        {
            "SHOWTYPE": "xlsx",
            "CATALOGID": "1837_xxpl",
            "TABKEY": "tab2",
            "txtDate": day,
            "txtZqdm": "",
            "random": "0.1",
        }
    )
    return f"{mf.SZSE_REPORT_URL}?{query}"


def _szse_turnover_url(day: str) -> str:
    query = urlencode(
        {
            "SHOWTYPE": "xlsx",
            "CATALOGID": "1803_sczm",
            "TABKEY": "tab1",
            "txtQueryDate": day,
            "random": "0.3",
        }
    )
    return f"{mf.SZSE_REPORT_URL}?{query}"


def _iter_weekdays(after_date: str, cutoff: str) -> list[str]:
    start = dt.date.fromisoformat(after_date) + dt.timedelta(days=1)
    end = dt.date.fromisoformat(cutoff)
    out: list[str] = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            out.append(cur.isoformat())
        cur += dt.timedelta(days=1)
    return out


def _format_yi(yuan: Decimal) -> str:
    return f"{yuan / Decimal('100000000'):.2f}亿元"


def _fetch_and_parse_day(day: str, work_dir: Path) -> dict[str, Any] | None:
    """Download one session from official SSE/SZSE endpoints and validate via microstructure_funding.

    Returns parsed metrics dict, or None if the date is an exchange holiday / unpublished session.
    Raises FundingDataError on partial corruption of an otherwise active session.
    """
    compact = day.replace("-", "")
    day_dir = work_dir / compact
    day_dir.mkdir(parents=True, exist_ok=True)

    p1_path = day_dir / mf._sse_detail_file(day, 1)
    p1_path.write_bytes(mf._request_bytes(_sse_detail_url(compact, 1), mf.SSE_HEADERS))
    first_page = mf._parse_sse_json(p1_path)
    help_data = first_page.get("pageHelp") or {}
    page_count = int(help_data.get("pageCount") or 0)
    first_rows = first_page.get("result") or []

    sse_turnover_path = day_dir / mf._sse_turnover_file(day)
    sse_turnover_path.write_bytes(mf._request_bytes(_sse_turnover_url(compact), mf.SSE_HEADERS))
    sse_turnover_doc = mf._parse_sse_json(sse_turnover_path)
    turnover_rows = sse_turnover_doc.get("result") or []

    if page_count < 1 or not first_rows or not turnover_rows:
        return None  # 休市或当日融资明细尚未公布

    detail_paths = [p1_path]
    for page in range(2, page_count + 1):
        p_path = day_dir / mf._sse_detail_file(day, page)
        p_path.write_bytes(mf._request_bytes(_sse_detail_url(compact, page), mf.SSE_HEADERS))
        detail_paths.append(p_path)

    sz_margin_path = day_dir / mf._szse_margin_file(day)
    sz_margin_bytes = mf._request_bytes(_szse_margin_url(day), mf.SZSE_HEADERS)
    if not sz_margin_bytes.startswith(b"PK"):
        return None
    sz_margin_path.write_bytes(sz_margin_bytes)

    sz_turnover_path = day_dir / mf._szse_turnover_file(day)
    sz_turnover_bytes = mf._request_bytes(_szse_turnover_url(day), mf.SZSE_HEADERS)
    if not sz_turnover_bytes.startswith(b"PK"):
        return None
    sz_turnover_path.write_bytes(sz_turnover_bytes)

    try:
        sh_margin, sh_eligible, sh_total, sh_etfs = mf._sse_margin_amount(detail_paths, day)
        sh_turnover, _, _ = mf._sse_stock_turnover(sse_turnover_path, day)
        sz_margin, sz_eligible, sz_total, sz_etfs = mf._szse_margin_amount(sz_margin_path)
        sz_turnover, _, _ = mf._szse_stock_turnover(sz_turnover_path)
    except (mf.FundingDataError, IndexError, ValueError):
        return None

    ratio = mf.calculate_ratio(sh_margin, sz_margin, sh_turnover, sz_turnover)
    return {
        "date": day,
        "value": float(ratio),
        "shMarginBuyYuan": sh_margin,
        "szMarginBuyYuan": sz_margin,
        "shTurnoverYuan": sh_turnover,
        "szTurnoverYuan": sz_turnover,
        "shEligibleCount": sh_eligible,
        "szEligibleCount": sz_eligible,
        "shExcludedEtfCount": sh_etfs,
        "szExcludedEtfCount": sz_etfs,
        "shMarginRows": sh_total,
        "szMarginRows": sz_total,
    }


def _find_card(packet: dict[str, Any], card_id: str) -> dict[str, Any]:
    for card in packet.get("cards") or []:
        if card.get("id") == card_id:
            return card
    raise KeyError(f"Missing card in funding packet: {card_id}")


def read_cn_funding(cache: Path | None = None) -> dict[str, Any]:
    """Return live CN margin buy share packet when present, else frozen baseline."""
    live = _live_packet_path(cache)
    target = live if live.is_file() else _frozen_packet_path()
    return json.loads(target.read_text(encoding="utf-8"))


def refresh_cn_funding(
    output: Path,
    *,
    cutoff: str,
    cache: Path | None = None,
    day_fetcher: Callable[[str, Path], dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Append newly published official SSE/SZSE sessions up to cutoff without touching frozen JSON."""
    output.mkdir(parents=True, exist_ok=True)
    cache_dir = cache or _DEFAULT_CACHE
    base_packet = copy.deepcopy(read_cn_funding(cache_dir))

    main_card = _find_card(base_packet, _MAIN_CARD_ID)
    ma20_card = _find_card(base_packet, _MA20_CARD_ID)

    by_date: dict[str, float | None] = {
        str(row["date"]): row.get("value")
        for row in (main_card.get("points") or [])
        if row.get("date")
    }
    valid_dates = sorted(d for d, v in by_date.items() if v is not None)
    last_date = valid_dates[-1] if valid_dates else "2025-09-17"

    fetcher = day_fetcher or _fetch_and_parse_day
    added_rows: list[dict[str, Any]] = []
    for day in _iter_weekdays(last_date, cutoff):
        if day in by_date and by_date[day] is not None:
            continue
        parsed = fetcher(day, output)
        if parsed is None or parsed.get("value") is None:
            continue
        by_date[day] = float(parsed["value"])
        added_rows.append(parsed)

    points = [{"date": d, "value": by_date[d]} for d in sorted(by_date)]
    percentiles = mf.strict_prior_percentiles(points, window=250)
    ma20_points = mf.rolling_mean_points(points, window=20)
    ma20_percentiles = mf.strict_prior_percentiles(ma20_points, window=250)

    now_iso = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    base_packet["generatedAt"] = now_iso
    main_card["points"] = points
    main_card["percentiles"] = percentiles
    main_card["refreshedAt"] = now_iso
    main_card["refreshMode"] = "live"

    ma20_card["points"] = ma20_points
    ma20_card["percentiles"] = ma20_percentiles
    ma20_card["refreshedAt"] = now_iso
    ma20_card["refreshMode"] = "live"

    valid_points = [p for p in points if p["value"] is not None]
    sample_start = valid_points[0]["date"] if valid_points else ""
    sample_end = valid_points[-1]["date"] if valid_points else ""
    latest_pctl = percentiles[-1]["value"] if percentiles else None

    if added_rows and added_rows[-1].get("date") == sample_end and "shMarginBuyYuan" in added_rows[-1]:
        latest = added_rows[-1]
        sh_m = Decimal(str(latest["shMarginBuyYuan"]))
        sz_m = Decimal(str(latest["szMarginBuyYuan"]))
        sh_t = Decimal(str(latest["shTurnoverYuan"]))
        sz_t = Decimal(str(latest["szTurnoverYuan"]))
        main_card["latestDetails"] = [
            {"label": "融资买入额", "value": _format_yi(sh_m + sz_m)},
            {"label": "沪深A股成交额", "value": _format_yi(sh_t + sz_t)},
            {"label": "融资买入额 · 上交所A股标的", "value": _format_yi(sh_m)},
            {"label": "融资买入额 · 深交所A股标的", "value": _format_yi(sz_m)},
            {"label": "成交额 · 上交所主板A股+科创板A股", "value": _format_yi(sh_t)},
            {"label": "成交额 · 深交所主板A股+创业板A股", "value": _format_yi(sz_t)},
            {"label": "融资标的股票数（沪/深）", "value": f"{latest['shEligibleCount']} / {latest['szEligibleCount']}只"},
            {"label": "排除ETF/基金融资行（沪/深）", "value": f"{latest['shExcludedEtfCount']} / {latest['szExcludedEtfCount']}条"},
            {"label": "融资源表总行数（沪/深）", "value": f"{latest['shMarginRows']} / {latest['szMarginRows']}条"},
            {"label": "有效同日配对日数", "value": f"{len(valid_points)}日"},
            {"label": "严格此前250日分位（中秩）", "value": f"{latest_pctl:.2f}%" if latest_pctl is not None else "—"},
            {"label": "样本期间", "value": f"{sample_start}—{sample_end}"},
            {"label": "源样本结束日", "value": sample_end},
        ]

    latest_ma20 = ma20_points[-1]["value"] if ma20_points else None
    latest_ma20_pctl = ma20_percentiles[-1]["value"] if ma20_percentiles else None
    if latest_ma20 is not None:
        ma20_card["latestDetails"] = [
            {"label": "最近一日20日均值", "value": f"{latest_ma20:.2f}%"},
            {
                "label": "严格此前250个有效20日均值分位（中秩）",
                "value": f"{latest_ma20_pctl:.2f}%" if latest_ma20_pctl is not None else "—",
            },
        ]

    # 同步沉淀沪深A股官方每日成交额历史（供实时成交额观测复用）
    turnover_by_date: dict[str, float] = {
        str(row["date"]): float(row["value_yi"])
        for row in (base_packet.get("turnoverPoints") or [])
        if row.get("date") and row.get("value_yi") is not None
    }
    for row in added_rows:
        if "shTurnoverYuan" in row and "szTurnoverYuan" in row:
            total_yi = (
                Decimal(str(row["shTurnoverYuan"])) + Decimal(str(row["szTurnoverYuan"]))
            ) / Decimal("100000000")
            turnover_by_date[str(row["date"])] = float(total_yi.quantize(Decimal("0.01")))
    if turnover_by_date:
        t_points = [{"date": d, "value_yi": turnover_by_date[d]} for d in sorted(turnover_by_date)]
        base_packet["turnoverPoints"] = t_points
        base_packet["latestTurnoverDate"] = t_points[-1]["date"]
        base_packet["latestTurnoverYi"] = t_points[-1]["value_yi"]

    payload_bytes = json.dumps(base_packet, ensure_ascii=False, indent=2).encode("utf-8")
    live_path = _live_packet_path(cache_dir)
    _atomic(live_path, payload_bytes)
    # 同步保存副本到本次工作目录，便于留痕审计（可保留在 cache/observations-*）。
    _atomic(output / _LIVE_FILENAME, payload_bytes)
    os.chmod(live_path, 0o644)
    return {
        "as_of": sample_end,
        "date": sample_end,
        "count": len(valid_points),
        "added": len(added_rows),
        "latest": round(float(valid_points[-1]["value"]), 4) if valid_points else None,
        "ma20": round(float(latest_ma20), 4) if latest_ma20 is not None else None,
    }
