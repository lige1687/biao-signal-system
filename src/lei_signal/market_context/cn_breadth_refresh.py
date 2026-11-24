"""Prepare an append-only, qualified A-share breadth candidate.

Only ``output`` is written. A failed qualification leaves an audit receipt but
never creates a candidate suitable for installation into the live cache.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from lei_signal.api.config import cache_root

ROOT = Path(__file__).resolve().parents[3]
CLI = (
    ROOT
    / ".codex/breadth-reading-coordination-20261101"
    / "cn-provider-probe-v4/npm-cache/_npx/f124025a92f4edba"
    / "node_modules/westock-data-skillhub/scripts/index.js"
)
WINDOWS = (20, 50, 200)
BATCH_SIZE = 20
MAX_RAW = 3 * 1024**2
MAX_OUTPUT = 100 * 1024**2
MIN_FREE = 5 * 1024**3
SHANGHAI = ZoneInfo("Asia/Shanghai")
SYMBOL = re.compile(r"(?:sh|sz|bj)\d{6}\Z")
BATCH = re.compile(
    r"\[Batch\]\s*状态:\s*(\S+)\s*\|\s*总数:\s*(\d+)\s*\|\s*成功:\s*(\d+)\s*\|\s*失败:\s*(\d+)"
)
FIELDS = ("symbol", "date", "open", "last", "high", "low", "volume", "amount", "exchange")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _guard(output: Path) -> None:
    v = os.statvfs(output)
    if v.f_bavail * v.f_frsize < MIN_FREE:
        raise RuntimeError("output volume has less than 5 GiB free")
    if sum(p.stat().st_size for p in output.rglob("*") if p.is_file()) >= MAX_OUTPUT:
        raise RuntimeError("candidate output reached 100 MiB cap")


def closed_cutoff(now: datetime | None = None) -> str:
    local = (now or datetime.now(SHANGHAI)).astimezone(SHANGHAI)
    day = local.date() if local.hour >= 18 else local.date() - timedelta(days=1)
    return day.isoformat()


def _resolve_node_bin() -> str:
    """Resolve Node.js binary even under minimal LaunchAgent/cron PATH."""
    env_bin = os.environ.get("LEI_NODE_BIN")
    if env_bin and os.path.isfile(env_bin) and os.access(env_bin, os.X_OK):
        return env_bin
    found = shutil.which("node")
    if found:
        return found
    for candidate in ("/opt/homebrew/bin/node", "/usr/local/bin/node", "/usr/bin/node"):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise FileNotFoundError(
        "node binary not found in PATH or /opt/homebrew/bin/node; set LEI_NODE_BIN"
    )


def _run_cli(symbols: list[str], *, limit: int = 300) -> bytes:
    if not CLI.is_file():
        raise FileNotFoundError(CLI)
    cmd = [
        _resolve_node_bin(),
        str(CLI),
        "kline",
        ",".join(symbols),
        "--period",
        "day",
        "--limit",
        str(limit),
        "--fq",
        "qfq",
    ]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True
    )
    try:
        out, err = proc.communicate(timeout=45)
    except subprocess.TimeoutExpired as exc:
        os.killpg(proc.pid, signal.SIGKILL)
        out, err = proc.communicate()
        raise CliQueryError("WeStock CLI timed out", out + b"\n[stderr]\n" + err) from exc
    if len(out) + len(err) > MAX_RAW:
        raise CliQueryError("WeStock response exceeded 3 MiB", (out + err)[:MAX_RAW])
    if proc.returncode:
        raise CliQueryError(
            f"WeStock CLI exited {proc.returncode}: {err[:180]!r}",
            out + b"\n[stderr]\n" + err,
        )
    return out


class CliQueryError(RuntimeError):
    def __init__(self, message: str, raw: bytes):
        self.raw = raw
        super().__init__(message)


def parse_kline(
    raw: bytes, symbols: list[str], cutoff: str
) -> dict[str, list[tuple[str, Decimal]]]:
    text = raw.decode("utf-8", "replace")
    requested = set(symbols)
    if len(requested) != len(symbols):
        raise ValueError("duplicate requested symbol")
    if len(symbols) > 1:
        m = BATCH.search(text)
        if (
            not m
            or m.group(1) != "success"
            or tuple(map(int, m.groups()[1:])) != (len(symbols), len(symbols), 0)
        ):
            raise ValueError("incomplete WeStock batch")
    rows: dict[str, list[tuple[str, Decimal]]] = {s: [] for s in symbols}
    seen: set[tuple[str, str]] = set()
    table = False
    for line in text.splitlines():
        if line.strip().startswith("| symbol | date | open |"):
            table = True
            continue
        if not table or not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(FIELDS):
            continue
        if cells[0] == "---":
            continue
        symbol, day = cells[:2]
        if symbol not in requested:
            raise ValueError(f"unexpected provider symbol {symbol}")
        try:
            datetime.strptime(day, "%Y-%m-%d")
            nums = [Decimal(c.replace(",", "")) for c in cells[2:]]
        except (ValueError, ArithmeticError) as exc:
            raise ValueError(f"invalid provider row {symbol} {day}") from exc
        if (symbol, day) in seen:
            raise ValueError(f"duplicate provider row {symbol} {day}")
        seen.add((symbol, day))
        if day > cutoff:
            continue
        if any(not n.is_finite() for n in nums):
            raise ValueError(f"nonfinite provider row {symbol} {day}")
        # Zero placeholders are not valid trades. They remain absent so each
        # affected session requires explicit nontrading evidence below.
        if any(n <= 0 for n in nums[:4]) or nums[4] <= 0 or nums[5] <= 0:
            continue
        if nums[3] > min(nums[0], nums[1]) or nums[2] < max(nums[0], nums[1]):
            raise ValueError(f"invalid OHLC order {symbol} {day}")
        rows[symbol].append((day, nums[1]))
    for symbol, series in rows.items():
        series.sort()
        if not series:
            # A symbol with no historical bars can still be an IPO or halted;
            # qualification below makes that explicit.
            continue
        if len(series) > 300:
            raise ValueError(f"too many provider bars {symbol}")
    return rows


def parse_zero_placeholders(raw: bytes, symbols: list[str], cutoff: str) -> dict[str, set[str]]:
    """Preserve explicit zero-volume K-line placeholders as nontrading evidence."""
    out: dict[str, set[str]] = defaultdict(set)
    requested = set(symbols)
    for line in raw.decode("utf-8", "replace").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(FIELDS) or cells[0] not in requested:
            continue
        symbol, day = cells[:2]
        if day > cutoff:
            continue
        try:
            volume, amount = Decimal(cells[6]), Decimal(cells[7])
        except ArithmeticError:
            continue
        if volume == 0 and amount == 0:
            out[day].add(symbol)
    return out


_BAOSTOCK_WORKER = r"""
import json, socket, sys
import baostock as bs
socket.setdefaulttimeout(15)
symbol, start, end = sys.argv[1:4]
login = bs.login()
if login.error_code != "0":
    raise RuntimeError("BaoStock login: " + login.error_msg)
try:
    result = bs.query_history_k_data_plus(symbol[:2] + "." + symbol[2:],
        "date,tradestatus,volume,amount", start_date=start, end_date=end,
        frequency="d", adjustflag="3")
    if result.error_code != "0":
        raise RuntimeError("BaoStock query: " + result.error_msg)
    rows = []
    while result.next():
        rows.append(dict(zip(result.fields, result.get_row_data())))
    print("@@RESULT@@" + json.dumps({"symbol": symbol, "rows": rows}))
finally:
    bs.logout()
"""


def _baostock_status(symbol: str, start: str, end: str) -> tuple[dict, bytes]:
    """One symbol per bounded subprocess, retaining the original SDK response."""
    import sys

    proc = subprocess.Popen(
        [sys.executable, "-B", "-c", _BAOSTOCK_WORKER, symbol, start, end],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=30)
    except subprocess.TimeoutExpired as exc:
        os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = proc.communicate()
        error = StatusQueryError(
            f"BaoStock status timeout {symbol}", stdout + b"\n[stderr]\n" + stderr
        )
        raise error from exc
    raw = stdout + b"\n[stderr]\n" + stderr
    if len(raw) > MAX_RAW:
        raise StatusQueryError(f"BaoStock status response too large {symbol}", raw[:MAX_RAW])
    if proc.returncode:
        raise StatusQueryError(f"BaoStock status failed {symbol}: {stderr[:160]!r}", raw)
    marker = [
        line
        for line in stdout.decode("utf-8", "replace").splitlines()
        if line.startswith("@@RESULT@@")
    ]
    if len(marker) != 1:
        raise StatusQueryError(f"BaoStock status response absent {symbol}", raw)
    return json.loads(marker[0][len("@@RESULT@@") :]), raw


class StatusQueryError(RuntimeError):
    def __init__(self, message: str, raw: bytes):
        self.raw = raw
        super().__init__(message)


def parse_snapshot(raw: bytes, day: str, symbols: list[str]) -> set[str]:
    """Return only symbols explicitly showing same-day zero traded volume."""
    text = raw.decode("gbk", "replace")
    lines = dict(re.findall(r'v_((?:sh|sz|bj)\d{6})="([^"]*)"', text))
    if set(lines) != set(symbols):
        raise ValueError("snapshot symbol coverage incomplete")
    halted = set()
    for symbol, payload in lines.items():
        fields = payload.split("~")
        if len(fields) < 38 or fields[30][:8] != day.replace("-", ""):
            raise ValueError(f"snapshot date or shape invalid: {symbol}")
        try:
            volume = Decimal(fields[36])
            price = Decimal(fields[3])
        except ArithmeticError as exc:
            raise ValueError(f"snapshot numeric field invalid: {symbol}") from exc
        if volume == 0 and price > 0:
            halted.add(symbol)
    return halted


def _snapshot(symbols: list[str]) -> bytes:
    response = requests.get("https://qt.gtimg.cn/q=" + ",".join(symbols), timeout=15)
    response.raise_for_status()
    if len(response.content) > MAX_RAW:
        raise ValueError("snapshot exceeded 3 MiB")
    return response.content


def _official_listings() -> tuple[dict[str, str], dict[str, int]]:
    import akshare as ak

    specs = (
        ("sh", ak.stock_info_sh_name_code, {"symbol": "主板A股"}, "证券代码", "上市日期"),
        ("sh", ak.stock_info_sh_name_code, {"symbol": "科创板"}, "证券代码", "上市日期"),
        ("sz", ak.stock_info_sz_name_code, {}, "A股代码", "A股上市日期"),
        ("bj", ak.stock_info_bj_name_code, {}, "证券代码", "上市日期"),
    )
    listed: dict[str, str] = {}
    counts: dict[str, int] = {}
    # Reject a truncated exchange table; the 2026-11-02 official snapshot had
    # 1700 / 618 / 2905 / 354 rows respectively. A large shrink needs review.
    minimum_rows = (1530, 556, 2614, 318)
    for i, (prefix, fn, kwargs, code_col, date_col) in enumerate(specs):
        frame = fn(**kwargs)
        if len(frame) < minimum_rows[i] or code_col not in frame or date_col not in frame:
            raise RuntimeError(f"official listing source {i} incomplete")
        counts[f"source_{i}"] = len(frame)
        for _, row in frame.iterrows():
            symbol = prefix + str(row[code_col]).zfill(6)
            day = str(row[date_col])[:10]
            if not SYMBOL.fullmatch(symbol) or symbol in listed:
                raise ValueError(f"invalid or duplicate official symbol {symbol}")
            datetime.strptime(day, "%Y-%m-%d")
            listed[symbol] = day
    if not all(any(s.startswith(prefix) for s in listed) for prefix in ("sh", "sz", "bj")):
        raise RuntimeError("official exchange coverage incomplete")
    return listed, counts


def qualify_tail(
    old: list[dict],
    listings: dict[str, str],
    calendar: list[str],
    series: dict[str, list[tuple[str, Decimal]]],
    cutoff: str,
    nontrading: dict[str, set[str]] | None = None,
    *,
    allow_partial: bool = False,
) -> tuple[list[dict], dict]:
    """Strict daily qualification; optional output is a continuous verified prefix."""
    if not old or [x["date"] for x in old] != sorted(set(x["date"] for x in old)):
        raise ValueError("old history is missing, duplicated, or unordered")
    if not listings or set(listings) != set(series):
        raise ValueError("official current universe and qfq requests differ")
    if calendar != sorted(set(calendar)) or not calendar:
        raise ValueError("trading calendar invalid")
    target = [d for d in calendar if old[-1]["date"] < d <= cutoff]
    if not target:
        raise ValueError("no completed new index sessions")
    nontrading = nontrading or {}
    tail = []
    audit = {}
    prefix_open = True
    for day in target:
        counters = {n: Counter() for n in WINDOWS}
        unresolved = defaultdict(list)
        counts = Counter()
        for symbol, ipo in listings.items():
            if ipo > day:
                counts["not_yet_listed"] += 1
                continue
            counts["listed"] += 1
            valid = [(d, p) for d, p in series[symbol] if d <= day]
            if not valid or valid[-1][0] != day:
                if symbol in nontrading.get(day, set()):
                    counts["confirmed_nontrading"] += 1
                else:
                    unresolved["missing_same_day_quote"].append(symbol)
                continue
            counts["traded"] += 1
            for n in WINDOWS:
                if len(valid) < n:
                    sessions_since_ipo = sum(ipo <= d <= day for d in calendar)
                    if sessions_since_ipo < n:
                        counts[f"ipo_warmup_{n}"] += 1
                    else:
                        unresolved[f"history_short_{n}"].append(symbol)
                    continue
                closes = [p for _, p in valid[-n:]]
                counters[n]["eligible"] += 1
                if closes[-1] * n > sum(closes):
                    counters[n]["above"] += 1
        audit[day] = {
            **counts,
            "eligible": {str(n): counters[n]["eligible"] for n in WINDOWS},
            "unresolved": {k: v for k, v in unresolved.items()},
        }
        if unresolved or any(not counters[n]["eligible"] for n in WINDOWS):
            prefix_open = False
            continue
        if prefix_open:
            tail.append(
                {
                    "date": day,
                    **{
                        f"ma{n}_pct": round(100 * counters[n]["above"] / counters[n]["eligible"], 6)
                        for n in WINDOWS
                    },
                }
            )
    if len(tail) != len(target) and (not allow_partial or not tail):
        raise QualificationError(audit)
    return old + tail, audit


class QualificationError(ValueError):
    def __init__(self, audit: dict):
        self.audit = audit
        super().__init__(
            "unresolved quote/history on "
            + ", ".join(day for day, info in audit.items() if info["unresolved"])
        )


def refresh(output: Path, cache: Path | None = None, cutoff: str | None = None) -> dict:
    """Collect full 300-bar qfq windows and prepare a review-only candidate."""
    output = Path(output)
    if output.exists():
        raise ValueError("output must be a new directory")
    cutoff = cutoff or closed_cutoff()
    datetime.strptime(cutoff, "%Y-%m-%d")
    if cutoff > closed_cutoff():
        raise ValueError("cutoff is not a completed Shanghai session")
    old_path = Path(cache or cache_root()) / "a_share_ma_breadth_history.json"
    old_raw = old_path.read_bytes()
    old = json.loads(old_raw)
    listings, source_counts = _official_listings()
    output.mkdir(parents=True)
    (output / "raw").mkdir()
    _guard(output)
    (output / "previous-history.json").write_bytes(old_raw)
    official_raw = json.dumps(listings, ensure_ascii=False, sort_keys=True).encode("utf-8")
    (output / "raw/official-listings.json.gz").write_bytes(gzip.compress(official_raw))
    receipt: dict = {
        "schema": "cn-breadth-refresh/1",
        "status": "collecting",
        "cutoff": cutoff,
        "old_history_sha256": _sha(old_raw),
        "old_last_date": old[-1]["date"],
        "official_source_counts": source_counts,
        "official_universe_count": len(listings),
        "official_listings_sha256": _sha(official_raw),
        "batches": [],
        "errors": [],
    }
    _write_json(output / "receipt.json", receipt)
    try:
        # The index dates, not a union of stock bars, define completed sessions.
        try:
            index_raw = _run_cli(["sh000001"])
        except CliQueryError as exc:
            (output / "raw/index-failed.md.gz").write_bytes(gzip.compress(exc.raw))
            receipt["index_failed_sha256"] = _sha(exc.raw)
            raise
        (output / "raw/index.md.gz").write_bytes(gzip.compress(index_raw))
        receipt["index_sha256"] = _sha(index_raw)
        index_text = index_raw.decode("utf-8", "replace")
        calendar = sorted(
            {
                m.group(1)
                for m in re.finditer(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|", index_text, re.M)
                if m.group(1) <= cutoff
            }
        )
        if old[-1]["date"] not in calendar:
            raise ValueError("index history does not overlap existing breadth tail")
        if calendar[-1] <= old[-1]["date"]:
            receipt.update(
                {
                    "status": "no_new_sessions",
                    "no_new_sessions": True,
                    "last_date": old[-1]["date"],
                    "last_index_session": calendar[-1],
                }
            )
            _write_json(output / "receipt.json", receipt)
            return receipt
        codes = sorted(listings)
        series: dict[str, list[tuple[str, Decimal]]] = {}
        nontrading: dict[str, set[str]] = defaultdict(set)
        for i in range(0, len(codes), BATCH_SIZE):
            _guard(output)
            group = codes[i : i + BATCH_SIZE]
            for attempt in (1, 2):
                raw = b""
                try:
                    raw = _run_cli(group)
                    parsed = parse_kline(raw, group, cutoff)
                    break
                except (RuntimeError, ValueError) as exc:
                    failed_raw = exc.raw if isinstance(exc, CliQueryError) else raw
                    if failed_raw:
                        failed_name = f"batch-{i // BATCH_SIZE:03d}-attempt-{attempt}.md.gz"
                        (output / "raw" / failed_name).write_bytes(gzip.compress(failed_raw))
                        receipt.setdefault("failed_responses", []).append(
                            {
                                "raw": failed_name,
                                "sha256": _sha(failed_raw),
                                "error": str(exc)[:200],
                            }
                        )
                    _write_json(output / "receipt.json", receipt)
                    if attempt == 2:
                        raise
                    time.sleep(0.25)
            name = f"batch-{i // BATCH_SIZE:03d}.md.gz"
            (output / "raw" / name).write_bytes(gzip.compress(raw))
            receipt["batches"].append(
                {
                    "symbols": group,
                    "raw": name,
                    "sha256": _sha(raw),
                    "rows": sum(map(len, parsed.values())),
                }
            )
            series.update(parsed)
            for day, symbols in parse_zero_placeholders(raw, group, cutoff).items():
                # BaoStock corroborates SH/SZ missing bars; the explicit
                # WeStock zero-volume placeholder is used only for BJ.
                nontrading[day].update(s for s in symbols if s.startswith("bj"))
            _write_json(output / "receipt.json", receipt)
            time.sleep(0.25)
        target = [d for d in calendar if old[-1]["date"] < d <= cutoff]
        missing_by_symbol = defaultdict(set)
        for symbol, ipo in listings.items():
            valid_dates = {d for d, _ in series[symbol]}
            for day in target:
                if (
                    ipo <= day
                    and day not in valid_dates
                    and symbol not in nontrading.get(day, set())
                ):
                    missing_by_symbol[symbol].add(day)
        status_queries = 0
        for symbol, missing_days in sorted(missing_by_symbol.items()):
            if symbol.startswith("bj"):
                continue
            if status_queries >= 250:
                receipt.setdefault("status_failures", {})[symbol] = "bounded at 250 status queries"
                continue
            status_queries += 1
            _guard(output)
            start, end = min(missing_days), max(missing_days)
            failure_message = "unknown status query failure"
            for attempt in (1, 2):
                try:
                    status, raw = _baostock_status(symbol, start, end)
                    break
                except Exception as exc:
                    failure_message = f"{type(exc).__name__}: {str(exc)[:200]}"
                    if isinstance(exc, StatusQueryError):
                        failed_name = f"baostock-{symbol}-attempt-{attempt}.txt.gz"
                        (output / "raw" / failed_name).write_bytes(gzip.compress(exc.raw))
                        receipt.setdefault("baostock_failed_responses", []).append(
                            {"symbol": symbol, "raw": failed_name, "sha256": _sha(exc.raw)}
                        )
                    if attempt == 1:
                        time.sleep(0.25)
            else:
                receipt.setdefault("status_failures", {})[symbol] = failure_message
                continue
            name = f"baostock-{symbol}-{start}-{end}.txt.gz"
            (output / "raw" / name).write_bytes(gzip.compress(raw))
            receipt.setdefault("baostock", []).append(
                {"symbol": symbol, "raw": name, "sha256": _sha(raw), "days": sorted(missing_days)}
            )
            seen_status_days = set()
            for row in status["rows"]:
                day = row.get("date")
                if day not in missing_days or day in seen_status_days:
                    continue
                seen_status_days.add(day)
                if row.get("tradestatus") == "0":
                    nontrading[day].add(symbol)
            _write_json(output / "receipt.json", receipt)
        today = datetime.now(SHANGHAI).date().isoformat()
        if cutoff == today:
            missing = [
                s
                for s, rows in series.items()
                if listings[s] <= cutoff
                and (not rows or rows[-1][0] != cutoff)
                and s not in nontrading.get(cutoff, set())
            ]
            for i in range(0, len(missing), 100):
                raw = _snapshot(missing[i : i + 100])
                name = f"snapshot-{i // 100:03d}.txt.gz"
                (output / "raw" / name).write_bytes(gzip.compress(raw))
                nontrading.setdefault(cutoff, set()).update(
                    parse_snapshot(raw, cutoff, missing[i : i + 100])
                )
                receipt.setdefault("snapshots", []).append({"raw": name, "sha256": _sha(raw)})
        candidate, audit = qualify_tail(
            old, listings, calendar, series, cutoff, nontrading, allow_partial=True
        )
        _write_json(output / "candidate-history.json", candidate)
        new_dates = [x["date"] for x in candidate[len(old) :]]
        receipt.update(
            {
                "status": "ready" if len(new_dates) == len(target) else "partial",
                "new_dates": new_dates,
                "candidate_sha256": _sha((output / "candidate-history.json").read_bytes()),
                "daily_audit": audit,
            }
        )
    except Exception as exc:
        receipt["status"] = "failed"
        receipt["errors"].append(f"{type(exc).__name__}: {str(exc)[:500]}")
        if isinstance(exc, QualificationError):
            receipt["daily_audit"] = exc.audit
    _write_json(output / "receipt.json", receipt)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--cutoff")
    args = parser.parse_args()
    result = refresh(args.output, args.cache, args.cutoff)
    print(
        json.dumps(
            {
                "status": result["status"],
                "new_dates": result.get("new_dates"),
                "errors": result["errors"],
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(0 if result["status"] in ("ready", "partial") else 1)
