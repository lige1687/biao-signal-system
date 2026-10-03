#!/usr/bin/env python3
"""Frozen Put/Call arithmetic. Default: synthetic only. Controller: --run-reviewed.

No network, global definitions, combinations, trading, or overwrite of run-01.
"""
from __future__ import annotations
import argparse
import hashlib
import io
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
PROTOCOL_HASH = "41684b2e13c962481119fd8b48392c0e5a36bc337cfe06004f51feec58f5c6c2"
SOURCE_HASHES = {
    "equitypc.csv": "2e73b05586b558d6763c8ab110edf9ee8bc1989384bd2b568da93dc80aa29349",
    "totalpc.csv": "0c49f75637aa83152d28129edb1fb3593d314e0ea7dff1396a39f1a6f2c56030",
    "px_SPY.csv": "952f397be0ccc5745185b91cce6acc781737c0f30a7a34aa8a230ae892ed5e45",
}
BASE = ["r20", "r63", "dma200", "dd252", "rv20"]
MODELS = {"I": [], "E": ["e"], "T": ["c"], "EQ": ["e", "eq"],
          "B": BASE, "BE": BASE+["e"], "BT": BASE+["c"], "BEQ": BASE+["e", "eq"]}
OPTIONAL = {"EQ", "BEQ"}
PAIRS = [(m,b) for b in ["B", "I"] for m in MODELS if m != b]+[("BEQ", "BE"), ("EQ", "E")]
TARGETS = {"window_mdd20": "y_mdd", "forward_return20": "y_return"}
START = pd.Timestamp("2012-06-11")
EVAL = pd.Timestamp("2015-01-01")
CUTOFF = pd.Timestamp("2019-10-04")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def jsonable(obj):
    if isinstance(obj, dict): return {str(k):jsonable(v) for k,v in obj.items()}
    if isinstance(obj, (list, tuple)): return [jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray): return jsonable(obj.tolist())
    if obj is pd.NaT: return None
    if isinstance(obj, (pd.Timestamp, datetime)): return obj.isoformat()
    if isinstance(obj, np.integer): return int(obj)
    if isinstance(obj, (float, np.floating)): return float(obj) if np.isfinite(obj) else None
    if isinstance(obj, np.bool_): return bool(obj)
    return obj


def write_json(path, obj):
    Path(path).write_text(json.dumps(jsonable(obj),indent=2,ensure_ascii=False,allow_nan=False)+"\n")


def check_bindings():
    if sha(ROOT/"protocol.json") != PROTOCOL_HASH:
        raise RuntimeError("STOP: frozen protocol drift")
    inputs = {}
    for name,expected in SOURCE_HASHES.items():
        p = ROOT/"inputs"/name
        actual = sha(p)
        if actual != expected: raise RuntimeError("STOP: frozen input drift: "+name)
        inputs[name] = {"sha256":actual,"bytes":p.stat().st_size}
    authority = []
    source_manifest = json.loads((ROOT/"source-manifest.json").read_text())
    for entry in source_manifest["files"]:
        if "role" in entry:
            p = Path(entry["source_path"])
            actual = sha(p) if p.exists() else None
            authority.append({"path":str(p),"role":entry["role"],"bound_sha256":entry["sha256"],
                              "actual_sha256":actual,"changed":actual != entry["sha256"]})
    return {"inputs":inputs,"protocol_sha256":PROTOCOL_HASH,
            "source_manifest_sha256":sha(ROOT/"source-manifest.json"),"authority_audit":authority}


def parse_product(text, product, feature):
    lines = text.splitlines()
    if len(lines) < 4 or "PRODUCT: "+product not in lines[1]:
        raise RuntimeError("STOP: product identity not established: "+product)
    frame = pd.read_csv(io.StringIO(text),skiprows=2)
    frame.columns = frame.columns.str.strip()
    required = ["DATE","P/C Ratio","CALL" if product == "EQUITY" else "CALLS",
                "PUT" if product == "EQUITY" else "PUTS","TOTAL"]
    if not set(required).issubset(frame.columns): raise RuntimeError("STOP: unidentified product columns")
    frame["source_date"] = pd.to_datetime(frame["DATE"],format="%m/%d/%Y",errors="raise")
    if frame["source_date"].isna().any() or frame["source_date"].duplicated().any():
        raise RuntimeError("STOP: invalid or duplicate source date")
    frame[feature] = pd.to_numeric(frame["P/C Ratio"],errors="coerce")
    prefix = "equity" if product == "EQUITY" else "total"
    for original,suffix in zip(required[2:],["calls","puts","volume"]):
        frame[prefix+"_"+suffix] = pd.to_numeric(frame[original],errors="coerce")
    frame[prefix+"_exact_ratio_audit_only"] = frame[prefix+"_puts"]/frame[prefix+"_calls"]
    return frame[["source_date",feature]+[col for col in frame if col.startswith(prefix+"_")]], {
        "product":product,"metadata":lines[:2],"column_header":lines[2],"rows":len(frame),
        "first_source":frame["source_date"].min(),"last_source":frame["source_date"].max()}


def common_sources(equity, total):
    frame = equity.merge(total,on="source_date",how="inner",validate="one_to_one")
    frame = frame.sort_values("source_date",kind="stable").reset_index(drop=True)
    frame["source_row"] = np.arange(len(frame))
    frame["eq"] = np.where(np.isfinite(frame["e"]),(frame["e"]>1).astype(float),np.nan)
    return frame, {"equity_dates":len(equity),"total_dates":len(total),"common_source_dates":len(frame),
                   "equity_only_source_dates":sorted(set(equity["source_date"])-set(total["source_date"])),
                   "total_only_source_dates":sorted(set(total["source_date"])-set(equity["source_date"]))}


def prepare_prices(frame):
    p = frame.copy()
    p["Date"] = pd.to_datetime(p["Date"],errors="raise").dt.normalize()
    if p["Date"].isna().any() or p["Date"].duplicated().any(): raise RuntimeError("STOP: invalid/duplicate quote date")
    p = p.sort_values("Date",kind="stable").reset_index(drop=True)
    p["Close"] = pd.to_numeric(p["Close"],errors="coerce")
    p.loc[~np.isfinite(p["Close"]) | (p["Close"]<=0),"Close"] = np.nan
    c = p["Close"]
    p["r20"] = 100*(c/c.shift(20)-1)
    p["r63"] = 100*(c/c.shift(63)-1)
    p["dma200"] = 100*(c/c.rolling(200,min_periods=200).mean()-1)
    p["dd252"] = 100*(c/c.rolling(252,min_periods=252).max()-1)
    p["rv20"] = 100*c.pct_change(fill_method=None).rolling(20,min_periods=20).std(ddof=1)*np.sqrt(20)
    return p


def target_values(path):
    if len(path) != 21 or not np.isfinite(path).all() or (np.asarray(path)<=0).any():
        raise ValueError("target needs exactly 21 finite positive closes")
    path = np.asarray(path,dtype=float)
    return 100*(path[-1]/path[0]-1), 100*np.max(1-path/np.maximum.accumulate(path))


def observations(source, prices):
    quote_positions = {d:i for i,d in enumerate(prices["Date"])}
    c = prices["Close"].to_numpy()
    rows = []
    for src in source.to_dict("records"):
        d = src["source_date"]
        r = {**src,"source_quote_index":np.nan,"t":pd.NaT,"t_index":np.nan,
             "target_start":pd.NaT,"target_end":pd.NaT,"target_start_index":np.nan,
             "target_end_index":np.nan,"y_return":np.nan,"y_mdd":np.nan,
             **{col:np.nan for col in BASE},"eligible":False}
        reasons = []
        if d < START or d > CUTOFF: reasons.append("source_outside_frozen_regime")
        if not np.isfinite([src["e"],src["c"]]).all(): reasons.append("nonfinite_product_ratio")
        elif src["e"]<0 or src["c"]<0: reasons.append("invalid_negative_product_ratio")
        if d not in quote_positions:
            reasons.append("source_date_not_actual_SPY_quote")
        else:
            i = quote_positions[d]; k = i+2
            r["source_quote_index"] = i; r["t_index"] = k
            r["target_start_index"] = k+1; r["target_end_index"] = k+21
            if k >= len(prices):
                reasons.append("incomplete_two_quote_wait")
            else:
                r["t"] = prices.at[k,"Date"]
                for col in BASE: r[col] = prices.at[k,col]
                if not np.isfinite([r[col] for col in BASE]).all(): reasons.append("nonfinite_price_controls")
                if not np.isfinite(c[i:k+1]).all(): reasons.append("nonfinite_availability_quote_path")
                if k+1 < len(prices): r["target_start"] = prices.at[k+1,"Date"]
                if k+21 < len(prices): r["target_end"] = prices.at[k+21,"Date"]
                if k+21 >= len(prices): reasons.append("incomplete_target_quotes")
                elif prices.at[k+21,"Date"] > CUTOFF: reasons.append("target_beyond_cutoff")
                elif not np.isfinite(c[k+1:k+22]).all(): reasons.append("nonfinite_target_path")
                else: r["y_return"],r["y_mdd"] = target_values(c[k+1:k+22])
        r["exclusion"] = "|".join(reasons)
        r["eligible"] = not reasons and np.isfinite([r["y_return"],r["y_mdd"]]).all()
        rows.append(r)
    return pd.DataFrame(rows).sort_values("source_date",kind="stable").reset_index(drop=True)


def train_mask(obs, year):
    boundary = pd.Timestamp(f"{year}-01-01")
    return obs["eligible"] & (obs["source_date"]>=START) & (obs["t"]<boundary) & (obs["target_end"]<boundary)


def fit_ols(train, features, ycol, optional=False):
    if len(train)<400: raise RuntimeError("STOP: fewer than 400 matured training rows")
    a = train[features].to_numpy(float)
    if not np.isfinite(a).all() or not np.isfinite(train[ycol]).all(): raise RuntimeError("STOP: nonfinite training population")
    mean,scale = a.mean(axis=0),a.std(axis=0,ddof=0)
    detail = {"features":features,"mean":mean,"scale":scale,"train_rows":len(train),
              "train_label_end_max":train["target_end"].max(),"train_t_max":train["t"].max(),
              "train_extreme_rows":int((train["eq"]==1).sum()),"beta":None}
    if (scale==0).any():
        if optional: return {**detail,"status":"not_estimable","reason":"zero_training_scale","rank":None}
        raise RuntimeError("STOP: zero scale in core model")
    z = np.column_stack([np.ones(len(train)),(a-mean)/scale])
    beta,_,rank,singular = np.linalg.lstsq(z,train[ycol].to_numpy(float),rcond=None)
    detail.update({"rank":int(rank),"singular_values":singular})
    if rank != z.shape[1]:
        if optional: return {**detail,"status":"not_estimable","reason":"rank_deficient"}
        raise RuntimeError("STOP: rank deficient core model")
    return {**detail,"status":"estimable","beta":beta}


def predict(frame, fit):
    if fit["status"] != "estimable": return np.full(len(frame),np.nan)
    a = frame[fit["features"]].to_numpy(float)
    return np.column_stack([np.ones(len(frame)),(a-fit["mean"])/fit["scale"]]) @ fit["beta"]


def annual_predictions(obs, ycol):
    rows,fits = [],[]
    for year in range(2015,2020):
        train = obs.loc[train_mask(obs,year)]
        ev = obs.loc[obs["eligible"] & (obs["t"].dt.year == year)].copy()
        if ev.empty: continue
        ev["y"] = ev[ycol]
        for model,features in MODELS.items():
            fit = fit_ols(train,features,ycol,model in OPTIONAL)
            fit.update({"year":year,"model":model,"target_column":ycol})
            fits.append(fit)
            ev["pred_"+model] = predict(ev,fit)
            ev["loss_"+model] = (ev["y"]-ev["pred_"+model])**2
        rows.append(ev)
    if not rows: raise RuntimeError("STOP: no matured evaluation rows")
    return pd.concat(rows,ignore_index=True),fits


def scores(frame):
    n = len(frame)
    if not n: return {"n":0,"status":"not_evaluated","mse":None,"rmse":None,"improvement_pct":None}
    mse,rmse,negative,status,estimable_counts = {},{},{},{},{}
    for m in MODELS:
        valid = np.isfinite(frame["pred_"+m].to_numpy())
        estimable_counts[m] = int(valid.sum())
        status[m] = "estimable" if valid.all() else "not_estimable" if not valid.any() else "partially_estimable"
        # Never silently change the agreed comparison population for rare branches.
        mse[m] = float(np.mean((frame["y"]-frame["pred_"+m])**2)) if valid.all() else None
        rmse[m] = math.sqrt(mse[m]) if mse[m] is not None else None
        negative[m] = {"negative_n":int((frame.loc[valid,"pred_"+m]<0).sum()),
                       "estimable_n":int(valid.sum()),"share":float((frame.loc[valid,"pred_"+m]<0).mean()) if valid.any() else None}
    improvement,reduction = {},{}
    for m,b in PAIRS:
        available = mse[m] is not None and mse[b] is not None
        key = f"{m}_vs_{b}"
        improvement[key] = 100*(1-mse[m]/mse[b]) if available and mse[b]>0 else None
        reduction[key] = n*(mse[b]-mse[m]) if available else None
    return {"n":n,"mse":mse,"rmse":rmse,"model_status":status,"estimable_prediction_counts":estimable_counts,
            "negative_prediction":negative,"improvement_pct":improvement,"squared_error_reduction_sum":reduction}


def coverage(obs, pred):
    codes = obs["exclusion"].str.split("|").explode()
    codes = codes.loc[codes!=""].value_counts().to_dict()
    a,b = pred["target_start_index"].to_numpy(),pred["target_end_index"].to_numpy()
    overlap = np.maximum(0,np.minimum(b[:-1],b[1:])-np.maximum(a[:-1],a[1:]))
    detail = pred[["source_row","source_date","t","target_start_index","target_end_index"]].copy()
    detail["next_overlap_return_segments"] = np.r_[overlap,np.nan]
    regime = obs.loc[obs["source_date"].between(START,CUTOFF)]
    return {"common_source_rows_before_regime_filter":len(obs),"source_regime_rows":len(regime),
            "source_regime_equity_extreme_rows":int((regime["eq"]==1).sum()),
            "source_regime_total_ratio_gt1_product_audit_only":int((regime["c"]>1).sum()),
            "mature_common_eligible_rows":int(obs["eligible"].sum()),"evaluation_rows":len(pred),
            "exclusion_counts_nonexclusive":codes,"first_eval_t":pred["t"].min(),"last_eval_t":pred["t"].max(),
            "first_label_start":pred["target_start"].min(),"last_label_end":pred["target_end"].max(),
            "adjacent_eval_pairs":len(overlap),"overlapping_pairs":int((overlap>0).sum()),
            "mean_overlap_return_segments":float(overlap.mean()) if len(overlap) else None,
            "max_overlap_return_segments":int(overlap.max()) if len(overlap) else None,
            "source_quote_gaps_in_eval":int(pred["source_quote_index"].diff().gt(1).sum())},detail


def group_behavior(obs, pred):
    # Build episodes on the complete evaluation source population, not filtered y.
    full = obs.loc[obs["source_date"].between(START,CUTOFF) & obs["t"].between(EVAL,CUTOFF)].copy()
    full["group"] = np.where(full["eq"]==1,"equity_gt1",np.where(full["eq"]==0,"equity_le1","missing_equity"))
    breaks = full["group"].ne(full["group"].shift()) | full["source_date"].diff().ge(pd.Timedelta(days=4)) | full["source_quote_index"].diff().ne(1)
    full["episode"] = breaks.cumsum()
    out = {}
    for label,extreme in [("equity_gt1",True),("equity_le1",False)]:
        allg = full.loc[full["eq"]==(1 if extreme else 0)]
        f = pred.loc[pred["eq"]==(1 if extreme else 0)]
        ids = set(f["source_row"])
        out[label] = {"full_eval_sources_n":len(allg),"mature_eligible_n":len(f),
                      "full_eval_episodes":int(allg["episode"].nunique()),
                      "episodes_with_mature_eligible_rows":int(allg.loc[allg["source_row"].isin(ids),"episode"].nunique()),
                      "return_mean":f["y_return"].mean(),"return_median":f["y_return"].median(),
                      "return_up_share":float((f["y_return"]>0).mean()) if len(f) else None,
                      "mdd_mean":f["y_mdd"].mean(),"mdd_median":f["y_mdd"].median()}
    return out


def moving_blocks(pred, target):
    n,block,draw_count = len(pred),126,2000
    if n<block: raise RuntimeError("STOP: fewer than 126 evaluation rows")
    seed = 20260929+(0 if target == "window_mdd20" else 1)
    rng = np.random.default_rng(seed)
    # A partially estimable branch has no whole-period range. Retain all rows;
    # no branch-specific population or imputation of missing predictions.
    active = {m:np.isfinite(pred["pred_"+m]).all() for m in MODELS}
    loss = {m:(pred["y"].to_numpy()-pred["pred_"+m].to_numpy())**2 for m in MODELS}
    out = []
    for draw in range(draw_count):
        starts = rng.integers(0,n-block+1,size=math.ceil(n/block))
        indices = np.concatenate([np.arange(s,s+block) for s in starts])[:n]
        mse = {m:float(loss[m][indices].mean()) if active[m] else np.nan for m in MODELS}
        row = {"draw":draw,"seed":seed,"n":n,"block_rows":block,
               "block_starts":json.dumps(starts.tolist(),separators=(",",":"))}
        row.update({"mse_"+m:value for m,value in mse.items()})
        row.update({f"improvement_{m}_vs_{b}":100*(1-mse[m]/mse[b]) if active[m] and active[b] and mse[b]>0 else np.nan for m,b in PAIRS})
        out.append(row)
    draws = pd.DataFrame(out)
    intervals = {}
    for m,b in PAIRS:
        series = draws[f"improvement_{m}_vs_{b}"]
        intervals[f"{m}_vs_{b}"] = {"status":"computed" if series.notna().all() else "not_estimable",
                                   "valid_draws":int(series.notna().sum()),"p2_5":series.quantile(.025),"p97_5":series.quantile(.975)}
    return draws,intervals


def target_results(obs, pred, fits, target):
    overall = scores(pred)
    raw = group_behavior(obs,pred)
    group_errors = {}
    for label,extreme in [("equity_gt1",True),("equity_le1",False)]:
        f = pred.loc[(pred["eq"]==1)==extreme]
        sc = scores(f)
        sc["share_of_total_squared_error_reduction"] = {
            key: val/overall["squared_error_reduction_sum"][key]
            if val is not None and overall["squared_error_reduction_sum"][key] not in (None,0) else None
            for key,val in sc.get("squared_error_reduction_sum",{}).items()}
        group_errors[label] = sc
    cov,overlap = coverage(obs,pred)
    return {"target":target,"overall":overall,"coverage":cov,"raw_equity_groups":raw,
            "raw_group_differences_extreme_minus_other":{
                "return_mean":raw["equity_gt1"]["return_mean"]-raw["equity_le1"]["return_mean"],
                "mdd_mean":raw["equity_gt1"]["mdd_mean"]-raw["equity_le1"]["mdd_mean"]},
            "group_errors":group_errors,
            "annual":{year:{**scores(pred.loc[pred["t"].dt.year == year]),
                            "eval_extreme_n":int(((pred["t"].dt.year == year) & (pred["eq"]==1)).sum())} for year in range(2015,2020)},
            "bands":{label:scores(pred.loc[pred["t"].dt.year.between(a,b)]) for label,a,b in [("2015-2016",2015,2016),("2017-2019",2017,2019)]},
            "remove_year_no_refit":{year:scores(pred.loc[pred["t"].dt.year != year]) for year in range(2015,2020)},
            "drop_equity_gt1_no_refit":scores(pred.loc[pred["eq"]!=1]),
            "fit_branch_statuses":[{key:f[key] for key in ["year","model","status","train_rows","train_extreme_rows"]} for f in fits]},overlap


def check_output_budget(output):
    if sum(p.stat().st_size for p in output.iterdir() if p.is_file())>20*1024*1024:
        raise RuntimeError("STOP: output budget exceeded")


def real_run():
    output = HERE/"run-01"
    if output.exists(): raise RuntimeError("STOP: run-01 exists; never overwrite")
    binding = check_bindings()
    started = datetime.now(timezone.utc)
    output.mkdir()
    try:
        e,em = parse_product((ROOT/"inputs/equitypc.csv").read_text(encoding="latin1"),"EQUITY","e")
        c,cm = parse_product((ROOT/"inputs/totalpc.csv").read_text(encoding="latin1"),"TOTAL","c")
        source,join = common_sources(e,c)
        prices = prepare_prices(pd.read_csv(ROOT/"inputs/px_SPY.csv"))
        obs = observations(source,prices)
        obs.to_csv(output/"observations.csv",index=False,float_format="%.17g")
        results,fit_attempts,estimable_fits = {},0,0
        for target,ycol in TARGETS.items():
            pred,fits = annual_predictions(obs,ycol)
            fit_attempts += len(fits); estimable_fits += sum(f["status"] == "estimable" for f in fits)
            if fit_attempts>80: raise RuntimeError("STOP: fit attempt budget exceeded")
            result,overlap = target_results(obs,pred,fits,target)
            draws,intervals = moving_blocks(pred,target)
            result["paired_block_intervals"] = intervals
            results[target] = result
            pred.to_csv(output/f"predictions-{target}.csv",index=False,float_format="%.17g")
            write_json(output/f"fits-{target}.json",fits)
            draws.to_csv(output/f"draws-{target}.csv",index=False,float_format="%.17g")
            overlap.to_csv(output/f"overlap-{target}.csv",index=False)
            check_output_budget(output)
        final_binding = check_bindings()
        write_json(output/"results.json",{
            "protocol_id":"sentiment.putcall-increment@1.0.0","primary_target":"window_mdd20","targets":results,
            "fit_attempts":fit_attempts,"estimable_fits":estimable_fits,"join_audit":join,
            "metric_unit":"relative MSE reduction percent, not profit",
            "target_unit":"percentage points of adjusted price change or positive magnitude of within-future-window maximum drop",
            "columns":{"beta":"intercept followed by standardized features in features order",
                       "eq":"reported Equity ratio strictly >1 only; Total has no threshold",
                       "block_starts":"0-based prediction row starts;126-row blocks truncated to total n",
                       "exclusion":"pipe-separated reasons; reason counts nonexclusive"},
            "rare_branch_policy":"Not-estimable years remain missing. Whole-period branch metrics/ranges absent if any eligible row prediction missing; no different population or feature deletion.",
            "limitations":["only 6 reported Equity>1 source dates after2012; initial training has1 before maturity filtering",
                           "mathematically estimable rare threshold is not demonstrated reliable predictive information",
                           "historical first release/revision times unknown; two-quote wait is a hypothetical proxy",
                           "adjustment vintages unknown and prices not actual executable quotes",
                           "already viewed exploratory family, not new independent validation",
                           "negative risk predictions retained expose unrestricted linear-model limitation",
                           "126-row blocks do not refit, omit full model uncertainty and multiple-testing correction"]})
        manifest = {**binding,"status":"completed","started_at":started,"completed_at":datetime.now(timezone.utc),
                    "authority_audit_after_run":final_binding["authority_audit"],"source_manifest_sha256_after_run":final_binding["source_manifest_sha256"],
                    "source_headers":{"equity":em,"total":cm},"code_sha256":sha(__file__),"python":platform.python_version(),
                    "numpy":np.__version__,"pandas":pd.__version__,"argv":sys.argv,"fit_attempts":fit_attempts,
                    "estimable_fits":estimable_fits,"global_definition_consumers_called":False,"network_requests":0,"pro_calls":0,"core_batches":1,
                    "outputs":{p.name:{"sha256":sha(p),"bytes":p.stat().st_size} for p in sorted(output.iterdir())}}
        write_json(output/"manifest.json",manifest)
        check_output_budget(output)
    except Exception as exc:
        write_json(output/"failure.json",{"status":"stopped","error":str(exc),"started_at":started,"binding":binding})
        raise


def synthetic_checks():
    """All inputs generated here; no market input/protocol/manifest loaded."""
    checks = []
    def record(name,actual,expected):
        passed = bool(np.allclose(actual,expected,rtol=1e-11,atol=1e-11))
        checks.append({"name":name,"actual":actual,"independent_expected":expected,"passed":passed})
        if not passed: raise AssertionError(name)
    def boolean(name,value):
        checks.append({"name":name,"passed":bool(value)})
        if not value: raise AssertionError(name)
    # Explicit small-path manual calculations, padded flat to exactly21 points.
    for name,path,expected in [
        ("monotonic_up",list(range(100,121)),[20,0]),
        ("monotonic_down",list(range(100,79,-1)),[-20,20]),
        ("recover_after_dip",[100,120,90,130]+[130]*17,[30,25]),
        ("new_peak_then_drop",[100,90,120,96]+[96]*17,[-4,20]),
        ("larger_late_drop",[100,120,108,150,90]+[90]*16,[-10,40])]:
        record("target_"+name,target_values(np.array(path,float)),expected)
    try: target_values(np.ones(20))
    except ValueError: boolean("reject20_closes_not21",True)
    else: raise AssertionError("target points")
    dates = pd.bdate_range("2012-01-02",periods=1500)
    closes = 100*1.001**np.arange(len(dates))
    p = prepare_prices(pd.DataFrame({"Date":dates,"Close":closes}))
    source = pd.DataFrame({"source_date":[dates[400]],"source_row":[0],"e":[1.],"c":[1.2],"eq":[0.]})
    row = observations(source,p).iloc[0]
    record("two_actual_quotes_wait",row["t_index"],402)
    record("target_start_after_t",row["target_start_index"],403)
    record("target_end_tplus21",row["target_end_index"],423)
    record("20_return_segments21_closes",row["target_end_index"]-row["target_start_index"],20)
    record("compound_return",row["y_return"],100*(1.001**20-1))
    record("future_peak_excludes_pre_window",row["y_mdd"],0)
    # Huge prior observed close must not become peak for future drawdown.
    pp = p.copy(); pp.at[402,"Close"] = 10000
    record("pre_window_peak_not_used",observations(source,pp).iloc[0]["y_mdd"],0)
    for col,expected in [("r20",100*(1.001**20-1)),("r63",100*(1.001**63-1)),
                         ("dma200",100*(closes[402]/(sum(closes[203:403])/200)-1)),("dd252",0),("rv20",0)]:
        record("baseline_"+col,row[col],expected)
    alternating = np.array([.01,-.02]*750)
    alt = prepare_prices(pd.DataFrame({"Date":dates,"Close":100*np.cumprod(1+alternating)}))
    record("rv20_ddof1",alt.at[402,"rv20"],100*np.sqrt(20*(.015**2)/19)*np.sqrt(20))
    missing = p.copy(); missing.at[410,"Close"] = np.nan
    rr = observations(source,missing).iloc[0]
    boolean("internal_missing_no_compression",not rr["eligible"] and "nonfinite_target_path" in rr["exclusion"])
    weekend = source.copy(); weekend["source_date"] = pd.Timestamp("2013-08-03")
    rr = observations(weekend,p).iloc[0]
    boolean("nonquote_source_not_shifted",not rr["eligible"] and "source_date_not_actual_SPY_quote" in rr["exclusion"])
    earlier = source.copy(); earlier["source_date"] = pd.Timestamp("2012-06-08")
    boolean("no_pre2012_regime_splice","source_outside_frozen_regime" in observations(earlier,p).iloc[0]["exclusion"])
    # Different features across products, retain rounded ratio exactly, no addition.
    raw_e = "warning\n, PRODUCT: EQUITY,,EXCHANGE: Cboe,\nDATE,CALL,PUT,TOTAL,P/C Ratio\n6/11/2012,1000,1004,2004,1.00\n6/12/2012,1000,1014,2014,1.01\n"
    raw_c = "warning\n, PRODUCT: TOTAL,,EXCHANGE: Cboe,\nDATE,CALLS,PUTS,TOTAL,P/C Ratio\n6/11/2012,1000,1500,2500,1.50\n6/13/2012,1000,1500,2500,1.50\n"
    e,_ = parse_product(raw_e,"EQUITY","e"); c,_ = parse_product(raw_c,"TOTAL","c")
    joined,audit = common_sources(e,c)
    record("inner_common_dates_only",len(joined),1)
    record("reported_rounded_e_not_exact",joined["e"].to_numpy(),[1.])
    record("Equity_eq_boundary_strict_gt1",joined["eq"].to_numpy(),[0])
    record("Total_not_added_to_Equity",joined["c"].to_numpy(),[1.5])
    e2 = e.copy(); e2["source_date"] = e2["source_date"]-pd.Timedelta(days=1)
    record("Equity_above1_positive",common_sources(e2,c)[0]["eq"].to_numpy(),[1.])
    matured = pd.DataFrame({"eligible":[True]*4,"source_date":pd.Timestamp("2014-11-01"),
                           "t":pd.to_datetime(["2014-11-01","2014-12-01","2014-12-01","2015-01-01"]),
                           "target_end":pd.to_datetime(["2014-12-31","2015-01-01","2015-01-02","2014-12-31"])})
    record("strict_year_maturity",train_mask(matured,2015).to_numpy(),[True,False,False,False])
    end_dates = pd.bdate_range("2018-01-01","2019-11-15")
    ep = prepare_prices(pd.DataFrame({"Date":end_dates,"Close":100+np.arange(len(end_dates))}))
    idx = int(np.flatnonzero(end_dates == CUTOFF)[0])
    ss = source.copy(); ss["source_date"] = end_dates[idx-23]
    record("cutoff_exact_allowed",observations(ss,ep).iloc[0]["eligible"],True)
    ss["source_date"] = end_dates[idx-22]
    rr = observations(ss,ep).iloc[0]
    boolean("cutoff_no_shortening",not rr["eligible"] and "target_beyond_cutoff" in rr["exclusion"])
    rng = np.random.default_rng(30)
    x = rng.uniform(.3,.9,450)
    tr = pd.DataFrame({"e":x,"eq":np.zeros(450),"copy":x,"y":5+3*x,"t":pd.Timestamp("2014-01-01"),"target_end":pd.Timestamp("2014-12-31")})
    f = fit_ols(tr,["e"],"y")
    record("train_scale_ddof0",[f["mean"][0],f["scale"][0]],[sum(x)/450,np.sqrt(sum((x-x.mean())**2)/450)])
    record("unclipped_over100_prediction",predict(pd.DataFrame({"e":[50]}),f),[155])
    opt = fit_ols(tr,["e","eq"],"y",optional=True)
    boolean("rare_zero_eq_not_estimable_no_feature_drop",opt["status"] == "not_estimable" and opt["features"] == ["e","eq"] and opt["beta"] is None)
    rank = fit_ols(tr,["e","copy"],"y",optional=True)
    boolean("optional_rank_not_estimable",rank["status"] == "not_estimable")
    for name,tframe,features in [("core_rank_stop",tr,["e","copy"]),("core_zero_stop",tr,["eq"]),("min400_stop",tr.iloc[:399],["e"])]:
        try: fit_ols(tframe,features,"y")
        except RuntimeError: boolean(name,True)
        else: raise AssertionError(name)
    tr.loc[0,"e"] = 1.2; tr.loc[0,"eq"] = 1.
    boolean("single_rare_row_estimable_not_reliability_claim",fit_ols(tr,["e","eq"],"y",optional=True)["status"] == "estimable")
    tr["y"] = -5+tr["e"]
    f = fit_ols(tr,["e"],"y")
    record("negative_risk_prediction_not_clipped",predict(pd.DataFrame({"e":[.5]}),f),[-4.5])
    # Full annual branch behavior: generated inputs,450 mature training rows,
    # one across-year label excluded, zero extreme branch remains unavailable.
    fixture = pd.DataFrame({col:rng.normal(size=452) for col in BASE})
    fixture["e"] = rng.uniform(.3,.9,452); fixture["c"] = rng.uniform(.6,1.6,452); fixture["eq"] = 0.
    fixture["source_date"] = list(pd.bdate_range("2012-06-11",periods=450))+[pd.Timestamp("2014-12-01"),pd.Timestamp("2015-01-02")]
    fixture["t"] = fixture["source_date"]+pd.Timedelta(days=2)
    fixture["target_end"] = fixture["t"]+pd.Timedelta(days=30)
    fixture["eligible"] = True; fixture["y_mdd"] = rng.uniform(0,20,452); fixture["y_return"] = rng.normal(size=452)
    pred,fits = annual_predictions(fixture,"y_mdd")
    record("skip_empty_eval_years",len(fits),8)
    record("mature_training_excludes_crossing_label",[f["train_rows"] for f in fits],[450]*8)
    record("same_population_optional_missing",len(pred),1)
    boolean("optional_preds_missing_core_present",pred["pred_EQ"].isna().all() and pred["pred_BEQ"].isna().all() and pred["pred_BE"].notna().all())
    metric = scores(pred)
    boolean("not_estimable_not_zero",metric["mse"]["EQ"] is None and metric["improvement_pct"]["EQ_vs_E"] is None)
    # Paired draws exact known constant losses; no market data used.
    fake = pd.DataFrame({"y":np.zeros(252)})
    for j,m in enumerate(MODELS): fake["pred_"+m] = np.full(252,j+1.)
    draws,intervals = moving_blocks(fake,"window_mdd20")
    record("2000_paired_draws",len(draws),2000)
    record("126_block_rows",draws["block_rows"].unique(),[126])
    record("paired_BEvsB_manual",draws.iloc[0]["improvement_BE_vs_B"],100*(1-36/25))
    record("paired_EQvsE_manual",draws.iloc[0]["improvement_EQ_vs_E"],100*(1-16/4))
    starts = json.loads(draws.iloc[0]["block_starts"])
    record("starts_rebuild_n",len(np.concatenate([np.arange(s,s+126) for s in starts])[:252]),252)
    fake["pred_EQ"] = np.nan; fake["pred_BEQ"] = np.nan
    _,intervals = moving_blocks(fake,"forward_return20")
    boolean("missing_branch_no_range_core_continues",intervals["EQ_vs_E"]["valid_draws"]==0 and intervals["BE_vs_B"]["valid_draws"]==2000)
    negative = fake.copy()
    negative["pred_E"] = -1.
    record("negative_prediction_share_reported",scores(negative)["negative_prediction"]["E"]["share"],1.)
    episodes = pd.DataFrame({"source_row":range(5),"source_date":pd.to_datetime(["2015-01-02","2015-01-03","2015-01-06","2015-01-07","2015-01-13"]),
                             "source_quote_index":[10,11,12,13,14],"eq":[1,1,0,1,1],
                             "y_return":np.ones(5),"y_mdd":np.ones(5)})
    episodes["t"] = episodes["source_date"]
    # Generated dates deliberately control the arithmetic gap independently of
    # quote positions; source-date qualification is separately tested above.
    stats = group_behavior(episodes,episodes.loc[episodes["eq"]==1])
    record("episode_break_nonextreme_between_and_gap_ge4",stats["equity_gt1"]["full_eval_episodes"],3)
    episodes.loc[4,"source_date"] = pd.Timestamp("2015-01-08")
    episodes.loc[4,"t"] = pd.Timestamp("2015-01-08")
    episodes.loc[4,"source_quote_index"] = 16
    record("episode_break_nonconsecutive_actual_quotes",group_behavior(episodes,episodes)["equity_gt1"]["full_eval_episodes"],3)
    fake253 = pd.concat([fake,fake.iloc[:1]],ignore_index=True)
    d253,_ = moving_blocks(fake253,"window_mdd20")
    starts = json.loads(d253.iloc[0]["block_starts"])
    record("truncated_final_block_retains253_rows",len(np.concatenate([np.arange(s,s+126) for s in starts])[:253]),253)
    record("core_draw_n253",d253.iloc[0]["n"],253)
    write_json(HERE/"synthetic-check.json",{"status":"passed","real_inputs_loaded":False,"real_market_batches":0,
                                          "checks":checks,"checks_count":len(checks),"code_sha256":sha(__file__)})
    print(json.dumps({"status":"synthetic checks passed","checks":len(checks),"real_market_batches":0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-reviewed",action="store_true",help="controller only after code review; unique real batch")
    args = parser.parse_args()
    if args.run_reviewed: real_run()
    else: synthetic_checks()
