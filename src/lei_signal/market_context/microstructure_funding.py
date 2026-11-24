"""Build dated, stock-only A-share financing participation observations."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree


AS_OF = "2026-11-05"
AS_OF_COMPACT = AS_OF.replace("-", "")
SESSION_DATES = (
    "2026-10-08", "2026-10-09", "2026-10-12", "2026-10-13", "2026-10-14",
    "2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20", "2026-10-21",
    "2026-10-22", "2026-10-23", "2026-10-26", "2026-10-27", "2026-10-28",
    "2026-10-29", "2026-10-30", "2026-11-02", "2026-11-03", "2026-11-04",
    "2026-11-05",
)
HISTORY_REQUEST_LEDGER_SHA256 = "b2fc79a3f70cc8278a4330877cef33654c7178f8bd95ebe2ca04baffb45677e8"
HISTORY_SESSION_DATES_SHA256 = "5b7278a3ec57d2bcc3ca0ba5de6461bb91b10e60ebef4f9817c73c608a338073"
SSE_DETAIL_URL = "https://query.sse.com.cn/marketdata/tradedata/queryMargin.do"
SSE_TURNOVER_URL = "https://query.sse.com.cn/commonQuery.do"
SZSE_REPORT_URL = "https://www.szse.cn/api/report/ShowReport"
SZSE_DATA_URL = "https://www.szse.cn/api/report/ShowReport/data"
SSE_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.sse.com.cn/"}
SZSE_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.szse.cn/"}

def _sse_detail_file(day: str, page: int) -> str:
    compact = day.replace("-", "")
    return f"sse-margin-{compact}-page{page}.json"


def _sse_turnover_file(day: str) -> str:
    return f"sse-stock-market-{day.replace('-', '')}.json"


def _szse_margin_file(day: str) -> str:
    return f"szse-margin-{day.replace('-', '')}.xlsx"


def _szse_turnover_file(day: str) -> str:
    return f"szse-turnover-{day.replace('-', '')}.xlsx"


class FundingDataError(ValueError):
    """Raised when official source files fail date, completeness, or unit checks."""


def _decimal(value: Any, label: str) -> Decimal:
    if value is None or isinstance(value, bool):
        raise FundingDataError(f"{label}: missing or non-numeric value")
    try:
        result = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, AttributeError) as exc:
        raise FundingDataError(f"{label}: invalid numeric value {value!r}") from exc
    if not result.is_finite() or result < 0:
        raise FundingDataError(f"{label}: expected a finite non-negative amount")
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_sse_json(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8").strip()
    if raw.startswith("callback(") and raw.endswith(")"):
        raw = raw[len("callback(") : -1]
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FundingDataError(f"{path.name}: malformed JSON/JSONP") from exc
    if not isinstance(result, dict):
        raise FundingDataError(f"{path.name}: expected a JSON object")
    return result


def _cell_column(reference: str) -> int:
    letters = re.match(r"([A-Z]+)", reference)
    if not letters:
        raise FundingDataError(f"Invalid XLSX cell reference: {reference!r}")
    column = 0
    for char in letters.group(1):
        column = column * 26 + ord(char) - ord("A") + 1
    return column - 1


def read_xlsx_rows(path: Path) -> list[list[str]]:
    """Read first-sheet text/numeric cells without trusting a broken A1 dimension."""
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            sheet_names = sorted(
                (name for name in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)),
                key=lambda value: int(re.search(r"sheet(\d+)", value).group(1)),
            )
            if len(sheet_names) != 1:
                raise FundingDataError(f"{path.name}: expected one worksheet, got {len(sheet_names)}")
            shared: list[str] = []
            if "xl/sharedStrings.xml" in names:
                shared_root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
                shared = ["".join(node.itertext()) for node in shared_root]
            root = ElementTree.fromstring(archive.read(sheet_names[0]))
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise FundingDataError(f"{path.name}: invalid XLSX archive/XML") from exc

    rows: list[list[str]] = []
    for row_node in root.iter():
        if row_node.tag.rsplit("}", 1)[-1] != "row":
            continue
        cells: list[str] = []
        for cell in row_node:
            if cell.tag.rsplit("}", 1)[-1] != "c":
                continue
            index = _cell_column(cell.attrib.get("r", ""))
            while len(cells) <= index:
                cells.append("")
            kind = cell.attrib.get("t")
            if kind == "inlineStr":
                value = "".join(cell.itertext())
            else:
                value_node = next((child for child in cell if child.tag.rsplit("}", 1)[-1] == "v"), None)
                value = value_node.text if value_node is not None and value_node.text is not None else ""
                if kind == "s":
                    try:
                        value = shared[int(value)]
                    except (ValueError, IndexError) as exc:
                        raise FundingDataError(f"{path.name}: invalid shared-string index") from exc
            cells[index] = value
        rows.append(cells)
    if not rows:
        raise FundingDataError(f"{path.name}: workbook has no worksheet rows")
    return rows


def _is_sse_a_stock(code: Any) -> bool:
    code = str(code or "").strip()
    return len(code) == 6 and code.isdigit() and code.startswith("6")


def _is_szse_a_stock(code: Any) -> bool:
    code = str(code or "").strip().zfill(6)
    return len(code) == 6 and code.isdigit() and code.startswith(("0", "3"))


def _sse_margin_amount(paths: Iterable[Path], day: str) -> tuple[Decimal, int, int, int]:
    paths = tuple(paths)
    total_rows: int | None = None
    page_count: int | None = None
    all_rows: list[dict[str, Any]] = []
    for expected_page, path in enumerate(paths, start=1):
        payload = _parse_sse_json(path)
        if payload.get("detailsDate") != day.replace("-", ""):
            raise FundingDataError(f"{path.name}: SSE detail date mismatch")
        help_data = payload.get("pageHelp") or {}
        rows = payload.get("result") or []
        if not isinstance(rows, list):
            raise FundingDataError(f"{path.name}: SSE result must be a list")
        if int(help_data.get("pageNo") or 0) != expected_page:
            raise FundingDataError(f"{path.name}: unexpected SSE page number")
        n = int(help_data.get("total") or 0)
        pages = int(help_data.get("pageCount") or 0)
        if total_rows is None:
            total_rows, page_count = n, pages
        elif (n, pages) != (total_rows, page_count):
            raise FundingDataError("SSE detail pagination metadata changed between pages")
        all_rows.extend(rows)
    if total_rows is None or page_count != len(paths) or len(all_rows) != total_rows:
        raise FundingDataError("SSE detail history is incomplete")
    codes = [str(row.get("stockCode", "")) for row in all_rows]
    if len(codes) != len(set(codes)):
        raise FundingDataError("SSE margin detail contains duplicate securities")
    stocks = [row for row in all_rows if _is_sse_a_stock(row.get("stockCode"))]
    excluded_etfs = [row for row in all_rows if str(row.get("stockCode", "")).startswith("5")]
    if not stocks:
        raise FundingDataError("SSE margin detail has no stock rows")
    amount = sum((_decimal(row.get("rzmre"), "SSE融资买入额(元)") for row in stocks), Decimal(0))
    return amount, len(stocks), len(all_rows), len(excluded_etfs)


def _sse_stock_turnover(path: Path, day: str) -> tuple[Decimal, int, list[dict[str, Any]]]:
    payload = _parse_sse_json(path)
    expected_date = day.replace("-", "")
    rows = payload.get("result") or []
    if not isinstance(rows, list):
        raise FundingDataError("SSE market statistics result must be a list")
    if {str(row.get("PRODUCT_CODE")) for row in rows} != {"01", "03"}:
        raise FundingDataError("SSE turnover must contain exactly main-board A and STAR market rows")
    values: list[Decimal] = []
    count = 0
    categories: list[dict[str, Any]] = []
    names = {"01": "上交所主板A股", "03": "科创板A股"}
    for row in rows:
        if str(row.get("TRADE_DATE")) != expected_date:
            raise FundingDataError("SSE stock turnover date mismatch")
        amount = _decimal(row.get("TRADE_AMT"), "SSE股票成交额(亿元)")
        stock_count = int(row.get("LIST_NUM") or 0)
        values.append(amount)
        count += stock_count
        categories.append({"code": str(row["PRODUCT_CODE"]), "name": names[str(row["PRODUCT_CODE"])], "turnover_yuan": amount * Decimal("100000000"), "stock_count": stock_count})
    return sum(values, Decimal(0)) * Decimal("100000000"), count, categories


def _szse_margin_amount(path: Path) -> tuple[Decimal, int, int, int]:
    rows = read_xlsx_rows(path)
    expected = ["证券代码", "证券简称", "融资买入额(元)", "融资余额(元)"]
    if rows[0][:4] != expected:
        raise FundingDataError(f"{path.name}: unexpected SZSE margin columns/units")
    records = rows[1:]
    stock_rows = [row for row in records if len(row) >= 3 and _is_szse_a_stock(row[0])]
    excluded_etfs = [row for row in records if len(row) >= 3 and str(row[0]).zfill(6).startswith(("15", "16"))]
    codes = [str(row[0]).zfill(6) for row in stock_rows]
    if len(codes) != len(set(codes)):
        raise FundingDataError("SZSE margin sheet contains duplicate A-share securities")
    if not stock_rows:
        raise FundingDataError("SZSE margin sheet has no A-share rows")
    amount = sum((_decimal(row[2], "SZSE融资买入额(元)") for row in stock_rows), Decimal(0))
    return amount, len(stock_rows), len(records), len(excluded_etfs)


def _szse_stock_turnover(path: Path) -> tuple[Decimal, int, list[dict[str, Any]]]:
    rows = read_xlsx_rows(path)
    if rows[0][:3] != ["证券类别", "数量(只)", "成交金额(元)"]:
        raise FundingDataError(f"{path.name}: unexpected SZSE turnover columns/units")
    categories: dict[str, list[str]] = {}
    for row in rows[1:]:
        if not row:
            continue
        name = row[0].strip()
        if name in ("主板A股", "创业板A股"):
            if name in categories:
                raise FundingDataError(f"duplicate SZSE turnover category: {name}")
            categories[name] = row
    if set(categories) != {"主板A股", "创业板A股"}:
        raise FundingDataError("SZSE turnover must include main-board A shares and ChiNext")
    amount = sum((_decimal(row[2], "SZSE股票成交额(元)") for row in categories.values()), Decimal(0))
    count = sum(int(row[1].replace(",", "")) for row in categories.values())
    details = [{"name": name, "turnover_yuan": _decimal(row[2], "SZSE股票成交额(元)"), "stock_count": int(row[1].replace(",", ""))} for name, row in categories.items()]
    return amount, count, details


def calculate_ratio(
    sh_margin_buy_yuan: Decimal,
    sz_margin_buy_yuan: Decimal,
    sh_stock_turnover_yuan: Decimal,
    sz_stock_turnover_yuan: Decimal,
) -> Decimal:
    """Percent of A-share turnover represented by A-share stock financing buys."""
    values = (sh_margin_buy_yuan, sz_margin_buy_yuan, sh_stock_turnover_yuan, sz_stock_turnover_yuan)
    if any(not value.is_finite() or value < 0 for value in values):
        raise FundingDataError("amounts must be finite non-negative yuan values")
    denominator = sh_stock_turnover_yuan + sz_stock_turnover_yuan
    if denominator <= 0:
        raise FundingDataError("matched A-share turnover denominator is zero")
    return (sh_margin_buy_yuan + sz_margin_buy_yuan) / denominator * Decimal(100)


def rolling_mean_points(points: list[dict[str, Any]], window: int = 20) -> list[dict[str, Any]]:
    """Compute a fixed-session moving mean; any null session invalidates that window."""
    if window <= 0:
        raise ValueError("window must be positive")
    result: list[dict[str, Any]] = []
    for index, point in enumerate(points):
        values = points[index - window + 1:index + 1] if index + 1 >= window else []
        mean: Decimal | None = None
        if len(values) == window and all(row.get("value") is not None for row in values):
            mean = sum((_decimal(row["value"], "rolling mean input") for row in values), Decimal(0)) / Decimal(window)
        result.append({"date": point["date"], "value": float(mean) if mean is not None else None})
    return result


def strict_prior_percentiles(points: list[dict[str, Any]], window: int = 250) -> list[dict[str, Any]]:
    """Midrank percentile against a complete prior window, excluding today."""
    if window <= 0:
        raise ValueError("window must be positive")
    output: list[dict[str, Any]] = []
    for index, point in enumerate(points):
        prior = [row.get("value") for row in points[max(0, index - window):index]]
        current = point.get("value")
        value = None
        if current is not None and len(prior) == window and all(item is not None for item in prior):
            below = sum(item < current for item in prior)
            tied = sum(item == current for item in prior)
            value = round(100 * (below + tied / 2) / window, 2)
        output.append({"date": point["date"], "value": value})
    return output


def _history_contract(repo_root: Path) -> tuple[list[str], dict[str, Any]]:
    history_dir = repo_root / "docs/ops/microstructure-observations-20261108/funding-history"
    ledger_path = history_dir / "history-request-ledger.json"
    dates_path = history_dir / "history-session-dates.json"
    if _sha256(ledger_path) != HISTORY_REQUEST_LEDGER_SHA256:
        raise FundingDataError("historical request ledger fingerprint mismatch")
    if _sha256(dates_path) != HISTORY_SESSION_DATES_SHA256:
        raise FundingDataError("historical session calendar fingerprint mismatch")
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        dates_doc = json.loads(dates_path.read_text(encoding="utf-8"))
        dates = dates_doc["historyDates"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise FundingDataError("historical request/calendar contract unreadable") from exc
    if len(dates) != 250 or len(set(dates)) != 250 or dates != sorted(dates):
        raise FundingDataError("historical contract must contain 250 sorted unique sessions")
    if not isinstance(ledger.get("days"), dict) or set(ledger["days"]) != set(dates):
        raise FundingDataError("historical daily completeness ledger does not match the calendar")
    return dates, {"ledger": ledger, "datesDocument": dates_doc, "ledgerPath": ledger_path, "datesPath": dates_path}


def _raw_metadata(path: Path, relative: str) -> dict[str, Any]:
    return {"path": relative, "bytes": path.stat().st_size, "sha256": _sha256(path)}


def _validate_collection_manifest(source_dir: Path, dates: Iterable[str], request_rows: list[dict[str, Any]], history_days: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], dict[str, str]]:
    requests = request_rows
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in requests:
        if not isinstance(row, dict):
            continue
        name = Path(str(row.get("path", ""))).name
        by_key.setdefault((row.get("date"), name), []).append(row)
    invalid: dict[str, str] = {}
    for day in dates:
        compact = day.replace("-", "")
        sse_page_rows: dict[int, list[dict[str, Any]]] = {}
        for row in requests:
            if not (
                isinstance(row, dict)
                and row.get("date") == day
                and isinstance(row.get("path"), str)
            ):
                continue
            match = re.fullmatch(rf"sse-margin-{compact}-page(\d+)\.json", Path(row["path"]).name)
            if match:
                sse_page_rows.setdefault(int(match.group(1)), []).append(row)
        # Do not assume two pages: older SSE sessions can fit on page one.
        page1_path = source_dir / _sse_detail_file(day, 1)
        expected_pages: int | None = None
        if page1_path.is_file():
            try:
                first_page = _parse_sse_json(page1_path)
                help_data = first_page.get("pageHelp") or {}
                expected_pages = int(help_data.get("pageCount") or 0)
            except (FundingDataError, TypeError, ValueError):
                expected_pages = None
        filenames = [
            *[_sse_detail_file(day, page) for page in range(1, (expected_pages or 0) + 1)],
            _sse_turnover_file(day), _szse_margin_file(day), _szse_turnover_file(day),
        ]
        expected_sources = {
            _sse_turnover_file(day): (SSE_TURNOVER_URL, {"SEARCH_DATE": day.replace("-", ""), "sqlId": "COMMON_SSE_SJ_GPSJ_CJGK_MRGK_C", "PRODUCT_CODE": "01,03"}),
            _szse_margin_file(day): (SZSE_REPORT_URL, {"CATALOGID": "1837_xxpl", "TABKEY": "tab2", "txtDate": day}),
            _szse_turnover_file(day): (SZSE_REPORT_URL, {"CATALOGID": "1803_sczm", "TABKEY": "tab1", "txtQueryDate": day}),
        }
        reasons: list[str] = []
        if expected_pages is None or expected_pages < 1:
            reasons.append("SSE detail page 1 missing or has invalid pagination metadata")
        elif set(sse_page_rows) != set(range(1, expected_pages + 1)):
            reasons.append(f"SSE detail manifest pages do not match pageCount={expected_pages}")
        if history_days is not None and day in history_days:
            day_contract = history_days[day]
            if not day_contract.get("complete") or day_contract.get("ssePageCount") != expected_pages:
                reasons.append("historical daily completeness/page-count ledger mismatch")
        for name in filenames:
            page_match = re.fullmatch(rf"sse-margin-{compact}-page(\d+)\.json", name)
            candidates = sse_page_rows.get(int(page_match.group(1)), []) if page_match else by_key.get((day, name), [])
            candidates = [row for row in candidates if row]
            # Keep failed/retry records in the ledger, but qualify from a successful
            # row whose saved fingerprint matches the archived object.
            path = source_dir / name
            matching = [row for row in candidates if row.get("status") in (200, "200", "reused_archived_raw", "existing_untouched") and row.get("sha256") == (_sha256(path) if path.is_file() else None)]
            if not matching:
                reasons.append(f"{name}: request manifest entry missing")
                continue
            row = matching[-1]
            query = urllib.parse.parse_qs(urllib.parse.urlparse(str(row.get("url", ""))).query)
            if page_match:
                page = int(page_match.group(1))
                parts = urllib.parse.urlparse(str(row.get("url", "")))
                expected_parts = urllib.parse.urlparse(SSE_DETAIL_URL)
                if (parts.scheme, parts.netloc, parts.path) != (expected_parts.scheme, expected_parts.netloc, expected_parts.path) or query.get("detailsDate") != [day.replace("-", "")] or query.get("pageHelp.pageNo") != [str(page)]:
                    reasons.append(f"{name}: request URL does not bind date/page to manifest path")
                continue
            expected_url, expected_params = expected_sources[name]
            parts = urllib.parse.urlparse(str(row.get("url", "")))
            expected_parts = urllib.parse.urlparse(expected_url)
            if (parts.scheme, parts.netloc, parts.path) != (expected_parts.scheme, expected_parts.netloc, expected_parts.path) or any(query.get(key) != [value] for key, value in expected_params.items()):
                reasons.append(f"{name}: request URL does not bind official source and date to {day}")
        if reasons:
            invalid[day] = "; ".join(reasons)
    return requests, invalid


def build_packet(source_dir: Path, generated_at: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    source_dir = source_dir.expanduser().resolve()
    repo_root = Path(__file__).resolve().parents[3]
    old_dates, history_contract = _history_contract(repo_root)
    session_dates = tuple(sorted((*old_dates, *SESSION_DATES)))
    try:
        current_manifest = json.loads((source_dir / "collection-manifest.json").read_text(encoding="utf-8"))
        current_requests = current_manifest["requests"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise FundingDataError("current collection manifest missing or invalid") from exc
    if current_manifest.get("requestedSessions") != list(SESSION_DATES):
        raise FundingDataError("current collection manifest session list does not match the qualified 21-session set")
    old_ledger = history_contract["ledger"]
    manifest_requests = [*old_ledger.get("requests", []), *current_requests]
    invalid_manifest_dates = _validate_collection_manifest(
        source_dir, session_dates, manifest_requests, old_ledger.get("days", {})
    )[1]
    observations: list[dict[str, Any]] = []
    source_files: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    for day in session_dates:
        compact = day.replace("-", "")
        first_page_path = source_dir / _sse_detail_file(day, 1)
        try:
            page_count = int((_parse_sse_json(first_page_path).get("pageHelp") or {}).get("pageCount") or 0)
        except (OSError, FundingDataError, TypeError, ValueError):
            page_count = 0
        detail_files = [_sse_detail_file(day, page) for page in range(1, page_count + 1)]
        filenames = [*detail_files, _sse_turnover_file(day), _szse_margin_file(day), _szse_turnover_file(day)]
        paths = [source_dir / name for name in filenames]
        if day in invalid_manifest_dates:
            observations.append({"date": day, "value": None})
            gaps.append({"date": day, "reason": invalid_manifest_dates[day]})
            continue
        if not all(path.is_file() for path in paths):
            observations.append({"date": day, "value": None})
            gaps.append({"date": day, "reason": "one or more required same-date exchange source files are missing"})
            continue
        detail_count = len(detail_files)
        sh_margin, sh_eligible_count, sh_total_count, sh_excluded_etfs = _sse_margin_amount(paths[:detail_count], day)
        sh_turnover, sh_market_count, sh_turnover_categories = _sse_stock_turnover(paths[detail_count], day)
        sz_margin, sz_eligible_count, sz_total_count, sz_excluded_etfs = _szse_margin_amount(paths[detail_count + 1])
        sz_turnover, sz_market_count, sz_turnover_categories = _szse_stock_turnover(paths[detail_count + 2])
        ratio = calculate_ratio(sh_margin, sz_margin, sh_turnover, sz_turnover)
        observations.append(
            {
                "date": day,
                "value": ratio,
                "shMarginBuyYuan": sh_margin,
                "szMarginBuyYuan": sz_margin,
                "shTurnoverYuan": sh_turnover,
                "szTurnoverYuan": sz_turnover,
                "shEligibleCount": sh_eligible_count,
                "szEligibleCount": sz_eligible_count,
                "shExcludedEtfCount": sh_excluded_etfs,
                "szExcludedEtfCount": sz_excluded_etfs,
                "shMarginRows": sh_total_count,
                "szMarginRows": sz_total_count,
                "shMarketCount": sh_market_count,
                "szMarketCount": sz_market_count,
                "shTurnoverCategories": sh_turnover_categories,
                "szTurnoverCategories": sz_turnover_categories,
            }
        )
        source_files.extend(_raw_metadata(path, path.name) for path in paths)
    if not any(item["value"] is not None for item in observations):
        raise FundingDataError("no complete same-date official SSE/SZSE source set")
    last = next(item for item in reversed(observations) if item["value"] is not None)
    ratio = last["value"]
    sh_margin = last["shMarginBuyYuan"]
    sz_margin = last["szMarginBuyYuan"]
    sh_turnover = last["shTurnoverYuan"]
    sz_turnover = last["szTurnoverYuan"]
    total_turnover = sh_turnover + sz_turnover
    buy_amount = sh_margin + sz_margin
    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    references: list[dict[str, Any]] = []
    ratio_points = [{"date": item["date"], "value": float(item["value"]) if item["value"] is not None else None} for item in observations]
    ratio_percentiles = strict_prior_percentiles(ratio_points, 250)
    latest_ratio_percentile = ratio_percentiles[-1]["value"]
    total_bytes = sum(item["bytes"] for item in source_files)
    card = {
        "id": "cn-margin-buy-share-a-stocks",
        "title": "沪深A股融资买入额占沪深A股成交额",
        "market": "cn",
        "unit": "%",
        "frequency": "daily",
        "scope": "仅沪深市场，不含北交所。分子为上交所和深交所当日融资买入额中证券代码识别为A股的融资融券标的；分母为上交所主板A股、科创板A股及深交所主板A股、创业板A股当日成交额。分子只含融资标的股票，分母覆盖沪深全部A股。",
        "meaning": "表示融资买入活动相对于沪深A股成交额的规模；它不是净资金流入、投资者身份或卖压指标。",
        "sourceName": "上海证券交易所、深圳证券交易所融资融券明细与股票成交统计",
        "sourceUrl": "https://www.sse.com.cn/market/othersdata/margin/sum/",
        "refreshedAt": generated_at,
        "refreshMode": "snapshot",
        "points": ratio_points,
        "percentiles": ratio_percentiles,
        "references": references,
        "latestDetails": [
            {"label": "融资买入额", "value": f"{buy_amount / Decimal('100000000'):.2f}亿元"},
            {"label": "沪深A股成交额", "value": f"{total_turnover / Decimal('100000000'):.2f}亿元"},
            {"label": "融资买入额 · 上交所A股标的", "value": f"{sh_margin / Decimal('100000000'):.2f}亿元"},
            {"label": "融资买入额 · 深交所A股标的", "value": f"{sz_margin / Decimal('100000000'):.2f}亿元"},
            {"label": "成交额 · 上交所主板A股+科创板A股", "value": f"{sh_turnover / Decimal('100000000'):.2f}亿元"},
            {"label": "成交额 · 深交所主板A股+创业板A股", "value": f"{sz_turnover / Decimal('100000000'):.2f}亿元"},
            {"label": "融资标的股票数（沪/深）", "value": f"{last['shEligibleCount']} / {last['szEligibleCount']}只"},
            {"label": "排除ETF/基金融资行（沪/深）", "value": f"{last['shExcludedEtfCount']} / {last['szExcludedEtfCount']}条"},
            {"label": "融资源表总行数（沪/深）", "value": f"{last['shMarginRows']} / {last['szMarginRows']}条"},
            {"label": "有效同日配对日数", "value": f"{sum(item['value'] is not None for item in observations)}日"},
            {"label": "严格此前250日分位（中秩）", "value": f"{latest_ratio_percentile:.2f}%" if latest_ratio_percentile is not None else "资料不足"},
            {"label": "样本期间", "value": f"{observations[0]['date']}—{AS_OF}"},
            {"label": "源样本结束日", "value": AS_OF},
        ],
        "limitations": [
            f"目前取得{sum(item['value'] is not None for item in observations)}个同日沪深配对点；MA20按最近20个交易日逐日比例计算；日比例与MA20分位各自只比较严格此前250个连续完整有效值，不以前填补或压缩缺失日期。",
            "分子是沪深融资融券标的A股，不含基金类融资标的；分母是沪深全体A股成交额，二者股票资产类别一致但证券集合不完全相同，不含北交所。",
            "截至2026-11-08可读取到的最新深交所融资明细为2026-11-05；此固定快照不会自动更新。",
            "融资买入额描述借款买入成交，不等于资金净流入，也不单独指示后续风险或交易动作。",
        ],
        "percentileWindow": 250,
    }
    mean20_series = rolling_mean_points(
        [{"date": item["date"], "value": float(item["value"]) if item["value"] is not None else None} for item in observations],
        window=20,
    )
    mean20 = mean20_series[-1]["value"] if mean20_series else None
    mean20_percentiles = strict_prior_percentiles(mean20_series, 250)
    latest_mean20_percentile = mean20_percentiles[-1]["value"] if mean20_percentiles else None
    mean20_card = {
        "id": "cn-margin-buy-share-a-stocks-ma20",
        "title": "沪深A股融资买入占比 · 20日均值",
        "market": "cn",
        "unit": "%",
        "frequency": "daily",
        "scope": card["scope"],
        "meaning": "过去20个官方交易日逐日融资买入占比的简单平均；窗口内任何缺失日都会使该日均值留空。",
        "sourceName": card["sourceName"],
        "sourceUrl": card["sourceUrl"],
        "refreshedAt": generated_at,
        "refreshMode": "snapshot",
        "points": mean20_series,
        "percentiles": mean20_percentiles,
        "references": [],
        "latestDetails": [
            {"label": "最近一日20日均值", "value": f"{mean20:.2f}%" if mean20 is not None else "资料不足"},
            {"label": "严格此前250个有效20日均值分位（中秩）", "value": f"{latest_mean20_percentile:.2f}%" if latest_mean20_percentile is not None else "资料不足"},
        ],
        "limitations": ["MA20是最近20个官方交易日逐日比例的算术平均；窗口内有缺失日则为空。", "分位只比较严格此前250个完整MA20值，当前值不进入参照窗；这是描述性指标，不表示净资金流入或预测信号。"],
        "percentileWindow": 250,
    }
    history_rows = []
    for item in observations:
        if item["value"] is None:
            history_rows.append({"date": item["date"], "value_pct": None, "reason": next(gap["reason"] for gap in gaps if gap["date"] == item["date"]), "categoryNames": {"sseTurnover": ["上交所主板A股", "科创板A股"], "szseTurnover": ["深交所主板A股", "创业板A股"]}})
            continue
        history_rows.append({
            "date": item["date"], "value_pct": float(item["value"]),
            "sse_margin_buy_yuan": str(item["shMarginBuyYuan"]), "szse_margin_buy_yuan": str(item["szMarginBuyYuan"]),
            "sse_stock_turnover_yuan": str(item["shTurnoverYuan"]), "szse_stock_turnover_yuan": str(item["szTurnoverYuan"]),
            "sse_stock_categories": [{"code": category["code"], "name": category["name"], "turnover_yuan": str(category["turnover_yuan"]), "stock_count": category["stock_count"]} for category in item["shTurnoverCategories"]],
            "szse_stock_categories": [{"name": category["name"], "turnover_yuan": str(category["turnover_yuan"]), "stock_count": category["stock_count"]} for category in item["szTurnoverCategories"]],
            "sse_margin_rows": item["shMarginRows"], "sse_a_stock_margin_rows": item["shEligibleCount"], "sse_excluded_etf_fund_rows": item["shExcludedEtfCount"],
            "szse_margin_rows": item["szMarginRows"], "szse_a_stock_margin_rows": item["szEligibleCount"], "szse_excluded_etf_fund_rows": item["szExcludedEtfCount"],
            "sse_stock_count": item["shMarketCount"], "szse_stock_count": item["szMarketCount"],
        })
    no_data_probes: list[dict[str, Any]] = []
    probe_path = source_dir / "szse-margin-detail.json"
    if probe_path.is_file():
        try:
            probe = json.loads(probe_path.read_text(encoding="utf-8"))[0]
            metadata = probe.get("metadata", {})
            if metadata.get("catalogid") == "1837_xxpl" and not probe.get("data"):
                no_data_probes.append({
                    "date": "2026-11-06",
                    "url": "https://www.szse.cn/api/report/ShowReport/data?CATALOGID=1837_xxpl&TABKEY=tab2&txtDate=2026-11-06&txtZqdm=",
                    "httpStatus": 200,
                    "sourceRows": 0,
                    "status": "official endpoint returned no published rows; excluded from matched history",
                    "path": probe_path.name,
                    "bytes": probe_path.stat().st_size,
                    "sha256": _sha256(probe_path),
                })
        except (OSError, IndexError, json.JSONDecodeError, TypeError):
            pass
    ledger = {
        "schemaVersion": 1,
        "asOf": AS_OF,
        "builtAt": generated_at,
        "sourceRequestLedgerRecords": len(manifest_requests),
        "failedRequestAttempts": sum(row.get("status") not in (200, "200", "reused_archived_raw", "existing_untouched") for row in manifest_requests),
        "sourceCollectionSummary": {
            "uniqueAcceptedObjects": len(source_files),
            "successfulAcceptedRawObjects": len(source_files),
            "failedAcceptedRawObjects": 0,
            "failedRequestAttempts": sum(row.get("status") not in (200, "200", "reused_archived_raw", "existing_untouched") for row in manifest_requests),
            "requestRecordsAcrossManifests": len(manifest_requests),
            "historicalHttpRequestAttempts": old_ledger.get("requestCount"),
            "requestBudgetAuthorized": 1500,
            "rawObjectByteBudgetAuthorized": 300 * 1024 * 1024,
            "acceptedRawBytes": total_bytes,
            "note": "Current 21-session collection manifest and historical request ledger are both retained and validated. Historical failed/retry records remain in the ledger; each selected source object must match a successful request SHA and its date-bound URL. The current-session acquisition record reports 95 fetched and 10 previously archived objects; the historical ledger reports 1,013 HTTP attempts including one recovered failure.",
        },
        "acceptedSourceBytes": total_bytes,
        "acceptedRawFiles": source_files,
        "requestManifest": {"current": "collection-manifest.json (external source archive)", "currentManifestSha256": _sha256(source_dir / "collection-manifest.json"), "history": str(history_contract["ledgerPath"]), "historyLedgerSha256": _sha256(history_contract["ledgerPath"]), "historyCalendar": str(history_contract["datesPath"]), "historyCalendarSha256": _sha256(history_contract["datesPath"]), "note": "URL date parameters bind SZSE XLSX because workbook rows contain no date column"},
        "selectedRows": {
            "sseMarginAllSecurities": last["shMarginRows"],
            "sseMarginAStocks": last["shEligibleCount"],
            "szseMarginAllSecurities": last["szMarginRows"],
            "szseMarginAStocks": last["szEligibleCount"],
            "sseStockTurnoverCategories": [{"code": "01", "name": "上交所主板A股"}, {"code": "03", "name": "科创板A股"}],
            "sseStockCount": sh_market_count,
            "szseStockTurnoverCategories": ["主板A股", "创业板A股"],
            "szseStockCount": sz_market_count,
        },
        "units": {
            "marginBuy": "元; converted from source rows with header explicitly labelled 元",
            "sseTurnover": "亿元; converted to 元",
            "szseTurnover": "元",
            "ratio": "%",
        },
        "formulas": {
            "numerator": "sum(SSE RZMRE for six-digit A-share codes beginning 6) + sum(SZSE financing-buy amount for six-digit A-share codes beginning 0 or 3)",
            "denominator": "SSE PRODUCT_CODE 01+03 TRADE_AMT (亿元 converted to 元) + SZSE 主板A股+创业板A股 成交金额(元)",
            "value": "100 * numerator / denominator",
        },
        "history": history_rows,
        "mean20Pct": float(mean20) if mean20 is not None else None,
        "rollingMean20": mean20_series,
        "missingDates": gaps,
        "nonAcceptedNoDataProbes": no_data_probes,
        "notAvailable": [],
    }
    unavailable = [item for item in ledger["notAvailable"] if item["reason"]]
    packet = {"schemaVersion": 1, "generatedAt": generated_at, "cards": [card, mean20_card], "unavailable": unavailable}
    return packet, ledger


def _request_bytes(url: str, headers: dict[str, str], timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise FundingDataError(f"HTTP {response.status}: {url}")
        payload = response.read(50 * 1024 * 1024 + 1)
    if len(payload) > 50 * 1024 * 1024:
        raise FundingDataError("source object exceeded 50 MiB cap")
    return payload


def collect_latest(source_dir: Path, as_of: str = AS_OF) -> list[dict[str, Any]]:
    """Collect five official objects for the latest known matched date, no retries."""
    if as_of != AS_OF:
        raise FundingDataError(f"collector is qualified only for {AS_OF}")
    source_dir = source_dir.expanduser().resolve()
    source_dir.mkdir(parents=True, exist_ok=True)
    compact = as_of.replace("-", "")
    files: list[tuple[str, str, dict[str, str]]] = []
    for page in (1, 2):
        query = urllib.parse.urlencode(
            {
                "isPagination": "true", "tabType": "mxtype", "detailsDate": compact,
                "pageHelp.pageSize": "5000", "pageHelp.pageNo": str(page),
                "pageHelp.beginPage": str(page), "pageHelp.cacheSize": "1", "pageHelp.endPage": str(page),
            }
        )
        files.append((f"sse-margin-{compact}-page{page}.json", f"{SSE_DETAIL_URL}?{query}", SSE_HEADERS))
    query = urllib.parse.urlencode(
        {"sqlId": "COMMON_SSE_SJ_GPSJ_CJGK_MRGK_C", "PRODUCT_CODE": "01,03", "type": "inParams", "SEARCH_DATE": compact, "jsonCallBack": "callback"}
    )
    files.append((f"sse-stock-market-{compact}.json", f"{SSE_TURNOVER_URL}?{query}", SSE_HEADERS))
    for filename, params in (
        (f"szse-margin-{compact}.xlsx", {"SHOWTYPE": "xlsx", "CATALOGID": "1837_xxpl", "TABKEY": "tab2", "txtDate": as_of, "txtZqdm": "", "random": "0.1"}),
        (f"szse-turnover-{compact}.xlsx", {"SHOWTYPE": "xlsx", "CATALOGID": "1803_sczm", "TABKEY": "tab1", "txtQueryDate": as_of, "random": "0.3"}),
    ):
        files.append((filename, f"{SZSE_REPORT_URL}?{urllib.parse.urlencode(params)}", SZSE_HEADERS))
    ledger: list[dict[str, Any]] = []
    for name, url, headers in files:
        payload = _request_bytes(url, headers)
        path = source_dir / name
        path.write_bytes(payload)
        ledger.append({"url": url, "status": 200, **_raw_metadata(path, name)})
    return ledger


def _urls_for_day(day: str) -> list[tuple[str, str, dict[str, str]]]:
    compact = day.replace("-", "")
    files: list[tuple[str, str, dict[str, str]]] = []
    for page in (1, 2):
        query = urllib.parse.urlencode(
            {"isPagination": "true", "tabType": "mxtype", "detailsDate": compact,
             "pageHelp.pageSize": "5000", "pageHelp.pageNo": str(page), "pageHelp.beginPage": str(page),
             "pageHelp.cacheSize": "1", "pageHelp.endPage": str(page)}
        )
        files.append((f"sse-margin-{compact}-page{page}.json", f"{SSE_DETAIL_URL}?{query}", SSE_HEADERS))
    query = urllib.parse.urlencode(
        {"sqlId": "COMMON_SSE_SJ_GPSJ_CJGK_MRGK_C", "PRODUCT_CODE": "01,03", "type": "inParams", "SEARCH_DATE": compact, "jsonCallBack": "callback"}
    )
    files.append((f"sse-stock-market-{compact}.json", f"{SSE_TURNOVER_URL}?{query}", SSE_HEADERS))
    files.append((f"szse-margin-{compact}.xlsx", f"{SZSE_REPORT_URL}?" + urllib.parse.urlencode(
        {"SHOWTYPE": "xlsx", "CATALOGID": "1837_xxpl", "TABKEY": "tab2", "txtDate": day, "txtZqdm": "", "random": "0.1"}
    ), SZSE_HEADERS))
    files.append((f"szse-turnover-{compact}.xlsx", f"{SZSE_REPORT_URL}?" + urllib.parse.urlencode(
        {"SHOWTYPE": "xlsx", "CATALOGID": "1803_sczm", "TABKEY": "tab1", "txtQueryDate": day, "random": "0.3"}
    ), SZSE_HEADERS))
    return files


def collect_sessions(source_dir: Path, dates: Iterable[str] = SESSION_DATES) -> list[dict[str, Any]]:
    """Collect one date-matched five-object set per official trading session; no retries."""
    source_dir = source_dir.expanduser().resolve()
    source_dir.mkdir(parents=True, exist_ok=True)
    ledger: list[dict[str, Any]] = []
    dates = tuple(dates)
    for day in dates:
        for name, url, headers in _urls_for_day(day):
            path = source_dir / name
            if path.exists():
                ledger.append({"date": day, "url": url, "status": "reused_archived_raw", **_raw_metadata(path, name)})
                continue
            try:
                payload = _request_bytes(url, headers)
                path.write_bytes(payload)
                ledger.append({"date": day, "url": url, "status": 200, **_raw_metadata(path, name)})
            except Exception as exc:
                status = getattr(exc, "code", None)
                ledger.append({"date": day, "url": url, "status": status or "request_failed", "error": str(exc), "path": name})
    manifest_path = source_dir / "collection-manifest.json"
    manifest_path.write_text(
        json.dumps({"schemaVersion": 1, "requestedSessions": list(dates), "requests": ledger}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return ledger


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True, help="directory holding archived official source files")
    parser.add_argument("--output", type=Path, help="write shared observation packet JSON to this path")
    parser.add_argument("--ledger", type=Path, help="write source ledger JSON to this path")
    parser.add_argument("--collect", action="store_true", help="fetch the five qualified official objects into --source-dir")
    parser.add_argument("--collect-sessions", action="store_true", help="fetch the 21 official trading sessions in SESSION_DATES")
    args = parser.parse_args()
    if args.collect_sessions:
        collect_ledger = collect_sessions(args.source_dir)
    elif args.collect:
        collect_ledger = collect_latest(args.source_dir)
    else:
        collect_ledger = []
    packet, ledger = build_packet(args.source_dir)
    if collect_ledger:
        ledger["collectionLedger"] = collect_ledger
        ledger["networkFetchCount"] = sum(row["status"] == 200 for row in collect_ledger)
    encoded = json.dumps(packet, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    if args.ledger:
        args.ledger.parent.mkdir(parents=True, exist_ok=True)
        args.ledger.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
