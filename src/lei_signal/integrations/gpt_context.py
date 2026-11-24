"""Bounded, local, read-only facts for GPT-facing conversations.

This module transports existing system evidence through GET calls. It does not
explicitly request a refresh, though existing GET handlers may update public
background data when their cache expires or initialize local storage. It does
not interpret plans as signals or research reports as trading approval.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from zoneinfo import ZoneInfo

from lei_signal.integrations.storage_health import collect_storage_health

_MAX_HTTP_BYTES = 4 * 1024 * 1024
_MAX_PACKET_BYTES = 8 * 1024 * 1024
_FUND_CODE = re.compile(r"^[0-9]{6}$")
_SHANGHAI = ZoneInfo("Asia/Shanghai")
_FUNDAMENTAL_SECTIONS = {
    "overview": ("/api/fundamentals/overview", "mixed"),
    "rates": ("/api/fundamentals/rates", "mixed"),
    "us-macro": ("/api/fundamentals/us-macro", "us"),
    "rates-history": ("/api/fundamentals/rates-history?lookback_days=1095", "mixed"),
    "macro-history": ("/api/fundamentals/macro-history?page_size=60", "cn"),
}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _loopback_base(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "http" or parsed.username or parsed.password:
        raise ValueError("base_url must be unauthenticated loopback HTTP")
    if parsed.path or parsed.query or parsed.fragment or not parsed.hostname:
        raise ValueError("base_url must not contain a path, query or fragment")
    try:
        host_ok = ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        host_ok = parsed.hostname == "localhost"
    if not host_ok or parsed.port is None:
        raise ValueError("base_url must use an explicit loopback host and port")
    return value


def _allowed_path(path: str) -> bool:
    return path in {
        "/api/portfolio/workspace",
        "/api/portfolio",
        "/api/plans",
        "/api/plans/summary",
        "/api/factors/panel",
        "/api/experiments",
        "/api/upgrades",
        "/api/watchlist",
        "/api/opportunities/today",
        "/api/fundamentals/observations?market=cn",
        "/api/fundamentals/observations?market=us",
        *(path for path, _ in _FUNDAMENTAL_SECTIONS.values()),
    } or bool(
        re.fullmatch(
            r"/api/symbols/(?:[0-9]{6}\.(?:SS|SZ)|[A-Z]{1,6}|\^[A-Z0-9]{1,12}|TH[0-9]{6}\.SECTOR)/(?:detail|buy-point-review)",
            path,
        )
    )


def _is_fund_code(value: str | None) -> bool:
    return value is not None and bool(_FUND_CODE.fullmatch(value))


def product_identities(repo_root: Path | None = None) -> dict[str, dict]:
    """Display identity only; never price or market-data qualification."""
    root = repo_root or Path(__file__).resolve().parents[3]
    try:
        value = json.loads((root / "configs/chat-product-identities.v1.json").read_text())
        return {
            k: v
            for k, v in value.get("products", {}).items()
            if re.fullmatch(r"(?:[0-9]{6}\.(SS|SZ)|[A-Z]{1,6})", k)
            and isinstance(v, dict)
            and v.get("name")
            and v.get("source_url")
        }
    except (OSError, ValueError, TypeError):
        return {}


class SystemContext:
    """Read an explicitly bounded set of local facts, with per-source failures.

    ``fetch`` is injectable for offline verification and receives a whitelisted
    relative API path. The default transport bypasses proxies and redirects.
    """

    def __init__(
        self,
        repo_root: str | Path | None = None,
        base_url: str = "http://127.0.0.1:8000",
        *,
        fetch: Callable[[str], dict[str, Any] | list[Any]] | None = None,
    ) -> None:
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[3]).resolve()
        self.base_url = _loopback_base(base_url)
        self._fetch_override = fetch
        self._opener = build_opener(ProxyHandler({}), _NoRedirect())

    def _get(self, path: str) -> dict[str, Any] | list[Any]:
        if not _allowed_path(path):
            raise ValueError("API path is not on the read-only allowlist")
        if self._fetch_override is not None:
            result = self._fetch_override(path)
            if not isinstance(result, (dict, list)):
                raise ValueError("API response must be JSON object or array")
            return result
        request = Request(self.base_url + path, method="GET")
        timeout = (
            45 if path.endswith("/detail") else 30 if path == "/api/fundamentals/us-macro" else 8
        )
        try:
            with self._opener.open(request, timeout=timeout) as response:
                if response.status != 200:
                    raise ValueError(f"HTTP {response.status}")
                size = response.headers.get("Content-Length")
                if size and int(size) > _MAX_HTTP_BYTES:
                    raise ValueError("API response too large")
                raw = response.read(_MAX_HTTP_BYTES + 1)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise ValueError(f"local API unavailable: {exc}") from exc
        if len(raw) > _MAX_HTTP_BYTES:
            raise ValueError("API response too large")
        try:
            result = json.loads(raw)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid local API JSON") from exc
        if not isinstance(result, (dict, list)):
            raise ValueError("API response must be JSON object or array")
        return result

    @staticmethod
    def _result(
        view: str,
        data: Any = None,
        *,
        sources: dict | None = None,
        limitations: list[str] | None = None,
        errors: dict | None = None,
        generated_at: str | None = None,
    ) -> dict[str, Any]:
        return {
            "view": view,
            "available": data is not None,
            "generated_at": datetime.now(_SHANGHAI).isoformat(),
            "data": data,
            "sources": sources or {},
            "limitations": limitations or [],
            "errors": errors or {},
        }

    def _collect(self, paths: dict[str, str]) -> tuple[dict, dict, dict]:
        data, errors, sources = {}, {}, {}

        def get_one(pair: tuple[str, str]) -> tuple[str, Any, str | None, str]:
            name, path = pair
            retrieved_at = datetime.now(_SHANGHAI).isoformat()
            try:
                return name, self._get(path), None, retrieved_at
            except (ValueError, TypeError) as exc:
                return name, None, str(exc), retrieved_at

        with ThreadPoolExecutor(max_workers=min(4, len(paths) or 1)) as pool:
            results = list(pool.map(get_one, paths.items()))
        for name, value, error, retrieved_at in results:
            if error:
                errors[name] = error
            else:
                expected_list = name in {"plans", "watchlist"}
                if not isinstance(value, list if expected_list else dict):
                    errors[name] = "invalid API schema: expected " + (
                        "list" if expected_list else "object"
                    )
                else:
                    data[name] = value
            sources[name] = {
                "path": paths[name],
                "retrieved_at": retrieved_at,
                "available": name in data,
                "error": errors.get(name),
                "source_generated_at": value.get("generated_at")
                if isinstance(value, dict)
                else None,
            }
        return data, errors, sources

    def _packet(
        self, slot: str | None = None
    ) -> tuple[dict | None, str | None, str | None, list[dict]]:
        if slot not in (None, "1135", "1440"):
            return None, None, "slot must be 1135 or 1440", []
        directory = self.repo_root / "data/cache/portfolio-chat-briefing"
        candidates = directory.glob("packet-*.json") if directory.is_dir() else []
        files = sorted(candidates, key=lambda p: p.name, reverse=True)
        rejected = []
        for path in files:
            try:
                if not path.resolve().is_relative_to(directory.resolve()):
                    raise ValueError("packet path escapes cache directory")
                if path.stat().st_size > _MAX_PACKET_BYTES:
                    raise ValueError("packet too large")
                raw = path.read_bytes()
                if len(raw) > _MAX_PACKET_BYTES:
                    raise ValueError("packet too large")
                packet = json.loads(raw)
                if not isinstance(packet, dict) or packet.get("slot") not in {"1135", "1440"}:
                    raise ValueError("invalid packet schema")
                if slot and packet.get("slot") != slot:
                    continue
                if not isinstance(packet.get("generated_at"), str):
                    raise ValueError("packet timestamp missing")
                stamp = datetime.fromisoformat(packet["generated_at"])
                if stamp.tzinfo is None:
                    raise ValueError("packet timestamp lacks timezone")
                if stamp > datetime.now(_SHANGHAI):
                    raise ValueError("packet timestamp is in the future")
                return packet, str(path), None, rejected
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                rejected.append({"path": str(path), "reason": str(exc)})
        return None, None, "no readable local briefing packet", rejected

    @staticmethod
    def _packet_sources(packet: dict | None, path: str | None, rejected: list[dict]) -> dict:
        return {
            "briefing_packet": {
                "path": path,
                "retrieved_at": datetime.now(_SHANGHAI).isoformat(),
                "available": packet is not None,
                "source_generated_at": packet.get("generated_at") if packet else None,
                "fallback": bool(rejected),
                "rejected": rejected,
            }
        }

    @staticmethod
    def _packet_errors(packet: dict, view: str) -> dict:
        errors = {}
        status = packet.get("source_status") or {}
        relevant = {
            "news": ("news", "news_status"),
            "trades": ("trades",),
            "latest_brief": tuple(status),
        }.get(view, ())
        for name in relevant:
            source = status.get(name) or {}
            if source.get("ok") is False:
                errors[name] = source.get("error") or "source unavailable"
        if view in {"news", "latest_brief"}:
            receipt = (packet.get("news_coverage") or {}).get("last_run") or {}
            if receipt.get("errors"):
                errors["news_receipt"] = receipt["errors"]
            if receipt.get("status") == "failed":
                errors["news_receipt_status"] = "failed"
        if (
            view in {"trades", "latest_brief"}
            and (packet.get("trade_ledger") or {}).get("available") is False
        ):
            errors["trade_ledger"] = "trade ledger unavailable in packet"
        return errors

    def storage(self) -> dict[str, Any]:
        """Read fixed disk identities, capacity and resource paths without API calls."""
        health = collect_storage_health(self.repo_root)
        response = self._result(
            "storage",
            health,
            sources={
                "storage": {
                    "retrieved_at": health.get("checked_at"),
                    "available": health.get("severity") != "unknown",
                    "scope": "本机固定存储策略、容量与已登记资源路径，只读检查",
                }
            },
            limitations=[
                "这是检查时的容量，不能保证之后仍有空间；未控制其他任务的写入。",
                "只对本日报新增音频工作执行预检，不自动删除资料或修改交易记录。",
                "resources[].read_path 仅在本次核对设备和目录后可用；不授权迁移或新写入。",
            ],
            errors={"storage": health.get("reasons")}
            if health.get("severity") == "unknown"
            else {},
        )
        response["available"] = health.get("severity") != "unknown"
        return response

    def overview(self, query: str = "", limit: int = 10) -> dict[str, Any]:
        if not isinstance(query, str) or len(query) > 160 or "\x00" in query:
            return self._result(
                "overview", errors={"query": "query must be at most 160 characters without NUL"}
            )
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
            return self._result(
                "overview", errors={"limit": "limit must be an integer from 1 to 20"}
            )
        data, errors, sources = self._collect(
            {
                "workspace": "/api/portfolio/workspace",
                "portfolio": "/api/portfolio",
                "plans_summary": "/api/plans/summary",
                "fundamentals_cn": "/api/fundamentals/observations?market=cn",
                "fundamentals_us": "/api/fundamentals/observations?market=us",
                "factors": "/api/factors/panel",
                "research": "/api/experiments",
                "upgrades": "/api/upgrades",
            }
        )
        packet, path, packet_error, rejected = self._packet()
        if packet_error:
            errors["briefing_packet"] = packet_error
        if rejected:
            errors["briefing_packet_fallback"] = rejected
        if packet:
            errors.update(
                {f"packet_{k}": v for k, v in self._packet_errors(packet, "latest_brief").items()}
            )
        research = data.get("research") or {}
        upgrades = data.get("upgrades") or {}
        upgrades_available = "upgrades" in data
        upgrade_items = upgrades.get("items") if upgrades_available else None
        if upgrades_available and not isinstance(upgrade_items, list):
            errors["upgrades"] = "invalid upgrades items schema"
            sources["upgrades"]["available"] = False
            sources["upgrades"]["error"] = errors["upgrades"]
            upgrades_available = False
            upgrade_items = None
        upgrade_matches = []
        status_counts = {}
        if upgrades_available:
            needle = query.casefold()
            for item in upgrade_items:
                if not isinstance(item, dict):
                    continue
                status = str(item.get("status") or "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
                searchable = " ".join(
                    str(item.get(field) or "")
                    for field in ("id", "title", "owner", "evidence", "next_action")
                ).casefold()
                if not needle or needle in searchable:
                    upgrade_matches.append(item)

        def compact_goal(item: dict) -> dict:
            evidence = str(item.get("evidence") or "")
            next_action = str(item.get("next_action") or "")
            links = item.get("links") if isinstance(item.get("links"), list) else []
            auth = item.get("authorization") if isinstance(item.get("authorization"), dict) else {}
            return {
                "id": item.get("id"),
                "title": item.get("title"),
                "kind": item.get("kind"),
                "status": item.get("status"),
                "owner": item.get("owner"),
                "progress": item.get("progress"),
                "evidence": evidence[:500],
                "links": links[:5],
                "next_action": next_action[:300],
                "updated_at": item.get("updated_at"),
                "authorization": {key: auth.get(key) for key in ("granted", "at")},
                "authorization_scope_omitted": True,
                "fields_truncated": {
                    "evidence": len(evidence) > 500,
                    "next_action": len(next_action) > 300,
                },
                "links_truncated": len(links) > 5,
            }

        upgrade_summary = {
            "generated_at": upgrades.get("generated_at") if upgrades_available else None,
            "total": len(upgrade_items) if upgrades_available else None,
            "matched_total": len(upgrade_matches) if upgrades_available else None,
            "returned": min(limit, len(upgrade_matches)) if upgrades_available else 0,
            "truncated": len(upgrade_matches) > limit if upgrades_available else None,
            "status_counts": status_counts if upgrades_available else None,
            "query": query,
            "limit": limit,
            "items": [compact_goal(item) for item in upgrade_matches[:limit]],
        }
        summary = {
            "access_scope": "local_codex_tool_only",
            "chatgpt_direct_local_connection_verified": False,
            "workspace": {
                k: data.get("workspace", {}).get(k) for k in ("generated_at", "as_of", "coverage")
            },
            "portfolio_as_of": data.get("portfolio", {}).get("as_of"),
            "plans_summary": data.get("plans_summary"),
            "fundamentals": {
                m: {
                    "generated_at": (data.get(f"fundamentals_{m}") or {}).get("generated_at"),
                    "items": len((data.get(f"fundamentals_{m}") or {}).get("items", [])),
                }
                for m in ("cn", "us")
            },
            "factors": {
                k: (data.get("factors") or {}).get(k)
                for k in (
                    "generated_at",
                    "data_as_of",
                    "study_date",
                    "research_proxy_note",
                    "counts",
                )
            },
            "research_count": len(research.get("items", [])),
            "system_upgrades": upgrade_summary,
            "briefing_packet_at": packet.get("generated_at") if packet else None,
            "briefing_slot": packet.get("slot") if packet else None,
            "storage_health": collect_storage_health(self.repo_root),
        }
        response = self._result(
            "overview",
            summary,
            sources={**sources, **self._packet_sources(packet, path, rejected)},
            limitations=[
                "本机工具可读不等于手机或网页 ChatGPT 已直连。",
                "每项资料日期独立于本次读取时间；旧持仓金额不是现值。",
                "system_upgrades 是系统目标台账，不等于跨 AI 协调分支的当前任务状态。",
                "目标摘要省略具体授权范围；granted=true 不能推断所有工作均已获准。",
                "research_count 只是报告目录数量，不表示研究完成进度。",
            ],
            errors=errors,
        )
        response["available"] = bool(data or packet)
        return response

    def portfolio(self, fund_code: str | None = None) -> dict[str, Any]:
        if fund_code is not None and not _is_fund_code(fund_code):
            return self._result("portfolio", errors={"fund_code": "expected six digits"})
        data, errors, sources = self._collect(
            {"workspace": "/api/portfolio/workspace", "portfolio": "/api/portfolio"}
        )
        packet, packet_path, packet_error, rejected = self._packet()
        sources.update(self._packet_sources(packet, packet_path, rejected))
        if packet_error:
            errors["briefing_packet"] = packet_error
        if rejected:
            errors["briefing_packet_fallback"] = rejected
        if (
            packet
            and (packet.get("source_status") or {}).get("user_context", {}).get("ok") is False
        ):
            errors["user_context"] = (
                (packet.get("source_status") or {}).get("user_context") or {}
            ).get("error") or "user context unavailable"
        workspace = data.get("workspace") or {}
        original = data.get("portfolio") or {}
        items = workspace.get("items", [])
        groups = original.get("groups", [])
        if fund_code:
            items = [x for x in items if x.get("code") == fund_code]
            groups = [
                {**g, "holdings": [h for h in g.get("holdings", []) if h.get("code") == fund_code]}
                for g in groups
            ]
            groups = [g for g in groups if g["holdings"]]
        result = {
            "generated_at": workspace.get("generated_at"),
            "as_of": workspace.get("as_of"),
            "coverage": workspace.get("coverage"),
            "items": items,
            "historical_portfolio": {
                "as_of": original.get("as_of"),
                "data_source_cn": original.get("data_source_cn"),
                "observations": original.get("observations"),
                "advices": original.get("advices"),
                "groups": groups,
            },
            "user_stated_context": [
                entry
                for entry in (packet or {}).get("user_stated_context", [])
                if isinstance(entry, dict)
                and (fund_code is None or entry.get("fund_code") == fund_code)
            ],
            "user_context_note": (packet or {}).get("user_context_note"),
            "user_context_packet_generated_at": packet.get("generated_at") if packet else None,
        }
        return self._result(
            "portfolio",
            result if (data or packet) else None,
            sources=sources,
            limitations=[
                "持仓金额来自原快照，不能视为今日账户现值。",
                "季报前十大穿透只说明披露时的部分持仓。",
                "只有已关联原计划和同产品合格行情才可复核条件。",
                "用户原话是待复核的持有理由，不是已确认计划或成交。",
            ],
            errors=errors,
            generated_at=workspace.get("generated_at"),
        )

    def fundamentals(self, market: str = "cn", section: str = "observations") -> dict[str, Any]:
        if market not in {"cn", "us"}:
            return self._result("fundamentals", errors={"market": "expected cn or us"})
        if section == "observations":
            path, scope, applied = f"/api/fundamentals/observations?market={market}", market, True
        elif section in _FUNDAMENTAL_SECTIONS:
            path, scope = _FUNDAMENTAL_SECTIONS[section]
            applied = False
        else:
            return self._result("fundamentals", errors={"section": "unknown fixed section"})
        data, errors, sources = self._collect({section: path})
        payload = data.get(section)
        response = self._result(
            "fundamentals",
            payload,
            sources=sources,
            limitations=[
                "仅作市场背景，不参与技术判定。",
                "本适配器不显式请求刷新；既有 GET 可能按系统缓存期限更新公开背景资料。",
                "逐项使用 observation_date、published_at 和 quality_status；"
                "接口读取时间不等于数据日期。",
                "除 observations 外，market 参数不筛选结果；"
                "以 selection.effective_market_scope 为准。",
            ],
            errors=errors,
            generated_at=(payload or {}).get("generated_at"),
        )
        response["selection"] = {
            "section": section,
            "requested_market": market,
            "market_parameter_applied": applied,
            "effective_market_scope": scope,
        }
        return response

    def news(self, fund_code: str | None = None, limit: int = 20) -> dict[str, Any]:
        if fund_code is not None and not _is_fund_code(fund_code):
            return self._result("news", errors={"fund_code": "expected six digits"})
        limit = max(1, min(int(limit), 50))
        packet, path, error, rejected = self._packet()
        if packet is None:
            return self._result(
                "news",
                sources=self._packet_sources(None, None, rejected),
                errors={"briefing_packet": error, "rejected_packets": rejected},
            )
        rows = list(packet.get("news", []))
        bloggers = list(
            packet.get("blogger_previous_trading_day", packet.get("blogger_yesterday", []))
        )
        if fund_code:
            known_codes = {h.get("code") for h in packet.get("holdings", []) if isinstance(h, dict)}

            def bound(item: dict) -> bool:
                symbols = item.get("symbols") or []
                explicit = item.get("fund_code")
                return fund_code in known_codes and (
                    explicit == fund_code or (isinstance(symbols, list) and fund_code in symbols)
                )

            rows = [x for x in rows if isinstance(x, dict) and bound(x)]
            bloggers = [x for x in bloggers if isinstance(x, dict) and bound(x)]
        result = {
            "items": rows[:limit],
            "matched_count": len(rows),
            "blogger_yesterday": bloggers[:50],
            "blogger_previous_trading_day": bloggers[:50]
            if "blogger_previous_trading_day" in packet
            else [],
            "blogger_window": packet.get("blogger_window")
            or {
                "status": "legacy_packet",
                "date": None,
                "note": "旧包按自然昨天筛选，不能称上个交易日；需生成新简报。",
            },
            "news_coverage": packet.get("news_coverage"),
            "configured_authors": packet.get("configured_authors"),
            "video_content_coverage": packet.get("video_content_coverage"),
            "unqualified_news": packet.get("unqualified_news"),
            "packet_generated_at": packet.get("generated_at"),
        }
        errors = self._packet_errors(packet, "news")
        if rejected:
            errors["briefing_packet_fallback"] = rejected
        response = self._result(
            "news",
            result,
            sources=self._packet_sources(packet, path, rejected),
            limitations=[
                "仅按明确基金代码绑定，不从标题推测持仓关联。",
                "博主全局抓取覆盖情况不能当作某只基金的持仓关联。",
                "需区分发布时间、抓取时间和正文/标题覆盖；来源错误保留在 news_coverage。",
            ],
            errors=errors,
        )
        status = packet.get("source_status") or {}
        response["available"] = (
            status.get("news", {}).get("ok") is True
            and status.get("news_status", {}).get("ok") is not False
            and (packet.get("news_coverage", {}).get("last_run") or {}).get("status") != "failed"
        )
        return response

    def plans(self, fund_code: str | None = None) -> dict[str, Any]:
        if fund_code is not None and not _is_fund_code(fund_code):
            return self._result("plans", errors={"fund_code": "expected six digits"})
        data, errors, sources = self._collect(
            {
                "plans": "/api/plans",
                "summary": "/api/plans/summary",
                "workspace": "/api/portfolio/workspace",
            }
        )
        plans = data.get("plans") if isinstance(data.get("plans"), list) else []
        workspace = data.get("workspace") or {}
        if fund_code:
            linked_ids = {
                x.get("plan", {}).get("plan_id")
                for x in workspace.get("items", [])
                if x.get("code") == fund_code and isinstance(x.get("plan"), dict)
            }
            plans = [x for x in plans if x.get("plan_id") in linked_ids]
        result = {
            "plans": plans,
            "summary": data.get("summary"),
            "workspace_as_of": workspace.get("as_of"),
            "workspace_generated_at": workspace.get("generated_at"),
        }
        return self._result(
            "plans",
            result if data else None,
            sources=sources,
            limitations=[
                "计划存在不代表与当前基金持仓关联。",
                "summary 中今日计数为0可能只是尚未扫描。",
            ],
            errors=errors,
            generated_at=workspace.get("generated_at"),
        )

    def trades(self) -> dict[str, Any]:
        packet, path, error, rejected = self._packet()
        if packet is None:
            return self._result(
                "trades",
                sources=self._packet_sources(None, None, rejected),
                errors={"briefing_packet": error, "rejected_packets": rejected},
            )
        errors = self._packet_errors(packet, "trades")
        if rejected:
            errors["briefing_packet_fallback"] = rejected
        response = self._result(
            "trades",
            {
                "trade_ledger": packet.get("trade_ledger"),
                "packet_generated_at": packet.get("generated_at"),
            },
            sources=self._packet_sources(packet, path, rejected),
            limitations=[
                "成交台账不自动更新旧持仓快照。",
                "系统 priced 不等于基金平台已确认成交份额。",
            ],
            errors=errors,
        )
        response["available"] = (
            packet.get("source_status", {}).get("trades", {}).get("ok") is True
            and (packet.get("trade_ledger") or {}).get("available") is True
        )
        return response

    def opportunities(self) -> dict[str, Any]:
        """Read the saved scan and fill display names from exact identities."""
        from lei_signal.api.config import INDEX_OVERRIDES, OVERSEAS_NAME_CN
        from lei_signal.api.labels import THS_INDUSTRY_NAMES

        data, errors, sources = self._collect(
            {
                "opportunities": "/api/opportunities/today",
                "watchlist": "/api/watchlist",
            }
        )
        names = {**OVERSEAS_NAME_CN, **{s: x.display_name for s, x in INDEX_OVERRIDES.items()}}
        names.update({f"TH{code}.SECTOR": name for code, name in THS_INDUSTRY_NAMES.items()})
        identities = product_identities(self.repo_root)
        names.update({symbol: row["name"] for symbol, row in identities.items()})
        for item in data.get("watchlist", []):
            name = item.get("display_name")
            if name and name != item.get("symbol"):
                names[item["symbol"]] = name
        result = data.get("opportunities")
        if result:
            result = json.loads(json.dumps(result))
            for group in ("actionable", "waiting", "blocked"):
                for item in result.get(group, []):
                    symbol = item.get("symbol", "")
                    if not item.get("display_name") or item["display_name"] == symbol:
                        item["display_name"] = names.get(symbol, "名称待核对")
                        if symbol in identities:
                            item["name_source"] = identities[symbol]
            result["requires_detail_review"] = True
        return self._result(
            "opportunities",
            result,
            errors=errors,
            sources=sources,
            limitations=["保存的候选名单不是买入指令；扫描日期不等于行情日期。"],
        )

    def analysis(self, symbol: str) -> dict[str, Any]:
        """The system's existing detailed product analysis, without forced refresh."""
        path = f"/api/symbols/{symbol}/detail"
        if not _allowed_path(path):
            return self._result("analysis", errors={"symbol": "unsupported product identity"})
        data, errors, sources = self._collect({"analysis": path})
        return self._result(
            "analysis",
            data.get("analysis"),
            errors=errors,
            sources=sources,
            limitations=[
                "基本面/消息只解释背景；同日未完成日线不能当收盘确认。",
                "指数、联接基金与场内ETF是不同产品，不借用价格执行。",
            ],
        )

    def daily_review(self, slot: str = "1440") -> dict[str, Any]:
        from lei_signal.integrations.daily_decisions import build_daily_decisions

        if slot not in {"1135", "1440"}:
            return self._result("daily_review", errors={"slot": "unsupported slot"})
        portfolio, plans, opportunities, news = (
            self.portfolio(),
            self.plans(),
            self.opportunities(),
            self.news(),
        )
        decision = build_daily_decisions(
            portfolio=portfolio, plans=plans, opportunities=opportunities, news=news, slot=slot
        )
        return self._result(
            "daily_review",
            decision,
            errors=decision["source_errors"],
            sources={
                name: result["sources"]
                for name, result in (
                    ("portfolio", portfolio),
                    ("plans", plans),
                    ("opportunities", opportunities),
                    ("news", news),
                )
            },
        )

    def plan_scenario(self, plan_id: str) -> dict[str, Any]:
        """A conditional picture from an existing plan, without making up levels."""
        from lei_signal.integrations.daily_decisions import plan_scenario, render_scenario_svg

        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", plan_id):
            return self._result("plan_scenario", errors={"plan_id": "invalid plan identity"})
        plans, portfolio = self.plans(), self.portfolio()
        plan = next(
            (x for x in (plans.get("data") or {}).get("plans", []) if x.get("plan_id") == plan_id),
            None,
        )
        if plan is None:
            return self._result("plan_scenario", errors={"plan": "saved plan not found"})
        product = next(
            (
                h
                for h in (portfolio.get("data") or {}).get("items", [])
                if h.get("symbol") == plan.get("symbol")
            ),
            {"symbol": plan.get("symbol")},
        )
        identity = product_identities(self.repo_root).get(plan.get("symbol"))
        if identity and not product.get("name"):
            product = {**product, "display_name": identity["name"]}
        scenario = plan_scenario(plan, product=product)
        return self._result(
            "plan_scenario",
            {"scenario": scenario, "svg": render_scenario_svg(scenario)},
            sources={"plans": plans["sources"], "portfolio": portfolio["sources"]},
            errors={**plans["errors"], **portfolio["errors"]},
            limitations=scenario["limitations"],
        )

    def factors(self) -> dict[str, Any]:
        data, errors, sources = self._collect({"factors": "/api/factors/panel"})
        panel = data.get("factors")
        return self._result(
            "factors",
            panel,
            sources=sources,
            limitations=[
                "冻结预计算研究观察，不重算，也不是买卖点。",
                "保留 study_date、data_as_of、provenance 与研究代理说明。",
            ],
            errors=errors,
            generated_at=(panel or {}).get("generated_at"),
        )

    def _research_index(self) -> tuple[list[dict], dict]:
        try:
            response = self._get("/api/experiments")
            if not isinstance(response, dict) or not isinstance(response.get("items"), list):
                raise ValueError("invalid research index")
            return response["items"], {}
        except ValueError as exc:
            return [], {"experiments": str(exc)}

    def _registry(self) -> dict:
        path = (self.repo_root / "docs/experiments/registry.json").resolve()
        if not path.is_relative_to(self.repo_root / "docs") or not path.is_file():
            raise ValueError("registry path leaves the documentation directory")
        raw = path.read_bytes()
        if len(raw) > _MAX_HTTP_BYTES:
            raise ValueError("registry too large")
        entries = json.loads(raw).get("entries", {})
        if not isinstance(entries, dict):
            raise ValueError("invalid research registry")
        return entries

    def research_search(self, query: str = "", limit: int = 10) -> dict[str, Any]:
        limit = max(1, min(int(limit), 20))
        if not isinstance(query, str) or len(query) > 200:
            return self._result("research_search", errors={"query": "query exceeds 200 characters"})
        index, errors = self._research_index()
        try:
            registry = self._registry()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            registry = {}
            errors["registry"] = str(exc)
        words = [x.casefold() for x in query.split() if x]
        matches = []
        for row in index:
            if not isinstance(row, dict):
                continue
            haystack = " ".join(
                str(row.get(k) or "") for k in ("title", "oneLiner", "name")
            ).casefold()
            if words and not all(word in haystack for word in words):
                continue
            item = {
                k: row.get(k)
                for k in (
                    "name",
                    "title",
                    "date",
                    "category",
                    "verdict",
                    "archived",
                    "oneLiner",
                    "pending",
                    "bytes",
                )
            }
            entry = registry.get(row.get("name"), {})
            item["registered"] = isinstance(entry, dict) and bool(entry)
            item["report_sha256_available"] = (
                bool(entry.get("report_sha256")) if isinstance(entry, dict) else False
            )
            matches.append(item)
            if len(matches) >= limit:
                break
        result = self._result(
            "research_search",
            {"items": matches, "query": query, "index_count": len(index)},
            sources={
                "research_index": {
                    "path": "/api/experiments",
                    "retrieved_at": datetime.now(_SHANGHAI).isoformat(),
                    "available": "experiments" not in errors,
                },
                "registry": {
                    "path": "docs/experiments/registry.json",
                    "retrieved_at": datetime.now(_SHANGHAI).isoformat(),
                    "available": "registry" not in errors,
                },
            },
            limitations=[
                "只检索标题和一句话结论；待分类稿不作有效研究。",
                "报告正文必须单独核验原文件字节 SHA-256。",
            ],
            errors=errors,
        )
        result["available"] = "experiments" not in errors
        return result

    def research_report(self, name: str, max_chars: int = 12000) -> dict[str, Any]:
        if not isinstance(name, str) or len(name) > 300:
            return self._result("research_report", errors={"name": "invalid report name"})
        index, errors = self._research_index()
        allowed = {row.get("name"): row for row in index if isinstance(row, dict)}
        if (
            not isinstance(name, str)
            or name not in allowed
            or not name.startswith("docs/")
            or any(part in ("", ".", "..") for part in name.split("/"))
            or "\\" in name
        ):
            errors["name"] = "report is not in the API index"
            return self._result("research_report", errors=errors)
        row = allowed[name]
        if row.get("pending"):
            errors["registry"] = "pending report is not a verified conclusion"
            return self._result("research_report", errors=errors)
        try:
            entry = self._registry().get(name)
            expected = entry.get("report_sha256") if isinstance(entry, dict) else None
            if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise ValueError("registered report SHA-256 is missing")
            root = self.repo_root.resolve()
            path = (root / name).resolve()
            if not path.is_relative_to(root / "docs") or not path.is_file():
                raise ValueError("report path leaves the documentation directory")
            if path.stat().st_size > _MAX_HTTP_BYTES:
                raise ValueError("report too large")
            raw = path.read_bytes()
            if len(raw) > _MAX_HTTP_BYTES:
                raise ValueError("report too large")
            actual = hashlib.sha256(raw).hexdigest()
            if actual != expected:
                raise ValueError("report SHA-256 does not match registry")
            text = raw.decode("utf-8")
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            errors["report"] = str(exc)
            return self._result("research_report", errors=errors)
        max_chars = max(1, min(int(max_chars), 50000))
        conflicts = []
        for key in ("category", "verdict"):
            if row.get(key) != entry.get(key):
                conflicts.append(f"API index {key} differs from registry; registry value used")
        result = {
            "name": name,
            "title": row.get("title"),
            "date": row.get("date"),
            "category": entry.get("category"),
            "verdict": entry.get("verdict"),
            "markdown": text[:max_chars],
            "truncated": len(text) > max_chars,
            "sha256": actual,
            "registry_sha256_verified": True,
        }
        return self._result(
            "research_report",
            result,
            sources={
                "file": {
                    "path": name,
                    "retrieved_at": datetime.now(_SHANGHAI).isoformat(),
                    "available": True,
                    "sha256": actual,
                },
                "registry": {
                    "path": "docs/experiments/registry.json",
                    "retrieved_at": datetime.now(_SHANGHAI).isoformat(),
                    "available": True,
                },
            },
            limitations=["研究结论须结合对象、时期、样本与适用范围；不代表生产采用。", *conflicts],
            errors=errors,
        )

    def latest_brief(self, slot: str | None = None) -> dict[str, Any]:
        packet, path, error, rejected = self._packet(slot)
        if packet is None:
            return self._result(
                "latest_brief",
                sources=self._packet_sources(None, None, rejected),
                errors={"briefing_packet": error, "rejected_packets": rejected},
            )
        result = {
            k: packet.get(k)
            for k in (
                "schema_version",
                "slot",
                "generated_at",
                "mode",
                "holding_record_as_of",
                "coverage",
                "changes",
                "removed_since_previous",
                "plan_review",
                "trade_ledger",
                "news_coverage",
                "video_content_coverage",
                "storage_health",
                "blogger_window",
                "source_status",
                "user_stated_context",
                "user_context_note",
                "limitations",
            )
        }
        result["holdings_count"] = len(packet.get("holdings", []))
        from lei_signal.portfolio.brief_render import render_brief

        result["report_markdown"] = render_brief(packet)
        result["news_count"] = len(packet.get("news", []))
        result["blogger_yesterday_count"] = len(packet.get("blogger_yesterday", []))
        result["blogger_previous_trading_day_count"] = len(
            packet.get("blogger_previous_trading_day", [])
        )
        errors = self._packet_errors(packet, "latest_brief")
        if rejected:
            errors["briefing_packet_fallback"] = rejected
        response = self._result(
            "latest_brief",
            result,
            sources=self._packet_sources(packet, path, rejected),
            limitations=[
                "保存的资料包不是通知送达回执，也不是连续盯盘。",
                "用户原话是待复核背景，不自动变成确认计划或成交。",
            ],
            errors=errors,
        )
        response["available"] = (packet.get("source_status") or {}).get("workspace", {}).get(
            "ok"
        ) is True and (packet.get("trade_ledger") or {}).get("available") is not False
        return response


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read bounded local system context")
    parser.add_argument(
        "--view",
        required=True,
        choices=(
            "overview",
            "storage",
            "portfolio",
            "fundamentals",
            "news",
            "plans",
            "trades",
            "factors",
            "research_search",
            "research_report",
            "latest_brief",
            "research-search",
            "research-report",
            "latest-brief",
            "opportunities",
            "analysis",
            "daily-review",
        ),
    )
    parser.add_argument("--code")
    parser.add_argument("--symbol", default="")
    parser.add_argument("--market", default="cn", choices=("cn", "us"))
    parser.add_argument(
        "--section",
        default="observations",
        choices=("observations", *_FUNDAMENTAL_SECTIONS),
    )
    parser.add_argument("--query", default="")
    parser.add_argument("--name", default="")
    parser.add_argument("--slot", choices=("1135", "1440"))
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)
    context = SystemContext()
    call = {
        "overview": lambda: context.overview(args.query, args.limit),
        "storage": context.storage,
        "portfolio": lambda: context.portfolio(args.code),
        "fundamentals": lambda: context.fundamentals(args.market, args.section),
        "news": lambda: context.news(args.code, args.limit),
        "plans": lambda: context.plans(args.code),
        "trades": context.trades,
        "factors": context.factors,
        "research_search": lambda: context.research_search(args.query, args.limit),
        "research_report": lambda: context.research_report(args.name),
        "latest_brief": lambda: context.latest_brief(args.slot),
        "opportunities": context.opportunities,
        "analysis": lambda: context.analysis(args.symbol),
        "daily_review": lambda: context.daily_review(args.slot or "1440"),
    }[args.view.replace("-", "_")]
    print(json.dumps(call(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
