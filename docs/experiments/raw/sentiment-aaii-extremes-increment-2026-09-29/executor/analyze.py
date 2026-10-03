#!/usr/bin/env python3
"""Frozen local arithmetic only. No network, global-object consumers or trading.

Default invocation performs ONLY synthetic checks. Real run requires controller
code review followed by explicit --run-reviewed; run-01 is never overwritten.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROTOCOL_HASH = "e9ce1b5a60b306ef016a6ac4f0d88b81cb6d3ddb0140b8a5cea82ea9eca904ab"
SOURCE_HASHES = {
    "aaii-candidate-values.csv": "12f30895c7ea2c68663a60f2d60a85384dfd0d9d324474e0501298e460cf9c05",
    "px_SPY.csv": "952f397be0ccc5745185b91cce6acc781737c0f30a7a34aa8a230ae892ed5e45",
}
BASE = ["r20", "r63", "dma200", "dd252", "rv20"]
MODELS = {"I": [], "X": ["x"], "XE": ["x", "lo", "hi"],
          "B": BASE, "BX": BASE + ["x"], "BXE": BASE + ["x", "lo", "hi"]}
PAIRS = [("BXE", "B"), ("BX", "B"), ("BXE", "BX")]
HORIZONS = [5, 20, 60, 120, 252]
CUTOFF = pd.Timestamp("2026-06-30")
START = pd.Timestamp("1995-01-01")
EVAL = pd.Timestamp("2010-01-01")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, np.ndarray):
        return jsonable(obj.tolist())
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return float(obj) if np.isfinite(obj) else None
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def write_json(path, obj):
    Path(path).write_text(json.dumps(jsonable(obj), ensure_ascii=False,
                                   indent=2, allow_nan=False) + "\n")


def check_bindings():
    if sha(ROOT / "protocol.json") != PROTOCOL_HASH:
        raise RuntimeError("STOP: frozen protocol drift")
    inputs = {}
    for name, expected in SOURCE_HASHES.items():
        path = ROOT / "inputs" / name
        actual = sha(path)
        if actual != expected:
            raise RuntimeError(f"STOP: frozen input drift: {name}")
        inputs[name] = {"sha256": actual, "bytes": path.stat().st_size}
    # Shared authority changes are recorded separately; none of these files
    # supplies executable definitions for this frozen, local arithmetic branch.
    manifest = json.loads((ROOT / "source-manifest.json").read_text())
    authority = []
    for rec in manifest["files"]:
        if "role" in rec:
            p = Path(rec["source_path"])
            actual = sha(p) if p.exists() else None
            authority.append({"path": str(p), "role": rec["role"],
                              "bound_sha256": rec["sha256"], "actual_sha256": actual,
                              "changed": actual != rec["sha256"]})
    return {"protocol_sha256": PROTOCOL_HASH, "inputs": inputs,
            "source_manifest_sha256": sha(ROOT / "source-manifest.json"),
            "authority_audit": authority}


def prepare_prices(frame):
    """Retain every quote position, including missing closes. Never dropna."""
    p = frame.copy()
    p["Date"] = pd.to_datetime(p["Date"], errors="raise").dt.normalize()
    if p["Date"].isna().any() or p["Date"].duplicated().any():
        raise RuntimeError("STOP: invalid or duplicate quote date")
    p = p.sort_values("Date", kind="stable").reset_index(drop=True)
    p["Close"] = pd.to_numeric(p["Close"], errors="coerce")
    # Invalid entries keep their positions but make all relevant windows invalid.
    p.loc[~np.isfinite(p["Close"]) | (p["Close"] <= 0), "Close"] = np.nan
    c = p["Close"]
    p["r20"] = 100 * (c / c.shift(20) - 1)
    p["r63"] = 100 * (c / c.shift(63) - 1)
    p["dma200"] = 100 * (c / c.rolling(200, min_periods=200).mean() - 1)
    p["dd252"] = 100 * (c / c.rolling(252, min_periods=252).max() - 1)
    ret = c.pct_change(fill_method=None)
    p["rv20"] = 100 * ret.rolling(20, min_periods=20).std(ddof=1) * np.sqrt(20)
    return p


def group(x):
    return "low" if x <= -25 else "high" if x >= 25 else "neutral"


def observations(survey, prices, h):
    s = survey.copy()
    s["source_date"] = pd.to_datetime(s["date"], errors="raise").dt.normalize()
    if s["source_date"].isna().any():
        raise RuntimeError("STOP: missing survey date")
    s["source_row"] = np.arange(len(s))
    s = s.sort_values(["source_date", "source_row"], kind="stable")
    dates = prices["Date"].to_numpy(dtype="datetime64[ns]")
    c = prices["Close"].to_numpy()
    rows = []
    for source in s.to_dict("records"):
        d = source["source_date"]
        assumed = d + pd.Timedelta(days=7)
        # Date-only quotes occur strictly after assumed day local 23:59.
        k = int(np.searchsorted(dates, assumed.to_datetime64(), side="right"))
        x = 100 * (float(source["bullish"]) - float(source["bearish"]))
        r = {"source_row": source["source_row"], "source_date": d,
             "assumed_available": assumed + pd.Timedelta(hours=23, minutes=59),
             "t": pd.NaT, "t_index": k, "target_start": pd.NaT,
             "target_end": pd.NaT, "target_start_index": k+1,
             "target_end_index": k+1+h, "h": h, "x": x,
             "lo": max(-25-x, 0), "hi": max(x-25, 0),
             "group": group(x), "y": np.nan, "eligible": False,
             **{col: np.nan for col in BASE}}
        reasons = []
        if k >= len(prices):
            reasons.append("no_quote_after_assumed_date")
        else:
            r["t"] = prices.at[k, "Date"]
            for col in BASE:
                r[col] = prices.at[k, col]
            if not (START <= r["t"] <= CUTOFF):
                reasons.append("observation_outside_range")
            if not np.isfinite([r[z] for z in ["x"] + BASE]).all():
                reasons.append("nonfinite_x_or_baseline")
            a, b = k+1, k+1+h
            if a < len(prices):
                r["target_start"] = prices.at[a, "Date"]
            if b < len(prices):
                r["target_end"] = prices.at[b, "Date"]
            if b >= len(prices):
                reasons.append("incomplete_target_quotes")
            elif prices.at[a, "Date"] > CUTOFF or prices.at[b, "Date"] > CUTOFF:
                reasons.append("target_beyond_cutoff")
            elif not np.isfinite(c[a:b+1]).all():
                reasons.append("nonfinite_target_path")
            else:
                r["y"] = 100 * (c[b] / c[a] - 1)
        r["exclusion"] = "|".join(reasons)
        rows.append(r)
    out = pd.DataFrame(rows)
    # Latest source date wins, with latest physical source row as deterministic tie.
    duplicate = out["t"].notna() & out.duplicated("t", keep="last")
    for idx in out.index[duplicate]:
        out.at[idx, "exclusion"] += ("|" if out.at[idx, "exclusion"] else "") + "duplicate_t_keep_latest_source"
    out["eligible"] = out["exclusion"].eq("") & np.isfinite(out["y"])
    return out.sort_values(["t", "source_date", "source_row"], kind="stable").reset_index(drop=True)


def train_mask(obs, year):
    boundary = pd.Timestamp(f"{year}-01-01")
    return obs["eligible"] & (obs["t"] >= START) & (obs["t"] < boundary) & (obs["target_end"] < boundary)


def fit_ols(train, features):
    if len(train) < 100:
        raise RuntimeError("STOP: fewer than 100 matured training rows")
    a = train[features].to_numpy(float)
    mean, scale = a.mean(axis=0), a.std(axis=0, ddof=0)
    if not np.isfinite(a).all() or not np.isfinite(train["y"]).all() or (scale == 0).any():
        raise RuntimeError("STOP: nonfinite training or zero feature scale")
    design = np.column_stack([np.ones(len(train)), (a-mean)/scale])
    beta, _, rank, singular = np.linalg.lstsq(design, train["y"].to_numpy(float), rcond=None)
    if rank != design.shape[1]:
        raise RuntimeError("STOP: rank deficient design")
    return {"features": features, "mean": mean, "scale": scale,
            "beta": beta, "rank": int(rank), "singular_values": singular,
            "train_rows": len(train), "train_label_end_max": train["target_end"].max(),
            "train_t_max": train["t"].max()}


def predict(frame, fit):
    a = frame[fit["features"]].to_numpy(float)
    z = (a-fit["mean"])/fit["scale"]
    return np.column_stack([np.ones(len(frame)), z]) @ fit["beta"]


def annual_predictions(obs):
    rows, fits = [], []
    for year in range(2010, 2027):
        tr = obs.loc[train_mask(obs, year)]
        ev = obs.loc[obs["eligible"] & (obs["t"].dt.year == year)].copy()
        if ev.empty:
            continue  # No immature-label shortening and no meaningless empty-year fit.
        for model, features in MODELS.items():
            fit = fit_ols(tr, features)
            fit.update({"year": year, "model": model})
            fits.append(fit)
            ev["pred_" + model] = predict(ev, fit)
        rows.append(ev)
    if not rows:
        raise RuntimeError("STOP: no evaluation observations")
    return pd.concat(rows, ignore_index=True), fits


def scores(frame):
    n = len(frame)
    if not n:
        return {"n": 0, "status": "not_evaluated", "mse": None, "improvement_pct": None}
    mse = {m: float(np.mean((frame["y"]-frame["pred_"+m])**2)) for m in MODELS}
    return {"n": n, "mse": mse,
            "improvement_pct": {f"{m}_vs_{b}": 100*(1-mse[m]/mse[b]) if mse[b] > 0 else None for m,b in PAIRS},
            "squared_error_reduction_sum": {f"{m}_vs_{b}": n*(mse[b]-mse[m]) for m,b in PAIRS}}


def run_counts(full_observations, pred):
    # Establish runs over full chronological evaluation survey population before
    # eligibility filtering, so missing observations cannot join distinct runs.
    seq = full_observations.loc[(full_observations["t"] >= EVAL) & (full_observations["t"] <= CUTOFF)].copy()
    seq = seq.loc[~seq["exclusion"].str.contains("duplicate_t")].sort_values("source_date")
    breaks = seq["group"].ne(seq["group"].shift()) | seq["source_date"].diff().gt(pd.Timedelta(days=14))
    seq["run_id"] = breaks.cumsum()
    counts = {}
    for g in ["low", "neutral", "high"]:
        allg = seq.loc[seq["group"] == g]
        eligible_ids = set(pred.loc[pred["group"] == g, "source_row"])
        counts[g] = {"survey_rows": len(allg), "all_runs": int(allg["run_id"].nunique()),
                     "runs_with_mature_eligible_rows": int(allg.loc[allg["source_row"].isin(eligible_ids), "run_id"].nunique())}
    return counts


def coverage(obs, pred):
    eligible = obs.loc[obs["eligible"]].copy()
    codes = obs["exclusion"].str.split("|").explode()
    codes = codes.loc[codes != ""].value_counts().to_dict()
    overlap = pred[["source_row", "target_start_index", "target_end_index"]].copy()
    # h return intervals indexed [start,end), an endpoint shared alone is not overlap.
    start = overlap["target_start_index"].to_numpy()
    end = overlap["target_end_index"].to_numpy()
    spans = np.maximum(0, np.minimum(end[:-1], end[1:])-np.maximum(start[:-1], start[1:]))
    overlap["next_target_overlap_return_segments"] = np.r_[spans, np.nan] if len(pred) else []
    return {"source_rows": len(obs), "eligible_all_years": len(eligible),
            "evaluation_rows": len(pred), "exclusion_counts_nonexclusive": codes,
            "eval_first_t": pred["t"].min(), "eval_last_t": pred["t"].max(),
            "adjacent_pairs": max(len(pred)-1, 0), "overlapping_adjacent_pairs": int((spans > 0).sum()),
            "eval_adjacent_source_gaps_over14days": int(pred["source_date"].diff().gt(pd.Timedelta(days=14)).sum()),
            "adjacent_overlap_segments_mean": float(spans.mean()) if len(spans) else None,
            "max_overlap_segments": int(spans.max()) if len(spans) else None}, overlap


def moving_blocks(pred, h):
    n, block, draws = len(pred), 52, 2000
    if n < block:
        raise RuntimeError("STOP: fewer than 52 evaluation survey rows")
    rng = np.random.default_rng(20260929+h)
    loss = np.column_stack([(pred["y"]-pred["pred_"+m])**2 for m in MODELS])
    model_idx = {m: i for i,m in enumerate(MODELS)}
    out = []
    for draw in range(draws):
        starts = rng.integers(0, n-block+1, size=math.ceil(n/block))
        indices = np.concatenate([np.arange(k,k+block) for k in starts])[:n]
        mse = loss[indices].mean(axis=0)
        row = {"draw": draw, "seed": 20260929+h, "n": n, "block_rows": block,
               "block_starts": json.dumps(starts.tolist(), separators=(",", ":"))}
        row.update({"mse_"+m: mse[i] for m,i in model_idx.items()})
        row.update({f"improvement_{m}_vs_{b}": 100*(1-mse[model_idx[m]]/mse[model_idx[b]]) if mse[model_idx[b]] > 0 else np.nan for m,b in PAIRS})
        out.append(row)
    frame = pd.DataFrame(out)
    intervals = {f"{m}_vs_{b}": {"valid_draws": int(frame[f"improvement_{m}_vs_{b}"].notna().sum()),
                  "p2_5": frame[f"improvement_{m}_vs_{b}"].quantile(.025),
                  "p97_5": frame[f"improvement_{m}_vs_{b}"].quantile(.975)} for m,b in PAIRS}
    return frame, intervals


def horizon_results(obs, pred, h):
    full = scores(pred)
    counts = run_counts(obs, pred)
    raw, errors = {}, {}
    for g in ["low", "neutral", "high"]:
        f = pred.loc[pred["group"] == g]
        raw[g] = {**counts[g], "eligible_n": len(f), "mean_y": f["y"].mean(),
                  "median_y": f["y"].median(), "up_share": float((f["y"] > 0).mean()) if len(f) else None}
        errors[g] = scores(f)
        errors[g]["share_of_total_squared_error_reduction"] = {
            key: (val / full["squared_error_reduction_sum"][key] if full["squared_error_reduction_sum"][key] != 0 else None)
            for key,val in errors[g].get("squared_error_reduction_sum", {}).items()}
    cov, overlap = coverage(obs, pred)
    return {"h": h, "overall": full, "coverage": cov, "raw_groups": raw,
            "raw_group_mean_differences": {"low_minus_neutral": raw["low"]["mean_y"]-raw["neutral"]["mean_y"],
                                           "high_minus_neutral": raw["high"]["mean_y"]-raw["neutral"]["mean_y"]},
            "group_errors": errors,
            "annual": {year: scores(pred.loc[pred["t"].dt.year == year]) for year in range(2010,2027)},
            "bands": {label: scores(pred.loc[pred["t"].dt.year.between(a,b)]) for label,a,b in [("2010-2014",2010,2014),("2015-2019",2015,2019),("2020-2026H1",2020,2026)]},
            "remove_year_no_refit": {year: scores(pred.loc[pred["t"].dt.year != year]) for year in range(2010,2027)},
            "remove_group_no_refit": {g: scores(pred.loc[pred["group"] != g]) for g in ["low", "high"]}}, overlap


def real_run():
    output = HERE / "run-01"
    if output.exists():
        raise RuntimeError("STOP: run-01 already exists; never overwrite")
    binding = check_bindings()
    output.mkdir()  # Existing directory is an irreversible refusal, even if failed.
    started = datetime.now(timezone.utc)
    try:
        survey = pd.read_csv(ROOT / "inputs/aaii-candidate-values.csv")
        prices = prepare_prices(pd.read_csv(ROOT / "inputs/px_SPY.csv"))
        results, fit_count = {}, 0
        for h in HORIZONS:
            obs = observations(survey, prices, h)
            pred, fits = annual_predictions(obs)
            fit_count += len(fits)
            if fit_count > 510:
                raise RuntimeError("STOP: fit budget exceeded")
            result, overlap = horizon_results(obs, pred, h)
            draws, intervals = moving_blocks(pred, h)
            result["paired_block_intervals"] = intervals
            results[str(h)] = result
            obs.to_csv(output / f"observations-h{h}.csv", index=False, float_format="%.17g")
            pred.to_csv(output / f"predictions-h{h}.csv", index=False, float_format="%.17g")
            overlap.to_csv(output / f"overlap-h{h}.csv", index=False)
            write_json(output / f"fits-h{h}.json", fits)
            draws.to_csv(output / f"draws-h{h}.csv", index=False, float_format="%.17g")
            if sum(p.stat().st_size for p in output.iterdir()) > 20*1024*1024:
                raise RuntimeError("STOP: output budget exceeded")
        final_binding = check_bindings()
        # check_bindings itself rejects protocol/input drift. Shared standards
        # are audited at both ends, not allowed to silently redefine arithmetic.
        write_json(output / "results.json", {"protocol_id": "sentiment.aaii-extremes-increment@1.0.0",
                   "primary_horizon": 120, "horizons": results, "fit_count": fit_count,
                   "metric_unit": "relative MSE reduction percent; NOT investment return",
                   "y_unit": "percentage points of adjusted price change",
                   "columns": {"eligible": "all six models use identical finite x/B/y population per horizon",
                               "beta": "intercept first, then standardized features in listed order",
                               "block_starts": "0-based positions into chronological predictions, contiguous blocks truncated to n",
                               "exclusion": "pipe-separated reasons, counts nonexclusive"},
                   "limitations": ["historical release/revision timestamps unknown; date+7 proxy",
                                   "historical price adjustment vintages unproven; closes not execution prices",
                                   "already viewed exploratory family; not independent validation",
                                   "fixed 52-row blocks do not refit and do not cover full model uncertainty",
                                   "discontinuous block boundaries and long-range dependence remain"]})
        manifest = {**binding, "status": "completed", "started_at": started,
                    "authority_audit_after_run": final_binding["authority_audit"],
                    "source_manifest_sha256_after_run": final_binding["source_manifest_sha256"],
                    "completed_at": datetime.now(timezone.utc), "fit_count": fit_count,
                    "code_sha256": sha(__file__), "python": platform.python_version(),
                    "numpy": np.__version__, "pandas": pd.__version__, "argv": sys.argv,
                    "global_definition_consumers_called": False, "network_requests": 0,
                    "core_batches": 1, "pro_calls": 0,
                    "outputs": {p.name: {"sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir())}}
        write_json(output / "manifest.json", manifest)
        if sum(p.stat().st_size for p in output.iterdir()) > 20*1024*1024:
            raise RuntimeError("STOP: final output budget exceeded")
    except Exception as exc:
        write_json(output / "failure.json", {"status": "stopped", "error": str(exc),
                                             "started_at": started, "binding": binding})
        raise


def synthetic_checks():
    """No input/protocol/manifest files loaded here; generated fixture only."""
    checks = []
    def record(name, actual, expected):
        passed = bool(np.allclose(actual, expected, rtol=1e-12, atol=1e-12))
        checks.append({"name": name, "actual": actual, "independent_expected": expected, "passed": passed})
        if not passed:
            raise AssertionError(name)
    xs = [-150., -26., -25., 0., 25., 26., 150.]
    record("unclipped_hinge_boundaries", [[max(-25-x,0),max(x-25,0)] for x in xs],
           [[125,0],[1,0],[0,0],[0,0],[0,0],[0,1],[0,125]])
    dates = pd.bdate_range("2008-01-01", periods=900)
    closes = 100*1.001**np.arange(len(dates))
    p = prepare_prices(pd.DataFrame({"Date": dates, "Close": closes}))
    survey = pd.DataFrame({"date": [dates[400]-pd.Timedelta(days=7)], "bullish": [.4], "bearish": [.3]})
    for h in HORIZONS:
        row = observations(survey,p,h).iloc[0]
        record(f"h{h}_strict_quote_after_available", row["t_index"], 401)
        record(f"h{h}_target_h_segments", row["target_end_index"]-row["target_start_index"], h)
        record(f"h{h}_compound_y", row["y"], 100*(1.001**h-1))
    k = 401
    record("r20_exact", p.at[k,"r20"], 100*(1.001**20-1))
    record("r63_exact", p.at[k,"r63"], 100*(1.001**63-1))
    record("sma200_includes_t_199_back", p.at[k,"dma200"], 100*(closes[k]/sum(closes[k-199:k+1])*200-1))
    record("dd252_monotonic_zero", p.at[k,"dd252"], 0)
    record("rv20_constant_daily_returns_zero", p.at[k,"rv20"], 0)
    alternating = np.array([.01, -.02]*450)
    pa = prepare_prices(pd.DataFrame({"Date": dates, "Close": 100*np.cumprod(1+alternating)}))
    record("rv20_sample_std_ddof1", pa.at[k,"rv20"], 100*np.sqrt((10*(.01+.005)**2+10*(-.02+.005)**2)/19)*np.sqrt(20))
    mature = pd.DataFrame({"eligible": [True]*4, "t": pd.to_datetime(["2008-12-01","2009-12-01","2009-12-01","2010-01-01"]),
                           "target_end": pd.to_datetime(["2009-12-31","2010-01-01","2010-01-02","2009-12-31"])})
    record("training_strict_label_maturity", train_mask(mature,2010).to_numpy(), [True,False,False,False])
    pm = p.copy(); pm.at[410,"Close"] = np.nan
    row = observations(survey,pm,20).iloc[0]
    record("missing_target_internal_quote_excluded_no_compression", row["eligible"], False)
    checks.append({"name": "missing_path_explicit_reason", "passed": "nonfinite_target_path" in row["exclusion"]})
    cut_dates = pd.bdate_range("2025-01-01", "2026-07-31")
    pc = prepare_prices(pd.DataFrame({"Date": cut_dates,"Close": 100+np.arange(len(cut_dates))}))
    sc = pd.DataFrame({"date": [pd.Timestamp("2026-06-19")], "bullish":[.4], "bearish":[.3]})
    cutrow = observations(sc,pc,5).iloc[0]
    record("cutoff_no_shortening", cutrow["eligible"], False)
    sc["date"] = pd.Timestamp("2026-06-12")
    exactcut = observations(sc,pc,5).iloc[0]
    record("target_end_on_cutoff_allowed", exactcut["eligible"], True)
    checks.append({"name":"cutoff_end_date_exact", "actual":str(exactcut["target_end"].date()),
                   "independent_expected":"2026-06-30", "passed":exactcut["target_end"] == CUTOFF})
    dup = pd.DataFrame({"date": ["2009-07-03","2009-07-04"],"bullish":[.2,.7],"bearish":[.3,.1]})
    du = observations(dup,p,5)
    record("duplicate_t_latest_source_wins", du.loc[du["eligible"],"x"].to_numpy(), [60.])
    rng = np.random.default_rng(17)
    x = rng.normal(size=120)
    train = pd.DataFrame({"x":x,"copy":x,"y":5+3*x,"target_end":pd.Timestamp("2009-12-31"),"t":pd.Timestamp("2009-01-01")})
    f = fit_ols(train,["x"])
    record("OLS_training_mean_scale", [f["mean"][0], f["scale"][0]], [np.sum(x)/120,np.sqrt(np.sum((x-x.mean())**2)/120)])
    record("OLS_unclipped_prediction_over100", predict(pd.DataFrame({"x":[50]}),f), [155])
    for label,features in [("rank_deficiency",["x","copy"]),("zero_scale",["constant"])]:
        train["constant"] = 1.
        try:
            fit_ols(train,features)
        except RuntimeError:
            checks.append({"name":label+"_stops","passed":True})
        else:
            raise AssertionError(label)
    # Full annual logic without any source input: one test year, late label kept
    # out of that year's training, every empty test year skipped.
    fixture = pd.DataFrame({col:rng.normal(size=132) for col in BASE})
    fixture["x"] = rng.uniform(-60,60,size=132)
    fixture["lo"] = np.maximum(-25-fixture["x"],0)
    fixture["hi"] = np.maximum(fixture["x"]-25,0)
    fixture["y"] = rng.normal(size=132)
    fixture["eligible"] = True
    fixture["t"] = list(pd.date_range("1995-01-01",periods=130,freq="30D")) + [pd.Timestamp("2009-12-01"),pd.Timestamp("2010-01-04")]
    fixture["target_end"] = fixture["t"] + pd.Timedelta(days=100)
    pp,ff = annual_predictions(fixture)
    record("empty_eval_years_skip_fits", len(ff),6)
    record("annual_training_label_crossing_excluded", [f["train_rows"] for f in ff],[130]*6)
    record("same_eval_rows_all_models",len(pp),1)
    checks.append({"name":"all_synthetic_training_labels_before_year", "passed":all(f["train_label_end_max"] < pd.Timestamp(f"{f['year']}-01-01") for f in ff)})
    failed = scores(pp.iloc[:0])
    checks.append({"name":"empty_year_not_evaluated_not_zero", "passed":failed["status"] == "not_evaluated" and failed["mse"] is None})
    # Numerical block result uses synthetic errors; retained starts reconstruct paired indices.
    fake = pd.DataFrame({"y":np.zeros(104)})
    for j,m in enumerate(MODELS): fake["pred_"+m] = np.full(104,j+1.)
    draws, intervals = moving_blocks(fake,5)
    record("paired_blocks_constant_loss_ratio", draws["improvement_BXE_vs_B"].to_numpy(), np.full(2000,100*(1-36/16)))
    record("block_draw_count", len(draws), 2000)
    record("block_starts_reconstruct_exact_n", len(np.concatenate([np.arange(k,k+52) for k in json.loads(draws.iloc[0]["block_starts"])])),104)
    if not all(check["passed"] for check in checks):
        raise AssertionError("synthetic boolean check failure")
    report = {"status":"passed","real_inputs_loaded":False,"real_market_batches":0,
              "checks":checks,"checks_count":len(checks),"code_sha256":sha(__file__)}
    write_json(HERE / "synthetic-check.json",report)
    print(json.dumps({"status":"synthetic checks passed","checks":len(checks),"real_market_batches":0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-reviewed", action="store_true", help="controller only, after review; run once")
    args = parser.parse_args()
    if args.run_reviewed:
        real_run()
    else:
        synthetic_checks()
