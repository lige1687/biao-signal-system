"""Run the 48 frozen single-product technical cash accounts."""
from pathlib import Path
from datetime import datetime,timezone
import gzip,hashlib,importlib.util,json,sys
import pandas as pd
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;INPUT=HERE/"inputs"
def read(p):return json.loads(p.read_text())
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def structure_only(position,observations,close):return None
def load_data():
    cfg=read(INPUT/"execution-config.json");prices={}
    for symbol in cfg["symbols"]:
        rows=pd.read_csv(INPUT/f"bars/{symbol}-nominal.csv").to_dict("records")
        prices[symbol]={r["date"]:{k:r[k] for k in ("open","high","low","close","volume")} for r in rows}
    actions=[]
    for a in read(INPUT/"actions.json"):
        if a["symbol"] not in cfg["symbols"]:continue
        x=dict(a,ex_date=a["effective_date"])
        if a["type"]=="cash_dividend":x["cash_per_share"]=float(a["cash"])
        else:x["ratio"]=float(a["ratio"])
        actions.append(x)
    with gzip.open(INPUT/"exit-observations.json.gz","rt") as f:obs=json.load(f)
    with gzip.open(INPUT/"source-candidates/precision-candidates.json.gz","rt") as f:precision=json.load(f)
    diagnostic=read(INPUT/"source-candidates/diagnostic-candidates.json")
    return cfg,prices,actions,obs,precision,diagnostic
def main():
    out=HERE/"account-results";assert not out.exists(),"preserve prior run";out.mkdir()
    protocol_lock=read(ROOT/"protocol-lock.json");assert sha(ROOT/"protocol.md")==protocol_lock["sha256"]
    source_lock=read(HERE/"source-lock.json")
    for p,h in source_lock["files"].items():assert sha(Path(p))==h,p
    cfg,prices,actions,obs,precision,diagnostic=load_data()
    assert "2021-02-08" not in prices["sz159915"]
    acd=set(cfg["acd_methods"]);diagnostics=set(cfg["diagnostic_methods"])
    selected=[c for c in precision if c["symbol"] in cfg["symbols"] and c["config_id"] in acd]
    selected += [c for c in diagnostic if c["symbol"] in cfg["symbols"] and c["config_id"] in diagnostics]
    assert len([c for c in selected if c["config_id"] in acd])==379
    assert len([c for c in selected if c["config_id"] in diagnostics])==755
    save(out/"run-lock.json",{"started_at_utc":datetime.now(timezone.utc).isoformat(),"source_lock_sha256":sha(HERE/"source-lock.json"),
        "source_files":source_lock["files"],"protocol_sha256":protocol_lock["sha256"],"accounts":48,"config":cfg})
    save(out/"candidates.json",selected)
    engine=module("technical_frozen_engine",HERE/"engine.py");metrics=module("technical_frozen_metrics",HERE/"metrics.py")
    summaries=[];annual=[]
    for symbol in cfg["symbols"]:
      for method in cfg["methods"]:
       cs=[c for c in selected if c["symbol"]==symbol and c["config_id"]==method]
       for fee in cfg["fees_per_side"]:
        fee_tag=str(int(round(fee*10000))).zfill(2);account_id=f"{symbol}-{method}-fee{fee_tag}bp";folder=out/account_id;folder.mkdir()
        exit_rule=structure_only if method in acd else None
        r=engine.simulate({symbol:prices[symbol]},[a for a in actions if a["symbol"]==symbol],cs,{symbol:obs[symbol]},
            start=cfg["start"],end=cfg["end"],initial_per_symbol=cfg["initial_per_symbol"],weekly_per_symbol=0,
            fee=fee,config_id=method,limits={symbol:cfg["limits"][symbol]},limit_changes={symbol:cfg["limit_changes"][symbol]},
            blocked_dates={symbol:cfg["blocked_dates"][symbol]},exit_rule=exit_rule,explicit_config_set=acd)
        pd.DataFrame(r["daily"]).to_csv(folder/"daily.csv",index=False)
        pd.DataFrame(r["trades"]).to_csv(folder/"trades.csv",index=False)
        for name in ("orders","events","roundtrips"):save(folder/(name+".json"),r[name])
        m=metrics.summarize(r);m.update(account_id=account_id,symbol=symbol,config_id=method,method=method,fee_per_side=fee,
            raw_candidates=len(cs),signal_accepted=sum(bool(c.get("signal_accepted")) for c in cs),
            sizing_policy="full_available_cash" if method in diagnostics else "one_percent_prior_equity",
            exit_policy="ema20_and_cost20_or_structure" if method in diagnostics else "initial_structure_stop_only")
        summaries.append(m)
        df=pd.DataFrame(r["daily"]);df["investment_pnl"]=df.equity.diff().fillna(df.equity.iloc[0]-cfg["initial_per_symbol"])-df.deposit
        assert abs(float(df.investment_pnl.sum())-m["net_gain"])<1e-6
        for year,g in df.groupby(df.date.str[:4]):annual.append(dict(account_id=account_id,symbol=symbol,config_id=method,fee_per_side=fee,year=year,investment_pnl=float(g.investment_pnl.sum()),ending_equity=float(g.equity.iloc[-1]),trade_count=sum(t["date"].startswith(year) for t in r["trades"])))
        for p,h in source_lock["files"].items():assert sha(Path(p))==h,p
        save(out/"progress.json",{"completed":len(summaries),"total":48,"latest":account_id})
        print(account_id,m["last_equity"],m["max_drawdown"],m["buys"],flush=True)
    save(out/"summary.json",summaries);pd.DataFrame(summaries).to_csv(out/"summary.csv",index=False);pd.DataFrame(annual).to_csv(out/"annual.csv",index=False)
    for p,h in source_lock["files"].items():assert sha(Path(p))==h,p
    save(out/"completion.json",{"finished_at_utc":datetime.now(timezone.utc).isoformat(),"accounts_completed":len(summaries),"all_input_hashes_unchanged":True,"source_lock_sha256_after":sha(HERE/"source-lock.json")})
if __name__=="__main__":main()
