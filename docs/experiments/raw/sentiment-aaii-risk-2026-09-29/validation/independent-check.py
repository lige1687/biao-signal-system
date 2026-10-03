#!/usr/bin/env python3
"""Independent source/timing/target-path expectation; never emits all real labels."""
import bisect, csv, datetime as dt, hashlib, json, math
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
PROTOCOL_SHA="10610236e4da9e497ee43086d3f5b9845d0c7bc9c9f16018dc15d254d66f8230"
INPUT_SHA={"aaii-candidate-values.csv":"12f30895c7ea2c68663a60f2d60a85384dfd0d9d324474e0501298e460cf9c05",
           "px_SPY.csv":"952f397be0ccc5745185b91cce6acc781737c0f30a7a34aa8a230ae892ed5e45"}
T_DATES=["2010-01-08","2015-01-09","2020-01-10","2022-01-07","2025-07-03","2026-01-02"]
RANGE_START=dt.date(1995,1,1); EVAL_START=dt.date(2010,1,1); END=dt.date(2026,6,30)

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read_csv(p):
    with p.open(newline="",encoding="utf-8-sig") as f: return list(csv.DictReader(f))
def dateval(s): return dt.date.fromisoformat(s[:10])

def load_inputs():
    protocol_path=BASE/"protocol.json"
    if digest(protocol_path)!=PROTOCOL_SHA: raise SystemExit("protocol hash drift")
    protocol=json.loads(protocol_path.read_text())
    manifest=json.loads((BASE/"source-manifest.json").read_text())
    for name,expected in INPUT_SHA.items():
        got=digest(BASE/"inputs"/name)
        if got!=expected or manifest["inputs"][name]["sha256"]!=expected: raise SystemExit(f"input hash drift: {name}")
    surveys=read_csv(BASE/"inputs/aaii-candidate-values.csv")
    quotes=read_csv(BASE/"inputs/px_SPY.csv")
    if list(surveys[0])!=["date","bullish","neutral","bearish","bull_bear","spread_pp","ma20_pp"]: raise SystemExit("AAII columns changed")
    if list(quotes[0])!=["Date","Close","Volume"]: raise SystemExit("SPY columns changed")
    return protocol,surveys,quotes

def finite_positive(s):
    try:
        x=float(s); return x if math.isfinite(x) and x>0 else None
    except (TypeError,ValueError): return None

def window_mdd(window):
    """Largest peak-to-later-trough decline, with both endpoints inside window."""
    peak=window[0]; peak_i=0; best=0.0; best_peak_i=0; trough_i=0
    for idx,value in enumerate(window[1:],start=1):
        loss=1.0-value/peak
        if loss>best:
            best=loss; best_peak_i=peak_i; trough_i=idx
        if value>peak:
            peak=value; peak_i=idx
    return {"target_pct":100*best,"peak_index":best_peak_i,"trough_index":trough_i,
            "peak_close":window[best_peak_i],"trough_close":window[trough_i]}

def path_availability(prices, dates, t_index, cutoff=END):
    """Check only existence/validity of exactly 121 future closes; compute no target."""
    a=t_index+1; b=t_index+121
    if b>=len(prices) or dates[b]>cutoff: return {"valid":False,"reason":"incomplete_or_after_cutoff","a_index":a,"b_index":b}
    window=prices[a:b+1]
    if len(window)!=121 or any(x is None for x in window): return {"valid":False,"reason":"invalid_or_missing_close","a_index":a,"b_index":b}
    return {"valid":True,"a_index":a,"b_index":b}

def target_path(prices, dates, t_index, cutoff=END):
    """Compute a real risk value only when called for a prespecified example."""
    available=path_availability(prices,dates,t_index,cutoff)
    if not available["valid"]: return available
    a=available["a_index"]; b=available["b_index"]
    window=prices[a:b+1]
    measured=window_mdd(window)
    return {"valid":True,"a_index":a,"b_index":b,"target_pct":measured["target_pct"],
            "peak_index":a+measured["peak_index"],"trough_index":a+measured["trough_index"],
            "peak_close":measured["peak_close"],"trough_close":measured["trough_close"]}

def baselines_valid(prices,i):
    if i<251: return False
    if any(x is None for x in prices[i-251:i+1]): return False
    # r20/r63, 200-close mean, 252-close drawdown, and 20-return volatility all covered.
    return all(x is not None for x in prices[i-63:i+1])

def synthetic_checks():
    up=[100,101,102,103]; rise_fall=[100,110,99]
    pre_peak=[200,100,90]
    missing=[100,102,None,98]
    up_result=window_mdd(up); rise_result=window_mdd(rise_fall); pre_result=window_mdd(pre_peak[1:])
    assert up_result["target_pct"]==0.0
    assert math.isclose(rise_result["target_pct"],10.0) and rise_result["peak_close"]==110 and rise_result["trough_close"]==99
    assert math.isclose(pre_result["target_pct"],10.0)
    assert any(x is None for x in missing)
    cutoff=dt.date(2026,6,30); fake_dates=[cutoff-dt.timedelta(days=121-i) for i in range(123)]
    # Position 0 is t; 121 future closes through final date is mature; one later t is not.
    mature=target_path([100.0]*123,fake_dates,0,cutoff)
    late=target_path([100.0]*123,fake_dates,1,cutoff)
    missing_dates=[dt.date(2020,1,1)+dt.timedelta(days=i) for i in range(123)]
    missing_target=target_path([100.0]+[100.0]*119+[None,100.0],missing_dates,0,missing_dates[-1])
    assert not missing_target["valid"] and missing_target["reason"]=="invalid_or_missing_close"
    return {
      "all_up_zero":{"input_prices":up,"calculated_pct":up_result["target_pct"],"expected_pct":0.0},
      "rise_then_fall":{"input_prices":rise_fall,"calculated_pct":rise_result["target_pct"],"peak_close":rise_result["peak_close"],"trough_close":rise_result["trough_close"]},
      "prewindow_peak_ignored":{"prior_outside_window":200,"future_window_prices":pre_peak[1:],"calculated_pct":pre_result["target_pct"],"expected_pct":10.0,"incorrect_if_prewindow_peak_used_pct":55.0},
      "missing_close_excludes_whole_window":{"future_window_prices_example":missing,"121_close_test_reason":missing_target["reason"],"expected_valid":False},
      "endpoint_boundary":{"mature_t_index_0_valid":mature["valid"],"late_t_index_1_valid":late["valid"],"rule":"last required close on cutoff is valid; next quote beyond cutoff is not"}}

def main():
    protocol,surveys,quote_rows=load_inputs()
    quote_dates=[]; prices=[]; invalid_quote_rows=[]
    for n,row in enumerate(quote_rows,2):
        try: day=dateval(row["Date"])
        except Exception: invalid_quote_rows.append(n); continue
        quote_dates.append(day); prices.append(finite_positive(row["Close"]))
    if quote_dates!=sorted(quote_dates) or len(set(quote_dates))!=len(quote_dates): raise SystemExit("SPY dates not strictly ordered/unique")
    qindex={d:i for i,d in enumerate(quote_dates)}
    qdays=[d for d in quote_dates]
    parsed=[]; invalid_survey=[]; mappings=[]
    for physical,row in enumerate(surveys,2):
        try: sd=dateval(row["date"])
        except Exception:
            invalid_survey.append(physical); continue
        try: x=float(row["spread_pp"]); xok=math.isfinite(x)
        except Exception: xok=False
        publish_assumption=sd+dt.timedelta(days=7)
        ti=bisect.bisect_right(qdays,publish_assumption)
        tday=qdays[ti] if ti<len(qdays) else None
        mapping={"physical_row":physical,"source_date":sd,"x_valid":xok,"x":x if xok else None,"assumed_publish_date":publish_assumption,"t_date":tday,"t_index":ti if tday else None}
        parsed.append(mapping); mappings.append(mapping)
    # Same t: protocol retains latest source date then physical source row.
    winners={}
    for m in parsed:
        if m["t_date"] is not None:
            key=m["t_date"]
            if key not in winners or (m["source_date"],m["physical_row"])>(winners[key]["source_date"],winners[key]["physical_row"]): winners[key]=m
    winner_rows=set(id(v) for v in winners.values())
    reason_counts={"invalid_source_date":len(invalid_survey),"no_quote_after_assumed_publication":sum(m["t_date"] is None for m in parsed),
                   "duplicate_t_superseded":sum(m["t_date"] is not None and id(m) not in winner_rows for m in parsed),
                   "invalid_x":0,"insufficient_252_quote_warmup":0,"before_1995_evaluation_range":0,
                   "target_endpoint_after_cutoff_or_quote_range":0,"target_missing_or_nonpositive_close":0,"outside_train_and_evaluation_ranges":0}
    records=[]
    for day,m in sorted(winners.items()):
        i=qindex[day]
        if not m["x_valid"]: reason_counts["invalid_x"]+=1; continue
        if not baselines_valid(prices,i): reason_counts["insufficient_252_quote_warmup"]+=1; continue
        if day<RANGE_START: reason_counts["before_1995_evaluation_range"]+=1; continue
        tp=path_availability(prices,quote_dates,i)
        if not tp["valid"]:
            reason_counts["target_endpoint_after_cutoff_or_quote_range" if tp["reason"]=="incomplete_or_after_cutoff" else "target_missing_or_nonpositive_close"]+=1; continue
        in_train=dt.date(1995,1,1)<=day<=dt.date(2009,12,31)
        in_eval=EVAL_START<=day<=END
        if not (in_train or in_eval): reason_counts["outside_train_and_evaluation_ranges"]+=1; continue
        records.append({"source_date":m["source_date"],"physical_row":m["physical_row"],"t_date":day,"t_index":i,
                        "split":"training" if in_train else "evaluation","x":m["x"],
                        "maturity_end":quote_dates[i+121]})
    # Prespecified samples: first fully eligible mapping whose t is on/after requested date.
    selected=[]
    for requested in map(dt.date.fromisoformat,T_DATES):
        hit=next((r for r in records if r["t_date"]>=requested),None)
        if hit is None:
            selected.append({"requested_date":requested.isoformat(),"selected":False,"reason":"no eligible t on/after request"}); continue
        idx=hit["t_index"]
        tp=target_path(prices,quote_dates,idx)
        selected.append({"requested_date":requested.isoformat(),"selected":True,"source_date":hit["source_date"].isoformat(),
                         "physical_source_row":hit["physical_row"],"assumed_publication_date":(hit["source_date"]+dt.timedelta(days=7)).isoformat()+" 23:59 Asia/Shanghai",
                         "t_date":hit["t_date"].isoformat(),"target_start":quote_dates[idx+1].isoformat(),"target_end":quote_dates[idx+121].isoformat(),
                         "target_pct":tp["target_pct"],"peak_date":quote_dates[tp["peak_index"]].isoformat(),"trough_date":quote_dates[tp["trough_index"]].isoformat(),
                         "peak_close":tp["peak_close"],"trough_close":tp["trough_close"]})
    # Pipeline counts, before range and common-coverage exclusions.
    t_mapped=sum(m["t_date"] is not None for m in parsed)
    common=len(records); train=sum(r["split"]=="training" for r in records); evaluation=sum(r["split"]=="evaluation" for r in records)
    mature_by_year={}
    for y in range(2010,2027):
        boundary=dt.date(y,1,1)
        mature_by_year[str(y)]=sum(r["t_date"]<boundary and r["maturity_end"]<boundary for r in records)
    # protocol maturity is for training rows in each evaluation year; count eligible historical rows by year as an expectation.
    quote_bad=sum(p is None for p in prices)
    out={"protocol_sha256":PROTOCOL_SHA,"input_sha256":INPUT_SHA,
         "price_basis_limit":"cached adjusted Close; historical adjustment/dividend vintage unknown",
         "source_identity":{"survey":{"rows":len(surveys),"valid_date_rows":len(parsed),"invalid_date_physical_rows":invalid_survey,"source_dates_monotonic":all(parsed[i]["source_date"]<=parsed[i+1]["source_date"] for i in range(len(parsed)-1)),"first_date":min(m['source_date'] for m in parsed).isoformat(),"last_date":max(m['source_date'] for m in parsed).isoformat()},
                            "spy":{"rows":len(quote_rows),"unique_ordered_dates":len(quote_dates),"invalid_date_rows":invalid_quote_rows,"invalid_or_nonpositive_close_rows":quote_bad,"first_date":quote_dates[0].isoformat(),"last_date":quote_dates[-1].isoformat()}},
         "timing_rule":{"assumed_publication":"survey source date + 7 calendar days, 23:59 Asia/Shanghai","t":"first actual SPY quote date strictly after assumed publication date","target":"t+1 through t+121 quote closes inclusive (121 closes, 120 changes); peak is inside this future window"},
         "coverage":{"raw_survey_rows":len(surveys),"valid_source_dates":len(parsed),"mapped_to_t_rows":t_mapped,
                     "mapped_t_date_min":min(winners).isoformat() if winners else None,"mapped_t_date_max":max(winners).isoformat() if winners else None,
                     "unique_t_after_latest_source_dedup":len(winners),"common_eligible_rows":common,"training_common_eligible_1995_2009":train,
                     "evaluation_common_eligible_2010_2026_06_30":evaluation,"evaluation_by_t_year":{str(y):sum(r['split']=='evaluation' and r['t_date'].year==y for r in records) for y in range(2010,2027)},
                     "exclusions_by_stage":reason_counts,
                     "tail_rows_excluded_by_incomplete_endpoint":reason_counts["target_endpoint_after_cutoff_or_quote_range"],
                     "mature_common_training_rows_available_before_evaluation_year":mature_by_year},
         "real_target_values_computed_only_for_prespecified_examples":sum(bool(x.get("selected")) for x in selected),
         "prespecified_examples":selected,"synthetic_checks":synthetic_checks(),
         "limitations":["Counts assert quote-row coverage only; no external holiday calendar qualified.","No forward-risk values were computed except the six prespecified examples.","Historical first publication time and survey revisions are unknown; +7 days is an assumption.","This checks source/timing/target expectations, not estimator correctness or predictive performance."]}
    (HERE/"expectation.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__": main()
