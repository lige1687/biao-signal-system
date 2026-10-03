"""Check five prespecified historical input windows. No forward outcomes or fitting."""
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
DATES = ["2008-09-12", "2008-09-15", "2009-03-09", "2020-03-23", "2025-12-31"]
CACHE = Path("/Users/yongbiaoli/.lei_signal_lab/cache/sp500_klines.parquet")


def main():
    snapshots = list(csv.DictReader((BASE / "inputs/fja-sp500-historical-components.csv").open()))
    frozen_cache = BASE / "inputs/local-prespecified-window-prices.parquet"
    local = pd.read_parquet(frozen_cache if frozen_cache.exists() else CACHE)
    calendar = local.index[(local["AAPL"].notna()) & (local["AAPL"] > 0)]
    archive = zipfile.ZipFile(BASE / "inputs/boris-stooq-2017.zip")
    files = {x.filename[7:-7].upper(): x for x in archive.infolist()
             if x.filename.startswith("Stocks/") and x.filename.endswith(".us.txt")}
    public_frames = {}
    memberships = {d: max((x for x in snapshots if x["date"] <= d), key=lambda x: x["date"])
                   for d in DATES}
    needed = set().union(*(set(x["tickers"].split(",")) for x in memberships.values()))
    for symbol in sorted(needed & files.keys()):
        data = archive.read(files[symbol])
        if not data:
            public_frames[symbol] = None
            continue
        frame = pd.read_csv(io.BytesIO(data), usecols=["Date", "Close"], parse_dates=["Date"])
        if frame.empty:
            public_frames[symbol] = None
            continue
        public_frames[symbol] = frame.set_index("Date")["Close"]
    fnspid = {}
    for symbol in ("AGN", "ALTR"):
        frame = pd.read_csv(BASE / "inputs" / f"fnspid-{symbol}-sample.csv", usecols=["date", "adj close"], parse_dates=["date"])
        fnspid[symbol] = frame.set_index("date")["adj close"]

    def check(series, required):
        if series is None or series.empty:
            return "no_rows"
        if series.index.has_duplicates:
            return "duplicate_dates"
        values = series.reindex(required)
        if values.isna().any():
            return "missing_required_quote_dates"
        if not np.isfinite(values).all() or (values <= 0).any():
            return "invalid_price"
        return "complete_50_quote_window_identity_unverified"

    results, details = [], []
    for date in DATES:
        required = calendar[calendar <= date][-50:]
        assert len(required) == 50 and str(required[-1].date()) == date
        members = sorted(set(memberships[date]["tickers"].split(",")))
        counters = {source: 0 for source in ("local", "stooq2017", "fnspid_selected", "union")}
        missing = []
        for symbol in members:
            statuses = {
                "local": check(local[symbol] if symbol in local else None, required),
                "stooq2017": check(public_frames.get(symbol), required),
                "fnspid_selected": check(fnspid.get(symbol), required),
            }
            complete = [source for source, status in statuses.items() if status.startswith("complete_")]
            for source in complete:
                counters[source] += 1
            counters["union"] += bool(complete)
            if not complete:
                missing.append(symbol)
            details.append({"date": date, "ticker": symbol, "statuses": statuses,
                            "source_priority_if_later_identity_audited": complete[0] if complete else None})
        results.append({"date": date, "membership_snapshot": memberships[date]["date"],
                        "members": len(members), "window_begin": str(required[0].date()),
                        "window_end": date, "complete_50_date_windows_identity_unverified": counters,
                        "no_complete_name_matched_window": len(missing), "missing_tickers": missing})
        print(date, len(members), counters, "missing", len(missing))
    payload = {"stage": "input_availability_only", "identity_qualified": False,
               "calendar_basis": "50 observed AAPL quote dates in read-only local cache ending on each fixed date",
               "caution": "Complete quote window does not prove the security is the historical member. FNSPID AGN matches Watson price, not old Allergan; fja old aliases may collapse entities. Stooq archive stops2017; no prospective breadth or return effects computed.",
               "results": results, "details": details}
    (BASE / "actual-50day-window-coverage.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
