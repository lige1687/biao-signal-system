"""Locked phase-13 comparison: six A accounts under exits S and T, plus fixed 17 paths."""
from bisect import bisect_right
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import csv, gzip, hashlib, importlib.util, json, math, sys
import pandas as pd

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
P13 = HERE.parent
ROOT = P13.parents[3]
P12 = P13.parent / "research-twelfth-2026-09-08"
P8 = P13.parent / "research-eighth-2026-09-08"
ENGINE = P12 / "precision-fix/engine.py"
BASE = P12 / "precision-account-results"
OUTPUT = HERE / "account-results"


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def structure_only(position, observations, close):
    return None


def ema_cost_exit(position, observations, close):
    ema, cost = observations.get("ema20"), observations.get("cost20")
    if not finite(ema) or not finite(cost):
        raise ValueError("Missing exit observation ema20/cost20")
    if close < ema and close < cost:
        return "ema_cost_exit"
    return None


def load_inputs():
    settings = read(P8 / "product-qualification/execution-parameters.json")
    prices = {}
    for symbol in settings["symbols"]:
        rows = pd.read_csv(Path(settings["prices_directory"]) / f"{symbol}-nominal.csv", dtype={"date": str}).to_dict("records")
        prices[symbol] = {r["date"]: {k: r[k] for k in ("open", "high", "low", "close", "volume")} for r in rows}
    actions = []
    for action in read(settings["actions_file"]):
        item = dict(action, ex_date=action["effective_date"])
        if action["type"] == "cash_dividend": item["cash_per_share"] = float(action["cash"])
        else: item["ratio"] = float(action["ratio"])
        actions.append(item)
    with gzip.open(P12 / "precision-fix/candidates.json.gz", "rt") as fh:
        candidates = [c for c in json.load(fh) if c["config_id"].startswith("A")]
    with gzip.open(P8 / "candidate-study/exit-observations.json.gz", "rt") as fh:
        observations = json.load(fh)
    configs = read(P13 / "configurations.json")
    assert len(candidates) == 504 and len({c["candidate_id"] for c in candidates}) == 504
    assert {c["config_id"] for c in candidates} == {c["id"] for c in configs}
    return settings, prices, actions, candidates, observations, configs


def write_result(folder, result):
    folder.mkdir(parents=True)
    for name in ("daily", "trades"):
        if result[name]: pd.DataFrame(result[name]).to_csv(folder / f"{name}.csv", index=False)
        else: pd.DataFrame(columns=["date","config_id","symbol","side","shares","price","notional","fee","reason","order_id","position_id","candidate_id"]).to_csv(folder / f"{name}.csv", index=False)
    for name in ("orders", "events", "roundtrips"):
        save(folder / f"{name}.json", result[name])


def compare_baseline_bytes(configs):
    rows = []
    for cfg in configs:
        for name in ("daily.csv", "trades.csv", "orders.json", "events.json", "roundtrips.json"):
            actual, expected = OUTPUT / "S" / cfg / name, BASE / cfg / name
            rows.append({"config_id": cfg, "file": name, "actual_sha256": sha(actual),
                         "expected_sha256": sha(expected), "byte_identical": actual.read_bytes() == expected.read_bytes()})
    save(HERE / "baseline-byte-checks.json", rows)
    if not all(r["byte_identical"] for r in rows):
        save(HERE / "FAILED-baseline-mismatch.json", [r for r in rows if not r["byte_identical"]])
        raise RuntimeError("S baseline differs from twelfth precision-fixed tables; T not run")


def accept_independent_observation_check():
    result_path=P13/"independent-review/observation-results.json"
    lock_path=P13/"independent-review/observation-inputs-lock.json"
    result=read(result_path);lock=read(lock_path)
    assert result["status"]=="passed" and result["observations"]==11158 and result["differences"]==0
    for item in lock: assert sha(item["source"])==item["sha256"],item["source"]
    accepted={"source":str(result_path.resolve()),"source_sha256":sha(result_path),"input_lock":str(lock_path.resolve()),"input_lock_sha256":sha(lock_path),"status":"passed","observations":11158,"differences":0,"note":"accepted independent-review result; execution runner did not repeat or claim this recalculation"}
    save(HERE/"accepted-observation-review.json",accepted)
    return [result_path,lock_path]+[Path(item["source"]) for item in lock]


def unavailable(symbol, day, bars, reference, settings):
    if day in settings["blocked_dates"].get(symbol, []): return "known_open_unavailable"
    if day not in bars[symbol]: return "missing_quote"
    limit = settings["limits"][symbol]
    for effective, value in settings["limit_changes"].get(symbol, []):
        if effective <= day: limit = value
    if abs(float(bars[symbol][day]["open"]) - reference) >= reference * limit - .00051:
        return "at_open_limit_conservative"
    return None


def fixed_position_path(base, prices, actions, observations, settings, method):
    symbol, entry, end = base["symbol"], base["entry_date"], "2026-06-30"
    buy = next(t for t in read(BASE / base["config_id"] / "roundtrips.json") if t["position_id"] == base["position_id"])
    entry_trade = next(t for t in pd.read_csv(BASE / base["config_id"] / "trades.csv").to_dict("records") if t["position_id"] == base["position_id"] and t["side"] == "buy")
    shares = float(entry_trade["shares"]); initial_shares = shares
    entry_notional = float(entry_trade["notional"]); buy_fee = float(entry_trade["fee"])
    stop = float(base["initial_stop"]); cash = -(entry_notional + buy_fee); dividends = 0.; sell_fee = 0.; exit_notional = 0.
    pending = None; events = []; exit_date = None; exit_price = None; sold=False; rights={};receivables={}
    previous_dates = [d for d in prices[symbol] if d < entry]
    reference = float(prices[symbol][max(previous_dates)]["close"])
    from datetime import date,timedelta
    current=date.fromisoformat(entry)
    while current<=date.fromisoformat(end):
        day=current.isoformat()
        for action in sorted((a for a in actions if a["symbol"] == symbol and a["ex_date"] == day), key=lambda x:x["event_id"]):
            if action["type"] == "split":
                if day != entry and not sold: shares *= action["ratio"]; stop /= action["ratio"]
                reference /= action["ratio"]
                events.append({"date":day,"kind":"split","event_id":action["event_id"],"shares_after":shares,"stop_after":stop})
            else:
                entitled=rights.get(action["event_id"],0.); amount=entitled*action["cash_per_share"]
                receivables[action["event_id"]]=amount;dividends+=amount
                if day != entry and not sold: stop *= (reference-action["cash_per_share"])/reference
                reference -= action["cash_per_share"]
                events.append({"date":day,"kind":"dividend_receivable","event_id":action["event_id"],"amount":amount,"entitled_shares":entitled,"stop_after":stop})
        for action in (a for a in actions if a["symbol"]==symbol and a["type"]=="cash_dividend" and a["pay_date"]==day):
            amount=receivables.pop(action["event_id"],0.);cash+=amount;events.append({"date":day,"kind":"dividend_paid","event_id":action["event_id"],"amount":amount})
        if pending and not sold and day > pending["signal_date"]:
            block = unavailable(symbol, day, prices, reference, settings)
            pending["attempts"].append({"date":day,"reason":block or "filled"})
            if block is None:
                exit_date=day;exit_price=float(prices[symbol][day]["open"]);exit_notional=shares*exit_price;sell_fee=exit_notional*.001;cash+=exit_notional-sell_fee
                events.append({"date":day,"kind":"sell","reason":pending["reason"],"shares":shares,"price":exit_price,"fee":sell_fee})
                shares=0.;sold=True
        if day in prices[symbol]: reference=float(prices[symbol][day]["close"])
        if not sold and day in prices[symbol] and pending is None:
            close=reference
            reason = "structure_stop" if close < stop else None
            if reason is None and method == "T": reason = ema_cost_exit({}, observations[symbol].get(day,{}), close)
            if reason:
                pending={"signal_date":day,"reason":reason,"attempts":[]}
                events.append({"date":day,"kind":"exit_signal","reason":reason,"close":close,"stop":stop,"observation":deepcopy(observations[symbol].get(day,{}))})
        for action in (a for a in actions if a["symbol"]==symbol and a["type"]=="cash_dividend" and a["record_date"]==day):
            rights[action["event_id"]]=shares if not sold else 0.;events.append({"date":day,"kind":"dividend_recorded","event_id":action["event_id"],"shares":rights[action["event_id"]]})
        current+=timedelta(days=1)
    mark_date = exit_date or max(d for d in prices[symbol] if d <= end)
    mark = 0. if sold else shares*float(prices[symbol][mark_date]["close"])
    pnl = exit_notional + mark + dividends - entry_notional - buy_fee - sell_fee
    return {"config_id":base["config_id"],"position_id":base["position_id"],"candidate_id":base["candidate_id"],"symbol":symbol,"method":method,"entry_date":entry,"entry_price":float(entry_trade["price"]),"initial_shares":initial_shares,"final_shares":shares,"initial_stop":float(base["initial_stop"]),"final_stop":stop,"exit_signal_date":pending["signal_date"] if pending else None,"exit_reason":pending["reason"] if pending else None,"exit_attempts":pending["attempts"] if pending else [],"exit_date":exit_date,"exit_price":exit_price,"entry_notional":entry_notional,"buy_fee":buy_fee,"sell_fee":sell_fee,"dividends":dividends,"exit_notional":exit_notional,"terminal_market_value":mark,"terminal_value_from_entry_cash":cash+mark,"net_pnl":pnl,"baseline_net_pnl":float(base["net_pnl"]),"events":events}


def summarize_and_tables(results, configs, candidates, metrics):
    summaries=[];annual=[];products=[];outcomes=[]
    for method in ("S","T"):
        for config in configs:
            cfg=config["id"];r=results[(method,cfg)];cs=[c for c in candidates if c["config_id"]==cfg]
            m=metrics.summarize(r);m.update(method=method,config_id=cfg,module="A",raw_candidates=len(cs),signal_accepted=sum(c["signal_accepted"] for c in cs),full_strategy_qualified=False);summaries.append(m)
            df=pd.DataFrame(r["daily"]);df["pnl"]=df.equity.diff().fillna(df.equity.iloc[0])-df.deposit
            for yr,g in df.groupby(df.date.str[:4]): annual.append({"method":method,"config_id":cfg,"year":yr,"investment_pnl":float(g.pnl.sum()),"ending_equity":float(g.equity.iloc[-1]),"trade_count":sum(t["date"].startswith(yr) for t in r["trades"])})
            for s in sorted(results[(method,cfg)]["daily"][-1].keys()):
                pass
            final=r["daily"][-1]
            for symbol in sorted(k[7:] for k in final if k.startswith("equity_")):
                products.append({"method":method,"config_id":cfg,"symbol":symbol,"ending_equity":final["equity_"+symbol],"funding":final["funding_"+symbol],"net_gain":final["equity_"+symbol]-final["funding_"+symbol],"fees":final["fees_"+symbol],"buys":sum(t["side"]=="buy" and t["symbol"]==symbol for t in r["trades"]),"sells":sum(t["side"]=="sell" and t["symbol"]==symbol for t in r["trades"]),"open_shares":final["units_"+symbol]})
            ordermap={o["candidate_id"]:o for o in r["orders"] if o["side"]=="buy"}
            for c in cs:
                o=ordermap[c["candidate_id"]];outcomes.append({"method":method,"config_id":cfg,"candidate_id":c["candidate_id"],"symbol":c["symbol"],"signal_date":c["signal_date"],"signal_accepted":c["signal_accepted"],"signal_reject_reason":c["signal_reject_reason"],"status":o["status"],"order_reason":o["reason"],"position_id":o.get("position_id")})
    save(OUTPUT/"summary.json",summaries);pd.DataFrame(summaries).to_csv(OUTPUT/"summary.csv",index=False)
    pd.DataFrame(annual).to_csv(OUTPUT/"annual-contributions.csv",index=False);pd.DataFrame(products).to_csv(OUTPUT/"product-contributions.csv",index=False)
    pd.DataFrame(outcomes).to_csv(OUTPUT/"candidate-outcomes.csv",index=False)
    wide=pd.DataFrame(outcomes).pivot(index=["config_id","candidate_id","symbol","signal_date"],columns="method",values=["status","order_reason","position_id"]).reset_index()
    wide.columns=["_".join(x).strip("_") for x in wide.columns];wide.to_csv(OUTPUT/"candidate-status-comparison.csv",index=False)
    for method in ("S","T"):
        method_summaries=[x for x in summaries if x["method"]==method]
        save(OUTPUT/method/"summary.json",method_summaries)
        pd.DataFrame(method_summaries).to_csv(OUTPUT/method/"summary.csv",index=False)
        method_annual=[x for x in annual if x["method"]==method]
        method_products=[x for x in products if x["method"]==method]
        pd.DataFrame(method_annual).to_csv(OUTPUT/method/"annual-contributions.csv",index=False)
        pd.DataFrame(method_products).to_csv(OUTPUT/method/"product-contributions.csv",index=False)
        save(OUTPUT/method/"candidates.json",candidates)


def main():
    assert not OUTPUT.exists(), "preserve prior attempt"
    OUTPUT.mkdir(parents=True)
    initial=read(P13/"initial-lock.json")
    for path,digest in initial["files"].items(): assert sha(path)==digest, path
    settings,prices,actions,candidates,observations,configs=load_inputs()
    raw_actions=read(P8/"product-qualification/actions.json")
    observation_sources=accept_independent_observation_check()
    sources=[Path(p) for p in initial["files"]] + [Path(__file__),HERE/"test_execution.py",P8/"spark-metrics/metrics.py"]+observation_sources
    lock={"started_at_utc":datetime.now(timezone.utc).isoformat(),"files":{str(p.resolve()):sha(p) for p in sources},"candidate_count":len(candidates),"candidate_ids_sha256":hashlib.sha256("\n".join(c["candidate_id"] for c in candidates).encode()).hexdigest(),"configs":[c["id"] for c in configs],"methods":{"S":"structure only","T":"structure first, otherwise strict close below EMA20 and 20-quote lag"},"start":"2015-01-01","end":"2026-06-30","fee_per_side":.001,"weekly_per_symbol":250,"risk_fraction":.01}
    save(HERE/"run-lock.json",lock)
    engine=module("phase13_engine",ENGINE);metrics=module("phase13_metrics",P8/"spark-metrics/metrics.py")
    results={};explicit={c["id"] for c in configs}
    for config in configs:
        cfg=config["id"];cs=[c for c in candidates if c["config_id"]==cfg]
        r=engine.simulate(prices,actions,cs,observations,start="2015-01-01",end="2026-06-30",weekly_per_symbol=250,fee=.001,config_id=cfg,limits=settings["limits"],limit_changes=settings["limit_changes"],blocked_dates=settings["blocked_dates"],exit_rule=structure_only,explicit_config_set=explicit)
        results[("S",cfg)]=r;write_result(OUTPUT/"S"/cfg,r)
    compare_baseline_bytes([c["id"] for c in configs])
    for config in configs:
        cfg=config["id"];cs=[c for c in candidates if c["config_id"]==cfg]
        r=engine.simulate(prices,actions,cs,observations,start="2015-01-01",end="2026-06-30",weekly_per_symbol=250,fee=.001,config_id=cfg,limits=settings["limits"],limit_changes=settings["limit_changes"],blocked_dates=settings["blocked_dates"],exit_rule=ema_cost_exit,explicit_config_set=explicit)
        results[("T",cfg)]=r;write_result(OUTPUT/"T"/cfg,r)
    summarize_and_tables(results,configs,candidates,metrics)
    baseline=[]
    for cfg in [c["id"] for c in configs]: baseline += read(BASE/cfg/"roundtrips.json")
    assert len(baseline)==17
    paths=[fixed_position_path(rt,prices,actions,observations,settings,m) for rt in baseline for m in ("S","T")]
    save(HERE/"fixed-17-paths.json",paths)
    comparison=[]
    for i in range(0,len(paths),2):
        s,t=paths[i:i+2]
        assert abs(s["net_pnl"]-s["baseline_net_pnl"])<1e-8,(s["position_id"],s["net_pnl"],s["baseline_net_pnl"])
        comparison.append({k:s[k] for k in ("config_id","position_id","candidate_id","symbol","entry_date","initial_shares")} | {"S_exit_signal_date":s["exit_signal_date"],"S_exit_date":s["exit_date"],"S_exit_reason":s["exit_reason"],"S_net_pnl":s["net_pnl"],"T_exit_signal_date":t["exit_signal_date"],"T_exit_date":t["exit_date"],"T_exit_reason":t["exit_reason"],"T_net_pnl":t["net_pnl"],"T_minus_S":t["net_pnl"]-s["net_pnl"]})
    pd.DataFrame(comparison).to_csv(HERE/"fixed-17-comparison.csv",index=False);save(HERE/"fixed-17-reconciliation.json",{"positions":17,"all_S_net_pnl_matched":True,"max_abs_difference":max(abs(p["net_pnl"]-p["baseline_net_pnl"]) for p in paths if p["method"]=="S")})
    for path,digest in lock["files"].items(): assert sha(path)==digest,path
    save(HERE/"completion.json",{"finished_at_utc":datetime.now(timezone.utc).isoformat(),"accounts_completed":12,"fixed_positions_completed":17,"baseline_tables_byte_identical":True,"observation_rows_independently_matched":11158,"observation_check_source":"independent-review/observation-results.json","all_input_hashes_unchanged":True,"full_strategy_qualified":False})


if __name__ == "__main__": main()
