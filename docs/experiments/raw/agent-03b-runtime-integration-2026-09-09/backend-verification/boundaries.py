"""Isolated review of explicitly required object/window and unknown boundaries."""
from pathlib import Path
prefix=Path(__file__).with_name('fixture.py').read_text()
checks=r'''
    from copy import deepcopy
    oldrecord=record
    def record(k,ok,data):
        oldrecord(k,ok,data)
        (RAW/'boundary-results.json').write_text(json.dumps(observed,ensure_ascii=False,indent=2,default=str))
    def chat(text,cid,symbol=A):
        response=message(client,text,sid=sid,cid=cid,symbol=symbol)
        assert response.status_code==200,response.text
        return response.json()
    first=message(client,'按模块A退出1，只比较2024-01-01至2025-04-04',cid='window-first').json()
    sid,qid=first['session_id'],first['question_id']
    with patch.object(br,'start_request_worker',return_value=False):
        cr=create(client,sid,qid,'valid-a').json()
    run_sync(db,cr['request_id'])
    done=read_request(cr['request_id']);assert done['status']=='completed',done
    output=Path(done['result_ref']);result=json.loads(output.read_text())
    original_window=first['evidence_card']['history_and_scope']['comparison_config']['window']
    same=chat('继续按刚才的条件讨论','same')
    samecfg=same['evidence_card']['history_and_scope']['comparison_config']
    record('w0_same_object_inherits',samecfg['window']['start']==original_window['start'] and samecfg['window']['end']==original_window['end'],samecfg)
    switched=chat(f'换看{B}，按模块A退出1讨论','switch',B)
    sc=switched['evidence_card']['history_and_scope']['comparison_config']
    record('w1_other_object_does_not_inherit',sc['window'] is None,{'resolved':switched['resolved_symbol'],'config':sc,'original_symbol':A})
    explicit=chat('只比较2024-01-01至2024-06-28，按模块A退出1讨论','b-window',B)
    with patch.object(br,'start_request_worker',return_value=False):
        rb=create(client,sid,explicit['question_id'],'valid-b',symbol=B,data_cutoff='2024-06-28').json()
    run_sync(db,rb['request_id']);bdone=read_request(rb['request_id']);assert bdone['status']=='completed',bdone
    adopted=chat(f'回到{A}，采用这次回测的窗口，按模块A退出1讨论','adopt-a')
    ac=adopted['evidence_card']['history_and_scope']['comparison_config']
    record('w2_adopt_does_not_select_other_object',not ac.get('window') or (bdone['run_id'] not in ac['window'].get('source','') and ac['window']['start']==original_window['start'] and ac['window']['end']==original_window['end']),{'resolved':adopted['resolved_symbol'],'config':ac,'other_run_id':bdone['run_id'],'other_symbol':B})
    invalid=chat('按模块A退出1，只比较2024-02-30至2024-06-28','invalid-date')
    ic=invalid['evidence_card']['history_and_scope']['comparison_config']
    record('w3_invalid_calendar_date_unverified',ic.get('window_state')!='verified',ic)
    # Valid original result still supports explicit same window after all switches.
    exact_text='按模块A退出1，只比较2024-01-01至2025-04-04'
    valid=chat(exact_text,'valid-read')['evidence_card']['history_and_scope']
    entry=next(x for x in valid['matched_runs'] if x['request_id']==cr['request_id'])
    record('v0_valid_complete_result_supported',entry['supports_question'],entry)
    # Missing is distinct from explicit null in the required full parameter record.
    bad=deepcopy(result);assert 'stop_atr_buffer' in bad['params'] and bad['params']['stop_atr_buffer'] is None
    del bad['params']['stop_atr_buffer'];output.write_text(json.dumps(bad))
    with connect(db) as conn:
        row=conn.execute('SELECT * FROM agent_backtest_requests WHERE request_id=?',(cr['request_id'],)).fetchone()
        error=br._validate_output_for_request(row,bad,json.loads(row['input_refs_json']))
    missing=chat(exact_text,'missing-field')['evidence_card']['history_and_scope']
    me=next(x for x in missing['matched_runs'] if x['request_id']==cr['request_id'])
    record('v1_missing_required_field_not_exact',error is not None and not me['supports_question'],{'validation_error':error,'entry':me})
    output.write_text(json.dumps(result))
    valid_question=chat(exact_text,'valid-second-question')
    with patch.object(br,'start_request_worker',return_value=False):
        good2=create(client,sid,valid_question['question_id'],'good-second',data_cutoff='2025-04-04').json()
    assert good2['request_id']!=cr['request_id']
    run_sync(db,good2['request_id']);assert read_request(good2['request_id'])['status']=='completed'
    before_bad=chat(exact_text,'two-good-before')['evidence_card']['history_and_scope']
    assert good2['request_id'] in before_bad['supporting_runs']
    bad=deepcopy(result);bad['run_manifest']='invalid-manifest-shape';output.write_text(json.dumps(bad))
    damaged=chat(exact_text,'damaged-manifest')
    dc=damaged.get('evidence_card')
    bad_entry=next((x for x in (dc or {}).get('history_and_scope',{}).get('matched_runs',[]) if x.get('request_id')==cr['request_id']),None)
    rejected_visible=bool(bad_entry and not bad_entry.get('supports_question') and (bad_entry.get('validation_reject') or bad_entry.get('differences_cn')))
    record('v2_bad_record_does_not_remove_evidence_card',dc is not None and bool(dc.get('facts')) and cr['request_id'] not in dc.get('history_and_scope',{}).get('supporting_runs',[]) and good2['request_id'] in dc.get('history_and_scope',{}).get('supporting_runs',[]) and rejected_visible,{'card':dc,'reply':damaged.get('reply'),'bad_entry':bad_entry,'good_run_before':good2['request_id'],'supporting_before':before_bad['supporting_runs']})
    output.write_text(json.dumps(result))
(RAW/'source-after.json').write_text(json.dumps(hashes(),indent=2))
print('source_unchanged',BEFORE==hashes(),flush=True)
'''
exec(compile(prefix+checks,str(Path(__file__).resolve()),'exec'))
