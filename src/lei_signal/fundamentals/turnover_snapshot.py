"""Validated fixed historical stock-turnover observation; no source fetching."""

from __future__ import annotations

import json
import hashlib
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from lei_signal.fundamentals import sources
from lei_signal.fundamentals.observation_meta import observation_item


SNAPSHOT_PATH = Path(__file__).resolve().parents[3] / "data/market_observations/stock-turnover-20260929.json"
DATES = (
    "2026-08-31", "2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04",
    "2026-09-07", "2026-09-08", "2026-09-09", "2026-09-10", "2026-09-11",
    "2026-09-14", "2026-09-15", "2026-09-16", "2026-09-17", "2026-09-18",
    "2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24", "2026-09-28",
    "2026-09-29",
)
EVIDENCE_SHA256 = {
    "docs/experiments/raw/market-turnover-21day-2026-10-01/qualified-21day-input-values.json": "3b36cdf71735a49500b50b803339cd4ae15d41b7e887a2d72938e6af31a51e6a",
    "docs/experiments/raw/market-turnover-21day-2026-10-01/independent-final-21day-acceptance.json": "06a03b640fff4c13ffbae01d9eff9de4d16b207c93a9c4433e71ca02672b8b60",
}
SSE_URL = "https://www.sse.com.cn/market/stockdata/overview/day/"
SZSE_URL = "https://www.szse.cn/market/overview/index.html"
AMOUNT_RE = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]{1,2})?\Z")
HASH_RE = re.compile(r"[0-9a-f]{64}\Z")
PINNED_DAILY_SHA256 = "0e595e3b8e9294e898edf3b519bac6c6cf0dd1cd3f273b57a9e43bbf0030040d"


def _invalid(reason: str) -> sources.FundamentalsSourceError:
    return sources.FundamentalsSourceError(f"成交额历史快照无效：{reason}")


def _amount(value: Any, field: str) -> Decimal:
    if not isinstance(value, str) or not AMOUNT_RE.fullmatch(value):
        raise _invalid(f"{field} 格式或精度错误")
    number = Decimal(value)
    if not number.is_finite() or number <= 0:
        raise _invalid(f"{field} 必须是正数")
    return number


def load_turnover_snapshot(path: Path | None = None) -> dict[str, Any]:
    """Return only the pinned 2026-09-29 observation and its prior-20-day comparison."""
    path = path or SNAPSHOT_PATH
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _invalid("文件缺失或JSON损坏") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != "fixed-stock-turnover/1":
        raise _invalid("版本不符")
    if (raw.get("observation_date"), raw.get("history_start"), raw.get("history_end")) != (
        "2026-09-29", DATES[0], DATES[-1]
    ):
        raise _invalid("不是已核固定历史窗口")
    if raw.get("units") != {"sse": "亿元", "szse": "元", "display": "亿元"}:
        raise _invalid("金额单位不符")
    if raw.get("source_urls") != [SSE_URL, SZSE_URL]:
        raise _invalid("交易所来源不符")
    evidence = raw.get("source_evidence")
    if not isinstance(evidence, list) or {e.get("path"): e.get("sha256") for e in evidence if isinstance(e, dict)} != EVIDENCE_SHA256 or len(evidence) != 2:
        raise _invalid("来源证据指纹不符")
    if raw.get("first_published_at") is not None or raw.get("refresh_policy") != "fixed historical snapshot only; no automatic update":
        raise _invalid("首次发布时间或刷新语义被改变")
    daily = raw.get("daily")
    if not isinstance(daily, list) or len(daily) != len(DATES):
        raise _invalid("交易日缺失")
    observed_dates = [row.get("date") if isinstance(row, dict) else None for row in daily]
    if tuple(observed_dates) != DATES:
        raise _invalid("交易日重复、缺失或超出固定窗口")
    canonical_daily = json.dumps(daily, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    if hashlib.sha256(canonical_daily).hexdigest() != PINNED_DAILY_SHA256:
        raise _invalid("逐日数值或原始来源身份与已核快照不符")
    combined: list[Decimal] = []
    for row in daily:
        for name in ("sse_raw_sha256", "szse_raw_sha256"):
            if not isinstance(row.get(name), str) or not HASH_RE.fullmatch(row[name]):
                raise _invalid(f"{name} 缺失或无效")
        sse = _amount(row.get("sse_a_yi"), "上海金额")
        szse = _amount(row.get("szse_a_yuan"), "深圳金额")
        combined.append(sse + szse / Decimal("100000000"))
    target = combined[-1]
    prior_mean = sum(combined[:-1]) / Decimal(20)
    if prior_mean <= 0:
        raise _invalid("此前20日均值无效")
    value = float(target.quantize(Decimal("0.01")))
    change = float(((target / prior_mean - 1) * 100).quantize(Decimal("0.01")))
    return observation_item(
        metric_id="stock_turnover", label="A股股票成交额", market="cn",
        universe="沪深A股股票（上交所主板A股和科创板；深交所主板A股和创业板A股）",
        value=value, unit="亿元", change=change, change_unit="%",
        comparison_period="相对此前20个完整交易日均值",
        observation_date=DATES[-1], published_at=None, publication_precision="unknown",
        fetched_at=None, history_start=DATES[0], history_end=DATES[-1],
        observation_count=21, valid_count=21, eligible_count=21,
        source_name="上交所、深交所每日成交统计（固定历史快照）",
        source_url=SSE_URL, source_access="public_web",
        reading="仅说明截至2026-09-29的历史交易活跃度，不表示当前市场，也不参与交易判定。",
        limitations=[
            "首次公布时间与修订记录未核实，不能用作当时已知的收益研究资料",
            "固定历史资料；未来日期及自动刷新未核实",
            "排除B股、基金、北交所、回购和重复父分类；上海公布精度为两位亿元",
        ],
        evidence_refs=[SSE_URL, SZSE_URL, *EVIDENCE_SHA256],
        quality_reason="固定历史读数；首次公布时间和未来更新时效未核实",
    )
