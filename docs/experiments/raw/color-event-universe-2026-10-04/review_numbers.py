"""Independent direct-price labels and saved-coefficient checks; never refits."""
import collections
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).parent

def main():
    p=ROOT/'docs/experiments/raw/volume-information-2026-09-30/execution/panel.json'
    data=json.loads(p.read_text()); calendar=data['calendar']; ix={d:i for i,d in enumerate(calendar)}
    bars={(r['asset'],r['date']):r for r in data['bars']}
    events=json.loads((HERE/'independent-events.json').read_text())['rows']
    lookup={r['id']:r for r in events}
    auxiliary=json.loads((HERE/'core/auxiliary.json').read_text())['runs']
    def target(r,kind):
        i=ix[r['date']]
        if i+21>=len(calendar):return None,None
        path=[float(bars[(r['asset'],d)]['close']) for d in calendar[i+1:i+22]]
        return (100*(path[-1]/path[0]-1) if kind=='forward_return' else
                max(0,100*(1-min(path)/path[0]))),calendar[i+21]
    def features(r):
        i=ix[r['date']];a=r['asset'];c=[float(bars[(a,d)]['close']) for d in calendar[i-60:i+1]]
        f={'ret20':100*(c[-1]/c[-21]-1),'ret60':100*(c[-1]/c[0]-1),
           'vol20':statistics.stdev(math.log(c[j]/c[j-1]) for j in range(len(c)-20,len(c)))*math.sqrt(252)*100,
           'bull_group':int(r['bull_group']), 'week20_green':int(r['week20_state']=='green'),
           'week20_black':int(r['week20_state']=='black')}
        f.update({'asset_'+code:int(a.startswith(code)) for code in ['510050','510500','588000']})
        return f
    def pred(r,detail):
        f=features(r)
        return detail['intercept']+sum((f[k]-m)/s*b for k,m,s,b in zip(detail['features'],detail['mean'],detail['std'],detail['coef']))
    def mse(rows):
        by=collections.defaultdict(list)
        for a,y,h in rows:by[a].append((h-y)**2)
        return statistics.mean(statistics.mean(v) for v in by.values())
    outputs=[];max_error=0
    for branch,rel in json.loads((HERE/'evidence-index.json').read_text())['results'].items():
        path=HERE/rel;result=json.loads(path.read_text());contract=json.loads(path.with_name('contract.json').read_text())
        kind=contract['target']['kind'];color=contract['feature']['event_color'];predictions=result['predictions']
        details={(d['fold'],d['model']):d for d in result['execution']['fit_details']}
        labelerr=prederr=0
        for r in predictions:
            event=lookup[r['id']];assert event['event_color']==color
            y,end=target(event,kind);assert end==r['label_end']
            labelerr=max(labelerr,abs(y-r['y']))
            for m in ['B1','B2']:prederr=max(prederr,abs(pred(event,details[(r['fold'],m)])-r[m]))
        assert labelerr<1e-9 and prederr<1e-9
        summaries=[];ref_rows=[];fallback=0
        for j,fold in enumerate(contract['split']['folds']):
            training=[]
            for r in events:
                if r['event_color']!=color or r['date']>fold['train_end']:continue
                y,end=target(r,kind)
                if end and end<fold['eval_start']:training.append((r,y))
            perasset=collections.defaultdict(list);perstate=collections.defaultdict(list)
            for r,y in training:perasset[r['asset']].append(y);perstate[(r['asset'],r['week20_state'])].append(y)
            training_errors={m:math.sqrt(mse([(r['asset'],y,pred(r,details[(str(j),m)])) for r,y in training])) for m in ['B1','B2']}
            for row in predictions:
                if row['fold']!=str(j):continue
                r=lookup[row['id']]; values=perstate.get((r['asset'],r['week20_state']))
                fallback+=int(not values)
                ref_rows.append((row['asset'],row['y'],statistics.mean(perasset[row['asset']]),statistics.mean(values or perasset[row['asset']])))
            summaries.append({'fold':j,'training_rows':len(training),'training_rmse':training_errors})
        simple=mse([(a,y,v) for a,y,v,_ in ref_rows]);state=mse([(a,y,v) for a,y,_,v in ref_rows])
        expected=auxiliary[branch]['state_only_training_group_mean']
        assert abs(simple-expected['etf_training_mean_mse'])<1e-9
        assert abs(state-expected['state_only_mse'])<1e-9
        assert fallback==expected['fallback_rows']
        outputs.append({'branch':branch,'label_max_absolute_error':labelerr,'prediction_max_absolute_error':prederr,
                        'evaluated_rows':len(predictions),'training':summaries,'simple_etf_rmse':math.sqrt(simple),
                        'state_only_rmse':math.sqrt(state),'fallback_rows':fallback,
                        'negative_predictions':{m:sum(r[m]<0 for r in predictions) for m in ['B1','B2']},
                        'nonnegative_prediction_required_for_interpretation':kind=='mae'})
        max_error=max(max_error,labelerr,prederr)
    report={'input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'branches':outputs,
            'new_fits':0,'max_error':max_error,'all_checks_passed':True,
            'scope':'Independent labels, features, saved-coefficient predictions and training-only simple means. No proof of vendor arrival, full action coverage or live profitability.'}
    (HERE/'independent-numeric-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'all_checks_passed':True,'max_error':max_error,'new_fits':0}))

if __name__=='__main__':main()
