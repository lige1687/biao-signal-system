"""Independent, offline reconciliation of one frozen financial evaluation result.

CLI: --evaluation-contract FINANCIAL_EVALUATION_RUN_JSON --result-manifest
FINANCIAL_EVALUATION_RESULT_MANIFEST_JSON --out NEW_EXTERNAL_DIRECTORY.
The contract binds design/amendments, original saved prices, panel, and runner;
the result manifest binds stock_weights.csv and summary files.  The verifier
uses only Python's standard library and never imports the evaluation runner.
Output is create-only on the same mounted external device as the main result.
No network, fitting, market fetch, original momentum run, or trading write.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import statistics
import struct
from collections import defaultdict
from pathlib import Path

METHODS = 'PMFBD'
SCOPES = {'gp': ('gpa', False), 'common_gp': ('gpa', True), 'common_cfo': ('cfoa', True)}
SCENARIOS = {'unknown_minus_one': -1., 'unknown_zero': 0.}
PAIRS = [('F','P'),('B','M'),('B','D'),('B','P'),('B','F')]
FILES = ('stock_weights.csv','monthly.json','qualification_layers.json','performance.json','paired.json','other_uses.json','uncertainty.json')


def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()


def rows(path):
    with open(path,encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)):
            raise ValueError(f'bad CSV header: {path}')
        return list(reader)


def number(value):
    if value is None or value=='': return None
    x=float(value)
    if not math.isfinite(x): raise ValueError('nonfinite input')
    return x


def equal(a,b,tol=1e-9):
    if a is None or b is None: return a is None and b is None
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        return math.isclose(a,b,rel_tol=tol,abs_tol=tol)
    return a==b


def percentiles(members,key):
    groups=defaultdict(list)
    for r in members: groups[number(r[key])].append(r['code'])
    n=len(members); pos=0; result={}
    for value in sorted(groups):
        codes=groups[value]; pct=(pos+(len(codes)-1)/2)/(n-1) if n>1 else 1.
        for code in codes: result[code]=pct
        pos+=len(codes)
    return result


def targets(members,feature):
    """Build each method from independent sector ranks, preserving n/N."""
    grouped=defaultdict(list)
    for r in members: grouped[r['industry']].append(r)
    nall=len(members); out={m:{} for m in METHODS}; detail={}
    for sector, group in grouped.items():
        n=len(group); take=n if n<5 else math.ceil(n/5)
        m=percentiles(group,'momentum'); f=percentiles(group,feature)
        b={code:(m[code]+f[code])/2 for code in m}
        chosen={method:set(sorted(m, key=lambda code:(-score[code],code))[:take])
                for method,score in [('M',m),('F',f),('B',b)]}
        for r in group:
            c=r['code']; out['P'][c]=1/nall
            for method in 'MFB': out[method][c]=(n/nall/take) if c in chosen[method] else 0.
            detail[c]={'sector_n':n,'sector_selected_k':take,'tiny_no_selection':n<5,
                       'momentum_percentile':m[c],'financial_percentile':f[c],
                       'blend_percentile':b[c]}
    out['D']={c:(out['P'][c]+out['M'][c])/2 for c in out['P']}
    return out,detail


def stats(values):
    v=[x for x in values if x is not None]
    if not v: return {'status':'not_evaluated','defined_months':0,'mean':None,'sample_std':None,
                      'worst_month':None,'worst_10pct_mean':None}
    k=math.ceil(len(v)/10)
    return {'status':'evaluated','defined_months':len(v),'mean':sum(v)/len(v),
            'sample_std':statistics.stdev(v) if len(v)>1 else None,
            'worst_month':min(v),'worst_10pct_mean':sum(sorted(v)[:k])/k}


def quote_drawdown(ordered_monthly_returns):
    """Marked quote path only; None means an incomplete path, never a cash account."""
    if not ordered_monthly_returns or any(x is None for x in ordered_monthly_returns): return None
    wealth=peak=1.; worst=0.
    for gain in ordered_monthly_returns:
        wealth*=1+gain
        peak=max(peak,wealth)
        worst=min(worst,wealth/peak-1)
    return worst


def correlation(x,y):
    if len(x)!=len(y) or len(x)<3: return None
    ax=sum(x)/len(x); ay=sum(y)/len(y)
    vx=sum((v-ax)**2 for v in x);vy=sum((v-ay)**2 for v in y)
    if vx==0 or vy==0:return None
    return sum((a-ax)*(b-ay) for a,b in zip(x,y))/math.sqrt(vx*vy)


def score_spearman(pool,feature):
    if len(pool)<3:return None
    # Rank globally within the month's eligible pool, not separately per sector.
    m=percentiles(pool,'momentum'); f=percentiles(pool,feature)
    order=sorted(m)
    return correlation([m[c] for c in order],[f[c] for c in order])


def linear_quantile(sorted_values,p):
    loc=(len(sorted_values)-1)*p;lo=math.floor(loc);hi=math.ceil(loc)
    return sorted_values[lo]+(sorted_values[hi]-sorted_values[lo])*(loc-lo)


def resample_intervals(series_by_key, *, n_months=132, draws=10000, seed=20261019):
    """Independent circular month blocks, with one shared draw per measure."""
    if any(len(v)!=n_months for v in series_by_key.values()):raise ValueError('resampling series length mismatch')
    result={}
    for block in (6,12):
        rng=random.Random(seed); indices_hash=hashlib.sha256()
        sampled={key:[] for key in series_by_key}
        for _ in range(draws):
            positions=[]
            while len(positions)<n_months:
                start=rng.randrange(n_months)
                positions.extend((start+offset)%n_months for offset in range(block))
            positions=positions[:n_months]
            for pos in positions:indices_hash.update(struct.pack('>H',pos))
            for key,series in series_by_key.items():
                visible=[series[pos] for pos in positions if series[pos] is not None]
                if visible:sampled[key].append(sum(visible)/len(visible))
        for key,means in sampled.items():
            means.sort()
            for confidence in (.95,.975):
                tail=(1-confidence)/2
                result[key+(block,confidence)]={
                    'draws_requested':draws,'draws_valid':len(means),
                    'lower':linear_quantile(means,tail) if means else None,
                    'upper':linear_quantile(means,1-tail) if means else None,
                    'status':'evaluated' if means else 'not_evaluated',
                    'shared_index_sha256':indices_hash.hexdigest()}
    return result


def period(month,period):
    year=month[:4]
    if period=='all': return True
    if period=='2015-2019': return '2015'<=year<='2019'
    if period=='2020-2025': return '2020'<=year<='2025'
    if period.startswith('year-'): return year==period[5:]
    if period.startswith('without-'): return year!=period[8:]
    raise ValueError('unknown period')


class Audit:
    def __init__(self): self.counts=defaultdict(int); self.diffs=[]
    def check(self,area,key,field,actual,expected):
        self.counts[area]+=1
        if not equal(actual,expected):
            if len(self.diffs)<200: self.diffs.append({'area':area,'key':key,'field':field,'actual':actual,'expected':expected})
    def fields(self,area,key,actual,expected,names):
        for name in names: self.check(area,key,name,actual.get(name),expected.get(name))


def reconcile(contract_path,manifest_path):
    contract=json.loads(Path(contract_path).read_text()); manifest=json.loads(Path(manifest_path).read_text())
    if contract.get('schema')!='financial-evaluation-run/1' or manifest.get('schema')!='financial-evaluation-result/1':
        raise ValueError('contract/result schema mismatch')
    if digest(contract_path)!=manifest.get('contract_sha256') or manifest.get('inputs')!=contract['inputs']:
        raise ValueError('result is not bound to supplied evaluation contract')
    for name,item in contract['inputs'].items():
        if digest(item['path'])!=item['sha256']: raise ValueError(f'changed bound input: {name}')
    source=Path(manifest_path).resolve().parent
    if source!=Path(contract['output']['path']).resolve(): raise ValueError('result output path differs from contract')
    for name in FILES:
        item=manifest['outputs'][name]
        if digest(source/name)!=item['sha256'] or (source/name).stat().st_size!=item['bytes']:
            raise ValueError(f'changed result file: {name}')
    design=json.loads(Path(contract['inputs']['design']['path']).read_text())
    amendment=json.loads(Path(contract['inputs']['amendment']['path']).read_text())
    if design['selection']['fraction']!=.2 or design['reuse']['stock_count']!=600 or design['reuse']['monthly_decisions']!=132 or amendment['base_design_sha256']!=contract['inputs']['design']['sha256']:
        raise ValueError('unrecognized frozen statistical design')
    if set(design['selection']['methods'])!=set(METHODS): raise ValueError('method set changed')
    prices=rows(contract['inputs']['prices']['path']); panel=rows(contract['inputs']['panel']['path']); emitted=rows(source/'stock_weights.csv')
    pmap={(r['month'],r['code']):r for r in prices}; fmap={(r['month'],r['code']):r for r in panel}
    if len(prices)!=79200 or len(panel)!=79200 or len(pmap)!=79200 or set(pmap)!=set(fmap):
        raise ValueError('source cohort/month grid differs')
    months=sorted({m for m,c in pmap}); codes={c for m,c in pmap}
    if len(months)!=132 or len(codes)!=600: raise ValueError('source grid dimensions differ')
    saved={(r['scope'],r['month'],r['code']):r for r in emitted}
    if len(saved)!=len(emitted): raise ValueError('duplicate output stock weight')
    monthly=json.loads((source/'monthly.json').read_text()); mon={(r['scope'],r['month']):r for r in monthly}
    if len(mon)!=len(monthly): raise ValueError('duplicate output monthly row')
    performance=json.loads((source/'performance.json').read_text()); paired=json.loads((source/'paired.json').read_text())
    layers=json.loads((source/'qualification_layers.json').read_text()); layer={r['month']:r for r in layers}
    other=json.loads((source/'other_uses.json').read_text())
    audit=Audit(); reconstructed={}; expected_keys=set(); prior={scope:None for scope in SCOPES}
    other_acc=defaultdict(list)
    windows=['all','2015-2019','2020-2025']+[f'year-{y}' for y in range(2015,2026)]+[f'without-{y}' for y in range(2015,2026)]
    perf_keys={(scope,scenario,window,method) for scope in SCOPES for scenario in SCENARIOS
               for window in windows for method in METHODS}
    actual_perf=[(r['scope'],r['scenario'],r['period'],r['method']) for r in performance]
    audit.check('summary_membership','performance','missing_count',len(perf_keys-set(actual_perf)),0)
    audit.check('summary_membership','performance','extra_or_duplicate_count',len(actual_perf)-len(perf_keys & set(actual_perf)),0)
    pair_keys={(scope,scenario,window,f'{left}-{right}') for scope in SCOPES for scenario in SCENARIOS
               for window in windows for left,right in PAIRS}
    pair_keys|={('common_candidate',scenario,window,f'CFO_{method}-GP_{method}')
                for scenario in SCENARIOS for window in windows for method in 'FB'}
    actual_pairs=[(r['scope'],r['scenario'],r['period'],r['comparison']) for r in paired]
    audit.check('summary_membership','paired','missing_count',len(pair_keys-set(actual_pairs)),0)
    audit.check('summary_membership','paired','extra_or_duplicate_count',len(actual_pairs)-len(pair_keys & set(actual_pairs)),0)
    for month in months:
        gp=[]; common=[]; price_n=sector_n=0
        for code in codes:
            p=pmap[month,code]; f=fmap[month,code]
            if p['eligibility_reason']=='eligible': price_n+=1
            sector=f['industry']
            if p['eligibility_reason']!='eligible' or len(sector)!=3 or not sector[0].isalpha() or not sector[1:].isdigit() or sector.startswith('J'): continue
            sector_n+=1
            if f['gp_status']!='qualified': continue
            item={'code':code,'industry':sector,'momentum':p['momentum'],'gpa':f['gpa'],'cfoa':f['cfoa'],
                  'future':number(p['future_return']),'halt':p['either_halt']=='True','source':f}
            gp.append(item)
            if f['cfo_status']=='qualified': common.append(item)
        if month not in layer: raise ValueError('missing qualification layer')
        audit.fields('layer_counts',month,layer[month],{'original_600':600,'price_eligible':price_n,'sector_eligible':sector_n,'gp_pool':len(gp),'common_pool':len(common)},('original_600','price_eligible','sector_eligible','gp_pool','common_pool'))
        for scope,(feature,requires_cash) in SCOPES.items():
            pool=common if requires_cash else gp
            keys={(scope,month,r['code']) for r in pool};expected_keys.update(keys)
            if not pool:
                audit.check('empty_month',(scope,month),'monthly_absent',(scope,month) not in mon,True)
                prior[scope]=None
                continue
            weights,detail=targets(pool,feature)
            for r in pool:
                key=(scope,month,r['code']); savedrow=saved.get(key)
                if savedrow is None: audit.check('weight_membership',key,'present',False,True);continue
                audit.check('weight_membership',key,'present',True,True)
                for method in METHODS: audit.check('weights',key,'weight_'+method,number(savedrow['weight_'+method]),weights[method][r['code']])
                audit.fields('stock_source',key,savedrow,
                             {'industry':r['industry'],'report_year':r['source']['report_year'],
                              'announcement_id':r['source']['announcement_id'],
                              'publication_date':r['source']['publication_date'],
                              'financial_feature':feature,'either_halt':str(r['halt'])},
                             ('industry','report_year','announcement_id','publication_date',
                              'financial_feature','either_halt'))
                for name,expected in [('momentum',number(r['momentum'])),('financial_score',number(r[feature])),
                                      ('gpa',number(r['gpa'])),('cfoa',number(r['cfoa'])),
                                      ('future_return',r['future'])]:
                    audit.check('stock_source',key,name,number(savedrow[name]),expected)
                for name in ('sector_n','sector_selected_k','tiny_no_selection','momentum_percentile','financial_percentile','blend_percentile'):
                    value=savedrow[name]
                    parsed=(value=='True') if name=='tiny_no_selection' else (int(value) if name in ('sector_n','sector_selected_k') else number(value))
                    audit.check('ranks',key,name,parsed,detail[r['code']][name])
            actual=mon.get((scope,month))
            if actual is None: audit.check('monthly_presence',(scope,month),'present',False,True);continue
            exp={'pool_n':len(pool),'methods':{}}
            exp['spearman_financial_momentum']=score_spearman(pool,feature)
            for method in METHODS:
                w=weights[method]; unknown=sum(w[r['code']] for r in pool if r['future'] is None)
                halt=sum(w[r['code']] for r in pool if r['halt'])
                previous=prior[scope][method] if prior[scope] else None
                replacement=sum(abs(w.get(c,0)-previous.get(c,0)) for c in (set(w)|set(previous)))/2 if previous else None
                exp['methods'][method]={'unknown_weight':unknown,'either_halt_weight':halt,
                                        'holdings':sum(v>0 for v in w.values()),'max_weight':max(w.values()),
                                        'target_replacement':replacement}
                for scenario,missing in SCENARIOS.items():
                    exp['methods'][method][scenario]=sum(w[r['code']]*(missing if r['future'] is None else r['future']) for r in pool)
                audit.fields('monthly_methods',(scope,month,method),actual['methods'][method],exp['methods'][method],
                             ('unknown_weight','either_halt_weight','holdings','max_weight','target_replacement','unknown_minus_one','unknown_zero'))
                other_acc[scope,method].append(exp['methods'][method])
            prior[scope]=weights
            exp['overlap_F_M']=sum(min(weights['F'][c],weights['M'][c]) for c in weights['P'])
            exp['overlap_B_M']=sum(min(weights['B'][c],weights['M'][c]) for c in weights['P'])
            audit.fields('monthly_pool',(scope,month),actual,exp,
                         ('pool_n','overlap_F_M','overlap_B_M','spearman_financial_momentum'))
            reconstructed[scope,month]=exp
    audit.check('weight_membership','all','unexpected_count',len(set(saved)-expected_keys),0)
    audit.check('monthly_presence','all','unexpected_count',len(set(mon)-set(reconstructed)),0)
    for row in performance:
        scope,scenario,method,window=row['scope'],row['scenario'],row['method'],row['period']
        vals=[reconstructed.get((scope,m),{}).get('methods',{}).get(method,{}).get(scenario) for m in months if period(m,window)]
        expected=stats(vals); key=(scope,scenario,window,method)
        audit.fields('performance',key,row,expected,('status','defined_months','mean','sample_std','worst_month','worst_10pct_mean'))
        full=[reconstructed.get((scope,m),{}).get('methods',{}).get(method,{}).get(scenario) for m in months]
        drawdown=quote_drawdown(full) if window=='all' else None
        audit.check('quote_drawdown',key,'marked_quote_max_drawdown',row['marked_quote_max_drawdown'],drawdown)
        downs=[m for m in months if period(m,window) and reconstructed.get((scope,m),{}).get('methods',{}).get('P',{}).get(scenario,None) is not None and reconstructed[scope,m]['methods']['P'][scenario]<0]
        audit.check('p_down',key,'p_down_common_months',row['p_down_common_months'],len(downs))
        audit.check('p_down',key,'p_down_common_mean',row['p_down_common_mean'],stats([reconstructed[scope,m]['methods'][method][scenario] for m in downs])['mean'])
    for row in paired:
        scope,scenario,window,comparison=row['scope'],row['scenario'],row['period'],row['comparison']
        if scope=='common_candidate':
            left,right=comparison.split('-');method=left[-1]
            a_scope,b_scope='common_cfo','common_gp'
            p_scope='common_gp'
        else:
            left,right=comparison.split('-');method=None;a_scope=b_scope=p_scope=scope
        values=[];downvalues=[]
        for m in months:
            if not period(m,window): continue
            a=reconstructed.get((a_scope,m),{}).get('methods',{}).get(method or left,{}).get(scenario)
            b=reconstructed.get((b_scope,m),{}).get('methods',{}).get(method or right,{}).get(scenario)
            v=a-b if a is not None and b is not None else None;values.append(v)
            p=reconstructed.get((p_scope,m),{}).get('methods',{}).get('P',{}).get(scenario)
            if v is not None and p is not None and p<0: downvalues.append(v)
        key=(scope,scenario,window,comparison)
        audit.fields('paired',key,row,stats(values),('status','defined_months','mean','sample_std','worst_month','worst_10pct_mean'))
        audit.check('paired_p_down',key,'p_down_common_months',row['p_down_common_months'],len(downvalues))
        audit.check('paired_p_down',key,'p_down_common_mean',row['p_down_common_mean'],stats(downvalues)['mean'])
    for row in other:
        if row['scenario']!='all':
            scope=row['scope'];scenario=row['scenario'];both={}
            for left,right in [('F','M'),('B','M')]:
                xy=[(r['methods'][left][scenario],r['methods'][right][scenario])
                    for m in months if (r:=reconstructed.get((scope,m))) is not None]
                both[left]=correlation([x for x,y in xy],[y for x,y in xy])
                audit.check('other_correlations',(scope,scenario),f'corr_common_months_{left}_{right}',
                            row[f'corr_common_months_{left}_{right}'],len(xy))
                audit.check('other_correlations',(scope,scenario),f'return_corr_{left}_{right}',
                            row[f'return_corr_{left}_{right}'],both[left])
            continue
        scope=row['scope']; present=[reconstructed[scope,m] for m in months if (scope,m) in reconstructed]
        if not present: continue
        key=scope
        audit.check('other',key,'defined_months',row['defined_months'],len(present))
        audit.check('other',key,'mean_pool_n',row['mean_pool_n'],statistics.mean(r['pool_n'] for r in present))
        for name,field in [('mean_overlap_F_M','overlap_F_M'),('mean_overlap_B_M','overlap_B_M')]:
            audit.check('other',key,name,row[name],statistics.mean(r[field] for r in present))
        rho=[r['spearman_financial_momentum'] for r in present if r['spearman_financial_momentum'] is not None]
        audit.check('other',key,'mean_financial_momentum_spearman',row['mean_financial_momentum_spearman'],
                    statistics.mean(rho) if rho else None)
        for method in METHODS:
            series=other_acc[scope,method]; actual=row['method_uses'][method]
            for outfield,infield in [('mean_holdings','holdings'),('mean_max_weight','max_weight')]:
                audit.check('other',(scope,method),outfield,actual[outfield],statistics.mean(x[infield] for x in series))
            turnover=[x['target_replacement'] for x in series if x['target_replacement'] is not None]
            audit.check('other',(scope,method),'mean_target_replacement',actual['mean_target_replacement'],statistics.mean(turnover) if turnover else None)
    expected_other={(scope,scenario) for scope in SCOPES for scenario in ('all',*SCENARIOS)}
    actual_other=[(r['scope'],r['scenario']) for r in other]
    audit.check('summary_membership','other_uses','missing_count',len(expected_other-set(actual_other)),0)
    audit.check('summary_membership','other_uses','extra_or_duplicate_count',len(actual_other)-len(expected_other & set(actual_other)),0)
    series={}
    for scope in SCOPES:
        for scenario in SCENARIOS:
            for method in METHODS:
                series[scope,scenario,method]=[
                    reconstructed.get((scope,m),{}).get('methods',{}).get(method,{}).get(scenario)
                    for m in months]
            for left,right in PAIRS:
                a=series[scope,scenario,left];b=series[scope,scenario,right]
                series[scope,scenario,f'{left}-{right}']=[x-y if x is not None and y is not None else None
                                                           for x,y in zip(a,b)]
    for scenario in SCENARIOS:
        for method in 'FB':
            a=series['common_cfo',scenario,method];b=series['common_gp',scenario,method]
            series['common_candidate',scenario,f'CFO_{method}-GP_{method}']=[
                x-y if x is not None and y is not None else None for x,y in zip(a,b)]
    expected_intervals=resample_intervals(series)
    uncertainty=json.loads((source/'uncertainty.json').read_text())
    actual_interval_keys=[]
    for row in uncertainty:
        key=(row['scope'],row['scenario'],row['measure'],row['block_months'],row['confidence'])
        actual_interval_keys.append(key)
        if key in expected_intervals:
            audit.fields('uncertainty',key,row,expected_intervals[key],
                         ('draws_requested','draws_valid','lower','upper','status','shared_index_sha256'))
    audit.check('summary_membership','uncertainty','missing_count',len(set(expected_intervals)-set(actual_interval_keys)),0)
    audit.check('summary_membership','uncertainty','extra_or_duplicate_count',
                len(actual_interval_keys)-len(set(expected_intervals)&set(actual_interval_keys)),0)
    return {'schema':'independent-financial-effect-reconciliation/1','status':'matched_checked_fields' if not audit.diffs else 'differences_found',
            'evaluation_contract_sha256':digest(contract_path),'result_manifest_sha256':digest(manifest_path),
            'checks_by_area':dict(audit.counts),'differences_count_capped':len(audit.diffs),'differences':audit.diffs,
            'interpretation_limits':['Marked quote drawdown compounds selected monthly stock quotes; it is not an executable account wealth path.',
                                     'Low rank or return correlation describes difference in ordering/co-movement; it does not establish unique financial information or incremental investable value.'],
            'unverified':['announcement change count and reason_counts',
                          'actual human maintenance, trading fills, costs, portfolio wealth',
                          'old nine-group volatility/liquidity-conditioned competitor; this result only compares frozen simple within-industry momentum'],
            'scope':'one frozen result; no new performance experiment'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--evaluation-contract',type=Path,required=True)
    ap.add_argument('--result-manifest',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    contract=json.loads(args.evaluation_contract.read_text()); result=Path(args.result_manifest).resolve().parent
    out=args.out.resolve(); mount=Path(contract['output']['mount']).resolve()
    if (not os.path.ismount(mount) or result.stat().st_dev!=contract['output']['external_device'] or
        out.exists() or not out.parent.is_dir() or out.parent.stat().st_dev!=result.stat().st_dev or
        not out.is_relative_to(mount)):
        raise ValueError('create-only external output binding failed')
    audit=reconcile(args.evaluation_contract,args.result_manifest)
    out.mkdir()
    with (out/'independent-reconciliation.json').open('x') as f:
        json.dump(audit,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    print(json.dumps({'status':audit['status'],'out':str(out),'sha256':digest(out/'independent-reconciliation.json'),
                      'differences_count_capped':audit['differences_count_capped']},ensure_ascii=False))

if __name__=='__main__': main()
