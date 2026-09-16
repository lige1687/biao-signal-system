"""Independent remaining original-contract checks. Temporary DB + real HTTP/engine.
A valid request's own output/manifest is used, avoiding early rejection of the
wrong request manifest masking a missing params/input comparison.
"""
from pathlib import Path
fixture=Path(__file__).with_name('reproduce.py').read_text()
prefix=fixture.split('    resolved = client.post("/api/copilot/resolve"',1)[0]
checks=r'''
    _record=record
    def record(key,good,data):
        _record(key,good,data)
        (RAW/"remaining-results.json").write_text(json.dumps(observed,ensure_ascii=False,indent=2,default=str))
    from copy import deepcopy
    base=message(client,"按模块A退出1讨论依据",cid="valid-base").json()
    sid,qid=base["session_id"],base["question_id"]
    with patch.object(br,"start_request_worker",return_value=False):
        cr=create(client,sid,qid,"valid-run").json()
    run_sync(db,cr["request_id"])
    done=read_request(cr["request_id"])
    assert done["status"]=="completed",done
    output=Path(done["result_ref"])
    result=json.loads(output.read_text())
    follow=message(client,"仍按模块A退出1，这次依据是否适用？",sid=sid,cid="same-method").json()
    hs=follow["evidence_card"]["history_and_scope"]
    entry=next(x for x in hs["matched_runs"] if x["request_id"]==cr["request_id"])
    record("t1_unknown_window",not entry["supports_question"] and entry["compatibility"]!="exact",
       {"comparison_config":hs.get("comparison_config"),"matched":entry})
    explicit=message(client,"按模块A退出1，只比较2024-01-01至2024-06-28这个窗口",sid=sid,cid="explicit-window").json()
    eh=explicit["evidence_card"]["history_and_scope"]
    ee=next(x for x in eh["matched_runs"] if x["request_id"]==cr["request_id"])
    record("t1_explicit_window",not ee["supports_question"],{"asked_window":"2024-01-01..2024-06-28","config":eh.get("comparison_config"),"run":ee})
    # One request, its own correct manifest; change exactly one actual output field.
    recovery=[]
    for field,value in [("fee_label","different-fee"),("data_fingerprint","different-input"),("symbols",[A,B])]:
        wrong=deepcopy(result);wrong["params"][field]=value
        with connect(db) as conn:
            conn.execute("UPDATE agent_backtest_requests SET status='running',result_ref='',run_manifest_json='',error='' WHERE request_id=?",(cr["request_id"],));conn.commit()
            row=conn.execute("SELECT * FROM agent_backtest_requests WHERE request_id=?",(cr["request_id"],)).fetchone()
            error=br._validate_output_for_request(row,wrong,json.loads(row["input_refs_json"]))
        output.write_text(json.dumps(wrong))
        restored=read_request(cr["request_id"])
        recovery.append({"field":field,"altered":value,"validator_error":error,"status":restored["status"]})
    record("t2_recovery_params",all(x["status"]!="completed" for x in recovery),recovery)
    output.write_text(json.dumps(result))
    with connect(db) as conn:
        conn.execute("UPDATE agent_backtest_requests SET status='running',result_ref='',error='' WHERE request_id=?",(cr["request_id"],));conn.commit()
    normal=read_request(cr["request_id"])
    record("t2_valid_recovery",normal["status"]=="completed",{"status":normal["status"]})
    original=message(client,"按模块A整理成计划",sid=sid,cid="plan-retry").json()
    assert original.get("plan_artifact"),original
    retried=message(client,"按模块A整理成计划",sid=sid,cid="plan-retry").json()
    record("t3_plan_retry",original["plan_artifact"]==retried.get("plan_artifact"),
        {"first_question":original["question_id"],"retry_question":retried["question_id"],
         "first_artifact":original["plan_artifact"],"retry_artifact":retried.get("plan_artifact"),
         "same_text":original["reply"]==retried["reply"]})
    with connect(db) as conn:
        shaped=agent._server_plan_artifact(conn,sid,qid,A,{"suggested_plan":{
          "module":"A","direction":"long","entry_rule_id":"first_ma_pullback_confirmed",
          "entry_trigger_cn":"回调后站回均线","target_b_price":120.0}},"按模块A整理成计划")
    record("t3_field_contract",all(isinstance(shaped["fields"][k],dict) and "value" in shaped["fields"][k] for k in ("entry_rule_id","entry_trigger_cn","target_b_price")),shaped["fields"])

(RAW/"remaining-results.json").write_text(json.dumps(observed,ensure_ascii=False,indent=2,default=str))
(RAW/"source-after.json").write_text(json.dumps(hashes(),indent=2))
print("sources_unchanged",BEFORE==hashes(),flush=True)
'''
exec(compile(prefix+checks,str(Path(__file__).resolve()),'exec'))
