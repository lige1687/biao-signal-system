"""Compare every returned table on one real frozen default-funding path."""
import gzip,importlib.util,json,sys
from pathlib import Path
import pandas as pd
HERE=Path(__file__).resolve().parent;RAW=HERE.parent.parent
def mod(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def structure_only(position,observations,close):return None
old=mod("real_old",RAW/"research-twelfth-2026-09-08/precision-fix/engine.py")
new=mod("real_new",HERE/"engine.py")
rows=pd.read_csv(HERE/"inputs/bars/sh510300-nominal.csv").to_dict("records")
prices={"sh510300":{r["date"]:{k:r[k] for k in ("open","high","low","close","volume")} for r in rows}}
actions=[]
for a in json.load(open(HERE/"inputs/actions.json")):
 if a["symbol"]!="sh510300":continue
 x=dict(a,ex_date=a["effective_date"])
 if a["type"]=="cash_dividend":x["cash_per_share"]=float(a["cash"])
 else:x["ratio"]=float(a["ratio"])
 actions.append(x)
with gzip.open(HERE/"inputs/source-candidates/precision-candidates.json.gz","rt") as f:
 candidates=[c for c in json.load(f) if c["symbol"]=="sh510300" and c["config_id"]=="A20E"]
kwargs=dict(start="2015-01-01",end="2026-06-30",weekly_per_symbol=250,fee=.001,config_id="A20E",
 limits={"sh510300":.1},limit_changes={"sh510300":[]},blocked_dates={"sh510300":[]},
 exit_rule=structure_only,explicit_config_set={"A20E"})
a=old.simulate(prices,actions,candidates,{},**kwargs);b=new.simulate(prices,actions,candidates,{},**kwargs)
checks={k:a[k]==b[k] for k in ("daily","trades","orders","events","roundtrips")}
assert all(checks.values()),checks
print(json.dumps({"path":"sh510300-A20E-default-weekly-250","all_tables_exact":True,"tables":checks},indent=2))
