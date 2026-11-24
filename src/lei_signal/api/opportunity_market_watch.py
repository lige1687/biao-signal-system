"""Read-only, source-dated market observations for the opportunity page.

The observations are narrative context. They never change a technical signal.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

from lei_signal.api.config import cache_root

_BREADTH_HISTORY = "a_share_ma_breadth_history.json"
_BREADTH_SNAPSHOT = "a_share_ma_breadth.json"
_MAX_CACHE_BYTES = 2_000_000
_READING_METRICS = (
    ("cn", "cpi", "macro"),
    ("cn", "cn_10y", "macro"),
    ("us", "vix", "sentiment"),
    ("us", "us_10y", "macro"),
    ("us", "hy_oas", "sentiment"),
)


def _date(value: object, *, as_of: date) -> date | None:
    try:
        result = date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None
    return result if result and result <= as_of else None


def _percent(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) and 0 <= result <= 100 else None


def _json_file(path: Path) -> object | None:
    try:
        if path.stat().st_size > _MAX_CACHE_BYTES:
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None



def _qualified_breadth(cache_dir: Path, closed_through: date) -> tuple[dict | None, list[str]]:
    """Validate the new same-day receipt independently of the old mixed-day cache."""
    raw = _json_file(cache_dir / "a_share_ma_breadth_qualification.json")
    if not isinstance(raw, dict):
        return None, ["同日宽度核对记录不可读取。"]
    if (
        raw.get("price_adjustment") != "qfqday"
        or raw.get("price_provenance") not in {"qfq_cache_v1", "qfq_source_receipt_v1"}
        or raw.get("price_source_ref")
        != "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get"
        or not re.fullmatch(r"[a-f0-9]{64}", str(raw.get("price_cache_sha256") or ""))
    ):
        return None, ["宽度样本的前复权来源尚未核实；旧缓存不作为已核同日样本。"]
    day = _date(raw.get("target_day"), as_of=closed_through)
    total, available = raw.get("universe_total"), raw.get("same_day_available")
    if (day is None or raw.get("calculation_status") != "verified_same_day_sample"
            or type(total) is not int or type(available) is not int
            or not 0 < available <= total):
        return None, ["尚未取得有效的同日宽度样本；旧混日读数已停止用于近期判断。"]
    for window in (50, 200):
        eligible, above = raw.get(f"eligible{window}"), raw.get(f"above{window}")
        pct = _percent(raw.get(f"ma{window}_pct"))
        if (type(eligible) is not int or type(above) is not int
                or not 0 <= above <= eligible <= available or eligible == 0
                or pct is None or not math.isclose(pct, above / eligible * 100, abs_tol=0.0001)):
            return None, ["同日宽度的分子、分母与比例不一致，暂停展示。"]
    return {
        "date": day.isoformat(), "b50": raw["ma50_pct"], "b200": raw["ma200_pct"],
        "repeated": False, "window_start": day.isoformat(), "window_count": 1,
        "source": raw.get("source") or "腾讯同日前复权日线与交易所成员表",
        "quality": raw,
    }, []


def _breadth(
    cache_dir: Path, as_of: date, completed_through: date | None
) -> tuple[dict | None, list[str]]:
    closed_through = min(as_of, completed_through or as_of - timedelta(days=1))
    if (cache_dir / "a_share_ma_breadth_qualification.json").exists():
        return _qualified_breadth(cache_dir, closed_through)
    history = _json_file(cache_dir / _BREADTH_HISTORY)
    snapshot = _json_file(cache_dir / _BREADTH_SNAPSHOT)
    if not isinstance(history, list) or not isinstance(snapshot, dict):
        return None, ["全A宽度的本机历史或快照缺失，未形成近期观察。"]
    # A date-only request cannot prove today's close is complete. The route may
    # explicitly pass today's date after the Shanghai close.
    closed_through = min(as_of, completed_through or as_of - timedelta(days=1))
    snapshot_day = _date(snapshot.get("date"), as_of=closed_through)
    valid: dict[date, dict] = {}
    for row in history:
        if not isinstance(row, dict):
            continue
        day = _date(row.get("date"), as_of=closed_through)
        b50, b200 = _percent(row.get("ma50_pct")), _percent(row.get("ma200_pct"))
        if day and day.weekday() < 5 and b50 is not None:
            valid[day] = {"date": day.isoformat(), "b50": b50, "b200": b200}
    if not valid or snapshot_day != max(valid):
        return None, ["全A宽度快照与历史末日不一致，未形成近期观察。"]
    latest = valid[snapshot_day]
    if _percent(snapshot.get("ma50_pct")) is None or not math.isclose(
        float(snapshot["ma50_pct"]), latest["b50"], abs_tol=0.0001
    ):
        return None, ["全A宽度快照与历史读数不一致，未形成近期观察。"]
    snapshot_b200 = _percent(snapshot.get("ma200_pct"))
    if (snapshot_b200 is None) != (latest["b200"] is None) or (
        snapshot_b200 is not None
        and not math.isclose(snapshot_b200, latest["b200"], abs_tol=0.0001)
    ):
        return None, ["全A宽度快照与历史读数不一致，未形成近期观察。"]
    dates = sorted(valid)
    previous = valid[dates[-2]] if len(dates) >= 2 else None
    latest["repeated"] = bool(
        previous and previous["b50"] == latest["b50"] and previous["b200"] == latest["b200"]
    )
    recent = dates[-5:]
    latest["window_start"] = recent[0].isoformat()
    latest["window_count"] = len(recent)
    if len(dates) >= 6 and (snapshot_day - dates[-6]).days <= 14:
        latest["comparison"] = valid[dates[-6]]
    latest["source"] = str(snapshot.get("source") or "本机全A均线宽度缓存")
    return latest, []


def _macro_rows(db_path: str, as_of: date, window_start: date) -> tuple[dict, list[str]]:
    path = Path(db_path)
    if not path.is_file():
        return {}, ["本机宏观观察库缺失。"]
    observations: dict[tuple[str, str], dict] = {}
    try:
        with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)) as conn:
            for market in ("cn", "us"):
                result = conn.execute(
                    "SELECT rows_json FROM opportunity_macro_observations "
                    "WHERE market=? AND status='ready' AND checked_on<=? AND checked_on>=? "
                    "ORDER BY checked_on DESC LIMIT 1",
                    (market, as_of.isoformat(), window_start.isoformat()),
                ).fetchone()
                if not result:
                    continue
                rows = json.loads(result[0])
                if not isinstance(rows, list):
                    continue
                for row in rows[:100]:
                    if not isinstance(row, dict):
                        continue
                    metric = row.get("metric_id")
                    day = _date(row.get("observation_date"), as_of=as_of)
                    published = row.get("published_at")
                    text = row.get("text")
                    url = row.get("source_ref")
                    if (
                        not isinstance(metric, str)
                        or day is None
                        or (
                            published is not None
                            and _date(str(published)[:10], as_of=as_of) is None
                        )
                        or row.get("market") not in (None, market)
                        or row.get("public") is not True
                        or row.get("provenance") != "local_macro_observation"
                        or row.get("quality_status") == "missing"
                        or not isinstance(row.get("source"), str)
                        or not row["source"].strip()
                        or not isinstance(url, str)
                        or urlparse(url).scheme != "https"
                        or not urlparse(url).netloc
                        or not isinstance(text, str)
                        or not text.strip()
                        or re.search(r"\b(?:nan|inf|infinity)\b", text, re.IGNORECASE)
                    ):
                        continue
                    value_text = text.split("为", 1)[-1] if "为" in text else ""
                    number = re.match(r"\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)", value_text)
                    if not number or not math.isfinite(float(number.group())):
                        continue
                    if "value" in row:
                        try:
                            if not math.isfinite(float(row["value"])):
                                continue
                        except (TypeError, ValueError, OverflowError):
                            continue
                    key = (market, metric)
                    old = observations.get(key)
                    if old is None or day.isoformat() > old["observation_date"]:
                        observations[key] = row
    except (sqlite3.Error, ValueError, OSError):
        return {}, ["本机宏观观察库不可读取。"]
    return observations, []


def _reading(market: str, metric: str, kind: str, row: dict, as_of: date) -> dict:
    day = row["observation_date"]
    limitations = [x for x in row.get("limitations", []) if isinstance(x, str)][:6]
    if not row.get("published_at"):
        limitations.append("发布时间未核，不能把这项读数当作近期发布的事件。")
    if day != as_of.isoformat():
        limitations.append(f"观测日为{day}，不是{as_of.isoformat()}的实时读数。")
    if row.get("quality_status") not in (None, "verified"):
        limitations.append(f"来源质量标记：{row['quality_status']}。")
    title = "VIX" if metric == "vix" else row.get("text", "").split("为")[0]
    title = title.removeprefix(f"截至{day}，")
    return {
        "id": f"{market}:{metric}",
        "title": title,
        "market": market.upper(),
        "kind": kind,
        "status": "observed",
        "impact": "neutral",
        "fact": row.get("text", ""),
        "meaning": "这是有日期的市场读数；单次水平不能说明走势或交易方向。",
        "watch": "核对后续同口径读数及正式发布时间。",
        "observation_date": day,
        "source": row.get("source", "本机宏观观察"),
        "source_ref": row.get("source_ref", ""),
        "limitations": limitations,
        "published_at": row.get("published_at"),
        "checked_at": row.get("checked_at"),
    }


def build_market_watch(
    *,
    as_of: date,
    db_path: str,
    cache_dir: Path | None = None,
    completed_through: date | None = None,
) -> dict:
    """Build a bounded JSON view from existing local snapshots, with no refresh."""
    news_start = as_of - timedelta(days=4)
    result: dict = {
        "as_of": as_of.isoformat(),
        "news_window": {"start": news_start.isoformat(), "end": as_of.isoformat(), "days": 5},
        "market_window_label": "暂无可核对的市场交易日序列",
        "items": [],
        "readings": [],
        "limitations": [],
    }
    breadth, breadth_gaps = _breadth(
        Path(cache_dir) if cache_dir else Path(cache_root()), as_of, completed_through
    )
    result["limitations"].extend(breadth_gaps)
    if breadth:
        b50, b200 = breadth["b50"], breadth["b200"]
        breadth_day = breadth["date"]
        quality = breadth.get("quality")
        result["market_window_label"] = (
            f"最近{breadth['window_count']}个已保存全A观测日期"
            f"（{breadth['window_start']}—{breadth_day}）"
        )
        # Import at use time: symbols owns these existing display thresholds and
        # imports many API modules itself. This does not invoke its alert prose.
        from lei_signal.api.routes.symbols import _COLD_THRESHOLD, _HOT_THRESHOLD

        breadth_limitations = [
            "缓存未保存逐股行情日期和同日覆盖率，成分可能混用不同日期，需复核。",
            "20%/80%是现有宽度展示观察值，不是策略买卖阈值。",
        ]
        if quality:
            breadth_limitations = list(quality.get("limitations") or []) + [
                f"50日线按{quality['eligible50']}只有足够历史的股票计算；200日线按{quality['eligible200']}只计算。",
                "缺日或历史不足的股票未计作低于均线；不同分母的比例不可相加。",
                "20%/80%沿用既有观察值；尚未核历史同日序列，不展示近期变化幅度。",
            ]
            result["market_window_label"] = f"{breadth_day}同日样本（此前混日序列暂不比较）"
        if breadth["repeated"]:
            breadth_limitations.append("与前一已保存观测日读数完全相同，不能据此认定出现新的触发。")
        if b50 <= _COLD_THRESHOLD:
            breadth_meaning = "站上50日线的股票比例较低；仅为宽度观察。"
        elif b50 >= _HOT_THRESHOLD:
            breadth_meaning = "站上50日线的股票比例较高；仅为宽度观察。"
        else:
            breadth_meaning = "站上50日线的股票比例处于现有宽度观察区间内。"
        breadth_fact = f"截至{breadth_day}，站上50日线占比{b50:.2f}%"
        if b200 is not None:
            breadth_fact += f"，站上200日线占比{b200:.2f}%"
        breadth_fact += "。"
        if quality:
            breadth_fact += (
                f"同日行情已核{quality['same_day_available']}/{quality['universe_total']}只。"
            )
        comparison = breadth.get("comparison")
        if comparison:
            breadth_fact += (
                f"较{comparison['date']}，50日线占比变化{b50 - comparison['b50']:+.2f}个百分点。"
            )
        common = {
            "id": "cn_all_a:breadth_b50_b200",
            "title": "全A均线宽度",
            "market": "CN_ALL_A",
            "kind": "breadth",
            "status": "observed" if quality else "needs_check",
            "quality_label": "同日样本已核" if quality else "覆盖待核",
            "impact": "neutral" if quality else "unknown",
            "fact": breadth_fact,
            "meaning": breadth_meaning,
            "watch": (
                "留意下个交易日参与上涨的股票是否增多；同日覆盖缺口与成员日期见资料边界。"
                if quality else "先核逐股同日覆盖，再观察下一有效交易日的宽度变化。"
            ),
            "observation_date": breadth_day,
            "source": breadth["source"],
            "source_ref": (
                None if quality else "/api/market-context/breadth-history?market_id=CN_ALL_A"
            ),
            "limitations": breadth_limitations,
            "threshold": {
                "value": _COLD_THRESHOLD,
                "upper_value": _HOT_THRESHOLD,
                "basis": (
                    "src/lei_signal/api/routes/symbols.py::_breadth_alerts "
                    "现有全A宽度展示观察阈值（B50及B200）；非策略规则。"
                ),
            },
        }
        breadth_age = (as_of - date.fromisoformat(breadth_day)).days
        focus_title = None
        if b50 <= _COLD_THRESHOLD and b200 is not None and b200 <= _COLD_THRESHOLD:
            focus_title = "全A宽度双线低于现有观察值"
        elif b50 >= _HOT_THRESHOLD and b200 is not None and b200 >= _HOT_THRESHOLD:
            focus_title = "全A宽度双线高于现有观察值"
        elif b50 <= _COLD_THRESHOLD:
            focus_title = "全A 50日线宽度低于现有观察值"
        elif b50 >= _HOT_THRESHOLD:
            focus_title = "全A 50日线宽度高于现有观察值"
        if breadth_age <= 7 and focus_title:
            title = focus_title.replace("全A", "已核A股样本") if quality else focus_title
            result["items"].append({**common, "title": title})
        else:
            result["readings"].append(common)
        if breadth_age > 7:
            result["limitations"].append(
                f"全A宽度最近观测日{breadth_day}距查询日超过7个自然日，未列为焦点。"
            )
    rows, macro_gaps = _macro_rows(db_path, as_of, as_of - timedelta(days=7))
    result["limitations"].extend(macro_gaps)
    for market, metric, kind in _READING_METRICS:
        row = rows.get((market, metric))
        if row:
            result["readings"].append(_reading(market, metric, kind, row, as_of))
    if not rows:
        result["limitations"].append("近5日未找到已保存的宏观观察快照；未查询外部来源。")
    return result
