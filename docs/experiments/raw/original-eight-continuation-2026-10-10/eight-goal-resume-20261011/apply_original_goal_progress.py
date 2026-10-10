"""Apply only root-frozen original-goal progress and verify actual API state."""
import datetime,hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
RAW=Path(__file__).parent
OP=urllib.request.build_opener(urllib.request.ProxyHandler({}))
URL="http://127.0.0.1:8000/api/upgrades"
def sha(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def goals():
    with OP.open(URL,timeout=30) as r:return {g["id"]:g for g in json.load(r)["items"]}
def semantic(g):return {k:v for k,v in g.items() if k!="history"}
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n")
def main():
    plan=json.loads((RAW/"goal-progress-plan.json").read_text())
    assert plan["root_evidence_accepted"] is True
    assert plan["independent_data_audit_accepted"] is True
    records=[]
    for i,step in enumerate(plan["steps"]):
        key=step["goal_id"]
        assert key in {"K-data-boundary","K-risk-attribution"}
        before=goals()[key];payload=dict(step["payload"]);payload["version"]=before["version"]
        target=step["target_fields"]
        if before.get("status") in step.get("skip_if_status_in",[]) or all(before[k]==v for k,v in target.items()):
            records.append({"step":i,"goal_id":key,"reused_already_applied_state":True,"version":before["version"]});continue
        if step["method"]=="PATCH":
            assert set(payload)<={"version","milestones","evidence","links","next_action"}
            assert [(x["id"],x["title"]) for x in payload["milestones"]]==[(x["id"],x["title"]) for x in before["milestones"]]
        else:
            assert payload["action"] in {"start","submit_review"}
        intent={"step":i,"goal_id":key,"before":semantic(before),"before_history_sha256":sha(before["history"]),"payload":payload,"target_fields":target}
        save(RAW/("goal-progress-write-intent-"+str(i)+".json"),intent)
        endpoint=URL+"/"+key+("/actions" if step["method"]=="POST" else "")
        req=urllib.request.Request(endpoint,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"},method=step["method"])
        error=None
        try:
            with OP.open(req,timeout=30) as r:json.load(r)
        except Exception as e:error=type(e).__name__+": "+str(e)
        after=goals()[key]
        reached=all(after[k]==v for k,v in target.items())
        allowed=set(target)|{"version","updated_at","history","progress"}
        changed={k for k in before if before[k]!=after[k]}
        record={"step":i,"goal_id":key,"version_before":before["version"],"version_after":after["version"],"status":after["status"],"progress":after.get("progress"),"actual_target_readback":reached,"changed_fields":sorted(changed),"protected_fields_preserved":changed<=allowed,"history_prefix_preserved":after["history"][:len(before["history"])]==before["history"],"response_error":error}
        records.append(record);save(RAW/"goal-progress-readback.json",{"at":datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),"records":records})
        assert reached,record
        assert changed<=allowed,record
        assert after["history"][:len(before["history"])]==before["history"],record
        assert after["version"]==before["version"]+1,record
    final=goals();save(RAW/"goal-progress-final-state.json",{"at":datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),"items":[semantic(final[k]) for k in ["K-data-boundary","K-risk-attribution"]],"other_goals_not_modified_by_this_script":True})
    print(json.dumps(records,ensure_ascii=False))
if __name__=="__main__":main()
