"""Offline, descriptive observations from SHA-bound BaoStock responses."""

from __future__ import annotations

import bisect
import csv
import gzip
import hashlib
import json
import math
import plistlib
import subprocess
from array import array
from collections import Counter
from pathlib import Path
from statistics import median

FIELDS = ["date", "code", "open", "high", "low", "close", "preclose", "volume", "amount", "adjustflag", "tradestatus", "pctChg", "isST"]
PREFIXES = ("sh.60", "sh.68", "sz.00", "sz.30")
MOUNT = Path("/Volumes/win+mac通用")
BASE = MOUNT / "LeiSignal-新实验结果/public-universe-deep-completion-20261026/public-universe-deep-completion-20261026-20261026T225421-69a3af262800/result/cn-all-equity"
META = BASE / "all-equity-read-index-v8-meta.json"
OLD = MOUNT / "LeiSignal-新实验结果/twenty-year-universe-data-20261025/twenty-year-universe-data-20261025-20261025T154847-f27d39c4e083/result/cn/stock-source-union-v4/actual-date-unions.jsonl"
REPO = Path(__file__).resolve().parents[3]
HERE = REPO / "docs/experiments/raw/douyin-observation-models-overlap-2026-10-31/observation-integration-20261101/compute"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows(path: Path):
    with path.open() as stream:
        for line in stream:
            yield json.loads(line)


def number(raw):
    try:
        value = float(raw)
    except (ValueError, TypeError):
        return None
    return value if math.isfinite(value) else None


def classify(row, code):
    """Return trade return/amount, suspension, or invalid source row."""
    if len(row) != len(FIELDS) or row[1] != code or row[9] != "3":
        return None
    volume, amount = number(row[7]), number(row[8])
    if row[10] == "0":
        if (row[7] == "" or volume == 0) and (row[8] == "" or amount == 0):
            return ("suspended", None, None)
        return None
    if row[10] != "1" or volume is None or amount is None or volume <= 0 or amount <= 0:
        return None
    close, preclose, change = number(row[5]), number(row[6]), number(row[11])
    if close is None or preclose is None or change is None or close <= 0 or preclose <= 0:
        return None
    return ("trade", change / 100, amount)


def read_source(ref, code, verify=True):
    path = Path(ref.get("source_path") or ref["path"])
    if not path.is_file() or not path.resolve().is_relative_to(MOUNT):
        raise RuntimeError(f"source outside verified archive: {path}")
    blob = path.read_bytes()
    expected = ref.get("compressed_sha256") or ref["sha256"]
    if verify and hashlib.sha256(blob).hexdigest() != expected:
        raise RuntimeError(f"source SHA mismatch: {path}")
    payload = gzip.decompress(blob) if ref.get("compressed_sha256") else blob
    if verify and ref.get("payload_sha256") and hashlib.sha256(payload).hexdigest() != ref["payload_sha256"]:
        raise RuntimeError(f"payload SHA mismatch: {path}")
    source = json.loads(payload)
    expected_rows = ref.get("rows", ref.get("response_rows"))
    if source.get("error_code") != "0" or source.get("fields") != FIELDS or expected_rows is None or len(source.get("data", [])) != expected_rows:
        raise RuntimeError(f"source response mismatch: {path}")
    return source["data"]


def stock_observations(item, previous, date_set, verify, audit):
    """Merge archived source pointers; conflicts invalidate the affected date."""
    refs = (previous["source_refs"] if previous else []) + item["reused_raw_sources"] + item["new_price_sources"]
    observations = {}
    invalid = set()
    for ref in refs:
        for row in read_source(ref, item["code"], verify):
            day = row[0] if row else None
            if day not in date_set or not ref.get("valid_slice_start", day) <= day <= ref.get("valid_slice_end", day):
                continue
            if day < item["supplier_ipo"] or (item["supplier_out"] and day > item["supplier_out"]):
                audit["outside_lifecycle"] += 1
                invalid.add(day)
                continue
            parsed = classify(row, item["code"])
            if parsed is None:
                audit["invalid_rows"] += 1
                invalid.add(day)
                continue
            if day in observations and observations[day] != parsed:
                audit["conflicts"] += 1
                invalid.add(day)
            else:
                observations[day] = parsed
        audit["source_files"] += 1
    for day in invalid:
        observations.pop(day, None)
    return observations


def mean_ranks_desc(values):
    ranked = sorted(range(len(values)), key=lambda i: (-values[i], i))
    ranks = [0.0] * len(values)
    pos = 0
    while pos < len(values):
        end = pos + 1
        while end < len(values) and values[ranked[end]] == values[ranked[pos]]:
            end += 1
        rank = (pos + 1 + end) / 2
        for at in ranked[pos:end]:
            ranks[at] = rank
        pos = end
    return ranks


def str20(returns, market_returns, delta=0.7):
    if len(returns) != 20 or len(market_returns) != 20:
        raise ValueError("STR requires 20 full sessions")
    salience = [abs(r - m) / (abs(r) + abs(m) + 0.1) for r, m in zip(returns, market_returns)]
    ranks = mean_ranks_desc(salience)
    raw_weights = [delta ** (rank - 1) for rank in ranks]
    total = sum(raw_weights)
    return sum(weight * ret for weight, ret in zip(raw_weights, returns)) / total - sum(returns) / 20


def downside20(observations):
    if len(observations) != 20 or any(row is None for row in observations):
        return None
    ratios = [abs(row[1] * 100) / row[2] * 1e8 for row in observations if row[0] == "trade" and row[1] < 0]
    return sum(ratios) / len(ratios) if ratios else None


def verify_inputs(spec):
    info = subprocess.run(["/usr/sbin/diskutil", "info", "-plist", str(MOUNT)], capture_output=True, check=True).stdout
    if plistlib.loads(info).get("VolumeUUID") != spec["sourceVolumeUUID"]:
        raise RuntimeError("external volume UUID mismatch")
    meta = json.loads(META.read_text())
    index = Path(meta["index_path"])
    binding = [(META, "metaSha256"), (index, "indexSha256"), (OLD, "oldUnionSha256")]
    calendar_ref = json.loads((REPO / "docs/experiments/raw/public-universe-deep-completion-2026-10-26/cn-all-equity-plan/coverage-plan-v2.json").read_text())["baseline"]["calendar"]
    binding.append((Path(calendar_ref["path"]), "calendarSha256"))
    for path, key in binding:
        if sha256(path) != spec[key]:
            raise RuntimeError(f"SHA mismatch: {key}")
    if meta["index_sha256"] != spec["indexSha256"] or meta["old_union"]["sha256"] != spec["oldUnionSha256"]:
        raise RuntimeError("metadata pointers changed")
    with Path(calendar_ref["path"]).open() as stream:
        dates = [row["trade_date"] for row in csv.DictReader(stream) if spec["firstDate"] <= row["trade_date"] <= spec["sourceThrough"]]
    if not dates or dates[-1] != spec["sourceThrough"] or len(set(dates)) != len(dates):
        raise RuntimeError("calendar incomplete or duplicated")
    source_hash = hashlib.sha256(json.dumps({key: spec[key] for _, key in binding}, sort_keys=True).encode()).hexdigest()
    return index, dates, source_hash


def iter_stocks(index):
    old_iter = rows(OLD)
    previous = next(old_iter, None)
    for item in rows(index):
        code = item["code"]
        while previous is not None and previous["code"] < code:
            previous = next(old_iter, None)
        old = previous if previous is not None and previous["code"] == code else None
        if code.startswith(PREFIXES):
            yield item, old


def calculate(index, dates, source_hash, spec):
    date_set = set(dates)
    date_index = {day: i for i, day in enumerate(dates)}
    size = len(dates)
    market_sum, market_n = [0.0] * size, [0] * size
    universe_diff = [0] * (size + 1)
    first_audit = Counter()
    for item, old in iter_stocks(index):
        left, right = bisect.bisect_left(dates, item["supplier_ipo"]), bisect.bisect_right(dates, item["supplier_out"] or dates[-1])
        if left < right:
            universe_diff[left] += 1
            universe_diff[right] -= 1
        observations = stock_observations(item, old, date_set, True, first_audit)
        for day, row in observations.items():
            if row[0] == "trade":
                at = date_index[day]
                market_sum[at] += row[1]
                market_n[at] += 1
        first_audit["stocks"] += 1
    market = [market_sum[i] / market_n[i] if market_n[i] else None for i in range(size)]
    universe_n = []
    running = 0
    for difference in universe_diff[:-1]:
        running += difference
        universe_n.append(running)
    downside_values = [array("d") for _ in dates]
    str_values = [array("d") for _ in dates]
    audit = Counter()
    checks = []
    check_dates = {"2017-12-29", "2019-12-31", "2021-12-31", "2023-12-29", "2025-12-31"}
    used_check_dates = set()
    for item, old in iter_stocks(index):
        observed = stock_observations(item, old, date_set, False, audit)
        stock = [observed.get(day) for day in dates]
        for i in range(19, size):
            if dates[i] < item["supplier_ipo"] or (item["supplier_out"] and dates[i] > item["supplier_out"]):
                continue
            window = stock[i - 19:i + 1]
            down = downside20(window)
            if down is not None:
                downside_values[i].append(down)
            if not all(row is not None and row[0] == "trade" for row in window) or any(value is None for value in market[i - 19:i + 1]):
                continue
            returns = [row[1] for row in window]
            markets = market[i - 19:i + 1]
            value = str20(returns, markets) * 100
            str_values[i].append(value)
            if dates[i] in check_dates and dates[i] not in used_check_dates:
                checks.append({"code": item["code"], "date": dates[i], "dates": dates[i-19:i+1], "r": returns,
                               "amount": [row[2] for row in window], "rbar": markets, "priceImpact": down, "strPp": value})
                used_check_dates.add(dates[i])
    if first_audit["source_files"] != audit["source_files"] or first_audit["conflicts"] != audit["conflicts"] or first_audit["invalid_rows"] != audit["invalid_rows"]:
        raise RuntimeError("two source scans diverged")
    def points(values):
        return [{"date": day, "value": median(values[i]) if values[i] else None, "n": len(values[i]), "universeN": universe_n[i]}
                for i, day in enumerate(dates)]
    limits = ["Supplier lifecycle is retrospective and not a point-in-time official all-A-share security master.",
              "Source rows end 2026-10-23; current value is unavailable and no later value is carried forward.",
              "Missing or invalid source rows break stock windows; suspended days are known nonquotes.",
              "Raw price changes may include corporate-action effects; observations do not establish impact, attention, predictive value or trading efficacy."]
    result = {"schemaVersion": 1, "historicalOnly": True, "current": None, "asOf": dates[-1], "sourceThrough": spec["sourceThrough"],
              "sourceSha256": source_hash, "sourceName": "BaoStock archived daily raw K responses", "sourceUrl": spec["sourceUrl"],
              "scopeLabel": spec["universe"], "limitations": limits,
              "series": {
                  "downside-price-impact": {"definitionId": "baostock-downside-price-impact-20-v1", "label": "下跌日价额比 · 20日观察版",
                      "unit": "百分点/亿元", "meaning": "下跌日原始涨跌幅绝对值相对成交额的强度", "reading": "数值较高表示相同成交额对应较大价格变动；不代表成交导致跌幅。",
                      "definition": spec["downsidePriceImpact"], "limitations": ["停牌不贡献下跌样本；缺日及零下跌窗口保留空值。"], "points": points(downside_values)},
                  "salience-str": {"definitionId": "salience-str-20-independent-v1", "label": "STR · 20日观察版",
                      "unit": "百分点", "meaning": "凸显权重下的20日平均涨跌幅相对普通均值的差", "reading": "正值表示更凸显的日期涨跌幅权重后更高；不代表市场顶底。",
                      "definition": spec["salienceStr"], "limitations": ["独立20日观察口径；不同于论文月内及月末15日设计，也非原视频精确复刻。"], "points": points(str_values)}}}
    report = {"sourceFilesVerified": first_audit["source_files"], "supplierCodes": first_audit["stocks"], "invalidRows": first_audit["invalid_rows"],
              "conflicts": first_audit["conflicts"], "outsideLifecycleRows": first_audit["outside_lifecycle"],
              "calendarDays": size, "sourceThrough": dates[-1], "sourceSha256": source_hash,
              "downsideValidDays": sum(bool(v) for v in downside_values), "strValidDays": sum(bool(v) for v in str_values),
              "latestDownsideN": len(downside_values[-1]), "latestStrN": len(str_values[-1])}
    return result, report, checks


def main():
    spec = json.loads((HERE / "frozen-spec.json").read_text())
    output, audit, checks = [HERE / name for name in ("daily-aggregates.json", "audit.json", "sample-windows.json")]
    if any(path.exists() for path in (output, audit, checks)):
        raise RuntimeError("descriptive run already exists")
    index, dates, source_hash = verify_inputs(spec)
    result, report, examples = calculate(index, dates, source_hash, spec)
    blobs = [json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode() + b"\n" for obj in (result, report, examples)]
    if sum(map(len, blobs)) > 2_000_000:
        raise RuntimeError("output exceeds frozen 2 MB small-artifact limit")
    for path, blob in zip((output, audit, checks), blobs):
        path.write_bytes(blob)
    print(json.dumps({"outputBytes": sum(map(len, blobs)), **report, "sampleWindows": len(examples)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
