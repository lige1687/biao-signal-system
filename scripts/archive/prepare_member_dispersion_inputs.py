"""Rebuild fixed-current-member observation inputs from registered offline snapshots."""
import argparse
from bisect import bisect_right
from datetime import datetime
from io import BytesIO
import gzip
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

REPO = Path.home() / "Desktop/lei-signal-lab"
VOLUME = Path("/Volumes/win+mac通用/LeiSignal-新实验结果")
EVIDENCE = REPO / "docs/ops/microstructure-observations-20261108"
SECTORS = tuple(f"{number:06d}" for number in range(908, 918))
SECTOR_ETFS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")
NY = ZoneInfo("America/New_York")
CACHE = Path.home() / ".lei_signal_lab/cache"
CACHE_VERSION = {
    "000300.SS": (
        "e80c862e5ab57a4fb6f0e18c6e8134b8781e723c69d2716ea831387a1d6c3a65",
        "2a30e454844925f1c31514a8b0bc180c235e0207f3be5b0f2df7b55aaad7bc5a",
        0.006,
    ),
    "^GSPC": (
        "411a52f888c439d4f47a18cb1a2eaac0eca1f12770f89ea987d081deafd8239b",
        "aeb5f3faf29420b9b664b31431736264359264c4bc20a02745e96dc0419f276b",
        0.001,
    ),
}


def archived(project, suffix):
    matches = list((VOLUME / project).glob(suffix))
    if len(matches) != 1:
        raise ValueError(f"expected one registered {project}/{suffix}, got {matches}")
    return matches[0]


def read_bytes(path, sha256=None):
    blob = path.read_bytes()
    if sha256 and hashlib.sha256(blob).hexdigest() != sha256:
        raise ValueError(f"fingerprint mismatch: {path}")
    return blob


def read(path, sha256=None):
    blob = read_bytes(path, sha256)
    return json.loads(gzip.decompress(blob) if path.suffix == ".gz" else blob)


def archived_attempts(folder):
    return {
        row["file"]: row["sha256"]
        for row in map(json.loads, (folder / "attempts.jsonl").read_text().splitlines())
        if row["status"] == "ok"
    }


def read_ref(ref):
    return read(Path(ref.get("source_path") or ref["path"]), ref.get("compressed_sha256") or ref["sha256"])


def positive(series):
    series = series.astype(float)
    if not series.index.is_unique:
        raise ValueError("duplicated session")
    return series.where(np.isfinite(series) & series.gt(0))


def yahoo(body, symbol, field="adjclose"):
    result = (body["chart"]["result"] or [None])[0]
    if result is None:
        return None
    if result["meta"]["symbol"] != symbol or result["meta"]["exchangeTimezoneName"] != str(NY):
        raise ValueError(f"Yahoo identity mismatch: {symbol}")
    dates = [datetime.fromtimestamp(t, NY).date().isoformat() for t in result["timestamp"]]
    column = result["indicators"][field if field == "adjclose" else "quote"][0][field]
    return positive(pd.Series(column, index=dates, dtype=float))


def china_members():
    snapshot = archived("stock-universe-cn-20261015", "*/result")
    paths = {p.name.removesuffix("-daily.json"): p for p in snapshot.glob("*-daily.json") if not p.name.startswith("._")}
    if len(paths) != 300:
        raise ValueError("unexpected CSI 300 snapshot roster")
    archive = archived("public-universe-deep-completion-20261026", "*/result/cn-all-equity")
    meta = read(archive / "all-equity-read-index-v8-meta.json")
    raw_index = Path(meta["index_path"]).read_bytes()
    if hashlib.sha256(raw_index).hexdigest() != meta["index_sha256"]:
        raise ValueError("invalid BaoStock v8 archive index")
    index = {}
    for line in raw_index.splitlines():
        row = json.loads(line)
        if row["code"] in paths:
            index[row["code"]] = row
    old_union = {}
    old_ref = meta["old_union"]
    old_blob = Path(old_ref["path"]).read_bytes()
    if hashlib.sha256(old_blob).hexdigest() != old_ref["sha256"]:
        raise ValueError("invalid BaoStock v4 archive index")
    for line in old_blob.splitlines():
        row = json.loads(line)
        if row["code"] in paths:
            old_union[row["code"]] = row["source_refs"]

    def price_rows(body, symbol, first, last):
        for values in body["data"]:
            row = dict(zip(body["fields"], values))
            day = row["date"]
            if first <= day <= last and row["tradestatus"] == "1":
                if row["code"] != symbol or row["adjustflag"] != "3":
                    raise ValueError(f"unexpected BaoStock price identity: {symbol}")
                yield day, float(row["close"])

    def adjustment_rows(body):
        for values in body["data"]:
            row = dict(zip(body["fields"], values))
            yield row["dividOperateDate"], float(row["backAdjustFactor"])

    panels = {}
    attempts = archived_attempts(snapshot)
    overlap_count, overlap_conflicts = 0, 0
    for code, path in paths.items():
        entry = index[code]
        prices = dict(price_rows(read(path, attempts[path.name]), code, "2020-01-01", "2026-06-30"))
        factor_path = snapshot / f"{code}-adjustments.json"
        factors = dict(adjustment_rows(read(factor_path, attempts[factor_path.name])))
        for ref in entry["new_factor_sources"]:
            factors.update(adjustment_rows(read_ref(ref)))
        conflicting_dates = set()
        refs = old_union.get(code, []) + entry["new_price_sources"] + entry["reused_raw_sources"]
        for ref in refs:
            first = ref.get("valid_slice_start") or ref.get("observed_first_date") or ref.get("first_date") or ref.get("source_request_start") or "9999"
            last = ref.get("valid_slice_end") or ref.get("observed_last_date") or ref.get("last_date") or ref.get("source_request_end") or "0000"
            if last < "2026-06-01" or first > "2026-10-23":
                continue
            for day, price in price_rows(read_ref(ref), code, max(first, "2026-06-01"), min(last, "2026-10-23")):
                prior = prices.setdefault(day, price)
                if day <= "2026-06-30":
                    overlap_count += 1
                if not math.isclose(prior, price, abs_tol=0.0001):
                    conflicting_dates.add(day)
        overlap_conflicts += len(conflicting_dates)
        events = sorted(factors)
        adjusted = {}
        for day, price in prices.items():
            if day not in conflicting_dates:
                event = bisect_right(events, day) - 1
                adjusted[day] = price * (factors[events[event]] if event >= 0 else 1)
        panels[code] = positive(pd.Series(adjusted, dtype=float))
    print(f"CN raw duplicate/overlap comparisons in June: {overlap_count}; conflicting symbol/dates removed: {overlap_conflicts}")
    return pd.DataFrame(panels)


def america_members():
    snapshot = archived("stock-universe-us-20261015", "*/result")
    recent = read(EVIDENCE / "constituents/source-ledger.json")
    if len(recent) != 502 or len({r["symbol"] for r in recent}) != 502:
        raise ValueError("unexpected IVV snapshot roster")
    old_cols, recent_cols = {}, {}
    attempts = archived_attempts(snapshot)
    for ref in recent:
        symbol = ref["symbol"]
        path = snapshot / f"{symbol}.json"
        old_cols[symbol] = yahoo(read(path, attempts[path.name]), symbol)
        recent_cols[symbol] = yahoo(read_ref(ref), symbol)
    old = pd.DataFrame(old_cols).sort_index()
    recent = pd.DataFrame(recent_cols).sort_index()
    bridge_path = archived("breadth-reading-aid-20261101", "*173936-481c3e5b7840/result/breadth-us/adjusted-closes.parquet")
    bridge_blob = read_bytes(bridge_path, "95b6c1aea7987712e647f7532ed828ec3fc4eaae42797e18f252dd2e3577ecaa")
    bridge = pd.read_parquet(BytesIO(bridge_blob)).astype(float)
    bridge.index = bridge.index.strftime("%Y-%m-%d")
    bridge = bridge.reindex(columns=old.columns).where(lambda x: x.gt(0) & np.isfinite(x))
    return old, bridge, recent


def extend_index(symbol, index):
    bars_sha, metadata_sha, max_delta = CACHE_VERSION[symbol]
    frame = pd.read_parquet(BytesIO(read_bytes(CACHE / f"{symbol}.bars.parquet", bars_sha)))
    metadata = read(CACHE / f"{symbol}.bars.meta.json", metadata_sha)
    if (
        metadata["symbol"] != symbol
        or metadata["kind"] != "bars"
        or metadata["rows"] != len(frame)
        or metadata["first_date"] != str(frame.index[0])
        or metadata["last_date"] != str(frame.index[-1])
        or not frame.index.is_monotonic_increasing
    ):
        raise ValueError(f"invalid cached index metadata: {symbol}")
    cached = positive(frame["close"])
    cached.index = cached.index.strftime("%Y-%m-%d")
    common = index.index.intersection(cached.index)
    differences = (index[common] - cached[common]).abs()
    print(f"{symbol} cache: {len(common)} overlapping sessions, max close difference {differences.max():.8f}")
    if len(common) < 250 or differences.max() > max_delta or cached.isna().any():
        raise ValueError(f"cached index failed overlap: {symbol}")
    return index.combine_first(cached.loc[cached.index > index.index.max()])


def market_sources():
    pointer = read(REPO / "docs/experiments/raw/market-increment-map-2026-11-02/continuation-20261103/data-package-pointer.json")
    package = Path(pointer["path"])
    read(package, pointer["sha256"])

    def sector_raw(key):
        path = package.parent / "sources" / f"{key}.json"
        ref = read(path.with_suffix(".receipt.json"))
        return read(path, ref["sha256"])

    def tencent(code):
        rows = sector_raw(f"cn-{code}")["data"][f"sh{code}"]["day"]
        return positive(pd.Series([r[2] for r in rows], index=[r[0] for r in rows]))

    cn_index_recent = tencent("000300").loc[:"2026-11-02"]
    cn_index_archive = archived("twenty-year-universe-data-20261025", "*/result/cn/consumer/parent-price-frozen-000300-2006_20261023.csv")
    frozen = pd.read_csv(BytesIO(read_bytes(cn_index_archive, "3a8ddfca66662e3ea97c36531593ba8431d0150098951b8d88e35b18c67bd9b1")), index_col="date")
    cn_index = positive(frozen["close"])
    common = cn_index.index.intersection(cn_index_recent.index)
    if len(common) < 250 or (cn_index[common] - cn_index_recent[common]).abs().max() > 0.02:
        raise ValueError("CSI 300 index archive and Tencent close failed overlap")
    cn_index = cn_index_recent.combine_first(cn_index)
    cn_sectors = pd.DataFrame({code: tencent(code).loc[:"2026-11-02"] for code in SECTORS})
    us_sectors = pd.DataFrame({code: yahoo(sector_raw(f"us-{code}"), code, "close").loc[:"2026-10-30"] for code in SECTOR_ETFS})
    us_path = REPO / "docs/ops/breadth-reading-aid-20261101/workbuddy-us-gspc-json-v4.snapshot"
    us_index = yahoo(read(us_path, "c6b755d57b4b6fdc2e11cb2678482b35327ea6b869ca3cf4a2031bf5ec56b22c"), "^GSPC", "close").loc[:"2026-10-23"]
    return extend_index("000300.SS", cn_index), extend_index("^GSPC", us_index), cn_sectors, us_sectors


def returns(prices):
    return prices.pct_change(fill_method=None)


def member_metrics(prices):
    minimum = math.ceil(0.95 * len(prices.columns))
    daily = returns(prices)
    result = {"disp_raw": daily.std(axis=1, ddof=0).mul(100).where(daily.count(axis=1).ge(minimum))}
    for period in (20, 60):
        avg = prices.rolling(period, min_periods=period).mean()
        covered = avg.count(axis=1)
        result[f"pct_above_ma{period}"] = prices.gt(avg).sum(axis=1).mul(100).div(covered).where(covered.ge(minimum))
    return pd.DataFrame(result)


def us_metrics(frames, calendar):
    old, bridge, recent = (frame.reindex(calendar) for frame in frames)
    bridge_returns = returns(bridge)
    for name, dataset in (("old", old), ("recent", recent)):
        returns_on_both = returns(dataset).stack().align(bridge_returns.stack(), join="inner")
        gap = (returns_on_both[0] - returns_on_both[1]).abs()
        print(f"US {name}/bridge overlapping symbol-returns={len(gap)}, median diff={gap.median():.9g}, >0.05pp={gap.gt(0.0005).sum()}, >0.5pp={gap.gt(0.005).sum()}")
        if len(gap) < 10000 or gap.gt(0.0005).mean() > 0.002:
            raise ValueError(f"US {name} bridge overlap failed")
    # Choose metrics only within complete windows of one snapshot. Never calculate a
    # daily return or moving average with prices taken from two vintages.
    return member_metrics(recent).combine_first(member_metrics(old)).combine_first(member_metrics(bridge))


def card(market, index, sectors, metrics, source_labels, calendar):
    fields = metrics.copy()
    fields["index_close"] = index
    daily = returns(sectors.reindex(calendar))
    fields["sector_disp_raw"] = daily.std(axis=1, ddof=0).mul(100).where(daily.notna().all(axis=1))
    fields = fields.loc["2020-01-02":]
    print(market, len(fields), "sessions", fields.index[0], fields.index[-1])
    for column in fields:
        valid = fields[column].dropna()
        print(f"  {column}: {len(valid)} {valid.index[0]}..{valid.index[-1]} last={valid.iloc[-1]:.8f}")
    print("  complete diagnostics inputs", fields.drop(columns="sector_disp_raw").dropna().shape[0])
    return {
        "id": f"{market}-current-members-daily-dispersion",
        "sources": source_labels,
        "points": [
            {"date": day, **{name: round(float(value), 8) if pd.notna(value) else None for name, value in row.items()}}
            for day, row in fields.iterrows()
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="write the normalized JSON to this path")
    args = parser.parse_args()
    cn_index, us_index, cn_sectors, us_sectors = market_sources()
    # The archived index-session axes keep exchange holidays out and retain missing
    # member/sector observations. The recent US panel was itself reindexed to ^GSPC.
    cn_calendar = cn_index.loc["2020-01-02":].index
    cn_plan = REPO / "docs/experiments/raw/public-universe-deep-completion-2026-10-26/cn-all-equity-plan/coverage-plan-v2.json"
    cn_calendar_ref = read(cn_plan)["baseline"]["calendar"]
    cn_calendar_raw = read_bytes(Path(cn_calendar_ref["path"]), cn_calendar_ref["sha256"])
    cn_witness = pd.read_csv(BytesIO(cn_calendar_raw))["trade_date"]
    cn_witness = pd.Index(cn_witness[cn_witness.between("2020-01-02", "2026-10-23")])
    if not cn_calendar[cn_calendar <= "2026-10-23"].equals(cn_witness):
        raise ValueError("CSI 300 index session axis diverges from the archived calendar")
    us_frames = america_members()
    us_calendar = us_index.loc["2020-01-02":].index
    for name, frame in zip(("bridge", "recent"), us_frames[1:]):
        expected_sessions = us_calendar[us_calendar >= frame.index.min()]
        if not frame.index.equals(expected_sessions):
            raise ValueError(f"US {name} dates diverge from the index-session axis")
    cn = card("cn", cn_index, cn_sectors, member_metrics(china_members().reindex(cn_calendar)), {
        "members": "BaoStock 沪深300固定300股（2026-10-15 名单）后复权，逐日相邻双报价覆盖至少95%，历史回看，截至2026-10-23。",
        "breadth": "同一沪深300固定池，合格股连续20/60个交易日实际收盘均线，当日站上均线占比，至少95%成员可计算。",
        "index": "沪深300价格指数收盘，历史归档与腾讯行情重叠核对，缓存补齐至2026-11-06。",
        "sectors": "腾讯行情所载沪深300十行业价格指数，十行业相邻两日均有价时计算，至2026-11-02。",
    }, cn_calendar)
    us = card("us", us_index, us_sectors, us_metrics(us_frames, us_calendar), {
        "members": "Yahoo Finance 调整收盘，2026-10-15 IVV 固定持仓代理502股，至少95%有相邻两日价；2026年夏季缺口复用其中488股的重叠归档，截至2026-11-06。",
        "breadth": "同一IVV固定代理池，以各Yahoo归档内连续20/60个交易日的实际均线计算，至少95%成员合格，覆盖随日期变化。",
        "index": "Yahoo Finance 标普500价格指数收盘归档，与近期指数缓存重叠核对，补齐至2026-11-06。",
        "sectors": "Yahoo Finance 11只 Select Sector SPDR ETF 拆分调整收盘（不含现金分红），全部相邻两日有价时计算，至2026-10-30。",
    }, us_calendar)
    args.output.write_text(json.dumps({"schemaVersion": 1, "cards": [cn, us]}, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
