"""Prepare point-in-time breadth inputs for the frozen experiment."""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import akshare as ak
import baostock as bs
import numpy as np
import pandas as pd
import pdfplumber
import requests
from bs4 import BeautifulSoup

# baostock 0.9.30 still calls the pandas<2 append API in historical queries.
if not hasattr(pd.DataFrame, "append"):
    pd.DataFrame.append = pd.DataFrame._append

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = HERE / "prepared"
SOURCES = OUT / "sources"
OLD = ROOT / "docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12"
ALL_A_PANEL = Path.home() / ".lei_signal_lab/cache/a_share_klines_full.parquet"
START_WARM = pd.Timestamp("2014-12-01")
PRICE_START = "2014-01-01"
END = pd.Timestamp("2026-06-30")

CHINEXT_SOURCE_FILES = [
    "t20260529_620819.html", "t20251128_617545.html", "t20250603_613877.html",
    "t20240531_607513.html", "t20241202_610741.html", "t20231127_604734.html",
    "t20230529_600689.html", "t20221128_597558.html", "t20220530_593483.html",
    "t20211129_589914.html", "t20210601_586215.html", "t20201201_583545.html",
    "t20200602_578019.html", "t20191202_572315.html", "t20190603_567561.html",
    "t20181210_563449.html", "t20180910_554739.html", "P020180611322725643044.pdf",
    "P020180328434919926847.pdf", "t20170911_502151.html",
    "P020180328434598371240.pdf", "t20170313_501964.html",
    "P020180328434250569548.pdf", "t20160919_501801.html",
    "P020180328433995424132.pdf", "t20160314_501661.html",
    "P020180328433742533247.pdf", "t20150914_501547.html",
    "t20150608_501461.html", "t20150309_501388.html", "t20141215_501336.html",
]
CODE_RENAMES = {"302132": ("300114", pd.Timestamp("2025-02-17"))}
SPECIAL_CHINEXT_CHANGES = [
    {
        "filename": "P020240805528066886656.pdf",
        "url": "https://www.cnindex.com.cn/zh_information/notices_news/2024y/202408/P020240805528066886656.pdf",
        "announcement_date": pd.Timestamp("2024-08-05"),
        "effective_date": pd.Timestamp("2024-08-12"),
        "additions": ["300212"],
        "deletions": ["300376"],
        "count": 1,
    },
]


def canonical_member(code: str) -> str:
    return CODE_RENAMES.get(code, (code, None))[0]


def dated_member(code: str, day: pd.Timestamp) -> str:
    for new_code, (old_code, effective) in CODE_RENAMES.items():
        if code == old_code and day >= effective:
            return new_code
    return code


def save_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def etf_dates(symbol: str) -> pd.DatetimeIndex:
    prefix = "sh" if symbol.startswith("5") else "sz"
    p = OLD / "inputs/bars" / f"{prefix}{symbol}-nominal.csv"
    df = pd.read_csv(p, parse_dates=["date"])
    return pd.DatetimeIndex(df.loc[df.date.between(START_WARM, END), "date"])


def fetch_szse_source(filename: str) -> tuple[str, bytes]:
    bases = [
        "https://www.szse.cn/disclosure/notice/",
        "https://www.szse.cn/marketServices/message/index/dynamic/",
    ]
    for base in bases:
        url = urljoin(base, filename)
        r = requests.get(url, timeout=45)
        if r.status_code == 200 and len(r.content) > 1000 and b"404" not in r.content[:500]:
            return url, r.content
    raise RuntimeError(f"cannot fetch {filename}")


def first_trading_day(year: int, month: int, trading_dates: pd.DatetimeIndex) -> pd.Timestamp:
    matches = trading_dates[(trading_dates.year == year) & (trading_dates.month == month)]
    if not len(matches):
        raise ValueError(f"no trading date for {year}-{month:02d}")
    return matches.min()


def parse_effective_date(text: str, trading_dates: pd.DatetimeIndex) -> pd.Timestamp:
    compact = re.sub(r"\s+", "", text)
    m = re.search(r"决定于(\d{4})年(\d{1,2})月(\d{1,2})日", compact)
    if m:
        return pd.Timestamp(date(*map(int, m.groups())))
    m = re.search(r"决定于(\d{4})年(\d{1,2})月(?:的)?第一个交易日", compact)
    if m:
        return first_trading_day(int(m.group(1)), int(m.group(2)), trading_dates)
    raise ValueError("effective date not found")


def parse_html_change(content: bytes):
    text = content.decode("utf-8", errors="replace")
    soup = BeautifulSoup(text, "lxml")
    needle = soup.find(string=re.compile("创业板指数样本股调整名单"))
    if needle is None:
        raise ValueError("ChiNext table heading absent")
    table = needle.parent.find_next("table")
    frame = pd.read_html(io.StringIO(str(table)))[0]
    rows = []
    for raw in frame.iloc[:, :4].itertuples(index=False, name=None):
        inc, out = str(raw[0]).split(".")[0].zfill(6), str(raw[2]).split(".")[0].zfill(6)
        if re.fullmatch(r"30\d{4}", inc) and re.fullmatch(r"30\d{4}", out):
            rows.append((inc, out))
    return " ".join(soup.stripped_strings), rows


def parse_pdf_change(content: bytes):
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    start = text.find("创业板指数样本股调整名单")
    if start < 0:
        raise ValueError("ChiNext PDF section absent")
    section = text[start + len("创业板指数样本股调整名单"):]
    next_heading = re.search(r"\n[^\n]*指数样本股调整名单", section)
    if next_heading:
        section = section[:next_heading.start()]
    rows = []
    for line in section.splitlines():
        codes = re.findall(r"\b(30\d{4})\b", line)
        if len(codes) >= 2:
            rows.append((codes[0], codes[1]))
    return text, rows


def build_chinext_memberships(trading_dates: pd.DatetimeIndex):
    SOURCES.mkdir(parents=True, exist_ok=True)
    records = []
    for filename in CHINEXT_SOURCE_FILES:
        url, content = fetch_szse_source(filename)
        target = SOURCES / filename
        target.write_bytes(content)
        text, pairs = parse_pdf_change(content) if filename.endswith(".pdf") else parse_html_change(content)
        try:
            effective = parse_effective_date(text, trading_dates)
        except Exception as exc:
            raise ValueError(f"effective date not found in {filename}: {text[:500]}") from exc
        published_match = re.search(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text[-1200:])
        published = pd.Timestamp(date(*map(int, published_match.groups()))) if published_match else pd.NaT
        if not pairs:
            raise ValueError(f"empty adjustment: {filename}")
        records.append({
            "filename": filename, "url": url, "announcement_date": published,
            "effective_date": effective, "additions": [canonical_member(x) for x, _ in pairs],
            "deletions": [canonical_member(x) for _, x in pairs], "count": len(pairs), "sha256": sha256(target),
        })
    for special in SPECIAL_CHINEXT_CHANGES:
        r = requests.get(special["url"], timeout=45)
        r.raise_for_status()
        target = SOURCES / special["filename"]
        target.write_bytes(r.content)
        records.append({**special, "sha256": sha256(target)})
    current = ak.index_stock_cons("399006")
    members = set(current["品种代码"].astype(str).str.zfill(6).map(canonical_member))
    if len(members) != 100:
        raise ValueError(f"current ChiNext size {len(members)}")
    current.to_csv(OUT / "chinext_current_snapshot.csv", index=False)
    snapshots = []
    reverse_checks = []
    by_effective = {pd.Timestamp(r["effective_date"]): r for r in records}
    candidate = []
    for r in sorted(records, key=lambda x: x["effective_date"]):
        candidate.append({**r, "announcement_date": None if pd.isna(r["announcement_date"]) else str(r["announcement_date"].date()), "effective_date": str(r["effective_date"].date())})
    save_json(OUT / "chinext_adjustments_candidate.json", candidate)
    for effective in sorted(by_effective, reverse=True):
        r = by_effective[effective]
        additions, deletions = set(r["additions"]), set(r["deletions"])
        missing_adds = sorted(additions - members)
        unexpected_deletions = sorted(deletions & members)
        post_size = len(members)
        members = (members - additions) | deletions
        reverse_checks.append({
            "effective_date": effective, "post_size": post_size, "pre_size": len(members),
            "missing_additions_in_post": missing_adds,
            "deletions_already_in_post": unexpected_deletions,
        })
        if len(members) != 100 or missing_adds or unexpected_deletions:
            raise ValueError(f"ChiNext reverse chain failed at {effective.date()}: {reverse_checks[-1]}")
    # Rebuild forward from the membership immediately before the oldest change.
    initial = set(members)
    members = set(initial)
    for d in trading_dates:
        if d in by_effective:
            r = by_effective[d]
            members = (members - set(r["deletions"])) | set(r["additions"])
        snapshots.append({"date": d, "members": sorted(dated_member(c, d) for c in members), "version": max([x for x in by_effective if x <= d], default=pd.NaT)})
    long_rows = [{"date": s["date"], "symbol": c, "version": s["version"]} for s in snapshots for c in s["members"]]
    pd.DataFrame(long_rows).to_parquet(OUT / "chinext_membership_daily.parquet", index=False)
    changes_out = []
    for r in sorted(records, key=lambda x: x["effective_date"]):
        changes_out.append({**r, "announcement_date": None if pd.isna(r["announcement_date"]) else str(r["announcement_date"].date()), "effective_date": str(r["effective_date"].date())})
    save_json(OUT / "chinext_adjustments.json", changes_out)
    save_json(OUT / "chinext_reverse_checks.json", [{**x, "effective_date": str(x["effective_date"].date())} for x in reverse_checks])
    return {s["date"]: tuple(s["members"]) for s in snapshots}, records


def build_csi300_memberships(trading_dates: pd.DatetimeIndex):
    login = bs.login()
    if login.error_code != "0":
        raise RuntimeError(login.error_msg)
    cache = {}
    def query_at(pos: int):
        if pos in cache:
            return cache[pos]
        d = trading_dates[pos]
        frame = bs.query_hs300_stocks(d.strftime("%Y-%m-%d")).get_data()
        if frame.empty:
            raise ValueError(f"no CSI300 membership {d.date()}")
        codes = tuple(sorted(frame["code"].str.split(".").str[-1].str.zfill(6).unique()))
        if len(codes) != 300:
            raise ValueError(f"CSI300 {d.date()} size {len(codes)}")
        cache[pos] = codes
        return codes

    # A monthly-sized probe grid finds changed intervals; binary search then locates
    # the first effective trading day. This avoids thousands of identical downloads.
    probes = sorted(set(list(range(0, len(trading_dates), 20)) + [len(trading_dates) - 1]))
    try:
        for i, pos in enumerate(probes):
            query_at(pos)
            if (i + 1) % 25 == 0:
                print(f"CSI300 probe dates {i + 1}/{len(probes)}", flush=True)
        change_positions = []
        for left, right in zip(probes[:-1], probes[1:]):
            left_set, right_set = query_at(left), query_at(right)
            if left_set == right_set:
                continue
            lo, hi = left + 1, right
            while lo < hi:
                mid = (lo + hi) // 2
                if query_at(mid) == left_set:
                    lo = mid + 1
                else:
                    hi = mid
            change_positions.append(lo)
    finally:
        bs.logout()
    anchors = [0] + sorted(set(change_positions))
    rows = []
    anchor_i = 0
    current = query_at(0)
    for i, d in enumerate(trading_dates):
        if anchor_i + 1 < len(anchors) and i >= anchors[anchor_i + 1]:
            anchor_i += 1
            current = query_at(anchors[anchor_i])
        version = hashlib.sha256("|".join(current).encode()).hexdigest()[:12]
        rows.extend({"date": d, "symbol": c, "version": version} for c in current)
    df = pd.DataFrame(rows)
    df.to_parquet(OUT / "csi300_membership_daily.parquet", index=False)
    save_json(OUT / "csi300_membership_probe_audit.json", {
        "probe_step_trading_days": 20,
        "probe_dates": [str(trading_dates[p].date()) for p in probes],
        "detected_effective_dates": [str(trading_dates[p].date()) for p in change_positions],
        "queries": len(cache),
        "limitation": "If a constituent left and returned within the same 20-trading-day probe interval, endpoint comparison would not detect it.",
    })
    return {d: tuple(g.symbol) for d, g in df.groupby("date")}


def fetch_constituent_prices(symbols: list[str]):
    login = bs.login()
    if login.error_code != "0":
        raise RuntimeError(login.error_msg)
    frames = []
    try:
        for i, symbol in enumerate(sorted(symbols)):
            prefix = "sh" if symbol.startswith("6") else "sz"
            rs = bs.query_history_k_data_plus(
                f"{prefix}.{symbol}", "date,code,close,tradestatus,isST",
                start_date=PRICE_START, end_date=str(END.date()), frequency="d", adjustflag="1",
            )
            frame = rs.get_data()
            if not frame.empty:
                frame["symbol"] = symbol
                frames.append(frame)
            if (i + 1) % 100 == 0:
                print(f"constituent prices {i + 1}/{len(symbols)}", flush=True)
    finally:
        bs.logout()
    out = pd.concat(frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"])
    out["close"] = pd.to_numeric(out["close"], errors="coerce")
    out.loc[out["tradestatus"] != "1", "close"] = np.nan
    out.to_parquet(OUT / "constituent_prices_post_adjusted.parquet", index=False)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d300 = etf_dates("510300")
    dcy = etf_dates("159915")
    all_dates = d300.union(dcy).sort_values()
    chinext = None
    chinext_failure = None
    try:
        chinext, changes = build_chinext_memberships(dcy)
    except Exception as exc:
        chinext_failure = str(exc)
        save_json(OUT / "chinext_chain_failure.json", {"grade": "C", "reason": chinext_failure})
        print(f"ChiNext branch paused: {chinext_failure}", flush=True)
    csi_path = OUT / "csi300_membership_daily.parquet"
    if csi_path.exists():
        csi_df = pd.read_parquet(csi_path)
        csi300 = {pd.Timestamp(d): tuple(g.symbol) for d, g in csi_df.groupby("date")}
        print("using frozen CSI300 membership cache", flush=True)
    else:
        csi300 = build_csi300_memberships(d300)
    # Reuse the already-audited long-history panel. It is a current-list backfill,
    # so missing old constituents lower coverage and keep the result at grade B.
    panel = pd.read_parquet(ALL_A_PANEL).sort_index()
    panel.columns = [str(c).zfill(6) for c in panel.columns]
    panel = panel.loc[(panel.index >= pd.Timestamp(PRICE_START)) & (panel.index <= END)]
    from research_engine import breadth_from_close_panel
    index_jobs = [("csi300", d300, csi300)]
    if chinext:
        index_jobs.append(("chinext", dcy, chinext))
    for name, dates, membership in index_jobs:
        b = breadth_from_close_panel(panel.reindex(panel.index.union(dates)).sort_index(), membership, 0.90)
        b = b.reindex(dates)
        b.to_parquet(OUT / f"breadth_{name}.parquet")
    print("computing all-A breadth", flush=True)
    all_a = panel
    first = all_a.apply(pd.Series.first_valid_index)
    last = all_a.apply(pd.Series.last_valid_index)
    membership = {d: tuple(c for c in all_a.columns if first[c] <= d <= last[c]) for d in all_dates}
    b = breadth_from_close_panel(all_a.reindex(all_a.index.union(all_dates)).sort_index(), membership, 0.90).reindex(all_dates)
    b.to_parquet(OUT / "breadth_all_a.parquet")
    hashes = {}
    for p in [ALL_A_PANEL, OLD / "inputs/actions.json", OLD / "inputs/dated-restrictions.json", OLD / "inputs/bars/sh510300-nominal.csv", OLD / "inputs/bars/sz159915-nominal.csv"]:
        hashes[str(p)] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    for p in sorted(OUT.glob("*.parquet")) + sorted(OUT.glob("*.json")) + sorted(OUT.glob("*.csv")):
        if p.name != "input_fingerprints.json":
            hashes[str(p.relative_to(HERE))] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    save_json(OUT / "input_fingerprints.json", hashes)
    quality = {}
    for name in ["all_a", "csi300"] + (["chinext"] if chinext else []):
        b = pd.read_parquet(OUT / f"breadth_{name}.parquet")
        main_b = b.loc[(b.index >= "2015-01-01") & (b.index <= "2026-06-30")]
        quality[name] = {
            "grade": "B" if name in {"all_a", "csi300"} else "A",
            "rows": len(main_b), "valid_rows": int(main_b.valid.sum()),
            "minimum_coverage": float(main_b.coverage.min()),
            "median_coverage": float(main_b.coverage.median()),
            "first_valid": str(main_b.index[main_b.valid].min().date()),
            "last_valid": str(main_b.index[main_b.valid].max().date()),
        }
    if not chinext:
        quality["chinext"] = {"grade": "C", "reason": chinext_failure, "valid_rows": 0}
    save_json(OUT / "data_quality.json", quality)
    print(json.dumps(quality, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
