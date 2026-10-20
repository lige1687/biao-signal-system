"""Controller-only contract checks; original production unchanged; temp DB + HTTP.
Frontend converter is bundled from actual component; payload expression extracted
verbatim for a headless save-path check, not a claim of browser acceptance.
"""
from pathlib import Path
prefix=Path(__file__).with_name('fixture.py').read_text()
checks=r'''
    from copy import deepcopy
    import subprocess
    original_record=record
    def record(key,good,data):
        original_record(key,good,data)
        (RAW/'additional-results.json').write_text(json.dumps(observed,ensure_ascii=False,indent=2,default=str))
    base=message(client,'按模块A退出1讨论依据',cid='base').json()
    sid,qid=base['session_id'],base['question_id']
    with patch.object(br,'start_request_worker',return_value=False):
        req=create(client,sid,qid,'run').json()
    run_sync(db,req['request_id'])
    done=read_request(req['request_id'])
    assert done['status']=='completed',done
    output=Path(done['result_ref']); result=json.loads(output.read_text())
    rg=result['data_range']; window=f"只比较{rg['start']}至{rg['end']}"
    def match(text,cid):
        r=message(client,text,sid=sid,cid=cid)
        assert r.status_code==200,r.text
        h=r.json()['evidence_card']['history_and_scope']
        return h,next(x for x in h['matched_runs'] if x['request_id']==req['request_id'])
    h,e=match('按模块A退出1，'+window,'exact')
    record('n0_exact_window_positive',e['supports_question'],{'config':h['comparison_config'],'entry':e})
    hh,ee=match('继续按刚才的条件，历史依据适用吗','inherit')
    record('n1_window_inherited',hh['comparison_config'].get('window')==h['comparison_config'].get('window') or bool(hh['comparison_config'].get('window')),{'first':h['comparison_config'],'followup':hh['comparison_config']})
    # Completed output changed after completion: read path must use full validator.
    bad=deepcopy(result);bad['params']['data_fingerprint']='different-input'
    output.write_text(json.dumps(bad))
    with connect(db) as conn:
        row=conn.execute('SELECT * FROM agent_backtest_requests WHERE request_id=?',(req['request_id'],)).fetchone()
        rejection=br._validate_output_for_request(row,bad,json.loads(row['input_refs_json']))
    hb,eb=match('按模块A退出1，'+window,'bad-completed')
    record('n2_completed_evidence_validates_input',not eb['supports_question'],{'recovery_validator_error':rejection,'read_entry':eb})
    output.write_text(json.dumps(result))
    # Correct own manifest with missing or inconsistent actual range.
    failures=[]
    for label,value in [('missing',{}),('wrong_start',dict(rg,start='2024-06-01')),('shortened_end',dict(rg,end='2024-06-28'))]:
        bad=deepcopy(result);bad['data_range']=value
        output.write_text(json.dumps(bad))
        with connect(db) as conn:
            conn.execute("UPDATE agent_backtest_requests SET status='running',result_ref='',run_manifest_json='',error='' WHERE request_id=?",(req['request_id'],));conn.commit()
        recovered=read_request(req['request_id'])
        failures.append({'change':label,'range':value,'status':recovered['status'],'error':recovered.get('error')})
    record('n3_recovery_actual_range',all(x['status']!='completed' for x in failures),failures)
    output.write_text(json.dumps(result))
    with connect(db) as conn:
        conn.execute("UPDATE agent_backtest_requests SET status='running',result_ref='',error='' WHERE request_id=?",(req['request_id'],));conn.commit()
    assert read_request(req['request_id'])['status']=='completed'
    # Same request's new worker output violates effective fee while manifest is valid.
    real_execute=bt.execute_run
    def altered_execute(*a,**kw):
        r=real_execute(*a,**kw);r['params']['fee_label']='different-fee';return r
    with patch.object(br,'start_request_worker',return_value=False):
        req2=create(client,sid,qid,'write-path',exit_variant='a6_3_structure_stop').json()
    with patch.object(bt,'execute_run',side_effect=altered_execute):
        run_sync(db,req2['request_id'])
    written=read_request(req2['request_id'])
    record('n4_normal_completion_same_validator',written['status']!='completed',{'status':written['status'],'error':written.get('error')})
    # Produce valid known system artifact, call actual frontend converter, then real save API.
    plan_reply=message(client,'按模块A整理成计划',sid=sid,cid='plan').json()
    pq=plan_reply['question_id']
    with connect(db) as conn:
        artifact=agent._server_plan_artifact(conn,sid,pq,A,{'suggested_plan':{'module':'A','direction':'long','entry_rule_id':'first_ma_pullback_confirmed','entry_trigger_cn':'回调后站回均线','invalidation_price':90.0,'target_b_price':120.0}},'按模块A整理成计划')
        row=conn.execute("SELECT message_id,meta_json FROM agent_messages WHERE question_id=? AND role='assistant' ORDER BY message_id DESC LIMIT 1",(pq,)).fetchone()
        meta=json.loads(row['meta_json']);meta['plan_artifact']=artifact
        conn.execute('UPDATE agent_messages SET meta_json=? WHERE message_id=?',(json.dumps(meta),row['message_id']));conn.commit()
    (RAW/'known-artifact.json').write_text(json.dumps(artifact))
    src=(ROOT/'web/src/components/PlanDraftCard.tsx').read_text()
    expression=src.split('const buildPayload = (rulesetVersion: string): CreatePlanPayload => (',1)[1].split('\n  });',1)[0]
    js="import {planDraftFromArtifact} from './plan-card.mjs';\nimport fs from 'node:fs';\n"
    js+="const artifact=JSON.parse(fs.readFileSync(new URL('./known-artifact.json',import.meta.url)));\nconst {draft}=planDraftFromArtifact(artifact);\n"
    js+=f"const symbol={json.dumps(A)},sessionId={json.dumps(sid)},questionId={pq},clientRequestId='controller-known-draft',rulesetVersion='test';\n"
    js+='const payload=('+expression+'});\nconsole.log(JSON.stringify({draft,payload}));\n'
    (RAW/'frontend-save.mjs').write_text(js)
    run=subprocess.run(['node',str(RAW/'frontend-save.mjs')],text=True,capture_output=True)
    (RAW/'frontend-run.log').write_text(run.stdout+'\n'+run.stderr)
    assert run.returncode==0,run.stderr
    adapted=json.loads(run.stdout)
    saved=client.post('/api/plans',json=adapted['payload'])
    assert saved.status_code==201,saved.text
    plan=saved.json()
    with connect(db) as conn:
        stored=dict(conn.execute('SELECT * FROM trade_plans WHERE plan_id=?',(plan['plan_id'],)).fetchone())
    record('n5_known_fields_survive_frontend_save',all(stored.get(k)==artifact['fields'][k]['value'] for k in ['entry_rule_id','entry_trigger_cn','target_b_price']),{'artifact':artifact['fields'],'converted':adapted,'saved_fields':{k:stored.get(k) for k in ['entry_rule_id','entry_trigger_cn','target_b_price']}})
    retry=message(client,'按模块A整理成计划',sid=sid,cid='plan').json()
    stream=client.post('/api/agent/chat/stream',json={'message':'按模块A整理成计划','context_kind':'symbol','symbol':A,'session_id':sid,'client_request_id':'plan'})
    (RAW/'stream-retry.txt').write_text(stream.text)
    history=client.get(f'/api/agent/sessions/{sid}/messages').json()
    record('n6_plan_replay_preserved',retry.get('plan_artifact')==artifact and artifact['artifact_id'] in stream.text and any(x.get('plan_artifact')==artifact for x in history),{'http_retry_artifact':retry.get('plan_artifact'),'stream_status':stream.status_code,'history_match':any(x.get('plan_artifact')==artifact for x in history)})
(RAW/'source-after.json').write_text(json.dumps(hashes(),indent=2))
print('source_unchanged',BEFORE==hashes(),flush=True)
'''
exec(compile(prefix+checks,str(Path(__file__).resolve()),'exec'))
