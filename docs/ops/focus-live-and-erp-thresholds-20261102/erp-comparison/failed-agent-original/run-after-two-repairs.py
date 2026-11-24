from __future__ import annotations
import collections, datetime as dt, hashlib, json, pathlib, random, statistics
ROOT=pathlib.Path(__file__).resolve().parents[4]
OUT=pathlib.Path(__file__).resolve().parent
M=json.loads((OUT/'method.json').read_text())
P=ROOT/M['data']['frozenEligibleWeeks']
assert hashlib.sha256(P.read_bytes()).hexdigest()==M['data']['sha256']
rows=json.loads(P.read_text())
assert len(rows)==920 and rows[0]['date']=='2008-11-14'
old_contract=json.loads((ROOT/'docs/experiments/raw/douyin-observation-models-overlap-2026-10-31/erp-effect-display-20261101/compute/contract.json').read_text())
price_spec=old_contract['inputs']['dailyPrice']
price_path=ROOT/price_spec['path']
assert hashlib.sha256(price_path.read_bytes()).hexdigest()==price_spec['sha256']
price_dates=json.loads(price_path.read_text())['series']['hs300']['dates']
price_index={day:i for i,day in enumerate(price_dates)}
for r in rows:
    r['priceIndex']=price_index[r['date']]
    r['block']=f"{2008+2*((int(r['date'][:4])-2008)//2)}-{2009+2*((int(r['date'][:4])-2008)//2)}"

def q(vals,p):
    a=sorted(vals)
    if not a:return None
    x=(len(a)-1)*p;i=int(x);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i)
def mean(vals):return statistics.fmean(vals) if vals else None
def sign(side):return 1 if side=='upper' else -1

def metric(es,allrows,h,with_boot=False):
    controls=[r for r in allrows if not r['event']]
    cells=collections.defaultdict(list)
    for r in controls:cells[r['B']].append(r['outcomes'][str(h)]['returnPct'])
    cellmean={k:mean(v) for k,v in cells.items() if len(v)>=5}
    common=[r for r in es if r['B'] in cellmean]
    actual=[r['outcomes'][str(h)]['returnPct'] for r in es]
    directional=[sign(r['side'])*r['outcomes'][str(h)]['returnPct'] for r in es]
    matched=[sign(r['side'])*(r['outcomes'][str(h)]['returnPct']-cellmean[r['B']]) for r in common]
    base=mean([r['outcomes'][str(h)]['returnPct'] for r in allrows])
    return {'n':len(es),'riseN':sum(v>0 for v in actual),'fallN':sum(v<0 for v in actual),'meanReturnPct':mean(actual),'medianReturnPct':statistics.median(actual) if actual else None,'meanDirectionalPct':mean(directional),'allWeekReturnPct':base,'allWeekDirectionalDifferencePct':(mean(directional)-sign(es[0]['side'])*base if es and all(r['side']==es[0]['side'] for r in es) else None),'matchedN':len(common),'matchedControlPct':mean([cellmean[r['B']] for r in common]),'matchedDirectionalIncrementPct':mean(matched),'meanAdversePct':mean([r['outcomes'][str(h)]['minMovePct'] if r['side']=='upper' else -r['outcomes'][str(h)]['maxMovePct'] for r in es]),'worstAdversePct':min([r['outcomes'][str(h)]['minMovePct'] if r['side']=='upper' else -r['outcomes'][str(h)]['maxMovePct'] for r in es],default=None),'commonDates':[r['date'] for r in common]}

def bootstrap(es,allrows,h):
    blocks=sorted(set(r['block'] for r in allrows));rng=random.Random(20261101)
    eb={b:[r for r in es if r['block']==b] for b in blocks};ab={b:[r for r in allrows if r['block']==b] for b in blocks}
    vals=[]
    for _ in range(2000):
        drawn=[rng.choice(blocks) for _ in blocks]
        e=[r for b in drawn for r in eb[b]];a=[r for b in drawn for r in ab[b]]
        if not e:continue
        x=metric(e,a,h)['matchedDirectionalIncrementPct']
        if x is not None:vals.append(x)
    return {'lo':q(vals,.025),'hi':q(vals,.975),'valid':len(vals),'empty':2000-len(vals)}

results={'audit':{'rows':len(rows),'firstDate':rows[0]['date'],'lastDate':rows[-1]['date']},'thresholds':{},'eventMap':{},'increment':{}}
all_events={}
for k in (1,1.5,2):
    rs=[dict(r) for r in rows]
    for i,r in enumerate(rs):
        r['side']='upper' if r['erp']>r['middle']+k*r['sigma'] else 'lower' if r['erp']<r['middle']-k*r['sigma'] else 'inside'
        prior=rs[i-1] if i else None
        gap=(dt.date.fromisoformat(r['date'])-dt.date.fromisoformat(prior['date'])).days if prior else 999
        r['event']=bool(prior and gap<=10 and r['side']!='inside' and prior['side']!=r['side'])
    es=[r for r in rs if r['event']];all_events[k]=es
    result={'bandWeeks':{s:sum(r['side']==s for r in rs) for s in ('upper','lower')},'events':{s:sum(r['side']==s for r in es) for s in ('upper','lower')},'eligibleByH':{},'byH':{},'byPeriod63':{},'cooldown63':{}}
    for h in (21,63,126):
        eligible=[r for r in rs if r['outcomes'].get(str(h))]
        events=[r for r in eligible if r['event']]
        result['eligibleByH'][str(h)]=len(eligible)
        result['byH'][str(h)]={}
        for side in ('upper','lower'):
            sub=[r for r in events if r['side']==side]
            result['byH'][str(h)][side]=metric(sub,eligible,h)|{'ciMatched':bootstrap(sub,eligible,h)}
    eligible=[r for r in rs if r['outcomes'].get('63')]
    for period,pred in [('through2016',lambda r:r['date']<='2016-12-31'),('from2017',lambda r:r['date']>='2017-01-01')]:
        aa=[r for r in eligible if pred(r)];ee=[r for r in aa if r['event']]
        result['byPeriod63'][period]={side:metric([r for r in ee if r['side']==side],aa,63) for side in ('upper','lower')}
    for side in ('upper','lower'):
        last=None;kept=[]
        for r in eligible:
            if r['event'] and r['side']==side:
                if last is None or r['priceIndex']-last>63:kept.append(r);last=r['priceIndex']
        result['cooldown63'][side]=metric(kept,eligible,63)
    result['dates']={side:[r['date'] for r in es if r['side']==side] for side in ('upper','lower')}
    results['thresholds'][str(k)]=result
    results['eventMap'][str(k)]=[{'date':r['date'],'side':r['side'],'z':(r['erp']-r['middle'])/r['sigma'],'B':r['B'],'block':r['block'],'outcomes':r['outcomes']} for r in es]
# Compare episodes by nearest same-side events within 126 trading days, recording time shift as well as standalone signals.
for looser in (1,1.5):
    prev=all_events[looser];strict=all_events[2]
    out={}
    for side in ('upper','lower'):
        a=[r for r in prev if r['side']==side];b=[r for r in strict if r['side']==side]
        aligned=[];standalone=[]
        for r in a:
            nxt=[s for s in b if 0<=s['priceIndex']-r['priceIndex']<=126]
            if nxt:
                s=min(nxt,key=lambda x:x['priceIndex']-r['priceIndex'])
                aligned.append({'earlyDate':r['date'],'strictDate':s['date'],'leadTradingDays':s['priceIndex']-r['priceIndex'],'earlyReturn63Pct':r['outcomes']['63']['returnPct'] if r['outcomes'].get('63') else None,'strictReturn63Pct':s['outcomes']['63']['returnPct'] if s['outcomes'].get('63') else None})
            else:standalone.append(r)
        out[side]={'aligned':aligned,'standaloneDates':[r['date'] for r in standalone],'standaloneN':len(standalone),'standalone63':metric([r for r in standalone if r['outcomes'].get('63')],[r for r in rows if r['outcomes'].get('63') and dict(r,side='inside',event=False)],63) if False else None}
        # Actual standalone comparison uses the threshold's own non-event controls.
        rr=[dict(r) for r in rows if r['outcomes'].get('63')]
        dset=set(x['date'] for x in prev)
        for x in rr:x['event']=x['date'] in dset
        out[side]['standalone63']=metric([r for r in standalone if r['outcomes'].get('63')],rr,63)
    results['increment'][str(looser)]=out
old=json.loads((ROOT/M['data']['oldResults']).read_text())
reconcile={}
for side in ('upper','lower'):
    new=results['thresholds']['2']['byH']['63'][side]
    was=old['horizons']['63']['bySide'][side]
    reconcile[side]={'eventN':new['n'],'oldEventN':was['raw']['eventN'],'meanReturnDiffPct':new['meanReturnPct']-was['actualReturnMeanPct'],'matchedDirectionalIncrementDiffPct':new['matchedDirectionalIncrementPct']-was['matched']['incrementPct'],'dateAgreement':results['thresholds']['2']['dates'][side]==[r['date'] for r in json.loads((ROOT/'docs/experiments/raw/douyin-observation-models-overlap-2026-10-31/erp-effect-display-20261101/compute/entry-events.json').read_text()) if r['side']==side]}
results['reconcile2sigma']=reconcile
(OUT/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps({'counts':{k:v['events'] for k,v in results['thresholds'].items()},'reconcile':reconcile},ensure_ascii=False))
