"""Read-only disclosed fund constituents for explanation, never trading signals."""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "configs" / "fund-disclosures.v1.json"
_QUARTER_END = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}


@dataclass(frozen=True)
class DisclosureCatalog:
    records: dict[str, dict]
    error: str | None = None


def _valid_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _source_date(value: object, *, allow_time: bool, today: date) -> date:
    if not isinstance(value, str) or not value:
        raise ValueError("来源或报告日期缺失")
    try:
        parsed = (datetime.fromisoformat(value.replace("Z", "+00:00")).date()
                  if allow_time else date.fromisoformat(value))
    except ValueError as exc:
        raise ValueError("来源或报告日期格式无效") from exc
    if parsed > today:
        raise ValueError("来源或报告日期在未来")
    return parsed


def _recheck_required(value: object, today: date) -> bool:
    if not isinstance(value, str) or not value:
        return True
    try:
        checked = datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return True
    return checked != today


def _invalid(row: dict, reason: str, today: date) -> dict:
    return {
        **{key: row.get(key) for key in (
            "fund_code", "fund_name", "checked_at", "source_url", "source_name",
            "published_at", "report_period", "report_date", "official_report_url",
        )},
        "status": "invalid",
        "is_realtime": False,
        "source_recheck_required": _recheck_required(row.get("checked_at"), today),
        "scope": "direct_stock_top10",
        "summary": "披露资料校验未通过，不能据此判断行业分布。",
        "coverage_pct": None,
        "industry_coverage_pct": None,
        "unknown_pct": None,
        "industry_unknown_pct": None,
        "by_industry_pct": {},
        "holdings": [],
        "limitations": [reason],
    }


def _validated(row: dict, today: date) -> dict:
    code = row.get("fund_code")
    if not isinstance(code, str) or not re.fullmatch(r"\d{6}", code):
        raise ValueError("基金代码不是六位数字")
    if row.get("scope") != "direct_stock_top10":
        raise ValueError("披露范围不是直接股票前十")
    if row.get("status") not in {"available", "unavailable"}:
        raise ValueError("披露状态无效")
    if not _valid_url(row.get("source_url")) or not isinstance(row.get("source_name"), str) or not row["source_name"].strip():
        raise ValueError("披露来源名称或链接缺失")
    if row.get("official_report_url") is not None and not _valid_url(row["official_report_url"]):
        raise ValueError("官方报告链接无效")
    checked = _source_date(row.get("checked_at"), allow_time=True, today=today)
    period = row.get("report_period")
    report_value = row.get("report_date")
    report_unknown = report_value in (None, "", "unknown") and period in (None, "", "unknown")
    if row["status"] == "available" or not report_unknown:
        report_day = _source_date(report_value, allow_time=False, today=today)
        match = re.fullmatch(r"(\d{4})Q([1-4])", period) if isinstance(period, str) else None
        if not match or report_value != f"{match.group(1)}-{_QUARTER_END[int(match.group(2))]}":
            raise ValueError("报告季度与截止日期不一致")
        if checked < report_day:
            raise ValueError("来源核查日期早于报告截止日期")
    else:
        report_day = None
    published = row.get("published_at")
    if published is not None:
        published_day = _source_date(published, allow_time=True, today=today)
        if published_day > checked or (report_day is not None and published_day < report_day):
            raise ValueError("报告发布日期与截止日或核查日冲突")
    raw_holdings = row.get("holdings")
    if not isinstance(raw_holdings, list) or len(raw_holdings) > 10:
        raise ValueError("前十成分行数无效")
    if row["status"] == "unavailable" and raw_holdings:
        raise ValueError("不可用记录不能包含成分")
    if row["status"] == "available" and not raw_holdings:
        raise ValueError("可用记录缺少成分")
    limitations = row.get("limitations") or []
    if not isinstance(limitations, list) or any(not isinstance(v, str) for v in limitations):
        raise ValueError("资料限制说明格式无效")
    limitations = list(limitations)
    cleaned = []
    by_industry: dict[str, float] = {}
    seen: set[str] = set()
    total = industry_total = 0.0
    no_industry_source = 0
    for holding in raw_holdings:
        if not isinstance(holding, dict):
            raise ValueError("成分行格式无效")
        stock_code, stock_name = holding.get("stock_code"), holding.get("stock_name")
        if not isinstance(stock_code, str) or not stock_code.strip() or stock_code in seen:
            raise ValueError("成分代码缺失或重复")
        if not isinstance(stock_name, str) or not stock_name.strip():
            raise ValueError("成分名称缺失")
        seen.add(stock_code)
        weight = holding.get("weight_pct")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or not 0 <= weight <= 100:
            raise ValueError("成分权重无效")
        weight = float(weight)
        total += weight
        market = holding.get("market", "unknown")
        if market not in {"cn", "hk", "us", "other", "unknown"}:
            raise ValueError("成分市场分类无效")
        label, label_url = holding.get("industry_label"), holding.get("industry_source_url")
        confirmed_label = label.strip() if isinstance(label, str) and label.strip() and _valid_url(label_url) else None
        if label and not confirmed_label:
            no_industry_source += 1
        if confirmed_label:
            industry_total += weight
            by_industry[confirmed_label] = by_industry.get(confirmed_label, 0) + weight
        cleaned.append({
            "stock_code": stock_code, "stock_name": stock_name, "weight_pct": weight,
            "market": market, "industry_label": confirmed_label,
            "industry_source_url": label_url if confirmed_label else None,
            "classification_note": holding.get("classification_note")
            if isinstance(holding.get("classification_note"), str) else None,
        })
    if total > 100 + 1e-9:
        raise ValueError("直接股票前十权重合计超过基金净值100%")
    if no_industry_source:
        limitations.append(f"{no_industry_source}条行业标签缺少可核来源链接，按未知处理。")
    if checked < today:
        limitations.append(f"来源上次核对为{checked.isoformat()}，本次尚未检查更近披露。")
    limitations.append("直接股票前十不代表基金全部资产或当前持仓；未披露部分保留未知。")
    limitations.append("行业标签概括公司主要业务，不是按各业务收入精确拆分。")
    return {
        **{key: row.get(key) for key in (
            "fund_code", "fund_name", "checked_at", "source_url", "source_name",
            "scope", "published_at", "report_period", "report_date", "status",
            "official_report_url",
        )},
        "holdings": cleaned, "limitations": limitations,
        "is_realtime": False,
        "source_recheck_required": checked < today,
        "summary": (
            f"截至{checked.isoformat()}核对的公开记录：{period}直接股票前十，"
            f"覆盖基金净值{total:.2f}%，有来源的行业标签覆盖{industry_total:.2f}%。"
            if row["status"] == "available"
            else f"截至{checked.isoformat()}核对的公开记录尚无可用直接股票前十，行业分布未知。"
        ),
        "coverage_pct": round(total, 4),
        "industry_coverage_pct": round(industry_total, 4),
        "unknown_pct": round(100 - total, 4),
        "industry_unknown_pct": round(100 - industry_total, 4),
        "by_industry_pct": {key: round(value, 4) for key, value in sorted(by_industry.items())},
    }


def load_disclosures(path: Path = DEFAULT_PATH, *, today: date | None = None) -> DisclosureCatalog:
    """Read once per workspace snapshot; malformed rows stay invalid, never guessed."""
    if not path.exists():
        return DisclosureCatalog({})
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return DisclosureCatalog({}, "披露配置无法读取或解析")
    if not isinstance(payload, dict) or payload.get("schema_version") != 1 or not isinstance(payload.get("funds"), list):
        return DisclosureCatalog({}, "披露配置版本或基金列表无效")
    records: dict[str, dict] = {}
    current = today or date.today()
    for row in payload["funds"]:
        if not isinstance(row, dict):
            continue
        code = row.get("fund_code")
        if not isinstance(code, str) or not re.fullmatch(r"\d{6}", code):
            continue
        try:
            result = _validated(row, current)
        except ValueError as exc:
            result = _invalid(row, str(exc), current)
        if code in records:
            records[code] = _invalid(row, "同一基金代码出现重复披露记录", current)
        else:
            records[code] = result
    return DisclosureCatalog(records)


def disclosure_for_holding(code: str | None, name: str, catalog: DisclosureCatalog) -> dict:
    if catalog.error:
        return _invalid({"fund_code": code, "fund_name": name}, catalog.error, date.today())
    if not code or code not in catalog.records:
        return {
            "fund_code": code, "fund_name": name, "status": "missing",
            "is_realtime": False, "source_recheck_required": True,
            "scope": "direct_stock_top10", "summary": "尚无可核的成分披露资料，行业分布未知。",
            "coverage_pct": None, "industry_coverage_pct": None,
            "unknown_pct": None, "industry_unknown_pct": None,
            "by_industry_pct": {}, "holdings": [],
            "limitations": ["未取得与该基金代码准确匹配的披露记录。"],
        }
    result = dict(catalog.records[code])
    result["limitations"] = list(result["limitations"])
    if re.search(r"联接|FOF", name, re.I):
        result["limitations"].append(
            "联接基金或FOF可能主要持有其他基金；直接股票前十不能代表目标基金或完整行业暴露。"
        )
    return result
