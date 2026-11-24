"""Research references in the existing definition registry, never trading signals.

Monthly published returns are attribution inputs, not security characteristics.
Network acquisition is separate from these deterministic offline operators.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from fractions import Fraction

import numpy as np
import pandas as pd

from lei_signal.features.indicators import seeded_ema

REFERENCE_KINDS = {"feature", "factor_return", "model_definition", "method", "case"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_references(registry):
    """Optional additive section; historical registries remain compatible."""
    records = registry.get("research_references", [])
    identities = set()
    objects = {f"{o['id']}@{o['version']}": o for o in registry["objects"]}
    required = {
        "id",
        "version",
        "name",
        "aliases",
        "kind",
        "source",
        "construction",
        "external_id",
        "implementation",
        "market",
        "asset_type",
        "universe",
        "frequency",
        "calendar",
        "currency",
        "unit",
        "inputs",
        "historical_availability",
        "missing_policy",
        "preprocessing",
        "questions",
        "uses",
        "not_for",
        "variant",
        "local_changes",
        "license_status",
        "engineering_status",
        "evidence_status",
    }
    for record in records:
        if required - record.keys() or record["kind"] not in REFERENCE_KINDS:
            raise ValueError("incomplete research reference")
        ref = record["id"] + "@" + record["version"]
        if ref in identities or not re.fullmatch(r"\d+\.\d+\.\d+", record["version"]):
            raise ValueError("duplicate/invalid reference version")
        identities.add(ref)
        if record["variant"] not in {"canonical", "local_variant"}:
            raise ValueError("reference variant required")
        if record["variant"] == "local_variant" and not record["local_changes"]:
            raise ValueError("local changes required")
        if set(record["uses"]) & set(record["not_for"]) or "production_trade" in record["uses"]:
            raise ValueError("conflicting reference uses")
        for target in record.get("object_refs", []):
            if target not in objects:
                raise ValueError("unresolved reference object")
            if record["kind"] in {"feature", "factor_return"}:
                allowed = (
                    {"feature", "state_signal"}
                    if record["kind"] == "feature"
                    else {"factor_return"}
                )
                if objects[target]["type"] not in allowed:
                    raise ValueError("reference/object type mismatch")
    for record in records:
        if any(member not in identities for member in record.get("members", [])):
            raise ValueError("unresolved model member")
    return records


def require_adapter(record, *, purpose, market, frequency, currency):
    if purpose not in record["uses"]:
        raise ValueError("reference does not allow this purpose")
    if (record["market"], record["frequency"], record["currency"]) != (market, frequency, currency):
        raise ValueError("incompatible market/frequency/currency")
    if purpose == "prediction" and record["kind"] != "feature":
        raise ValueError("published realized returns are not prediction features")
    if purpose == "prediction" and record["historical_availability"] == "unknown":
        raise ValueError("historical availability unknown")
    return True


def select_baselines(registry, *, market, frequency, currency, asset_type):
    """Returns explicit inclusion and exclusion reasons, not a silent fallback."""
    selected, excluded = [], []
    for record in validate_references(registry):
        ref = record["id"] + "@" + record["version"]
        try:
            require_adapter(
                record, purpose="comparison", market=market, frequency=frequency, currency=currency
            )
            if record["kind"] != "feature" or record["asset_type"] != asset_type:
                raise ValueError("not a comparable asset feature")
            if not record.get("object_refs") or record["engineering_status"] != "implemented":
                raise ValueError("not implemented")
            selected.append(ref)
        except ValueError as exc:
            excluded.append({"reference": ref, "reason": str(exc)})
    return {"selected": selected, "excluded": excluded}


def parse_french(text, dataset):
    columns = {"ff5": ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"], "mom": ["Mom"]}[dataset]
    rows = list(csv.reader(io.StringIO(text)))
    start = next((i for i, r in enumerate(rows) if [c.strip() for c in r[1:]] == columns), None)
    if start is None:
        raise ValueError("unexpected factor columns/parser version")
    parsed = []
    for row in rows[start + 1 :]:
        if not row or not row[0].strip():
            if parsed:
                break
            continue
        date = row[0].strip()
        if not re.fullmatch(r"\d{6}", date):
            break  # annual block is intentionally excluded
        month = pd.Period(date[:4] + "-" + date[4:], freq="M")
        if len(row) != len(columns) + 1:
            raise ValueError("wrong factor row width")
        values = []
        for value in row[1:]:
            value = value.strip()
            v = float(value) if value else np.nan
            if np.isinf(v):
                raise ValueError("nonfinite return")
            values.append(np.nan if v in {-99.99, -999.0} else v / 100)
        parsed.append([str(month), *values])
    result = pd.DataFrame(parsed, columns=["month", *columns])
    if result.empty or result.month.duplicated().any() or not result.month.is_monotonic_increasing:
        raise ValueError("empty/duplicate/unsorted monthly returns")
    return result


def parse_ch3(frame):
    expected = ["mnthdt", "rf_mon", "mktrf", "SMB", "VMG"]
    if list(frame.columns) != expected:
        raise ValueError("unexpected CH3 columns/parser version")
    result = frame.copy()
    dates = pd.to_datetime(result.mnthdt.astype(str), format="%Y%m%d", errors="raise")
    if not dates.dt.is_month_end.all():
        raise ValueError("CH3 monthly dates must be month-end")
    result.insert(0, "month", dates.dt.to_period("M").astype(str))
    result = result.drop(columns="mnthdt")
    for key in expected[1:]:
        result[key] = pd.to_numeric(result[key], errors="raise")
        result[key] = result[key].mask(result[key].isin([-99.99, -999]))
        if np.isinf(result[key]).any():
            raise ValueError("nonfinite CH3 return")
    if result.empty or result.month.duplicated().any() or not result.month.is_monotonic_increasing:
        raise ValueError("empty/duplicate/unsorted CH3 returns")
    return result  # decimal already; mktrf already subtracts rf_mon


def load_published_returns(snapshot, *, root, market, frequency, currency):
    require_adapter(
        {
            "kind": "factor_return",
            "uses": ["attribution"],
            "historical_availability": "unknown",
            **snapshot,
        },
        purpose="attribution",
        market=market,
        frequency=frequency,
        currency=currency,
    )
    for kind in ("raw", "output"):
        if sha256(root / snapshot[kind + "_path"]) != snapshot[kind + "_sha256"]:
            raise ValueError("snapshot hash mismatch")
    result = pd.read_csv(root / snapshot["output_path"])
    if result.month.duplicated().any() or not result.month.is_monotonic_increasing:
        raise ValueError("snapshot monthly alignment invalid")
    result.attrs["evidence_kind"] = "official_published_returns_not_security_level_replication"
    return result


def local_features(frame, n):
    """Strict corrected SMA boundary; same seeded EMA, no fill of missing quotes."""
    if set(frame.columns) != {"close"}:
        raise ValueError("feature input columns must be exactly close")
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer >=2")
    close = frame.close.astype(float)
    if (close.dropna() <= 0).any() or np.isinf(close).any():
        raise ValueError("prices must be positive finite or missing")
    sma = close.rolling(n, min_periods=n).mean()
    ema = seeded_ema(close, n)
    states = []
    # Exact decimal CSV arithmetic avoids the previously documented equal-price bug.
    fractions = [None if pd.isna(v) else Fraction(str(v)) for v in frame.close]
    for i in range(len(frame)):
        window = fractions[max(0, i - n) : i + 1]
        if len(window) < n + 1 or any(v is None for v in window):
            states.append(pd.NA)
        else:
            states.append(window[-1] * n > sum(window[1:]) and window[-1] > window[0])
    ready = close.notna() & ema.notna() & ema.shift().notna()
    e = ((close > ema) & (ema > ema.shift())).astype("boolean").where(ready)
    returns = close.pct_change(fill_method=None)
    return pd.DataFrame(
        {
            "sma": sma,
            "ema": ema,
            "sma_distance": close / sma - 1,
            "ema_distance": close / ema - 1,
            "S": pd.Series(states, index=frame.index, dtype="boolean"),
            "E": e,
            "hist_return": close / close.shift(n) - 1,
            "volatility": returns.rolling(n, min_periods=n).std(ddof=1),
        }
    )


def time_split(rows, split_date):
    train = (rows.date < split_date) & (rows.label_end < split_date)
    validation = rows.date >= split_date
    return train, validation


def linear_predict(train_x, train_y, test_x):
    """OLS, no parameter search; scaling fitted on training only."""
    mean = train_x.mean(axis=0)
    scale = train_x.std(axis=0)
    scale[scale == 0] = 1
    x = np.column_stack([np.ones(len(train_x)), (train_x - mean) / scale])
    tx = np.column_stack([np.ones(len(test_x)), (test_x - mean) / scale])
    coef = np.linalg.lstsq(x, train_y, rcond=None)[0]
    return tx @ coef
