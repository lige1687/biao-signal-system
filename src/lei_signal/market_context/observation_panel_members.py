"""Extend the fixed IVV member correlation with its qualified historical price batch."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from lei_signal.market_context.microstructure_equity import (
    OUTPUT,
    REPO,
    US_SNAPSHOT,
    member_cards,
)

ID = "us-current-members-pairwise-correlation"


def build() -> dict:
    recent = REPO / "docs/ops/microstructure-observations-20261108/constituents/source-ledger.json"
    refs = json.loads(recent.read_text())
    symbols = {ref["symbol"] for ref in refs if ref["qualification"] == "ok"}
    verification = json.loads((US_SNAPSHOT / "verification.json").read_text())
    qualified = {row["code"] for row in verification["rows"] if row["acquisition_status"] == "ok"}
    if len(symbols) != 502 or symbols != qualified:
        raise ValueError("The two price batches do not share the same IVV members")
    prices = {}
    for symbol in sorted(symbols):
        body = json.loads((US_SNAPSHOT / f"{symbol}.json").read_text())["chart"]["result"][0]
        if body["meta"]["symbol"] != symbol:
            raise ValueError(f"Archived quote identity mismatch: {symbol}")
        adj = body["indicators"]["adjclose"][0]["adjclose"]
        points = {}
        for timestamp, value in zip(body["timestamp"], adj, strict=True):
            day = datetime.fromtimestamp(timestamp, UTC).date().isoformat()
            if "2024-11-01" <= day <= "2026-06-30" and value is not None and value > 0:
                points[day] = value
        prices[symbol] = points
    old = member_cards("us", prices, {"files": len(prices)})[1]
    card = next(row for row in json.loads(OUTPUT.read_text())["cards"] if row["id"] == ID)
    # The two price batches have no overlap. Compute each within its own batch
    # and leave the gap unbridged, including the recent batch's 20-day warm-up.
    if old["points"][-1]["date"] >= card["points"][0]["date"]:
        raise ValueError("Price batch dates overlap unexpectedly")
    points = [*old["points"], {"date": "2026-07-01", "value": None}, *card["points"]]
    if sum(row["value"] is not None for row in points) < 252:
        raise ValueError("Not enough valid fixed-member correlations")
    return {
        ID: {
            "frequency": "daily",
            "unit": card["unit"],
            "points": points,
            "note": (
                "同一502只IVV持仓代理股票。历史复权价原件止2026-06-30，新批次始于2026-08-25。"
                "两个批次各自计算21日窗，缺口及新批次预热留空。统计使用最近252个有效观测。"
            ),
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = build()
    with args.output.open("x") as handle:
        json.dump(data, handle, ensure_ascii=False, allow_nan=False)


if __name__ == "__main__":
    main()
