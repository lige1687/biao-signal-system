"""Describe zero-share days in already saved account ledgers; never simulate trades."""

import argparse
import csv
import hashlib
import io
import json
from datetime import date
from pathlib import Path


BASE = Path("docs/experiments/raw/factor-module-a-continuation-2026-09-27")
PAIRED = Path(
    "/Volumes/win+mac通用/LeiSignal-新实验结果/weekly-two-etf-core-account-20261011/"
    "weekly-two-etf-core-account-20261011-20261011T010700-a4081c5d8c11/result/paired-core-account.json"
)
SYMBOLS = ("510300.SS", "510050.SS", "510500.SS", "512100.SS", "159915.SZ", "588000.SS")
POLICIES = ("A_ALL", "A_SMA")


def read_bound_bytes(path):
    raw = path.read_bytes()
    return raw, hashlib.sha256(raw).hexdigest()


def describe(days, zero):
    if len(days) != len(zero) or days != sorted(days) or len(set(days)) != len(days):
        raise ValueError("daily dates missing, unordered, or duplicated")
    spans = []
    start = None
    for index, is_zero in enumerate(zero):
        if is_zero and start is None:
            start = index
        if start is not None and (not is_zero or index == len(days) - 1):
            stop = index if is_zero else index - 1
            spans.append((start, stop))
            start = None
    longest = max(spans, key=lambda pair: (pair[1] - pair[0] + 1, -pair[0])) if spans else None
    return {
        "first_model_day": days[0] if days else None,
        "last_model_day": days[-1] if days else None,
        "model_quote_days": len(days),
        "zero_share_model_days": sum(zero),
        "zero_share_fraction": sum(zero) / len(days) if days else None,
        "zero_share_periods": len(spans),
        "first_zero_share_day": days[spans[0][0]] if spans else None,
        "last_zero_share_day": days[spans[-1][1]] if spans else None,
        "longest_zero_share_run": None if longest is None else {
            "first": days[longest[0]],
            "last": days[longest[1]],
            "model_quote_days": longest[1] - longest[0] + 1,
            "calendar_days_inclusive": (date.fromisoformat(days[longest[1]]) - date.fromisoformat(days[longest[0]])).days + 1,
            "elapsed_calendar_days": (date.fromisoformat(days[longest[1]]) - date.fromisoformat(days[longest[0]])).days,
        },
    }


def old_account(path):
    raw, digest = read_bound_bytes(path)
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    required = {"date", "units", "is_trading_day"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"old saved ledger field mismatch: {path}")
    if len(rows) != 1729 or rows[0]["date"] != "2022-01-01" or rows[-1]["date"] != "2026-09-25":
        raise ValueError(f"old saved ledger date/row mismatch: {path}")
    trading = [r for r in rows if r["is_trading_day"] == "True"]
    if len(trading) != 1147 or any(r["is_trading_day"] not in ("True", "False") for r in rows):
        raise ValueError(f"old model quote-day flag mismatch: {path}")
    result = describe([r["date"] for r in trading], [float(r["units"]) == 0 for r in trading])
    return {"path": str(path), "sha256_readback_now": digest, "bytes": len(raw),
            "all_calendar_rows": len(rows), "share_field": "units", "quote_day_field": "is_trading_day=True", **result}


def new_account(daily, policy):
    if len(daily) != 2790:
        raise ValueError(f"new saved ledger model-day count mismatch: {policy}")
    days = [r["day"] for r in daily]
    shares = [r["account"]["shares"] for r in daily]
    if any(set(s) != {"sh510300", "sz159915"} for s in shares):
        raise ValueError(f"new saved ledger share field mismatch: {policy}")
    return {"policy": policy, "share_field": "account.shares.{sh510300,sz159915}",
            "quote_day_field": "each saved daily entry is a model quote day",
            **describe(days, [all(int(value) == 0 for value in s.values()) for s in shares])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    root = Path(args.repo_root)
    old = {}
    for symbol in SYMBOLS:
        for policy in POLICIES:
            name = f"{symbol}-{policy}-base-daily.csv"
            old[f"{symbol}/{policy}"] = old_account(root / BASE / name)
    raw, digest = read_bound_bytes(PAIRED)
    paired = json.loads(raw)
    if paired.get("core_contract_sha256") != "9a19eb623bbb1dccd7cd3060322317a44dbd6931cb791c718a6210edddd360be":
        raise ValueError("new saved account core contract mismatch")
    newer = {policy: new_account(paired["results"][policy]["account"]["daily"], policy)
             for policy in ("P0", "P1")}
    print(json.dumps({"schema_version": 1,
                      "definition": "End-of-saved-model-day holdings are exactly zero shares; cash, pending orders and receivables do not change this share-only flag. Only quote/model days enter counts. Consecutive runs use adjacent saved model dates; calendar inclusive/elapsed durations describe endpoints and include non-quote days, not extra quote-day observations.",
                      "old_six_etf_base_fee_accounts": old,
                      "new_two_etf": {"path": str(PAIRED), "sha256_readback_now": digest,
                                      "bytes": len(raw), "accounts": newer},
                      "account_replays": 0,
                      "scientific_runs": 0}, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
