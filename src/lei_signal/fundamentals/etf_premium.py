"""A股场内跨境ETF实时溢价率观测（腾讯行情 + 东方财富官方净值，直连免代理）。"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import requests

from lei_signal.api.config import cache_root

_TIMEOUT = 10
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://fundf10.eastmoney.com/",
}

# 覆盖常用跨境核心场内ETF，按跟踪指数分组便于同组比价找最便宜的一只
CROSS_BORDER_WATCHLIST: tuple[dict[str, str], ...] = (
    {"code": "513100", "market": "sh", "name": "纳指ETF国泰", "index_group": "纳指100"},
    {"code": "159941", "market": "sz", "name": "纳指ETF广发", "index_group": "纳指100"},
    {"code": "513300", "market": "sh", "name": "纳斯达克ETF华夏", "index_group": "纳指100"},
    {"code": "513500", "market": "sh", "name": "标普500ETF博时", "index_group": "标普500"},
    {"code": "159655", "market": "sz", "name": "标普ETF华夏", "index_group": "标普500"},
    {"code": "513180", "market": "sh", "name": "恒生科技ETF华夏", "index_group": "恒生科技"},
)

# 明确参考阈值：1%以内公道，1%-3%偏贵，超过3%属于明显高溢价风险
FAIR_MAX_PCT = 1.0
WARN_MAX_PCT = 3.0


def classify_premium(premium_pct: float | None) -> tuple[str, str]:
    """返回 (风险等级英文键, 大白话状态标签)。"""
    if premium_pct is None:
        return "unknown", "净值或行情缺失"
    if premium_pct <= FAIR_MAX_PCT:
        return "fair", "价格公道（正常区间）"
    if premium_pct <= WARN_MAX_PCT:
        return "caution", "小幅偏贵（建议对比同类）"
    return "high_risk", "明显偏贵（高溢价风险，慎追）"


def _direct_session() -> requests.Session:
    sess = requests.Session()
    sess.trust_env = False
    return sess


def fetch_tencent_quotes(
    specs: tuple[dict[str, str], ...] = CROSS_BORDER_WATCHLIST,
) -> dict[str, dict[str, Any]]:
    """批量拉取腾讯场内现价，返回 {code: {price, prev_close, quote_date, name}}。"""
    q_syms = ",".join(f"{s['market']}{s['code']}" for s in specs)
    url = f"https://qt.gtimg.cn/q={q_syms}"
    with _direct_session() as sess:
        resp = sess.get(url, headers={"User-Agent": _HEADERS["User-Agent"]}, timeout=_TIMEOUT)
        resp.raise_for_status()
        text = resp.text
    out: dict[str, dict[str, Any]] = {}
    for line in text.strip().splitlines():
        parts = line.split("~")
        if len(parts) < 35:
            continue
        code = parts[2].strip()
        try:
            price = float(parts[3])
            prev_close = float(parts[4]) if parts[4] else None
        except ValueError:
            continue
        if price <= 0:
            continue
        raw_t = parts[30].strip()
        q_date = (
            f"{raw_t[:4]}-{raw_t[4:6]}-{raw_t[6:8]}"
            if len(raw_t) >= 8 and raw_t[:8].isdigit()
            else None
        )
        out[code] = {
            "name": parts[1].strip() or code,
            "price": round(price, 4),
            "prev_close": round(prev_close, 4) if prev_close is not None else None,
            "quote_date": q_date,
        }
    return out


def fetch_eastmoney_nav(code: str) -> dict[str, Any]:
    """拉取东方财富最新官方单位净值与申赎状态。"""
    url = f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize=3"
    with _direct_session() as sess:
        resp = sess.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    rows = (payload.get("Data") or {}).get("LSJZList") or []
    for row in rows:
        nav_str = str(row.get("DWJZ") or "").strip()
        nav_date = str(row.get("FSRQ") or "").strip()
        if not nav_str or not nav_date:
            continue
        try:
            nav_val = float(nav_str)
        except ValueError:
            continue
        if nav_val > 0:
            return {
                "nav": round(nav_val, 4),
                "nav_date": nav_date,
                "subscribe_status": str(row.get("SGZT") or "").strip() or "未知",
            }
    raise ValueError(f"{code} 未返回有效官方净值")


def evaluate_premium_row(
    spec: dict[str, str],
    quote: dict[str, Any] | None,
    nav_info: dict[str, Any] | None,
    error: str | None = None,
) -> dict[str, Any]:
    price = quote.get("price") if quote else None
    quote_date = quote.get("quote_date") if quote else None
    nav = nav_info.get("nav") if nav_info else None
    nav_date = nav_info.get("nav_date") if nav_info else None
    sub_status = nav_info.get("subscribe_status") if nav_info else "未知"

    premium_pct: float | None = None
    if price is not None and nav is not None and nav > 0:
        premium_pct = round((price / nav - 1.0) * 100.0, 2)

    level, label_cn = classify_premium(premium_pct)
    nav_lag = bool(quote_date and nav_date and nav_date < quote_date)
    note_parts: list[str] = []
    if nav_lag:
        note_parts.append(f"官方净值截至{nav_date}，滞后于场内价日期，估算溢价含隔夜波动")
    if "暂停" in sub_status:
        note_parts.append("当前暂停申购，场内高溢价不易快速回落")
    if error:
        note_parts.append(f"采集异常：{error}")

    return {
        "code": spec["code"],
        "name": spec["name"],
        "index_group": spec["index_group"],
        "market_price": price,
        "quote_date": quote_date,
        "official_nav": nav,
        "nav_date": nav_date,
        "premium_pct": premium_pct,
        "subscribe_status": sub_status,
        "risk_level": level,
        "verdict_cn": label_cn,
        "nav_lag": nav_lag,
        "is_lowest_in_group": False,
        "note_cn": "；".join(note_parts) if note_parts else "净值与场内价同日对齐，可直接对比。",
    }


def _cache_path(cache: Path | None = None) -> Path:
    return (cache or Path(cache_root())) / "cross_border_etf_premium.json"


def build_cross_border_premium(
    *,
    specs: tuple[dict[str, str], ...] = CROSS_BORDER_WATCHLIST,
    quote_loader: Callable[[tuple[dict[str, str], ...]], dict[str, dict[str, Any]]] | None = None,
    nav_loader: Callable[[str], dict[str, Any]] | None = None,
    cache: Path | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """拉取并计算所有常用跨境场内ETF溢价率，标出同指数最便宜选项。"""
    errors: list[str] = []
    q_loader = quote_loader or fetch_tencent_quotes
    n_loader = nav_loader or fetch_eastmoney_nav

    quotes: dict[str, dict[str, Any]] = {}
    try:
        quotes = q_loader(specs)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"场内行情读取失败：{exc}")

    items: list[dict[str, Any]] = []
    for spec in specs:
        code = spec["code"]
        nav_info = None
        err = None
        try:
            nav_info = n_loader(code)
        except Exception as exc:  # noqa: BLE001
            err = str(exc)
            errors.append(f"{spec['name']}({code})净值失败：{exc}")
        items.append(evaluate_premium_row(spec, quotes.get(code), nav_info, error=err))

    # 标记每个跟踪指数组里溢价最低的一只
    by_group: dict[str, list[dict[str, Any]]] = {}
    for row in items:
        if row["premium_pct"] is not None:
            by_group.setdefault(row["index_group"], []).append(row)
    for group_rows in by_group.values():
        best = min(group_rows, key=lambda r: float(r["premium_pct"]))
        best["is_lowest_in_group"] = True

    result = {
        "generated_at": datetime.now(UTC).isoformat(),
        "thresholds": {
            "fair_max_pct": FAIR_MAX_PCT,
            "warn_max_pct": WARN_MAX_PCT,
            "rule_cn": "溢价不超过1%属于价格公道；1%至3%偏贵需对比同类；超过3%属于明显高溢价风险，慎追。",
        },
        "items": items,
        "errors": errors,
    }
    if persist and any(row["premium_pct"] is not None for row in items):
        try:
            target = _cache_path(cache)
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, target)
        except OSError:
            pass
    return result


def read_cached_cross_border_premium(cache: Path | None = None) -> dict[str, Any] | None:
    path = _cache_path(cache)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
