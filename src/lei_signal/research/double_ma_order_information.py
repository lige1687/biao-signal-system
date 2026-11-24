"""T03 daily double-order information. Default feature-only; no implicit real y.

Proposed install: src/lei_signal/research/double_ma_order_information.py.
Future real labels require both explicit compute_labels=True and a separately
authorized contract permissions.real_labels=True; current proposal forbids it.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from lei_signal.features.indicators import seeded_ema
from lei_signal.research.definitions import economic_index

DEFINITION_REF = 'research.trend.double_ma_order_state@1.0.0'
KIND = 'double_ma_order_information'
ASSETS = ('510300.SS', '510050.SS', '510500.SS', '588000.SS')
BASELINE = ('distance_sma20','distance_sma60','distance_sma120','distance_ema20','distance_ema60','distance_ema120','ret20','vol20','sma60_up5','asset_510050','asset_510500','asset_588000')

def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def _known(r):
    c = r.get('close')
    return (r.get('status') == 'quoted' and r.get('action_known') is True and
            isinstance(c, (int,float)) and not isinstance(c,bool) and math.isfinite(c) and c > 0)

def _synthetic_or_authorized_label(rows, i, target):
    # Caller already enforces the real-label permission guard. No halt skipping.
    a,b = i+1,i+21
    if b >= len(rows):
        return None,None,'immature_label'
    end = rows[b]['date']
    path = rows[a:b+1]
    if not all(_known(r) for r in path):
        return None,end,'all21_quoted_qualified_closes_required'
    entry = float(path[0]['close'])
    return 100*max(0.,1-min(float(r['close']) for r in path)/entry),end,None

def prepare_double_order_observations(payload, contract, *, compute_labels=False):
    synthetic = payload.get('data_mode') == 'synthetic' and contract.get('data',{}).get('mode') == 'synthetic'
    if payload.get('data_mode') != contract.get('data',{}).get('mode'):
        raise ValueError('payload and contract data modes differ')
    if compute_labels and not synthetic and contract.get('permissions',{}).get('real_labels') is not True:
        raise ValueError('T03 preparation refuses real labels; separate explicit effect authorization is required')
    f=contract['feature']; t=contract['target']
    if (f.get('kind')!=KIND or f.get('definition_ref')!=DEFINITION_REF or
        f.get('lookback')!=120 or f.get('warmup')!=252 or f.get('missing_policy')!='segmented'):
        raise ValueError('T03 exact dual20/60/120 segmented252 feature required')
    if (t.get('kind')!='mae' or t.get('start_offset')!=1 or t.get('end_offset')!=21 or
        t.get('entry_field')!='close' or t.get('path_field','close')!='close' or t.get('price_measure','economic_price')!='economic_price'):
        raise ValueError('T03 exact21-close20-interval MAE target required')
    calendar=payload['calendar']; assets=contract['universe']['assets']
    if not calendar or calendar!=sorted(set(calendar)):
        raise ValueError('ordered unique official session timeline required')
    for d in calendar:
        datetime.strptime(d,'%Y-%m-%d')
    if len(set(assets))!=len(assets):
        raise ValueError('duplicate asset')
    if payload.get('data_mode')!='synthetic' and (tuple(assets)!=ASSETS or payload.get('price_series')!='economic_price'):
        raise ValueError('four fixed economic-price ETF sources required')
    by={}
    for r in payload['bars']:
        k=(r['asset'],r['date'])
        if k in by or r['asset'] not in assets or r['date'] not in calendar:
            raise ValueError('duplicate/out-of-scope observation')
        if r.get('status') not in {'quoted','halt','vendor_missing','not_listed','terminated','action_unknown'}:
            raise ValueError('unsupported quote status')
        if r.get('status')!='quoted' and any(r.get(n) is not None for n in ('open','high','low','close')):
            raise ValueError('nonquoted observation cannot carry prices')
        by[k]=r
    out=[]
    for asset in assets:
        bars=[by.get((asset,d),{'asset':asset,'date':d,'status':'vendor_missing'}) for d in calendar]
        valid=[_known(r) for r in bars]
        runs=[]; start=None
        for i in range(len(calendar)+1):
            if i<len(calendar) and valid[i]:
                if start is None:start=i
            elif start is not None:
                runs.append((start,i)); start=None
        feats={}
        for begin,end in runs:
            c=pd.Series([bars[i]['close'] for i in range(begin,end)],dtype=float)
            m={f'{p}{n}':(c.rolling(n,min_periods=n).mean() if p=='sma' else seeded_ema(c,n)) for p in ('sma','ema') for n in (20,60,120)}
            ret=100*(c/c.shift(20)-1)
            vol=100*c.pct_change(fill_method=None).rolling(20,min_periods=20).std(ddof=1)
            episode=0; prev=None; episode_id=None
            for k in range(251,len(c)):
                state=bool(m['sma20'].iloc[k]>m['sma60'].iloc[k]>m['sma120'].iloc[k] and m['ema20'].iloc[k]>m['ema60'].iloc[k]>m['ema120'].iloc[k])
                if prev is None or state!=prev:
                    episode+=1;episode_id=f'{asset}|{calendar[begin+k]}|{int(state)}'
                prev=state
                x={f'distance_{name}':float(c.iloc[k]/v.iloc[k]-1) for name,v in m.items()}
                x.update(ret20=float(ret.iloc[k]),vol20=float(vol.iloc[k]),sma60_up5=int(m['sma60'].iloc[k]>m['sma60'].iloc[k-5]),added=int(state))
                x.update({f'asset_{code[:6]}':int(asset==code) for code in ASSETS[1:]})
                feats[begin+k]=(x,episode_id,k+1)
        for i,d in enumerate(calendar):
            if not contract['question']['period'][0]<=d<=contract['question']['period'][1]:continue
            value=feats.get(i)
            x,eid,continuous=value if value else ({k:None for k in (*BASELINE,'added')},None,0)
            endpoint=i+21
            flags=endpoint<len(calendar) and all(valid[j] for j in range(i+1,endpoint+1))
            y,le,lr=_synthetic_or_authorized_label(bars,i,t) if compute_labels else (None,None,'not_computed')
            out.append({'id':f'{asset}|{d}','asset':asset,'date':d,'stratum':f'{asset}|{d[:4]}',
                'features':x,'F':bool(x['added']) if value else None,'episode_id':eid,'ready_252':bool(value),
                'continuous_close':continuous,'eligible':bool(value and (y is not None if compute_labels else True)),
                'feature_reason':None if value else 'close_unqualified_or_segment_warmup252',
                'y':y,'label_end':le,'target_label_reason':lr,'label_reason':lr,'tested_condition':bool(x['added']) if value else None,
                'target_end_date':calendar[endpoint] if endpoint<len(calendar) else None,'target_dates_qualified':flags})
    return {'observations':out,'coverage':{'observations':len(out),'ready_252':sum(r['ready_252'] for r in out)},'warnings':['Seen retrospective deterministic expression; no live PIT/trade certification.']}

def qualify_double_order_panel(payload, contract, root):
    """Formal economic_index arithmetic on explicit replay clock; no historical PIT fiction.

    All original effective/availability fields are preserved. Computational dates
    alone are translated to dates AFTER actual recomputation time; all shadow
    availability is actual recomputation time. This checks price mathematics,
    never claims those events were known on original historical dates.
    """
    root=Path(root); q=contract['data']['qualification']
    if _sha(root/q['manifest_path'])!=q['manifest_sha256']:raise ValueError('manifest changed')
    manifest=json.loads((root/q['manifest_path']).read_text())
    panel_path=root/contract['data']['path']
    if _sha(panel_path)!=manifest['panel_sha256'] or _sha(panel_path)!=contract['data']['sha256']:raise ValueError('panel hash changed')
    bound=json.loads(panel_path.read_text())
    if payload!=bound:raise ValueError('caller payload differs from bound panel')
    if (manifest['assets']!=list(ASSETS) or manifest['panel_rows']!=len(bound['bars']) or
        manifest['calendar_rows']!=len(bound['calendar'])):raise ValueError('manifest asset/count mismatch')
    calendar_path=root/q['calendar_path']
    if _sha(calendar_path)!=q['calendar_sha256']:raise ValueError('official calendar changed')
    official=json.loads(calendar_path.read_text())
    expected=sorted(d for d,v in official['days'].items() if v['is_trading_day'] and bound['calendar'][0]<=d<=bound['calendar'][-1])
    if expected!=bound['calendar']:raise ValueError('panel differs from official session timeline')
    if manifest['economic_actions']['historical_available_at'] is not None:raise ValueError('frozen historical availability policy changed')
    if len(manifest['bindings'])!=40:raise ValueError('frozen40 binding count changed')
    for item in manifest['bindings']:
        if _sha(root/item['path'])!=item['sha256']:raise ValueError('actual named source binding changed: '+item['path'])
    prior=json.loads(Path(q['prior_qualification_path']).read_text())
    if _sha(q['prior_qualification_path'])!=q['prior_qualification_sha256']:raise ValueError('prior qualification changed')
    if not prior['underlying_bindings']['all_match']:raise ValueError('prior named sources unqualified')
    source_path=root/manifest['source_qualification']['path']
    if _sha(source_path)!=manifest['source_qualification']['sha256']:raise ValueError('source qualification hash changed')
    source=json.loads(source_path.read_text())
    actions_path=root/manifest['economic_actions']['path']
    if _sha(actions_path)!=manifest['economic_actions']['sha256']:raise ValueError('actions changed')
    actions=json.loads(actions_path.read_text())
    calendar=payload['calendar']; by={(r['asset'],r['date']):r for r in payload['bars']}
    at=datetime.now(timezone.utc); replay_first=pd.Timestamp((at+timedelta(days=1)).date())
    original_first=pd.Timestamp(calendar[0]); shift=replay_first-original_first
    checked={}
    for asset in contract['universe']['assets']:
        info=source['products'][asset]; path=root/info['nominal_path']
        if _sha(path)!=info['nominal_sha256']:raise ValueError('nominal input changed')
        if path.suffix=='.parquet':
            frame=pd.read_parquet(path,columns=['close']); nom={str(d)[:10]:float(c) for d,c in zip(frame.index,frame['close'])}
        else:
            with path.open() as stream:nom={r['date']:float(r['close']) for r in csv.DictReader(stream)}
        selected=[a for a in actions['included'] if a['symbol']==asset]
        shadow=[{**a,'effective_date':str((pd.Timestamp(a['close_effective_date'])+shift).date()),'available_at':at.isoformat()} for a in selected]
        series=pd.Series([nom[d] for d in calendar],index=pd.DatetimeIndex([pd.Timestamp(d)+shift for d in calendar]))
        computed=economic_index(series,shadow).to_numpy()
        delta=max(abs(computed[i]-by[(asset,d)]['close']) for i,d in enumerate(calendar))
        if delta>1e-10:raise ValueError('formal economic_index differs from panel')
        checked[asset]={'rows':len(calendar),'actions':len(selected),'max_abs_difference':float(delta)}
    return {'quality':checked,'actual_source_bindings_verified':40,'formal_primitive':'lei_signal.research.definitions.economic_index',
        'recomputed_at':at.isoformat(),'replay_clock_first':str(replay_first.date()),
        'clock_translation':'Original date offsets preserved; shadow computational clock after actual recomputation time. Source historic available_at stays null; no real labels.',
        'historical_arrival':'not_certified','action_history_completeness':'not_proved','allowed_conclusion_ceiling':['insufficient','not_supported'],
        'warnings':['Retrospective price-math reconstruction only; source action arrival null and Shanghai-specific calendar completeness not certified.']}

def primary_rmse_summary(predictions, axis, dependence, *, policy='equal_asset'):
    """Pure fixed-prediction aggregation, never fitting. Use only after authorization.

    Identical frame/date-axis/seed draws give paired old/new squared-loss means.
    RMSE improvement is sqrt(old_draw)-sqrt(new_draw), never sqrt(deltaMSE).
    """
    from lei_signal.research.workflow_evaluation import _block_draws, _weights
    frame=pd.DataFrame(predictions)
    if frame.empty or frame.duplicated(['asset','date']).any():raise ValueError('nonempty paired unique predictions required')
    values=frame[['y','B1','B2']].to_numpy(float)
    if not np.isfinite(values).all():raise ValueError('nonfinite predictions forbidden')
    old=(frame.B1-frame.y).to_numpy()**2;new=(frame.B2-frame.y).to_numpy()**2
    w=_weights(frame,policy);old_mse=float(w@old);new_mse=float(w@new)
    old_draw,old_invalid=_block_draws(frame,old,axis,policy,dependence)
    new_draw,new_invalid=_block_draws(frame,new,axis,policy,dependence)
    if old_invalid!=new_invalid or len(old_draw)!=len(new_draw):raise ValueError('paired resampling support differs')
    delta=np.sqrt(old_draw)-np.sqrt(new_draw)
    secondary=old_draw-new_draw
    return {'metric':'RMSE','unit':'percentage_point','B1':math.sqrt(old_mse),'B2':math.sqrt(new_mse),
        'absolute_error_improvement':math.sqrt(old_mse)-math.sqrt(new_mse),
        'attention_threshold_pp':0.10,'lo':float(np.quantile(delta,.025)) if len(delta) else None,
        'hi':float(np.quantile(delta,.975)) if len(delta) else None,'valid_draws':len(delta),
        'unestimable_draws':old_invalid,'dependence':dict(dependence),
        'secondary':{'metric':'MSE','unit':'percentage_point_squared','B1':old_mse,'B2':new_mse,
            'absolute_error_improvement':old_mse-new_mse,'lo':float(np.quantile(secondary,.025)) if len(secondary) else None,
            'hi':float(np.quantile(secondary,.975)) if len(secondary) else None},
        'scope':'fixed paired OLS expression forecast-error difference only; no account value or strong significance claim'}

def attach_primary_rmse(result, contract, observations):
    if contract['feature']['kind']!=KIND:return result
    if not result.get('predictions'):
        result['primary_rmse']={'status':'not_computed','reason':'no authorized predictions'}
        return result
    axis=sorted({r['date'] for r in observations if any(f['eval_start']<=r['date']<=f['eval_end'] for f in contract['split']['folds'])})
    result['primary_rmse']=primary_rmse_summary(result['predictions'],axis,contract['dependence'])
    secondary={**contract['dependence'],'block_length':60}
    result['primary_rmse_block60']=primary_rmse_summary(result['predictions'],axis,secondary)
    return result
