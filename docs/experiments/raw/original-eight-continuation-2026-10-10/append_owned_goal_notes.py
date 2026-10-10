"""Append only approved progress notes; recover unknown writes by actual readback."""
import datetime,json,urllib.request
from pathlib import Path
RAW=Path(__file__).parent
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get():
    with opener.open('http://127.0.0.1:8000/api/upgrades',timeout=30) as r:return {x['id']:x for x in json.load(r)['items']}
def main():
    import sys
    phase=sys.argv[1]
    src=json.loads((RAW/(phase+'-goal-notes-20261011.json')).read_text())
    out=RAW/(phase+'-goal-readback-20261011.json')
    receipts=[]
    for goal_id,note in src['notes'].items():
        before=get()[goal_id]
        existed=any(x.get('note')==note for x in before['history'])
        intent={'goal_id':goal_id,'version_before':before['version'],'note':note,'scope':src['scope'],'before':before}
        (RAW/(phase+'-'+goal_id+'-write-intent-20261011.json')).write_text(json.dumps(intent,ensure_ascii=False,indent=2)+'\n')
        if not existed:
            body={'version':before['version'],'action':'note','note':note,'scope':src['scope']}
            req=urllib.request.Request('http://127.0.0.1:8000/api/upgrades/'+goal_id+'/actions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
            with opener.open(req,timeout=30) as r:json.load(r)
        after=get()[goal_id]
        assert sum(x.get('note')==note for x in after['history'])==1
        changed=[k for k in before if before[k]!=after[k]]
        assert set(changed)<= {'history','updated_at','version'},changed
        if not existed:assert after['history'][:-1]==before['history'] and after['version']==before['version']+1
        receipts.append({'goal_id':goal_id,'version_before':before['version'],'version_after':after['version'],'status':after['status'],'owner':after['owner'],'actual_note_readback':True,'persistent_fields_preserved':True,'changed_fields':changed,'reused_existing_identical_note':existed,'note':note})
        out.write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'result_commit':src['result_commit'],'receipts':receipts},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in x.items() if k!='note'} for x in receipts],ensure_ascii=False))
if __name__=='__main__':main()
