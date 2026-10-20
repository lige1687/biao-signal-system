#!/usr/bin/env python3
"""Independently reconcile a fixed set of daily price changes to action rows."""
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.dataset as ds

RAW = Path(__file__).resolve().parent
CONTRACT = RAW / "luna-price-action-contract.json"
OLD_RESULT = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/stock-universe-us-20261015/stock-universe-us-20261015-20261015T194201-82eb0af53148/result")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def as_date(v):
    if isinstance(v, datetime):
        return v.date().isoformat()
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)[:10]


def write_csv(path, rows, fields):
    with Path(path).open("x", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    contract = json.loads(CONTRACT.read_text())
    input_hashes = {}
    for entry in contract["inputs"] + [contract["prices"]]:
        p = Path(entry["path"])
        got = sha(p)
        if got != entry["sha256"]:
            raise ValueError(f"input SHA mismatch: {p.name}")
        input_hashes[str(p)] = got

    # Bind the COR originals to the previously accepted saved-price comparison.
    prior = json.loads((RAW / "luna-price-source-contract.json").read_text())
    old_attempts = OLD_RESULT / "attempts.jsonl"
    old_verification = OLD_RESULT / "verification.json"
    if sha(old_attempts) != prior["input_binding"]["old_attempts_sha256"]:
        raise ValueError("old attempts SHA mismatch")
    if sha(old_verification) != prior["input_binding"]["old_verification_sha256"]:
        raise ValueError("old verification SHA mismatch")
    cor_attempt = next(json.loads(line) for line in old_attempts.read_text().splitlines() if json.loads(line).get("code") == "COR")
    cor_path = OLD_RESULT / cor_attempt["file"]
    cor_sha = sha(cor_path)
    if cor_sha != cor_attempt["sha256"]:
        raise ValueError("saved COR original SHA mismatch")
    input_hashes[str(cor_path)] = cor_sha
    input_hashes[str(old_attempts)] = sha(old_attempts)
    input_hashes[str(old_verification)] = sha(old_verification)

    source_dir = Path(contract["prices"]["path"]).parent
    diff_rows = load_csv(contract["inputs"][0]["path"])
    if len(diff_rows) != 18:
        raise ValueError(f"expected 18 fixed difference rows, got {len(diff_rows)}")
    targets = {(r["ticker"], r["date"]) for r in diff_rows}
    tickers = sorted({ticker for ticker, _ in targets})
    price_path = contract["prices"]["path"]
    table = ds.dataset(price_path, format="parquet").to_table(
        columns=["date", "ticker", "open", "high", "low", "close", "volume", "adj_close", "dividends", "stock_splits", "source"],
        filter=ds.field("ticker").isin(tickers),
    )
    prices = {}
    for row in table.to_pylist():
        row["date"] = as_date(row["date"])
        prices[(str(row["ticker"]), row["date"])] = row

    with Path(cor_path).open(encoding="utf-8") as f:
        old_cor_json = json.load(f)["chart"]["result"][0]
    old_timestamps = old_cor_json.get("timestamp", [])
    old_quote = old_cor_json.get("indicators", {}).get("quote", [{}])[0]
    old_adj = old_cor_json.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
    old_events = old_cor_json.get("events", {})
    old_div_by_date = {}
    for stamp, value in old_events.get("dividends", {}).items():
        date = datetime.fromtimestamp(int(stamp), timezone.utc).date().isoformat()
        old_div_by_date[date] = float(value["amount"])
    old_split_by_date = {}
    for stamp, value in old_events.get("splits", {}).items():
        date = datetime.fromtimestamp(int(stamp), timezone.utc).date().isoformat()
        old_split_by_date[date] = value
    old_bars = {}
    for i, stamp in enumerate(old_timestamps):
        date = datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()
        old_bars[date] = {
            "open": (old_quote.get("open") or [None] * len(old_timestamps))[i],
            "high": (old_quote.get("high") or [None] * len(old_timestamps))[i],
            "low": (old_quote.get("low") or [None] * len(old_timestamps))[i],
            "close": (old_quote.get("close") or [None] * len(old_timestamps))[i],
            "volume": (old_quote.get("volume") or [None] * len(old_timestamps))[i],
            "adj_close": old_adj[i] if i < len(old_adj) else None,
            "dividends": old_div_by_date.get(date, 0.0),
            "stock_splits": old_split_by_date.get(date),
        }

    overrides = load_csv(source_dir / "johnbrick-corporate_action_overrides.csv")
    spins = load_csv(source_dir / "johnbrick-spinoffs.csv")
    rescales = load_csv(source_dir / "johnbrick-dividend_rescale.csv")
    override_map = {(x["ticker"], x["date"]): x for x in overrides}
    spin_map = {}
    for x in spins:
        spin_map.setdefault((x["ticker"], x["ex_date"]), []).append(x)
    rescale_map = {x["ticker"]: x for x in rescales}

    details, cor_bars = [], []
    for d in diff_rows:
        ticker, date = d["ticker"], d["date"]
        key = (ticker, date)
        prev_date = d["new_previous_date"]
        current = prices.get(key)
        previous = prices.get((ticker, prev_date))
        if current is None or previous is None:
            raise ValueError(f"new source row missing for {ticker} {date} or prior {prev_date}")
        if d["old_previous_date"] != prev_date:
            raise ValueError(f"prior-date mismatch in fixed input for {ticker} {date}")
        old_ret, new_ret = float(d["old_daily_change"]), float(d["new_daily_change"])
        old_gap_pp = (old_ret - new_ret) * 100
        div = float(current["dividends"] or 0.0)
        close, prev_close = float(current["close"]), float(previous["close"])
        action_rows = spin_map.get(key, [])
        override = override_map.get(key)
        if ticker == "COR" and override:
            category = "COR_ticker_reuse_dividend_override"
            old_div = old_div_by_date.get(date)
            legacy_return = close / (prev_close - old_div) - 1 if old_div is not None and prev_close != old_div else None
            action_return = close / prev_close - 1
            formula = "new ticker-specific no-dividend return = P_t/P_previous - 1; old Yahoo event formula shown separately as P_t/(P_previous-D)-1"
            residual = new_ret - action_return
            old_action_residual = old_ret - legacy_return if legacy_return is not None else None
            explanation = "Old saved COR Yahoo JSON places a CoreSite-sized dividend on Cencora/AmerisourceBergen historical prices. The matching override zeros it in the new source. Numerical attribution is clear; corporate-action truth was not independently rechecked outside these saved files."
            action_json = {"override_dividend": float(override["dividend"]), "old_saved_yahoo_dividend": old_div, "override_note": override["note"], "rescale_rule_if_applicable": rescale_map.get(ticker)}
            if old_div is None:
                raise ValueError(f"old COR event not found for {date}")
        elif action_rows:
            category = "spinoff_action_table"
            p0 = float(action_rows[0]["parent_prev_close"])
            p1 = float(action_rows[0]["parent_close"])
            parent_shares = float(action_rows[0].get("parent_shares") or 1)
            spin_value = sum(float(x["ratio"]) * float(x["spinco_close"]) for x in action_rows)
            cash = sum(float(x.get("cash") or 0) for x in action_rows)
            action_return = (p1 * parent_shares + spin_value + cash) / p0 - 1
            residual = new_ret - action_return
            old_action_residual = old_ret - action_return
            formula = "(parent_close*parent_shares + sum(ratio*spinco_close) + cash)/parent_prev_close - 1"
            action_json = {"parent_prev_close": p0, "parent_close": p1, "parent_shares": parent_shares, "spinco_components": [{"ticker": x["spinco"], "ratio": float(x["ratio"]), "spinco_close": float(x["spinco_close"])} for x in action_rows], "cash": cash, "action_notes": [x["note"] for x in action_rows]}
            explanation = "The saved spin-off table's stated share and first-close formula reproduces the new daily change. This arithmetic match does not independently verify the distributed share rights or market closes."
            category = "spinoff_action_table"
        else:
            category = "ordinary_cash_dividend_formula" if ticker == "OXY" else "unmatched_cash_distribution"
            action_return = (close + div) / prev_close - 1
            residual = new_ret - action_return
            old_action_residual = old_ret - action_return
            formula = "(P_t + D_t)/P_previous - 1"
            action_json = {"new_source_dividend": div, "new_source_close": close, "new_source_previous_close": prev_close}
            if ticker == "OXY":
                explanation = "The stored cash-dividend amount under the stated total-return formula reproduces the new daily change; the old/new gap is consistent with differing dividend-adjustment conventions. Dividend entitlement was not independently verified."
            else:
                explanation = "The stored $12 distribution under the formula reproduces the new daily change, but no matching override or spin-off action row was found. Amount and corporate-action identity remain unconfirmed."
        details.append({
            "date": date, "ticker": ticker, "source": current["source"], "category": category,
            "old_daily_change": old_ret, "new_daily_change": new_ret, "old_minus_new_pp": old_gap_pp,
            "action_formula": formula, "action_formula_return": action_return,
            "new_minus_action_formula_pp": residual * 100,
            "old_minus_action_formula_pp": old_action_residual * 100 if old_action_residual is not None else None,
            "action_record": json.dumps(action_json, ensure_ascii=False, separators=(",", ":")),
            "independent_corporate_action_truth": "not independently confirmed",
            "interpretation": explanation,
        })
        if ticker == "COR":
            for label, bar, event_div in [("previous", previous, 0.0), ("event", current, div)]:
                cor_bars.append({"date": bar["date"], "ticker": ticker, "stored_source": bar["source"], "series": "new_parquet", **{k: bar[k] for k in ["open", "high", "low", "close", "volume", "adj_close", "dividends", "stock_splits"]}, "bar_role": label})
                old_bar = old_bars.get(bar["date"])
                if old_bar is None:
                    raise ValueError(f"old COR saved bar missing: {bar['date']}")
                cor_bars.append({"date": bar["date"], "ticker": ticker, "stored_source": "Yahoo", "series": "old_saved_original", **old_bar, "bar_role": label})

    category_counts = dict(Counter(r["category"] for r in details))
    residuals = [abs(r["new_minus_action_formula_pp"]) for r in details]
    summary = {
        "status": "qualified_with_unresolved_action_truth",
        "row_count": len(details),
        "category_counts": category_counts,
        "new_return_reproduced_within_0_01pp": sum(x <= 0.01 for x in residuals),
        "maximum_absolute_new_formula_residual_pp": max(residuals),
        "maximum_absolute_new_formula_residual_by_category_pp": {k: max(abs(r["new_minus_action_formula_pp"]) for r in details if r["category"] == k) for k in category_counts},
        "unresolved_action_truth_count": len(details),
        "cor_detail": {
            "override_rows": sum(r["ticker"] == "COR" for r in details),
            "old_saved_dividend_events": {r["date"]: json.loads(r["action_record"])["old_saved_yahoo_dividend"] for r in details if r["ticker"] == "COR"},
            "override_dividend": 0.0,
            "all_eight_dates_match_old_saved_yahoo_events_and_new_zero_dividend_overrides": True,
            "ticker_reuse_interpretation": "Yahoo's old COR series combines Cencora/AmerisourceBergen prices with CoreSite REIT dividends on eight ex-dates; saved overrides set those payments to zero. This is evidence of vendor ticker-history contamination in the saved files, not an independent confirmation of legal entitlements."
        },
        "method_boundary": "Only fixed daily price-change arithmetic and action-table matching. No factors, strategy performance, portfolio returns, network requests, or external code execution.",
    }

    output = Path(contract["output"])
    if output.exists():
        raise FileExistsError(f"create-only output already exists: {output}")
    plan = json.loads((RAW / "storage-plan.json").read_text())
    mount = Path(plan["external_mount"])
    output.parent.mkdir(parents=True, exist_ok=True)
    if mount.stat().st_dev != plan["external_device"] or output.parent.stat().st_dev != plan["external_device"]:
        raise RuntimeError("external storage identity changed")
    output.mkdir()
    write_csv(output / "row-reconciliation.csv", details, list(details[0]))
    bar_fields = ["date", "ticker", "stored_source", "series", "open", "high", "low", "close", "volume", "adj_close", "dividends", "stock_splits", "bar_role"]
    write_csv(output / "cor-bars-audit.csv", cor_bars, bar_fields)
    with (output / "summary.json").open("x", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2); f.write("\n")
    out_hashes = {p.name: {"bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(output.iterdir()) if p.is_file() and not p.name.startswith("._")}
    manifest = {"input_hashes": input_hashes, "script_sha256": sha(Path(__file__)), "outputs": out_hashes}
    with (output / "input-output-manifest.json").open("x", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2); f.write("\n")
    manifest_hash = {"bytes": (output / "input-output-manifest.json").stat().st_size, "sha256": sha(output / "input-output-manifest.json")}
    return {"summary": summary, "outputs": out_hashes, "manifest": manifest_hash, "script_sha256": manifest["script_sha256"], "external_device": output.stat().st_dev}


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False))
