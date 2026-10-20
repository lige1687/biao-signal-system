"""Protocol-gated runner. It intentionally cannot run before root freezes candidate rules."""
import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime,timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from account_adapter import FIRST12, execute_candidate_account, load_frozen_inputs, load_json, validate_candidate_bundle
OUT=HERE/"account-results"


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+"\n")


def write_csv(path,rows):
    fields=list(rows[0]) if rows else ["account_id"]
    with path.open("w",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=fields);w.writeheader();w.writerows(rows)


def rolling36(monthly):
    out=[]
    for i in range(35,len(monthly)):
        first,last=monthly[i-35],monthly[i]
        start,end=first["start_equity"],last["end_equity"]
        out.append({"start_month":first["period"],"end_month":last["period"],"start_equity":start,
                    "end_equity":end,"change":end-start,"return":end/start-1})
    return out


def split_periods(daily):
    result=[]
    for label,start,end,initial in [("2015-2019","2015-01-01","2019-12-31",100000.0),
                                    ("2020-2026H1","2020-01-01","2026-06-30",None)]:
        rows=[r for r in daily if start<=r["date"]<=end]
        if initial is None:
            prior=[r for r in daily if r["date"]<start];initial=prior[-1]["equity"]
        high=initial;worst=0.0
        for row in rows:high=max(high,row["equity"]);worst=min(worst,row["equity"]/high-1)
        result.append({"period":label,"start_equity":initial,"end_equity":rows[-1]["equity"],
                       "change":rows[-1]["equity"]-initial,"return":rows[-1]["equity"]/initial-1,
                       "max_drawdown":worst,"average_invested_weight":sum(r["invested_weight"] for r in rows)/len(rows),
                       "cash_only_days":sum(r["units"]==0 for r in rows)})
    return result


def preflight(protocol_path, candidates_path):
    gate = load_json(protocol_path)
    if gate.get("status") != "locked" or gate.get("main_run_authorized") is not True:
        raise RuntimeError("new-return run blocked: final root protocol is not locked")
    bundle = load_json(candidates_path)
    protocol=ROOT/gate["protocol_path"]
    if sha(protocol)!=gate["protocol_sha256"]:raise RuntimeError("root protocol hash mismatch")
    candidates = validate_candidate_bundle(bundle, gate)
    account_count = len(candidates) * len(gate["symbols"]) * len(gate["fees_per_side"])
    if account_count > gate["new_account_count_max"]:
        raise RuntimeError("new account cap exceeded")
    return gate, bundle, account_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=HERE/"protocol-gate.json")
    parser.add_argument("--candidates", type=Path, default=HERE/"candidates.json")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    gate, bundle, count = preflight(args.protocol, args.candidates)
    if args.preflight_only:
        print(json.dumps({"status":"ready","candidates":len(bundle["candidates"]),"accounts":count}, ensure_ascii=False))
        return
    if OUT.exists():raise RuntimeError("preserve prior account-results attempt")
    OUT.mkdir();frozen=load_frozen_inputs()
    dependencies=[Path(__file__),HERE/"account_adapter.py",HERE/"prepare_signals.py",HERE/"protocol-gate.json",args.candidates,
                  ROOT/gate["protocol_path"],ROOT/"docs/experiments/raw/research-broad-etf-multimethod-2026-09-08/protocol-lock.json",
                  FIRST12/"run_accounts.py",FIRST12/"config.json",FIRST12/"source-lock.json",FIRST12/"prepared-signals.json",
                  FIRST12/"inputs/actions.json",FIRST12/"inputs/execution-parameters-source.json",FIRST12/"inputs/dated-restrictions.json"]
    dependencies += [FIRST12/"inputs/bars"/f"{s}-nominal.csv" for s in gate["symbols"]]
    runlock={"started_at_utc":datetime.now(timezone.utc).isoformat(),"inputs":{str(p.resolve()):sha(p) for p in dependencies},
             "candidate_ids":[c["candidate_id"] for c in bundle["candidates"]],"account_count":count}
    save(OUT/"run-lock.json",runlock);summaries=[]
    for candidate in bundle["candidates"]:
      for symbol in gate["symbols"]:
       for fee in gate["fees_per_side"]:
        result=execute_candidate_account(candidate,symbol,fee,frozen)
        result["summary"]["method"]=candidate["candidate_id"]
        result["summary"]["cash_execution_policy"]=candidate["execution_policy"]
        result["summary"]["average_invested_weight"]=sum(r["invested_weight"] for r in result["daily"])/len(result["daily"])
        folder=OUT/result["summary"]["account_id"];folder.mkdir()
        for name in ("daily","trades","monthly","yearly","drawdown_recovery"):write_csv(folder/f"{name}.csv",result[name])
        for name in ("signals","rejected","summary"):save(folder/f"{name}.json",result[name])
        write_csv(folder/"rolling-36-month.csv",rolling36(result["monthly"]))
        write_csv(folder/"fixed-periods.csv",split_periods(result["daily"]))
        summaries.append(result["summary"])
    save(OUT/"summary.json",summaries)
    for path,digest in runlock["inputs"].items():
        if sha(path)!=digest:raise RuntimeError(f"input changed during run: {path}")
    save(OUT/"completion.json",{"finished_at_utc":datetime.now(timezone.utc).isoformat(),"accounts":len(summaries),
         "input_hashes_unchanged":True,"candidate_ids":runlock["candidate_ids"]})


if __name__ == "__main__":
    main()
