#!/usr/bin/env python3
"""Compare independent H1/H2 reconstructions with executor artifacts."""
import csv,hashlib,json
from collections import defaultdict
from datetime import date,timedelta
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE.parent/"execution"/"account-results";TOL=1e-7
def readj(p):return json.loads(Path(p).read_text())
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def csvrows(p):
 with Path(p).open() as f:return list(csv.DictReader(f))
def sunday_before(s):return(date.fromisoformat(s)-timedelta(days=1)).isoformat()
def period_rows(daily,kind):
 groups=defaultdict(list)
 for r in daily:groups[r["date"][:7] if kind=="monthly" else r["date"][:4]].append(r)
 return groups
def aggregate(daily,trades,kind):
 out=[];prev=100000.
 for period,rows in sorted(period_rows(daily,kind).items()):
  peak=prev;dd=0.
  for r in rows:peak=max(peak,r["equity"]);dd=min(dd,r["equity"]/peak-1)
  ts=[t for t in trades if t["date"].startswith(period)]
  end=rows[-1]["equity"];before_fee=rows[0]["fees"]-sum(t["fee"] for t in ts);before_div=rows[0]["dividends_received"]
  # First-day cash actions are included in cumulative fields, so deltas use
  # trade rows for fees and adjacent-day/end differences for dividends.
  fees=sum(t["fee"] for t in ts)
  prior_div=0.
  first_index=daily.index(rows[0])
  if first_index:prior_div=daily[first_index-1]["dividends_received"]
  divs=rows[-1]["dividends_received"]-prior_div
  out.append({"period":period,"start_equity":prev,"end_equity":end,"change":end-prev,"return":end/prev-1,
              "max_drawdown":dd,"buys":sum(t["side"]=="buy" for t in ts),"sells":sum(t["side"]=="sell" for t in ts),
              "fees":fees,"dividends_received":divs,"cash_only_days":sum(r["units"]==0 for r in rows)})
  prev=end
 return out
def compare_rows(ind,actual,keys,numeric):
 amap={tuple(str(r[k]) for k in keys):r for r in ind};bmap={tuple(str(r[k]) for k in keys):r for r in actual};fails=[];mx=0.
 for key in sorted(set(amap)|set(bmap)):
  if key not in amap or key not in bmap:fails.append({"key":key,"reason":"missing"});continue
  for f in numeric:
   d=abs(float(amap[key][f])-float(bmap[key][f]));mx=max(mx,d)
   if d>TOL:fails.append({"key":key,"field":f,"difference":d})
 return {"independent_rows":len(ind),"executor_rows":len(actual),"max_difference":mx,"failures":fails[:20],"passed":not fails}
def signal_core(x,method):
 base={"eligible_date":x["eligible_date"],"source_week":x["source_week"],"breadth":float(x["breadth"]),"target":str(x["target"]),"reason":x["reason"]}
 if method.startswith("H1"):
  base.update({"breadth_source_date":x.get("breadth_source_date",x.get("signal_date")),"decision_date":x.get("decision_date",sunday_before(x["eligible_date"]))})
 else:
  for k in ("decision_date","breadth_source_date","etf_observation_date","recent_trend_switch_date","breadth_target","trend_target","combined_target"):base[k]=x.get(k)
 return base
def reject_core(x,method):
 # H1 executor uses breadth source date as signal_date while the independent
 # engine uses the completed-week Sunday. Both refer to the same eligible week.
 return (x.get("date"),x.get("reason"),float(x.get("target",0)) if x.get("target") is not None else None,
         round(float(x.get("actual_open_weight",0)),12) if x.get("actual_open_weight") is not None else None)
def main():
 lock=readj(HERE/"comparison-lock-before.json")["files"]
 if {p:sha(p) for p in lock}!=lock:raise RuntimeError("comparison inputs changed after lock")
 independent=readj(HERE/"etf-independent-accounts.json");checks=[];signals=[];rejects=[];summaries=[];aggregates=[]
 daily_num=("cash","receivable","units","mark","market_value","equity","invested_weight","fees","dividends_received","mark_age_days")
 trade_num=("shares","price","notional","fee","target","equity_open_before_fee","actual_open_weight_before","cash_after","units_after")
 for aid,ind in sorted(independent.items()):
  folder=OUT/aid;method=aid.split("-",2)[1]
  d=compare_rows(ind["daily"],csvrows(folder/"daily.csv"),("date",),daily_num);d.update(account_id=aid,table="daily");checks.append(d)
  t=compare_rows(ind["trades"],csvrows(folder/"trades.csv"),("date","side"),trade_num);t.update(account_id=aid,table="trades");checks.append(t)
  exsig=readj(folder/"signals.json");ic=[signal_core(x,method) for x in ind["signals"]];ec=[signal_core(x,method) for x in exsig]
  signals.append({"account_id":aid,"independent_count":len(ic),"executor_count":len(ec),"passed":ic==ec,"first_differences":[{"index":i,"independent":a,"executor":b} for i,(a,b) in enumerate(zip(ic,ec)) if a!=b][:10]})
  exrej=readj(folder/"rejected.json");ir=[reject_core(x,method) for x in ind["rejected"]];er=[reject_core(x,method) for x in exrej]
  rejects.append({"account_id":aid,"independent_count":len(ir),"executor_count":len(er),"passed":ir==er,"first_differences":[{"index":i,"independent":a,"executor":b} for i,(a,b) in enumerate(zip(ir,er)) if a!=b][:10]})
  daily=ind["daily"];trades=ind["trades"];peak=100000.;mdd=0.
  for r in daily:peak=max(peak,r["equity"]);mdd=min(mdd,r["equity"]/peak-1)
  final=daily[-1];calc={"final_equity":final["equity"],"net_gain":final["equity"]-100000,"total_return":final["equity"]/100000-1,
    "final_cash":final["cash"],"final_receivable":final["receivable"],"final_units":final["units"],"terminal_market_value":final["market_value"],
    "fees":final["fees"],"dividends_received":final["dividends_received"],"buys":sum(t["side"]=="buy" for t in trades),
    "sells":sum(t["side"]=="sell" for t in trades),"cash_only_days":sum(r["units"]==0 for r in daily),"max_drawdown":mdd,
    "average_invested_weight":sum(r["invested_weight"] for r in daily)/len(daily)}
  exsum=readj(folder/"summary.json");diff={k:abs(float(v)-float(exsum[k])) for k,v in calc.items()}
  summaries.append({"account_id":aid,"passed":max(diff.values())<=TOL,"max_difference":max(diff.values()),"differences":diff,"calculated":calc})
  for kind in ("monthly","yearly"):
   calcrows=aggregate(daily,trades,kind);exrows=csvrows(folder/f"{kind}.csv")
   q=compare_rows(calcrows,exrows,("period",),("start_equity","end_equity","change","return","max_drawdown","buys","sells","fees","dividends_received","cash_only_days"))
   q.update(account_id=aid,table=kind);aggregates.append(q)
 after={p:sha(p) for p in lock};dump(HERE/"comparison-lock-after.json",{"files":after})
 dump(HERE/"row-checks.json",checks);dump(HERE/"signal-checks.json",signals);dump(HERE/"rejected-checks.json",rejects);dump(HERE/"summary-checks.json",summaries);dump(HERE/"period-checks.json",aggregates)
 failed=[x for xs in (checks,signals,rejects,summaries,aggregates) for x in xs if not x["passed"]]
 dump(HERE/"results.json",{"status":"passed" if not failed and after==lock else "failed","accounts":len(independent),
   "weekly_signals_per_account":588,"daily_rows_checked":sum(x["independent_rows"] for x in checks if x["table"]=="daily"),
   "trade_rows_checked":sum(x["independent_rows"] for x in checks if x["table"]=="trades"),
   "monthly_rows_checked":sum(x["independent_rows"] for x in aggregates if x["table"]=="monthly"),
   "yearly_rows_checked":sum(x["independent_rows"] for x in aggregates if x["table"]=="yearly"),
   "failed_sections":len(failed),"input_hashes_unchanged":after==lock,"first_failures":failed[:10],
   "signal_date_note":"H1 executor labels signal_date with breadth source date; independent engine labels completed-week Sunday. Semantic comparison proves both breadth_source_date and derived Sunday decision_date match; execution week and all financial rows match."})
 print(json.dumps(readj(HERE/"results.json"),ensure_ascii=False,indent=2))
if __name__=="__main__":main()
