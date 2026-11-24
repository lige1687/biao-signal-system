"""Offline retrospective diagnostics, separate from prediction and account attribution.

Realized same-month factors are unavailable at the start of that month. Outputs
are conditional economic-index explanations, never trade returns or forecasts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.research.factor_lab.benchmarks import load_published_returns

ASSETS = ("510300.SS", "510050.SS", "510500.SS", "512100.SS", "159915.SZ", "588000.SS")
REFS = ("reference.ch3.mktrf@1.0.0", "reference.ch3.smb@1.0.0", "reference.ch3.vmg@1.0.0")
MODELS = {"M0": [], "M1": ["mktrf"], "MX": ["SMB", "VMG"], "M3": ["mktrf", "SMB", "VMG"]}
QUALIFIED_USE = "limited_retrospective_economic_index_month_change_attribution_only"


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def _bound(binding, root):
    path = (root / binding["path"]).resolve()
    if _hash(path) != binding["sha256"]:
        raise ValueError(f"input hash mismatch: {path}")
    return path


def block_interval(values, length, draws, seed):
    """Paired circular blocks; values already average assets within each date."""
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all() or len(values) < length or length < 1:
        raise ValueError("invalid finite date series or block length")
    if type(draws) is not int or draws < 1:
        raise ValueError("draws must be a positive integer")
    rng = np.random.default_rng(seed)
    n = len(values)
    starts = rng.integers(0, n, size=(draws, int(np.ceil(n / length))))
    indexes = (starts[..., None] + np.arange(length)) % n
    means = values[indexes.reshape(draws, -1)[:, :n]].mean(axis=1)
    return np.quantile(means, [0.025, 0.975]).tolist()


def _calendar(path):
    data = _json(path)
    if "days" in data:
        dates = sorted(d for d, value in data["days"].items() if value["is_trading_day"])
    else:
        dates = data["dates"]
    if dates != sorted(set(dates)):
        raise ValueError("calendar must be sorted and unique")
    parsed = pd.to_datetime(dates, format="%Y-%m-%d", errors="raise")
    return (
        pd.Series(dates, index=parsed.to_period("M").astype(str)).groupby(level=0).last().to_dict()
    )


def _prepare(protocol_path, out_dir):
    p = _json(protocol_path)
    root = Path(p.get("root", ".")).expanduser().resolve()
    out = Path(out_dir).resolve()
    if out.exists():
        raise ValueError("output directory already exists")
    expected = {
        "schema_version": "classic-attribution/1.0",
        "purpose": "retrospective_attribution",
        "read_only_local": True,
        "market": "CN",
        "currency": "CNY",
        "frequency": "monthly",
        "target": "conditional_economic_index_month_change_minus_rf_once",
        "factor_timing": "same_month_realized_ex_post",
        "unit": "decimal",
    }
    if any(p.get(key) != value for key, value in expected.items()):
        raise ValueError(
            "only declared CN/CNY/monthly retrospective decimal explanation is supported"
        )
    if sorted(p.get("assets", [])) != sorted(ASSETS):
        raise ValueError("the bounded study requires the six specified ETFs")
    train, evaluation = p["train_months"], p["evaluation_months"]
    if train != pd.period_range("2022-01", "2023-12", freq="M").astype(str).tolist():
        raise ValueError("training months must be fixed 2022-01 through 2023-12")
    if evaluation != pd.period_range("2024-01", "2026-06", freq="M").astype(str).tolist():
        raise ValueError("evaluation months must be fixed 2024-01 through 2026-06")
    if p.get("resampling") != {"block_lengths": [3, 6], "draws": 2000, "seed": 20261002}:
        raise ValueError("resampling differs from the bounded design")
    if len(p.get("strategy_files", [])) != 2:
        raise ValueError("two frozen strategy sources are required")
    for item in p["strategy_files"] + p.get("source_files", []):
        _bound(item, root)
    required_code = {
        "classic_attribution.py",
        "benchmarks.py",
        "definitions.py",
        "run_factor_lab.py",
    }
    if required_code - {Path(item["path"]).name for item in p.get("code_files", [])}:
        raise ValueError("required code fingerprints missing")
    resolved_code = [_bound(item, root) for item in p["code_files"]]
    if Path(__file__).resolve() not in resolved_code:
        raise ValueError("executing module not included in code bindings")
    qualification = _json(_bound(p["qualification"], root))
    if qualification.get("qualified_for") != QUALIFIED_USE:
        raise ValueError("economic-index qualification missing or incompatible")
    registry = _json(_bound(p["registry"], root))
    cards = {o["id"] + "@" + o["version"]: o for o in registry["objects"]}
    if sorted(p.get("definition_refs", [])) != sorted(REFS):
        raise ValueError("exact CH3 definition refs required")
    for ref in REFS:
        if (
            ref not in cards
            or cards[ref]["type"] != "factor_return"
            or "attribution" not in cards[ref]["uses"]
        ):
            raise ValueError("definition incompatible with retrospective attribution")
    snapshot = p["snapshot"]
    factors = load_published_returns(
        snapshot, root=root, market="CN", frequency="monthly", currency="CNY"
    )
    if not {"month", "rf_mon", "mktrf", "SMB", "VMG"} <= set(factors):
        raise ValueError("CH3 fields required")
    if factors.month.duplicated().any() or not factors.month.is_monotonic_increasing:
        raise ValueError("factor months must be unique and sorted")
    months = train + evaluation
    factors = factors.set_index("month")
    if not set(months) <= set(factors.index):
        raise ValueError("missing required factor months")
    factors = factors.loc[months, ["rf_mon", "mktrf", "SMB", "VMG"]]
    if not np.isfinite(factors.to_numpy(dtype=float)).all():
        raise ValueError("factor values missing or nonfinite")
    ends = _calendar(_bound(p["calendar"], root))
    all_months = ["2021-12"] + months
    if not set(all_months) <= set(ends):
        raise ValueError("calendar does not cover required endpoints")
    inputs = p["economic_inputs"]
    if sorted(item["symbol"] for item in inputs) != sorted(ASSETS):
        raise ValueError("economic inputs must contain each specified ETF exactly once")
    rows = []
    for item in inputs:
        date_col, price_col = item["date_column"], item["price_column"]
        frames = [
            pd.read_csv(_bound(b, root), usecols=[date_col, price_col]) for b in item["files"]
        ]
        prices = pd.concat(frames, ignore_index=True).rename(
            columns={date_col: "date", price_col: "price"}
        )
        if prices.date.duplicated().any() or not prices.date.is_monotonic_increasing:
            raise ValueError("price dates must be unique and sorted across input files")
        pd.to_datetime(prices.date, format="%Y-%m-%d", errors="raise")
        prices = prices.set_index("date").price
        if not np.isfinite(prices.to_numpy(dtype=float)).all() or (prices <= 0).any():
            raise ValueError("economic prices must be positive finite")
        if not {ends[m] for m in all_months} <= set(prices.index):
            raise ValueError("missing exact calendar month-end price; no last-observation fallback")
        for i, month in enumerate(months, 1):
            previous = all_months[i - 1]
            start, end = float(prices[ends[previous]]), float(prices[ends[month]])
            gross = end / start - 1
            f = factors.loc[month]
            rows.append(
                {
                    "symbol": item["symbol"],
                    "month": month,
                    "start_date": ends[previous],
                    "end_date": ends[month],
                    "start_level": start,
                    "end_level": end,
                    "economic_change": gross,
                    "target": gross - float(f.rf_mon),
                    **{col: float(f[col]) for col in factors.columns},
                    "split": "train" if month in train else "evaluation",
                }
            )
    panel = pd.DataFrame(rows)
    # Validate every design before any fit, rather than partially fitting an invalid batch.
    for _, group in panel[panel.split == "train"].groupby("symbol"):
        for columns in MODELS.values():
            matrix = np.column_stack([np.ones(len(group)), group[columns].to_numpy()])
            if np.linalg.matrix_rank(matrix) != matrix.shape[1]:
                raise ValueError("training model matrix is rank deficient")
    return p, panel, out


def _summary(frame, models, key):
    return {
        model: {
            "mse_pp2": float(frame[f"{model}_loss_pp2"].mean()),
            "rmse_pp": float(np.sqrt(frame[f"{model}_loss_pp2"].mean())),
            "rows": len(frame),
            "dates": int(frame[key].nunique()),
            "assets": int(frame.symbol.nunique()),
        }
        for model in models
    }


def _stability(frame, key, old, new, delete_block=0):
    data = frame.copy()
    data["improvement_pp2"] = data[f"{old}_loss_pp2"] - data[f"{new}_loss_pp2"]
    data["year"] = data[key].str[:4]
    result = {"by_asset": [], "by_year": [], "leave_one_asset_out": [], "leave_one_date_out": []}
    for column, label in [("symbol", "by_asset"), ("year", "by_year")]:
        for value, group in data.groupby(column):
            result[label].append(
                {
                    column: value,
                    "rows": len(group),
                    "dates": int(group[key].nunique()),
                    "baseline_mse_pp2": float(group[f"{old}_loss_pp2"].mean()),
                    "augmented_mse_pp2": float(group[f"{new}_loss_pp2"].mean()),
                    "improvement_pp2": float(group.improvement_pp2.mean()),
                }
            )
    for symbol in sorted(data.symbol.unique()):
        result["leave_one_asset_out"].append(
            {
                "excluded": symbol,
                "improvement_pp2": float(data.loc[data.symbol != symbol, "improvement_pp2"].mean()),
            }
        )
    dates = sorted(data[key].unique())
    for date in dates:
        result["leave_one_date_out"].append(
            {
                "excluded": date,
                "improvement_pp2": float(data.loc[data[key] != date, "improvement_pp2"].mean()),
            }
        )
    if delete_block:
        result["leave_block_out"] = []
        for i in range(len(dates) - delete_block + 1):
            excluded = dates[i : i + delete_block]
            result["leave_block_out"].append(
                {
                    "excluded": excluded,
                    "improvement_pp2": float(
                        data.loc[~data[key].isin(excluded), "improvement_pp2"].mean()
                    ),
                }
            )
    return result


def run_attribution(protocol_path, out_dir):
    """Run a frozen, bounded retrospective study; all validation precedes fitting."""
    protocol_path = Path(protocol_path).resolve()
    p, panel, out = _prepare(protocol_path, out_dir)
    explanations, coefficients = [], []
    for symbol, group in panel.groupby("symbol", sort=True):
        training = group[group.split == "train"]
        evaluation = group[group.split == "evaluation"].copy()
        for model, columns in MODELS.items():
            x = np.column_stack([np.ones(len(training)), training[columns].to_numpy()])
            tx = np.column_stack([np.ones(len(evaluation)), evaluation[columns].to_numpy()])
            coef = (
                np.array([training.target.mean()])
                if not columns
                else np.linalg.lstsq(x, training.target.to_numpy(), rcond=None)[0]
            )
            coefficients.append(
                {
                    "symbol": symbol,
                    "model": model,
                    "intercept": float(coef[0]),
                    **{
                        column: float(value)
                        for column, value in zip(columns, coef[1:], strict=True)
                    },
                    "training_months": len(training),
                }
            )
            evaluation[model] = tx @ coef
            evaluation[f"{model}_loss_pp2"] = ((evaluation.target - evaluation[model]) * 100) ** 2
        explanations.append(evaluation)
    predictions = pd.concat(explanations, ignore_index=True).sort_values(["month", "symbol"])
    performance = _summary(predictions, MODELS, "month")
    date_delta = (
        predictions.groupby("month", sort=True)
        .apply(lambda g: float((g.M1_loss_pp2 - g.M3_loss_pp2).mean()), include_groups=False)
        .to_numpy()
    )
    improvement = performance["M1"]["mse_pp2"] - performance["M3"]["mse_pp2"]
    increments = {
        "baseline": "M1",
        "candidate": "M3",
        "improvement_pp2": improvement,
        "relative_percent": improvement / performance["M1"]["mse_pp2"] * 100
        if performance["M1"]["mse_pp2"]
        else None,
        "intervals": {str(b): block_interval(date_delta, b, 2000, 20261002) for b in (3, 6)},
    }
    results = {
        "purpose": "retrospective_attribution",
        "fit_count": 24,
        "ols_fits": 18,
        "training_means": 6,
        "models": performance,
        "increment": increments,
        "stability": _stability(predictions, "month", "M1", "M3", delete_block=6),
        "coverage": {
            "assets": 6,
            "training_months_each": 24,
            "evaluation_months_each": 30,
            "monthly_panel_rows": len(panel),
            "evaluation_rows": len(predictions),
            "exclusions": [],
            "calendar_assumption": "frozen supplied calendar; no independent SSE certification",
        },
        "limitations": [
            "same-month realized factors are not forecasts",
            "economic index is not account return",
            "conditional fixed-coefficient exploratory intervals; no independent new evidence",
            "source revisions, action completeness and publication times are not certified",
        ],
    }
    out.mkdir(parents=True, exist_ok=False)
    panel.to_csv(out / "monthly-panel.csv", index=False)
    predictions.to_csv(out / "explanations.csv", index=False)
    pd.DataFrame(coefficients).to_csv(out / "coefficients.csv", index=False)
    _write(out / "results.json", results)
    _write(
        out / "model-card.json",
        {
            "outcome": p["target"],
            "factors": list(REFS),
            "models": MODELS,
            "market": "CN",
            "currency": "CNY",
            "frequency": "monthly",
            "rf": "subtract rf_mon from target exactly once; leave factor returns unchanged",
            "train": p["train_months"],
            "evaluation": p["evaluation_months"],
            "estimation": "separate ETF intercept OLS; fixed coefficients; no tuning",
            "uncertainty": p["resampling"],
            "interpretation": "intercept and residual are not unique alpha",
            "qualification": p["qualification"],
        },
    )
    _write(
        out / "attempt.json",
        {
            "protocol_sha256": _hash(protocol_path),
            "status": "completed",
            "ols_fits": 18,
            "training_means": 6,
            "parameter_search": False,
        },
    )
    _write(
        out / "manifest.json",
        {
            "schema_version": "classic-attribution-output/1.0",
            "protocol": str(protocol_path),
            "protocol_sha256": _hash(protocol_path),
            "source_and_code_bindings": p,
            "outputs": {f.name: _hash(f) for f in sorted(out.iterdir())},
        },
    )
    return results


def compare_saved_predictions(path, *, calendar_dates, duplicate_models=None):
    """Reuse saved forecasts without fitting; strict common keys and calendar."""
    raw = pd.read_csv(path)
    if raw.duplicated(["date", "symbol", "question_id"]).any():
        raise ValueError("duplicate saved forecast keys")

    def extract(question, column):
        subset = raw[raw.question_id == question][["date", "symbol", "target", column]].copy()
        if subset.empty:
            raise ValueError(f"missing saved model: {question}")
        return subset.set_index(["date", "symbol"]).sort_index().rename(columns={column: "value"})

    baseline = extract("已有SMA再加EMA", "augmented")
    augmented = extract("完整信息增加双确认组合表示", "baseline")
    if not baseline.index.equals(augmented.index) or not np.allclose(
        baseline.target, augmented.target, rtol=0, atol=1e-12
    ):
        raise ValueError("saved forecast targets or common keys differ")
    frame = (
        baseline.rename(columns={"value": "S+E"})
        .join(augmented[["value"]].rename(columns={"value": "S+E+X"}))
        .reset_index()
    )
    dates = sorted(frame.date.unique())
    if calendar_dates != sorted(set(calendar_dates)) or dates != calendar_dates:
        raise ValueError("saved forecasts are not consecutive on the declared trading calendar")
    expected_keys = {(date, symbol) for date in dates for symbol in ASSETS}
    if set(zip(frame.date, frame.symbol, strict=True)) != expected_keys:
        raise ValueError("six-ETF complete common observations required")
    checks = duplicate_models or {
        "S+E": [("已有EMA再加SMA", "augmented")],
        "S+E+X": [
            ("SMA加历史收益波动后再加EMA", "augmented"),
            ("EMA加历史收益波动后再加SMA", "augmented"),
        ],
    }
    for model, copies in checks.items():
        for question, column in copies:
            if duplicate_models is None and question not in set(raw.question_id):
                continue
            duplicate = extract(question, column)
            selected = baseline if model == "S+E" else augmented
            if not duplicate.index.equals(selected.index) or not np.allclose(
                duplicate.to_numpy(), selected.to_numpy(), rtol=0, atol=1e-12
            ):
                raise ValueError("repeated saved model or target differs")
    if not np.isfinite(frame[["target", "S+E", "S+E+X"]].to_numpy()).all():
        raise ValueError("nonfinite saved forecasts")
    frame["fixed_zero"] = 0.0
    for model in ("fixed_zero", "S+E", "S+E+X"):
        frame[f"{model}_loss_pp2"] = ((frame.target - frame[model]) * 100) ** 2
    models = _summary(frame, ("fixed_zero", "S+E", "S+E+X"), "date")
    delta = (frame["S+E_loss_pp2"] - frame["S+E+X_loss_pp2"]).groupby(frame.date).mean().to_numpy()
    result = {
        "fit_count": 0,
        "source_sha256": _hash(path),
        "models": models,
        "increment": {
            "improvement_pp2": float(delta.mean()),
            "interval_pp2": block_interval(delta, 60, 2000, 20260928),
        },
        "stability": _stability(frame, "date", "S+E", "S+E+X"),
        "scope": "post-hoc joint return20+volatility20 representation; not complete LEI increment",
        "candidate_only": "not stored in the historical outputs; not estimated",
    }
    return result
