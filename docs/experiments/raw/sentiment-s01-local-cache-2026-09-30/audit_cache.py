"""Read-only local S&P 500 breadth-cache identity and numerical-lineage audit.

This script never edits files under ~/.lei_signal_lab and never computes returns.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


CACHE = Path("/Users/yongbiaoli/.lei_signal_lab/cache")
ROOT = Path("/Users/yongbiaoli/.lei_signal_lab")
OUT = Path("docs/experiments/raw/sentiment-s01-local-cache-2026-09-30/cache-profile.json")
DATES = ["2008-09-12", "2008-09-15", "2009-03-09", "2020-03-23", "2025-12-31"]


def identity(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def norm_float(value):
    return None if pd.isna(value) else float(value)


def main() -> None:
    json_path = CACHE / "sp500_ma_breadth_history.json"
    price_path = CACHE / "sp500_klines.parquet"
    qfq_path = CACHE / "us_qfq_matrix.parquet"
    timing_path = CACHE / "timing/breadth_sp500.parquet"
    research_path = CACHE / "sentiment_research_2026-09/breadth_raw.json"
    csv_path = CACHE / "sentiment_research_2026-09/breadth_sp500_200dma.csv"
    backdated_universe_path = ROOT / "sp500_backfill_root/fixtures/market_context/universes/SP500.parquet"
    fixture_path = Path("tests/fixtures/market_context/universes/SP500.parquet")
    paths = [json_path, price_path, qfq_path, timing_path, research_path, csv_path, backdated_universe_path, fixture_path]

    readings = json.loads(json_path.read_text())
    widths = pd.DataFrame(readings).set_index("date")
    widths.index = pd.to_datetime(widths.index)
    prices = pd.read_parquet(price_path)
    qfq = pd.read_parquet(qfq_path)
    qfq_current = prices.loc[qfq.index, qfq.columns]
    qfq_values, current_values = qfq.to_numpy(), qfq_current.to_numpy()
    changed = ~((qfq_values == current_values) | (np.isnan(qfq_values) & np.isnan(current_values)))
    changed_date_indexes = np.flatnonzero(changed.any(axis=1))
    timing = pd.read_parquet(timing_path)
    fixture = pd.read_parquet(fixture_path)
    backdated = pd.read_parquet(backdated_universe_path)
    research = json.loads(research_path.read_text())
    comparison = timing.join(
        widths.rename(columns={"breadth_20": "j20", "breadth_50": "j50", "breadth_200": "j200"}),
        how="left",
    )
    cross = {}
    for window in (20, 50, 200):
        a, b = comparison[f"b{window}"], comparison[f"j{window}"]
        both = a.notna() & b.notna()
        diff = (a[both] - b[both]).abs()
        cross[str(window)] = {
            "overlap_nonnull_dates": int(both.sum()),
            "max_absolute_percent_point_difference": norm_float(diff.max()),
            "within_json_4decimal_rounding_tolerance": bool((diff <= 0.000051).all()),
            "dates_beyond_rounding_tolerance": int((diff > 0.000051).sum()),
            "first_beyond_rounding_tolerance": str(diff.index[diff > 0.000051].min().date()) if (diff > 0.000051).any() else None,
            "last_beyond_rounding_tolerance": str(diff.index[diff > 0.000051].max().date()) if (diff > 0.000051).any() else None,
        }

    full_reconstruction = {}
    for window in (20, 50, 200):
        ma = prices.rolling(window).mean()
        eligible = prices.notna() & ma.notna()
        denominator = eligible.sum(axis=1)
        above = ((prices > ma) & eligible).sum(axis=1)
        candidate = (above / denominator.where(denominator > 0) * 100).where(denominator >= 100)
        stored = widths[f"breadth_{window}"]
        candidate = candidate.loc[widths.index]
        both = candidate.notna() & stored.notna()
        diff = (candidate[both] - stored[both]).abs()
        full_reconstruction[str(window)] = {
            "candidate_nonnull_on_json_dates": int(candidate.notna().sum()),
            "stored_nonnull": int(stored.notna().sum()),
            "shared_nonnull": int(both.sum()),
            "null_status_mismatch": int((candidate.notna() != stored.notna()).sum()),
            "dates_beyond_4decimal_rounding_tolerance": int((diff > 0.000051).sum()),
            "max_absolute_percent_point_difference": norm_float(diff.max()),
        }
        del ma, eligible, denominator, above, candidate

    # Only five source-qualification dates; no target or future outcome is loaded.
    forward_filled = prices.ffill()
    samples = []
    for day in DATES:
        date = pd.Timestamp(day)
        close = prices.loc[date]
        row = {"date": day, "json": {key: norm_float(val) for key, val in widths.loc[date].to_dict().items()}}
        row["price_columns"] = int(len(close))
        row["quoted_price_columns"] = int(close.notna().sum())
        row["timing"] = {key: norm_float(val) for key, val in timing.loc[date].to_dict().items()} if date in timing.index else None
        row["recomputed_no_fill"] = {}
        row["recomputed_forward_fill"] = {}
        for window in (20, 50):
            for key, matrix in (("recomputed_no_fill", prices), ("recomputed_forward_fill", forward_filled)):
                history = matrix.loc[:date].tail(window)
                if len(history) != window:
                    row[key][str(window)] = None
                    continue
                ready = history.notna().sum(axis=0) == window
                ma = history.sum(axis=0, min_count=window) / window
                eligible = close.notna() & ready & ma.notna()
                n = int(eligible.sum())
                above = int(((close > ma) & eligible).sum())
                row[key][str(window)] = {
                    "eligible": n,
                    "above": above,
                    "percent": 100.0 * above / n if n else None,
                    "absolute_difference_from_json_pp": abs(100.0 * above / n - widths.loc[date, f"breadth_{window}"]) if n else None,
                }
        samples.append(row)

    con = sqlite3.connect("file:" + str(ROOT / "lab.db") + "?mode=ro", uri=True)
    con.execute("PRAGMA query_only=ON")
    db = pd.read_sql_query(
        "SELECT as_of, breadth_20, breadth_50, breadth_200, universe_version, provenance "
        "FROM market_breadth_snapshots WHERE market_id='SP500' AND universe_version='backfill_v1'",
        con,
    )
    con.close()
    db = db.set_index(pd.to_datetime(db["as_of"]))
    db_cross = {}
    for window in (20, 50, 200):
        joined = db[[f"breadth_{window}"]].join(
            widths[[f"breadth_{window}"]].rename(columns={f"breadth_{window}": "cache"}),
            how="left",
        )
        both = joined[f"breadth_{window}"].notna() & joined["cache"].notna()
        diff = (joined.loc[both, f"breadth_{window}"] - joined.loc[both, "cache"]).abs()
        db_cross[str(window)] = {
            "overlap_nonnull_dates": int(both.sum()),
            "max_absolute_percent_point_difference": norm_float(diff.max()),
        }

    report = {
        "schema": "sentiment-s01-local-cache-profile/1",
        "read_only_external_data": True,
        "no_future_returns_or_market_fits": True,
        "files": [identity(path) for path in paths],
        "json_breadth": {
            "rows": int(len(widths)),
            "first_date": str(widths.index.min().date()),
            "last_date": str(widths.index.max().date()),
            "non_null": {str(window): int(widths[f"breadth_{window}"].notna().sum()) for window in (20, 50, 200)},
        },
        "price_matrix": {
            "rows": int(len(prices)),
            "columns": int(len(prices.columns)),
            "first_date": str(prices.index.min().date()),
            "last_date": str(prices.index.max().date()),
            "columns_also_in_current_fixture": len(set(map(str, prices.columns)) & set(fixture["symbol"].astype(str))),
            "columns_not_in_current_fixture": sorted(set(map(str, prices.columns)) - set(fixture["symbol"].astype(str))),
        },
        "qfq_matrix": {
            "rows": int(len(qfq)),
            "columns": int(len(qfq.columns)),
            "first_date": str(qfq.index.min().date()),
            "last_date": str(qfq.index.max().date()),
            "current_matrix_columns_identical": bool(qfq.columns.equals(prices.columns)),
            "current_matrix_identical_on_qfq_dates": bool(not changed.any()),
            "current_matrix_changed_cells_on_qfq_dates": int(changed.sum()),
            "current_matrix_changed_dates_on_qfq_dates": [str(qfq.index[i].date()) for i in changed_date_indexes],
        },
        "timing_breadth": {
            "rows": int(len(timing)),
            "first_date": str(timing.index.min().date()),
            "last_date": str(timing.index.max().date()),
            "fields": list(timing.columns),
            "compared_to_json": cross,
        },
        "full_reconstruction_from_current_494_column_matrix": full_reconstruction,
        "db_backfill": {
            "rows": int(len(db)),
            "provenance_counts": db["provenance"].fillna("").value_counts().to_dict(),
            "compared_to_json": db_cross,
        },
        "current_fixture": {
            "rows": int(len(fixture)),
            "effective_from_counts": fixture["effective_from"].astype(str).value_counts().to_dict(),
            "source_kind_counts": fixture["source_kind"].astype(str).value_counts().to_dict(),
        },
        "backdated_universe": {
            "rows": int(len(backdated)),
            "effective_from_counts": backdated["effective_from"].astype(str).value_counts().to_dict(),
            "source_counts": backdated["source"].astype(str).value_counts().to_dict(),
        },
        "other_research_json_names": [item.get("name") for item in research],
        "samples": samples,
        "interpretation_boundary": "Numerical duplication and source membership can be audited; none of these checks proves historical S&P 500 membership, first availability, or investable predictive effect.",
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n")
    print(json.dumps({
        "json_rows": report["json_breadth"]["rows"],
        "price_matrix_columns": report["price_matrix"]["columns"],
        "same_current_fixture_columns": report["price_matrix"]["columns_also_in_current_fixture"],
        "timing_comparison": cross,
        "full_reconstruction": full_reconstruction,
        "db_comparison": db_cross,
        "sample_recomputations": [{
            "date": x["date"],
            "quoted_price_columns": x["quoted_price_columns"],
            "recomputed_no_fill": x["recomputed_no_fill"],
            "recomputed_forward_fill": x["recomputed_forward_fill"],
        } for x in samples],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
