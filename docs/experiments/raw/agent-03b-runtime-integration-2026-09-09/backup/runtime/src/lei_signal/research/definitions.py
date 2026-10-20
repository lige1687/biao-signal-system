"""Versioned research definitions. No production consumers and no order execution.

The JSON registry is the single hand-maintained definition source. Profiles are
expanded by resolve(); formulas are documentation, never evaluated as code.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "docs/research/definitions.v1.json"
TYPES = {"feature", "state_signal", "factor_return", "risk_metric", "benchmark", "policy/strategy"}
VERSION = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
USES = {"description", "ranking", "research_signal", "attribution", "comparison", "diagnostic"}
REQUIRED = {
    "id",
    "version",
    "name",
    "type",
    "uses",
    "not_for",
    "scope",
    "definition",
    "input",
    "universe",
    "time",
    "dependencies",
    "validation",
    "status",
    "sources",
}
SECTIONS = {
    "definition": {"formula", "parameters", "endpoints", "unit", "direction", "transforms"},
    "input": {"fields", "price_basis", "currency", "frequency", "calendar"},
    "universe": {"version", "eligibility", "warmup", "missing", "quality_gate", "degrade"},
    "time": {
        "observation_time",
        "available_at",
        "decision_at",
        "execution_at",
        "timezone",
        "effective_from",
    },
    "validation": {"method", "tolerance", "tests", "limitations"},
    "status": {
        "definition_clarity",
        "data_qualification",
        "implementation",
        "effectiveness",
        "production",
    },
}


def load_registry(path=REGISTRY):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_registry(data)
    return data


def _expand(registry, obj):
    profile = obj.get("profile")
    if profile is not None and profile not in registry["profiles"]:
        raise ValueError(f"unknown profile: {profile}")
    card = deepcopy(registry["profiles"].get(profile, {}))
    for key, value in obj.items():
        # Exactly one profile, one-level field overrides; no implicit version aliases.
        if isinstance(value, dict) and isinstance(card.get(key), dict):
            card[key].update(deepcopy(value))
        else:
            card[key] = deepcopy(value)
    return card


def validate_registry(registry):
    if registry.get("schema_version") != "1.0.0" or not VERSION.fullmatch(
        registry.get("version", "")
    ):
        raise ValueError("unsupported registry version")
    standard = registry.get("standard", "")
    if (
        registry.get("standard_version") != "1.0.0"
        or not isinstance(standard, str)
        or Path(standard).is_absolute()
        or ".." in Path(standard).parts
        or not (ROOT / standard).is_file()
    ):
        raise ValueError("missing or unsupported definition standard")
    for name, kind in {"profiles": dict, "sources": dict, "objects": list, "models": list}.items():
        if not isinstance(registry.get(name), kind):
            raise ValueError(f"invalid registry section: {name}")
    for source in registry["sources"].values():
        if not isinstance(source, dict) or set(source) != {"path", "sha256"}:
            raise ValueError("source requires path and sha256")
        p, digest = source["path"], source["sha256"]
        if (
            not isinstance(p, str)
            or not p
            or Path(p).is_absolute()
            or ".." in Path(p).parts
            or not isinstance(digest, str)
            or not re.fullmatch("[a-f0-9]{64}", digest)
        ):
            raise ValueError("invalid source path/hash")
    cards = {}
    for obj in registry.get("objects", []):
        c = _expand(registry, obj)
        if REQUIRED - c.keys():
            raise ValueError(f"missing required fields: {REQUIRED - c.keys()}")
        for field in ("id", "version", "name", "type", "scope"):
            if not isinstance(c[field], str) or not c[field].strip():
                raise ValueError(f"nonempty string required: {field}")
        for field in ("uses", "not_for", "dependencies", "sources"):
            if (
                not isinstance(c[field], list)
                or any(not isinstance(v, str) or not v for v in c[field])
                or len(c[field]) != len(set(c[field]))
            ):
                raise ValueError(f"unique string list required: {field}")
        if not re.fullmatch(r"[a-z][a-z0-9_.-]+", c["id"]) or not VERSION.fullmatch(c["version"]):
            raise ValueError("invalid identity/version")
        ref = c["id"] + "@" + c["version"]
        if ref in cards:
            raise ValueError(f"duplicate identity: {ref}")
        if c["type"] not in TYPES or not c["uses"] or not set(c["uses"]) <= USES:
            raise ValueError(f"invalid type/use: {ref}")
        if set(c["uses"]) & set(c["not_for"]):
            raise ValueError(f"conflicting uses: {ref}")
        for section, required in SECTIONS.items():
            if not isinstance(c[section], dict) or required - c[section].keys():
                raise ValueError(f"incomplete {section}: {ref}")
            if any(c[section][k] is None or c[section][k] == "" for k in required):
                raise ValueError(f"empty {section}: {ref}")
        if c["status"]["production"] != "not_authorized":
            raise ValueError("this research registry grants no production authority")
        fields = c["input"]["fields"]
        if (
            not isinstance(fields, list)
            or not fields
            or any(not isinstance(v, str) or not v for v in fields)
            or len(fields) != len(set(fields))
        ):
            raise ValueError("input fields must be unique strings")
        if not isinstance(c["definition"]["parameters"], dict):
            raise ValueError("parameters must be an explicit object, possibly empty")
        tol = c["validation"]["tolerance"]
        if (
            not isinstance(tol, dict)
            or set(tol) != {"absolute", "relative", "integer"}
            or any(
                not isinstance(v, (int, float))
                or isinstance(v, bool)
                or not np.isfinite(v)
                or v < 0
                for v in tol.values()
            )
        ):
            raise ValueError("tolerances must be finite and nonnegative")
        if not isinstance(c["validation"]["tests"], list) or not c["validation"]["tests"]:
            raise ValueError("explicit validation tests/evidence paths required")
        try:
            ZoneInfo(c["time"]["timezone"])
        except (ZoneInfoNotFoundError, TypeError, ValueError) as exc:
            raise ValueError("invalid timezone") from exc
        if (
            not isinstance(c["dependencies"], list)
            or not isinstance(c["sources"], list)
            or not c["sources"]
        ):
            raise ValueError("dependencies/sources must be explicit lists")
        for source in c["sources"]:
            if source not in registry["sources"]:
                raise ValueError(f"unknown source: {source}")
        if c["type"] in {"benchmark", "policy/strategy"}:
            required = {
                "selection",
                "weights",
                "cash",
                "fees",
                "rebalance",
                "execution",
                "exit",
                "reentry",
                "investability",
            }
            if required - c.get("policy", {}).keys():
                raise ValueError(f"incomplete policy: {ref}")
            if any(
                not isinstance(c["policy"][k], str) or not c["policy"][k].strip() for k in required
            ):
                raise ValueError(f"empty or malformed policy: {ref}")
        cards[ref] = c
    if not cards:
        raise ValueError("empty registry")
    visited, active = set(), set()

    def visit(ref):
        if ref not in cards:
            raise ValueError(f"unresolved dependency/version: {ref}")
        if ref in active:
            raise ValueError(f"cyclic dependency: {ref}")
        if ref in visited:
            return
        active.add(ref)
        for dep in cards[ref]["dependencies"]:
            visit(dep)
        active.remove(ref)
        visited.add(ref)

    for ref in cards:
        visit(ref)
    for model in registry.get("models", []):
        required = {
            "id",
            "version",
            "dependent_return",
            "factor_returns",
            "form",
            "frequency",
            "window",
            "risk_free",
            "currency",
            "missing_alignment",
            "estimation",
            "uncertainty",
            "status",
        }
        if required - model.keys() or not VERSION.fullmatch(model["version"]):
            raise ValueError("incomplete model card")
        for ref in [model["dependent_return"], *model["factor_returns"]]:
            if ref not in cards or cards[ref]["type"] not in {"factor_return", "benchmark"}:
                raise ValueError("model requires a registered return series, not a breadth level")
    return cards


def resolve(registry, reference, purpose=None):
    cards = validate_registry(registry)
    if reference not in cards:
        raise ValueError(f"unknown exact definition version: {reference}")
    card = cards[reference]
    if purpose is not None and purpose not in card["uses"]:
        raise ValueError(f"{purpose} not allowed for {reference}")
    return card


def _valid_price(series):
    s = series.astype(float)
    if not s.index.is_unique or not s.index.is_monotonic_increasing:
        raise ValueError("quotes require unique increasing observation dates")
    q = s.dropna()
    if ((q <= 0) | ~np.isfinite(q)).any():
        raise ValueError("prices must be finite and positive; missing must be explicit NaN")
    return q


def historical_percentile(series, window=756, minimum=252):
    if not 1 <= minimum <= window:
        raise ValueError("invalid percentile window")
    if not np.isfinite(series.dropna()).all():
        raise ValueError("percentile requires finite values or explicit missing")

    # Independent expression of pandas average-rank, including current value.
    def rank(a):
        if np.isnan(a[-1]):
            return np.nan
        v = a[~np.isnan(a)]
        return (np.sum(v < a[-1]) + (np.sum(v == a[-1]) + 1) / 2) / len(v)

    return series.rolling(window, min_periods=minimum).apply(rank, raw=True)


def realized_volatility(series, window=20):
    q = _valid_price(series)
    return (
        q.pct_change(fill_method=None)
        .rolling(window, min_periods=window)
        .std(ddof=1)
        .mul(np.sqrt(252))
        .reindex(series.index)
    )


def trend_state(price, mean):
    original = price.index
    price = _valid_price(price)
    mean = mean.reindex(price.index)
    valid = price.notna() & mean.notna()
    above = (price > mean).astype(float).where(valid)
    previous_valid = valid.shift(1, fill_value=False)
    cross = ((price > mean) & (price.shift(1) <= mean.shift(1))).astype(float)
    return pd.DataFrame(
        {
            "above": above,
            "cross_up": cross.where(valid & previous_valid),
            "recovered": (price >= mean).astype(float).where(valid),
        }
    ).reindex(original)


def quote_features(series):
    q = _valid_price(series)
    r = pd.DataFrame(index=q.index)
    r["momentum"] = q.shift(21) / q.shift(252) - 1
    r["valid_count"] = np.arange(1, len(q) + 1)
    for n in (50, 200):
        mean = q.rolling(n, min_periods=n).mean()
        state = trend_state(q, mean)
        r[f"sma{n}"] = mean
        r[f"distance{n}"] = q / mean - 1
        r[f"above{n}"] = state.above
        r[f"cross_up{n}"] = state.cross_up
        r[f"recovered{n}"] = state.recovered
    r["rv20"] = realized_volatility(q)
    r["rv_rank"] = historical_percentile(r.rv20)
    return r.reindex(series.index)


def select_mixed(momentum, rv_rank, valid_count, *, current_quotes):
    candidates = [
        s
        for s in momentum
        if s in current_quotes and valid_count.get(s, 0) >= 273 and np.isfinite(momentum[s])
    ]
    ranked = sorted(candidates, key=lambda s: (-momentum[s], s))
    return [s for s in ranked if pd.isna(rv_rank.get(s, np.nan)) or rv_rank[s] < 0.8][:3]


def equal_targets(selected, allocation=1.0):
    if not 0 <= allocation <= 1 or len(selected) != len(set(selected)):
        raise ValueError("invalid allocation or duplicate selection")
    return {s: allocation / len(selected) for s in selected} if selected else {}


def economic_index(series, events):
    """Signal index; dividends here are not spendable account cash.

    Contract requires timestamped event availability. Historical files lacking it
    cannot be certified point-in-time by this function.
    """
    q = _valid_price(series)
    if not isinstance(q.index, pd.DatetimeIndex):
        raise ValueError("corporate actions require dated observations")
    local_days = (
        q.index.tz_convert("Asia/Shanghai").tz_localize(None) if q.index.tz is not None else q.index
    ).normalize()
    ids = [a["event_id"] for a in events]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate event id")
    values, level = [], 1.0
    for i, (_day, price) in enumerate(q.items()):
        if i:
            actions = sorted(
                (
                    a
                    for a in events
                    if local_days[i - 1] < pd.Timestamp(a["effective_date"]) <= local_days[i]
                ),
                key=lambda a: (a["effective_date"], a["event_id"]),
            )
            mult, cash = 1.0, 0.0
            for a in reversed(actions):
                known = pd.Timestamp(a["available_at"])
                obs = local_days[i].tz_localize("Asia/Shanghai") + pd.Timedelta(hours=15)
                if known.tzinfo is None or known > obs:
                    raise ValueError("event not available at observation time")
                if a["type"] == "split":
                    ratio = float(a["ratio"])
                    if not np.isfinite(ratio) or ratio <= 0:
                        raise ValueError("invalid split ratio")
                    mult *= ratio
                    cash *= ratio
                elif a["type"] == "cash_dividend":
                    amount = float(a["cash"])
                    if not np.isfinite(amount) or amount < 0:
                        raise ValueError("invalid cash dividend")
                    cash += amount
                else:
                    raise ValueError("unsupported economic action")
            level *= (price * mult + cash) / q.iloc[i - 1]
        values.append(level)
    return pd.Series(values, index=q.index, name="economic_index", dtype=float).reindex(
        series.index
    )


def breadth(close, membership_by_date, minimum_coverage=0.9):
    if not 0 <= minimum_coverage <= 1 or not close.index.is_unique or not close.columns.is_unique:
        raise ValueError("invalid coverage or duplicate observations")
    if not close.index.is_monotonic_increasing:
        raise ValueError("breadth calendar must be increasing")
    means = {}
    for s in close:
        q = _valid_price(close[s])
        means[s] = {n: q.rolling(n, min_periods=n).mean().reindex(close.index) for n in (50, 200)}
    rows = []
    for day in close.index:
        members = list(dict.fromkeys(membership_by_date.get(day, ())))
        eligible, quoted = [], 0
        for s in members:
            if s in close and pd.notna(close.at[day, s]):
                quoted += 1
                if pd.notna(means[s][200].at[day]):
                    eligible.append(s)
        total, count = len(members), len(eligible)
        coverage = count / total if total else np.nan
        reason = (
            "membership_missing"
            if not total
            else "no_eligible_quotes"
            if not count
            else "coverage_below_minimum"
            if coverage < minimum_coverage
            else None
        )
        row = dict(
            date=day,
            pool_total=total,
            quoted=quoted,
            eligible=count,
            coverage=coverage,
            missing_reason=reason,
            valid=reason is None,
        )
        for n in (50, 200):
            row[f"b{n}"] = (
                sum(close.at[day, s] > means[s][n].at[day] for s in eligible) / count
                if reason is None
                else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows).set_index("date")


def breadth_delta(series, lag=20, unit="fraction"):
    if unit not in {"fraction", "percent"} or lag < 1:
        raise ValueError("invalid unit or lag")
    limit = 1 if unit == "fraction" else 100
    if ((series.dropna() < 0) | (series.dropna() > limit)).any():
        raise ValueError("breadth outside declared unit")
    return series - series.shift(lag)


def three_tier(value):
    if pd.isna(value):
        return np.nan
    if not 0 <= value <= 1:
        raise ValueError("expected breadth fraction, not percent")
    return 1.0 if value < 0.433 else 0.5 if value < 0.567 else 0.0


def concentration(market_values, equity, groups, denominator="account"):
    vals = np.array(list(market_values.values()), dtype=float)
    if not np.isfinite(equity) or equity <= 0 or not np.isfinite(vals).all() or (vals < 0).any():
        raise ValueError("invalid long-only account")
    if vals.sum() > equity + 1e-8 or denominator not in {"account", "invested"}:
        raise ValueError("exposure or denominator invalid")
    if set(groups) != set(market_values) or any(
        not isinstance(g, str) or not g for g in groups.values()
    ):
        raise ValueError("each product needs exactly one mutually exclusive group")
    base = equity if denominator == "account" else vals.sum()
    if base == 0:
        raise ValueError("no invested assets")
    weights = {s: v / base for s, v in market_values.items()}
    combined = {}
    for s, w in weights.items():
        combined[groups[s]] = combined.get(groups[s], 0) + w
    return dict(product_weights=weights, group_weights=combined, exposure=vals.sum() / equity)


def fingerprint(path):
    p = Path(path).resolve()
    try:
        name = p.relative_to(ROOT).as_posix()
    except ValueError:
        name = str(p)
    return {"path": name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def verify_sources(registry, root=ROOT):
    """Explicit IO check, separate from cheap structural resolution; fail on drift."""
    for source in registry["sources"].values():
        p = Path(root) / source["path"]
        if not p.is_file() or fingerprint(p)["sha256"] != source["sha256"]:
            raise ValueError(f"changed or missing source: {source['path']}")
    return len(registry["sources"])


def calculate(reference, prices, *, registry=None, membership=None):
    """Small identity-bound interface for integrated examples, not a policy engine.

    Registered but unsupported/legacy policies deliberately have no evaluator.
    Parameter changes require an explicit implementation update, never a new label
    pasted onto the old algorithm. Per-file metadata avoids repeating cards per row.
    """
    reg = load_registry() if registry is None else registry
    card = resolve(reg, reference)
    parameters = card["definition"]["parameters"]
    identity = card["id"]
    if identity == "mixed.momentum.raw":
        if parameters != {"long_lag": 252, "skip_lag": 21}:
            raise ValueError("implementation binding differs from registered parameters")
        values = quote_features(prices).momentum
    elif identity in {"trend.sma50", "trend.sma200"}:
        n = int(identity.removeprefix("trend.sma"))
        if parameters != {"window": n, "min_periods": n}:
            raise ValueError("implementation binding differs from registered parameters")
        values = quote_features(prices)[f"sma{n}"]
    elif identity.startswith("breadth.") and identity.endswith(".common"):
        n = 50 if ".b50." in identity else 200
        if parameters != {
            "window": n,
            "eligible_window": 200,
            "minimum_coverage": 0.9,
            "strict_above": True,
        }:
            raise ValueError("implementation binding differs from registered parameters")
        if membership is None:
            raise ValueError("explicit dated membership required")
        values = breadth(prices, membership)
    else:
        raise ValueError("no integrated implementation for this identity; mapped legacy only")
    return dict(
        reference=reference,
        unit=card["definition"]["unit"],
        values=values,
        missing_reason="See per-day missing_reason for breadth; quote warmup/missing is NaN",
        production_authorization="not_authorized",
    )


def make_manifest(
    *,
    registry,
    references,
    code_files,
    input_files,
    data_cutoff,
    available_at,
    decision_at,
    protocol,
    pool_version,
    quality,
):
    times = [pd.Timestamp(t) for t in (data_cutoff, available_at, decision_at)]
    if any(t.tzinfo is None for t in times) or not times[0] <= times[1] <= times[2]:
        raise ValueError("data must be available before decision, with explicit timezone")
    if not references or not code_files or not input_files or not pool_version or not quality:
        raise ValueError("manifest needs identities, code, inputs, pool and quality")
    cards = validate_registry(registry)
    closure = set()

    def add(ref):
        resolve(registry, ref)
        if ref in closure:
            return
        closure.add(ref)
        for dep in cards[ref]["dependencies"]:
            add(dep)

    for ref in references:
        add(ref)
    if json.loads(REGISTRY.read_text()) != registry:
        raise ValueError("persist a versioned registry before emitting a manifest")
    return dict(
        principles_version="1.0.0",
        definition_standard_version=registry["standard_version"],
        registry_version=registry["version"],
        registry_file=fingerprint(REGISTRY),
        standard_file=fingerprint(ROOT / registry["standard"]),
        registry_canonical_sha256=hashlib.sha256(
            json.dumps(registry, sort_keys=True).encode()
        ).hexdigest(),
        definition_refs=references,
        dependency_closure=sorted(closure),
        codes=[fingerprint(p) for p in code_files],
        inputs=[fingerprint(p) for p in input_files],
        data_cutoff=data_cutoff,
        available_at=available_at,
        decision_at=decision_at,
        protocol=fingerprint(protocol),
        pool_version=pool_version,
        quality=quality,
        production_authorization="not_authorized",
    )
