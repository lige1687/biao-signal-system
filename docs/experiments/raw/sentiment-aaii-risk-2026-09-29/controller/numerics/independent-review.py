#!/usr/bin/env python3
"""Independent saved-risk arithmetic only; no optimizer or executor import.
Default: generated tests. --audit: exactly one actual numerical review.
"""
import argparse
import hashlib
import json
import math
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
RUN=ROOT/"executor/run-01"
FEATURES={"I":[],"V":["rv20"],"B":["r20","r63","dma200","dd252","rv20"],"BX":["r20","r63","dma200","dd252","rv20","x"]}
PAIRS=[("BX","B"),("BX","I"),("BX","V"),("B","I"),("V","I"),("B","V")]
START=pd.Timestamp("1995-01-01")
TOL=1e-9


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def serial(o):
    if isinstance(o,dict):return {str(k):serial(v) for k,v in o.items()}
    if isinstance(o,(list,tuple)):return [serial(v) for v in o]
    if isinstance(o,np.ndarray):return serial(o.tolist())
    if o is pd.NaT:return None
    if isinstance(o,(pd.Timestamp,datetime)):return o.isoformat()
    if isinstance(o,np.integer):return int(o)
    if isinstance(o,np.bool_):return bool(o)
    if isinstance(o,(float,np.floating)):return float(o) if np.isfinite(o) else None
    return o


def write(path,data):Path(path).write_text(json.dumps(serial(data),indent=2,ensure_ascii=False,allow_nan=False)+"\n")


def sigmoid(eta):
    # Independent stable implementation; no scipy special or executor helper.
    eta=np.asarray(eta,float); out=np.empty_like(eta)
    pos=eta>=0
    out[pos]=1/(1+np.exp(-eta[pos]))
    e=np.exp(eta[~pos]);out[~pos]=e/(1+e)
    return out


def loss_gradient(theta,z,actual_fraction):
    mu=sigmoid(theta[0]+z@theta[1:]);error=mu-actual_fraction
    objective=np.dot(error,error)/len(error)+.001*np.dot(theta[1:],theta[1:])
    d=2*error*mu*(1-mu)/len(error)
    grad=np.r_[d.sum(),z.T@d+.002*theta[1:]]
    return float(objective),grad


def percentile(values,p):
    # Explicit sorted linear interpolation, independent of pandas quantile.
    a=sorted(float(v) for v in values if np.isfinite(v))
    if not a:return None
    point=(len(a)-1)*p
    lo=int(math.floor(point));hi=int(math.ceil(point));weight=point-lo
    return a[lo]+weight*(a[hi]-a[lo])


def load_frame(path):
    d=pd.read_csv(path,float_precision="round_trip")
    for col in ["source_date","t","target_start","target_end"]:
        if col in d:d[col]=pd.to_datetime(d[col])
    return d


def bindings():
    manifest=json.loads((RUN/"manifest.json").read_text())
    protocol=json.loads((ROOT/"protocol.json").read_text())
    source=json.loads((ROOT/"source-manifest.json").read_text())
    norm=json.loads((ROOT/"controller/norm-binding.json").read_text())
    code_review=json.loads((ROOT/"controller/code-review.json").read_text())
    if protocol["models"]!=FEATURES or protocol["estimation"]["lambda"]!=.001:
        raise RuntimeError("fixed model/lambda identity mismatch")
    actual={}
    for p in [ROOT/"protocol.json",ROOT/"source-manifest.json",ROOT/"controller/norm-binding.json",ROOT/"controller/code-review.json",RUN/"manifest.json"]:
        actual[str(p)]=sha(p)
    b=manifest["binding"]
    if sha(ROOT/"protocol.json")!=b["protocol_sha256"] or b["protocol_sha256"]!=code_review["protocol_sha256"]:raise RuntimeError("protocol identity drift")
    if sha(ROOT/"source-manifest.json")!=b["source_manifest_sha256"]:raise RuntimeError("source-manifest identity drift")
    if sha(ROOT/"controller/norm-binding.json")!=b["norm_binding_sha256"]:raise RuntimeError("norm binding identity drift")
    if code_review["code_sha256"]!=manifest["code_sha256"] or not code_review["accepted"]:raise RuntimeError("accepted code binding mismatch")
    for name,record in manifest["outputs"].items():
        p=RUN/name
        if sha(p)!=record["sha256"]:raise RuntimeError("sealed output drift: "+name)
        actual[str(p)]=sha(p)
    for name,record in protocol["inputs"].items():
        if record["sha256"]!=b["inputs"][name]["sha256"] or record["sha256"]!=source["inputs"][name]["sha256"]:
            raise RuntimeError("input fingerprint records inconsistent")
    for rec in norm["standards"]:
        matching=[r for r in b["authority_audit"] if r["bound_path"]==rec["source_path"]]
        if len(matching)!=1 or matching[0]["actual_sha256"]!=rec["sha256"] or matching[0]["changed"]:
            raise RuntimeError("norm frozen identity mismatch")
    return {"actual_file_hashes":actual,"input_hashes_declared_by_source_protocol_and_manifest":b["inputs"],
            "code_hash_in_accepted_review_and_run_manifest":manifest["code_sha256"],"norm_versions":norm["versions"],
            "norm_frozen_records":norm["standards"],
            "scope_note":"Read contract lists run-01, protocol, source-manifest, norm-binding and code-review. This subreview does not reopen raw inputs, norm snapshots or executor source; their declared bindings and root code review are recorded, not misrepresented as fresh file hashes."},protocol


def fits_review(obs,pred,fits,ledger):
    rows=[];failures=[];total_history=0
    ledger_map={(a["year"],a["model"]):a for a in ledger["attempts"]}
    all_years=list(range(2010,2027))
    if len(fits)!=68 or ledger["started_fits"]!=68 or ledger["completed_fits"]!=68 or ledger["failed_fits"]!=0:
        failures.append("fit counts inconsistent with completed core68")
    if len({(f["year"],f["model"]) for f in fits})!=len(fits):failures.append("duplicate fit identity")
    for year in all_years:
        missing=set(FEATURES)-{f["model"] for f in fits if f["year"]==year}
        if missing:failures.append({"year":year,"missing_models":sorted(missing)})
    for f in fits:
        year=f["year"];model=f["model"];bound=pd.Timestamp(f"{year}-01-01")
        mask=obs["eligible"] & (obs["t"]>=START) & (obs["t"]<bound) & (obs["target_end"]<bound)
        tr=obs.loc[mask];ev=pred.loc[pred["t"].dt.year==year]
        record={"year":year,"model":model,"train_rows_independent":len(tr),"eval_rows":len(ev),
                "train_source_row_sha256":hashlib.sha256(json.dumps(tr["source_row"].tolist(),separators=(",",":")).encode()).hexdigest(),
                "train_t_min":tr["t"].min(),"train_t_max":tr["t"].max(),"train_label_end_max":tr["target_end"].max(),
                "training_mean_risk_pp":tr["y"].mean(),"branch":f["branch"]}
        notes=[]
        if f["features"]!=FEATURES[model]:notes.append("feature identity")
        if len(tr)!=f["train_rows"] or len(tr)<100:notes.append("training row count")
        if tr["t"].max()>=bound or tr["target_end"].max()>=bound:notes.append("immature training")
        for col,actual in [("train_t_min",tr["t"].min()),("train_t_max",tr["t"].max()),("train_label_end_max",tr["target_end"].max()),("eval_t_min",ev["t"].min()),("eval_t_max",ev["t"].max())]:
            if pd.Timestamp(f[col])!=actual:notes.append(col+" metadata")
        actual=tr["y"].to_numpy(float)/100
        mean_fraction=float(actual.mean())
        record["target_mean_fraction_abs_diff"]=abs(mean_fraction-f["target_mean_fraction"])
        if record["target_mean_fraction_abs_diff"]>TOL:notes.append("training target mean")
        attempt=ledger_map.get((year,model))
        if attempt is None or attempt["status"]!="completed" or attempt["train_rows"]!=len(tr) or attempt["eval_rows"]!=len(ev):notes.append("ledger count/status")
        if attempt is not None and attempt["result"]!=f:notes.append("ledger final saved result")
        if model=="I":
            prediction=np.full(len(ev),100*mean_fraction)
            record["constant_mean_abs_diff"]=abs(f["constant_pp"]-100*mean_fraction)
            if f["branch"]!="arithmetic_mean" or f["optimizer_started"] or attempt["optimizer_log"]:notes.append("mean must not optimize")
            if record["constant_mean_abs_diff"]>TOL:notes.append("arithmetic mean value")
            record["optimizer_history_checked_rows"]=0
        else:
            columns=f["features"]
            train_x=tr[columns].to_numpy(float);mean=train_x.mean(axis=0);scale=train_x.std(axis=0,ddof=0)
            record["mean_abs_diff_max"]=float(np.max(abs(mean-np.asarray(f["mean"]))))
            record["scale_abs_diff_max"]=float(np.max(abs(scale-np.asarray(f["scale"]))))
            if not np.isfinite(train_x).all() or (scale<=0).any() or max(record["mean_abs_diff_max"],record["scale_abs_diff_max"])>TOL:notes.append("training-only scaling")
            z=(train_x-mean)/scale
            ze=(ev[columns].to_numpy(float)-mean)/scale
            if f["branch"]=="constant_zero":
                if mean_fraction!=0:notes.append("constant-zero branch without zero targets")
                prediction=np.zeros(len(ev));record["optimizer_history_checked_rows"]=0
            else:
                if f["branch"]!="bounded_sigmoid":notes.append("unexpected prediction branch")
                theta=np.asarray(f["beta"],float)
                prediction=100*sigmoid(theta[0]+ze@theta[1:])
                objective,gradient=loss_gradient(theta,z,actual)
                record.update({"objective_independent":objective,"objective_abs_diff":abs(objective-f["objective"]),
                               "final_gradient_independent":gradient,"gradient_abs_diff_max":float(np.max(abs(gradient-np.asarray(f["final_gradient"])))),
                               "max_abs_final_gradient_independent":float(np.max(abs(gradient))),"optimizer_success":f["success"],
                               "nit":f["nit"],"nfev":f["nfev"],"njev":f["njev"]})
                if not f["success"] or not np.isfinite(theta).all() or np.max(abs(gradient))>1e-6:notes.append("optimizer success/gradient")
                if record["objective_abs_diff"]>TOL or record["gradient_abs_diff_max"]>TOL or abs(f["max_abs_gradient"]-np.max(abs(gradient)))>TOL:notes.append("saved objective/gradient")
                history=f["optimizer_history"]
                starts=[h for h in history if h["stage"]=="single_start"]
                finals=[h for h in history if h["stage"]=="final"]
                if len(starts)!=1 or len(finals)!=1 or history[0]["stage"]!="single_start" or history[-1]["stage"]!="final":notes.append("single start/final log")
                if len(history)!=f["nit"]+2 or [h["iteration"] for h in history]!=list(range(len(history))):notes.append("iteration log numbering")
                if history!=attempt["optimizer_log"]:notes.append("ledger optimizer history")
                expected_initial=np.r_[math.log(mean_fraction/(1-mean_fraction)),np.zeros(len(columns))]
                initial_diff=float(np.max(abs(expected_initial-np.asarray(starts[0]["beta"]))))
                initial_obj,initial_grad=loss_gradient(expected_initial,z,actual)
                record.update({"initial_beta_abs_diff_max":initial_diff,"initial_objective_independent":initial_obj,
                               "initial_objective_abs_diff":abs(initial_obj-f["initial_objective"]),
                               "final_minus_initial_objective_independent":objective-initial_obj})
                if initial_diff>TOL or objective>initial_obj+1e-12 or abs(f["final_objective"]-objective)>TOL or abs(f["objective_change_final_minus_initial"]-(objective-initial_obj))>TOL:notes.append("initialization/nonincrease/final log")
                if np.max(abs(np.asarray(finals[0]["beta"])-theta))>TOL or abs(theta[0]-f["intercept"])>TOL:notes.append("final parameter/intercept log")
                max_o,max_g=0.,0.
                for h in history:
                    ht=np.asarray(h["beta"],float);ho,hg=loss_gradient(ht,z,actual)
                    max_o=max(max_o,abs(ho-h["objective"]));max_g=max(max_g,float(np.max(abs(hg-np.asarray(h["gradient"])))),abs(np.max(abs(hg))-h["max_abs_gradient"]))
                record.update({"optimizer_history_checked_rows":len(history),"history_objective_abs_diff_max":max_o,"history_gradient_abs_diff_max":max_g})
                total_history+=len(history)
                if max_o>TOL or max_g>TOL:notes.append("logged objective/analytic gradient")
        record["prediction_abs_diff_max"]=float(np.max(abs(prediction-ev["pred_"+model].to_numpy(float))))
        record["prediction_min"]=float(prediction.min());record["prediction_max"]=float(prediction.max())
        if record["prediction_abs_diff_max"]>TOL or not np.isfinite(prediction).all() or (prediction<0).any() or (prediction>100).any():notes.append("saved prediction/support")
        record["issues"]=notes;record["passed"]=not notes
        if notes:failures.append({"year":year,"model":model,"issues":notes})
        rows.append(record)
    return {"saved_model_records_checked":len(rows),"new_fits":0,"optimizer_calls":0,"optimizer_history_rows_checked":total_history,
            "failures":failures,"fits":rows,"passed":not failures}


def uncertainty_review(pred,results):
    all_reviews={};failures=[]
    losses={m:(pred["y"].to_numpy()-pred["pred_"+m].to_numpy())**2 for m in FEATURES}
    for block in [52,104]:
        d=pd.read_csv(RUN/f"draws-block{block}.csv",float_precision="round_trip")
        notes=[];ranges={};replays=[]
        if len(d)!=2000 or not d["seed"].eq(20260929+block).all() or not d["block_rows"].eq(block).all() or not d["n"].eq(len(pred)).all():notes.append("draw budget/seed/size")
        max_draw_ratio_diff=0.;max_range_diff=0.
        for m,b in PAIRS:
            key=f"{m}_vs_{b}";col="improvement_"+key
            independent=100*(1-d["mse_"+m].to_numpy()/d["mse_"+b].to_numpy())
            delta=float(np.max(abs(independent-d[col].to_numpy())))
            lo,hi=percentile(independent,.025),percentile(independent,.975)
            saved=results["uncertainty"][str(block)][key]
            range_delta=max(abs(lo-saved["p2_5"]),abs(hi-saved["p97_5"]))
            max_draw_ratio_diff=max(max_draw_ratio_diff,delta);max_range_diff=max(max_range_diff,range_delta)
            ranges[key]={"valid_draws":int(np.isfinite(independent).sum()),"p2_5_independent":lo,"p97_5_independent":hi,
                         "saved_range_abs_diff_max":range_delta,"all_saved_draw_ratio_abs_diff_max":delta}
            if saved["valid_draws"]!=2000 or saved["refit"] or delta>TOL or range_delta>TOL:notes.append("range or saved ratio "+key)
        for draw in [0,1]:
            r=d.iloc[draw];starts=json.loads(r["block_starts"])
            if len(starts)!=math.ceil(len(pred)/block) or any(s<0 or s>len(pred)-block for s in starts):notes.append("invalid block starts")
            indices=np.concatenate([np.arange(s,s+block) for s in starts])[:len(pred)]
            mse={m:float(loss[indices].sum()/len(indices)) for m,loss in losses.items()}
            mse_diff=max(abs(mse[m]-r["mse_"+m]) for m in FEATURES)
            ratios={f"{m}_vs_{b}":100*(1-mse[m]/mse[b]) for m,b in PAIRS}
            ratio_diff=max(abs(v-r["improvement_"+key]) for key,v in ratios.items())
            replays.append({"draw":draw,"block_starts":starts,"n":len(indices),"mse_independent":mse,
                            "mse_abs_diff_max":mse_diff,"improvements_independent":ratios,"improvement_abs_diff_max":ratio_diff})
            if mse_diff>TOL or ratio_diff>TOL:notes.append("paired block replay "+str(draw))
        all_reviews[str(block)]={"draws_checked":len(d),"all_six_ranges":ranges,"replayed_draws":replays,
                                 "max_saved_draw_ratio_abs_diff":max_draw_ratio_diff,"max_range_abs_diff":max_range_diff,"issues":notes,"passed":not notes}
        failures.extend([{ "block":block,"issue":n} for n in notes])
    return {"blocks":all_reviews,"failures":failures,"passed":not failures,"refits":0}


def synthetic():
    checks=[]
    def check(name,actual,expected,tol=1e-12):
        ok=bool(np.allclose(actual,expected,atol=tol,rtol=tol));checks.append({"name":name,"actual":actual,"expected":expected,"passed":ok})
        if not ok:raise AssertionError(name)
    z=np.array([[-1.],[0.],[1.]])
    objective,g=loss_gradient(np.array([0.,0.]),z,np.array([.1,.2,.3]))
    check("mean_fraction_objective",objective,(.4**2+.3**2+.2**2)/3)
    check("analytic_gradient",g,[.15,-1/30])
    theta=np.array([-.8,.3]);actual=np.array([.1,.2,.3]);_,gradient=loss_gradient(theta,z,actual)
    finite=[]
    for j in range(2):
        t1=theta.copy();t2=theta.copy();t1[j]+=1e-6;t2[j]-=1e-6
        finite.append((loss_gradient(t1,z,actual)[0]-loss_gradient(t2,z,actual)[0])/2e-6)
    check("analytic_gradient_finite_difference",gradient,finite,1e-9)
    check("stable_expit",sigmoid(np.array([-1000.,0.,1000.])),[0,.5,1])
    check("linear_percentile_2_5",percentile(range(2000),.025),49.975)
    check("linear_percentile_97_5",percentile(range(2000),.975),1949.025)
    starts=[1,0];idx=np.concatenate([np.arange(s,s+3) for s in starts])[:5]
    check("paired_block_truncation",idx,[1,2,3,0,1])
    check("mature_boundary_strict",np.array(pd.to_datetime(["2009-12-31","2010-01-01"])<pd.Timestamp("2010-01-01")),[True,False])
    write(HERE/"synthetic-check.json",{"passed":True,"new_fits":0,"real_records_loaded":False,"checks":checks,"code_sha256":sha(__file__)})
    print("synthetic checks passed: "+str(len(checks)))


def audit():
    marker=HERE/"actual-run.json"
    if marker.exists():raise RuntimeError("one actual numerical review already consumed")
    with marker.open("x") as f:json.dump({"started_at":datetime.now(timezone.utc).isoformat(),"code_sha256":sha(__file__),"new_fits":0},f)
    identity=None
    try:
        identity,protocol=bindings()
        obs=load_frame(RUN/"observations.csv");pred=load_frame(RUN/"predictions.csv")
        fits=json.loads((RUN/"fits.json").read_text());ledger=json.loads((RUN/"fit-ledger.json").read_text());results=json.loads((RUN/"results.json").read_text())
        fr=fits_review(obs,pred,fits,ledger)
        ur=uncertainty_review(pred,results)
        # No raw target recreation; root owns independent labels and opportunity set.
        status="passed" if fr["passed"] and ur["passed"] else "differences_detected"
        result={"status":status,"actual_runs":1,"new_model_fits":0,"optimizer_calls":0,"network_requests":0,
                "completed_at":datetime.now(timezone.utc),"code_sha256":sha(__file__),"tolerance":TOL,
                "identity":identity,"fit_review":fr,"uncertainty_review":ur,
                "summary_max_differences":{key:max(r.get(key,0.) for r in fr["fits"]) for key in ["mean_abs_diff_max","scale_abs_diff_max","constant_mean_abs_diff","objective_abs_diff","gradient_abs_diff_max","history_objective_abs_diff_max","history_gradient_abs_diff_max","prediction_abs_diff_max"]},
                "maximum_final_gradient":max(r.get("max_abs_final_gradient_independent",0.) for r in fr["fits"]),
                "boundary":"Numerical reconstruction of saved objective and estimates, not refitting, global optimality, causal evidence or independent market validation. Historical source release/revision and price vintages remain unknown.",
                "not_recomputed_here":["raw target paths","common population eligibility from raw files","annual/delete-year effect conclusions"],
                "model_features":FEATURES,"lambda":protocol["estimation"]["lambda"]}
        final,_=bindings()
        if final!=identity:raise RuntimeError("sealed bindings changed during numerical review")
        write(HERE/"audit.json",result)
        size=sum(p.stat().st_size for p in HERE.iterdir() if p.is_file())
        if size>2*1024*1024:raise RuntimeError("numerical review output budget exceeded")
        print(json.dumps({"status":status,"saved_models_checked":len(fits),"logged_stages_checked":fr["optimizer_history_rows_checked"],"new_fits":0,"max_differences":result["summary_max_differences"],"max_final_gradient":result["maximum_final_gradient"],"bytes":size}))
    except Exception as exc:
        write(HERE/"failure.json",{"status":"failed","error":str(exc),"actual_runs":1,"new_fits":0,"identity":identity})
        raise


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--audit",action="store_true");args=p.parse_args()
    if args.audit:audit()
    else:synthetic()
