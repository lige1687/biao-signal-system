#!/usr/bin/env python3
"""Structural qualification of reported annual operating income and permanent equity.

This does not calculate a profitability ratio, factor score, return, or historical issuer identity.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, os, re, shutil, subprocess
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

FLOW_TAGS = {'OperatingIncomeLoss', 'InterestExpense', 'InterestAndDebtExpense', 'InterestExpenseDebt', 'InterestExpenseNonOperating'}
BS_TAGS = {'Assets','Liabilities','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
           'PreferredStockValue','PreferredStockValueOutstanding','PreferredStockCarryingValue','PreferredStockRedemptionValue',
           'StockholdersEquity','MinorityInterest','RedeemableNoncontrollingInterestEquityCarryingAmount'}
INTEREST_TAGS = {'InterestExpense','InterestAndDebtExpense','InterestExpenseDebt','InterestExpenseNonOperating'}
PREFERRED_TAGS = {'PreferredStockValue','PreferredStockValueOutstanding','PreferredStockCarryingValue','PreferredStockRedemptionValue'}
INCLUSIVE='StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'
TEMP_RE = re.compile(r'(?:TemporaryEquity|Redeemable.*(?:Equity|Interest).*(?:Amount|Value|Carrying)|(?:Equity|Interest).*Redeemable.*(?:Amount|Value|Carrying))', re.I)

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def read_csv(path):
    with open(path,encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def finite_decimal(value):
    if value is None or str(value).strip()=='': return None
    try:
        d=Decimal(str(value).strip())
        return d if d.is_finite() else None
    except (InvalidOperation, ValueError): return None

def standard(row):
    return str(row.get('version','')).startswith('us-gaap/')

def eligible_fact(row, sub, tags, qtrs):
    return (row.get('adsh')==sub.get('adsh') and row.get('tag') in tags and standard(row)
        and row.get('ddate')==str(sub.get('period','')).replace('-','')
        and row.get('qtrs')==str(qtrs) and row.get('uom')=='USD'
        and not row.get('segments','').strip() and not row.get('coreg','').strip()
        and finite_decimal(row.get('value')) is not None)

def pres_rows(pres, adsh, tag, version, stmt):
    return [p for p in pres if p.get('adsh')==adsh and p.get('tag')==tag and p.get('version')==version
            and p.get('stmt')==stmt and p.get('inpth')=='0']

def fact_evidence(row, pres, stmt):
    matches=pres_rows(pres,row.get('adsh'),row.get('tag'),row.get('version'),stmt)
    return [{k:p.get(k) for k in ('report','line','stmt','inpth','tag','version','plabel')} for p in matches]

def candidate_facts(sub, facts):
    return [r for r in facts if r.get('adsh')==sub.get('adsh')]

def qualify_filing(sub, facts, pres):
    reasons=[]; steps={}; eligible=True
    def check(name,ok,why):
        nonlocal eligible
        steps[name]={'passed':bool(ok),'reason':why}
        if not ok: eligible=False; reasons.append(f'{name}: {why}')
    formok=sub.get('form') in ('10-K','10-K/A') and sub.get('fp')=='FY'
    check('filing_type_period',formok,'requires 10-K/10-K/A and fp=FY' if not formok else 'matched')
    try: sic=int(sub.get('sic') or '')
    except ValueError: sic=-1
    sicok=not (6000<=sic<=6999) and sic>=0
    check('sic',sicok,'financial SIC 6000-6999 or missing/invalid' if not sicok else 'nonfinancial SIC')
    period=str(sub.get('period','')).replace('-','')
    dateok=bool(re.fullmatch(r'\d{8}',period))
    check('period_date',dateok,'period must be an 8-digit filing date' if not dateok else 'NUM.ddate must equal SUB.period')
    rows=candidate_facts(sub,facts)
    # Only standard, exact-period, undimensioned finite source amounts are considered.
    def pick(tagset,qtrs,stmt, exact_tag=None):
        chosen=[]
        for row in rows:
            if not eligible_fact(row,sub,tagset,qtrs): continue
            if exact_tag and row.get('tag')!=exact_tag: continue
            p=fact_evidence(row,pres,stmt)
            if p: 
                rr=dict(row); rr['_presentation']=p; chosen.append(rr)
        return chosen
    oi=pick({'OperatingIncomeLoss'},4,'IS')
    oi_values={finite_decimal(r['value']) for r in oi}
    oi_unique=len(oi_values)==1
    check('operating_income',oi_unique,'requires one finite standard OperatingIncomeLoss in main IS' if not oi_unique else 'unique finite amount')
    oi_line=None; oi_report=None
    if oi_unique:
        oirow=oi[0]; oi_line=min((int(p['line']) for p in oirow['_presentation'] if str(p.get('line','')).isdigit()),default=None)
        oi_report=oirow['_presentation'][0]['report']
    interest=[]
    for row in rows:
        if not eligible_fact(row,sub,INTEREST_TAGS,4): continue
        for p in fact_evidence(row,pres,'IS'):
            if p.get('report')==oi_report and oi_line is not None and str(p.get('line','')).isdigit() and int(p['line'])>oi_line:
                rr=dict(row);rr['_presentation']=[p];interest.append(rr)
    ivals={finite_decimal(r['value']) for r in interest}
    interest_unique=bool(interest) and len(ivals)==1
    check('interest',interest_unique,'requires finite listed interest tag on same IS report after OI; all finite values must agree' if not interest_unique else 'same-report line after OI; unique amount')
    def unique_bs(tag):
        candidates=pick({tag},0,'BS')
        vals={finite_decimal(r['value']) for r in candidates}
        return candidates, vals
    bs={}; bsvals={}
    for tag in ('Assets','Liabilities',INCLUSIVE):
        bs[tag],bsvals[tag]=unique_bs(tag)
        check('balance_'+tag,len(bsvals[tag])==1,'requires one finite standard BS amount' if len(bsvals[tag])!=1 else 'unique finite amount')
    balance_ok=False; equity=None
    if all(len(bsvals[t])==1 for t in ('Assets','Liabilities',INCLUSIVE)):
        a=next(iter(bsvals['Assets']));l=next(iter(bsvals['Liabilities']));equity=next(iter(bsvals[INCLUSIVE]));balance_ok=(a==l+equity)
    check('balance_identity',balance_ok,'Assets must equal Liabilities plus inclusive equity exactly' if not balance_ok else 'exact identity')
    positive=equity is not None and equity>0
    check('positive_inclusive_equity',positive,'inclusive equity must be positive' if not positive else 'positive')
    pref=pick(PREFERRED_TAGS,0,'BS')
    pref_present=bool(pref); pref_zero=pref_present and all(finite_decimal(r['value'])==0 for r in pref)
    check('preferred_total',pref_zero,'requires >=1 standard monetary total and every finite amount zero' if not pref_zero else 'all reported preferred totals equal zero')
    # Parent + NCI must equal inclusive if both are disclosed; each component must be unique.
    parent,pv=unique_bs('StockholdersEquity'); nci,nv=unique_bs('MinorityInterest')
    parent_present=bool(parent); nci_present=bool(nci)
    parent_nci_ok=True
    if parent_present and nci_present:
        parent_nci_ok=len(pv)==1 and len(nv)==1 and equity is not None and next(iter(pv))+next(iter(nv))==equity
    check('parent_nci_reconciliation',parent_nci_ok,'parent equity plus MinorityInterest must exactly equal inclusive equity when both present' if not parent_nci_ok else ('components reconcile' if parent_present and nci_present else 'not both disclosed; no substitution'))
    temporary=[]
    for r in rows:
        tag=r.get('tag','')
        if (tag=='RedeemableNoncontrollingInterestEquityCarryingAmount' or TEMP_RE.search(tag)) and eligible_fact(r,sub,{tag},0) and standard(r):
            p=fact_evidence(r,pres,'BS')
            if p: temporary.append({**r,'_presentation':p})
    temporary_zero=all(finite_decimal(r['value'])==0 for r in temporary)
    check('temporary_redeemable_equity',temporary_zero,'nonzero standard temporary/redeemable total blocks qualification' if not temporary_zero else ('all reported totals zero' if temporary else 'no qualifying temporary/redeemable amount reported'))
    def evidence(rs):
        return [{k:r.get(k) for k in ('tag','version','ddate','qtrs','uom','segments','coreg','value','source_zip')}|{'presentation':r.get('_presentation',[])} for r in rs]
    return {
      'adsh':sub.get('adsh'),'cik':sub.get('cik'),'name':sub.get('name'),'sic':sub.get('sic'),
      'form':sub.get('form'),'fp':sub.get('fp'),'fy':sub.get('fy'),'fye':sub.get('fye'),'period':sub.get('period'),
      'filed':sub.get('filed'),'accepted':sub.get('accepted'),'source_zip':sub.get('source_zip'),
      'sourcequalified':bool(eligible),'meaning':'structural candidate only; historical issuer identity not approved',
      'steps':steps,'reasons':reasons,
      'source_facts':{'operating_income':evidence(oi),'interest':evidence(interest),
        'assets':evidence(bs['Assets']),'liabilities':evidence(bs['Liabilities']),'inclusive_equity':evidence(bs[INCLUSIVE]),
        'preferred_totals':evidence(pref),'parent_equity':evidence(parent),'minority_interest':evidence(nci),
        'temporary_redeemable_equity':evidence(temporary)},
      'negative_interest_review_required':bool(interest_unique and next(iter(ivals))<0)
    }

def qualify_all(inputs):
    filings=[]; input_manifest={}
    for label,receipt_path in inputs:
        receipt=json.load(open(receipt_path,encoding='utf-8'))
        tables=receipt['output_tables']; base=Path(receipt['output_directory'])
        for key in ('submissions.csv','presentation.csv','statement-facts.csv'):
            spec=tables[key]; p=Path(spec['path'])
            if not p.is_file() or sha256(p)!=spec['sha256'] or p.stat().st_size!=spec['bytes']:
                raise RuntimeError(f'input integrity mismatch: {p}')
            input_manifest[f'{label}/{key}']={'path':str(p),'sha256':spec['sha256'],'bytes':spec['bytes'],'receipt':str(receipt_path),'receipt_sha256':sha256(receipt_path)}
        source_hashes={Path(x['path']).name:x['sha256'] for x in receipt.get('input_sources',[])}
        subs=read_csv(tables['submissions.csv']['path'])
        pres=read_csv(tables['presentation.csv']['path'])
        facts=read_csv(tables['statement-facts.csv']['path'])
        pre_by=defaultdict(list); fact_by=defaultdict(list)
        for r in pres: pre_by[r['adsh']].append(r)
        for r in facts: fact_by[r['adsh']].append(r)
        for sub in subs:
            result=qualify_filing(sub,fact_by[sub['adsh']],pre_by[sub['adsh']])
            result['input_panel']=label
            result['source_zip_sha256']=source_hashes.get(result.get('source_zip'))
            filings.append(result)
    return filings,input_manifest

def verify_storage(plan):
    mount=plan['external_mount']
    st=os.stat(mount)
    if st.st_dev!=int(plan['external_device']): raise RuntimeError('external device mismatch; stopped')
    out=Path(plan['output'])/'reported-op-qualification'
    if out.exists(): raise RuntimeError(f'create-only output already exists: {out}')
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--raw',required=True); ap.add_argument('--run',action='store_true'); a=ap.parse_args()
    raw=Path(a.raw); plan=json.load(open(raw/'storage-plan.json')); out=verify_storage(plan)
    if not a.run: raise SystemExit('preflight only; pass --run after synthetic tests')
    inputs=[('candidate',raw/'fsds-panel-execution-receipt.json'),('predecessor',raw/'fsds-predecessor-execution-receipt.json'),('warmup',raw/'fsds-warmup-execution-receipt.json')]
    filings,manifest=qualify_all(inputs)
    if len(filings)!=8247: raise RuntimeError(f'expected 8247 rows, got {len(filings)}')
    out.mkdir(parents=True,exist_ok=False)
    jl=out/'filings.jsonl'
    with jl.open('x',encoding='utf8') as f:
        for item in filings: f.write(json.dumps(item,ensure_ascii=False,separators=(',',':'))+'\n')
    byyear=defaultdict(Counter); bypanel=defaultdict(Counter)
    for r in filings:
        byyear[str(r['fy'] or 'missing')][('qualified' if r['sourcequalified'] else 'not_qualified')]+=1
        bypanel[r['input_panel']][('qualified' if r['sourcequalified'] else 'not_qualified')]+=1
    summary={'schema':'reported-op-qualification/1','rows':len(filings),'qualified':sum(x['sourcequalified'] for x in filings),
      'not_qualified':sum(not x['sourcequalified'] for x in filings),'by_fy':{k:dict(v) for k,v in sorted(byyear.items())},
      'by_panel':{k:dict(v) for k,v in sorted(bypanel.items())},'inputs':manifest,'filings_jsonl':str(jl),
      'filings_sha256':sha256(jl),'script_sha256':sha256(__file__),'network_requests':0,
      'price_or_return_inputs_read':False,'qualification_boundary':'Structural candidate only; not issuer identity acceptance or factor value.'}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return summary
if __name__=='__main__':
    result=main(); print(json.dumps(result,ensure_ascii=False,indent=2))
