"""Rebuild display-only observations from explicit, read-only input snapshots.

No network calls, price repairs, forward fills, signals, or trade rules.
Usage: python3 export_snapshot.py --cache-root /path/to/.sentiment_cache
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = REPO / "web/public/research/relative-market-observations-20261108/data.json"
START = "2024-01-01"
END = "2026-11-06"


def read_prices(path: Path, json_input: bool = False) -> dict[str, float]:
    rows = json.loads(path.read_text()) if json_input else list(csv.DictReader(path.open()))
    result = {}
    for row in rows:
        day = row.get("date", row.get("day"))
        date.fromisoformat(day)
        if day < START or day > END:
            continue
        value = float(row.get("close", row.get("value")))
        if day in result or not math.isfinite(value) or value <= 0:
            raise ValueError(f"Duplicate or invalid price: {path.name} {day}")
        result[day] = value
    return dict(sorted(result.items()))


def build_points(numerator: dict[str, float], denominator: dict[str, float]):
    # Same market's common close dates only; do not borrow a preceding price.
    days = sorted(numerator.keys() & denominator.keys())
    assert len(days) >= 120
    ratios = [numerator[d] / denominator[d] for d in days]
    return [dict(date=d, ratio=ratios[i], numerator=numerator[d], denominator=denominator[d],
                 ma60=math.fsum(ratios[i - 59:i + 1]) / 60 if i >= 59 else None)
            for i, d in enumerate(days)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-root", type=Path, required=True)
    args = parser.parse_args()
    files = {
        "512100": HERE / "512100-sina-raw.json", "510300": HERE / "510300-sina-raw-v2.json",
        **{x: args.cache_root / "us" / f"{x}.csv" for x in ("SMH", "QQQ", "RSP", "SPY")},
        **{x: args.cache_root / "cboe" / f"{x}.csv" for x in ("VIX", "VIX3M")},
    }
    values = {symbol: read_prices(path, symbol in ("512100", "510300")) for symbol, path in files.items()}
    price_note = "收盘价格比，不含现金分红再投资。除息也会影响比值；历史从2024年开始，避开此前已知份额折算。"
    specs = [
        ("cn-style-relative", "cn", "relative", "大小盘 · 中证1000 / 沪深300", "512100", "中证1000ETF", "510300", "沪深300ETF"),
        ("vix-term-structure", "us", "term", "VIX · 期限结构", "VIX", "30天隐含波动率", "VIX3M", "3个月隐含波动率"),
        ("us-semiconductor-relative", "us", "relative", "半导体 / 纳指100", "SMH", "半导体ETF", "QQQ", "纳指100ETF"),
        ("us-equal-weight-relative", "us", "relative", "标普500 · 等权 / 市值加权", "RSP", "标普500等权ETF", "SPY", "标普500市值加权ETF"),
    ]
    cards = []
    checks = []
    for identity, market, kind, title, num, num_label, den, den_label in specs:
        points = build_points(values[num], values[den])
        assert points[-1]["date"] == END
        if kind == "term":
            sources = [{"name": f"Cboe · {x}历史", "url": f"https://cdn.cboe.com/api/global/us_indices/daily_prices/{x}_History.csv"} for x in (num, den)]
            note = "两条指数均为年化隐含波动率。同一美股收盘日的VIX除以VIX3M；1倍表示两个期限相同。"
        else:
            sources = [{"name": f"新浪行情 · {x}", "url": f"https://finance.sina.com.cn/realstock/company/sh{x}/nc.shtml" if market == "cn" else f"https://stock.finance.sina.com.cn/usstock/quotes/{x}.html"} for x in (num, den)]
            note = price_note
            # A large isolated gap needs source review; never repair with future prices.
            for symbol in (num, den):
                sequence = list(values[symbol].values())
                assert max(abs(b / a - 1) for a, b in zip(sequence, sequence[1:])) < .35, symbol
        cards.append(dict(id=identity, market=market, kind=kind, title=title,
                          numerator=dict(symbol=num, label=num_label), denominator=dict(symbol=den, label=den_label),
                          sources=sources, price_note=note, points=points))
        old, latest = points[-21], points[-1]
        checks.append(dict(id=identity, count=len(points), start=points[0]["date"], end=latest["date"],
                           value=latest["ratio"], prior_date=old["date"], change20_pct=(latest["ratio"] / old["ratio"] - 1) * 100,
                           dropped_num_dates=len(values[num]) - len(points), dropped_den_dates=len(values[den]) - len(points)))
    snapshot = dict(schema_version=1, imported_at=datetime.now(timezone.utc).isoformat(), refresh_mode="snapshot", cards=cards)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n")
    manifest = dict(output=str(OUT), output_sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(),
                    checks=checks, inputs={k: dict(path=str(v), sha256=hashlib.sha256(v.read_bytes()).hexdigest()) for k, v in files.items()},
                    qualification="Current-vintage display snapshot, no historical point-in-time or total-return claim.",
                    acquisition="CN prices fetched from Sina CN_MarketData.getKLineData, scale=240, datalen=1023. US and Cboe reused Trae caches; no Trae cleanup functions executed.")
    (HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
