"""Build the two frozen weekly candidates; no account or return calculation."""
import json
import sys
from datetime import date,timedelta
from decimal import Decimal as D
from pathlib import Path

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from account_adapter import FIRST12, qualify_weekly_records


def target_text(value):
    return "1" if value==D("1") else "0.5" if value==D("0.5") else "0"


def old_tier(value):
    x=D(str(value))
    return D("1") if x<D("43.3") else D("0.5") if x<D("56.7") else D("0")


def build_h1(weekly,symbols,end,start="2015-01-01"):
    state=D("0");base=[]
    for row in qualify_weekly_records(weekly,end):
        if row["eligible_date"]<start:continue
        x=D(str(row["breadth"]))
        if not row["candidate_only"]:
            if state==0 and x*3<=130:state=D("1")
            elif state==1 and x*3>136:state=D("0")
        base.append(dict(row,target=target_text(state),reason="H1_weekly_binary_hysteresis",
                         entry_compare="3*breadth<=130",exit_compare="3*breadth>136"))
    return [dict(r,symbol=s) for s in symbols for r in base]


def trend_at(day,breakouts,bars,forbidden_marks=()):
    state=D("0");last_switch=None
    for event in breakouts:
        if event["signal_date"]>day:break
        state=D(event["target"]);last_switch=event["signal_date"]
    observed=max(b["date"] for b in bars if b["date"]<=day and b["date"] not in forbidden_marks)
    return state,last_switch,observed


def build_h2(weekly,breakouts,bars_by_symbol,symbols,end,start="2015-01-01"):
    out=[];restrictions=json.loads((FIRST12/"inputs/dated-restrictions.json").read_text())
    forbidden={s:{r["date"] for r in restrictions if r["symbol"]==s and not r["close_mark_allowed"]} for s in symbols}
    for row in qualify_weekly_records(weekly,end):
        if row["eligible_date"]<start:continue
        week_decision=(date.fromisoformat(row["eligible_date"])-timedelta(days=1)).isoformat()
        knowledge_date=min(end,week_decision)
        for symbol in symbols:
            trend,switch,observed=trend_at(knowledge_date,breakouts[symbol],bars_by_symbol[symbol],forbidden[symbol])
            width=old_tier(row["breadth"]);target=max(width,trend)
            out.append(dict(row,symbol=symbol,signal_date=knowledge_date,target=target_text(target),reason="H2_weekly_breadth_trend_participation",
                            decision_date=knowledge_date,breadth_source_date=row["signal_date"],breadth_value=row["breadth"],
                            etf_observation_date=observed,recent_trend_switch_date=switch,
                            breadth_target=target_text(width),trend_target=target_text(trend),combined_target=target_text(target)))
    return out


def main():
    prepared=json.loads((FIRST12/"prepared-signals.json").read_text())
    config=json.loads((FIRST12/"config.json").read_text())
    from account_adapter import load_frozen_inputs
    _,_,_,_,bars=load_frozen_inputs();start,end=config["research_window"]
    raw=[("H1_weekly_binary_hysteresis",build_h1(prepared["weekly_breadth"],config["symbols"],end,start)),
         ("H2_weekly_breadth_trend_participation",build_h2(prepared["weekly_breadth"],prepared["breakout"],bars,config["symbols"],end,start))]
    terminal=[];candidates=[]
    for candidate_id,records in raw:
        terminal += [dict(x,candidate_id=candidate_id) for x in records if x["candidate_only"]]
        candidates.append({"candidate_id":candidate_id,"provenance":"research_proxy","claims_paper_original":False,
                           "execution_policy":"weekly_5pp_target","signals":[x for x in records if not x["candidate_only"]]})
    Path(HERE/"candidates.json").write_text(json.dumps({"candidates":candidates,"terminal_candidates":terminal},ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    print(json.dumps({c["candidate_id"]:len(c["signals"]) for c in candidates},ensure_ascii=False))


if __name__=="__main__":main()
