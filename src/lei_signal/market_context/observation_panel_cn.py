"""Source-bound, additive A-share observation panel continuation.

The archived BaoStock concentration batch contains unadjusted daily responses
through 2026-11-06. This adapter reads those responses without modifying them.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

import numpy as np

from lei_signal.research.observation_candidates import (
    classify,
    downside20,
    iter_stocks,
    stock_observations,
    str20,
)

ROOT = Path(__file__).resolve().parents[3]
RAW = Path(
    "/Volumes/win+mac通用/LeiSignal-新实验结果/microstructure-observations-20261108/concentration-refresh-20261108"
)
OPS = ROOT / "docs/ops/microstructure-observations-20261108/concentration-refresh"
FIELDS = [
    "date",
    "code",
    "open",
    "high",
    "low",
    "close",
    "preclose",
    "volume",
    "amount",
    "adjustflag",
    "tradestatus",
    "pctChg",
    "isST",
]
PREFIXES = ("sh.60", "sh.68", "sz.00", "sz.30")


def _bound_json(path: Path, expected: str) -> dict:
    blob = path.read_bytes()
    if hashlib.sha256(blob).hexdigest() != expected:
        raise ValueError(f"SHA mismatch: {path}")
    return json.loads(blob)


def _recent() -> tuple[list[str], dict[str, dict[str, tuple]], dict]:
    summary = json.loads((OPS / "collection-summary.json").read_text())
    if summary["state"] != "collection_complete" or summary["recentSuccess"] != 5228:
        raise ValueError("recent acquisition is not accepted as complete")
    calendar_ref = summary["calendar"]
    calendar = _bound_json(Path(calendar_ref["sourcePath"]), calendar_ref["sha256"])
    if calendar.get("errorCode") != "0" or calendar.get("fields") != [
        "calendar_date",
        "is_trading_day",
    ]:
        raise ValueError("trading calendar source schema changed")
    dates = [
        row[0]
        for row in calendar["data"]
        if row[1] == "1" and "2026-10-08" <= row[0] <= "2026-11-06"
    ]
    if dates != calendar_ref["recentDates"] or len(dates) != 22:
        raise ValueError("recent calendar does not match accepted 22 sessions")
    log = RAW / "collection-requests.jsonl"
    if (
        hashlib.sha256(log.read_bytes()).hexdigest()
        != json.loads((OPS / "collection-ledger.json").read_text())["requestLogSha256"]
    ):
        raise ValueError("recent request log SHA mismatch")
    refs = [json.loads(line) for line in log.open()]
    refs = [r for r in refs if r.get("event") == "query" and r.get("kind") == "recent"]
    if len(refs) != 5228 or len({r["code"] for r in refs}) != 5228:
        raise ValueError("recent source cardinality mismatch")
    by_code: dict[str, dict[str, tuple]] = {}
    for ref in refs:
        if ref["status"] != "0" or ref["start"] != dates[0] or ref["end"] != dates[-1]:
            raise ValueError(f"recent query status/range mismatch: {ref['code']}")
        path = Path(ref["path"])
        if not path.resolve().is_relative_to(RAW / "recent"):
            raise ValueError("recent source outside accepted archive")
        body = _bound_json(path, ref["sha256"])
        if (
            body.get("errorCode") != "0"
            or body.get("fields") != FIELDS
            or len(body.get("data", [])) != ref["rows"]
        ):
            raise ValueError(f"recent source schema mismatch: {path}")
        rows = {}
        for row in body["data"]:
            if (
                len(row) != len(FIELDS)
                or row[1] != ref["code"]
                or row[0] not in dates
                or row[0] in rows
            ):
                raise ValueError(f"recent row identity/date mismatch: {path}")
            rows[row[0]] = classify(row, ref["code"])
        by_code[ref["code"]] = rows
    return (
        dates,
        by_code,
        {
            "sourceFilesVerified": len(refs),
            "sourceEnd": dates[-1],
            "sourceLedgerSha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        },
    )


def _join_older(
    recent_dates: list[str], recent: dict[str, dict[str, tuple]], provenance: dict
) -> tuple[list[str], dict[str, dict[str, tuple]]]:
    """Use the frozen qualified price index for warm-up and overlap assurance."""
    from lei_signal.research.observation_candidates import HERE, verify_inputs

    spec = json.loads((HERE / "frozen-spec.json").read_text())
    index, all_old_dates, _ = verify_inputs(spec)
    old_dates = [d for d in all_old_dates if "2026-09-01" <= d <= spec["sourceThrough"]]
    if old_dates[-1] != "2026-10-23" or [d for d in old_dates if d >= recent_dates[0]] != [
        d for d in recent_dates if d <= old_dates[-1]
    ]:
        raise ValueError("frozen and recent calendars disagree in overlap")
    old_set = set(old_dates)
    overlap_count = 0
    mismatch = []
    for item, previous in iter_stocks(index):
        code = item["code"]
        observed = stock_observations(item, previous, old_set, True, defaultdict(int))
        if code not in recent:
            recent[code] = observed
            continue
        for day in recent_dates:
            if day not in old_set:
                continue
            left, right = observed.get(day), recent[code].get(day)
            if left is None or right is None:
                if left != right:
                    mismatch.append((code, day, "missing"))
            elif left[0] != right[0] or (
                left[0] == "trade"
                and (
                    not math.isclose(left[1], right[1], abs_tol=1e-12)
                    or not math.isclose(left[2], right[2], abs_tol=0.01)
                )
            ):
                mismatch.append((code, day, "value"))
            else:
                overlap_count += 1
        for day, value in observed.items():
            recent[code].setdefault(day, value)
    if mismatch:
        raise ValueError(
            f"old/recent quote overlap differs: {mismatch[:8]} ({len(mismatch)} total)"
        )
    provenance["overlapRowsVerified"] = overlap_count
    provenance["frozenSourceThrough"] = old_dates[-1]
    return old_dates + [d for d in recent_dates if d > old_dates[-1]], recent


def _candidates(dates: list[str], by_code: dict[str, dict[str, tuple]]) -> dict:
    """Compute only windows wholly contained in the independently acquired batch."""
    market = {}
    for day in dates:
        returns = [r[1] for rows in by_code.values() if (r := rows.get(day)) and r[0] == "trade"]
        market[day] = sum(returns) / len(returns) if returns else None
    down: dict[str, list[float]] = defaultdict(list)
    salience: dict[str, list[float]] = defaultdict(list)
    for rows in by_code.values():
        for i in range(19, len(dates)):
            window = dates[i - 19 : i + 1]
            obs = [rows.get(day) for day in window]
            value = downside20(obs)
            if value is not None and math.isfinite(value):
                down[dates[i]].append(value)
            if all(r is not None and r[0] == "trade" for r in obs) and all(
                market[d] is not None for d in window
            ):
                value = str20([r[1] for r in obs], [market[d] for d in window]) * 100
                if math.isfinite(value):
                    salience[dates[i]].append(value)
    base = {
        "frequency": "daily",
        "sourceName": "BaoStock归档沪深A股原始日线",
        "sourceUrl": "https://github.com/zxygithub/baostock/blob/master/docs/pythonAPI.md",
        "note": "供应商历史股票名录固定回看；原始涨跌幅与成交额；非预测或可交易信号。",
    }
    output = {}
    for key, unit, values in [
        ("downside-price-impact", "百分点/亿元", down),
        ("salience-str", "百分点", salience),
    ]:
        output[key] = {
            **base,
            "unit": unit,
            "points": [
                {"date": d, "value": median(values[d]) if values[d] else None} for d in dates[19:]
            ],
        }
    return output


def _csi_history() -> tuple[dict, dict]:
    """Extend the existing 300-member adjusted-close computation backwards."""
    from lei_signal.market_context import microstructure_equity as equity

    start, end = equity.AMOUNT_START, equity.AMOUNT_END
    try:
        equity.AMOUNT_START, equity.AMOUNT_END = "2025-08-01", "2026-10-23"
        _, prices = equity.load_amounts({"inputs": []})
    finally:
        equity.AMOUNT_START, equity.AMOUNT_END = start, end
    if len(prices) != 300:
        raise ValueError("CSI fixed-member source does not contain 300 stocks")
    card = equity.member_cards("cn", prices, {"files": len(prices), "sha256": "frozen-v8-source"})[
        1
    ]
    points = card["points"]
    baseline = json.loads(
        (ROOT / "web/public/research/microstructure-observations-20261108/equity.json").read_text()
    )
    original = next(
        c for c in baseline["cards"] if c["id"] == "cn-current-members-pairwise-correlation"
    )
    observed = {p["date"]: p["value"] for p in points}
    mismatch = [
        (p["date"], p["value"], observed.get(p["date"]))
        for p in original["points"]
        if p["date"] not in observed
        or (p["value"] is not None and p["value"] != observed[p["date"]])
    ]
    if mismatch:
        raise ValueError(f"extended CSI series changed accepted overlap: {mismatch[:4]}")
    result = {
        "frequency": "daily",
        "unit": "相关系数",
        "sourceName": card["sourceName"],
        "sourceUrl": card["sourceUrl"],
        "note": (
            "2026-10-15取得的固定300股当前名单回看；BaoStock原始日线×后复权因子。"
            "价格原件止2026-10-23，非历史逐时成分。"
        ),
        "points": points,
    }
    audit = {
        "points": len(points),
        "valid": sum(p["value"] is not None for p in points),
        "firstDate": points[0]["date"],
        "lastDate": points[-1]["date"],
        "overlapPointsVerified": len(original["points"]),
    }
    return result, audit


def _focus_history() -> tuple[dict, dict]:
    """Reuse the already accepted fixed-300 continuation through November 2."""
    base = json.loads((ROOT / "web/public/research/focus-momentum/observation.v1.json").read_text())
    follow = json.loads(
        (ROOT / "web/public/research/focus-momentum/continuation.v1.json").read_text()
    )
    if (
        base["definitionId"] != follow["definitionId"]
        or not follow["overlapVerified"]
        or base["asOf"] != "2025-12-31"
        or follow["historicalAsOf"] != base["asOf"]
        or follow["scope"]["sampleSize"] != 300
        or follow["asOf"] != "2026-11-02"
    ):
        raise ValueError("fixed focus continuation identity/date qualification changed")
    for relative, expected in base["source"]["sha256"].items():
        path = ROOT / relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"frozen focus source SHA mismatch: {path}")
    rows = base["series"] + follow["series"]
    dates = [r["date"] for r in rows]
    if dates != sorted(set(dates)) or dates[-1] != follow["asOf"]:
        raise ValueError("fixed focus continuation dates overlap or disagree")
    points = [{"date": row["date"], "value": row["focus"] * 100} for row in rows]
    return {
        "frequency": "daily",
        "unit": "%",
        "sourceName": "BaoStock归档固定300股历史样本与已验收续接",
        "sourceUrl": "https://github.com/zxygithub/baostock/blob/master/docs/pythonAPI.md",
        "note": ("2014-12-31历史名单固定300股，后来退出者仍在样本；已验收续接止2026-11-02。"),
        "points": points,
    }, {"points": len(points), "firstDate": dates[0], "lastDate": dates[-1]}


def _csi_bridge() -> tuple[dict, dict]:
    """Carry the fixed roster through November 6 with BaoStock ex-date preclose."""
    from lei_signal.market_context import microstructure_equity as equity

    start, end = equity.AMOUNT_START, equity.AMOUNT_END
    try:
        equity.AMOUNT_START, equity.AMOUNT_END = "2025-08-01", "2026-10-23"
        _, prices = equity.load_amounts({"inputs": []})
    finally:
        equity.AMOUNT_START, equity.AMOUNT_END = start, end
    if len(prices) != 300:
        raise ValueError("CSI fixed roster changed")
    old = equity.member_cards("cn", prices, {"files": 300, "sha256": "frozen-v8-source"})[1]
    old_dates = [p["date"] for p in old["points"]]
    recent_dates, _, _ = _recent()
    dates = old_dates + [d for d in recent_dates if d > old_dates[-1]]
    refs = {
        r["code"]: r
        for line in (RAW / "collection-requests.jsonl").open()
        if (r := json.loads(line)).get("event") == "query" and r.get("kind") == "recent"
    }
    overlap_error = []
    returns: dict[str, dict[str, float]] = {}
    overlap_returns: dict[str, dict[str, float]] = {}
    for code, series in prices.items():
        old_ret = {
            day: series[day] / series[old_dates[i - 1]] - 1
            for i, day in enumerate(old_dates)
            if i and day in series and old_dates[i - 1] in series
        }
        compared_ret = dict(old_ret)
        ref = refs.get(code)
        if ref is None:
            raise ValueError(f"CSI member absent from recent source: {code}")
        body = _bound_json(Path(ref["path"]), ref["sha256"])
        if body.get("errorCode") != "0" or body.get("fields") != FIELDS:
            raise ValueError(f"CSI recent quote schema changed: {code}")
        for row in body["data"]:
            day = row[0]
            if row[1] != code or row[9] != "3" or day not in recent_dates:
                raise ValueError(f"CSI recent quote identity changed: {code}/{day}")
            if row[10] != "1":
                continue
            close, preclose = float(row[5]), float(row[6])
            if not (
                math.isfinite(close) and math.isfinite(preclose) and close > 0 and preclose > 0
            ):
                continue
            value = close / preclose - 1
            if not row[11] or abs(value - float(row[11]) / 100) > 1e-5:
                raise ValueError(f"CSI supplier return identity failed: {code}/{day}")
            if day in old_ret:
                overlap_error.append(abs(old_ret[day] - value))
                compared_ret[day] = value
            else:
                old_ret[day] = value
                compared_ret[day] = value
        returns[code] = old_ret
        overlap_returns[code] = compared_ret
    if len(overlap_error) < 3000 or max(overlap_error) > 1e-5:
        raise ValueError("CSI adjusted/preclose overlap precision gate failed")
    appended = []
    correlation_overlap = {}
    last_complete = 0
    for i, day in enumerate(dates):
        if i < 20 or day < "2026-10-20":
            continue
        window = dates[i - 19 : i + 1]
        panel = overlap_returns if day <= old_dates[-1] else returns
        complete = [
            np.asarray([rows[d] for d in window], dtype=float)
            for rows in panel.values()
            if all(d in rows for d in window)
        ]
        value = None
        if len(complete) >= 285:
            matrix = np.asarray(complete)
            if not np.any(np.std(matrix, axis=1) == 0):
                corr = np.corrcoef(matrix)
                upper = corr[np.triu_indices(len(matrix), 1)]
                if np.isfinite(upper).all():
                    value = float(np.mean(upper))
        if day <= old_dates[-1]:
            correlation_overlap[day] = value
        else:
            appended.append({"date": day, "value": value})
        last_complete = len(complete)
    accepted = {p["date"]: p["value"] for p in old["points"]}
    differences = [
        abs(correlation_overlap[d] - accepted[d])
        for d in correlation_overlap
        if correlation_overlap[d] is not None and accepted[d] is not None
    ]
    if len(differences) < 4 or max(differences) > 1e-5:
        raise ValueError("CSI correlation overlap precision gate failed")
    result = {
        "frequency": "daily",
        "unit": "相关系数",
        "sourceName": "BaoStock归档当前300股原始日线与除权参考价",
        "sourceUrl": "https://www.baostock.com/helpdocs/pdf/BaoStock%E5%A4%8D%E6%9D%83%E5%9B%A0%E5%AD%90%E7%AE%80%E4%BB%8B.pdf",
        "note": (
            "2026-10-15取得的当前300股固定回看；"
            "新增日以同源close/preclose链接后复权日收益，非逐时历史成分。"
        ),
        "points": old["points"] + appended,
    }
    audit = {
        "sourceRowsCompared": len(overlap_error),
        "maxReturnDifference": max(overlap_error),
        "overlapCorrelationDays": len(differences),
        "maxCorrelationDifference": max(differences),
        "appendedDays": len(appended),
        "lastDate": appended[-1]["date"],
        "lastValidMembers": last_complete,
    }
    return result, audit


def _focus_bridge() -> tuple[dict, dict]:
    """Run the accepted fixed-300 adapter with a conservative held factor."""
    from lei_signal.research import focus_recent as f
    from lei_signal.research.fip import SOURCE_FIELDS
    from lei_signal.research.high52_revalidation import ADJUSTMENT_FIELDS, adapt_back_adjusted

    base = ROOT / "docs/ops/focus-live-and-erp-thresholds-20261102/reopen-home-20261102"
    result_path = base / "data/data-result.json"
    calendar_path = base / "gap-calendar.json"
    accepted = json.loads(
        (ROOT / "web/public/research/focus-momentum/continuation.v1.json").read_text()
    )
    inputs = json.loads((f.OLD_DIR / "inputs.json").read_text())
    manifest = json.loads(
        f.checked(Path(inputs["source_manifest"]["path"]), inputs["source_manifest"]["sha256"])
    )
    assets = manifest["asset_sources"]
    if (
        len(assets) != 300
        or accepted["source"]["manifestSha256"] != inputs["source_manifest"]["sha256"]
    ):
        raise ValueError("focus fixed-300 manifest changed")
    gap, gap_meta = f.gap_sources(result_path, set(assets), "2026-11-02")
    if gap_meta["resultSha256"] != accepted["source"]["gapResultSha256"]:
        raise ValueError("accepted focus gap source changed")
    plan = json.loads(f.CALENDAR_PLAN.read_text())
    ref = plan["baseline"]["calendar"]
    raw_calendar = f.checked(Path(ref["path"]), ref["sha256"]).decode()
    calendar = [
        r["trade_date"]
        for r in csv.DictReader(raw_calendar.splitlines())
        if f.START <= r["trade_date"] <= "2026-10-23"
    ]
    extra = json.loads(calendar_path.read_text())
    for source_ref in extra["sources"]:
        f.checked(Path(source_ref["path"]), source_ref["sha256"])
    if (
        extra["sessions"]
        != ["2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30", "2026-11-02"]
        or hashlib.sha256(calendar_path.read_bytes()).hexdigest()
        != accepted["source"]["gapCalendarSha256"]
    ):
        raise ValueError("accepted focus supplement calendar changed")
    calendar += extra["sessions"]
    recent_dates, _, _ = _recent()
    calendar += [d for d in recent_dates if d > "2026-11-02"]
    if calendar != sorted(set(calendar)) or calendar[-1] != "2026-11-06":
        raise ValueError("focus continuation calendar not exact")
    wanted = set(assets)
    index = {r["code"]: r for line in f.INDEX.open() if (r := json.loads(line))["code"] in wanted}
    old = {r["code"]: r for line in f.OLD_UNION.open() if (r := json.loads(line))["code"] in wanted}
    if set(index) != wanted:
        raise ValueError("focus v8 fixed cohort incomplete")
    refs = {
        r["code"]: r
        for line in (RAW / "collection-requests.jsonl").open()
        if (r := json.loads(line)).get("event") == "query" and r.get("kind") == "recent"
    }
    audit = Counter()
    verified = []
    by_day: dict[str, dict[str, dict]] = defaultdict(dict)
    new_breaks = {}
    recent_overlap = 0
    for code, pair in sorted(assets.items()):
        v8 = index[code]
        daily_refs = [
            pair["daily"],
            *old.get(code, {}).get("source_refs", []),
            *v8["reused_raw_sources"],
            *v8["new_price_sources"],
            {**gap[code]["daily"], "valid_slice_start": "2026-10-26"},
        ]
        factor_refs = [
            pair["adjustments"],
            *v8["reused_factor_sources"],
            *v8["new_factor_sources"],
            {**gap[code]["factor"], "valid_slice_start": "2026-10-24"},
        ]
        daily = f.merge_rows(
            code, daily_refs, SOURCE_FIELDS, f.START, "2026-11-02", audit, verified
        )
        factors = f.merge_rows(
            code, factor_refs, ADJUSTMENT_FIELDS, "1900-01-01", "2026-11-02", audit, verified
        )
        recent_ref = refs.get(code)
        if recent_ref:
            body = _bound_json(Path(recent_ref["path"]), recent_ref["sha256"])
            if body.get("errorCode") != "0" or body.get("fields") != list(SOURCE_FIELDS):
                raise ValueError(f"focus new raw source schema changed: {code}")
            old_rows = {row[0]: row for row in daily if row[0] >= "2026-10-08"}
            for row in body["data"]:
                if row[1] != code or row[9] != "3" or row[0] not in recent_dates:
                    raise ValueError(f"focus new raw source identity changed: {code}")
                if row[0] <= "2026-11-02":
                    if row[0] in old_rows and row != old_rows[row[0]]:
                        raise ValueError(f"focus old/new raw overlap changed: {code}/{row[0]}")
                    recent_overlap += row[0] in old_rows
                else:
                    daily.append(row)
        daily.sort(key=lambda r: r[0])
        adapted = adapt_back_adjusted(
            {"error_code": "0", "fields": list(SOURCE_FIELDS), "data": daily},
            {"error_code": "0", "fields": list(ADJUSTMENT_FIELDS), "data": factors},
            code,
            calendar,
            factor_field="foreAdjustFactor",
        )
        breaks = [d for d in adapted["break_dates"] if d > "2026-11-02"]
        if breaks:
            new_breaks[code] = breaks
        partial = f.stock_windows(adapted, calendar, code, audit)
        for day, values in partial.items():
            if day >= "2026-10-20":
                by_day[day][code] = values
    computed = [f.observation(day, by_day.get(day, {})) for day in calendar if day >= "2026-10-20"]
    known = {r["date"]: r for r in accepted["series"]}
    for row in computed:
        day = row["date"]
        if day > "2026-11-02":
            continue
        original = known[day]
        if (
            row["qualified_count"] != original["qualifiedCount"]
            or row["focus_count"] != original["focusCount"]
        ):
            raise ValueError(f"focus overlap eligibility mismatch: {day}")
        if abs(row["focus"] - original["focus"]) > 1e-12:
            raise ValueError(f"focus overlap aggregate mismatch: {day}")
    appended = [r for r in computed if r["date"] > "2026-11-02"]
    if len(appended) != 4 or any(not r["signal_valid"] for r in appended):
        raise ValueError("focus new dates do not meet original 100-stock gate")
    history, _ = _focus_history()
    history["points"] += [{"date": r["date"], "value": r["focus"] * 100} for r in appended]
    history["note"] = (
        "固定300股历史样本；11/03—11/06使用原focus_recent复权适配与资格门禁。"
        "新日沿用11/02已核有效因子，仅原价/昨收与当日参考价通过一致性检查的窗口入样；"
        "新增公司行动无因子时相关窗口留空。"
    )
    return history, {
        "oldAggregateDaysMatched": len(computed) - len(appended),
        "recentRawOverlapRows": recent_overlap,
        "newDays": [
            {
                "date": r["date"],
                "qualifiedCount": r["qualified_count"],
                "focusCount": r["focus_count"],
                "focusPct": r["focus"] * 100,
            }
            for r in appended
        ],
        "newBreaks": new_breaks,
    }


def build() -> tuple[dict, dict]:
    dates, by_code, provenance = _recent()
    dates, by_code = _join_older(dates, by_code, provenance)
    cards = _candidates(dates, by_code)
    for card in cards.values():
        card["incremental"] = True
        card["points"] = [
            p for p in card["points"] if p["date"] > provenance["frozenSourceThrough"]
        ]
    csi, csi_audit = _csi_history()
    cards["cn-current-members-pairwise-correlation"] = csi
    focus, focus_audit = _focus_history()
    cards["focus-momentum"] = focus
    audit = {
        **provenance,
        "calculationStart": dates[19],
        "calculationEnd": dates[-1],
        "observations": {key: len(card["points"]) for key, card in cards.items()},
        "counts": {
            key: sum(value is not None for value in (p["value"] for p in card["points"]))
            for key, card in cards.items()
        },
        "csi": csi_audit,
        "focus": focus_audit,
        "limitations": [
            "Reuses frozen BaoStock price index and same-source recent overlap.",
            "Current qualified adjustment events are unavailable after their frozen end dates.",
        ],
    }
    return cards, audit


def build_bridge() -> tuple[dict, dict]:
    cards, audit = build()
    csi, bridge_audit = _csi_bridge()
    cards["cn-current-members-pairwise-correlation"] = csi
    audit["csiBridge"] = bridge_audit
    audit["limitations"] = [
        "CSI new returns use the BaoStock close/preclose chain and match the old overlap.",
        "Focus remains at 2026-11-02 until its full adapter qualification succeeds.",
    ]
    return cards, audit


def build_focus() -> tuple[dict, dict]:
    cards, audit = build_bridge()
    focus, focus_audit = _focus_bridge()
    cards["focus-momentum"] = focus
    audit["focusBridge"] = focus_audit
    audit["simplifiedFocusBridgeRejected"] = (
        "Raw pctChg chaining alone failed 10/20-11/02 accepted eligibility counts "
        "and focus aggregates; the published continuation uses the full factor adapter."
    )
    audit["limitations"] = [
        "CSI new returns use the BaoStock close/preclose chain and match the old overlap.",
        "Focus new values use the original factor adapter and exclude unqualified windows.",
    ]
    return cards, audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bridge", action="store_true")
    parser.add_argument("--focus", action="store_true")
    args = parser.parse_args()
    cards, audit = build_focus() if args.focus else build_bridge() if args.bridge else build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise ValueError("staged output already exists")
    args.output.write_text(json.dumps(cards, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
    print(json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    main()
