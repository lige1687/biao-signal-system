"""Identity-bound batch calculation for the small factor library v0.

One batch builder over the frozen mixed-pool inputs; every output column traces
to an exact ``id@version`` card. The strict point-in-time corporate-action
contract in :mod:`lei_signal.research.definitions` is deliberately not weakened:
historical files without ``available_at`` timestamps go through an explicitly
labelled reconstruction branch only.

No production consumers, no order execution.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .definitions import quote_features, resolve

MIXED_PRICE_IDENTITIES = {"mixed.", "trend.", "cash."}

# Exact parameter bindings: changing a registered window/threshold/formula must
# break construction rather than silently run the old algorithm under a new card.
BINDINGS: dict[str, dict] = {
    "mixed.price.economic@1.0.0": {
        "params_check": lambda p: p.get("base") == 1
        and "reverse" in p.get("event_order", "")
        and "event_id" in p.get("event_order", ""),
        "formula_must_contain": ["nominal_close*split_multiplier+cash_equivalent"],
    },
    "mixed.asset.total_return@1.0.0": {
        "params": {"gross": True, "fees": 0, "base_currency": "CNY"},
        "formula_must_contain": ["I_i(t)/I_i(prev)-1"],
    },
    "cash.zero@1.0.0": {"params": {"annual_rate": 0}, "formula_must_contain": ["r_cash(t)=0"]},
    "mixed.momentum.raw@1.0.0": {
        "params": {"long_lag": 252, "skip_lag": 21},
        "formula_must_contain": ["I(t-21)/I(t-252)-1"],
    },
    "mixed.rv20@1.0.0": {
        "params": {"window": 20, "ddof": 1, "annualization": 252},
        "formula_must_contain": ["sqrt(252)"],
    },
    "mixed.rv_percentile@1.0.0": {
        "params": {"window": 756, "minimum": 252, "include_current": True, "ties": "average"},
        "formula_must_contain": ["average_rank"],
    },
    "mixed.volatility_allowed@1.0.0": {
        "params": {"exclude_at_or_above": 0.8, "nan": "pass_legacy"},
        "formula_must_contain": ["rv_percentile<0.8"],
    },
    "mixed.eligible@1.0.0": {
        "params": {"minimum_quotes": 273},
        "formula_must_contain": ["273"],
    },
    "mixed.momentum.rank@1.0.0": {
        "params": {"ties": "exact equality then symbol ascending"},
        "formula_must_contain": ["(-score,symbol)"],
    },
    "mixed.top3@1.0.0": {
        "params": {
            "n": 3,
            "fewer": "全部取用",
            "none": "空名单",
            "duplicate_direction": "full14允许相关方向重复",
        },
        "formula_must_contain": ["first3"],
    },
    "mixed.target.equal@1.0.0": {
        "params_check": lambda p: isinstance(p.get("allocation"), list) and 1 in p["allocation"],
        "formula_must_contain": ["allocation/len(selected)"],
    },
    "trend.sma200@1.0.0": {
        "params": {"window": 200, "min_periods": 200},
        "formula_must_contain": ["200"],
    },
    "trend.distance200@1.0.0": {
        "params": {"window": 200},
        "formula_must_contain": ["P_signal/SMA200-1"],
    },
    "trend.above200@1.0.0": {
        "params": {"equal": False},
        "formula_must_contain": ["P_signal>SMA200"],
    },
}

CONTRACT_FIELDS = [
    ("definition", ("formula", "parameters", "endpoints", "unit", "transforms")),
    ("input", ("fields", "price_basis", "currency", "frequency", "calendar")),
    ("universe", ("eligibility", "warmup", "missing", "quality_gate")),
    ("time", ("observation_time", "available_at", "decision_at", "execution_at", "timezone")),
]

EXCLUDE_RV = 0.8
MINIMUM_QUOTES = 273
TOP_N = 3


@dataclass(frozen=True)
class FactorBatch:
    values: pd.DataFrame  # date, symbol, economic_index, total_return, prev_quote_date,
    #                       momentum, rv20, rv_rank, valid_count, sma200, distance200, above200
    missing: pd.DataFrame  # date, symbol, field, reason (abnormal rows only)
    metadata: dict  # refs, input identity, calculation binding, units, quality


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()


def contract_digest(card: dict) -> str:
    contract = {"id": card["id"], "version": card["version"]}
    for section, fields in CONTRACT_FIELDS:
        block = card.get(section, {})
        contract[section] = {k: block.get(k) for k in fields if k in block}
    contract["dependencies"] = card.get("dependencies", [])
    return hashlib.sha256(_canon(contract)).hexdigest()


def bound_reference(reference: str, *, registry: dict) -> dict:
    """Resolve a card and verify this module's executable binding still matches."""
    if not reference.startswith(("mixed.", "trend.", "cash.")):
        raise ValueError(f"{reference} is not a mixed-pool binding")
    try:
        card = resolve(registry, reference)
    except ValueError as exc:
        raise ValueError(f"unknown exact definition: {reference}") from exc
    binding = BINDINGS.get(reference)
    if binding is None:
        raise ValueError(f"no executable binding in factor_runtime for {reference}")
    params = card["definition"]["parameters"]
    if "params" in binding and params != binding["params"]:
        raise ValueError(f"binding differs from registered parameters for {reference}: {params}")
    if "params_check" in binding and not binding["params_check"](params):
        raise ValueError(f"binding differs from registered parameters for {reference}: {params}")
    formula = card["definition"]["formula"]
    for needle in binding["formula_must_contain"]:
        if needle not in formula:
            raise ValueError(f"binding differs from registered formula for {reference}")
    return card


def _all_bindings(registry: dict) -> dict:
    out = {}
    for ref in BINDINGS:
        card = bound_reference(ref, registry=registry)
        out[ref] = {"contract_digest": contract_digest(card), "unit": card["definition"]["unit"]}
    return out


def _normalize_symbol(value) -> str:
    s = str(value).split(".")[0].replace("sh", "").replace("sz", "")
    if len(s) != 6 or not s.isdigit():
        raise ValueError(f"not a 6-digit product symbol: {value!r}")
    return s


def _normalized_actions(actions: list[dict]) -> list[dict]:
    out = []
    for a in actions:
        typ = a.get("type") or a.get("action_type")
        if typ not in {"split", "cash_dividend"}:
            continue
        sym = _normalize_symbol(a["symbol"])
        eff = a.get("effective_date") or a.get("ex_date")
        event_id = a.get("event_id") or f"{sym}:{typ}:{eff}"
        if typ == "split":
            ratio = float(a.get("ratio", a.get("split_ratio", 1)))
            if not np.isfinite(ratio) or ratio <= 0:
                raise ValueError(f"invalid split ratio for {event_id}")
            out.append(
                dict(event_id=event_id, symbol=sym, type=typ, effective_date=eff, ratio=ratio)
            )
        else:
            cash = float(a.get("cash", a.get("cash_per_share", a.get("cash_per_unit", 0))) or 0)
            if not np.isfinite(cash) or cash < 0:
                raise ValueError(f"invalid dividend cash for {event_id}")
            out.append(dict(event_id=event_id, symbol=sym, type=typ, effective_date=eff, cash=cash))
    return out


def reconstructed_economic_index(
    series: pd.Series, events: list[dict]
) -> tuple[pd.Series, list[str]]:
    """Historical rebuild of the registered mixed.price.economic chain.

    Same interval/reverse-merge arithmetic as the strict contract, but timestamps
    cannot be invented: every event lacking ``available_at`` is reported back so
    callers label the run ``historical_reconstruction_only``.
    """
    q = series.astype(float)
    if not q.index.is_unique or not q.index.is_monotonic_increasing:
        raise ValueError("quotes require unique increasing observation dates")
    q = q.dropna()
    if (q <= 0).any() or ~np.isfinite(q).all():
        raise ValueError("prices must be finite and positive")
    ids = [a["event_id"] for a in events]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate event id")
    unknown = sorted(
        {
            a["event_id"]
            for a in events
            if not a.get("available_at") and a["type"] in {"split", "cash_dividend"}
        }
    )
    days = q.index.normalize() if isinstance(q.index, pd.DatetimeIndex) else pd.to_datetime(q.index)
    values, level = [], 1.0
    prev = None
    for i, (day, price) in enumerate(zip(days, q.to_numpy(), strict=False)):
        if prev is not None:
            between = sorted(
                (
                    a
                    for a in events
                    if days[i - 1] < pd.Timestamp(a["effective_date"]) <= day
                ),
                key=lambda a: (a["effective_date"], a["event_id"]),
            )
            mult, cash = 1.0, 0.0
            for a in reversed(between):
                if a["type"] == "split":
                    mult *= float(a["ratio"])
                    cash *= float(a["ratio"])
                else:
                    cash += float(a["cash"])
            level *= (float(price) * mult + cash) / float(prev)
        values.append(level)
        prev = price
    return pd.Series(values, index=q.index, name="economic_index"), unknown


def _input_fingerprint(prices: pd.DataFrame, actions: list[dict]) -> str:
    payload = {
        "prices": prices[["date", "symbol", "open", "high", "low", "close", "volume"]]
        .sort_values(["date", "symbol"])
        .to_dict("records"),
        "actions": actions,
    }
    return hashlib.sha256(_canon(payload)).hexdigest()


def build_mixed_batch(
    prices: pd.DataFrame,
    actions: list[dict],
    *,
    registry: dict,
    input_identity: dict,
) -> FactorBatch:
    if input_identity.get("currency") != "CNY":
        raise ValueError("mixed-pool bindings require currency=CNY nominal inputs")
    if input_identity.get("price_basis") != "nominal_close":
        raise ValueError("mixed-pool bindings require nominal_close price_basis")
    if input_identity.get("kind") == "breadth_fraction":
        raise ValueError("a breadth level in [0,1] is not a nominal price series")
    if not input_identity.get("historical_reconstruction_only"):
        raise ValueError(
            "mixed actions lack available_at; reconstruction must be labelled explicitly"
        )

    bindings = _all_bindings(registry)
    norm_actions = _normalized_actions(actions)
    unknown_events = sorted(
        {a["event_id"] for a in actions if not a.get("available_at")}
        & {a["event_id"] for a in norm_actions}
    )

    required = {"date", "symbol", "open", "high", "low", "close", "volume"}
    if not required <= set(prices.columns):
        raise ValueError(f"prices frame lacks columns: {required - set(prices.columns)}")
    frame = prices.copy()
    frame["symbol"] = frame.symbol.map(_normalize_symbol)
    if frame.duplicated(["date", "symbol"]).any():
        raise ValueError("duplicate date/symbol rows")
    frame["date"] = frame.date.astype(str)

    rows = []
    missing_rows = []
    for sym, g in frame.groupby("symbol"):
        g = g.sort_values("date")
        close = g.set_index("date")["close"].astype(float)
        valid = close[close.notna() & np.isfinite(close) & (close > 0)]
        for day, price in close.items():
            if pd.isna(price):
                reason = "missing_quote"
            elif not np.isfinite(price):
                reason = "nonfinite_quote"
            elif price <= 0:
                reason = "nonpositive_quote"
            else:
                continue
            missing_rows.append(dict(date=day, symbol=sym, field="close", reason=reason))
        if valid.empty:
            missing_rows.append(
                dict(date=None, symbol=sym, field="close", reason="no_valid_quotes")
            )
            continue
        idx, unknown = reconstructed_economic_index(
            valid.rename_axis(None),
            [a for a in norm_actions if a["symbol"] == sym],
        )
        unknown_events = sorted(set(unknown_events) | set(unknown))
        feats = quote_features(idx)
        part = pd.DataFrame(
            {
                "date": idx.index,
                "symbol": sym,
                "economic_index": idx.to_numpy(),
                "total_return": idx.pct_change(fill_method=None).to_numpy(),
                "prev_quote_date": pd.Series(idx.index, index=idx.index).shift(1).to_numpy(),
                "momentum": feats.momentum.to_numpy(),
                "rv20": feats.rv20.to_numpy(),
                "rv_rank": feats.rv_rank.to_numpy(),
                "valid_count": feats.valid_count.to_numpy(),
                "sma200": feats.sma200.to_numpy(),
                "distance200": feats.distance200.to_numpy(),
                "above200": feats.above200.to_numpy(),
            }
        )
        part["prev_quote_date"] = part.prev_quote_date.map(
            lambda x: None if pd.isna(x) else pd.Timestamp(x).strftime("%Y-%m-%d")
        )
        rows.append(part)

    values = (
        pd.concat(rows, ignore_index=True)
        .sort_values(["date", "symbol"])
        .reset_index(drop=True)
        if rows
        else pd.DataFrame()
    )
    missing = pd.DataFrame(missing_rows, columns=["date", "symbol", "field", "reason"])
    nan_rv_pass = int(
        ((values.rv_rank.isna()) & (values.valid_count >= MINIMUM_QUOTES)).sum() if rows else 0
    )
    metadata = {
        "bindings": bindings,
        "input_identity": input_identity,
        "input_fingerprint": _input_fingerprint(frame, actions),
        "calculation": {
            "mixed.price.economic@1.0.0": (
                "reconstructed_economic_index (nominal close, reverse-merged actions)"
            ),
            "mixed.asset.total_return@1.0.0": "economic_index.pct_change across own valid quotes",
            "mixed.momentum.raw@1.0.0": "definitions.quote_features(economic_index).momentum",
            "mixed.rv20@1.0.0": "definitions.realized_volatility via quote_features",
            "mixed.rv_percentile@1.0.0": "definitions.historical_percentile via quote_features",
            "trend.sma200@1.0.0": "definitions.quote_features(economic_index).sma200",
        },
        "units": {
            "economic_index": "index_level",
            "momentum": "fraction",
            "total_return": "fraction_per_valid_quote_interval",
            "rv20": "annualized_fraction",
            "rv_rank": "fraction",
            "valid_count": "count_of_own_valid_quotes",
            "sma200": "index_level",
            "distance200": "fraction",
            "above200": "boolean",
        },
        "quality": {
            "mode": "historical_reconstruction_only",
            "events_without_available_at": unknown_events,
            "nan_rv_rank_pass_count_through_batch": nan_rv_pass,
            "point_in_time_availability": (
                "not certified; do not label these values as historically "
                "tradable at observation time"
            ),
        },
    }
    return FactorBatch(values=values, missing=missing, metadata=metadata)


def _snapshot(values: pd.DataFrame, day: str, symbols: list[str]) -> dict:
    todays = values[values.date == day].set_index("symbol")
    snap = {}
    for s in symbols:
        if s in todays.index:
            row = todays.loc[s]
            row = row.iloc[0] if isinstance(row, pd.DataFrame) else row
            snap[s] = row
    return snap


def monthly_decisions(
    batch: FactorBatch,
    *,
    variant: str,
    completed_months: list[str],
    symbols: list[str],
) -> pd.DataFrame:
    if variant not in {"E00", "E01", "E10", "E11"}:
        raise ValueError(f"unknown variant: {variant}")
    rank_top3 = variant in {"E10", "E11"}
    volatility_filter = variant in {"E01", "E11"}
    values = batch.values
    rows = []
    for day in completed_months:
        snap = _snapshot(values, day, symbols)
        eligible = [
            s
            for s in symbols
            if s in snap
            and int(snap[s].valid_count) >= MINIMUM_QUOTES
            and np.isfinite(snap[s].momentum)
        ]
        ranked = sorted(eligible, key=lambda s: (-float(snap[s].momentum), s))
        exclusions = {}
        if volatility_filter:
            kept = []
            for s in ranked:
                rv = snap[s].rv_rank
                if pd.isna(rv):
                    kept.append(s)
                elif float(rv) >= EXCLUDE_RV:
                    exclusions[s] = "rv_percentile_at_or_above_0.8"
                else:
                    kept.append(s)
            filtered = kept
        else:
            filtered = list(ranked)
        if rank_top3:
            selected_list = filtered[:TOP_N]
            ranked_out = filtered if volatility_filter else ranked
        else:
            selected_list = sorted(filtered)
            ranked_out = filtered if volatility_filter else sorted(ranked)
        scores = {
            s: (
                None
                if s not in snap or not np.isfinite(snap[s].momentum)
                else float(snap[s].momentum)
            )
            for s in symbols
        }
        weights = {s: (1.0 / len(selected_list) if s in selected_list else 0.0) for s in symbols}
        rows.append(
            dict(
                decision_date=day,
                selected="|".join(selected_list),
                ranked="|".join(ranked_out),
                scores=json.dumps(scores, ensure_ascii=False),
                weights=json.dumps(weights, ensure_ascii=False),
                exclusion_reasons=json.dumps(exclusions, ensure_ascii=False),
            )
        )
    return pd.DataFrame(rows)
