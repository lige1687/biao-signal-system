#!/usr/bin/env python3
"""Bounded local queries; only --generate may POST the opportunity ensure API."""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[4]
VIEWS = (
    "health",
    "overview",
    "storage",
    "portfolio",
    "watchlist",
    "fundamentals",
    "news",
    "plans",
    "trades",
    "factors",
    "research-search",
    "research-report",
    "latest-brief",
    "daily-review",
    "opportunities",
    "brief",
    "technical",
    "holding-market",
)
MAX_BYTES = 8 * 1024 * 1024


def select(row, keys):
    return {key: row[key] for key in keys if key in row}


def named_watchlist(data, names):
    """Use exact local identities, preserving supplied names and unresolved rows."""
    rows = []
    for original in data.get("items", []):
        row = dict(original)
        symbol = row.get("symbol", "")
        supplied = str(row.get("display_name") or "").strip()
        if supplied and supplied.upper() not in {symbol.upper(), symbol.split(".")[0].upper()}:
            row.update(display_name=supplied, name_source="watchlist")
        elif names.get(symbol):
            row.update(display_name=names[symbol], name_source="local_product_catalog")
        else:
            row.update(display_name="名称待核对", name_source="unresolved")
        rows.append(row)
    return {
        **data,
        "items": rows,
        "name_counts": dict(Counter(row["name_source"] for row in rows)),
    }


def compact(value, limit=6, path="$", omitted=None):
    """Bound payloads and disclose every omitted path; leave sources/errors intact."""
    if omitted is None:
        omitted = []
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            child = path + "." + key
            if key in {"sources", "errors", "limitations"}:
                result[key] = item
            elif key in {"chart", "content", "segments", "video_content"}:
                if item:
                    omitted.append({"path": child, "reason": "detail_on_request"})
            else:
                result[key] = compact(item, limit, child, omitted)
        return result
    if isinstance(value, list):
        if len(value) > limit:
            omitted.append({"path": path, "returned": limit, "total": len(value)})
        return [compact(v, limit, f"{path}[{i}]", omitted) for i, v in enumerate(value[:limit])]
    if isinstance(value, str) and len(value) > 1400:
        omitted.append({"path": path, "returned_chars": 1400, "total_chars": len(value)})
        return value[:1400]
    return value


def compact_board(board, args):
    rows = board.get("items", [])
    counts = dict(Counter(i.get("audit", {}).get("status", "unknown") for i in rows))
    if args.symbol:
        rows = [
            i
            for i in rows
            if args.symbol
            in {
                i.get("card", {}).get("subject", {}).get("id"),
                i.get("card", {}).get("subject", {}).get("symbol"),
            }
        ]
    if args.code:
        rows = [i for i in rows if i.get("card", {}).get("subject", {}).get("code") == args.code]
    if args.intent:
        rows = [i for i in rows if i.get("card", {}).get("intent") == args.intent]
    # Preserve server order. This script does not rank products or create signals.
    result = {k: v for k, v in board.items() if k != "items"}
    result.update(
        audit_counts=counts, matching_cards=len(rows), returned_cards=min(len(rows), args.limit)
    )
    result["items"] = []
    for row in rows[: args.limit]:
        card, audit = row.get("card", {}), row.get("audit", {})
        entry = select(row, ("review_id", "input_fingerprint"))
        entry["card"] = select(
            card,
            (
                "subject",
                "intent",
                "status",
                "headline",
                "data_as_of",
                "agent_eligible",
                "narrative_focus",
                "limitations",
                "searches",
            ),
        )
        grouped = {}
        for evidence in card.get("evidence", []):
            grouped.setdefault(evidence.get("role", "unknown"), []).append(evidence)
        entry["evidence_by_role"] = grouped
        entry["audit"] = audit
        result["items"].append(entry)
    return result


class Client:
    def __init__(self, context):
        self.context = context

    def call(self, path, method="GET"):
        get_ok = path in {"/api/health", "/api/watchlist"} or bool(
            re.fullmatch(
                r"/api/opportunity-reviews/(?:runs/orb_[a-f0-9]+|"
                r"preparations/opr_[a-f0-9]+|cards/ocr_[a-f0-9]+|"
                r"technical/[A-Za-z0-9.%^_-]+|market/holdings/[a-f0-9]+)",
                path,
            )
        )
        get_ok = get_ok or bool(
            re.fullmatch(
                r"/api/opportunity-reviews/runs/orb_[a-f0-9]{16,64}/brief\?subject_key="
                r"(?:symbol%3A[A-Za-z0-9.%^_-]{1,40}|holding%3A[a-f0-9]{12})",
                path,
            )
        )
        post_ok = method == "POST" and path == "/api/opportunity-reviews/ensure"
        if not ((method == "GET" and get_ok) or post_ok):
            raise ValueError("unsupported local query")
        request = Request(
            self.context.base_url + path,
            data=b"{}" if post_ok else None,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with self.context._opener.open(request, timeout=30) as response:
                raw = response.read(MAX_BYTES + 1)
        except HTTPError as exc:
            raise ValueError(f"local API HTTP {exc.code}") from None
        except (URLError, TimeoutError, OSError):
            raise ValueError(
                "local API unavailable or timed out; request was not retried"
            ) from None
        if len(raw) > MAX_BYTES:
            raise ValueError("local API response exceeds 8 MiB")
        result = json.loads(raw)
        if path == "/api/watchlist" and isinstance(result, list):
            return {"items": result, "count": len(result)}
        if not isinstance(result, dict):
            raise ValueError("expected JSON object")
        return result


def opportunity_query(client, args):
    """One ensure, then GET-only polling. Failed preparation never becomes success."""
    board, prep = None, None
    if args.generate:
        health = client.call("/api/health")
        if health.get("status") != "ok":
            return {"available": False, "errors": {"health": health}}
        board = client.call("/api/opportunity-reviews/ensure", "POST")
        prep_id = board.get("preparation_id")
    else:
        prep_id = args.preparation_id
    run_id = args.run_id or (board or {}).get("run_id")
    deadline = time.monotonic() + args.wait_seconds
    while True:
        if prep_id:
            prep = client.call("/api/opportunity-reviews/preparations/" + prep_id)
            if prep.get("status") == "complete":
                run_id = prep.get("run_id")
                if not run_id:
                    return {
                        "available": False,
                        "preparation": prep,
                        "errors": {"run": "completed preparation returned no run_id"},
                    }
                prep_id = None
            elif prep.get("status") == "failed":
                break
        if not prep_id and run_id:
            board = client.call("/api/opportunity-reviews/runs/" + run_id)
        if (prep or {}).get("review_error") or (board or {}).get("review_error"):
            break
        if not prep_id and (board or {}).get("status") in {"complete", "partial", "failed"}:
            break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(3, remaining))
    status = (board or {}).get("status")
    prep_failed = (prep or {}).get("status") == "failed"
    review_error = (prep or {}).get("review_error") or (board or {}).get("review_error")
    return {
        "available": board is not None,
        "preparation": prep,
        "generation_complete": not prep_failed
        and not review_error
        and not prep_id
        and status == "complete",
        "review_terminal": not prep_failed
        and not prep_id
        and status in {"complete", "partial", "failed"},
        "data": board if args.full else compact_board(board, args) if board else None,
        "errors": {"preparation": prep.get("error")}
        if prep_failed
        else {"review": review_error}
        if review_error
        else {},
        "resume": {"preparation_id": prep_id, "run_id": run_id},
        "limitations": [
            "完整审查以准备成功及run状态为准；pending/partial不能说全部完成。",
            "同一份资料的失败项不会由本脚本自动重试；不含计划或成交写入。",
        ],
    }


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("view", choices=VIEWS)
    p.add_argument("--repo", type=Path, default=ROOT)
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--code")
    p.add_argument("--symbol")
    p.add_argument("--holding-id")
    p.add_argument("--run-id")
    p.add_argument("--preparation-id")
    p.add_argument("--intent", choices=("buy", "sell"))
    p.add_argument(
        "--generate",
        action="store_true",
        help="opportunities only: one ensure POST, may invoke configured model",
    )
    p.add_argument("--wait-seconds", type=int, choices=range(46), default=0, metavar="0..45")
    p.add_argument("--limit", type=int, choices=range(1, 21), default=6, metavar="1..20")
    p.add_argument("--market", choices=("cn", "us"), default="cn")
    p.add_argument(
        "--section",
        choices=("observations", "overview", "rates", "us-macro", "rates-history", "macro-history"),
        default="observations",
    )
    p.add_argument("--query", default="")
    p.add_argument("--name", default="")
    p.add_argument("--slot", choices=("1135", "1440"), default="1440")
    p.add_argument(
        "--full",
        action="store_true",
        help="explicitly emit complete response; redirect to a local file before filtering",
    )
    return p


def validate(args):
    patterns = {
        "code": r"[0-9]{6}",
        "symbol": r"[A-Za-z0-9^][A-Za-z0-9.^_-]{0,31}",
        "holding_id": r"[a-f0-9]{6,64}",
        "run_id": r"orb_[a-f0-9]{16,64}",
        "preparation_id": r"opr_[a-f0-9]{16,64}",
    }
    for key, pattern in patterns.items():
        value = getattr(args, key)
        if value and not re.fullmatch(pattern, value):
            raise ValueError(f"invalid {key}")
    if args.generate and (args.view != "opportunities" or args.run_id or args.preparation_id):
        raise ValueError("--generate is only for a new opportunity ensure; resume uses GET IDs")
    if args.run_id and args.view not in {"opportunities", "brief"}:
        raise ValueError("run ID only applies to opportunities or brief")
    if (args.preparation_id or args.intent) and args.view != "opportunities":
        raise ValueError("review IDs and intent only apply to opportunities")
    if args.view == "brief" and (not args.run_id or bool(args.symbol) == bool(args.holding_id)):
        raise ValueError("brief requires --run-id and exactly one of --symbol/--holding-id")
    if args.view == "technical" and not args.symbol:
        raise ValueError("technical requires --symbol")
    if args.view == "holding-market" and not args.holding_id:
        raise ValueError("holding-market requires --holding-id")


def execute(args):
    validate(args)
    repo = args.repo.resolve()
    module_path = repo / "src/lei_signal/integrations/gpt_context.py"
    if not module_path.is_file():
        raise ValueError("system checkout unavailable; use --repo with the existing repository")
    sys.path.insert(0, str(repo / "src"))
    context = importlib.import_module("lei_signal.integrations.gpt_context").SystemContext(
        repo_root=repo,
        base_url=args.base_url,
    )
    client = Client(context)
    if args.view == "health":
        return client.call("/api/health")
    if args.view == "brief":
        key = "symbol:" + args.symbol if args.symbol else "holding:" + args.holding_id
        return client.call(
            "/api/opportunity-reviews/runs/"
            + args.run_id
            + "/brief?subject_key="
            + quote(key, safe="")
        )
    if args.view == "watchlist":
        names = importlib.import_module("lei_signal.copilot.subjects").catalog_names()
        identities = importlib.import_module(
            "lei_signal.integrations.gpt_context"
        ).product_identities(repo)
        names.update({symbol: row["name"] for symbol, row in identities.items()})
        return named_watchlist(client.call("/api/watchlist"), names)
    if args.view == "opportunities" and (args.generate or args.run_id or args.preparation_id):
        return opportunity_query(client, args)
    if args.view == "technical":
        data = client.call("/api/opportunity-reviews/technical/" + quote(args.symbol, safe=""))
        if not args.full:
            signals = data.get("signals", [])
            data["signals"] = [s for s in signals if s.get("is_recent")]
            data["signal_coverage"] = {
                "all": len(signals),
                "recent": len(data["signals"]),
                "history": "use --full; old/cleared events are not new opportunities",
            }
        return data
    if args.view == "holding-market":
        return client.call("/api/opportunity-reviews/market/holdings/" + args.holding_id)
    calls = {
        "overview": lambda: context.overview(args.query, args.limit),
        "storage": context.storage,
        "portfolio": lambda: context.portfolio(args.code),
        "fundamentals": lambda: context.fundamentals(args.market, args.section),
        "news": lambda: context.news(args.code, args.limit),
        "plans": lambda: context.plans(args.code),
        "trades": context.trades,
        "factors": context.factors,
        "research-search": lambda: context.research_search(args.query, args.limit),
        "research-report": lambda: context.research_report(args.name),
        "latest-brief": lambda: context.latest_brief(args.slot),
        "daily-review": lambda: context.daily_review(args.slot),
        "opportunities": context.opportunities,
    }
    result = calls[args.view]()
    if args.view == "opportunities":
        result["mode"] = "saved_scan_only"
        result.setdefault("limitations", []).append(
            "这是保存的扫描；今日Agent审查使用opportunities --generate。"
        )
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = execute(args)
    except (ValueError, OSError, ImportError) as exc:
        print(
            json.dumps(
                {"available": False, "errors": {"query": str(exc)}, "request_retried": False},
                ensure_ascii=False,
            )
        )
        return 1
    omitted = []
    output = result if args.full else compact(result, args.limit, omitted=omitted)
    print(
        json.dumps(
            {
                "view": args.view,
                "queried_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
                "result": output,
                "output_omissions": omitted,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
