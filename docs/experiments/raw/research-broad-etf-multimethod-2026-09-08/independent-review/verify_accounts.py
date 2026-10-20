#!/usr/bin/env python3
"""Independent H1/H2 ETF signal and cash reconstruction; no executor imports."""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from collections import defaultdict
from datetime import date,timedelta
from decimal import Decimal,ROUND_FLOOR,getcontext
from pathlib import Path
getcontext().prec=40;D=Decimal
HERE=Path(__file__).resolve().parent;BATCH=HERE.parent
FIRST=BATCH.parent/"research-broad-etf-cash-2026-09-08"/"first12";INP=FIRST/"inputs";OUT=BATCH/"execution"/"account-results"
START,END="2015-01-01","2026-06-30";SYMS=("sh510300","sz159915");METHODS=("H1_weekly_binary_hysteresis","H2_weekly_breadth_trend_participation");FEES=(D(".001"),D(".002"));TOL=1e-7

def readj(p):return json.loads(Path(p).read_text())
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def readbars(s):
 with (INP/"bars"/f"{s}-nominal.csv").open() as f: return [dict(r,**{k:D(r[k]) for k in ("open","high","low","close","volume")}) for r in csv.DictReader(f)]
def week(d):q=date.fromisoformat(d).isocalendar();return(q.year,q.week)
def monday_after(d):q=date.fromisoformat(d);return(q+timedelta(days=7-q.weekday())).isoformat()
def tier(x):x=D(str(x));return D(1) if x<D("43.3") else D(".5") if x<D("56.7") else D(0)

def weekly_rows():
 rows=[r for r in readj(INP/"a_share_breadth_33y_snapshot.json") if r.get("ma200_pct") is not None and r["date"]<=END]
 by={};
 for r in rows:by[week(r["date"])]=r
 out=[]
 for r in sorted(by.values(),key=lambda x:x["date"]):
  eligible=monday_after(r["date"])
  decision=(date.fromisoformat(eligible)-timedelta(days=1)).isoformat()
  if eligible>=START:out.append({"breadth_source_date":r["date"],"decision_date":decision,"eligible_date":eligible,"source_week":list(week(r["date"])),"breadth":D(str(r["ma200_pct"])),"candidate_only":decision>END})
 return out

def h1_signals(rows,symbol):
 state=D(0);out=[];terminal=[]
 for r in rows:
  x=r["breadth"]
  if not r["candidate_only"]:
   if state==0 and x*3<=130:state=D(1)
   elif state==1 and x*3>136:state=D(0)
  rec={"symbol":symbol,"signal_date":r["decision_date"],"decision_date":r["decision_date"],"breadth_source_date":r["breadth_source_date"],"eligible_date":r["eligible_date"],"source_week":r["source_week"],"breadth":float(x),"target":str(state),"reason":"H1_weekly_binary_hysteresis","candidate_only":r["candidate_only"]}
  (terminal if r["candidate_only"] else out).append(rec)
 return out,terminal

def h2_signals(rows,symbol,breakouts,bars,restrictions):
 invalid={r["date"] for r in restrictions if r["symbol"]==symbol and not r["close_mark_allowed"]};out=[];terminal=[]
 for r in rows:
  decision=min(END,r["decision_date"]);state=D(0);switch=None
  for event in breakouts:
   if event["signal_date"]>decision:break
   state=D(event["target"]);switch=event["signal_date"]
  observed=max(b["date"] for b in bars if b["date"]<=decision and b["date"] not in invalid)
  width=tier(r["breadth"]);target=max(width,state)
  rec={"symbol":symbol,"signal_date":decision,"decision_date":decision,"breadth_source_date":r["breadth_source_date"],"eligible_date":r["eligible_date"],"source_week":r["source_week"],"breadth":float(r["breadth"]),"breadth_value":float(r["breadth"]),"breadth_target":str(width),"trend_target":str(state),"combined_target":str(target),"target":str(target),"recent_trend_switch_date":switch,"etf_observation_date":observed,"reason":"H2_weekly_breadth_trend_participation","candidate_only":r["candidate_only"]}
  (terminal if r["candidate_only"] else out).append(rec)
 return out,terminal

def factor_for(symbol,source_day,asof,actions):
 factor=D(1)
 for a in sorted(actions,key=lambda x:(x["effective_date"],x["event_id"])):
  if a["symbol"]!=symbol or not(source_day<a["effective_date"]<=asof) or a["announcement_date"]>asof:continue
  if a["type"]=="split":factor/=D(a["ratio"])
  else:
   close=a["_prior_close"];factor*=((close-D(a["cash"]))/close)
 return factor

def breakout_signals(symbol,bars,actions,restrictions):
 invalid={r["date"] for r in restrictions if r["symbol"]==symbol and not r["close_mark_allowed"]}
 usable=[b for b in bars if b["date"] not in invalid];state=0;out=[];bydate={b["date"]:b for b in usable};dates=sorted(bydate)
 local=[]
 for original in actions:
  a=dict(original)
  if a["symbol"]==symbol and a["type"]=="cash_dividend":a["_prior_close"]=bydate[max(d for d in dates if d<a["effective_date"])]["close"]
  local.append(a)
 for i,b in enumerate(usable):
  if i<60 or not START<=b["date"]<=END:continue
  hist=[x["close"]*factor_for(symbol,x["date"],b["date"],local) for x in usable[i-60:i]]
  target=None;reason=None
  if state==0 and b["close"]>max(hist):target,reason=1,"close_above_prior_60_high"
  elif state==1 and b["close"]<min(hist):target,reason=0,"close_below_prior_60_low"
  if target is not None:
   out.append({"symbol":symbol,"signal_date":b["date"],"eligible_date":(date.fromisoformat(b["date"])+timedelta(days=1)).isoformat(),"target":str(target),"reason":reason,"current_close":str(b["close"]),"prior_60_min":str(min(hist)),"prior_60_max":str(max(hist))});state=target
 return out

def block_reason(symbol,day,bar,reference,settings,restrictions,actions):
 r=next((x for x in restrictions if x["symbol"]==symbol and x["date"]==day),None)
 if r and not(r["open_buy_allowed"] and r["open_sell_allowed"]):return "known_open_unavailable"
 if bar is None:return "missing_quote"
 if reference is None:return None
 ref=reference
 for a in actions:
  if a["symbol"]==symbol and a["effective_date"]==day:
   ref=ref-D(a["cash"]) if a["type"]=="cash_dividend" else ref/D(a["ratio"])
 limit=D(str(settings["limits"][symbol]));
 for d,x in settings["limit_changes"].get(symbol,[]):
  if d<=day:limit=D(str(x))
 return "at_open_limit_conservative" if abs(bar["open"]-ref)>=ref*limit-D(".00051") else None

def lot(x):return (x/D(100)).to_integral_value(rounding=ROUND_FLOOR)*D(100)
def simulate(account,symbol,method,fee,bars,actions,settings,restrictions,signals):
 bm={b["date"]:b for b in bars};cash=D(100000);recv=D(0);units=D(0);rights={};dues={};pending=None;fees=D(0);divpaid=D(0);reference=next(b["close"] for b in reversed(bars) if b["date"]<START);last=reference;lastdate=max(b["date"] for b in bars if b["date"]<START);trades=[];sout=[dict(s) for s in signals];reject=[];daily=[]
 incoming=defaultdict(list)
 for s in signals:incoming[s["eligible_date"]].append(s)
 if method=="hold":
  hs={"symbol":symbol,"signal_date":START,"eligible_date":min(d for d in bm if d>=START),"target":"1","reason":"initial_hold_allocation"};incoming[hs["eligible_date"]].append(hs);sout=[dict(hs)]
 cur=date.fromisoformat(START);finish=date.fromisoformat(END)
 while cur<=finish:
  day=cur.isoformat();bar=bm.get(day)
  for a in actions:
   if a["symbol"]==symbol and a["effective_date"]==day:
    if a["type"]=="split":units*=D(a["ratio"]);reference/=D(a["ratio"])
    else:dues[a["event_id"]]=rights.get(a["event_id"],D(0))*D(a["cash"]);recv+=dues[a["event_id"]];reference-=D(a["cash"])
  for a in actions:
   if a["symbol"]==symbol and a["type"]=="cash_dividend" and a.get("pay_date")==day:
    amt=dues.pop(a["event_id"],D(0));recv-=amt;cash+=amt;divpaid+=amt
  if method in METHODS and pending and week(day)!=tuple(pending["execution_week"]):reject.append({"date":day,"signal_date":pending["signal_date"],"reason":"stale_weekly_order_cancelled"});pending=None
  for s in incoming.get(day,[]):
   if pending:reject.append({"date":day,"signal_date":pending["signal_date"],"reason":"replaced_by_latest_completed_week"})
   pending=dict(s)
   if method in METHODS:pending["execution_week"]=list(week(day))
  if pending:
   why=block_reason(symbol,day,bar,reference,settings,restrictions,actions)
   if why:reject.append({"date":day,"signal_date":pending["signal_date"],"reason":why})
   else:
    px=bar["open"];eqopen=cash+recv+units*px;actual=units*px/eqopen if eqopen else D(0);target=D(pending["target"])
    reason=None;trade=None
    if method in METHODS and abs(target-actual)<D(".05"):reason="inside_5pp_band"
    elif target*eqopen>units*px:
     qty=min(lot((target*eqopen-units*px)/px),lot(cash/(px*(1+fee))))
     if qty<=0:reason="buy_rounds_to_zero_or_cash_short"
     else:trade=("buy",qty,qty*px,qty*px*fee);cash-=trade[2]+trade[3];units+=qty
    else:
     qty=units if target==0 else min(units,lot((units*px-target*eqopen)/px))
     if qty<=0:reason="sell_rounds_to_zero"
     else:trade=("sell",qty,qty*px,qty*px*fee);cash+=trade[2]-trade[3];units-=qty
    if reason:reject.append({"date":day,"signal_date":pending["signal_date"],"reason":reason,"actual_open_weight":float(actual),"target":float(target)});pending=None
    elif trade:
     side,qty,notional,cost=trade;fees+=cost;trades.append({"account_id":account,"date":day,"signal_date":pending["signal_date"],"side":side,"shares":float(qty),"price":float(px),"notional":float(notional),"fee":float(cost),"reason":pending["reason"],"target":float(target),"equity_open_before_fee":float(eqopen),"actual_open_weight_before":float(actual),"cash_after":float(cash),"units_after":float(units)});pending=None
  invalid_mark=any(r["symbol"]==symbol and r["date"]==day and not r["close_mark_allowed"] for r in restrictions)
  if bar is not None and not invalid_mark:last=bar["close"];lastdate=day;reference=bar["close"]
  for a in actions:
   if a["symbol"]==symbol and a["type"]=="cash_dividend" and a.get("record_date")==day:rights[a["event_id"]]=units
  eq=cash+recv+units*last;daily.append({"account_id":account,"date":day,"cash":float(cash),"receivable":float(recv),"units":float(units),"mark":float(last),"market_value":float(units*last),"equity":float(eq),"invested_weight":float(units*last/eq) if eq else 0.,"fees":float(fees),"dividends_received":float(divpaid),"mark_age_days":(date.fromisoformat(day)-date.fromisoformat(lastdate)).days})
  assert cash>=0 and recv>=0 and units>=0;cur+=timedelta(days=1)
 if pending is not None:reject.append({"date":END,"signal_date":pending["signal_date"],"reason":"pending_at_period_end"})
 for s in signals:
  if s["eligible_date"]>END:reject.append({"date":END,"signal_date":s["signal_date"],"reason":"signal_awaiting_next_open_after_period_end"})
 return {"daily":daily,"trades":trades,"signals":sout,"rejected":reject}

def input_paths():return [HERE/"review-protocol.md",HERE/"verify_accounts.py",BATCH/"protocol.md",BATCH/"protocol-lock.json",FIRST/"protocol.md",FIRST/"config.json",INP/"a_share_breadth_33y_snapshot.json",INP/"actions.json",INP/"dated-restrictions.json",INP/"execution-parameters-source.json"]+[INP/"bars"/f"{s}-nominal.csv" for s in SYMS]
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--prepare",action="store_true");ap.add_argument("--verify",action="store_true");a=ap.parse_args()
 bars={s:readbars(s) for s in SYMS};actions=readj(INP/"actions.json");restr=readj(INP/"dated-restrictions.json");settings=readj(INP/"execution-parameters-source.json")
 rows=weekly_rows();breakouts={s:breakout_signals(s,bars[s],actions,restr) for s in SYMS};signals={};terminal=[]
 for s in SYMS:
  signals[(s,METHODS[0])],t=h1_signals(rows,s);terminal+=t
  signals[(s,METHODS[1])],t=h2_signals(rows,s,breakouts[s],bars[s],restr);terminal+=t
 if a.prepare:
  dump(HERE/"independent-signals.json",{"signals":{f"{s}-{m}":v for (s,m),v in signals.items()},"terminal_candidates":terminal,"breakout":breakouts,"counts":{f"{s}-{m}":len(v) for (s,m),v in signals.items()}});return
 if not a.verify:raise SystemExit("choose --prepare or --verify")
 locked=readj(HERE/"input-lock-before.json")["files"];assert {str(p.resolve()):sha(p) for p in input_paths()}==locked
 if not OUT.exists():raise SystemExit("executor results not ready")
 # Result comparison is intentionally deferred until account-results exists and root authorizes it.
 results={}
 for s in SYMS:
  for method in METHODS:
   source=signals[(s,method)]
   for fee in FEES:
    aid=f"{s}-{method}-fee{fee}";results[aid]=simulate(aid,s,method,fee,bars[s],actions,settings,restr,source)
 dump(HERE/"etf-independent-accounts.json",results)

if __name__=="__main__":main()
