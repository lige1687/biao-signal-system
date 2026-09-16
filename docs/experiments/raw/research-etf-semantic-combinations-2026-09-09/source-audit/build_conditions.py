"""Build point-in-time C1 position/direction conditions. No payoff calculation."""
from __future__ import annotations
from pathlib import Path
import gzip, hashlib, importlib.util, json, math
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
BATCH = HERE.parent
INPUT = ROOT / "docs/experiments/raw/research-broad-etf-technical-2026-09-08/execution/inputs"
PRICE_BASIS = ROOT / "docs/experiments/raw/research-eighth-2026-09-08/product-qualification/price-helper/price_basis.py"
SYMBOLS = ("sh510300", "sz159915")

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def read_json(path: Path): return json.loads(path.read_text())
def write_json(path: Path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n")

def price_basis_class():
    spec=importlib.util.spec_from_file_location("semantic_price_basis",PRICE_BASIS)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.PriceBasis

def raw_asof(symbol: str, bars: dict, actions: list, day: str) -> pd.DataFrame:
    observed={symbol:[r for r in bars[symbol] if r["date"]<=day]}
    known=[a for a in actions if a["symbol"]==symbol and a["announcement_date"]<=day]
    basis=price_basis_class()(observed,known)
    rows=[]
    for row in observed[symbol]:
        converted=basis.bar(symbol,row,day,"cash_proportional_v1")
        rows.append({"date":row["date"],**{k:float(converted[k]) for k in ("open","high","low","close","volume")}})
    return pd.DataFrame(rows).set_index(pd.to_datetime([r["date"] for r in rows]))

def features(frame: pd.DataFrame) -> pd.DataFrame:
    out=frame.copy(); c=out.close.astype(float)
    out["sma20"]=c.rolling(20,min_periods=20).mean()
    values=c.to_list(); ema=[math.nan]*len(values); alpha=2/21
    if len(values)>=20:
        ema[19]=sum(values[:20])/20
        for i in range(20,len(values)): ema[i]=alpha*values[i]+(1-alpha)*ema[i-1]
    out["ema20"]=ema; out["close_lag20"]=c.shift(20)
    pc=c.shift(1); tr=pd.concat([out.high-out.low,(out.high-pc).abs(),(out.low-pc).abs()],axis=1).max(axis=1);tr.iloc[0]=math.nan
    out["atr20"]=tr.rolling(20,min_periods=20).mean()
    return out

def main():
    lock=read_json(HERE/"source-code-lock.json")
    for p,h in lock["files"].items(): assert sha(Path(p))==h,p
    with gzip.open(INPUT/"source-candidates/precision-candidates.json.gz","rt") as f: candidates=json.load(f)
    candidates=[c for c in candidates if c["symbol"] in SYMBOLS and c["config_id"]=="C1"]
    bars={s:pd.read_csv(INPUT/f"bars/{s}-nominal.csv",dtype={"date":str}).to_dict("records") for s in SYMBOLS}
    actions=read_json(INPUT/"actions.json")
    with gzip.open(INPUT/"exit-observations.json.gz","rt") as f: exit_obs=json.load(f)
    rows=[]; tail_checks=0
    for c in candidates:
        s,day=c["symbol"],c["signal_date"]; e=c["source_event"]; ev=e["evidence"]
        f=features(raw_asof(s,bars,actions,day)); r=f.iloc[-1]
        assert abs(float(r.close)-float(c["signal_ref"]))<1e-12
        assert abs(float(r.sma20)-float(exit_obs[s][day]["sma20"]))<1e-12
        dual=bool(r.close>r.ema20 and r.close>r.sma20 and r.ema20>f.ema20.iloc[-2] and r.sma20>f.sma20.iloc[-2] and r.close>r.close_lag20)
        assert dual is bool(ev["dual_ma_bull_state"])
        p=bool(r.close>=r.sma20 and abs(float(ev["l1_price"])-float(r.sma20))<=float(r.atr20))
        q=bool(ev["dual_ma_bull_state"])
        lifecycle_date=e["lifecycle_id"].rsplit(":",1)[-1]
        assert lifecycle_date<=ev["breakdown_date"]<=ev["reclaim_date"]==day==e["available_date"]
        # Future-tail perturbation cannot affect a point-in-time reconstruction.
        altered={k:list(v) for k,v in bars.items()}
        altered[s]=[dict(x,close=float(x["close"])*7,high=max(float(x["high"]),float(x["close"])*7)) if x["date"]>day else x for x in altered[s]]
        f2=features(raw_asof(s,altered,actions,day)); pd.testing.assert_frame_equal(f,f2,check_exact=True);tail_checks+=1
        rows.append({
          "candidate_id":c["candidate_id"],"source_candidate_id":c["source_candidate_id"],"symbol":s,
          "signal_date":day,"known_at":c["known_at"],"lifecycle_id":e["lifecycle_id"],
          "l1_confirmed_available_date":lifecycle_date,"breakdown_date":ev["breakdown_date"],"reclaim_date":ev["reclaim_date"],
          "l1":ev["l1_price"],"l2":ev["l2_price"],"stop":c["stop"],"close":float(r.close),
          "sma20":float(r.sma20),"atr20":float(r.atr20),"ema20":float(r.ema20),"close_lag20":float(r.close_lag20),
          "position_p":p,"direction_q":q,"group_membership":{"G0":True,"GP":p,"GQ":q,"GPQ":p and q},
          "signal_accepted":c["signal_accepted"],"signal_reject_reason":c["signal_reject_reason"],
          "target":c["target"],"target_source":c["target_source"],"target_confirmed_at":c["target_confirmed_at"],
          "basis_as_of":day,"price_basis":"cash_proportional_v1","position_distance_atr":1.0,
          "direction_source":"source_event.evidence.dual_ma_bull_state"
        })
    rows.sort(key=lambda x:(x["signal_date"],x["symbol"],x["candidate_id"]))
    assert len(rows)==84 and len({r["candidate_id"] for r in rows})==84
    summary={g:sum(r["group_membership"][g] for r in rows) for g in ("G0","GP","GQ","GPQ")}
    write_json(HERE/"conditions.json",{"status":"passed","definition":{"P":"close>=SMA20 and abs(L1-SMA20)<=1.0*ATR20 in signal-date cash_proportional_v1 units","Q":"C1 source-event dual_ma_bull_state on the reclaim date"},"counts":summary,"future_tail_checks":tail_checks,"rows":rows})
    for p,h in lock["files"].items(): assert sha(Path(p))==h,p

if __name__=="__main__": main()
