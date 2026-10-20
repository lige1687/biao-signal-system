#!/usr/bin/env python3
"""Derive strict, source-only accounting pathway checks from already saved panel tables."""
from __future__ import annotations
import argparse, csv, datetime as dt, decimal, hashlib, json, os, pathlib, shutil, time
from collections import defaultdict

RAW = pathlib.Path(__file__).resolve().parent
V1 = pathlib.Path('/Volumes/win+mac通用/LeiSignal-新实验结果/us-op-common-history-20261020/us-op-common-history-20261020-20261020T191922-92db83e55b32/result/accounting-structure-probe')
EXPECTED = {
    'filing-structure-candidates.csv': '1dddd86f27ddd98adaa4ca5297d6439696ff66bf471b0570d04575410b40e318',
    'fact-rows.csv': 'd7695a5a6e4e573beeed77da1f4ec691a155b22006b7956f4ec99424dbd919b1',
    'operating-income-identity-checks.csv': '2999d0eda785075f2adf1f4fcadfdbe25e6b46e7e4ef683582d08818732d2ec9',
    'manifest.json': '6f82221a3ce6c637260d1212c47a09a1ae09d65a9eead5d5ac6bb252b631430e',
}
PREFERRED_TOTAL_TAGS = {
    'PreferredStockValue', 'PreferredStockValueOutstanding',
    'PreferredStockCarryingValue', 'PreferredStockRedemptionValue',
    'PreferredStockIncludingAdditionalPaidInCapital',
    'PreferredStockNoParValue', 'PreferredStockNonVotingNoParValue',
}

def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def dec(x):
    try:
        y=decimal.Decimal(str(x))
        return y if y.is_finite() else None
    except (decimal.InvalidOperation, ValueError, TypeError):
        return None

def dumpj(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))

def usable_balance_fact(r):
    return r.get('uom')=='USD' and r.get('qtrs')=='0' and not r.get('segments') and not r.get('coreg') and dec(r.get('value')) is not None

def preferred_fact_class(tag, label):
    low=(label or '').lower()
    if tag not in PREFERRED_TOTAL_TAGS and 'preferredstock' not in tag.lower(): return 'not_preferred'
    if any(x in tag.lower() for x in ('pershare','pershares','numberofshares','sharesauthorized','sharesissued')):
        return 'excluded_share_or_per_share_tag'
    if tag in {'CommonAndPreferredStockValue'} or 'commonandpreferred' in tag.lower():
        return 'excluded_common_and_preferred_aggregate'
    if tag=='PreferredStockNoParValue' and ('per share' in low or 'per-share' in low):
        return 'excluded_row_explicitly_per_share'
    if ('in dollars per share' in low or 'in usd per share' in low or 'per-share amount' in low) and tag not in {'PreferredStockValue','PreferredStockValueOutstanding','PreferredStockCarryingValue','PreferredStockRedemptionValue','PreferredStockIncludingAdditionalPaidInCapital'}:
        return 'excluded_row_explicitly_per_share'
    if tag in PREFERRED_TOTAL_TAGS and ('per share' not in low and 'per-share' not in low and 'usd per share' not in low):
        return 'candidate_preferred_balance_amount'
    return 'review_required_tag_or_label'

def amount_summary(rows):
    amounts=sorted({str(dec(x['value'])) for x in rows if dec(x.get('value')) is not None},key=decimal.Decimal)
    tags=sorted({x['tag'] for x in rows})
    status=('missing_no_zero_fill' if not amounts else
            'unique_amount' if len(amounts)==1 and len(tags)==1 else
            'same_amount_multiple_tags_preserved' if len(amounts)==1 else
            'ambiguous_distinct_amounts')
    return {'status':status,'distinct_amounts_json':dumpj(amounts),'tags_json':dumpj(tags),
            'source_facts_json':dumpj(rows)}

def nci_candidate(r):
    t=r['tag'].lower()
    return (('minorityinterest' in t or 'noncontrollinginterest' in t)
            and 'redeemable' not in t and 'temporary' not in t and 'income' not in t
            and 'stockholdersequityincludingportion' not in t)

def preferred_balance_rows(facts):
    accepted=[]
    audit=[]
    for r in facts:
        if 'preferred' not in r['tag'].lower(): continue
        pres=json.loads(r.get('presentation_rows_json') or '[]')
        labels=sorted({p.get('row_name','') for p in pres})
        classification=preferred_fact_class(r['tag'],' | '.join(labels))
        eligible=(classification=='candidate_preferred_balance_amount' and usable_balance_fact(r) and r.get('version','').startswith('us-gaap/'))
        if eligible: accepted.append(r)
        audit.append({'tag':r['tag'],'version':r.get('version',''),'value':r.get('value',''),'uom':r.get('uom',''),'qtrs':r.get('qtrs',''),
                      'row_labels_json':dumpj(labels),'classification':classification,
                      'included_as_standard_preferred_balance_amount':eligible,
                      'nonstandard_version_candidate_only':not r.get('version','').startswith('us-gaap/')})
    return accepted,audit

def self_test():
    assert preferred_fact_class('PreferredStockParOrStatedValuePerShare','Preferred stock par value')=='excluded_share_or_per_share_tag'
    assert preferred_fact_class('PreferredStockValue','Preferred shares outstanding')=='candidate_preferred_balance_amount'
    assert preferred_fact_class('PreferredStockNoParValue','Preferred stock (USD per share)')=='excluded_row_explicitly_per_share'
    assert preferred_fact_class('CommonAndPreferredStockValue','Capital stock')=='excluded_common_and_preferred_aggregate'
    a=amount_summary([{'tag':'PreferredStockValueOutstanding','value':'0.00'}])
    assert a['status']=='unique_amount' and a['distinct_amounts_json']=='["0.00"]'
    b=amount_summary([{'tag':'PreferredStockValue','value':'0.00'},{'tag':'PreferredStockValueOutstanding','value':'5.00'}])
    assert b['status']=='ambiguous_distinct_amounts'
    c=amount_summary([])
    assert c['status']=='missing_no_zero_fill'
    assert nci_candidate({'tag':'MinorityInterest'})
    assert not nci_candidate({'tag':'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'})
    assert not nci_candidate({'tag':'TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests'})
    assert not nci_candidate({'tag':'RedeemableNoncontrollingInterestEquityFairValue'})
    print('self-test: 11 assertions passed')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out')
    ap.add_argument('--self-test',action='store_true')
    args=ap.parse_args()
    if args.self_test:
        self_test(); return 0
    if not args.out: raise SystemExit('--out required')
    started=dt.datetime.now(dt.timezone.utc).isoformat(); t0=time.monotonic()
    out=pathlib.Path(args.out).resolve()
    if out.exists(): raise SystemExit(f'output exists; refusing overwrite: {out}')
    manifest_path=V1/'manifest.json'
    for name,want in EXPECTED.items():
        p=V1/name
        if not p.is_file() or sha(p)!=want: raise SystemExit(f'v1 input hash mismatch: {p}')
    storage=json.loads((RAW/'storage-plan.json').read_text(encoding='utf-8'))
    result_root=pathlib.Path(storage['output']).resolve()
    if not str(out).startswith(str(result_root)+os.sep): raise SystemExit('output outside bound external result root')
    if not result_root.is_dir() or os.stat(result_root).st_dev!=storage['external_device']:
        raise SystemExit('external device/path binding mismatch')
    if shutil.disk_usage(result_root).free < storage['external_reserve_bytes']:
        raise SystemExit('external storage reserve would be breached')

    metadata={}; facts_by_key=defaultdict(list)
    with (V1/'filing-structure-candidates.csv').open(encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            meta={k:r.get(k,'') for k in ('name','sic','cik','form','fy','fp','period','accepted','candidate_month_ticker_keys_json','candidate_rounded_dates_json')}
            meta['normal_nonfinancial_sic']=r.get('normal_nonfinancial_sic','')
            metadata[r['adsh']]=meta
    with (V1/'fact-rows.csv').open(encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            if r['adsh'] not in metadata: continue
            if r.get('ddate') not in json.loads(metadata[r['adsh']]['candidate_rounded_dates_json'] or '[]'): continue
            if r.get('uom')!='USD' or r.get('segments') or r.get('coreg'): continue
            facts_by_key[(r['adsh'],r['ddate'])].append(r)
    prior_identity={}
    with (V1/'operating-income-identity-checks.csv').open(encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            prior_identity[(r['adsh'],r['rounded_date'])]=r.get('literal_sga_identity_matches','').lower()=='true'

    submission_facts=defaultdict(list); statement_input_hashes={}
    # Recover only exact total-assets and total-liabilities rows from the already extracted tables.
    panel_receipts=[]
    for pn in ['fsds-panel-execution-receipt.json','fsds-predecessor-execution-receipt.json','fsds-warmup-execution-receipt.json']:
        rec=json.loads((RAW/pn).read_text(encoding='utf-8')); panel_receipts.append(rec)
        for table in ('statement-facts.csv','presentation.csv'):
            binding=rec['output_tables'][table]; p=pathlib.Path(binding['path'])
            if sha(p)!=binding['sha256']: raise SystemExit(f'bound panel table hash mismatch: {p}')
            statement_input_hashes[str(p)]={'sha256':binding['sha256'],'bytes':p.stat().st_size,'panel_receipt_sha256':sha(RAW/pn)}
        stm=pathlib.Path(rec['output_tables']['statement-facts.csv']['path'])
        with stm.open(encoding='utf-8',newline='') as f:
            for r in csv.DictReader(f):
                if r.get('tag') not in {'Assets','Liabilities'}: continue
                if r.get('adsh') not in metadata or r.get('uom')!='USD' or r.get('qtrs')!='0' or r.get('segments') or r.get('coreg') or not r.get('version','').startswith('us-gaap/'): continue
                if r.get('ddate') not in json.loads(metadata[r['adsh']]['candidate_rounded_dates_json'] or '[]'): continue
                if dec(r.get('value')) is None: continue
                submission_facts[(r['adsh'],r['ddate'])].append(r)
    # Presentation rows are joined only for captured exact total balance tags.
    present=defaultdict(list)
    for rec in panel_receipts:
        p=pathlib.Path(rec['output_tables']['presentation.csv']['path'])
        with p.open(encoding='utf-8',newline='') as f:
            for r in csv.DictReader(f):
                if r.get('adsh') in metadata and r.get('tag') in {'Assets','Liabilities'} and not r.get('coreg') and r.get('version','').startswith('us-gaap/'):
                    present[(r['adsh'],r.get('tag',''))].append(r)

    path_rows=[]; balance_rows=[]; preferred_audit=[]
    path_counts=defaultdict(int); examples=[]
    for key, facts in sorted(facts_by_key.items()):
        adsh,date=key; meta=metadata[adsh]
        def rows(tag, qtrs=None):
            return [r for r in facts if r.get('tag')==tag and (qtrs is None or r.get('qtrs')==qtrs) and dec(r.get('value')) is not None and r.get('version','').startswith('us-gaap/')]
        parent=rows('StockholdersEquity','0'); common=rows('CommonStockholdersEquity','0')
        inclusive=rows('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest','0')
        nci=[r for r in facts if nci_candidate(r) and r.get('qtrs')=='0' and dec(r.get('value')) is not None and r.get('version','').startswith('us-gaap/')]
        redeemable=[r for r in facts if ('redeemable' in r.get('tag','').lower() and ('noncontrollinginterest' in r.get('tag','').lower() or 'minorityinterest' in r.get('tag','').lower())) and r.get('qtrs')=='0' and dec(r.get('value')) is not None]
        temporary=[r for r in facts if ('temporary' in r.get('tag','').lower() and ('noncontrollinginterest' in r.get('tag','').lower() or 'minorityinterest' in r.get('tag','').lower())) and r.get('qtrs')=='0' and dec(r.get('value')) is not None]
        pref,pref_audit=preferred_balance_rows(facts); preferred_audit.extend([{'adsh':adsh,'rounded_date':date,**x} for x in pref_audit])
        parent_s=amount_summary(parent); common_s=amount_summary(common); inclusive_s=amount_summary(inclusive)
        nci_s=amount_summary(nci); pref_s=amount_summary(pref); redeem_s=amount_summary(redeemable)
        def one(a):
            vals=json.loads(a['distinct_amounts_json'])
            return dec(vals[0]) if len(vals)==1 else None
        pv,cv,iv,nv,prv=map(one,(parent_s,common_s,inclusive_s,nci_s,pref_s))
        direct_complete=cv is not None and nv is not None
        inclusive_complete=iv is not None and prv is not None
        parent_complete=pv is not None and nv is not None and prv is not None
        direct_val=(cv+nv) if direct_complete else None
        inclusive_net=(iv-prv) if inclusive_complete else None
        parent_net=(pv+nv-prv) if parent_complete else None
        # Flow facts remain source evidence; only arithmetic identity is checked.
        # Flow identity is reused from the original v1 check rather than reconstructed with a new tag map.
        assets_liabs=submission_facts.get(key,[])
        arows=[r for r in assets_liabs if r['tag']=='Assets']; lrows=[r for r in assets_liabs if r['tag']=='Liabilities']
        assets_s=amount_summary(arows); liabs_s=amount_summary(lrows); av,lv=one(assets_s),one(liabs_s)
        gross_parent_nci=(pv+nv) if pv is not None and nv is not None else None
        balance_equity=iv if iv is not None else gross_parent_nci
        balance_equity_path='inclusive_equity' if iv is not None else ('parent_equity_plus_explicit_NCI' if gross_parent_nci is not None else 'unknown_no_zero_fill')
        eq_residual=None if av is None or lv is None or balance_equity is None else av-lv-balance_equity
        redeem_amount=one(redeem_s)
        temp_s=amount_summary(temporary)
        special_values=sorted({str(dec(x.get('value'))) for x in redeemable+temporary if dec(x.get('value')) is not None},key=decimal.Decimal)
        balance_closed=(eq_residual==0) if eq_residual is not None else None
        special_explains=(eq_residual in [dec(x) for x in special_values]) if eq_residual is not None and special_values else None
        parent_inclusive_match=(gross_parent_nci==iv) if gross_parent_nci is not None and iv is not None else None
        flow_identity=prior_identity.get(key)
        nci_tags=sorted({r['tag'] for r in nci}); redeem_tags=sorted({r['tag'] for r in redeemable}); temporary_tags=sorted({r['tag'] for r in temporary})
        row={'adsh':adsh,'name':meta['name'],'cik':meta['cik'],'sic':meta['sic'],'normal_nonfinancial_sic':meta['normal_nonfinancial_sic'],'form':meta['form'],'fy':meta['fy'],'fp':meta['fp'],'period':meta['period'],'accepted':meta['accepted'],'rounded_date':date,'candidate_month_ticker_keys_json':meta['candidate_month_ticker_keys_json'],
             'CommonStockholdersEquity_status':common_s['status'],'CommonStockholdersEquity_amounts_json':common_s['distinct_amounts_json'],'StockholdersEquity_status':parent_s['status'],'StockholdersEquity_amounts_json':parent_s['distinct_amounts_json'],'inclusive_equity_status':inclusive_s['status'],'inclusive_equity_amounts_json':inclusive_s['distinct_amounts_json'],
             'nonredeemable_NCI_status':nci_s['status'],'nonredeemable_NCI_tags_json':dumpj(nci_tags),'nonredeemable_NCI_amounts_json':nci_s['distinct_amounts_json'],'redeemable_NCI_tags_json':dumpj(redeem_tags),'redeemable_NCI_amounts_json':redeem_s['distinct_amounts_json'],'temporary_equity_NCI_tags_json':dumpj(temporary_tags),'temporary_equity_NCI_amounts_json':temp_s['distinct_amounts_json'],
             'preferred_total_status':pref_s['status'],'preferred_total_tags_json':pref_s['tags_json'],'preferred_total_amounts_json':pref_s['distinct_amounts_json'],
             'direct_CommonEquity_plus_NCI_complete':direct_complete,'direct_CommonEquity_plus_NCI_amount':str(direct_val) if direct_val is not None else '',
             'inclusive_equity_minus_preferred_complete':inclusive_complete,'inclusive_equity_minus_preferred_amount':str(inclusive_net) if inclusive_net is not None else '',
             'parent_equity_plus_NCI_minus_preferred_complete':parent_complete,'parent_equity_plus_NCI_minus_preferred_amount':str(parent_net) if parent_net is not None else '',
             'parent_equity_plus_NCI_equals_reported_inclusive_equity':parent_inclusive_match,
             'Assets_status':assets_s['status'],'Assets_amounts_json':assets_s['distinct_amounts_json'],'Assets_source_rows_json':dumpj([{k:r.get(k,'') for k in ('tag','value','ddate','qtrs','uom','source_zip')} for r in arows]),
             'Liabilities_status':liabs_s['status'],'Liabilities_amounts_json':liabs_s['distinct_amounts_json'],'Liabilities_source_rows_json':dumpj([{k:r.get(k,'') for k in ('tag','value','ddate','qtrs','uom','source_zip')} for r in lrows]),
             'balance_sheet_equity_reference_path':balance_equity_path,'Assets_minus_Liabilities_minus_equity_reference':str(eq_residual) if eq_residual is not None else '', 'Assets_equals_Liabilities_plus_inclusive_or_parent_plus_NCI':balance_closed,'residual_matches_one_reported_redeemable_or_temporary_item':special_explains,
             'revenue_minus_COGS_minus_SGA_equals_OperatingIncomeLoss_reused_v1_check':flow_identity}
        path_rows.append(row)
        for pname,val in [('direct_common_plus_nci',direct_complete),('inclusive_minus_preferred',inclusive_complete),('parent_plus_nci_minus_preferred',parent_complete)]: path_counts[pname+('_complete' if val else '_incomplete')]+=1
        if balance_closed is True: path_counts['assets_liabilities_equity_reference_closed']+=1
        elif eq_residual is not None: path_counts['assets_liabilities_equity_reference_nonzero_residual']+=1
        if special_explains is True: path_counts['residual_matches_one_reported_redeemable_or_temporary_item']+=1
        if meta['normal_nonfinancial_sic']=='True' and parent_complete and parent_inclusive_match and (balance_closed is True) and pref_s['status'] in {'unique_amount','same_amount_multiple_tags_preserved'} and prv==0 and not special_values:
            examples.append(row)
        balance_rows.append({'adsh':adsh,'name':meta['name'],'cik':meta['cik'],'sic':meta['sic'],'fy':meta['fy'],'form':meta['form'],'period':meta['period'],'accepted':meta['accepted'],'rounded_date':date,
                             'Assets_amounts_json':assets_s['distinct_amounts_json'],'Assets_presentations_json':dumpj([{'stmt':x.get('stmt',''),'line':x.get('line',''),'plabel':x.get('plabel',''),'version':x.get('version','')} for x in present.get((adsh,'Assets'),[])]),
                             'Liabilities_amounts_json':liabs_s['distinct_amounts_json'],'Liabilities_presentations_json':dumpj([{'stmt':x.get('stmt',''),'line':x.get('line',''),'plabel':x.get('plabel',''),'version':x.get('version','')} for x in present.get((adsh,'Liabilities'),[])]),
                             'inclusive_equity_amounts_json':inclusive_s['distinct_amounts_json'],'parent_equity_amounts_json':parent_s['distinct_amounts_json'],'nonredeemable_NCI_amounts_json':nci_s['distinct_amounts_json'],'redeemable_NCI_amounts_json':redeem_s['distinct_amounts_json'],'temporary_equity_NCI_amounts_json':temp_s['distinct_amounts_json'],'preferred_total_amounts_json':pref_s['distinct_amounts_json'],'Assets_minus_Liabilities_minus_equity_reference':row['Assets_minus_Liabilities_minus_equity_reference'],'balance_equity_reference_path':balance_equity_path,'Assets_equals_Liabilities_plus_equity_reference':balance_closed,'residual_matches_one_reported_special_equity_item':special_explains})
    # Sort qualifying normal examples by public filing acceptance time; include the earliest complete case.
    examples.sort(key=lambda r:(r['accepted'],r['adsh'],r['rounded_date']))
    output_files={}
    out.mkdir(parents=False,exist_ok=False)
    for fn,records in [('equity-pathway-review.csv',path_rows),('balance-sheet-closure.csv',balance_rows),('preferred-tag-filter-audit.csv',preferred_audit)]:
        p=out/fn
        fields=list(records[0]) if records else []
        with p.open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(records)
        output_files[fn]={'path':fn,'bytes':p.stat().st_size,'rows':len(records),'sha256':sha(p)}
    chosen_keys={(r['adsh'],r['rounded_date']) for r in examples[:1]}
    chosen_keys.add(('0001000228-14-000010','20131231'))
    example_facts=[]
    for key in sorted(chosen_keys):
        for r in facts_by_key.get(key,[]):
            tag=r.get('tag','').lower()
            if (r.get('tag') in {'Assets','Liabilities','StockholdersEquity','CommonStockholdersEquity','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest','OperatingIncomeLoss','SellingGeneralAndAdministrativeExpense','MinorityInterest','SalesRevenueNet','CostOfGoodsAndServicesSold','CostOfGoodsSold'}
                or any(x in tag for x in ('preferred','noncontrollinginterest','minorityinterest','depreciation','depletion','amortization','researchanddevelopment'))
                or ('interest' in tag and 'expense' in tag)):
                example_facts.append({k:r.get(k,'') for k in ('name','sic','cik','form','fy','fp','period','accepted','adsh','ddate','tag','version','qtrs','uom','finite_value','source_zip','presentation_rows_json')})
    for key in sorted(chosen_keys):
        for r in submission_facts.get(key,[]):
            prs=present.get((key[0],r['tag']),[])
            example_facts.append({'name':metadata[key[0]]['name'],'sic':metadata[key[0]]['sic'],'cik':metadata[key[0]]['cik'],'form':metadata[key[0]]['form'],'fy':metadata[key[0]]['fy'],'fp':metadata[key[0]]['fp'],'period':metadata[key[0]]['period'],'accepted':metadata[key[0]]['accepted'],'adsh':key[0],'ddate':key[1],'tag':r['tag'],'version':r.get('version',''),'qtrs':r.get('qtrs',''),'uom':r.get('uom',''),'finite_value':r.get('value',''),'source_zip':r.get('source_zip',''),'presentation_rows_json':dumpj([{'stmt':x.get('stmt',''),'line':x.get('line',''),'plabel':x.get('plabel',''),'version':x.get('version','')} for x in prs])})
    p=out/'example-source-facts.csv'
    fields=list(example_facts[0]) if example_facts else []
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(example_facts)
    output_files['example-source-facts.csv']={'path':'example-source-facts.csv','bytes':p.stat().st_size,'rows':len(example_facts),'sha256':sha(p)}
    year_support={}
    for adsh,meta in metadata.items():
        y=str(meta.get('fy') or 'unknown'); rec=year_support.setdefault(y,{'adshs':set(),'ciks':set(),'member_month_keys':set(),'filing_month_key_links':0})
        rec['adshs'].add(adsh); rec['ciks'].add(meta.get('cik',''))
        for item in json.loads(meta.get('candidate_month_ticker_keys_json') or '[]'):
            if isinstance(item,list) and len(item)==2:
                rec['member_month_keys'].add((str(item[0]),str(item[1]))); rec['filing_month_key_links']+=1
    year_support={y:{'filings':len(v['adshs']),'unique_CIKs':len(v['ciks']),'unique_member_month_ticker_keys':len(v['member_month_keys']),'filing_to_month_key_links':v['filing_month_key_links']} for y,v in sorted(year_support.items())}
    summary={'source_only':True,'network_requests':0,'market_effects_or_returns':0,'factor_or_OP_ratio_calculated':False,
             'method':'derive from v1 saved candidate facts and the already saved FSDS statement/presentation tables; no ZIP scan or new extraction.',
             'input_bindings':{'v1_manifest_sha256':sha(manifest_path),'filing_structure_candidates_sha256':sha(V1/'filing-structure-candidates.csv'),'fact_rows_sha256':sha(V1/'fact-rows.csv'),'storage_plan_sha256':sha(RAW/'storage-plan.json')},
             'candidate_accessions':len(metadata),'adsh_rounded_date_groups':len(path_rows),'v1_candidate_rows_reused':len(metadata),
             'preferred_filter':{'accepted_total_balance_tag_allowlist':sorted(PREFERRED_TOTAL_TAGS),'excluded_per_share_or_share_count':True,'uom_USD_alone_does_not_qualify':True,'missing_not_zero':True,'multiple_distinct_amounts_remain_ambiguous':True},
             'pathway_counts':dict(sorted(path_counts.items())),'year_support':year_support,'earliest_normal_nonfinancial_complete_balance_sheet_example':examples[0] if examples else None,
             'Henry_Schein_is_redeemable_NCI_exception':next((r for r in path_rows if r['adsh']=='0001000228-14-000010' and r['rounded_date']=='20131231'),None),
             'limitations':['A structural candidate is not research or factor eligibility.','D&A correspondence to a standardized numerator is not inferred from tag presence.','Only standard us-gaap versions enter structural path amounts; custom taxonomy facts remain visible as candidates and are not auto-mapped.','Minority, redeemable, and temporary equity items remain separate; no missing value is filled.'],
             'created_at_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    sp=out/'summary.json'; sp.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    output_files['summary.json']={'path':'summary.json','bytes':sp.stat().st_size,'rows':None,'sha256':sha(sp)}
    manifest={'created_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'source_only':True,'output_path':str(out),
              'inputs':{str(V1/'filing-structure-candidates.csv'):{'sha256':sha(V1/'filing-structure-candidates.csv'),'bytes':(V1/'filing-structure-candidates.csv').stat().st_size},
                        str(V1/'fact-rows.csv'):{'sha256':sha(V1/'fact-rows.csv'),'bytes':(V1/'fact-rows.csv').stat().st_size},
                        **statement_input_hashes,str(RAW/'storage-plan.json'):{'sha256':sha(RAW/'storage-plan.json'),'bytes':(RAW/'storage-plan.json').stat().st_size}},
              'outputs':list(output_files.values()),'summary_key_counts':summary['pathway_counts']}
    mp=out/'manifest.json'; mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'completed','started_at_utc':started,'elapsed_seconds':round(time.monotonic()-t0,3),'output_path':str(out),'manifest_sha256':sha(mp),'summary_sha256':sha(sp),'outputs':output_files,'pathway_counts':summary['pathway_counts'],'earliest_complete_example':{k:examples[0].get(k) for k in ('name','adsh','fy','period','accepted','Assets_minus_Liabilities_minus_equity_reference')} if examples else None,'redeemable_NCI_exception':{'adsh':'0001000228-14-000010','residual_matches_special_equity':summary['Henry_Schein_is_redeemable_NCI_exception']['residual_matches_one_reported_redeemable_or_temporary_item'] if summary['Henry_Schein_is_redeemable_NCI_exception'] else None}},ensure_ascii=False))
    return 0

if __name__=='__main__': raise SystemExit(main())
