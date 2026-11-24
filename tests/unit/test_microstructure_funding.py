from __future__ import annotations

import hashlib
import json
import urllib.parse
import zipfile
from decimal import Decimal
from pathlib import Path

import pytest

from lei_signal.market_context.microstructure_funding import (
    FundingDataError,
    SSE_DETAIL_URL,
    SSE_TURNOVER_URL,
    SZSE_REPORT_URL,
    _validate_collection_manifest,
    _is_sse_a_stock,
    _is_szse_a_stock,
    calculate_ratio,
    read_xlsx_rows,
    rolling_mean_points,
    strict_prior_percentiles,
)


def _xlsx(path: Path, sheet: str) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<dimension ref="A1"/><sheetData>'
            '<row r="1"><c r="A1" t="inlineStr"><is><t>证券代码</t></is></c>'
            '<c r="B1" t="inlineStr"><is><t>融资买入额(元)</t></is></c></row>'
            '<row r="2"><c r="A2" t="inlineStr"><is><t>000001</t></is></c>'
            '<c r="B2" t="inlineStr"><is><t>123,456</t></is></c></row>'
            '</sheetData></worksheet>',
        )
        archive.writestr("xl/workbook.xml", "<workbook/>")
    return path


def test_xlsx_reader_ignores_incorrect_a1_dimension(tmp_path: Path) -> None:
    rows = read_xlsx_rows(_xlsx(tmp_path / "sample.xlsx", "ignored"))
    assert rows == [["证券代码", "融资买入额(元)"], ["000001", "123,456"]]


def test_ratio_converts_all_inputs_as_yuan_and_returns_percent() -> None:
    value = calculate_ratio(Decimal("10"), Decimal("20"), Decimal("100"), Decimal("200"))
    assert value == Decimal(10)


def test_zero_or_negative_denominator_is_rejected() -> None:
    with pytest.raises(FundingDataError):
        calculate_ratio(Decimal("1"), Decimal("1"), Decimal("0"), Decimal("0"))
    with pytest.raises(FundingDataError):
        calculate_ratio(Decimal("1"), Decimal("1"), Decimal("100"), Decimal("-1"))


def test_stock_code_filters_exclude_etfs_and_non_a_share_securities() -> None:
    assert _is_sse_a_stock("600000") and _is_sse_a_stock("689009")
    assert not _is_sse_a_stock("510050") and not _is_sse_a_stock("900901")
    assert _is_szse_a_stock("000001") and _is_szse_a_stock("301001")
    assert not _is_szse_a_stock("159300") and not _is_szse_a_stock("200011")


def test_twenty_session_mean_does_not_compress_a_missing_day() -> None:
    points = [{"date": f"2026-10-{day:02d}", "value": 2.0} for day in range(1, 22)]
    points[5]["value"] = None
    means = rolling_mean_points(points, window=20)
    assert all(point["value"] is None for point in means[:19])
    assert means[19]["value"] is None
    assert means[20]["value"] is None
    points[5]["value"] = 2.0
    means = rolling_mean_points(points, window=20)
    assert means[19]["value"] == 2.0
    assert means[20]["value"] == 2.0


def test_prior_percentile_excludes_current_and_needs_full_unbroken_window() -> None:
    points = [{"date": f"d{i}", "value": float(i)} for i in range(4)]
    assert strict_prior_percentiles(points, 3) == [
        {"date": "d0", "value": None},
        {"date": "d1", "value": None},
        {"date": "d2", "value": None},
        {"date": "d3", "value": 100.0},
    ]
    points[1]["value"] = None
    assert strict_prior_percentiles(points, 3)[3]["value"] is None


def test_xlsx_unit_header_is_a_parseable_contract(tmp_path: Path) -> None:
    rows = read_xlsx_rows(_xlsx(tmp_path / "funding-unit-test.xlsx", "ignored"))
    assert rows[0][1] == "融资买入额(元)"


def _date_manifest(tmp_path: Path, day: str, page_count: int) -> list[dict[str, str | int]]:
    compact = day.replace("-", "")
    rows: list[dict[str, str | int]] = []
    detail_pages = [1] if page_count == 1 else [1, 2]
    for page in detail_pages:
        name = f"sse-margin-{compact}-page{page}.json"
        payload = json.dumps({"detailsDate": compact, "pageHelp": {"pageNo": page, "pageCount": page_count, "total": 1}, "result": []}).encode()
        (tmp_path / name).write_bytes(payload)
        url = SSE_DETAIL_URL + "?" + urllib.parse.urlencode({"detailsDate": compact, "pageHelp.pageNo": page})
        rows.append({"date": day, "path": name, "url": url, "status": 200, "sha256": hashlib.sha256(payload).hexdigest()})
    urls = {
        f"sse-stock-market-{compact}.json": SSE_TURNOVER_URL + "?" + urllib.parse.urlencode({"SEARCH_DATE": compact, "sqlId": "COMMON_SSE_SJ_GPSJ_CJGK_MRGK_C", "PRODUCT_CODE": "01,03"}),
        f"szse-margin-{compact}.xlsx": SZSE_REPORT_URL + "?" + urllib.parse.urlencode({"CATALOGID": "1837_xxpl", "TABKEY": "tab2", "txtDate": day}),
        f"szse-turnover-{compact}.xlsx": SZSE_REPORT_URL + "?" + urllib.parse.urlencode({"CATALOGID": "1803_sczm", "TABKEY": "tab1", "txtQueryDate": day}),
    }
    for name, url in urls.items():
        payload = b"fixture source bytes"
        (tmp_path / name).write_bytes(payload)
        rows.append({"date": day, "path": name, "url": url, "status": 200, "sha256": hashlib.sha256(payload).hexdigest()})
    return rows


def test_source_files_without_szse_manifest_row_are_not_qualified(tmp_path: Path) -> None:
    day = "2026-09-30"
    rows = _date_manifest(tmp_path, day, page_count=2)
    rows = [row for row in rows if not str(row["path"]).startswith("szse-turnover-")]
    _, invalid = _validate_collection_manifest(tmp_path, [day], rows)
    assert day in invalid
    assert "request manifest entry missing" in invalid[day]


def test_manifest_uses_actual_single_page_sse_count_and_rejects_missing_second_page(tmp_path: Path) -> None:
    day = "2025-09-18"
    rows = _date_manifest(tmp_path, day, page_count=1)
    _, invalid = _validate_collection_manifest(tmp_path, [day], rows)
    assert day not in invalid

    first = tmp_path / f"sse-margin-{day.replace('-', '')}-page1.json"
    first.write_text(json.dumps({"detailsDate": day.replace("-", ""), "pageHelp": {"pageNo": 1, "pageCount": 2, "total": 1}, "result": []}))
    (tmp_path / f"sse-margin-{day.replace('-', '')}-page2.json").write_text("{}")
    rows[0]["sha256"] = hashlib.sha256(first.read_bytes()).hexdigest()
    _, invalid = _validate_collection_manifest(tmp_path, [day], rows)
    assert day in invalid
    assert "pageCount=2" in invalid[day]

