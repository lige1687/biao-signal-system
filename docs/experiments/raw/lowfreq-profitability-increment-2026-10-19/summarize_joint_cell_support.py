"""Decision-time support audit for fixed industry x old nested-nine groups.

CLI: --panel-contract FINAL_FINANCIAL_PANEL_RUN_JSON --out NEW_EXTERNAL_DIR
The price reader retains only month, code, eligibility_reason, momentum, vol60,
and amount20. It never selects returns, halt flags, or any outcome statistic.
All weights are diagnostic targets; no effect comparison is run here.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

PRICE_COLUMNS=('month','code','eligibility_reason','momentum','vol60','amount20')
PANEL_COLUMNS=('month','code','industry','gp_status','gpa','cfo_status','cfoa')
SCOPES={'gp':('gpa',False),'common_gp':('gpa',True),'common_cfo':('cfoa',True)}
METHODS=('P','M','B','D')
SECTOR=re.compile(r'^[A-Z]\d{2}$')
REVIEW_SHA='16538c73dbd13e8bbdc9f2cd576d79c71bbd6a0e8ac07610ae0d4b8c16e1267f'
CONTROLLER_SHA='5047692cc4ee299fb1b194b999c4c4202168b9af71a2f162ff5f5c886080df5f'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for piece in iter(lambda:f.read(1<<20),b''):h.update(piece)
    return h.hexdigest()


def project_csv(path,columns):
    """Only named decision-time columns are retained from parsed CSV records."""
    with Path(path).open(newline='',encoding='utf-8-sig') as f:
        reader=csv.reader(f);names=next(reader)
        if len(names)!=len(set(names)) or not set(columns)<=set(names):raise ValueError('required source columns absent/duplicated')
        take=[names.index(name) for name in columns]
        result={}
        for values in reader:
            projected=dict(zip(columns,(values[i] for i in take)))
            key=projected['month'],projected['code']
            if key in result:raise ValueError('duplicate month/code')
            result[key]=projected
    return result


def finite(value):
    x=float(value)
    if not math.isfinite(x):raise ValueError('nonfinite decision feature')
    return x


def thirds(sorted_items):
    """Contiguous thirds, assigning one remainder item to each early group."""
    base,remainder=divmod(len(sorted_items),3);start=0;out=[]
    for group in range(3):
        stop=start+base+(group<remainder)
        out.append(sorted_items[start:stop]);start=stop
    return out


def old_nine(pool):
    if len({r['code'] for r in pool})!=len(pool):raise ValueError('duplicate security in pool')
    result={}
    for vi,vol_group in enumerate(thirds(sorted(pool,key=lambda r:(r['vol60'],r['code']))),1):
        for li,amount_group in enumerate(thirds(sorted(vol_group,key=lambda r:(r['amount20'],r['code']))),1):
            for row in amount_group:result[row['code']]=(vi,li)
    if len(result)!=len(pool):raise AssertionError('nested thirds lost security')
    return result


def mean_tied_ranks(members,feature):
    buckets=defaultdict(list)
    for row in members:buckets[row[feature]].append(row['code'])
    n=len(members);rank={};before=0
    for value in sorted(buckets):
        size=len(buckets[value]);p=(before+(size-1)/2)/(n-1) if n>1 else 1.
        for code in buckets[value]:rank[code]=p
        before+=size
    return rank


def joint_diagnostics(pool):
    """Returns weights and source support; no future outcomes enter this function."""
    nall=len(pool)
    if not nall:return {'pool_n':0,'cells':[],'weights':{m:{} for m in METHODS},
                        'old_nine_cell_sizes':{f'{v}-{a}':0 for v in range(1,4) for a in range(1,4)},
                        'joint_cell_count':0,'joint_cell_size_counts':{},
                        'tiny_hold_all_weight':None,'n_ge_5_weight':None,
                        'nonconstant_financial_weight':None,'actual_changed_joint_cell_weight':None,
                        'actual_B_minus_M_weight_change_mass':None,'selected_counts':{m:0 for m in METHODS},
                        'max_stock_weight':{m:None for m in METHODS},'share_max_abs_error':None}
    positions=old_nine(pool);by_joint=defaultdict(list)
    old_sizes=Counter(positions.values())
    for row in pool:by_joint[(row['industry'],*positions[row['code']])].append(row)
    weights={m:{} for m in METHODS};cells=[]
    for joint,members in sorted(by_joint.items()):
        count=len(members);k=count if count<5 else math.ceil(count/5)
        momentum=mean_tied_ranks(members,'momentum')
        financial=mean_tied_ranks(members,'financial')
        blend={c:(momentum[c]+financial[c])/2 for c in momentum}
        m_chosen={c for c in sorted(momentum,key=lambda c:(-momentum[c],c))[:k]}
        b_chosen={c for c in sorted(blend,key=lambda c:(-blend[c],c))[:k]}
        share=count/nall
        for row in members:
            code=row['code'];weights['P'][code]=1/nall
            weights['M'][code]=share/k if code in m_chosen else 0.
            weights['B'][code]=share/k if code in b_chosen else 0.
        cells.append({'industry':joint[0],'vol_group':joint[1],'amount_group':joint[2],
                      'n':count,'share':share,'tiny_hold_all':count<5,
                      'selected_slots_M':k,'selected_slots_B':k,
                      'financial_nonconstant':count>=5 and len({r['financial'] for r in members})>1,
                      'B_differs_from_M':b_chosen!=m_chosen})
    weights['D']={c:(weights['P'][c]+weights['M'][c])/2 for c in weights['P']}
    tiny=sum(cell['share'] for cell in cells if cell['tiny_hold_all'])
    nonconstant=sum(cell['share'] for cell in cells if cell['financial_nonconstant'])
    changed=sum(cell['share'] for cell in cells if cell['B_differs_from_M'])
    change_mass=sum(abs(weights['B'][c]-weights['M'][c]) for c in weights['P'])/2
    # P, M, B and D must preserve both original nine-cell and industry shares.
    expected_industry=Counter(r['industry'] for r in pool)
    expected_nine=Counter(positions[r['code']] for r in pool)
    error=0.
    for method in METHODS:
        w=weights[method]
        if abs(sum(w.values())-1)>1e-10:raise ValueError('target total not one')
        for industry,count in expected_industry.items():
            error=max(error,abs(sum(w[r['code']] for r in pool if r['industry']==industry)-count/nall))
        for nine,count in expected_nine.items():
            error=max(error,abs(sum(w[r['code']] for r in pool if positions[r['code']]==nine)-count/nall))
    if error>1e-10:raise ValueError('industry/nine-cell share drift')
    return {'pool_n':nall,'cells':cells,'weights':weights,
            'old_nine_cell_sizes':{f'{v}-{a}':old_sizes[v,a] for v in range(1,4) for a in range(1,4)},
            'joint_cell_count':len(cells),'joint_cell_size_counts':dict(sorted(Counter(c['n'] for c in cells).items())),
            'tiny_hold_all_weight':tiny,'n_ge_5_weight':1-tiny,
            'nonconstant_financial_weight':nonconstant,'actual_changed_joint_cell_weight':changed,
            'actual_B_minus_M_weight_change_mass':change_mass,
            'selected_counts':{m:sum(value>0 for value in weights[m].values()) for m in METHODS},
            'max_stock_weight':{m:max(weights[m].values()) for m in METHODS},
            'share_max_abs_error':error}


def summarize(contract_path):
    contract_path=Path(contract_path).resolve();spec=json.loads(contract_path.read_text())
    if spec.get('schema')!='financial-panel-run/1':raise ValueError('wrong panel contract schema')
    basis=Path(__file__).resolve().parent
    if (sha(basis/'existing-information-boundary-review.json')!=REVIEW_SHA or
        sha(basis/'existing-information-controller-decision.json')!=CONTROLLER_SHA):
        raise ValueError('existing-information method decision changed')
    bound=spec['inputs']
    for name,item in bound.items():
        for one in (item if isinstance(item,list) else [item]):
            if sha(one['path'])!=one['sha256']:raise ValueError(f'changed panel contract input: {name}')
    source=Path(spec['output']['path']).resolve();manifest=source/'manifest.json';m=json.loads(manifest.read_text())
    if (m.get('schema')!='financial-panel-result/1' or m.get('contract_sha256')!=sha(contract_path)
        or m.get('inputs')!=bound):raise ValueError('panel manifest lineage changed')
    for name,expected in m['outputs'].items():
        if sha(source/name)!=expected:raise ValueError(f'panel output changed: {name}')
    cohort=json.loads(Path(bound['cohort']['path']).read_text());codes=cohort['fixed_codes']
    if len(codes)!=600 or len(set(codes))!=600:raise ValueError('fixed 600 invalid')
    if Path(bound['price_calendar']['path']).resolve()!=(Path(cohort['price_quality_path']).parent/'per_stock_month.csv').resolve():
        raise ValueError('price input not original saved core')
    if sha(cohort['price_quality_path'])!=cohort['price_quality_sha256']:raise ValueError('price quality binding changed')
    price=project_csv(bound['price_calendar']['path'],PRICE_COLUMNS)
    panel=project_csv(source/'panel.csv',PANEL_COLUMNS)
    months=sorted({month for month,code in price});expected={(month,code) for month in months for code in codes}
    if (len(months)!=132 or len(price)!=79200 or len(panel)!=79200 or
        set(price)!=expected or set(panel)!=expected):raise ValueError('price/panel grid not exact 600 x 132')
    monthly=[];yearly=defaultdict(list)
    for month in months:
        gp=[];common=[]
        common_targets=None
        for code in codes:
            p=price[month,code];f=panel[month,code]
            if p['eligibility_reason']!='eligible' or not SECTOR.fullmatch(f['industry']) or f['industry'].startswith('J'):
                continue
            if f['gp_status']!='qualified':continue
            record={'code':code,'industry':f['industry'],'momentum':finite(p['momentum']),
                    'vol60':finite(p['vol60']),'amount20':finite(p['amount20']),
                    'gpa':finite(f['gpa']),'cfoa':finite(f['cfoa']) if f['cfo_status']=='qualified' else None}
            gp.append(record)
            if f['cfo_status']=='qualified':common.append(record)
        for scope,(field,needs_cash) in SCOPES.items():
            chosen=common if needs_cash else gp
            scored=[{**r,'financial':r[field]} for r in chosen]
            result=joint_diagnostics(scored)
            weights=result.pop('weights')
            # Confirm same pool and target baseline across the two financial candidates.
            if scope=='common_gp':common_targets={m:weights[m] for m in ('P','M','D')}
            if scope=='common_cfo':
                earlier=next(r for r in monthly[-2:] if r['month']==month and r['scope']=='common_gp')
                if result['pool_n']!=earlier['pool_n'] or result['selected_counts']['P']!=earlier['selected_counts']['P']:
                    raise ValueError('GP/CFO common pool differs')
                if any(weights[m]!=common_targets[m] for m in ('P','M','D')):
                    raise ValueError('GP/CFO common-pool baseline weights differ')
            row={'month':month,'scope':scope,**result}
            monthly.append(row);yearly[(month[:4],scope)].append(row)
    years={}
    for (year,scope),values in sorted(yearly.items()):
        years.setdefault(year,{})[scope]={name:statistics.median([r[name] for r in values if r[name] is not None])
                if any(r[name] is not None for r in values) else None
                for name in ('pool_n','tiny_hold_all_weight','n_ge_5_weight',
                             'nonconstant_financial_weight','actual_changed_joint_cell_weight',
                             'actual_B_minus_M_weight_change_mass')}
    return {'schema':'financial-joint-cell-support/1','status':'source_only_no_effect_run',
            'panel_contract_sha256':sha(contract_path),'panel_manifest_sha256':sha(manifest),
            'helper_sha256':sha(__file__),'method_review_sha256':REVIEW_SHA,
            'controller_decision_sha256':CONTROLLER_SHA,
            'bound_input_sha256':{k:[x['sha256'] for x in v] if isinstance(v,list) else v['sha256'] for k,v in bound.items()},
            'projected_price_fields':list(PRICE_COLUMNS),'projected_panel_fields':list(PANEL_COLUMNS),
            'shape':{'fixed_codes':600,'months':132,'scope_months':len(monthly)},
            'monthly':monthly,'yearly_medians':years,
            'interpretation':['Tiny-cell weight is the fraction of target portfolio held in n<5 cells, not cash exposure.',
                              'B-M target weight change describes ability to distinguish lists; no return or risk effect is measured.',
                              'This joint-cell audit does not authorize a stronger-information effect experiment.']}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--panel-contract',required=True,type=Path);cli.add_argument('--out',required=True,type=Path)
    args=cli.parse_args();spec=json.loads(args.panel_contract.read_text());out=args.out.resolve();mount=Path(spec['output']['mount']).resolve();source=Path(spec['output']['path']).resolve();device=spec['output']['external_device']
    if (not os.path.ismount(mount) or mount.stat().st_dev!=device or source.stat().st_dev!=device or
        out.exists() or not out.parent.is_dir() or out.parent.stat().st_dev!=device or not out.is_relative_to(mount)):
        raise ValueError('create-only external output binding failed')
    result=summarize(args.panel_contract)
    out.mkdir()
    with (out/'joint-cell-support.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    print(json.dumps({'status':result['status'],'out':str(out),'sha256':sha(out/'joint-cell-support.json')},ensure_ascii=False))

if __name__=='__main__':main()
