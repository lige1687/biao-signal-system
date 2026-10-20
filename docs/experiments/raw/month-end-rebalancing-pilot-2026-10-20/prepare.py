"""Qualify fields and dates without inspecting the research event outcomes."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    plan = json.loads((HERE / "storage-plan.json").read_text())
    out = Path(plan["output"])
    assert out.stat().st_dev == plan["external_device"]
    frames, records = {}, {}
    for symbol in ("SPY", "IEF"):
        path = out / f"{symbol}.json"
        expected = next(r["sha256"] for r in json.loads((HERE / "acquisition.json").read_text())
                        if r["name"] == path.name)
        assert sha(path) == expected
        data = json.loads(path.read_text())["chart"]["result"][0]
        assert data["meta"]["currency"] == "USD"
        assert data["meta"]["exchangeTimezoneName"] == "America/New_York"
        assert not data.get("events", {}).get("splits")
        ix = pd.to_datetime(data["timestamp"], unit="s", utc=True).tz_convert(
            "America/New_York").tz_localize(None).normalize()
        df = pd.DataFrame(data["indicators"]["quote"][0], index=ix)
        df["adjusted_close"] = data["indicators"]["adjclose"][0]["adjclose"]
        df["dividend"] = 0.0
        assert ix.is_unique and ix.is_monotonic_increasing
        assert np.isfinite(df.to_numpy()).all()
        assert (df[["open", "high", "low", "close", "adjusted_close"]] > 0).all().all()
        assert ((df["high"] >= df[["open", "close", "low"]].max(axis=1)) &
                (df["low"] <= df[["open", "close", "high"]].min(axis=1))).all()
        for event in data.get("events", {}).get("dividends", {}).values():
            date = pd.Timestamp(event["date"], unit="s", tz="UTC").tz_convert(
                "America/New_York").tz_localize(None).normalize()
            assert date in ix and event["amount"] >= 0
            df.loc[date, "dividend"] += event["amount"]
        frames[symbol] = df.add_prefix(symbol + "_")
        records[symbol] = {
            "raw_path": str(path), "sha256": expected, "rows": len(df),
            "first": str(ix[0].date()), "last": str(ix[-1].date()),
            "dividends": int((df["dividend"] > 0).sum()), "splits": 0,
            "missing_fields": 0, "nonpositive_ohlc": 0, "duplicate_dates": 0,
        }
    start = max(f.index.min() for f in frames.values())
    end = min(f.index.max() for f in frames.values())
    frames = {s: f.loc[start:end] for s, f in frames.items()}
    assert frames["SPY"].index.equals(frames["IEF"].index), "asymmetric missing dates"
    panel = pd.concat(frames.values(), axis=1)
    target = out / "qualified-panel.csv"
    assert not target.exists()
    panel.to_csv(target, index_label="date", float_format="%.15g")
    qualification = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "outcome_values_used_for_design": False,
        "inputs": records, "panel_path": str(target), "panel_sha256": sha(target),
        "common_rows": len(panel), "common_start": str(start.date()),
        "common_end": str(end.date()), "asymmetric_missing_dates": 0,
        "planned_event_months": len(pd.period_range("2003-01", "2026-09", freq="M")),
        "complete_month_policy": "next-month quotes present; observed shared quote calendar",
        "qualification": "limited_retrospective",
        "limits": [
            "Current vendor history, original historical arrival and revisions unavailable",
            "No independent full exchange-calendar or daily quote audit",
            "Dividend ex-dates from vendor; pay-date cash availability not modeled",
            "SPY/IEF cash ETFs, not original ES/TY futures; inception chosen retrospectively",
            "Adjusted close is sensitivity input, never assumed actual fill price",
        ],
    }
    (HERE / "qualification.json").write_text(json.dumps(qualification, ensure_ascii=False, indent=2))
    print(json.dumps(qualification, ensure_ascii=False))


if __name__ == "__main__":
    main()
