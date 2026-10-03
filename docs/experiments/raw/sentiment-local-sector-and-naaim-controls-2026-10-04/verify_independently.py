"""Independent price/label construction and augmented least-squares review, four fits."""
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]


def dump(name,obj):
    (ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def main():
    assert not (ROOT/'independent-review.json').exists(), 'sealed review already exists'
    begin=time.monotonic()
    paths={}
    for row in json.loads((ROOT/'inputs.json').read_text())['files']:
        p=REPO/row['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'];paths[row['role']]=p
    quotes=pd.read_csv(paths['prices'],parse_dates=['Date']).set_index('Date').Close
    survey=pd.read_csv(paths['survey'],parse_dates=['date'])
    observations=pd.read_csv(ROOT/'run-01/observations.csv',parse_dates=['anchor_date','source_date','target_end'])
    predictions=pd.read_csv(ROOT/'run-01/predictions.csv',parse_dates=['anchor_date','target_end'])
    for row,original in zip(observations.itertuples(),survey.itertuples(),strict=True):
        assert row.source_date==original.date and row.naaim==original.naaim
        k=int(quotes.index.searchsorted(original.date,side='right'))
        assert k==row.anchor_index and quotes.index[k]==row.anchor_date
        past=quotes.iloc[:k+1]
        returns=past.pct_change(fill_method=None)
        values=[100*(past.iloc[-1]/past.iloc[-21]-1),
                100*(past.iloc[-1]/past.iloc[-64]-1),
                100*(past.iloc[-1]/past.tail(200).mean()-1),
                100*(past.iloc[-1]/past.tail(252).max()-1),
                100*returns.tail(20).std(ddof=1)*math.sqrt(20)]
        np.testing.assert_allclose([row.r20,row.r63,row.dma200,row.dd252,row.rv20],values,rtol=1e-10,atol=1e-10)
        expected_y=100*(quotes.iloc[k+21]/quotes.iloc[k+1]-1)
        assert quotes.index[k+21]==row.target_end
        np.testing.assert_allclose(row.y,expected_y,rtol=1e-12,atol=1e-10)
    state=json.loads((ROOT/'research-state.json').read_text())
    assert state['core_fits']==4 and state['review_fits']==0
    differences=[];trials=[]
    for year in [2025,2026]:
        train=observations[observations.target_end<pd.Timestamp(f'{year}-01-01')]
        test=predictions[predictions.anchor_date.dt.year==year]
        for model in ['P','PX']:
            cols=['r20','r63','dma200','dd252','rv20']+(['naaim'] if model=='PX' else [])
            state['review_fits']+=1;assert state['review_fits']<=4
            dump('research-state.json',state)
            x=train[cols].to_numpy();mu=x.mean(axis=0);sigma=x.std(axis=0)
            a=np.column_stack([np.ones(len(x)),(x-mu)/sigma])
            penalizer=np.diag([0]+[1]*len(cols))
            augmented=np.vstack([a,math.sqrt(len(a)*.001)*penalizer])
            rhs=np.concatenate([train.y.to_numpy(),np.zeros(len(cols)+1)])
            beta=np.linalg.lstsq(augmented,rhs,rcond=None)[0]
            rebuilt=np.column_stack([np.ones(len(test)),(test[cols].to_numpy()-mu)/sigma])@beta
            differences.append(float(np.max(np.abs(rebuilt-test[f'pred_{model}']))))
            trials.append({'year':year,'model':model,'train_n':len(train),'eval_n':len(test),'method':'augmented least squares independent of frozen normal-equation kernel'})
    assert max(differences)<1e-9
    result=json.loads((ROOT/'run-01/results.json').read_text())
    for label,frame in [('overall',predictions)]+[(str(y),predictions[predictions.anchor_date.dt.year==y]) for y in [2025,2026]]:
        recorded=result['overall'] if label=='overall' else result['years'][label]
        for model in ['I','B','X','BX','P','PX']:
            error=frame[f'pred_{model}']-frame.y
            np.testing.assert_allclose(recorded[model]['mse_pp2'],np.mean(error**2),rtol=1e-12,atol=1e-12)
            np.testing.assert_allclose(recorded[model]['mae_pp'],np.mean(abs(error)),rtol=1e-12,atol=1e-12)
        primary=100*(1-recorded['PX']['mse_pp2']/recorded['P']['mse_pp2'])
        np.testing.assert_allclose(primary,recorded['PX_vs_P_improvement_pct'],rtol=1e-12)
    state.update(status='numeric_review_passed',next_action='archive report and portable saved-only checks; no more market fits')
    dump('research-state.json',state)
    dump('independent-review.json',{'passed':True,'market_fits':4,'all131_features_labels_reconstructed':True,'max_prediction_difference_pp':max(differences),'trials':trials,'wall_seconds':time.monotonic()-begin,'review_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'method_limits':'independent numerical construction by controller, not independent fresh historical sample or external scientific certification'})
    print(json.dumps({'passed':True,'review_fits':4,'max_prediction_difference_pp':max(differences)}))


if __name__=='__main__':main()
