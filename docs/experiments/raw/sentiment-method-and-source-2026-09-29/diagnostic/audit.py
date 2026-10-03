#!/usr/bin/env python3
"""One diagnostic of saved estimates; zero fitting and no frozen-file writes.
Default synthetic only; --run-diagnostic consumes the sole real diagnostic run.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE.parent.parent
AAII = RAW/"sentiment-aaii-extremes-increment-2026-09-29"
PC = RAW/"sentiment-putcall-increment-2026-09-29"
BASE = ["r20","r63","dma200","dd252","rv20"]
TOL = 1e-9


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def clean(o):
    if isinstance(o,dict): return {str(k):clean(v) for k,v in o.items()}
    if isinstance(o,(list,tuple)): return [clean(v) for v in o]
    if isinstance(o,np.ndarray): return clean(o.tolist())
    if o is pd.NaT: return None
    if isinstance(o,(pd.Timestamp,datetime)): return o.isoformat()
    if isinstance(o,np.integer): return int(o)
    if isinstance(o,np.bool_): return bool(o)
    if isinstance(o,(float,np.floating)): return float(o) if np.isfinite(o) else None
    return o


def write_json(p,o): Path(p).write_text(json.dumps(clean(o),indent=2,ensure_ascii=False,allow_nan=False)+"\n")


def frozen_identity(root):
    run = root/"executor/run-01"
    manifest = json.loads((run/"manifest.json").read_text())
    checked = {}
    for name,rec in manifest["inputs"].items():
        p = root/"inputs"/name
        if sha(p)!=rec["sha256"]: raise RuntimeError("sealed input drift: "+str(p))
        checked[str(p)] = sha(p)
    if sha(root/"protocol.json") != manifest["protocol_sha256"]: raise RuntimeError("sealed protocol drift")
    if sha(root/"executor/analyze.py") != manifest["code_sha256"]: raise RuntimeError("sealed implementation drift")
    for name,rec in manifest["outputs"].items():
        p = run/name
        if sha(p)!=rec["sha256"]: raise RuntimeError("sealed output drift: "+str(p))
        checked[str(p)] = sha(p)
    checked[str(run/"manifest.json")] = sha(run/"manifest.json")
    checked[str(root/"protocol.json")] = sha(root/"protocol.json")
    checked[str(root/"executor/analyze.py")] = sha(root/"executor/analyze.py")
    return checked


def load_dates(path):
    frame = pd.read_csv(path)
    for col in ["source_date","t","target_start","target_end"]:
        frame[col] = pd.to_datetime(frame[col])
    return frame


def background_at(close,k):
    past = close[k-19:k+1]/close[k-20:k]-1
    return [100*(close[k]/close[k-20]-1),100*(close[k]/close[k-63]-1),
            100*(close[k]/np.mean(close[k-199:k+1])-1),
            100*(close[k]/np.max(close[k-251:k+1])-1),100*np.std(past,ddof=1)*np.sqrt(20)]


def window_labels(path):
    # Sequential peak tracking is independent of original maximum.accumulate.
    high = path[0]; maximum_drop = 0.
    for value in path:
        high = max(high,value)
        maximum_drop = max(maximum_drop,1-value/high)
    return 100*(path[-1]/path[0]-1),100*maximum_drop


def label_audit(root,obs,kind):
    px = pd.read_csv(root/"inputs/px_SPY.csv")
    dates = pd.to_datetime(px["Date"]).to_numpy(dtype="datetime64[ns]")
    close = px["Close"].to_numpy(float)
    positions = {pd.Timestamp(d):i for i,d in enumerate(dates)}
    discrepancies = []; max_diff = {col:0. for col in BASE}
    label_diff = {"y":0.} if kind=="aaii" else {"y_return":0.,"y_mdd":0.}
    if kind=="aaii":
        survey = pd.read_csv(root/"inputs/aaii-candidate-values.csv")
        source_values = None
        cutoff = pd.Timestamp("2026-06-30"); h=120
    else:
        e = pd.read_csv(root/"inputs/equitypc.csv",skiprows=2,encoding="latin1")
        c = pd.read_csv(root/"inputs/totalpc.csv",skiprows=2,encoding="latin1")
        ed = pd.to_datetime(e["DATE"],format="%m/%d/%Y")
        cd = pd.to_datetime(c["DATE"],format="%m/%d/%Y")
        source_values = {d:(float(e.loc[i,"P/C Ratio"]),float(c.loc[cd==d,"P/C Ratio"].iloc[0])) for i,d in enumerate(ed) if (cd==d).any()}
        cutoff = pd.Timestamp("2019-10-04"); h=20
    valid = obs.loc[obs["eligible"]].copy()
    feature_diffs = {}
    for r in valid.to_dict("records"):
        d = r["source_date"]
        if kind=="aaii":
            k = int(np.searchsorted(dates,(d+pd.Timedelta(days=7)).to_datetime64(),side="right"))
            source = survey.iloc[int(r["source_row"])]
            x = 100*(float(source["bullish"])-float(source["bearish"]))
            expected_features = {"x":x,"lo":max(-25-x,0),"hi":max(x-25,0)}
            if pd.Timestamp(source["date"])!=d: discrepancies.append({"source_date":d,"reason":"source_row_date"})
        else:
            k = positions[d]+2
            e,c = source_values[d]
            expected_features = {"e":e,"c":c,"eq":float(e>1)}
        for col,value in expected_features.items():
            feature_diffs[col] = max(feature_diffs.get(col,0.),abs(r[col]-value))
        a,b = k+1,k+1+h
        if r["t"] != pd.Timestamp(dates[k]) or r["target_start"] != pd.Timestamp(dates[a]) or r["target_end"] != pd.Timestamp(dates[b]):
            discrepancies.append({"source_date":d,"reason":"timestamp_endpoint"})
        if r["target_end"]>cutoff: discrepancies.append({"source_date":d,"reason":"label_after_cutoff"})
        for col,value in zip(BASE,background_at(close,k)):
            max_diff[col] = max(max_diff[col],abs(r[col]-value))
        if kind=="aaii":
            label_diff["y"] = max(label_diff["y"],abs(r["y"]-100*(close[b]/close[a]-1)))
        else:
            ret,mdd = window_labels(close[a:b+1])
            label_diff["y_return"] = max(label_diff["y_return"],abs(r["y_return"]-ret))
            label_diff["y_mdd"] = max(label_diff["y_mdd"],abs(r["y_mdd"]-mdd))
    passed = not discrepancies and max([*max_diff.values(),*label_diff.values(),*feature_diffs.values()])<TOL
    return {"eligible_existing_rows_checked":len(valid),"h":h,"actual_returns":h,"actual_price_points":h+1,
            "date_failures":discrepancies,"max_baseline_abs_diff":max_diff,"max_label_abs_diff":label_diff,
            "max_source_feature_abs_diff":feature_diffs,"passed":passed},valid


def mse_summary(frame,models):
    return {m:float(np.mean((frame["y"]-frame["pred_"+m])**2)) if len(frame) else None for m in models}


def paired_losses(pred,models,pairs):
    mse = mse_summary(pred,models)
    annual = []; worst = []
    for m,b in pairs:
        error_m = (pred["y"]-pred["pred_"+m])**2
        error_b = (pred["y"]-pred["pred_"+b])**2
        delta = error_m-error_b
        positive_total = float(delta.loc[delta>0].sum())
        total = float(delta.sum())
        for year,f in pred.groupby(pred["t"].dt.year):
            idx=f.index
            value=float(delta.loc[idx].sum())
            annual.append({"comparison":m+"_vs_"+b,"year":int(year),"n":len(f),"mse_model":float(error_m.loc[idx].mean()),
                           "mse_baseline":float(error_b.loc[idx].mean()),"extra_squared_error_sum":value,
                           "share_of_total_signed_extra_error":value/total if total else None,
                           "improvement_pct":100*(1-error_m.loc[idx].mean()/error_b.loc[idx].mean())})
        ranked = delta.sort_values(ascending=False).head(10)
        rows = []
        for idx,value in ranked.items():
            r=pred.loc[idx]
            rows.append({"source_date":r["source_date"],"t":r["t"],"target_end":r["target_end"],"y":r["y"],
                         "prediction_model":r["pred_"+m],"prediction_baseline":r["pred_"+b],"extra_squared_error":value,
                         **{col:r[col] for col in ["x","e","c","eq","rv20"] if col in r}})
        worst.append({"comparison":m+"_vs_"+b,"extra_error_sum":total,"positive_extra_error_sum":positive_total,
                      "top10_positive_extra_error_share":float(ranked.clip(lower=0).sum()/positive_total) if positive_total else None,
                      "worst_rows":rows})
    return {"n":len(pred),"mse":mse,"comparisons":{m+"_vs_"+b:100*(1-mse[m]/mse[b]) for m,b in pairs},
            "annual_loss_contributions":annual,"worst_error_rows":worst}


def fit_diagnostics(obs,pred,fits,ycol,initial_start):
    detail=[]; shifts=[]; failures=[]
    for fit in fits:
        year,model=int(fit["year"]),fit["model"]
        boundary=pd.Timestamp(f"{year}-01-01")
        train=obs.loc[obs["eligible"] & (obs["t"]<boundary) & (obs["target_end"]<boundary)]
        if "source_date" in train and initial_start=="2012-06-11": train=train.loc[train["source_date"]>=initial_start]
        else: train=train.loc[train["t"]>=initial_start]
        ev=pred.loc[pred["t"].dt.year==year]
        features=fit["features"]
        matrix=train[features].to_numpy(float)
        mean,scale=matrix.mean(axis=0),matrix.std(axis=0,ddof=0)
        mean_diff=float(np.max(abs(mean-np.array(fit["mean"])))) if features else 0.
        scale_diff=float(np.max(abs(scale-np.array(fit["scale"])))) if features else 0.
        check={"year":year,"model":model,"train_n":len(train),"eval_n":len(ev),"training_labels_end_max":train["target_end"].max(),
               "training_t_max":train["t"].max(),"mean_abs_diff_max":mean_diff,"scale_abs_diff_max":scale_diff,
               "training_y_mean":train[ycol].mean(),"training_y_std":train[ycol].std(ddof=0),
               "evaluation_y_mean":ev["y"].mean(),"evaluation_y_std":ev["y"].std(ddof=0)}
        if len(train)!=fit["train_rows"] or mean_diff>TOL or scale_diff>TOL:
            failures.append({"year":year,"model":model,"reason":"training_population_or_scaling"})
        if train["target_end"].max()>=boundary or train["t"].max()>=boundary:
            failures.append({"year":year,"model":model,"reason":"immature_training"})
        if fit.get("status","estimable")!="estimable":
            check["status"]="not_estimable"; detail.append(check);continue
        z=np.column_stack([np.ones(len(train)),(matrix-mean)/scale])
        ze=np.column_stack([np.ones(len(ev)),(ev[features].to_numpy(float)-mean)/scale])
        beta=np.array(fit["beta"],float)
        fitted=z@beta; predicted=ze@beta
        diff=float(np.max(abs(predicted-ev["pred_"+model].to_numpy()))) if len(ev) else 0.
        # No solve/lstsq, only verify stored solution and inspect design geometry.
        normal_residual=float(np.max(abs(z.T@(train[ycol].to_numpy()-fitted)))/len(train))
        _,singular,vt=np.linalg.svd(z,full_matrices=False)
        condition=float(singular[0]/singular[-1])
        rank=int((singular>singular[0]*max(z.shape)*np.finfo(float).eps).sum())
        leverage_train=((z@vt.T)/singular)**2
        leverage_eval=((ze@vt.T)/singular)**2
        htrain=leverage_train.sum(axis=1); heval=leverage_eval.sum(axis=1)
        check.update({"status":"estimable","prediction_abs_diff_max":diff,"saved_solution_gradient_max_per_row":normal_residual,
                      "design_condition_number":condition,"computed_rank":rank,"n_parameters":z.shape[1],
                      "training_prediction_min":fitted.min(),"training_prediction_max":fitted.max(),
                      "evaluation_prediction_min":predicted.min(),"evaluation_prediction_max":predicted.max(),
                      "evaluation_prediction_negative_n":int((predicted<0).sum()),
                      "evaluation_prediction_outside_train_target_range_n":int(((predicted<train[ycol].min()) | (predicted>train[ycol].max())).sum()),
                      "training_leverage_max":htrain.max(),"evaluation_leverage_max":heval.max(),
                      "evaluation_leverage_over_train_max_n":int((heval>htrain.max()).sum()),
                      "training_mse":float(np.mean((train[ycol]-fitted)**2)),"evaluation_mse":float(np.mean((ev["y"]-predicted)**2)),
                      "standardized_beta":beta,"training_extreme_n":int((train["eq"]==1).sum()) if "eq" in train else None})
        if diff>TOL or normal_residual>TOL or rank!=z.shape[1]: failures.append({"year":year,"model":model,"reason":"saved_solution_or_prediction"})
        for j,col in enumerate(features):
            et=ev[col].to_numpy(); tt=train[col].to_numpy(); standardized=(et-mean[j])/scale[j]
            shifts.append({"year":year,"model":model,"feature":col,"train_n":len(train),"eval_n":len(ev),
                           "train_mean":mean[j],"train_std":scale[j],"eval_mean":et.mean(),"eval_std":et.std(ddof=0),
                           "mean_shift_training_std_units":(et.mean()-mean[j])/scale[j],
                           "train_min":tt.min(),"train_max":tt.max(),"eval_min":et.min(),"eval_max":et.max(),
                           "eval_outside_train_range_n":int(((et<tt.min()) | (et>tt.max())).sum()),
                           "eval_abs_z_gt3_n":int((abs(standardized)>3).sum()),"eval_abs_z_max":abs(standardized).max(),
                           "coefficient_per_original_unit":beta[j+1]/scale[j],
                           "eval_contribution_min":(standardized*beta[j+1]).min(),"eval_contribution_max":(standardized*beta[j+1]).max()})
        detail.append(check)
    return {"saved_fits_inspected":len(fits),"new_fits":0,"failures":failures,"fit_diagnostics":detail,"feature_shifts":shifts}


def code_inspection(root,kind):
    # Read exact immutable source. Do not import it or execute any old entrypoint.
    source=(root/"executor/analyze.py").read_text()
    markers = {"std_ddof0_training": "a.std(axis=0, ddof=0)" in source if kind=="aaii" else "a.std(axis=0,ddof=0)" in source,
               "strict_label_maturity": '(obs["target_end"] < boundary)' in source if kind=="aaii" else '(obs["target_end"]<boundary)' in source,
               "targets_full_window": "c[a:b+1]" in source if kind=="aaii" else "c[k+1:k+22]" in source,
               "no_automatic_prediction_clip": "np.clip" not in source,
               "two_quote_wait" if kind=="putcall" else "survey_plus7_strict_after": "k = i+2" in source if kind=="putcall" else 'side="right"' in source}
    return {"path":str(root/"executor/analyze.py"),"sha256":sha(root/"executor/analyze.py"),"source_markers":markers,
            "inspection_type":"literal source checks plus independent numerical audit; no import/old execution"}


def synthetic():
    tests=[]
    def check(name,value,expected):
        passed=bool(np.allclose(value,expected,atol=1e-12,rtol=1e-12))
        tests.append({"name":name,"actual":value,"independent_expected":expected,"passed":passed})
        if not passed: raise AssertionError(name)
    check("risk_future_peak_only",window_labels([100,120,90,130]),[30,25])
    check("risk_up_zero",window_labels([100,110,120]),[20,0])
    z=np.array([[1,-1],[1,0],[1,1]],float);beta=np.array([3,2.]);y=np.array([1,3,5.])
    check("saved_coefficient_prediction_no_fitting",z@beta,y)
    check("saved_normal_equation_zero",z.T@(y-z@beta),[0,0])
    px=np.array([100*(1.001**i) for i in range(300)])
    check("background_return20",background_at(px,260)[0],100*(1.001**20-1))
    pred=pd.DataFrame({"source_date":pd.to_datetime(["2015-01-02","2016-01-04"]),"t":pd.to_datetime(["2015-01-02","2016-01-04"]),
                       "target_end":pd.to_datetime(["2015-02-02","2016-02-04"]),"y":[0.,0.],"pred_B":[2.,3.],"pred_I":[1.,1.]})
    res=paired_losses(pred,["B","I"],[("B","I")])
    check("paired_loss_sign_new_minus_base",[r["extra_squared_error_sum"] for r in res["annual_loss_contributions"]],[3,8])
    check("paired_relative_mse",res["comparisons"]["B_vs_I"],-550)
    dates=pd.to_datetime(["2014-12-31","2015-01-01","2015-01-02"])
    check("strict_maturity_boundary",(dates<pd.Timestamp("2015-01-01")).to_numpy() if hasattr((dates<pd.Timestamp("2015-01-01")),"to_numpy") else dates<pd.Timestamp("2015-01-01"),[True,False,False])
    write_json(HERE/"synthetic-check.json",{"passed":True,"real_data_loaded":False,"new_fits":0,"checks":tests,"code_sha256":sha(__file__)})
    print("synthetic checks passed: "+str(len(tests)))


def run():
    marker=HERE/"actual-run.json"
    if marker.exists(): raise RuntimeError("sole diagnostic run already consumed")
    with marker.open("x") as f:
        json.dump({"status":"started","time":datetime.now(timezone.utc).isoformat(),"new_fits":0,"code_sha256":sha(__file__)},f)
    identities={}
    try:
        identities["aaii"]=frozen_identity(AAII);identities["putcall"]=frozen_identity(PC)
        aobs=load_dates(AAII/"executor/run-01/observations-h120.csv")
        apred=load_dates(AAII/"executor/run-01/predictions-h120.csv")
        afits=json.loads((AAII/"executor/run-01/fits-h120.json").read_text())
        labels,_=label_audit(AAII,aobs,"aaii")
        adiag=fit_diagnostics(aobs,apred,afits,"y","1995-01-01")
        amodels=["I","X","XE","B","BX","BXE"]
        aloss=paired_losses(apred,amodels,[("B","I"),("BX","B"),("BXE","B"),("BXE","BX"),("BX","I"),("BXE","I")])
        pcobs=load_dates(PC/"executor/run-01/observations.csv")
        pclabels,_=label_audit(PC,pcobs,"putcall")
        pcresults={}
        for target,ycol in [("window_mdd20","y_mdd"),("forward_return20","y_return")]:
            pred=load_dates(PC/f"executor/run-01/predictions-{target}.csv")
            fits=json.loads((PC/f"executor/run-01/fits-{target}.json").read_text())
            diag=fit_diagnostics(pcobs,pred,fits,ycol,"2012-06-11")
            models=["I","E","T","EQ","B","BE","BT","BEQ"]
            loss=paired_losses(pred,models,[("B","I"),("BE","B"),("BT","B"),("BEQ","BE"),("BE","I"),("BT","I"),("E","I"),("T","I"),("EQ","E")])
            negatives={m:{"n":int((pred["pred_"+m]<0).sum()),"share":float((pred["pred_"+m]<0).mean())} for m in models}
            negative_examples=pred.loc[(pred["pred_BEQ"]<0) | (pred["pred_B"]<0)].copy()
            risk_rows=negative_examples.sort_values("pred_BEQ").head(10)
            pcresults[target]={"diagnostics":diag,"loss":loss,"negative_predictions":negatives,
                               "negative_examples":risk_rows[["source_date","t","target_end","e","c","eq","y","pred_I","pred_B","pred_BE","pred_BT","pred_BEQ"]].to_dict("records")}
        failures=adiag["failures"]+sum([r["diagnostics"]["failures"] for r in pcresults.values()],[])
        passed=labels["passed"] and pclabels["passed"] and not failures
        aa_saved=json.loads((AAII/"executor/run-01/results.json").read_text())
        result={"status":"completed" if passed else "completed_with_detected_discrepancies","started_marker":json.loads(marker.read_text()),
                "completed_at":datetime.now(timezone.utc),"actual_diagnostic_runs":1,"model_fits":0,"network_requests":0,"pro_calls":0,
                "code_sha256":sha(__file__),"sealed_identities":identities,"implementation_checks_passed":passed,
                "code_inspection":{"aaii":code_inspection(AAII,"aaii"),"putcall":code_inspection(PC,"putcall")},
                "aaii120":{"labels":labels,"diagnostics":adiag,"loss":aloss},"putcall20":{"labels":pclabels,"targets":pcresults},
                "saved_other_AAII_horizons_context_no_recompute":{h:r["overall"] for h,r in aa_saved["horizons"].items() if h!="120"},
                "new_estimator_proposal":{"name":"Gamma log-link conditional mean with fixed training floor",
                    "formula":"risk_mean_pp = exp(intercept + standardized_features dot coefficients)",
                    "training_target":"replace exact zero training risk by fixed 0.000001 percentage points solely for Gamma objective; actual evaluation y remains unmodified",
                    "objective":"Gamma unit deviance 2*(y/mu - log(y/mu) -1), equivalently optimize mean(log(mu)+y/mu); intercept included",
                    "preprocessing":"same fixed features and training-only ddof0 standardization; mean model has intercept only; volatility model rv20 only; background and background+AAII same frozen five plus x",
                    "hyperparameters":"no regularization, no threshold search, no clipping predictions; fixed floor declared before new experiment; optimizer convergence/gradient/rank checks must be frozen in next protocol",
                    "status":"one proposal only; NOT FITTED; positive support addresses invalid negative risk values, not proven estimation improvement",
                    "limitations":["Gamma conditional variance need not fit actual risk distribution","zero floor changes training objective near zero and must be disclosed","log link can produce large positive extrapolations","no assurance it beats mature mean or volatility","MSE evaluation is distinct from Gamma fitting objective"]},
                "interpretation_boundary":{"proved":"all saved arithmetic comparisons and explicitly checked integrity items","inference":"shifts, leverage and coefficients can explain where sensitivity occurs, not causally prove why model loses","unresolved":"whether a nonnegative estimator improves future risk is not tested; empirical underperformance is not whole-family rejection"}}
        # Guard immutable sources again after the single pass.
        if frozen_identity(AAII)!=identities["aaii"] or frozen_identity(PC)!=identities["putcall"]:
            raise RuntimeError("sealed identity changed during diagnostic")
        write_json(HERE/"audit.json",result)
        annual=aloss["annual_loss_contributions"]
        shifts=adiag["feature_shifts"]
        for target,r in pcresults.items():
            annual += [{"target":target,**v} for v in r["loss"]["annual_loss_contributions"]]
            shifts += [{"target":target,**v} for v in r["diagnostics"]["feature_shifts"]]
        pd.DataFrame(annual).to_csv(HERE/"annual-loss-contributions.csv",index=False)
        pd.DataFrame(shifts).to_csv(HERE/"feature-shifts.csv",index=False)
        size=sum(p.stat().st_size for p in HERE.iterdir() if p.is_file())
        if size>4*1024*1024: raise RuntimeError("diagnostic output budget exceeded")
        print(json.dumps({"status":result["status"],"fits":0,"actual_diagnostic_runs":1,"aaii120":aloss["comparisons"],
                          "putcall":{t:r["loss"]["comparisons"] for t,r in pcresults.items()},"bytes":size}))
    except Exception as exc:
        write_json(HERE/"failure.json",{"status":"failed","error":str(exc),"actual_diagnostic_runs":1,"new_fits":0,"sealed_identities":identities})
        raise


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-diagnostic",action="store_true")
    args=parser.parse_args()
    if args.run_diagnostic: run()
    else: synthetic()
