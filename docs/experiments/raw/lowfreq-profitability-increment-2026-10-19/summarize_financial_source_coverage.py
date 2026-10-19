"""Offline, source-only final-panel adequacy summary; no market outcome columns.

CLI: --panel-contract FROZEN_FINANCIAL_PANEL_RUN_JSON --out NEW_EXTERNAL_DIR
Reads the contract's panel manifest, audit, progress, cohort, and a three-column
projection (month/code/eligibility_reason) of saved core price CSV. Every input
hash and output identity is verified before a create-only external write.
The retrospective outDate grouping describes coverage; it never filters a pool.
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
from datetime import date
from decimal import Decimal
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(1<<20),b''):h.update(part)
    return h.hexdigest()


def bound(item):
    if sha(item['path'])!=item['sha256']:raise ValueError(f'bound input changed: {item["path"]}')
    return Path(item['path'])


def projected_price(path):
    """csv.reader selects only availability columns; never materializes outcomes."""
    with Path(path).open(newline='',encoding='utf-8-sig') as f:
        reader=csv.reader(f);header=next(reader)
        names=('month','code','eligibility_reason')
        if len(header)!=len(set(header)) or not set(names)<=set(header):raise ValueError('price availability columns absent')
        positions=[header.index(n) for n in names]
        rows={}
        for values in reader:
            month,code,reason=(values[i] for i in positions)
            key=(month,code)
            if key in rows:raise ValueError('duplicate projected price key')
            rows[key]=reason
    return rows


def opportunity(sector_scores):
    """sector -> score list; no ranks or outcome data used."""
    groups={sector:list(values) for sector,values in sector_scores.items()}
    n=sum(len(v) for v in groups.values())
    if n==0:return {'pool_n':0,'tiny_hold_all_mass':None,'selectable_mass':None,
                    'selected_slots':0,'selected_fraction':None,'nonconstant_weight':None}
    tiny=sum(len(v) for v in groups.values() if len(v)<5)
    selected=sum(len(v) if len(v)<5 else math.ceil(len(v)/5) for v in groups.values())
    nonconstant=sum(len(v) for v in groups.values() if len(v)>=5 and len({Decimal(x) for x in v})>1)
    return {'pool_n':n,'tiny_hold_all_mass':tiny/n,'selectable_mass':(n-tiny)/n,
            'selected_slots':selected,'selected_fraction':selected/n,
            'nonconstant_weight':nonconstant/n}


def median(values):return statistics.median(values) if values else None


def pool_flags(price_reason,panel_row):
    sector=panel_row['industry']
    base=(price_reason=='eligible' and re.fullmatch(r'[A-Z]\d{2}',sector) is not None
          and not sector.startswith('J'))
    gp=base and panel_row['gp_status']=='qualified'
    common=gp and panel_row['cfo_status']=='qualified'
    return base,gp,common


def validate_qualified_dates(result,decision_date):
    if result['status']!='qualified':return
    publication=date.fromisoformat(result['publication_date'])
    decision=date.fromisoformat(decision_date)
    fiscal_year=int(result['report_year'])
    age=(decision.year-fiscal_year)*12+decision.month-12
    if not publication<decision or not 1<=age<=16:
        raise ValueError('qualified source publication/16-month age invalid')


def validate_recovery_evidence(result,decision_date):
    """A prior unreviewed notice may recover a later measurement, not truth."""
    flags=[v for v in result.get('recovery_evidence',[])
           if v.get('reason')=='measurement_recovered_with_unreviewed_prior_notice']
    for item in flags:
        if (result['status'] not in {'qualified','unknown'} or
            (result['status']=='unknown' and not result.get('reason')) or
            item.get('notice_review_status')!='unreviewed' or
            item.get('financial_authenticity_certified') is not False):
            raise ValueError('recovery flag recharacterized')
        notice=date.fromisoformat(item['publication_date'])
        fiscal_end=date.fromisoformat(item['annual_fiscal_end'])
        current=date.fromisoformat(item['annual_publication_date'])
        decision=date.fromisoformat(decision_date)
        fiscal_year=int(result['report_year'])
        annual_ids=set(item.get('annual_announcement_ids',[]))
        current_ids=set(result.get('announcement_ids',[]))
        if (current!=date.fromisoformat(result['publication_date']) or
            fiscal_end!=date(fiscal_year,12,31) or not annual_ids.intersection(current_ids) or
            not notice<fiscal_end or not notice<current or not current<decision):
            raise ValueError('recovery source date ordering invalid')
    return flags


def catalog_states(progress,cohort_codes):
    states={};counts=Counter()
    for code in cohort_codes:
        raw=progress.get('codes',{}).get(code.split('.')[1],{})
        annual=str(raw.get('catalogs',{}).get('annual',{}).get('status') or 'missing')
        correction=str(raw.get('catalogs',{}).get('correction',{}).get('status') or 'missing')
        status=str(raw.get('status') or 'missing')
        complete=annual.startswith('complete') and correction.startswith('complete')
        states[code]={'code_status':status,'annual_catalog_status':annual,
                      'correction_catalog_status':correction,'both_catalogs_complete':complete}
        counts['code:'+status]+=1;counts['annual:'+annual]+=1;counts['correction:'+correction]+=1
        counts['both_complete' if complete else 'either_incomplete']+=1
    return states,dict(sorted(counts.items()))


def source_state_summary(states,state_counts):
    complete=(state_counts.get('both_complete',0)==len(states) and
              all(v['code_status']=='complete' for v in states.values()))
    terminal=all(v['code_status'] in {'complete','incomplete'} for v in states.values())
    label=('sources_complete_attempts_terminal' if complete else
           'sources_incomplete_attempts_terminal' if terminal else 'attempts_pending')
    return label,{'all_codes_fully_complete':complete,
                  'both_catalog_complete_count':state_counts.get('both_complete',0)},\
           {'terminal':terminal,'terminal_code_statuses':['complete','incomplete'],
            'pending_or_running_or_missing_codes':sum(v['code_status'] not in {'complete','incomplete'} for v in states.values())}


def summarize(contract_path):
    contract_path=Path(contract_path).resolve();spec=json.loads(contract_path.read_text())
    if spec.get('schema')!='financial-panel-run/1':raise ValueError('wrong panel contract schema')
    inputs=spec['inputs']
    for key,item in inputs.items():
        if key=='preparation':
            for one in (item if isinstance(item,list) else [item]):bound(one)
        else:bound(item)
    outpath=Path(spec['output']['path']).resolve();manifest_path=outpath/'manifest.json'
    manifest=json.loads(manifest_path.read_text())
    if (manifest.get('schema')!='financial-panel-result/1' or
        manifest.get('contract_sha256')!=sha(contract_path) or manifest.get('inputs')!=inputs):
        raise ValueError('panel manifest lineage mismatch')
    for name,hashvalue in manifest['outputs'].items():
        if sha(outpath/name)!=hashvalue:raise ValueError(f'panel result changed: {name}')
    cohort=json.loads(Path(inputs['cohort']['path']).read_text())
    codes=cohort['fixed_codes'];code_set=set(codes)
    if len(codes)!=600 or len(code_set)!=600:raise ValueError('cohort not exact600')
    source_cohort=cohort['source_cohort'];bound(source_cohort)
    rawcohort=json.loads(Path(source_cohort['path']).read_text())
    fields=rawcohort['fields'];idx={field:fields.index(field) for field in ('code','outDate')}
    metadata={row[idx['code']]:row[idx['outDate']] for row in rawcohort['data'] if row[idx['code']] in code_set}
    if set(metadata)!=code_set:raise ValueError('original cohort metadata missing codes')
    attrition={code:('known_outDate_by_2025_12_31' if value and value<='2025-12-31'
                     else 'no_known_outDate_by_2025_12_31') for code,value in metadata.items()}
    attrition_code_counts=Counter(attrition.values())
    price=projected_price(inputs['price_calendar']['path'])
    panel={};months=set()
    with (outpath/'panel.csv').open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        required={'month','decision_date','code','industry','gp_status','gpa','cfo_status','cfoa','reason'}
        if not required<=set(reader.fieldnames or []):raise ValueError('panel columns absent')
        for row in reader:
            key=(row['month'],row['code'])
            if key in panel or row['code'] not in code_set:raise ValueError('panel key duplicate/outside cohort')
            panel[key]=row;months.add(row['month'])
    if len(months)!=132 or len(panel)!=79200 or set(price)!=set(panel):raise ValueError('panel/price not same600x132')
    progress=json.loads(Path(inputs['progress']['path']).read_text())
    states,state_counts=catalog_states(progress,codes)
    audit=json.loads((outpath/'audit.json').read_text())
    amap={(r['month'],r['code']):r for r in audit}
    if len(amap)!=79200 or len(audit)!=79200 or set(amap)!=set(panel):raise ValueError('audit key grid mismatch')
    monthly=[];industry=defaultdict(Counter);groups=defaultdict(Counter)
    recover={'gp_rows':0,'common_rows':0,'gp_recovered_rows':0,'common_recovered_rows':0,
             'gp_recovery_evidence_count':0,'common_recovery_evidence_count':0}
    for month in sorted(months):
        base=gp=common=0;gp_sectors=defaultdict(list);common_gp_sectors=defaultdict(list);cash_sectors=defaultdict(list)
        for code in codes:
            key=(month,code);p=panel[key];a=amap[key];s=states[code]
            if p['decision_date']!=a['decision_date']:raise ValueError('audit decision date mismatch')
            if (p['gp_status']!=a['gp']['status'] or p['cfo_status']!=a['cfo']['status'] or
                (p['gp_status']=='qualified' and Decimal(p['gpa'])!=Decimal(a['gp']['value'])) or
                (p['cfo_status']=='qualified' and Decimal(p['cfoa'])!=Decimal(a['cfo']['value']))):
                raise ValueError('audit field status mismatch')
            validate_qualified_dates(a['gp'],p['decision_date'])
            validate_qualified_dates(a['cfo'],p['decision_date'])
            gp_flags=validate_recovery_evidence(a['gp'],p['decision_date'])
            cfo_flags=validate_recovery_evidence(a['cfo'],p['decision_date'])
            sector=p['industry']
            base_ok,gp_ok,common_ok=pool_flags(price[key],p)
            if base_ok:base+=1
            if gp_ok:gp+=1;gp_sectors[sector].append(p['gpa'])
            if common_ok:
                common+=1;common_gp_sectors[sector].append(p['gpa']);cash_sectors[sector].append(p['cfoa'])
            group=groups[attrition[code]];group['all_rows']+=1
            if base_ok:
                group['price_industry_base_rows']+=1
                if s['both_catalogs_complete']:group['catalog_covered_base_rows']+=1
                sector_group=industry[sector];sector_group['base_rows']+=1
                if s['both_catalogs_complete']:sector_group['catalog_covered_base_rows']+=1
            if gp_ok:group['gp_rows']+=1;industry[sector]['gp_rows']+=1
            if common_ok:group['common_rows']+=1;industry[sector]['common_rows']+=1
            if gp_ok:
                recover['gp_rows']+=1
                flags=gp_flags
                if flags:
                    recover['gp_recovered_rows']+=1;recover['gp_recovery_evidence_count']+=len(flags)
            if common_ok:
                recover['common_rows']+=1
                flags=gp_flags+cfo_flags
                if flags:
                    recover['common_recovered_rows']+=1;recover['common_recovery_evidence_count']+=len(flags)
        gp_op=opportunity(gp_sectors);cash_op=opportunity(cash_sectors)
        if not 0<=common<=gp<=base<=600:raise ValueError('monthly pool inequality violated')
        monthly.append({'month':month,'price_industry_base_n':base,'gp_pool_n':gp,'common_pool_n':common,
                        'gp_opportunity':gp_op,'common_gp_opportunity':opportunity(common_gp_sectors),
                        'common_cfo_opportunity':cash_op})
    if any(recover[k]>recover[base] for k,base in [('gp_recovered_rows','gp_rows'),('common_recovered_rows','common_rows')]):
        raise ValueError('recovered rows exceed pool rows')
    for group in groups.values():
        if not 0<=group['common_rows']<=group['gp_rows']<=group['catalog_covered_base_rows']<=group['price_industry_base_rows']<=group['all_rows']:
            raise ValueError('attrition coverage inequality violated')
        denom=group['catalog_covered_base_rows'];group['common_over_catalog_covered_base']=group['common_rows']/denom if denom else None
    for label,count in attrition_code_counts.items():groups[label]['fixed_cohort_codes']=count
    for group in industry.values():
        if not 0<=group['common_rows']<=group['gp_rows']<=group['catalog_covered_base_rows']<=group['base_rows']:
            raise ValueError('industry coverage inequality violated')
        denom=group['catalog_covered_base_rows'];group['common_over_catalog_covered_base']=group['common_rows']/denom if denom else None
    yearly={}
    for year in sorted({m['month'][:4] for m in monthly}):
        records=[m for m in monthly if m['month'].startswith(year)]
        yearly[year]={scope:{field:median([m[key][field] for m in records if m[key][field] is not None])
                             for field in ('pool_n','tiny_hold_all_mass','selected_fraction','nonconstant_weight')}
                       for scope,key in [('gp','gp_opportunity'),('common_gp','common_gp_opportunity'),('common_cfo','common_cfo_opportunity')]}
    status,completeness,attempt_state=source_state_summary(states,state_counts)
    return {'schema':'financial-source-coverage-summary/1','status':status,
            'source_completeness':completeness,'attempt_state':attempt_state,
            'market_outcomes_read':False,'effect_run':False,'panel_contract_sha256':sha(contract_path),
            'panel_manifest_sha256':sha(manifest_path),'bound_input_sha256':{k:([v['sha256'] for v in item] if isinstance(item,list) else item['sha256']) for k,item in inputs.items()},
            'original_cohort_source_sha256':source_cohort['sha256'],'shape':{'codes':600,'months':132,'stock_months':79200},
            'source_code_state_counts':state_counts,'source_code_states':states,'monthly':monthly,'yearly_medians':yearly,
            'exit_metadata_attrition':dict(sorted(groups.items())),'industry_coverage':dict(sorted(industry.items())),
            'v2_measurement_recovery':{**recover,'gp_recovered_row_share':recover['gp_recovered_rows']/recover['gp_rows'] if recover['gp_rows'] else None,
                                       'common_recovered_row_share':recover['common_recovered_rows']/recover['common_rows'] if recover['common_rows'] else None},
            'interpretation':'Source sufficiency and selection opportunity only. outDate is retrospective description, never eligibility. Recovery flags are unreviewed-prior measurement permissions, not notice clearance or financial authenticity. No return advantage is calculated.'}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--panel-contract',required=True,type=Path);cli.add_argument('--out',required=True,type=Path)
    args=cli.parse_args();spec=json.loads(args.panel_contract.read_text());source=Path(spec['output']['path']).resolve()
    target=args.out.resolve();mount=Path(spec['output']['mount']).resolve();device=spec['output']['external_device']
    if (not os.path.ismount(mount) or mount.stat().st_dev!=device or source.stat().st_dev!=device or
        target.exists() or not target.parent.is_dir() or target.parent.stat().st_dev!=device or not target.is_relative_to(mount)):
        raise ValueError('create-only external output binding failed')
    result=summarize(args.panel_contract)
    target.mkdir()
    with (target/'source-coverage.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    print(json.dumps({'status':result['status'],'path':str(target),'sha256':sha(target/'source-coverage.json')},ensure_ascii=False))

if __name__=='__main__':main()
