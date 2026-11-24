"""Dated, public narrative sources for opportunity summaries; no network access."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

KINDS = ("macro", "sentiment", "news")
SOURCE_PATH = Path(__file__).resolve().parents[3] / "configs/opportunity-summary-sources.v1.json"
_SENTIMENT = re.compile(r"VIX|VXN|预期波动率|融资余额|融资买入|信用利差|投资者情绪", re.I)
_SENSITIVE = re.compile(
    r"持仓(?:编号|ID|id)|(?:持仓|投资|交易|申购|赎回)金额|账户|账号|成本价|原持仓计划|交易计划"
)


def valid_day(value: object, as_of: date) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        if len(value) == 10:
            day = date.fromisoformat(value)
        else:
            instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if instant.tzinfo is None:
                return None
            day = instant.date()
    except ValueError:
        return None
    return day.isoformat() if day <= as_of else None


def kind_for(evidence: dict) -> str | None:
    if evidence.get("provenance") == "unverified_news" or evidence.get("role") == "lead":
        return None
    narrative = evidence.get("narrative_kind")
    provenance = evidence.get("provenance")
    text = str(evidence.get("text") or "")
    if provenance == "local_macro_observation" or narrative == "macro":
        return "sentiment" if _SENTIMENT.search(text) else "macro"
    if (
        evidence.get("category") == "industry"
        and provenance == "verified_public_source"
        and narrative != "profile"
    ):
        return "news"
    return None


def curated_sources(symbol: str, name: str, as_of: date, *, path: Path = SOURCE_PATH) -> list[dict]:
    """An absent or invalid optional file supplies no facts; identity is exact."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if payload.get("schema_version") != 1 or not isinstance(payload.get("products"), list):
        return []
    result = []
    for row in payload["products"]:
        if not isinstance(row, dict) or row.get("symbol") != symbol or row.get("name") != name:
            continue
        kind = row.get("kind")
        method = row.get("evidence_type") == "method"
        support = row.get("supporting_source_ref")
        if support is not None and (
            not isinstance(support, str)
            or not support.startswith("https://")
            or not urlsplit(support).hostname
        ):
            continue
        if (
            kind not in KINDS
            or row.get("enabled") is False
            or (kind != "news" and not method)
            or (kind == "news" and method)
        ):
            continue
        published = valid_day(row.get("published_at"), as_of) if row.get("published_at") else None
        report = valid_day(row.get("report_date"), as_of) if row.get("report_date") else None
        checked = valid_day(row.get("checked_at"), as_of)
        ref = row.get("source_ref")
        body = row.get("text")
        source = row.get("source")
        if (
            (not published and not method)
            or (row.get("published_at") and not published)
            or not checked
            or (row.get("report_date") and not report)
            or (published and published > checked)
            or (report and published and report > published)
            or not isinstance(ref, str)
            or not ref.startswith("https://")
            or not urlsplit(ref).hostname
            or not isinstance(body, str)
            or not body.strip()
            or _SENSITIVE.search(body)
            or not isinstance(source, str)
            or not source.strip()
            or _SENSITIVE.search(source)
        ):
            continue
        result.append(
            {
                "id": "curated_"
                + hashlib.sha256(
                    json.dumps(row, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest()[:16],
                "text": body[:450],
                "source": source[:80],
                "source_ref": ref,
                "date": published if kind == "news" else report or published,
                "published_at": row.get("published_at"),
                "report_date": row.get("report_date"),
                "observation_date": row.get("report_date"),
                "checked_at": row["checked_at"],
                "provenance": "verified_public_source",
                "supporting_source_ref": support,
                "narrative_kind": kind,
                "relevance": row.get("relevance") or "industry_reference",
                "limitations": [
                    x[:180]
                    for x in (row.get("limitations") or [])
                    if isinstance(x, str) and not _SENSITIVE.search(x)
                ][:4],
                "category": "industry" if kind == "news" else "fundamentals",
                "kind": kind,
                "evidence_type": "method" if method else "observation",
                **{
                    key: row[key]
                    for key in (
                        "title",
                        "event_type",
                        "impact",
                        "meaning",
                        "counterpoint",
                        "importance_reason",
                        "priority",
                    )
                    if key in row
                },
            }
        )
    return result


def select_slots(sources: list[dict], *, max_each: int = 3, as_of: date | None = None) -> dict:
    """Cover each narrative kind with recent, relevant sources before capping."""
    slots = {}
    for kind in KINDS:
        rows = list({s["id"]: s for s in sources if s.get("kind") == kind}.values())
        if kind == "news" and as_of is not None:
            start = (as_of - timedelta(days=4)).isoformat()
            rows = [s for s in rows if start <= (valid_day(s.get("published_at"), as_of) or "")]
        rows.sort(
            key=lambda s: (
                s.get("evidence_type") != "method",
                s.get("relevance") in {"market_context", "industry_reference"},
                s.get("date") or "",
                s.get("published_at") or "",
                s["id"],
            ),
            reverse=True,
        )
        observations = [s for s in rows if s.get("evidence_type") != "method"]
        selected = observations[:max_each]
        method = next((s for s in rows if s.get("evidence_type") == "method"), None)
        if selected and method:
            selected = selected[: max_each - 1] + [method]
        limitations = [limit for s in selected for limit in s.get("limitations") or []]
        if not selected:
            limitations.append("没有可核对的同类公开资料")
        if kind == "news":
            limitations.append("行业资料只解释背景；不代表产品当前持仓或今日消息")
        if kind in {"macro", "sentiment"} and selected:
            limitations.append("单期观察不能证明方向或因果关系；首次公开时间未核时不能用于历史判断")
        slots[kind] = {"sources": selected, "limitations": list(dict.fromkeys(limitations))[:5]}
    return slots


def news_profiles(board: dict) -> list[dict]:
    """Use exact registered product identity; do not infer a fund's industry weights."""
    result = {}
    for item in board.get("items") or []:
        card = item.get("card") or item
        subject = card.get("subject") or {}
        symbol = subject.get("id") if subject.get("kind") == "symbol" else subject.get("symbol")
        focus = card.get("narrative_focus") or {}
        if isinstance(symbol, str) and focus.get("market") in {"cn", "us"}:
            result[symbol] = {**focus, "symbol": symbol, "name": subject.get("name") or symbol}
    return list(result.values())


def recent_news_watch(
    board: dict, as_of: date, *, path: Path = SOURCE_PATH, automated: dict | None = None
) -> dict:
    """Read verified original releases once across products; never fetch or score headlines.

    Selection order expresses the scope of the event, not a return prediction.
    The actual publication date controls freshness; check/report dates cannot renew it.
    """
    from lei_signal.copilot.subjects import catalog_names, display_name

    start = (as_of - timedelta(days=4)).isoformat()
    names = catalog_names()
    candidates = []
    symbols = {}
    unverified = 0
    for item in board.get("items") or []:
        card = item.get("card") or {}
        subject = card.get("subject") or {}
        symbol = subject.get("id") if subject.get("kind") == "symbol" else subject.get("symbol")
        if not isinstance(symbol, str) or not re.fullmatch(r"[A-Za-z0-9.^_-]{1,32}", symbol):
            continue
        name = names.get(symbol) or display_name(symbol, subject.get("name"))
        symbols[symbol] = name
        for source in card.get("evidence") or []:
            if source.get("provenance") == "unverified_news":
                unverified += 1
            if kind_for(source) == "news" and source.get("public") is True:
                candidates.append(
                    {**source, "scope": "industry", "products": [{"symbol": symbol, "name": name}]}
                )
    for symbol, name in sorted(symbols.items()):
        for source in curated_sources(symbol, name, as_of, path=path):
            if source["kind"] == "news":
                candidates.append(
                    {**source, "scope": "industry", "products": [{"symbol": symbol, "name": name}]}
                )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = {}
    if payload.get("schema_version") == 1:
        candidates.extend(x for x in payload.get("events", []) if isinstance(x, dict))
    automatic = automated or {}
    for event in automatic.get("events") or []:
        # Source publication date and polling time remain separate.
        excerpt = str(event.get("text") or "")
        if event.get("source_id") == "cn-nbs" and "分享到：" in excerpt:
            # Keep the saved original intact; remove the known publisher header
            # only from this display copy, through its explicit release date.
            excerpt = re.sub(r"^.*?20\d{2}年\d{1,2}月\d{1,2}日\s*", "", excerpt, count=1)
        candidates.append({**event, "text": excerpt,
                           "checked_at": str(event.get("checked_at") or "")[:10]})
    grouped = {}
    for source in candidates:
        published = valid_day(source.get("published_at"), as_of)
        report = valid_day(source.get("report_date"), as_of) if source.get("report_date") else None
        checked = valid_day(source.get("checked_at"), as_of) if source.get("checked_at") else None
        ref = source.get("source_ref")
        text = source.get("text")
        if (
            not published
            or source.get("enabled") is False
            or source.get("provenance") != "verified_public_source"
            or not isinstance(ref, str)
            or not ref.startswith("https://")
            or not urlsplit(ref).hostname
            or not isinstance(text, str)
            or not text.strip()
            or _SENSITIVE.search(text)
            or (report and report > published)
            or (source.get("report_date") and not report)
            or (source.get("checked_at") and (not checked or published > checked))
        ):
            continue
        scope = source.get("scope")
        if scope not in {"macro", "industry"}:
            continue
        parts = urlsplit(ref)
        canonical_path = re.sub(
            r"/(?:(?:default|index)\.html?)$", "", parts.path, flags=re.IGNORECASE
        )
        key = urlunsplit(
            (parts.scheme.lower(), parts.netloc.lower(), canonical_path.rstrip("/") or "/", "", "")
        ) + "|" + published
        product_rows = [
            p
            for p in source.get("products") or []
            if isinstance(p, dict) and p.get("symbol") in symbols
        ]
        if scope == "industry" and not product_rows:
            continue
        existing = grouped.get(key)
        if existing:
            for product in product_rows:
                if product["symbol"] not in {p["symbol"] for p in existing["products"]}:
                    existing["products"].append(product)
            continue
        category = source.get("event_type") or "industry_update"
        category_labels = {
            "policy": "影响全市场的政策变化",
            "macro_release": "官方经济数据发布",
            "earnings": "行业重要公司的经营披露",
            "industry_update": "与观察产品相关的行业原件",
        }
        impact = source.get("impact", "neutral")
        if impact not in {"positive", "negative", "mixed", "neutral", "unknown"}:
            impact = "unknown"
        grouped[key] = {
            "id": "news_" + hashlib.sha256(key.encode()).hexdigest()[:16],
            "scope": scope,
            "market": source.get("market"),
            "title": str(source.get("title") or re.split(r"[。；]", text)[0])[:75],
            "text": text[:450],
            "meaning": str(source.get("meaning") or "")[:160],
            "counterpoint": str(source.get("counterpoint") or "")[:160],
            "impact": impact,
            "published_at": published,
            "report_date": report,
            "checked_at": checked,
            "source": str(source.get("source") or "公开原件")[:80],
            "source_ref": ref,
            "event_type": category,
            "priority": "high"
            if source.get("priority") == "high" and source.get("importance_reason")
            else "normal",
            "importance_reason": str(
                source.get("importance_reason")
                or category_labels.get(category, category_labels["industry_update"])
            )[:120],
            "products": product_rows,
            "limitations": source.get("limitations") or [],
        }
    priority = {"policy": 0, "macro_release": 1, "earnings": 2, "industry_update": 3}
    rows = sorted(
        grouped.values(),
        key=lambda row: (
            row["priority"] != "high",
            priority.get(row["event_type"], 3),
            -date.fromisoformat(row["published_at"]).toordinal(),
            row["id"],
        ),
    )
    current = [row for row in rows if row["published_at"] >= start]
    # Latest already-verified macro release is useful as reference, but is never
    # relabelled as a recent event. Retire even references after one quarter.
    older = [
        row
        for row in rows
        if row["scope"] == "macro"
        and (as_of - timedelta(days=90)).isoformat() <= row["published_at"] < start
    ]
    return {
        "macro_news": [row for row in current if row["scope"] == "macro"][:3],
        "industry_news": [row for row in current if row["scope"] == "industry"][:3],
        "older_macro_news": sorted(older, key=lambda row: row["published_at"], reverse=True)[:3],
        "news_coverage": {
            "verified_recent": len(current),
            "unverified_titles": unverified,
            "older_industry_excluded": sum(
                row["scope"] == "industry" and row["published_at"] < start for row in rows
            ),
        },
        "news_update": automatic.get("coverage") or {},
        "news_limitations": [
            "按已核原件的影响范围与发布日期优先展示，尚未覆盖全部新闻；未核标题不参与判断。"
        ],
    }
