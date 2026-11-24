"""Frozen assumptions and validation shared by the observation service."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def instant(value: str | datetime) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("aware ISO timestamp required")
    return parsed


def money(value: Any, *, positive: bool = False) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("finite decimal required") from exc
    if not number.is_finite() or (positive and number <= 0):
        raise ValueError(
            "finite positive decimal required" if positive else "finite decimal required"
        )
    return number


def frozen_spec(config: dict, now: str | datetime) -> dict:
    """Freeze execution assumptions; source/config identity is part of the digest."""
    at = instant(now).isoformat()
    assets = config.get("assets") or ([config["group"]] if config.get("group") else [])
    if len(assets) != 1 or not assets[0].get("symbol"):
        raise ValueError("first version requires one named asset")
    accounts = config.get("accounts") or []
    kinds = {a.get("kind") for a in accounts}
    if not {"buy_hold", "cash"}.issubset(kinds):
        raise ValueError("buy_hold and cash accounts required")
    if len({a.get("id") for a in accounts}) != len(accounts):
        raise ValueError("duplicate account id")
    initial = money(config.get("initial_cash", 100000), positive=True)
    default_rule = {
        "universe": [assets[0]["symbol"]],
        "entry": "one queued order at freeze; next eligible observed quote only",
        "ranking": "single asset; no ranking",
        "sizing": "whole 100 share lots within initial cash including fees",
        "holding": "hold acquired shares; no rebalance",
        "exit": "none for passive baseline",
        "reentry": "none",
        "cash_conflict": "separate reference accounts; no common cash",
    }
    fee_bps = money(config.get("fee_bps", 10))
    slip_bps = money(config.get("slippage_bps", 5))
    if not (0 <= fee_bps < 10000 and 0 <= slip_bps < 10000):
        raise ValueError("fee and slippage bps must be between 0 and 10000")
    execution = {
        "lot": int(config.get("lot_size", 100)),
        "commission_rate": str(fee_bps / 10000),
        "slippage_rate": str(slip_bps / 10000),
        "commission_minimum": "0",
        "cash_interest_rate": "0",
        "order_tif": "GTC",
    }
    if execution["lot"] <= 0:
        raise ValueError("positive lot required")
    frozen_accounts = []
    for account in accounts:
        a = dict(account)
        if a["kind"] == "cash":
            cash_rule = {
                "universe": "现金参照",
                "entry": "初始虚拟现金入账，不购买产品",
                "ranking": "不排序",
                "sizing": "全部虚拟金额保持现金",
                "holding": "现金无息持有",
                "exit": "不卖出",
                "reentry": "不适用",
                "cash_conflict": "独立参照账户，不与其他账户共用资金",
            }
            a["rules"] = {**cash_rule, **(a.get("rules") or {})}
        elif a["kind"] == "buy_hold":
            a["rules"] = {**default_rule, **(a.get("rules") or {})}
        else:
            a["rules"] = a.get("rules") or {}
            frozen_accounts.append(a)
            continue
        if set(a["rules"]) != set(default_rule):
            raise ValueError("rules must contain exactly eight fields")
        frozen_accounts.append(a)
    return {
        "schema_version": 1,
        "frozen_at": at,
        "started_at": at,
        "initial_cash": str(initial),
        "assets": assets,
        "accounts": frozen_accounts,
        "execution": execution,
        "max_quote_age_seconds": int(config.get("max_quote_age_seconds", 120)),
        "config_hash": digest(config),
        "code_hashes": config.get("code_hashes") or config.get("source_fingerprints", {}),
        "mode": "simulated_forward_observation_no_broker",
    }
