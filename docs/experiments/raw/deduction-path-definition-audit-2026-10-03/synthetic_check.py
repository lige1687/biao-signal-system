"""Synthetic definition witnesses only; no market inputs, labels or fitted models."""
from __future__ import annotations
import argparse
from datetime import date, timedelta
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys

PINNED_COMMIT = "d444316817e9330c2d72a4a90c655467b45dd5bb"
EXPECTED = {'src/lei_signal/research/deduction_box_information.py': '3d62f32f3259aabd72bffd3c53c0bd56b6653145d403839cf64790ff55deb677', 'src/lei_signal/research/ema_only_wait_age_information.py': 'a98a6eff6ba15fa210f28e71092dcef79a75d9ff310f055dc712b40f5bd0982e', 'src/lei_signal/research/workflow_inputs.py': '0ff1fe0a3de19680cc9c8800fb62267993cc9f55dab36fbe28a2dd7153ca4691'}

def run(source_root: Path) -> dict:
    for rel, expected in EXPECTED.items():
        assert hashlib.sha256((source_root/rel).read_bytes()).hexdigest() == expected, rel
    sys.path.insert(0, str(source_root/"src"))
    from lei_signal.research.ema_only_wait_age_information import (
        DEFINITION_REF, prepare_sequence_observations, BASELINE_FEATURES,
    )
    q, alpha = F(19,21), F(2,21)
    delta = -20*(q**19-q**10)/q**25
    a = [F(100)]*300
    b = a.copy()
    t = 299
    a[t-19], a[t-10] = F(110), F(90)
    b[t-19], b[t-10] = F(90), F(110)
    for prices in (a,b):
        prices[t-21] = prices[t-22] = F(20)
        prices[t] = F(99)
    a[t-25] += delta
    emas = []
    for prices in (a,b):
        e = prices[0]
        for close in prices[1:]: e = alpha*close+q*e
        emas.append(e)
    assert emas[0] == emas[1] < 99
    observations = []
    for prices in (a,b):
        days = [(date(2022,1,3)+timedelta(days=i)).isoformat() for i in range(300)]
        payload = {"data_mode":"synthetic", "calendar":days,
            "bars":[{"asset":"synthetic-A", "date":day, "status":"quoted",
                "action_known":True,"open":float(c),"high":float(c),
                "low":float(c),"close":float(c)} for day,c in zip(days,prices)]}
        contract = {"feature":{"kind":"ema_only_wait_age_information",
            "definition_ref":DEFINITION_REF,"warmup":252,"missing_policy":"segmented"},
            "target":{"kind":"forward_return","start_offset":1,"end_offset":21,
                "entry_field":"close","price_measure":"economic_price"},
            "question":{"sampling":"daily","period":[days[0],days[-1]]},
            "universe":{"assets":["synthetic-A"]}}
        # Default source path explicitly forbids calculating market/future labels.
        result = prepare_sequence_observations(payload,contract,compute_labels=False)
        assert all(r["y"] is None and r["label_end"] is None for r in result["observations"])
        last = result["observations"][-1]
        assert last["eligible"] and last["E"] and last["S"] is False
        assert last["wait_age"] == 1
        observations.append(last)
    x_a,x_b = (r["features"] for r in observations)
    deltas = {k:abs(x_a[k]-x_b[k]) for k in x_a}
    assert set(x_a)==set(BASELINE_FEATURES)|{"added"}
    assert max(deltas.values()) < 1e-12
    candidate_a = 100*(a[t-10]/a[t-19]-1)
    candidate_b = 100*(b[t-10]/b[t-19]-1)
    assert candidate_a != candidate_b
    # A separate scope check: endpoints plus box top do not describe the path.
    paths = [[104,99,105,103,103,103,103,103,103,102],
             [104,101,105,103,103,103,103,103,103,102]]
    rehearsal = []
    for path in paths:
        history = path+[103]*9+[100] # C[t-19]..C[t], exactly twenty prices
        previous = sum(map(F,history))/20
        up = []
        for k in range(1,11):
            actual = sum(map(F,history[k:]+[100]*k))/20
            assert actual-previous == F(100-path[k-1],20)
            up.append(int(actual>previous));previous=actual
        rehearsal.append({"known_path":path,"first_up_day":next((i+1 for i,v in enumerate(up) if v),None)})
    assert rehearsal[0]["first_up_day"]==2 and rehearsal[1]["first_up_day"] is None
    return {"scope":"synthetic mathematics, not market information value",
        "pinned_source_commit":PINNED_COMMIT,"source_hashes":EXPECTED,
        "baseline_fields":list(x_a),"baseline_A":x_a,"baseline_B":x_b,
        "max_baseline_difference":max(deltas.values()),"tolerance":1e-12,
        "exact_EMA_equal":True,"current_ema":float(emas[0]),"age_A":1,"age_B":1,
        "endpoint_pct_A":float(candidate_a),"endpoint_pct_B":float(candidate_b),
        "same_endpoints_and_box_but_different_rehearsal":rehearsal,
        "rehearsal_identity_checks":20,"model_fits":0,"market_labels":0,"market_requests":0,
        "limitations":["Proves non-reconstructibility from this fixed baseline, not market usefulness.",
            "Endpoint change is exactly the nine-interval price return ending t-10.",
            "Future constant price is an explicit scenario, not a price forecast."]}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source-root",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    r=run(args.source_root.resolve())
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(r,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
    print(json.dumps({"baseline_columns":len(r["baseline_fields"]),
        "max_difference":r["max_baseline_difference"],"candidate_A":r["endpoint_pct_A"],
        "candidate_B":r["endpoint_pct_B"],"fits":0,"market_labels":0}))
