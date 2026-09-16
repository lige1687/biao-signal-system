"""大盘云图 (dapanyuntu.com) A-share market breadth fetcher.

The site publishes a ready-computed **MA20 站上率** (percent of stocks
above their 20-day moving average) per 二级行业 (86 industries), updated
daily at 16:00 CST. This is the same metric our `breadth.py` computes
from raw bars, but already aggregated across the whole A-share market -
so it needs one HTTP request instead of 5000+ per-stock bar fetches.

Endpoint
--------
    GET https://sckd.dapanyuntu.com/api/api/industry_ma20_analysis_page?page=N

`page=0` is the most recent ~31 trading days; higher pages walk backwards
in time (page=5 reaches ~9 months back). Requires Referer + User-Agent
headers or the server returns 403.

Response shape
--------------
    {
      "data":       [[date_idx, industry_idx, value], ...],
      "dates":      ["2026-06-22", ...],       # 31 trading days
      "industries": ["专业服务", ...],          # 86 二级行业
      "page": 0, "start_date": "...", "end_date": "..."
    }

`value` is the MA20 站上率 in percent (0-100). A value of exactly 0.0
means "no data for this industry on this date", not "zero percent" -
the site uses 0 as its missing sentinel, so we drop those.

Aggregation
-----------
The whole-market breadth is the equal-weighted mean across industries
that reported data. This is an approximation of a cap-weighted or
count-weighted market breadth: an industry with 5 stocks counts as much
as one with 300. We label the result `research_proxy` accordingly and
keep our own per-stock computation as a cross-check.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date

_HOST = "https://sckd.dapanyuntu.com"
_PATH = "/api/api/industry_ma20_analysis_page"

_HEADERS = {
    "Referer": f"{_HOST}/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    ),
}

#: The site uses 0.0 as its "no data" sentinel rather than null.
_MISSING_SENTINEL = 0.0

SOURCE = "dapanyuntu_industry_ma20"
SOURCE_LICENSE = "dapanyuntu-public/web"


class DapanyuntuUnavailableError(RuntimeError):
    """The upstream breadth API could not be reached or returned garbage."""


@dataclass(frozen=True, slots=True)
class IndustryBreadthPage:
    """One page of industry-level MA20 站上率 readings."""

    page: int
    dates: tuple[date, ...]
    industries: tuple[str, ...]
    #: (date, industry) -> MA20 站上率 in percent. Missing readings absent.
    values: dict[tuple[date, str], float] = field(default_factory=dict)

    def market_breadth(self, as_of: date) -> tuple[float | None, int, int]:
        """Equal-weighted whole-market MA20 站上率 for one session.

        Returns ``(breadth_pct, reporting_industries, total_industries)``.
        `breadth_pct` is None when no industry reported that day.
        """
        readings = [
            v for (d, _ind), v in self.values.items() if d == as_of
        ]
        total = len(self.industries)
        if not readings:
            return None, 0, total
        return sum(readings) / len(readings), len(readings), total


def _fetch_page_raw(page: int, *, timeout: float, attempts: int) -> dict:
    """GET one page, retrying transient network failures."""
    url = f"{_HOST}{_PATH}?page={page}"
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=_HEADERS)  # noqa: S310
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                if response.status != 200:
                    raise DapanyuntuUnavailableError(
                        f"大盘云图 page={page} 返回 HTTP {response.status}"
                    )
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            last = exc
            if attempt < attempts - 1:
                # The endpoint throttles rapid sequential requests.
                time.sleep(1.5 * (attempt + 1))
            continue
        if not isinstance(payload, dict) or "data" not in payload:
            last = DapanyuntuUnavailableError(
                f"大盘云图 page={page} 返回意外结构: {list(payload)[:5]}"
            )
            if attempt < attempts - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            break
        return payload

    raise DapanyuntuUnavailableError(
        f"大盘云图 page={page} 获取失败: {last}"
    ) from last


def fetch_page(
    page: int = 0,
    *,
    timeout: float = 25.0,
    attempts: int = 3,
) -> IndustryBreadthPage:
    """Fetch and parse one page of industry MA20 站上率."""
    payload = _fetch_page_raw(page, timeout=timeout, attempts=attempts)

    raw_dates = payload.get("dates") or []
    raw_industries = payload.get("industries") or []
    dates = tuple(date.fromisoformat(str(d)) for d in raw_dates)
    industries = tuple(str(name) for name in raw_industries)

    values: dict[tuple[date, str], float] = {}
    for row in payload.get("data") or []:
        if not isinstance(row, (list, tuple)) or len(row) != 3:
            continue
        date_idx, industry_idx, value = row
        try:
            date_idx = int(date_idx)
            industry_idx = int(industry_idx)
            value = float(value)
        except (TypeError, ValueError):
            continue
        if not (0 <= date_idx < len(dates)) or not (0 <= industry_idx < len(industries)):
            continue
        # 0.0 is the site's missing-data sentinel, not a real zero reading.
        if value == _MISSING_SENTINEL:
            continue
        values[(dates[date_idx], industries[industry_idx])] = value

    return IndustryBreadthPage(
        page=int(payload.get("page", page)),
        dates=dates,
        industries=industries,
        values=values,
    )


def fetch_history(
    *,
    pages: int = 10,
    timeout: float = 25.0,
    attempts: int = 3,
    pause_seconds: float = 1.0,
) -> list[IndustryBreadthPage]:
    """Fetch `pages` pages walking backwards from the most recent.

    Each page carries ~31 trading days, so 10 pages reaches roughly
    310 sessions - enough for the 252-session minimum our percentile
    computation requires.

    Pages that fail are skipped rather than aborting the whole walk:
    a partial history is still useful, and the caller can see which
    dates are present.
    """
    out: list[IndustryBreadthPage] = []
    for page in range(pages):
        try:
            out.append(fetch_page(page, timeout=timeout, attempts=attempts))
        except DapanyuntuUnavailableError:
            continue
        if page < pages - 1:
            time.sleep(pause_seconds)
    return out


def market_breadth_series(
    pages: list[IndustryBreadthPage],
) -> dict[date, tuple[float, int, int]]:
    """Flatten pages into ``{as_of: (breadth_pct, reporting, total)}``.

    Overlapping dates across pages resolve to the reading from the page
    with more reporting industries, so a truncated page never overwrites
    a complete one.
    """
    series: dict[date, tuple[float, int, int]] = {}
    for page in pages:
        for as_of in page.dates:
            breadth, reporting, total = page.market_breadth(as_of)
            if breadth is None:
                continue
            existing = series.get(as_of)
            if existing is None or reporting > existing[1]:
                series[as_of] = (breadth, reporting, total)
    return series


__all__ = [
    "SOURCE",
    "SOURCE_LICENSE",
    "DapanyuntuUnavailableError",
    "IndustryBreadthPage",
    "fetch_history",
    "fetch_page",
    "market_breadth_series",
]
