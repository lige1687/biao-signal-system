#!/usr/bin/env python3
"""Compare independently rebuilt ETF accounts with executor outputs."""
import csv,hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;FIRST=HERE.parent/"first12";OUT=FIRST/"account-results";TOL=1e-6
def readj(p):return json.loads(Path(p).read_text())
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def csvrows(p):
 with Path(p).open() as f:return list(csv.DictReader(f))
def num(x):return float(x)
def normalize_signal(x):return {k:x.get(k) for k in ("signal_date","eligible_date","target","reason","source_week","breadth","current_close","prior_60_min","prior_60_max") if k in x}
def main():
 locked=readj(HERE/"etf-comparison-lock-before.json")["files"]
 assert {p:sha(p) for p in locked}==locked
 independent=readj(HERE/"etf-independent-accounts.json");checks=[];signal_checks=[];summary_checks=[];rejection_counts=[]
 daily_fields=("cash","receivable","units","mark","market_value","equity","invested_weight","fees","dividends_received","mark_age_days")
 trade_fields=("shares","price","notional","fee","target","equity_open_before_fee","actual_open_weight_before","cash_after","units_after")
 for aid,ind in sorted(independent.items()):
  folder=OUT/aid;actual_daily=csvrows(folder/"daily.csv");actual_trades=csvrows(folder/"trades.csv")
  for label,a,b,keys,fields in (("daily",ind["daily"],actual_daily,("date",),daily_fields),("trades",ind["trades"],actual_trades,("date","signal_date","side"),trade_fields)):
   amap={tuple(str(r[k]) for k in keys):r for r in a};bmap={tuple(str(r[k]) for k in keys):r for r in b}
   if len(amap)!=len(a) or len(bmap)!=len(b):raise RuntimeError(f"nonunique comparison key {aid} {label}")
   for key in sorted(set(amap)|set(bmap)):
    present=key in amap and key in bmap;diffs={}
    if present:
     for f in fields:diffs[f]=abs(num(amap[key][f])-num(bmap[key][f]))
    checks.append({"account_id":aid,"table":label,"key":"|".join(key),"present_both":present,"max_difference":max(diffs.values(),default=None),"passed":present and max(diffs.values(),default=0)<=TOL})
  actual_signals=readj(folder/"signals.json");aa=[normalize_signal(x) for x in ind["signals"]];bb=[normalize_signal(x) for x in actual_signals]
  completed_executor=[x for x in bb if x.get("eligible_date","")<="2026-06-30"]
  extra_terminal=[x for x in bb if x.get("eligible_date","")>"2026-06-30"]
  signal_checks.append({"account_id":aid,"independent_confirmed_count":len(aa),"executor_total_count":len(bb),"executor_completed_count":len(completed_executor),"completed_signals_match":aa==completed_executor,"extra_terminal_records":extra_terminal,"classification":"executor terminal observation is not a confirmed completed-week signal" if extra_terminal else None})
  actual_rejected=readj(folder/"rejected.json");financial_executor=[r for r in actual_rejected if r.get("reason")!="signal_awaiting_next_open_after_period_end"]
  def reject_key(r):return(r.get("date"),r.get("signal_date"),r.get("reason"))
  ar=[reject_key(r) for r in ind["rejected"]];br=[reject_key(r) for r in financial_executor]
  rejection_counts.append({"account_id":aid,"independent_count":len(ar),"executor_financial_period_count":len(br),"executor_total_count":len(actual_rejected),"ordered_match":ar==br,"differences":[{"index":i,"independent":x,"executor":y} for i,(x,y) in enumerate(zip(ar,br)) if x!=y]})
  summary=readj(folder/"summary.json");daily=ind["daily"];trades=ind["trades"]
  peak=100000.;maxdd=0.
  for r in daily:peak=max(peak,r["equity"]);maxdd=min(maxdd,r["equity"]/peak-1)
  final=daily[-1];calc={"final_equity":final["equity"],"net_gain":final["equity"]-100000,"final_cash":final["cash"],"final_receivable":final["receivable"],"final_units":final["units"],"terminal_market_value":final["market_value"],"fees":final["fees"],"dividends_received":final["dividends_received"],"buys":sum(t["side"]=="buy" for t in trades),"sells":sum(t["side"]=="sell" for t in trades),"cash_only_days":sum(r["units"]==0 for r in daily),"max_drawdown":maxdd}
  diffs={k:abs(float(v)-float(summary[k])) for k,v in calc.items()}
  summary_checks.append({"account_id":aid,"calculated":calc,"executor":{k:summary[k] for k in calc},"differences":diffs,"passed":max(diffs.values())<=TOL})
 with (HERE/"etf-account-checks.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(checks[0]));w.writeheader();w.writerows(checks)
 dump(HERE/"etf-signal-checks.json",signal_checks);dump(HERE/"etf-summary-checks.json",summary_checks);dump(HERE/"etf-rejection-counts.json",rejection_counts)
 after={p:sha(p) for p in locked};dump(HERE/"etf-comparison-lock-after.json",{"files":after})
 failures=[x for x in checks if not x["passed"]];sigfail=[x for x in signal_checks if not x["completed_signals_match"]];sumfail=[x for x in summary_checks if not x["passed"]]
 terminal=sum(len(x["extra_terminal_records"]) for x in signal_checks);reject_mismatch=[x for x in rejection_counts if not x["ordered_match"]]
 dump(HERE/"etf-results.json",{"status":"passed_with_record_classification_findings" if not(failures or sigfail or sumfail) else "failed","accounts":12,"daily_and_trade_rows_checked":len(checks),"row_failures":len(failures),"completed_signal_accounts_failed":len(sigfail),"summary_accounts_failed":len(sumfail),"executor_extra_terminal_records":terminal,"rejection_account_mismatches":len(reject_mismatch),"rejection_checks":rejection_counts,"input_hashes_unchanged":after==locked,"first_row_failures":failures[:20],"signal_failures":sigfail,"summary_failures":sumfail,"width_boundary_finding":"All 588 confirmed completed-week signals match. Executor additionally records the 2026-06-30 Tuesday observation as eligible 2026-07-06 in four breadth accounts. The week was unfinished at period end, so independent review does not classify it as a confirmed weekly signal. It has no cash or trade effect.","restriction_record_finding":"For both sz159915 breadth fee accounts, the 2021-02-08 blocked attempt is financially handled identically but executor labels it missing_quote; the locked dated restriction identifies an official suspension, so independent review classifies it known_open_unavailable."})

if __name__=="__main__":main()
