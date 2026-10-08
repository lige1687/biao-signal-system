import shutil,json,csv,datetime
from pathlib import Path
from decimal import Decimal
from collections import defaultdict
print("DISK",shutil.disk_usage("."))
for x in ["fixed-ledger-cash-requirement-2026-10-08","sse-calendar-2026-h1-equivalence-2026-10-08"]:
 p=Path("docs/experiments/raw")/x
 print("FILES",x,[(f.name,f.stat().st_size) for f in p.iterdir() if f.is_file()])
P=Path("docs/experiments/raw/fixed-ledger-cash-requirement-2026-10-08");S=Path("docs/experiments/raw/factor-module-a-continuation-2026-09-27")
r=json.loads((P/"result.json").read_text());A=json.loads((S/"accounts.json").read_text());proof={}
def M(x):
 d=Decimal(x)*1000000
 assert d==int(d)
 return int(d)
for pol in ["A_ALL","A_SMA"]:
 totals=defaultdict(int);buys=defaultdict(int);paid=defaultdict(int)
 for a in [a for a in A if a["policy_id"]==pol and a["fee_scenario_id"]=="base"]:
  rows=list(csv.DictReader((S/a["daily_path"]).open()));dates=[x["date"] for x in rows]
  for x in rows:totals[x["date"]]+=M(x["cash"])
  l=json.loads((S/a["ledger_path"]).read_text())
  for f in l["fills"]:
   if Decimal(f["units_delta"])>0:buys[f["date"]]+=M(Decimal(f["units_delta"])*Decimal(f["price"])+Decimal(f["fee"]))
  for x in l["action_ledger"]:
   if x["type"]=="payment_day_end":paid[x["date"]]+=M(x["amount"])
 initial=600000*1000000;previous=initial;candidates={"buy_first":[],"sell_first":[]}
 for date in dates:
  sales=totals[date]-previous+buys[date]-paid[date];assert sales>=0
  candidates["buy_first"].append((previous-buys[date],date));candidates["sell_first"].append((min(previous,totals[date]-paid[date]),date));previous=totals[date]
 proof[pol]={}
 for scenario,values in candidates.items():
  minimum,date=min(values);req=max(0,initial-minimum);assert req==M(r["policies"][pol]["scenarios"][scenario]["minimum_initial_cash_exact"])
  proof[pol][scenario]={"required_micro_cny":req,"binding_date":date,"matches":True}
print("INDEPENDENT_CASH_CHECK",json.dumps(proof))
c=json.loads(Path("docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json").read_text())["days"]
closed=["01-01","01-02","02-16","02-17","02-18","02-19","02-20","02-23","04-06","05-01","05-04","05-05","06-19"]
actual={d for d,v in c.items() if "2026-01-01"<=d<="2026-06-30" and datetime.date.fromisoformat(d).weekday()<5 and not v["is_trading_day"]}
assert actual=={"2026-"+d for d in closed}
months={str(m):sum(v["is_trading_day"] for d,v in c.items() if d.startswith(f"2026-{m:02}")) for m in range(1,7)}
assert sum(months.values())==116
print("INDEPENDENT_CALENDAR_CHECK",json.dumps({"weekday_closed":sorted(actual),"monthly_open":months,"status":"passed"}))

cash_receipt={"status":"passed","method":"Independent prior-day saved cash and current purchase/payment amounts in integer micro-CNY; no cumulative-replay output used.","results":proof,"external_reviewer":False}
(P/"independent-check.json").write_text(json.dumps(cash_receipt,ensure_ascii=False,indent=2)+"\n")
cal_receipt={"status":"passed","method":"Exact set of independently transcribed13 weekday closures and monthly counts; no result-file used.","weekday_closed":sorted(actual),"monthly_open_days":months,"open_days":116,"external_reviewer":False}
(Path("docs/experiments/raw/sse-calendar-2026-h1-equivalence-2026-10-08")/"independent-check.json").write_text(json.dumps(cal_receipt,ensure_ascii=False,indent=2)+"\n")
