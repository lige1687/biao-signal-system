"""Offline observation export; no network, strategy changes or return experiments.

Input version is pinned by the previous independent audit. Output is a dated
observation snapshot, not an automatically maintained feed. Re-running requires
explicit paths; source caches and historical audit files are never written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

NAMES = {"512480": "半导体ETF", "515880": "通信ETF", "159915": "创业板ETF", "510300": "沪深300ETF"}


def rank(s: pd.Series) -> pd.Series:
    # Matches the reviewed Trae short-window definition, including today's close.
    return s.rolling(60, min_periods=36).rank(pct=True) * 100


def compute(bars: pd.DataFrame, market: pd.Series, benchmark: pd.Series | None) -> pd.DataFrame:
    """Backward-only formulas, same-date denominators, no missing-data filling."""
    if not bars.index.is_unique or not bars.index.is_monotonic_increasing:
        raise ValueError("duplicate or unordered input dates")
    c, amount, turn = (bars[k] for k in ("close", "amount", "turnover"))
    m = market.reindex(bars.index)
    bt = benchmark.reindex(bars.index) if benchmark is not None else turn.rolling(250, min_periods=120).mean()
    if m.isna().any() or (benchmark is not None and bt.isna().any()):
        raise ValueError("same-date denominator missing; refresh the qualified input first")
    if not np.isfinite(bars[["close", "amount", "turnover"]]).all().all() or (c <= 0).any() or (m <= 0).any():
        raise ValueError("invalid price, turnover or market amount")
    share = amount / m
    relative = (turn / bt).replace([np.inf, -np.inf], np.nan)
    surge = turn.rolling(5).mean() / turn.rolling(60).mean()
    crowd_parts = pd.concat([rank(share), rank(relative), rank(surge)], axis=1)
    activity = crowd_parts.mean(axis=1)
    ema20, ema60, ema120 = (c.ewm(span=n, adjust=False).mean() for n in (20, 60, 120))
    delta = c.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rsi = (100 - 100 / (1 + up / down.replace(0, np.nan))).where(down > 0, 100.0).where(down.notna())
    momentum = pd.concat([rank(c / ema20 - 1), rsi], axis=1).mean(axis=1)
    ret = c.pct_change(fill_method=None)
    rv = ret.rolling(10).std() / ret.rolling(60).std().replace(0, np.nan)
    ua = amount.where(ret > 0, 0.0).rolling(20).sum()
    da = amount.where(ret < 0, 0.0).rolling(20).sum()
    un = (ret > 0).astype(float).rolling(20).sum().clip(lower=1)
    dn = (ret < 0).astype(float).rolling(20).sum().clip(lower=1)
    ud = (ua / un) / (da / dn).replace(0, np.nan)
    volatility = pd.concat([rank(rv), rank(ud)], axis=1).mean(axis=1)
    trend = rank(((ema20 - ema60) / ema60 + (ema60 - ema120) / ema120) / 2)
    raw = .35 * activity + .25 * momentum + .20 * volatility + .20 * trend
    heat = raw.ewm(span=5, adjust=False).mean()
    # Keep original EMA initialization for comparability, but hide observations
    # until every short-window input is available. A missing input is not zero.
    ready = crowd_parts.notna().all(axis=1) & rank(rv).notna() & rank(ud).notna() & trend.notna() & rsi.notna()
    heat = heat.where(ready)
    peak = heat.rolling(20).max()
    drop = peak - heat
    high = c.ge(c.rolling(20).max()).astype("boolean").where(c.rolling(20).count().ge(20))
    divergence = (high & peak.ge(75) & drop.ge(10)).where(peak.notna() & high.notna())
    return pd.DataFrame({"price": c, "heat": heat, "activity": activity.where(ready),
        "amountSharePct": share * 100, "relativeTurnover": relative, "turnoverSurge": surge,
        "heatPeak20": peak, "heatDrop20": drop, "priceHigh20": high, "divergence": divergence})


def value(v):
    if pd.isna(v):
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return round(float(v), 6)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text())
    fingerprints = {}
    for code in [*NAMES, "_market_amount"]:
        p = args.cache / f"{code}.csv"
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if audit["source_sha256"].get(str(p)) != sha:
            raise ValueError(f"input version changed since audit: {code}")
        fingerprints[str(p)] = sha

    def read(code):
        x = pd.read_csv(args.cache / f"{code}.csv", parse_dates=["date"]).set_index("date")
        return x.loc["2017-09-28":"2026-11-08"]

    market, benchmark = read("_market_amount").amount, read("510300").turnover
    cards, checks = [], {}
    for code, name in NAMES.items():
        bars = read(code)
        bt = benchmark if code != "510300" else None
        frame = compute(bars, market, bt)
        old_heat = audit["etfs"][code]["latest_sentiment"]["sent_short"]
        assert abs(frame.heat.iloc[-1] - old_heat) < 1e-9
        # Appending later dates must never alter the prefix already available.
        for stop in (400, 1000):
            pd.testing.assert_frame_equal(frame.iloc[:stop], compute(bars.iloc[:stop], market, bt))
        p = frame.loc["2019-01-01":]
        rows = [{"date": d.strftime("%Y-%m-%d"), **{k: value(v) for k, v in row.items()}} for d, row in p.iterrows()]
        stats = audit["etfs"][code]["divergence"]
        cards.append({"symbol": code, "name": name, "kind": "sector" if code in ("512480", "515880") else "index",
            "turnoverComparison": "ETF换手率 ÷ 沪深300ETF同日换手率" if bt is not None else "自身换手率 ÷ 自身250日均值（至少120日）",
            "points": rows, "research": {"matureDays": stats["mature_days"], "spacedEvents": stats["spaced20_events"],
                "mean20": stats["mean20"] * 100, "otherHighMean20": stats["other_20d_high_mean20"] * 100,
                "spacedMean20": stats["spaced20_mean"] * 100}})
        checks[code] = {"rows": len(p), "first": rows[0]["date"], "last": rows[-1]["date"],
            "firstCompleteHeat": str(frame.heat.first_valid_index().date()), "latest": rows[-1],
            "prefixChecks": [400, 1000], "auditLatestHeatDifference": float(frame.heat.iloc[-1] - old_heat)}

    # A missing denominator must stop the build rather than silently ffill.
    try:
        compute(read("512480"), market.drop(market.index[-1]), benchmark)
    except ValueError:
        checks["missingDenominatorRejected"] = True
    else:
        raise AssertionError("missing denominator was accepted")
    payload = {"schemaVersion": 1, "generatedAt": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
        "snapshotAsOf": max(c["points"][-1]["date"] for c in cards),
        "sourceLabel": "本地行情历史缓存（采集器含东方财富、BaoStock来源）",
        "sourceNote": "逐行供应商及复权链尚未完整复核；按标注日期观察，未自动按日更新。",
        "priceNote": "价格沿用缓存调整序列，适合对照走势；绝对价格与分红复权口径待完整复核。",
        "cards": cards}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    for path, sha in fingerprints.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha
    evidence = {"inputSha256": fingerprints, "outputSha256": hashlib.sha256(args.out.read_bytes()).hexdigest(),
        "checks": checks, "notes": ["no new performance experiment", "historical performance copied from prior audit", "warmup hidden until all inputs are available", "same-date joins without filling"]}
    args.evidence.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False))
    print(json.dumps({"output": str(args.out), "bytes": args.out.stat().st_size, "checked": list(checks)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
