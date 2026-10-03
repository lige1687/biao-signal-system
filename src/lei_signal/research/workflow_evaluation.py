"""Research-only evaluators and stored-prediction aggregation.

No archived runner is imported. Scores describe predictive error, never account
returns. Callers own source qualification, scientific review and publication.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

VERSION = "1.0.0"
_BINARY = {"up", "downside_event"}
_CONTINUOUS = {"forward_return", "mae", "max_drawdown", "forward_volatility"}


class EvaluationError(ValueError):
    """Invalid dates, pairing, units or numerical inputs; poor effects are legal."""


def _date(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise EvaluationError(f"{field}: expected YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise EvaluationError(f"{field}: invalid date") from exc
    if parsed.isoformat() != value:
        raise EvaluationError(f"{field}: expected YYYY-MM-DD")
    return value


def _finite(value: Any, field: str) -> float:
    if isinstance(value, (bool, str)) or not isinstance(value, (int, float, np.number)):
        raise EvaluationError(f"{field}: expected finite number")
    number = float(value)
    if not np.isfinite(number):
        raise EvaluationError(f"{field}: expected finite number")
    return number


def _config(contract: Mapping[str, Any]) -> tuple[bool, str]:
    if contract.get("question", {}).get("layer") == "decision_policy":
        raise EvaluationError("decision_policy/account evaluation is not implemented")
    kind = contract.get("target", {}).get("kind")
    if kind not in _BINARY | _CONTINUOUS:
        raise EvaluationError("target.kind: unsupported; policy/account evaluation is not implemented")
    binary = kind in _BINARY
    expected = "probability" if binary else "percentage_point"
    if contract.get("target", {}).get("unit") != expected:
        raise EvaluationError(f"target.unit: {kind} requires {expected}")
    weights = contract.get("weights", {})
    if weights.get("policy") not in {"equal_asset", "equal_date"} or weights.get("comparison") != "fixed_common":
        raise EvaluationError("weights: require equal_asset/equal_date with fixed_common")
    if contract.get("training_weights", "equal_asset") not in {"equal_asset", "equal_date"}:
        raise EvaluationError("training_weights: require equal_asset/equal_date")
    dep = contract.get("dependence", {})
    for field in ("block_length", "draws"):
        if isinstance(dep.get(field), bool) or not isinstance(dep.get(field), int) or dep[field] < 1:
            raise EvaluationError(f"dependence.{field}: require positive integer")
    if isinstance(dep.get("seed"), bool) or not isinstance(dep.get("seed"), int) or dep["seed"] < 0:
        raise EvaluationError("dependence.seed: require nonnegative integer")
    return binary, weights["policy"]


def _weights(frame: pd.DataFrame, policy: str) -> np.ndarray:
    """Each observed asset/date gets equal total; normalize on the paired rows."""
    group = "asset" if policy == "equal_asset" else "date"
    values = 1.0 / frame[group].map(frame[group].value_counts()).to_numpy(float)
    return values / values.sum()


def _observations(rows: Sequence[Mapping[str, Any]], binary: bool) -> pd.DataFrame:
    required = {"id", "asset", "date", "stratum", "features", "eligible", "y", "label_end", "label_reason", "tested_condition"}
    prepared = []
    for i, raw in enumerate(rows):
        if not required.issubset(raw):
            raise EvaluationError(f"observations[{i}]: missing {sorted(required - raw.keys())}")
        r = dict(raw)
        if not isinstance(r["id"], str) or not r["id"] or not isinstance(r["asset"], str) or not r["asset"]:
            raise EvaluationError("observation id/asset: require nonempty strings")
        _date(r["date"], "observation.date")
        if r["stratum"] != f"{r['asset']}|{r['date'][:4]}":
            raise EvaluationError("stratum: must be asset|calendar year")
        if not isinstance(r["eligible"], bool) or not isinstance(r["features"], Mapping):
            raise EvaluationError("observation eligible/features: invalid shape")
        if r["tested_condition"] not in (None, False, True, 0, 1):
            raise EvaluationError("tested_condition: require boolean/0/1 or null")
        if r["eligible"]:
            r["y"] = _finite(r["y"], "observation.y")
            if binary and r["y"] not in (0.0, 1.0):
                raise EvaluationError("binary target y: require 0/1")
            _date(r["label_end"], "observation.label_end")
            if r["label_end"] < r["date"]:
                raise EvaluationError("label_end precedes observation date")
            if r["label_reason"] is not None:
                raise EvaluationError("eligible observation cannot have a label exclusion reason")
        prepared.append(r)
    frame = pd.DataFrame(prepared)
    if len(frame) and (frame.id.duplicated().any() or frame.duplicated(["asset", "date"]).any()):
        raise EvaluationError("observations: duplicate id or asset/date")
    return frame


def _axis(contract: Mapping[str, Any], observations: pd.DataFrame | None) -> list[str]:
    declared = contract.get("calendar", contract.get("data", {}).get("calendar"))
    if declared is None and observations is not None and len(observations):
        declared = sorted(observations.date.unique().tolist())
    if not isinstance(declared, (list, tuple)) or not declared:
        raise EvaluationError("full calendar required: supply observations (including excluded dates) or contract.calendar")
    axis = [_date(x, "calendar") for x in declared]
    if axis != sorted(set(axis)):
        raise EvaluationError("calendar: require ordered unique dates")
    if observations is not None and len(observations) and not set(observations.date).issubset(axis):
        raise EvaluationError("observations date outside declared calendar")
    if observations is not None and len(observations):
        eligible = observations[observations.eligible]
        if not set(eligible.label_end).issubset(axis):
            raise EvaluationError("eligible label_end outside declared calendar")
    return axis


def _folds(contract: Mapping[str, Any]) -> list[dict[str, str]]:
    folds = contract.get("split", {}).get("folds")
    if not isinstance(folds, list) or not folds:
        raise EvaluationError("split.folds: require nonempty list")
    result = []
    for i, f in enumerate(folds):
        if not isinstance(f, Mapping):
            raise EvaluationError("split.fold: require object")
        values = {key: _date(f.get(key), f"fold.{key}") for key in ("train_end", "eval_start", "eval_end")}
        if not values["train_end"] < values["eval_start"] <= values["eval_end"]:
            raise EvaluationError("fold: train_end must precede eval_start")
        if any(values["eval_start"] <= prior["eval_end"] and values["eval_end"] >= prior["eval_start"] for prior in result):
            raise EvaluationError("folds: overlapping evaluation dates")
        result.append({**values, "name": str(i)})
    if contract.get("split", {}).get("label_policy") not in {"purge", "require_mature"}:
        raise EvaluationError("split.label_policy: require purge or require_mature")
    return result


def _ridge(train: pd.DataFrame, evaluation: pd.DataFrame, cols: list[str], policy: str, binary: bool) -> tuple[np.ndarray, dict[str, Any]]:
    w = _weights(train, policy)
    y = train.y.to_numpy(float)
    x = np.array([[r[c] for c in cols] for r in train.features], dtype=float).reshape(len(train), len(cols))
    xe = np.array([[r[c] for c in cols] for r in evaluation.features], dtype=float).reshape(len(evaluation), len(cols))
    mean = w @ x
    std = np.sqrt(w @ ((x - mean) ** 2))
    zero = std < 1e-12
    std[zero] = 1.0
    z, ze = (x - mean) / std, (xe - mean) / std
    intercept = float(w @ y)
    coef = np.linalg.solve((z.T * w) @ z + np.eye(len(cols)), (z.T * w) @ (y - intercept)) if cols else np.array([])
    raw = intercept + ze @ coef
    prediction = np.clip(raw, 0, 1) if binary else raw
    fit = {"features": cols, "mean": mean.tolist(), "std": std.tolist(), "coef": coef.tolist(), "intercept": intercept, "lambda": 1.0, "weight_sum": float(w.sum()), "penalty_scale": "normalized weighted MSE + lambda*sum(coef^2)", "zero_variance": [c for c, flag in zip(cols, zero) if flag], "training_rows": len(train), "raw_min": float(raw.min()), "raw_max": float(raw.max()), "clipped_rows": int(np.sum(raw != prediction))}
    return prediction, fit


def _event(train: pd.DataFrame, evaluation: pd.DataFrame, cols: list[str], policy: str) -> tuple[np.ndarray, dict[str, Any]]:
    w = _weights(train, policy)
    train_mean = float(w @ train.y.to_numpy(float))
    groups: dict[tuple[float, ...], list[float]] = {}
    for features, y, weight in zip(train.features, train.y, w):
        key = tuple(float(features[c]) for c in cols)
        count, total, numerator = groups.get(key, [0, 0.0, 0.0])
        groups[key] = [count + 1, total + weight, numerator + weight * y]
    output = []
    counts, fallback = [], 0
    for features in evaluation.features:
        key = tuple(float(features[c]) for c in cols)
        count, total, numerator = groups.get(key, [0, 0.0, 0.0])
        output.append(numerator / total if total else train_mean)
        counts.append(int(count))
        fallback += int(count == 0)
    return np.array(output), {"features": cols, "group_counts": [{"key": list(key), "rows": int(value[0]), "weight": value[1]} for key, value in groups.items()], "evaluation_group_train_counts": counts, "fallback_rows": fallback, "intercept": train_mean, "training_rows": len(train)}


def evaluate_observations(observations: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]) -> dict[str, Any]:
    """Fit declared historical folds only after validating dates and features."""
    binary, policy = _config(contract)
    training_policy = contract.get("training_weights", "equal_asset")
    frame = _observations(observations, binary)
    axis = _axis(contract, frame)
    folds = _folds(contract)
    evaluator = contract.get("evaluator", {})
    kind = evaluator.get("kind")
    if kind not in {"prediction_ridge", "event_risk"} or evaluator.get("version") != VERSION:
        raise EvaluationError("evaluator: unsupported kind/version")
    if kind == "prediction_ridge" and evaluator.get("lambda") != 1.0:
        raise EvaluationError("evaluator.lambda: first version freezes normalized penalty at 1")
    if kind == "event_risk" and not binary:
        raise EvaluationError("event_risk: frequency evaluator requires up/downside_event binary target")
    baseline = evaluator.get("baseline_features", []) if kind == "prediction_ridge" else ["existing_state"]
    added = evaluator.get("added_features", []) if kind == "prediction_ridge" else ["added"]
    if not isinstance(baseline, list) or not isinstance(added, list) or not added or any(not isinstance(c, str) or not c for c in baseline + added):
        raise EvaluationError("evaluator features: require declared names and added information")
    if len(set(baseline + added)) != len(baseline + added):
        raise EvaluationError("evaluator features: duplicate/overlapping fields")
    eligible = frame[frame.eligible].copy() if len(frame) else frame
    for row in eligible.to_dict("records"):
        for column in baseline + added:
            if column not in row["features"]:
                raise EvaluationError(f"eligible features: missing {column}")
            _finite(row["features"][column], f"feature.{column}")
        if kind == "event_risk" and row["features"]["added"] not in (0, 1):
            raise EvaluationError("event_risk added: must be a binary event, not continuous group keys")
    # Prepare every split before the first numerical fit: bad later folds cannot
    # cause partial scientific execution before a validation error is raised.
    prepared, purged = [], 0
    for fold in folds:
        train = eligible[eligible.date <= fold["train_end"]].copy() if len(eligible) else eligible
        immature = train.label_end >= fold["eval_start"] if len(train) else np.array([], bool)
        if np.any(immature) and contract["split"]["label_policy"] == "require_mature":
            raise EvaluationError("training label not strictly mature before eval_start")
        purged += int(np.sum(immature))
        train = train.loc[~immature] if len(train) else train
        ev = eligible[(eligible.date >= fold["eval_start"]) & (eligible.date <= fold["eval_end"])].copy() if len(eligible) else eligible
        if contract["split"].get("evaluation_label_policy") == "contained" and len(ev):
            ev = ev.loc[ev.label_end <= fold["eval_end"]].copy()
        prepared.append((fold, train, ev))
    predictions, warnings, fit_details = [], [], []
    total_training_rows, fits = 0, 0
    for fold, train, ev in prepared:
        if len(train) < evaluator.get("minimum_training_rows", 1) or not len(ev):
            warnings.append(f"fold {fold['name']}: no mature training/evaluation rows; not estimated")
            continue
        total_training_rows += len(train)
        train_mean = float(_weights(train, training_policy) @ train.y.to_numpy(float))
        predicted = {"B0": np.full(len(ev), train_mean)}
        for model, cols in [("B1", baseline), ("B2", baseline + added)]:
            predicted[model], detail = (_ridge(train, ev, cols, training_policy, binary) if kind == "prediction_ridge" else _event(train, ev, cols, training_policy))
            fit_details.append({"fold": fold["name"], "model": model, "training_weights": training_policy, **detail})
            fits += 1
            if detail.get("zero_variance"):
                warnings.append(f"fold {fold['name']} {model}: zero variance features {detail['zero_variance']}")
        for j, row in enumerate(ev.to_dict("records")):
            prediction = {key: row[key] for key in ("id", "asset", "date", "y", "label_end")}
            prediction.update(fold=fold["name"], train_mean=train_mean, **{model: float(values[j]) for model, values in predicted.items()})
            if binary:
                prediction["B50"] = 0.5
            predictions.append(prediction)
    result = summarize_predictions(predictions, {**contract, "calendar": axis}, observations)
    result["warnings"] = warnings + result["warnings"]
    result["execution"] = {"fits": fits, "training_rows": total_training_rows, "purged_rows": purged, "fit_details": fit_details, "mode": "fit_declared_folds"}
    return result


def _paired_predictions(rows: Sequence[Mapping[str, Any]], binary: bool, folds: list[dict[str, str]], axis: list[str]) -> pd.DataFrame:
    required = {"id", "asset", "date", "fold", "y", "label_end", "B0", "B1", "B2"} | ({"B50"} if binary else set())
    prepared = []
    for i, raw in enumerate(rows):
        if not required.issubset(raw):
            raise EvaluationError(f"predictions[{i}]: missing paired baseline fields {sorted(required - raw.keys())}")
        r = dict(raw)
        if not isinstance(r["id"], str) or not r["id"] or not isinstance(r["asset"], str) or not r["asset"]:
            raise EvaluationError("prediction id/asset: require nonempty strings")
        _date(r["date"], "prediction.date")
        _date(r["label_end"], "prediction.label_end")
        if r["date"] not in axis or r["label_end"] not in axis or r["label_end"] < r["date"]:
            raise EvaluationError("prediction dates: outside calendar or label ends before observation")
        r["fold"] = str(r["fold"])
        matching = [f for f in folds if f["name"] == r["fold"] and f["eval_start"] <= r["date"] <= f["eval_end"]]
        if len(matching) != 1:
            raise EvaluationError("prediction fold/date: must belong to exactly one declared fold")
        for col in ["y", "B0", "B1", "B2"] + (["B50"] if binary else []):
            r[col] = _finite(r[col], f"prediction.{col}")
        if binary:
            if r["y"] not in (0, 1) or any(not 0 <= r[c] <= 1 for c in ("B0", "B1", "B2")) or r["B50"] != 0.5:
                raise EvaluationError("binary predictions: y=0/1, probabilities in [0,1], B50 exactly 0.5 required")
        if "train_mean" in r and _finite(r["train_mean"], "train_mean") != r["B0"]:
            raise EvaluationError("B0 must equal supplied train_mean")
        prepared.append(r)
    frame = pd.DataFrame(prepared)
    if len(frame) and (frame.id.duplicated().any() or frame.duplicated(["asset", "date"]).any()):
        raise EvaluationError("predictions: duplicate id or asset/date breaks fixed pairing")
    if len(frame) and (frame.groupby("fold").B0.nunique() > 1).any():
        raise EvaluationError("B0 must be a constant training mean/frequency within each fold")
    return frame


def _block_draws(frame: pd.DataFrame, values: np.ndarray, axis: list[str], policy: str, dep: Mapping[str, int]) -> tuple[np.ndarray, int]:
    """Circular moving blocks on the full axis; all assets share each draw.

    Draws missing an entire asset are unestimable for equal_asset and excluded,
    rather than silently changing the set of equally weighted assets.
    """
    rng = np.random.default_rng(dep["seed"])
    m, block, count = len(axis), dep["block_length"], dep["draws"]
    indexes = {d: i for i, d in enumerate(axis)}
    positions = frame.date.map(indexes).to_numpy(int)
    assets = sorted(frame.asset.unique())
    outputs = np.full(count, np.nan)
    for draw in range(count):
        starts = rng.integers(0, m, int(np.ceil(m / block)))
        chosen = ((starts[:, None] + np.arange(block)) % m).ravel()[:m]
        multiplicity = np.bincount(chosen, minlength=m)
        row_count = multiplicity[positions].astype(float)
        if policy == "equal_asset":
            means = []
            for asset in assets:
                mask = frame.asset.to_numpy() == asset
                denominator = row_count[mask].sum()
                if not denominator:
                    break
                means.append(float(row_count[mask] @ values[mask] / denominator))
            if len(means) == len(assets):
                outputs[draw] = np.mean(means)
        else:
            per_date = frame.assign(value=values).groupby("date").value.mean()
            ix = np.array([indexes[d] for d in per_date.index])
            denominator = multiplicity[ix].sum()
            if denominator:
                outputs[draw] = multiplicity[ix] @ per_date.to_numpy() / denominator
    valid = outputs[np.isfinite(outputs)]
    return valid, count - len(valid)


def _descriptions(frame: pd.DataFrame | None, ids: set[str], policy: str, binary: bool) -> dict[str, Any]:
    if frame is None or not len(frame):
        return {"available": False, "reason": "observations not supplied; own-group and common-support descriptions not reconstructed"}
    eligible = frame[frame.eligible].copy()
    result: dict[str, Any] = {"available": True, "population": "all_evaluable_observations (not restricted to forecast evaluation folds)", "raw_rows": len(frame), "evaluable_rows": len(eligible), "common_prediction_rows": len(ids), "event_opportunities": int(eligible.tested_condition.eq(True).sum()), "excluded": [{"id": r["id"], "reason": r["label_reason"] or "not_eligible"} for r in frame[~frame.eligible].to_dict("records")], "own_group": [], "common_asset_year": [], "unsupported_strata": [], "comparison_available": False}
    subset = eligible[eligible.tested_condition.notna()].copy()
    if not len(subset):
        result["common_support_reason"] = "tested_condition unknown"
        return result
    subset["condition"] = subset.tested_condition.astype(int)
    for condition, group in subset.groupby("condition"):
        result["own_group"].append({"condition": int(condition), "mean": float(_weights(group, policy) @ group.y.to_numpy(float)), "rows": len(group), "assets": int(group.asset.nunique()), "weighting": f"natural own-group {policy}; different composition is not net increment"})
    all_strata = pd.MultiIndex.from_frame(frame[["asset", "stratum"]].drop_duplicates())
    counts = subset.groupby(["asset", "stratum", "condition"]).size().unstack(fill_value=0).reindex(columns=[0, 1], fill_value=0).reindex(all_strata, fill_value=0)
    support = counts[(counts[0] > 0) & (counts[1] > 0)]
    for (asset, stratum), c in counts.iterrows():
        if (asset, stratum) not in support.index:
            result["unsupported_strata"].append({"asset": asset, "stratum": stratum, "rows0": int(c[0]), "rows1": int(c[1]), "reason": "both states not observed"})
    if not len(support):
        result["common_support_reason"] = "no asset-year contains both states; condition contrast not estimable (not evidence of ineffectiveness)"
        return result
    asset_count = len(support.index.get_level_values("asset").unique())
    mean0 = mean1 = overall = decomposition = 0.0
    supported_rows = 0
    for asset, stratum in support.index:
        g = subset[(subset.asset == asset) & (subset.stratum == stratum)]
        weight = 1 / asset_count / int((support.index.get_level_values("asset") == asset).sum())
        mu = {state: float(g[g.condition == state].y.mean()) for state in (0, 1)}
        share1 = float(g.condition.mean())
        mixed = float(g.y.mean())
        mean0 += weight * mu[0]
        mean1 += weight * mu[1]
        overall += weight * mixed
        decomposition += weight * ((1 - share1) * mu[0] + share1 * mu[1])
        supported_rows += len(g)
        result["common_asset_year"].append({"asset": asset, "stratum": stratum, "weight": weight, "rows0": int((g.condition == 0).sum()), "rows1": int((g.condition == 1).sum()), "mean0": mu[0], "mean1": mu[1], "overall": mixed, "share1": share1})
    result.update(comparison_available=True, common_support_rows=supported_rows, common_support_assets=asset_count, fixed_common_means={"condition0": mean0, "condition1": mean1, "difference": mean1 - mean0, "baseline": overall, "identity_error": overall - decomposition, "unit": "probability" if binary else "percentage_point", "weighting": "equal supported assets; equal supported years within asset; same strata in both conditions", "evidence": "descriptive, not causal"})
    return result


def summarize_predictions(predictions: Sequence[Mapping[str, Any]], contract: Mapping[str, Any], observations: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Validate paired stored predictions and reaggregate; never perform a fit."""
    binary, policy = _config(contract)
    obs = _observations(observations, binary) if observations is not None else None
    axis = _axis(contract, obs)
    frame = _paired_predictions(predictions, binary, _folds(contract), axis)
    warnings: list[str] = []
    if obs is not None and len(frame):
        lookup = {r["id"]: r for r in obs.to_dict("records")}
        for p in frame.to_dict("records"):
            r = lookup.get(p["id"])
            if r is None or not r["eligible"] or any(p[c] != r[c] for c in ("asset", "date", "y", "label_end")):
                raise EvaluationError("predictions do not match eligible observation identity/target")
    descriptions = _descriptions(obs, set(frame.id) if len(frame) else set(), policy, binary)
    if descriptions.get("available") and not descriptions.get("comparison_available") and obs.tested_condition.notna().any():
        warnings.append("common support absent: condition contrast cannot support an increment conclusion")
    performance, increments = [], []
    if not len(frame):
        warnings.append("no paired predictions: results not estimated")
        return {"predictions": [], "performance": [], "increments": [], "descriptions": descriptions, "warnings": warnings, "execution": {"fits": 0, "training_rows": 0, "purged_rows": 0, "mode": "pure_reaggregation"}}
    w = _weights(frame, policy)
    interval_axis = axis
    if contract["dependence"].get("axis_scope") == "evaluation":
        interval_axis = [d for d in axis if any(f["eval_start"] <= d <= f["eval_end"] for f in _folds(contract))]
    models = ["B0", "B1", "B2"] + (["B50"] if binary else [])
    losses: dict[str, np.ndarray] = {}
    mse: dict[str, float] = {}
    for model in models:
        with np.errstate(over="ignore", invalid="ignore"):
            losses[model] = (frame[model].to_numpy(float) - frame.y.to_numpy(float)) ** 2
        if not np.isfinite(losses[model]).all():
            raise EvaluationError("prediction squared error overflow: cannot emit a finite score")
        mse[model] = float(w @ losses[model])
        if model == "B50" and not np.all(losses[model] == 0.25):
            raise EvaluationError("B50 binary score must deterministically equal .25")
        if model == "B50":
            mse[model] = 0.25  # exact diagnostic, independent of floating sum(w)
        counts = {"rows": len(frame), "dates": int(frame.date.nunique()), "assets": int(frame.asset.nunique())}
        performance.append({"model": model, "metric": "Brier" if binary else "MSE", "value": mse[model], "unit": "probability_squared" if binary else "percentage_point_squared", **counts})
        if not binary:
            performance.append({"model": model, "metric": "RMSE", "value": float(np.sqrt(mse[model])), "unit": "percentage_point", **counts})
    for baseline in ["B1", "B0"] + (["B50"] if binary else []):
        difference = losses[baseline] - losses["B2"]
        draws, invalid = _block_draws(frame, difference, interval_axis, policy, contract["dependence"])
        improvement = mse[baseline] - mse["B2"]
        increments.append({"new_model": "B2", "old_model": baseline, "old_value": mse[baseline], "new_value": mse["B2"], "absolute_error_improvement": improvement, "relative_percent": improvement / mse[baseline] * 100 if mse[baseline] > 0 else None, "lo": float(np.quantile(draws, .025)) if len(draws) else None, "hi": float(np.quantile(draws, .975)) if len(draws) else None, "unit": "probability_squared" if binary else "percentage_point_squared", "metric": "Brier" if binary else "MSE", "rows": len(frame), "dates": int(frame.date.nunique()), "assets": int(frame.asset.nunique()), "calendar_dates": len(interval_axis), "block_length": contract["dependence"]["block_length"], "draws": contract["dependence"]["draws"], "valid_draws": len(draws), "unestimable_draws": invalid, "seed": contract["dependence"]["seed"], "weighting": policy, "interpretation": "positive means lower prediction error; not investment return"})
        if improvement < 0:
            warnings.append(f"B2 underperforms {baseline}: valid numerical negative result; do not retune to pass")
        if invalid:
            warnings.append(f"B2 vs {baseline}: {invalid} date-block draws lacked fixed common support and were excluded")
    periods = []
    for year, group in frame.groupby(frame.date.str[:4], sort=True):
        pw = _weights(group, policy)
        old = float(pw @ ((group.B1 - group.y) ** 2).to_numpy())
        new = float(pw @ ((group.B2 - group.y) ** 2).to_numpy())
        periods.append({"year": year, "old_value": old, "new_value": new,
                        "absolute_error_improvement": old-new, "rows": len(group),
                        "dates": int(group.date.nunique()), "assets": int(group.asset.nunique()),
                        "unit": "probability_squared" if binary else "percentage_point_squared"})
    signs = {np.sign(p["absolute_error_improvement"]) for p in periods}
    if -1 in signs and 1 in signs:
        warnings.append("year sign reversal: added-information improvement changes direction across years")
    if frame.date.nunique() < contract["dependence"]["block_length"] * 3:
        warnings.append("few date blocks: the evaluation span contains fewer than three declared blocks; interval evidence is limited")
    return {"predictions": frame.to_dict("records"), "performance": performance, "increments": increments, "descriptions": descriptions, "period_comparisons": periods, "warnings": warnings, "execution": {"fits": 0, "training_rows": 0, "purged_rows": 0, "mode": "pure_reaggregation"}}
