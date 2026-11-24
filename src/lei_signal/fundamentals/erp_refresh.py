"""Live successor to the frozen, qualified CSI300 ERP reference.

The reference file is immutable. Daily supplier observations are retained in a
separate runtime file; the displayed band input keeps one observation per week
and the latest published observation. No monthly PE source is spliced into it.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path

import requests

from lei_signal.api.config import cache_root

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = ROOT / "web/public/research/erp-bands/cn-reference.json"
SOURCE_URL = "https://baifenwei.com/indicator/equity-bond-spread/hs300/"


def _atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    if path.exists():
        original = path.read_bytes()
        path.with_name(f"{path.name}.before-{stamp}.bak").write_bytes(original)
    temporary = path.with_name(f"{path.name}.pending-{stamp}")
    temporary.write_bytes(data)
    temporary.replace(path)
    if path.read_bytes() != data:
        raise OSError("ERP runtime readback mismatch")


def parse_daily_page(text: str, cutoff: str) -> list[dict]:
    # This is a named index URL and its public chart data, not an anonymous PE API.
    if "沪深300" not in text or "PE-TTM" not in text:
        raise ValueError("CSI300 valuation identity missing")
    match = re.search(r"var\s+seriesByRange\s*=\s*", text)
    if not match:
        raise ValueError("published ERP chart data missing")
    ranges, _ = json.JSONDecoder().raw_decode(text[match.end() :])
    rows = ranges.get("1")
    if not isinstance(rows, list) or len(rows) < 30:
        raise ValueError("daily ERP history too short")
    result = []
    previous = ""
    for row in rows:
        day = row.get("date", "")
        if date.fromisoformat(day).isoformat() != day or day <= previous:
            raise ValueError("invalid or duplicated ERP date")
        previous = day
        spread, price, ratio = row.get("spread"), row.get("cp"), row.get("ratio")
        if (
            any(
                not isinstance(v, (int, float)) or not math.isfinite(v)
                for v in (spread, price, ratio)
            )
            or price <= 0
            or ratio <= 0
        ):
            raise ValueError("invalid ERP observation")
        if day <= cutoff:
            result.append({"date": day, "value": spread, "close": price})
    if not result:
        raise ValueError("no published completed ERP observation")
    return result


def build_live_reference(base: dict, daily: list[dict], cutoff: str) -> dict:
    original = {row["date"]: row for row in base["points"]}
    overlap = [row for row in daily if row["date"] in original]
    if len(overlap) < 12:
        raise ValueError("insufficient same-source reference anchors")
    # The two public charts were previously qualified as the same mcw PE_TTM
    # definition. Recheck the overlap each run, including index prices/dates.
    if any(
        abs(row["value"] - original[row["date"]]["value"]) > 0.02
        or abs(row["close"] - original[row["date"]]["close"]) > 0.05
        for row in overlap
    ):
        raise ValueError("supplier definition or date alignment changed")
    successors = [row for row in daily if base["asOf"] < row["date"] <= cutoff]
    weekly = {}
    for row in successors:
        day = date.fromisoformat(row["date"])
        iso = day.isocalendar()
        weekly[(iso.year, iso.week)] = row
    result = deepcopy(base)
    result["points"] += list(weekly.values())
    result.update(
        historicalOnly=False,
        asOf=result["points"][-1]["date"],
        sourceName="沪深300市值加权PE_TTM股债利差 · 股叉叉历史／百分位日更",
        sourceUrl=SOURCE_URL,
        note="历史按周观察，最新读数随已公开交易日更新；周内仅保留该周最新观测用于轨道，避免混入不同市盈率口径。",
        updateMode="automatic",
        overlapAnchors=len(overlap),
    )
    return result


def refresh_cn_erp(output: Path, *, cutoff: str, cache: Path | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    response = requests.get(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()
    import gzip

    with gzip.open(output / "published-page.html.gz", "wt") as handle:
        handle.write(response.text)
    base = json.loads(REFERENCE.read_text())
    daily = parse_daily_page(response.text, cutoff)
    result = build_live_reference(base, daily, cutoff)
    result["sourceSha256"] = hashlib.sha256(response.content).hexdigest()
    result["updatedAt"] = datetime.now(UTC).isoformat()
    # Retain every observed daily successor separately from weekly band input.
    result["dailySuccessors"] = [p for p in daily if p["date"] > base["asOf"]]
    encoded = json.dumps(result, ensure_ascii=False, indent=2).encode()
    (output / "candidate.json").write_bytes(encoded)
    target = (cache or Path(cache_root())) / "erp_cn_reference_live.json"
    existing = json.loads(target.read_text()) if target.exists() else None
    if existing and existing["asOf"] > result["asOf"]:
        raise ValueError("supplier response older than installed reference")
    _atomic(target, encoded)
    return {
        "as_of": result["asOf"],
        "target": str(target),
        "overlap_anchors": result["overlapAnchors"],
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def read_cn_erp(cache: Path | None = None) -> dict:
    path = (cache or Path(cache_root())) / "erp_cn_reference_live.json"
    return json.loads((path if path.exists() else REFERENCE).read_text())


def read_us_erp(cache: Path | None = None) -> dict[str, float] | None:
    path = (cache or Path(cache_root())) / "erp_us_history_live.json"
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    return {row["date"]: row["value"] for row in raw["points"]}


def refresh_us_erp(output: Path, *, cutoff: str, cache: Path | None = None) -> dict:
    from lei_signal.fundamentals import sources

    output.mkdir(parents=True, exist_ok=False)
    treasury = sources.fetch_treasury_history(7665)
    values = sources.fetch_us_erp_history(18250, treasury)
    values = {d: v for d, v in values.items() if d <= cutoff}
    if not values:
        raise ValueError("US ERP has no completed observations")
    result = {
        "as_of": max(values),
        "updated_at": datetime.now(UTC).isoformat(),
        "points": [{"date": d, "value": values[d]} for d in sorted(values)],
    }
    encoded = json.dumps(result, ensure_ascii=False).encode()
    (output / "candidate.json").write_bytes(encoded)
    target = (cache or Path(cache_root())) / "erp_us_history_live.json"
    old = read_us_erp(cache)
    if old and max(old) > result["as_of"]:
        raise ValueError("US ERP response moved backwards")
    _atomic(target, encoded)
    return {
        "as_of": result["as_of"],
        "target": str(target),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }
