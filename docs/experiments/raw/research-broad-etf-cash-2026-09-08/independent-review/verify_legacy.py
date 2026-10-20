#!/usr/bin/env python3
"""Independent reconstruction of the locked nine-index continuous-share ledgers."""
from __future__ import annotations
import argparse, hashlib, json, math, platform
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4]
PLAN=REPO/"docs/experiments/raw/research-broad-etf-plan-2026-09-08/legacy-baseline"
RUN=HERE.parent/"legacy-reconcile"
INPUTS=PLAN/"inputs"
ASSETS={
 "沪深300":"portfolio_split/sh000300_close.parquet","上证50":"portfolio_split/sh000016_close.parquet",
 "中证白酒":"portfolio_split/sz399997_close.parquet","国证地产":"portfolio_split/sz399393_close.parquet",
 "创业板指":"siphon_detector/cyb_399006_close.parquet","证券公司":"siphon_detector/sec_399975_close.parquet",
 "新能车":"portfolio_split/sz399976_close.parquet","中证医疗":"portfolio_split/sz399989_close.parquet",
 "国证有色":"portfolio_split/sz399395_close.parquet"}
START,END="2015-06-16","2026-08-18";FEE=.001;BAND=.05;TOL=1e-11

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+"\n")

def source_paths():
 paths=[HERE/"review-protocol.md",HERE/"verify_legacy.py",PLAN/"legacy-ab-daily-equity.csv"]
 paths+=sorted(p for p in INPUTS.rglob("*") if p.is_file())
 paths+=[RUN/x for x in ("frozen-protocol.md","daily.csv","trades.csv","summary.json","equity-comparison-daily.csv")]
 return paths

def lock():
 return {str(p.resolve()):sha(p) for p in source_paths()}

def load_prices():
 series={}
 for name,rel in ASSETS.items():
  d=pd.read_parquet(INPUTS/rel)
  s=d["close"].astype(float);s.index=pd.to_datetime(s.index);series[name]=s
 p=pd.DataFrame(series).dropna(how="all")
 return p[(p.index>=START)&(p.index<=END)].dropna()

def breadth_targets(dates):
 raw=json.loads((INPUTS/"breadth_overlay/a_share_breadth_33y_snapshot.json").read_text())
 s=pd.Series({pd.Timestamp(r["date"]):float(r["ma200_pct"]) for r in raw if r.get("ma200_pct") is not None}).sort_index()
 # Calendar week ending Friday, with the final actually observed breadth value retained.
 labels=s.index+pd.to_timedelta(4-np.asarray(s.index.weekday),unit="D")
 weekly=[]
 for label,g in s.groupby(labels):
  weekly.append((g.index[-1],float(g.iloc[-1]),1.0 if g.iloc[-1]<43.3 else .5 if g.iloc[-1]<56.7 else 0.0))
 target=pd.Series(np.nan,index=dates,dtype=float);checks=[]
 for signal_day,value,tier in weekly:
  pos=dates.searchsorted(signal_day)
  if pos<len(dates) and dates[pos]==signal_day: pos+=1
  if pos<len(dates):
   target.iloc[pos]=tier;checks.append({"signal_date":signal_day.date().isoformat(),"breadth":value,"tier":tier,"effective_date":dates[pos].date().isoformat()})
 return target.ffill().fillna(0.0),checks

def reconstruct(prices,tiers,account):
 names=list(prices);shares={n:0. for n in names};cash=1.;fees=0.;daily=[];trades=[]
 for row_no,(ts,pxs) in enumerate(prices.iterrows()):
  values={n:shares[n]*float(pxs[n]) for n in names};pre=cash+sum(values.values())
  if account=="A_true_buy_once_hold": target={n:1/len(names) for n in names};eligible={n:row_no==0 for n in names}
  elif account=="A_5pp_equal_weight_rebalance": target={n:1/len(names) for n in names};eligible={n:abs(target[n]-values[n]/pre)>=BAND for n in names}
  else: target={n:float(tiers.loc[ts])/len(names) for n in names};eligible={n:abs(target[n]-values[n]/pre)>=BAND for n in names}
  target_amt={n:pre*target[n] for n in names}
  sell={n:min(values[n],max(0.,values[n]-target_amt[n])) if eligible[n] else 0. for n in names}
  for n in names:
   gross=sell[n]
   if gross<=1e-12: continue
   qty=gross/float(pxs[n]);cost=gross*FEE;shares[n]-=qty;cash+=gross-cost;fees+=cost
   if abs(shares[n])<1e-12:shares[n]=0.
   trades.append(dict(account=account,date=ts.date().isoformat(),asset=n,side="sell",price=float(pxs[n]),shares=qty,gross_amount=gross,fee=cost,cash_after=cash,target_weight=target[n],pretrade_weight=values[n]/pre,reason="initial_buy" if account=="A_true_buy_once_hold" else "5pp_threshold"))
  after_sell={n:shares[n]*float(pxs[n]) for n in names}
  want={n:max(0.,target_amt[n]-after_sell[n]) if eligible[n] else 0. for n in names};planned=sum(want.values())
  scale=min(1.,cash/(planned*(1+FEE))) if planned>1e-12 else 0.
  for n in names:
   gross=want[n]*scale
   if gross<=1e-12: continue
   qty=gross/float(pxs[n]);cost=gross*FEE;shares[n]+=qty;cash-=gross+cost;fees+=cost
   if abs(cash)<1e-12:cash=0.
   trades.append(dict(account=account,date=ts.date().isoformat(),asset=n,side="buy",price=float(pxs[n]),shares=qty,gross_amount=gross,fee=cost,cash_after=cash,target_weight=target[n],pretrade_weight=values[n]/pre,reason="initial_buy" if account=="A_true_buy_once_hold" else "5pp_threshold"))
  after={n:shares[n]*float(pxs[n]) for n in names};equity=cash+sum(after.values())
  assert cash>=-TOL and min(shares.values())>=-TOL
  for n in names: daily.append(dict(account=account,date=ts.date().isoformat(),asset=n,price=float(pxs[n]),shares=shares[n],asset_value=after[n],cash=cash,equity=equity,pretrade_equity=pre,pretrade_weight=values[n]/pre,target_weight=target[n],posttrade_weight=after[n]/equity,cumulative_fees=fees))
 return pd.DataFrame(daily),pd.DataFrame(trades)

def compare_frames(ind,actual,keys,numeric,label):
 a=actual.copy();b=ind.copy()
 merged=b.merge(a,on=keys,how="outer",suffixes=("_ind","_run"),indicator=True)
 rows=[]
 for _,r in merged.iterrows():
  diffs={};ok=r["_merge"]=="both"
  if ok:
   for c in numeric:
    x,y=float(r[c+"_ind"]),float(r[c+"_run"]);diff=abs(x-y);diffs[c]=diff;ok=ok and diff<=TOL
  rows.append({**{k:r[k] for k in keys},"table":label,"present":r["_merge"],"passed":bool(ok),"max_numeric_difference":max(diffs.values(),default=None)})
 return pd.DataFrame(rows)

def metrics(eq):
 peak=eq.cummax();dd=eq/peak-1;ret=eq.pct_change().dropna();ann=(eq.iloc[-1]**(252/len(eq))-1)*100
 return {"end_equity":float(eq.iloc[-1]),"ann_pct":float(ann),"maxdd_pct":float(dd.min()*100),"daily_stability":float(ret.mean()/ret.std()*np.sqrt(252))}

def main():
 before=json.loads((HERE/"legacy-input-lock-before.json").read_text());assert lock()==before["files"]
 prices=load_prices();tiers,breadth_checks=breadth_targets(prices.index)
 actual_d=pd.read_csv(RUN/"daily.csv");actual_t=pd.read_csv(RUN/"trades.csv")
 all_d=[];all_t=[];account_checks=[]
 for account in ("A_true_buy_once_hold","A_5pp_equal_weight_rebalance","B_breadth_3tier_5pp_rebalance"):
  d,t=reconstruct(prices,tiers,account);all_d.append(d);all_t.append(t)
  dr=compare_frames(d,actual_d[actual_d.account==account],["account","date","asset"],["price","shares","asset_value","cash","equity","pretrade_equity","pretrade_weight","target_weight","posttrade_weight","cumulative_fees"],"daily")
  tr=compare_frames(t,actual_t[actual_t.account==account],["account","date","asset","side"],["price","shares","gross_amount","fee","cash_after","target_weight","pretrade_weight"],"trades")
  account_checks.append({"account":account,"daily_rows":len(d),"trade_rows":len(t),"daily_failures":int((~dr.passed).sum()),"trade_failures":int((~tr.passed).sum()),**metrics(d.groupby("date",sort=False).equity.first())})
  dr.to_csv(HERE/f"{account}-daily-checks.csv",index=False);tr.to_csv(HERE/f"{account}-trade-checks.csv",index=False)
 pd.DataFrame(breadth_checks).to_csv(HERE/"legacy-breadth-week-checks.csv",index=False)
 comparison=pd.read_csv(RUN/"equity-comparison-daily.csv")
 drift={}
 for col in ("A_legacy_minus_corrected_threshold","B_legacy_minus_corrected"):
  s=comparison.set_index("date")[col].astype(float);idx=s.abs().idxmax()
  drift[col]={"ending_difference":float(s.iloc[-1]),"max_absolute_difference":float(s.abs().max()),"max_difference_date":idx,"first_nonzero_date":s[s.abs()>1e-12].index[0]}
 dump(HERE/"legacy-drift-checks.json",{"mechanisms":["旧模型把目标权重直接当成持续权重，真实份额会随价格自然漂移","真实账户只有偏差达到5个百分点才交易","真实账户从现金支付费用，买入总额必须连同费用不超过现金"],"observed":drift})
 summary=read_summary=json.loads((RUN/"summary.json").read_text())["summaries"]
 summary_checks=[]
 for x in account_checks:
  reported=summary[x["account"]]
  summary_checks.append({"account":x["account"],"end_equity_difference":x["end_equity"]-reported["end_equity"],"ann_difference":x["ann_pct"]-reported["ann_pct"],"maxdd_difference":x["maxdd_pct"]-reported["maxdd_pct"],"passed":max(abs(x["end_equity"]-reported["end_equity"]),abs(x["ann_pct"]-reported["ann_pct"]),abs(x["maxdd_pct"]-reported["maxdd_pct"]))<=TOL})
 dump(HERE/"legacy-summary-checks.json",summary_checks)
 after=lock();dump(HERE/"legacy-input-lock-after.json",{"files":after})
 passed=all(x["daily_failures"]==0 and x["trade_failures"]==0 for x in account_checks) and all(x["passed"] for x in summary_checks) and after==before["files"]
 dump(HERE/"legacy-results.json",{"status":"passed" if passed else "failed","window":[START,END],"quote_days":len(prices),"assets":list(prices),"accounts":account_checks,"summary_checks":summary_checks,"input_hashes_unchanged":after==before["files"],"timeline":"review protocol written first; executor result schemas and values were then inspected; this verifier was written and locked before its independent historical calculation. It is not claimed that code was locked before any result inspection.","scope":"continuous-share arithmetic and frozen breadth mapping; index exercise is not ETF evidence","environment":{"python":platform.python_version(),"pandas":pd.__version__,"numpy":np.__version__}})
 if not passed: raise SystemExit(1)

if __name__=="__main__":main()
