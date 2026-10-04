"""Pure auxiliary summaries of the four frozen color-event outputs; no fitting."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import json
from pathlib import Path
import statistics

from lei_signal.research import workflow_inputs
from lei_signal.research.workflow_evaluation import summarize_predictions

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
PANEL = json.loads((ROOT / "docs/experiments/raw/volume-information-2026-09-30/execution/panel.json").read_text())
BY_ASSET = {a: [] for a in ("510300.SS", "510050.SS", "510500.SS", "588000.SS")}
for bar in PANEL["bars"]:
    if bar["asset"] in BY_ASSET:
        BY_ASSET[bar["asset"]].append(bar)
for asset in BY_ASSET:
    by_day = {r["date"]: r for r in BY_ASSET[asset]}
    BY_ASSET[asset] = [by_day.get(day, {"date": day, "asset": asset, "status": "vendor_missing"}) for day in PANEL["calendar"]]
INDEX = {day: i for i, day in enumerate(PANEL["calendar"])}


def label(asset, day, horizon, kind):
    return workflow_inputs._label(BY_ASSET[asset], INDEX[day], {
        "kind": kind, "start_offset": 1, "end_offset": horizon + 1,
        "entry_field": "close", "path_field": "close", "price_measure": "economic_price"})[0]


def stats(rows):
    if not rows:
        return {"n": 0, "dates": 0}
    values = [r["ret"] for r in rows]
    return {"n": len(rows), "dates": len({r["date"] for r in rows}),
            "mean_return_pp": statistics.mean(values), "up_rate": sum(v > 0 for v in values) / len(values),
            "return_below_minus_5": sum(v < -5 for v in values) / len(values),
            "return_below_minus_10": sum(v < -10 for v in values) / len(values),
            "return_below_minus_15": sum(v < -15 for v in values) / len(values),
            "mean_close_mae_pp": statistics.mean(r["mae"] for r in rows),
            "mean_close_mfe_pp": statistics.mean(r["mfe"] for r in rows),
            "mean_peak_to_trough_pp": statistics.mean(r["peak_to_trough"] for r in rows),
            "mae_over_5_rate": sum(r["mae"] > 5 for r in rows) / len(rows)}


def descriptive(branch):
    qualification = json.loads((HERE / branch / "qualification.json").read_text())
    from lei_signal.research.color_event_information import prepare_observations
    c = json.loads((HERE / branch / ("freeze-01" if branch == "green-return20" else "freeze-02") / "contract.json").read_text())
    obs = [r for r in prepare_observations(PANEL, c, compute_labels=False)["observations"] if r["eligible"]]
    assert len(obs) == qualification["coverage"]["eligible"]
    output = {}
    for horizon in (5, 10, 20, 60, 120):
        rows = []
        for r in obs:
            vals = {kind: label(r["asset"], r["date"], horizon, kind)
                    for kind in ("forward_return", "mae", "mfe", "max_drawdown")}
            if any(v is None for v in vals.values()):
                continue
            rows.append({"asset": r["asset"], "date": r["date"], "week": r["week20_state"],
                         "bull": r["bull_group"], "ret": vals["forward_return"],
                         "mae": vals["mae"], "mfe": vals["mfe"],
                         "peak_to_trough": vals["max_drawdown"]})
        output[str(horizon)] = {"all": stats(rows),
            "week": {w: stats([r for r in rows if r["week"] == w]) for w in ("green", "black", "gray")},
            "bull": {str(b): stats([r for r in rows if r["bull"] is b]) for b in (True, False)},
            "year": {y: stats([r for r in rows if r["date"].startswith(y)]) for y in
                     ("2023", "2024", "2025", "2026")},
            "asset": {a: stats([r for r in rows if r["asset"] == a]) for a in BY_ASSET}}
    return obs, output


def weighted_mse(rows, model):
    assets = sorted({r["asset"] for r in rows})
    if not assets:
        return None
    return statistics.mean(statistics.mean((r[model] - r["y"]) ** 2
                                              for r in rows if r["asset"] == a) for a in assets)


def simple_group_forecasts(obs, predictions, target):
    by_id = {r["id"]: r for r in obs}
    evaluation = []
    for fold in (0, 1):
        period_start = "2025-01-01" if fold == 0 else "2026-01-01"
        train_end = "2024-12-31" if fold == 0 else "2025-12-31"
        train = []
        for r in obs:
            v = label(r["asset"], r["date"], 20, target)
            if r["date"] <= train_end and v is not None and PANEL["calendar"][INDEX[r["date"]] + 21] < period_start:
                train.append((r, v))
        group = defaultdict(list)
        etf = defaultdict(list)
        for r, v in train:
            group[(r["asset"], r["week20_state"])].append(v)
            etf[r["asset"]].append(v)
        for p in predictions:
            if p["fold"] != str(fold):
                continue
            r = by_id[p["id"]]
            values = group.get((r["asset"], r["week20_state"]))
            fallback = not bool(values)
            prediction = statistics.mean(values if values else etf[r["asset"]])
            evaluation.append({**p, "state_only": prediction,
                               "etf_only": statistics.mean(etf[r["asset"]]),
                               "state_train_n": len(values or []),
                               "state_fallback_to_etf": fallback})
    return {"rows": len(evaluation), "fallback_rows": sum(r["state_fallback_to_etf"] for r in evaluation),
            "state_only_mse": weighted_mse(evaluation, "state_only"),
            "etf_training_mean_mse": weighted_mse(evaluation, "etf_only"),
            "pooled_training_mean_mse": weighted_mse(evaluation, "B0")}


def risk_frequency(obs, predictions):
    by_id = {r["id"]: r for r in obs}
    evaluated = []
    for fold in (0, 1):
        start = "2025-01-01" if fold == 0 else "2026-01-01"
        end = "2024-12-31" if fold == 0 else "2025-12-31"
        train = []
        for r in obs:
            mae = label(r["asset"], r["date"], 20, "mae")
            if r["date"] <= end and mae is not None and PANEL["calendar"][INDEX[r["date"]] + 21] < start:
                train.append((r, float(mae > 5)))
        group, etf = defaultdict(list), defaultdict(list)
        for r, event in train:
            group[(r["asset"], r["week20_state"])].append(event)
            etf[r["asset"]].append(event)
        for p in predictions:
            if p["fold"] != str(fold):
                continue
            r = by_id[p["id"]]
            mae = label(r["asset"], r["date"], 20, "mae")
            values = group.get((r["asset"], r["week20_state"]))
            evaluated.append({"asset": r["asset"], "date": r["date"], "actual": float(mae > 5),
                              "etf_frequency": statistics.mean(etf[r["asset"]]),
                              "week_group_frequency": statistics.mean(values if values else etf[r["asset"]]),
                              "fallback": not bool(values)})
    for r in evaluated:
        for model in ("etf_frequency", "week_group_frequency"):
            r[model] = (r[model] - r["actual"]) ** 2
    def mean_score(model):
        return statistics.mean(statistics.mean(r[model] for r in evaluated if r["asset"] == asset)
                               for asset in BY_ASSET)
    return {"rows": len(evaluated), "fallback_rows": sum(r["fallback"] for r in evaluated),
            "observed_risk_rate": statistics.mean(r["actual"] for r in evaluated),
            "etf_training_frequency_brier": mean_score("etf_frequency"),
            "week_group_training_frequency_brier": mean_score("week_group_frequency"),
            "interpretation": "historical training frequencies, not calibrated probabilities"}


def main():
    all_out = {"runs": {}, "cumulative_primary_real_fits": 0, "auxiliary_new_fits": 0,
               "method": "saved prediction aggregation; no new financial model fit"}
    for color in ("green", "black"):
        primary = "green-return20" if color == "green" else "black-mae20"
        obs, desc = descriptive(primary)
        for target in ("forward_return", "mae"):
            branch = color + ("-return20" if target == "forward_return" else "-mae20")
            out = HERE / branch / "core-01"
            result = json.loads((out / "result.json").read_text())
            c = json.loads((out / "contract.json").read_text())
            modified = deepcopy(c)
            modified["dependence"]["block_length"] = 60
            grouped = summarize_predictions(result["predictions"], modified)
            by_etf = {}
            leave_one = {}
            for asset in BY_ASSET:
                subset = [r for r in result["predictions"] if r["asset"] == asset]
                others = [r for r in result["predictions"] if r["asset"] != asset]
                by_etf[asset] = {"rows": len(subset), "B1_MSE": weighted_mse(subset, "B1"),
                                 "B2_MSE": weighted_mse(subset, "B2")}
                leave_one[asset] = {"rows": len(others), "B1_MSE": weighted_mse(others, "B1"),
                                    "B2_MSE": weighted_mse(others, "B2")}
            all_out["runs"][branch] = {"fits": result["execution"]["fits"],
                "descriptive_by_horizon": desc, "state_only_training_group_mean": simple_group_forecasts(obs, result["predictions"], target),
                "risk_frequency": risk_frequency(obs, result["predictions"]) if target == "mae" else None,
                "uncertainty_60day_full_calendar": grouped["increments"],
                "per_etf_saved_prediction": by_etf, "leave_one_etf_saved_prediction": leave_one}
            all_out["cumulative_primary_real_fits"] += result["execution"]["fits"]
    path = HERE / "auxiliary.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(all_out, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({"cumulative_primary_real_fits": all_out["cumulative_primary_real_fits"],
                      "branches": list(all_out["runs"])},ensure_ascii=False))


if __name__ == "__main__":
    main()
