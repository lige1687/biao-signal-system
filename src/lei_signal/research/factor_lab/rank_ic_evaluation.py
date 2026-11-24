"""Frozen, purpose-aware RankIC evaluation for factors and saved model scores.

This research boundary does not fit models, select features, flip directions, or
change production rules. Future labels are accepted only as a separate sidecar.
The numeric correlation delegates to the existing factor-lab diagnostics backend.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RankICScore:
    name: str
    column: str
    kind: Literal["raw_factor", "model_score"]
    direction: Literal["higher_score_higher_label", "lower_score_higher_label"]
    definition_reference: str = ""


@dataclass(frozen=True)
class RankICUniverse:
    name: str
    asset_type: str
    assets: tuple[str, ...]


@dataclass(frozen=True)
class RankICCheckpoint:
    at: str
    fold: str


@dataclass(frozen=True)
class RankICLabelWindow:
    checkpoint: str
    universe: str
    start: str
    end: str
    sessions: tuple[str, ...]
    start_session_offset: int
    end_session_offset: int
    calendar_reference: str
    session_sequence_sha256: str


@dataclass(frozen=True)
class RankICModelFold:
    fold: str
    train_start: str
    train_end: str
    training_labels_end: str
    transform_fit_end: str
    evaluation_start: str
    evaluation_end: str
    model_identity: str
    transform_identity: str


@dataclass(frozen=True)
class RankICRealBinding:
    study_reference: str
    score_frame_sha256: str
    label_frame_sha256: str
    qualification_reference: str
    frozen_protocol_reference: str
    approval_reference: str
    qualification_sha256: str
    frozen_protocol_sha256: str
    approval_sha256: str
    prior_result_sealed: bool = False
    frozen_addendum_reference: str = ""
    frozen_addendum_sha256: str = ""


@dataclass(frozen=True)
class RankICColumns:
    asset: str = "asset_id"
    asset_type: str = "asset_type"
    checkpoint: str = "checkpoint_at"
    computed_through: str = "computed_through_at"
    source_available: str = "source_available_at"
    label_asset: str = "asset_id"
    label_checkpoint: str = "checkpoint_at"
    label_value: str = "forward_return"
    label_start: str = "label_start_at"
    label_end: str = "label_end_at"
    label_available: str = "label_available_at"
    label_quality: str = "label_quality_valid"


@dataclass(frozen=True)
class RankICContract:
    contract_id: str
    data_mode: Literal["synthetic", "historical_reconstruction", "qualified"]
    purpose: Literal["return_ranking", "risk_ranking", "trend_switch", "entry_trigger"]
    label_semantics: Literal["higher_return", "higher_risk"]
    scores: tuple[RankICScore, ...]
    universes: tuple[RankICUniverse, ...]
    checkpoints: tuple[RankICCheckpoint, ...]
    window_start: str
    window_end: str
    evaluation_as_of: str
    temporal_basis: Literal["timestamp", "session_date_after_close"]
    availability_context: Literal["strict_point_in_time", "retrospective_after_close"]
    min_assets: int
    score_mask_policy: Literal["common", "per_score"]
    time_weighting: Literal["equal_checkpoint", "equal_fold_then_checkpoint"]
    label_horizon: str
    label_overlap: Literal["overlapping", "nonoverlapping", "unknown"]
    label_horizon_session_intervals: int
    label_windows: tuple[RankICLabelWindow, ...] = ()
    model_folds: tuple[RankICModelFold, ...] = ()
    real_binding: RankICRealBinding | None = None
    source_evidence: str = ""
    after_close_scenario: str = ""
    market_timezone: str = "Asia/Shanghai"
    columns: RankICColumns = RankICColumns()


@dataclass
class RankICEvaluation:
    metadata: dict
    periodic: pd.DataFrame
    summary: pd.DataFrame
    exclusions: pd.DataFrame


def _temporal(value: object, basis: str, field: str) -> pd.Timestamp:
    result = pd.Timestamp(value)
    if pd.isna(result):
        raise ValueError(f"{field} must not be missing")
    if basis == "timestamp":
        if result.tzinfo is None:
            raise ValueError(f"{field} must have an explicit timezone")
        return result.tz_convert("UTC")
    if result.tzinfo is not None or result != result.normalize():
        raise ValueError(f"{field} must be a session date, not a timestamp")
    return result


def _optional_times(series: pd.Series, basis: str, field: str) -> pd.Series:
    return series.map(lambda x: pd.NaT if pd.isna(x) else _temporal(x, basis, field))


def _validate_contract(c: RankICContract) -> dict[str, pd.Timestamp]:
    choices = {
        "data_mode": {"synthetic", "historical_reconstruction", "qualified"},
        "purpose": {"return_ranking", "risk_ranking", "trend_switch", "entry_trigger"},
        "label_semantics": {"higher_return", "higher_risk"},
        "temporal_basis": {"timestamp", "session_date_after_close"},
        "availability_context": {"strict_point_in_time", "retrospective_after_close"},
        "score_mask_policy": {"common", "per_score"},
        "time_weighting": {"equal_checkpoint", "equal_fold_then_checkpoint"},
        "label_overlap": {"overlapping", "nonoverlapping", "unknown"},
    }
    for field, allowed in choices.items():
        if getattr(c, field) not in allowed:
            raise ValueError(f"unsupported {field}")
    if (
        not c.contract_id
        or not c.label_horizon
        or (not isinstance(c.min_assets, int) or isinstance(c.min_assets, bool) or c.min_assets < 3)
    ):
        raise ValueError(
            "contract ID, label horizon and min_assets >= 3 (existing backend floor) are required"
        )
    if not c.scores or not c.universes or not c.checkpoints:
        raise ValueError("scores, universes and checkpoints must be frozen and nonempty")
    if c.purpose == "return_ranking" and c.label_semantics != "higher_return":
        raise ValueError("return ranking requires higher-return labels")
    if c.purpose == "risk_ranking" and c.label_semantics != "higher_risk":
        raise ValueError("risk ranking requires explicit higher-risk labels")
    if c.purpose != "risk_ranking" and c.label_semantics == "higher_risk":
        raise ValueError("risk labels are permitted only for explicit risk-ranking purpose")
    if c.availability_context == "retrospective_after_close":
        if not c.source_evidence or not c.after_close_scenario:
            raise ValueError(
                "retrospective research requires approved source evidence and scenario"
            )
    elif c.temporal_basis != "timestamp":
        raise ValueError("strict point-in-time evaluation requires timestamp boundaries")
    if len({s.name for s in c.scores}) != len(c.scores):
        raise ValueError("score names must be unique")
    if len({s.column for s in c.scores}) != len(c.scores):
        raise ValueError("score columns must be distinct")
    for score in c.scores:
        if not score.name or not score.column or score.kind not in {"raw_factor", "model_score"}:
            raise ValueError("every score needs an explicit name, column and kind")
        if score.direction not in {"higher_score_higher_label", "lower_score_higher_label"}:
            raise ValueError("every score needs a frozen direction")
    assets = [asset for u in c.universes for asset in u.assets]
    if len(set(assets)) != len(assets):
        raise ValueError("asset identity must be unique across frozen universes")
    if len({u.name for u in c.universes}) != len(c.universes):
        raise ValueError("universe names must be unique")
    if any(not u.name or not u.asset_type or not u.assets for u in c.universes):
        raise ValueError("each universe needs a name, asset type and assets")
    times = {
        name: _temporal(getattr(c, name), c.temporal_basis, name)
        for name in ("window_start", "window_end", "evaluation_as_of")
    }
    if not times["window_start"] <= times["window_end"] <= times["evaluation_as_of"]:
        raise ValueError("fixed window must end no later than evaluation_as_of")
    points = [_temporal(p.at, c.temporal_basis, "checkpoint") for p in c.checkpoints]
    if len(set(points)) != len(points) or any(not p.fold for p in c.checkpoints):
        raise ValueError("checkpoints must be unique and have fixed fold names")
    if any(not times["window_start"] <= t <= times["window_end"] for t in points):
        raise ValueError("every checkpoint must be inside the fixed window")
    timezone = ZoneInfo(c.market_timezone)
    local_points = [t.tz_convert(timezone) if t.tzinfo is not None else t for t in points]
    if len({(t.isocalendar().year, t.isocalendar().week) for t in local_points}) != len(points):
        raise ValueError("only one fixed checkpoint per market-local ISO week is permitted")
    if (
        not isinstance(c.label_horizon_session_intervals, int)
        or isinstance(c.label_horizon_session_intervals, bool)
        or c.label_horizon_session_intervals < 1
    ):
        raise ValueError("label_horizon_session_intervals must be a positive integer")
    expected_windows = {(t, u.name) for t in points for u in c.universes}
    windows = {}
    for w in c.label_windows:
        checkpoint = _temporal(w.checkpoint, c.temporal_basis, "label checkpoint")
        key = (checkpoint, w.universe)
        if key in windows:
            raise ValueError("duplicate frozen label window")
        start = _temporal(w.start, c.temporal_basis, "expected label start")
        end = _temporal(w.end, c.temporal_basis, "expected label end")
        sessions = [
            _temporal(day, "session_date_after_close", "calendar session") for day in w.sessions
        ]
        if not sessions or sessions != sorted(set(sessions)) or not w.calendar_reference:
            raise ValueError("label windows require a referenced, unique ordered session sequence")
        if session_sequence_sha256(w.sessions) != w.session_sequence_sha256:
            raise ValueError("frozen calendar session-sequence fingerprint mismatch")

        def local(t: pd.Timestamp) -> pd.Timestamp:
            return (
                t.tz_convert(timezone).tz_localize(None).normalize() if t.tzinfo is not None else t
            )

        local_checkpoint = local(checkpoint)
        if local_checkpoint not in sessions:
            raise ValueError("checkpoint is absent from the frozen session sequence")
        offsets = (w.start_session_offset, w.end_session_offset)
        if (
            any(not isinstance(v, int) or isinstance(v, bool) for v in offsets)
            or not 1 <= offsets[0] < offsets[1]
            or offsets[1] - offsets[0] != c.label_horizon_session_intervals
        ):
            raise ValueError(
                "frozen label offsets do not match the declared holding-session intervals"
            )
        position = sessions.index(local_checkpoint)
        if position + offsets[1] >= len(sessions):
            raise ValueError("frozen session sequence does not reach the label end")
        if (
            local(start) != sessions[position + offsets[0]]
            or local(end) != sessions[position + offsets[1]]
            or not checkpoint < start <= end
        ):
            raise ValueError("frozen label endpoints disagree with calendar/offset semantics")
        windows[key] = (start, end)
    if set(windows) != expected_windows:
        raise ValueError("exact label windows must be frozen for every checkpoint and universe")
    model_scores = any(score.kind == "model_score" for score in c.scores)
    if model_scores:
        bindings = {fold.fold: fold for fold in c.model_folds}
        if len(bindings) != len(c.model_folds) or set(bindings) != {p.fold for p in c.checkpoints}:
            raise ValueError("model scores require one frozen training binding per evaluation fold")
        for fold in c.model_folds:
            ft = {
                name: _temporal(getattr(fold, name), c.temporal_basis, name)
                for name in (
                    "train_start",
                    "train_end",
                    "training_labels_end",
                    "transform_fit_end",
                    "evaluation_start",
                    "evaluation_end",
                )
            }
            if not (
                ft["train_start"]
                <= ft["train_end"]
                < ft["evaluation_start"]
                <= ft["evaluation_end"]
            ):
                raise ValueError("training and evaluation fold boundaries overlap or invert")
            if not (
                ft["training_labels_end"] <= ft["train_end"]
                and ft["training_labels_end"] < ft["evaluation_start"]
            ):
                raise ValueError("training labels are not mature and purged before evaluation")
            if ft["transform_fit_end"] > ft["train_end"]:
                raise ValueError("feature transform was fitted after the training cutoff")
            if not fold.model_identity or not fold.transform_identity:
                raise ValueError("saved model and transform identities are required")
            if any(
                not ft["evaluation_start"] <= t <= ft["evaluation_end"]
                for t, p in zip(points, c.checkpoints, strict=True)
                if p.fold == fold.fold
            ):
                raise ValueError("checkpoint lies outside its frozen model evaluation fold")
    elif c.model_folds:
        raise ValueError("raw-factor-only contracts must not claim model training bindings")
    if c.data_mode != "synthetic":
        binding = c.real_binding
        if binding is None or not all(
            (
                binding.study_reference,
                binding.qualification_reference,
                binding.frozen_protocol_reference,
                binding.approval_reference,
            )
        ):
            raise ValueError(
                "real data requires explicit qualification, frozen protocol and approval"
            )
        if any(not score.definition_reference for score in c.scores):
            raise ValueError(
                "real factor/model scores require explicit definition/version references"
            )
        for value in (
            binding.score_frame_sha256,
            binding.label_frame_sha256,
            binding.qualification_sha256,
            binding.frozen_protocol_sha256,
            binding.approval_sha256,
        ):
            if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
                raise ValueError("real input frames must be bound to exact SHA-256 fingerprints")
        if binding.prior_result_sealed and (
            not binding.frozen_addendum_reference
            or not _valid_sha256(binding.frozen_addendum_sha256)
        ):
            raise ValueError(
                "sealed results require a separately frozen and approved RankIC addendum"
            )
    elif c.real_binding is not None:
        raise ValueError("real qualification evidence must not be relabeled synthetic")
    return times


def _valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def session_sequence_sha256(sessions: tuple[str, ...]) -> str:
    payload = json.dumps(sessions, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _typed_scalar(value: object) -> list:
    if value is None:
        return ["None"]
    if value is pd.NA:
        return ["pd.NA"]
    if value is pd.NaT:
        return ["pd.NaT"]
    if isinstance(value, (bool, np.bool_)):
        return ["bool", bool(value)]
    if isinstance(value, (int, np.integer)):
        return ["integer", str(value)]
    if isinstance(value, (float, np.floating)):
        return ["float", float(value).hex()]
    if isinstance(value, str):
        return ["string", value]
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return [type(value).__name__, value.isoformat()]
    raise ValueError(f"unsupported evaluation-input scalar type: {type(value).__name__}")


def frame_sha256(frame: pd.DataFrame) -> str:
    """Type-aware exact frame identity; external qualification is a separate step."""
    payload = {
        "schema": "lei-evaluation-frame-identity/2",
        "columns": [_typed_scalar(column) for column in frame.columns],
        "dtypes": [str(dtype) for dtype in frame.dtypes],
        "rows": [
            [_typed_scalar(value) for value in row]
            for row in frame.itertuples(index=False, name=None)
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _require(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{name} missing columns: {missing}")
    if len(set(columns)) != len(columns):
        raise ValueError(f"{name} column bindings must be distinct")


def _prepare(scores: pd.DataFrame, labels: pd.DataFrame, c: RankICContract) -> pd.DataFrame:
    b = c.columns
    causal_names = [b.asset, b.asset_type, b.checkpoint, b.computed_through, b.source_available]
    score_names = [s.column for s in c.scores]
    label_names = [
        b.label_asset,
        b.label_checkpoint,
        b.label_value,
        b.label_start,
        b.label_end,
        b.label_available,
        b.label_quality,
    ]
    _require(scores, causal_names + score_names, "causal scores")
    _require(labels, label_names, "label sidecar")
    future_columns = {b.label_value, b.label_start, b.label_end, b.label_available, b.label_quality}
    if future_columns & set(scores.columns):
        raise ValueError("future-label columns must remain in the evaluation-only sidecar")
    left = scores[causal_names + score_names].copy()
    left.columns = ["asset", "asset_type", "checkpoint", "computed_through", "source_available"] + [
        f"score_{i}" for i in range(len(c.scores))
    ]
    right = labels[label_names].copy()
    right.columns = [
        "asset",
        "checkpoint",
        "label",
        "label_start",
        "label_end",
        "label_available",
        "label_quality",
    ]
    for frame, name in ((left, "causal scores"), (right, "label sidecar")):
        if frame[["asset", "checkpoint"]].isna().any().any():
            raise ValueError(f"{name} keys must not be missing")
        frame["checkpoint"] = frame["checkpoint"].map(
            lambda x: _temporal(x, c.temporal_basis, "checkpoint")
        )
        if frame.duplicated(["asset", "checkpoint"]).any():
            raise ValueError(f"{name} duplicate asset/checkpoint keys")
    left["score_row_present"] = True
    right["label_row_present"] = True
    grid = pd.DataFrame(
        [
            {
                "asset": a,
                "checkpoint": _temporal(p.at, c.temporal_basis, "checkpoint"),
                "fold": p.fold,
                "universe": u.name,
                "expected_asset_type": u.asset_type,
            }
            for p in c.checkpoints
            for u in c.universes
            for a in u.assets
        ]
    )
    selected = left[left["checkpoint"].isin(grid["checkpoint"])]
    allowed = set(zip(grid["asset"], grid["checkpoint"], strict=False))
    if any(
        key not in allowed for key in zip(selected["asset"], selected["checkpoint"], strict=False)
    ):
        raise ValueError("selected score rows contain assets outside the frozen universe")
    joined = grid.merge(left, on=["asset", "checkpoint"], how="left", validate="one_to_one")
    joined = joined.merge(right, on=["asset", "checkpoint"], how="left", validate="one_to_one")
    joined["computed_through"] = _optional_times(
        joined["computed_through"], c.temporal_basis, "computed_through"
    )
    for field in ("label_start", "label_end", "label_available"):
        joined[field] = _optional_times(joined[field], c.temporal_basis, field)
    joined["source_available"] = _optional_times(
        joined["source_available"], "timestamp", "source_available"
    )
    for field in ["label"] + [f"score_{i}" for i in range(len(c.scores))]:
        joined[field] = pd.to_numeric(joined[field], errors="raise").astype("float64")
    known_quality = joined["label_quality"].dropna()
    if not known_quality.map(lambda x: isinstance(x, (bool, np.bool_))).all():
        raise ValueError("label_quality must contain booleans, not strings or numbers")
    return joined


def _true(value: object) -> bool:
    return isinstance(value, (bool, np.bool_)) and bool(value)


def _reasons(row: pd.Series, c: RankICContract, times: dict) -> list[str]:
    reasons = []
    if not _true(row["score_row_present"]):
        reasons.append("score_row_missing")
    elif row["asset_type"] != row["expected_asset_type"]:
        reasons.append("asset_type_mismatch")
    if pd.isna(row["computed_through"]):
        reasons.append("computed_through_unknown")
    elif row["computed_through"] > row["checkpoint"]:
        reasons.append("feature_computed_from_future")
    available = row["source_available"]
    if pd.isna(available):
        if c.availability_context == "strict_point_in_time":
            reasons.append("source_arrival_unknown")
    else:
        if c.temporal_basis == "session_date_after_close":
            available = available.tz_convert(c.market_timezone).tz_localize(None).normalize()
        if available > row["checkpoint"]:
            reasons.append("source_not_yet_available")
    if c.model_folds:
        fold = next(f for f in c.model_folds if f.fold == row["fold"])
        end = _temporal(fold.evaluation_end, c.temporal_basis, "fold evaluation_end")
        if pd.notna(row["label_end"]) and row["label_end"] > end:
            reasons.append("label_not_mature_in_model_fold")
    if not _true(row["label_row_present"]):
        reasons.append("label_row_missing")
    if not _true(row["label_quality"]):
        reasons.append("label_quality_invalid")
    if not np.isfinite(row["label"]):
        reasons.append("label_missing_or_nonfinite")
    window = next(
        w
        for w in c.label_windows
        if _temporal(w.checkpoint, c.temporal_basis, "label checkpoint") == row["checkpoint"]
        and w.universe == row["universe"]
    )
    if (
        pd.notna(row["label_start"])
        and pd.notna(row["label_end"])
        and (
            row["label_start"] != _temporal(window.start, c.temporal_basis, "expected label start")
            or row["label_end"] != _temporal(window.end, c.temporal_basis, "expected label end")
        )
    ):
        reasons.append("label_endpoint_differs_from_frozen_window")
    if pd.isna(row["label_start"]) or pd.isna(row["label_end"]):
        reasons.append("label_window_unknown")
    elif not row["checkpoint"] < row["label_start"] <= row["label_end"]:
        reasons.append("label_not_strictly_forward")
    elif row["label_end"] > times["window_end"]:
        reasons.append("label_not_mature_in_fixed_window")
    if pd.isna(row["label_available"]):
        # Session-date retrospective research asserts only end-of-label-window maturity.
        if c.temporal_basis == "timestamp":
            reasons.append("label_arrival_unknown")
    elif row["label_available"] > times["evaluation_as_of"]:
        reasons.append("label_not_yet_available_to_evaluator")
    elif pd.notna(row["label_end"]) and row["label_available"] < row["label_end"]:
        reasons.append("label_available_before_window_end")
    return reasons


def _existing_rank_ic(
    score: pd.Series,
    label: pd.Series,
    checkpoint: pd.Timestamp,
    min_assets: int,
) -> float | None:
    """Delegate to the current repository backend; never reimplement its ranks."""
    from .diagnostics import _cross_section_ic

    pairs = pd.DataFrame(
        {
            "observation_date": checkpoint,
            "value": score,
            "target": label,
            "exclusion_reason": None,
        }
    )
    result = _cross_section_ic(pairs, min_pairs=min_assets)
    if len(result["periods"]) != 1 or result["periods"][0]["n"] != len(score):
        raise RuntimeError("existing RankIC backend violated the expected single-section contract")
    return result["periods"][0]["ic"]


def _summarize(periodic: pd.DataFrame, c: RankICContract) -> pd.DataFrame:
    summaries = []
    for (universe, score_name), group in periodic.groupby(["universe", "score"], sort=False):
        valid = group[group["rank_ic"].notna()]
        result = {
            "universe": universe,
            "asset_type": group.iloc[0]["asset_type"],
            "score": score_name,
            "score_kind": group.iloc[0]["score_kind"],
            "direction": group.iloc[0]["direction"],
            "time_weighting": c.time_weighting,
            "expected_periods": len(group),
            "expected_folds": int(group["fold"].nunique()),
            "valid_folds": int(valid["fold"].nunique()),
            "summary_undefined_reason": None,
            "valid_periods": len(valid),
            "period_coverage": len(valid) / len(group),
            "expected_asset_periods": int(group["expected_assets"].sum()),
            "eligible_asset_periods": int(group["eligible_assets"].sum()),
            "mean_rank_ic": None,
            "mean_directional_rank_ic": None,
            "rank_ic_dispersion": None,
            "descriptive_icir": None,
        }
        result["asset_coverage"] = (
            result["eligible_asset_periods"] / result["expected_asset_periods"]
        )
        if (
            c.time_weighting == "equal_fold_then_checkpoint"
            and valid["fold"].nunique() != group["fold"].nunique()
        ):
            result["summary_undefined_reason"] = "frozen_fold_has_no_defined_period"
        elif len(valid):
            if c.time_weighting == "equal_checkpoint":
                weights = np.full(len(valid), 1 / len(valid))
            else:
                fold_sizes = valid.groupby("fold")["rank_ic"].transform("size").to_numpy()
                weights = 1 / (valid["fold"].nunique() * fold_sizes)
            values = valid["rank_ic"].to_numpy(dtype=float)
            mean = float(np.sum(weights * values))
            result["mean_rank_ic"] = mean
            direction = 1 if group.iloc[0]["direction"] == "higher_score_higher_label" else -1
            result["mean_directional_rank_ic"] = direction * mean
            if len(valid) > 1:
                variance = float(np.sum(weights * (values - mean) ** 2) / (1 - np.sum(weights**2)))
                dispersion = float(np.sqrt(max(0, variance)))
                result["rank_ic_dispersion"] = dispersion
                if dispersion > 0:
                    result["descriptive_icir"] = mean / dispersion
        summaries.append(result)
    return pd.DataFrame(summaries)


def evaluate_frozen_rank_ic(
    causal_scores: pd.DataFrame,
    label_sidecar: pd.DataFrame,
    contract: RankICContract,
) -> RankICEvaluation:
    """Evaluate a frozen factor/model ranking contract without touching inputs.

    Raw RankIC always uses the original score direction. The separately named
    directional value follows the predeclared direction; negative results do not
    trigger an automatic flip. No threshold, significance or annualization is used.
    """
    c = contract
    times = _validate_contract(c)
    if c.real_binding is not None and (
        frame_sha256(causal_scores) != c.real_binding.score_frame_sha256
        or frame_sha256(label_sidecar) != c.real_binding.label_frame_sha256
    ):
        raise ValueError("evaluation input fingerprint differs from the frozen real binding")
    payload = asdict(c)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    metadata = {
        "schema": "lei-rank-ic-evaluation/1.1",
        "synthetic_provenance": "caller-declared; values are not authenticated as synthetic",
        "session_date_scope": (
            "completed-date retrospective; intraday arrival ordering not evaluated"
            if c.temporal_basis == "session_date_after_close"
            else "timestamp"
        ),
        "data_mode": c.data_mode,
        "synthetic": c.data_mode == "synthetic",
        "provenance_validation": (
            "input identity only; external qualification/approval are referenced"
        ),
        "contract": payload,
        "contract_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        "metric": "Spearman cross-sectional RankIC; exact average ties",
        "backend": "lei_signal.research.factor_lab.diagnostics._cross_section_ic",
        "live_qualified": False,
        "inference": "descriptive only; no annualization or independence/significance claim",
        "label_dependence": c.label_overlap,
        "status": "evaluated",
        "undefined_period_policy": "reported and excluded from defined-period means; no zero fill",
        "model_fold_evidence": "frozen boundaries/identities checked; saved fits not reexecuted",
    }
    if c.purpose in {"trend_switch", "entry_trigger"}:
        metadata.update(
            status="metric_not_applicable",
            recommended_metrics=(
                ["state-transition timing", "false-warning rate", "conditional forward outcomes"]
                if c.purpose == "trend_switch"
                else [
                    "entry/exit matched outcomes",
                    "risk-normalized outcomes",
                    "fees and adverse excursion",
                ]
            ),
        )
        return RankICEvaluation(metadata, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    joined = _prepare(causal_scores, label_sidecar, c)
    joined["base_reasons"] = joined.apply(lambda row: _reasons(row, c, times), axis=1)
    rows, exclusions = [], []
    for (checkpoint, universe), group in joined.groupby(["checkpoint", "universe"], sort=False):
        score_fields = [f"score_{i}" for i in range(len(c.scores))]
        common_missing = ~np.isfinite(group[score_fields]).all(axis=1)
        for i, score in enumerate(c.scores):
            reasons = []
            for pos, (_, row) in enumerate(group.iterrows()):
                reason = list(row["base_reasons"])
                if not np.isfinite(row[f"score_{i}"]):
                    reason.append("score_missing_or_nonfinite")
                elif c.score_mask_policy == "common" and common_missing.iloc[pos]:
                    reason.append("other_declared_score_missing")
                reasons.append(reason)
                if reason:
                    exclusions.append(
                        {
                            "checkpoint": checkpoint.isoformat(),
                            "universe": universe,
                            "asset": row["asset"],
                            "score": score.name,
                            "reasons": tuple(reason),
                        }
                    )
            eligible = group.loc[[not r for r in reasons]]
            undefined = None
            value = None
            if len(eligible) < c.min_assets:
                undefined = "fewer_than_min_assets"
            elif eligible[f"score_{i}"].nunique() < 2:
                undefined = "constant_score"
            elif eligible["label"].nunique() < 2:
                undefined = "constant_label"
            else:
                value = _existing_rank_ic(
                    eligible[f"score_{i}"], eligible["label"], checkpoint, c.min_assets
                )
                if value is None or not np.isfinite(value):
                    value, undefined = None, "backend_undefined"
            direction = 1 if score.direction == "higher_score_higher_label" else -1
            rows.append(
                {
                    "checkpoint": checkpoint.isoformat(),
                    "fold": group.iloc[0]["fold"],
                    "universe": universe,
                    "asset_type": group.iloc[0]["expected_asset_type"],
                    "score": score.name,
                    "score_kind": score.kind,
                    "direction": score.direction,
                    "expected_assets": len(group),
                    "eligible_assets": len(eligible),
                    "asset_coverage": len(eligible) / len(group),
                    "unknown_source_arrival_assets": int(eligible["source_available"].isna().sum()),
                    "rank_ic": value,
                    "directional_rank_ic": direction * value if value is not None else None,
                    "undefined_reason": undefined,
                    "thin_cross_section": len(eligible) == 2,
                }
            )
    periodic = pd.DataFrame(rows)
    metadata["excluded_asset_score_rows"] = len(exclusions)
    counts: dict[str, int] = {}
    for item in exclusions:
        for reason in item["reasons"]:
            counts[reason] = counts.get(reason, 0) + 1
    metadata["exclusion_reason_counts_nonexclusive"] = counts
    metadata["source_arrival_claim"] = (
        "strict known source times only"
        if c.availability_context == "strict_point_in_time"
        else "declared retrospective scenario; actual arrival is not certified"
    )
    return RankICEvaluation(metadata, periodic, _summarize(periodic, c), pd.DataFrame(exclusions))
