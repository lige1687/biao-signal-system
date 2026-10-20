#!/usr/bin/env python3
"""Bounded source-only accounting-structure probe over prequalified annual filings."""
from __future__ import annotations
import argparse, csv, datetime as dt, decimal, hashlib, json, math, os, pathlib, re, shutil, sys, time
from collections import Counter, defaultdict

RAW_DEFAULT = pathlib.Path(__file__).resolve().parent
FLOW_GROUPS = {'revenue', 'cogs', 'sga', 'interest'}
CORE_GROUPS = FLOW_GROUPS | {'equity'}
INTEREST_EXACT = {'InterestExpense','InterestAndDebtExpense','InterestExpenseDebt','InterestExpenseNonOperating'}
REVENUE_EXACT = {'Revenues','SalesRevenueNet','RevenueFromContractWithCustomerExcludingAssessedTax','RevenueFromContractWithCustomerIncludingAssessedTax','SalesRevenueGoodsNet','SalesRevenueServicesNet'}
COGS_EXACT = {'CostOfRevenue','CostOfGoodsAndServicesSold','CostOfGoodsSold','CostOfServices'}
BALANCE_CONCEPTS = {'equity','equity_including_nci','preferred','minority_interest','aoci','retained_earnings','common_stock_treasury','deferred_tax','liabilities'}


def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def load_csv(path):
    with pathlib.Path(path).open('r',encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def dec(v):
    try:
        x=decimal.Decimal(str(v))
        return x if x.is_finite() else None
    except (decimal.InvalidOperation, TypeError, ValueError):
        return None


def concept(tag):
    t=tag.lower()
    if tag in REVENUE_EXACT or ('revenue' in t or 'salesrevenue' in t or 'premiumsearned' in t): return 'revenue'
    if tag in COGS_EXACT or any(x in t for x in ('costofrevenue','costofgoods','costofservices','costofsales','costofproducts')): return 'cogs'
    if tag=='SellingGeneralAndAdministrativeExpense': return 'sga'
    if 'researchanddevelopment' in t and 'expense' in t: return 'rd'
    if tag=='OperatingIncomeLoss' or tag.startswith('OperatingIncomeLossBefore'): return 'operating_income'
    if tag in INTEREST_EXACT or ('interest' in t and ('expense' in t or 'debt' in t) and 'income' not in t): return 'interest'
    if tag in {'StockholdersEquity','CommonStockholdersEquity'}: return 'equity'
    if tag=='StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest': return 'equity_including_nci'
    if 'noncontrollinginterest' in t or 'minorityinterest' in t: return 'minority_interest'
    if 'preferredstock' in t and any(x in t for x in ('value','carrying','redemption','equity')): return 'preferred'
    if 'accumulatedothercomprehensive' in t or 'othercomprehensiveincomeaccumulated' in t: return 'aoci'
    if tag.startswith('RetainedEarningsAccumulatedDeficit') or tag.startswith('RetainedEarnings'): return 'retained_earnings'
    if 'commonstock' in t or 'treasurystock' in t or 'additionalpaidincapital' in t: return 'common_stock_treasury'
    if 'deferredincometax' in t or 'deferredtax' in t: return 'deferred_tax'
    if tag in {'Liabilities','LiabilitiesAndStockholdersEquity'} or tag.startswith('LiabilitiesCurrent') or tag.startswith('LongTermLiabilities'): return 'liabilities'
    if any(x in t for x in ('depreciation','depletion','amortization')): return 'depreciation_amortization'
    return None


def expected_qtrs(group):
    return '0' if group in BALANCE_CONCEPTS else '4'


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--raw',default=str(RAW_DEFAULT))
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    t0=time.monotonic(); started=dt.datetime.now(dt.timezone.utc).isoformat()
    raw=pathlib.Path(args.raw).resolve(); out=pathlib.Path(args.out).resolve()
    review=raw/'astra-qualification-final-review.md'
    correction=raw/'method-correction-sga-mapping.json'
    coverage_receipt_path=raw/'annual-formation-coverage-receipt.json'
    panel_receipt_paths=[raw/'fsds-panel-execution-receipt.json',raw/'fsds-predecessor-execution-receipt.json',raw/'fsds-warmup-execution-receipt.json']
    coverage_receipt=json.loads(coverage_receipt_path.read_text(encoding='utf-8'))
    panel_receipts=[json.loads(p.read_text(encoding='utf-8')) for p in panel_receipt_paths]
    storage_plan=json.loads((raw/'storage-plan.json').read_text(encoding='utf-8'))
    if coverage_receipt.get('return_code')!=0 or any(x.get('status')!='source_extraction_only' for x in panel_receipts):
        raise SystemExit('bound prior outputs do not report successful source-only completion')
    result_root=pathlib.Path(storage_plan['output']).resolve()
    if not str(out).startswith(str(result_root)+os.sep): raise SystemExit('output is outside bound external result path')
    if out.exists(): raise SystemExit(f'output exists; refusing overwrite: {out}')
    if not result_root.exists(): raise SystemExit('bound result root missing')
    st=os.stat(result_root)
    if st.st_dev!=storage_plan['external_device']: raise SystemExit('external device ID mismatch')
    free=shutil.disk_usage(result_root).free
    if free < storage_plan['external_reserve_bytes']: raise SystemExit('external reserve would be breached')

    # Verify hashes inherited from prior execution receipts before reading their tables.
    input_bindings={}
    annual_monthly=pathlib.Path(coverage_receipt['output_directory'])/'monthly-formation-readiness.csv'
    annual_field=pathlib.Path(coverage_receipt['output_directory'])/'field-coverage.csv'
    for p in [annual_monthly,annual_field]:
        key=p.name
        bound=coverage_receipt['output_files'][key]
        actual=sha(p)
        if actual!=bound['sha256']: raise SystemExit(f'annual input hash mismatch: {p}')
        input_bindings[str(p)]={'sha256':actual,'bytes':p.stat().st_size,'rows_bound':bound.get('rows')}
    for p in [review,correction,raw/'accounting-target-ruling.md',raw/'method-correction-exact-period.json']:
        if not p.is_file(): raise SystemExit(f'bound review input missing: {p}')
        input_bindings[str(p)]={'sha256':sha(p),'bytes':p.stat().st_size,'kind':'method_or_review_reference'}
    panel_table_paths=[]
    for rec in panel_receipts:
        for table in ['submissions.csv','presentation.csv','statement-facts.csv']:
            meta=rec['output_tables'][table]; p=pathlib.Path(meta['path'])
            actual=sha(p)
            if actual!=meta['sha256']: raise SystemExit(f'panel input hash mismatch: {p}')
            input_bindings[str(p)]={'sha256':actual,'bytes':p.stat().st_size,'panel':rec['output_directory']}
            panel_table_paths.append((rec['output_directory'],table,p))

    # Keep only unique finite amounts for the four named flows plus positive equity.
    selected=defaultdict(lambda:{'keys':[],'evaluations':[]})
    candidate_rows=0; selected_month_rows=0
    required=CORE_GROUPS
    with annual_monthly.open('r',encoding='utf-8',newline='') as f:
        for row in csv.DictReader(f):
            candidate_rows+=1
            try: evals=json.loads(row.get('candidate_cik_evaluations_json') or '[]')
            except json.JSONDecodeError: continue
            for e in evals:
                groups=e.get('field_groups',{})
                if not all(groups.get(g,{}).get('status')=='finite_unique_amount' for g in required): continue
                vals=groups.get('equity',{}).get('distinct_finite_values') or []
                if len(vals)!=1 or dec(vals[0]) is None or dec(vals[0])<=0: continue
                selected_month_rows+=1
                a=e.get('adsh')
                if not a: continue
                selected[a]['keys'].append({'month':row['month'],'ticker':row['ticker'],'candidate_cik':e.get('candidate_cik')})
                selected[a]['evaluations'].append(e)
    if not selected: raise SystemExit('no selected filings; refusing empty result')
    selected_adsh=set(selected)

    # Read submission, presentation and numeric facts from the three already-saved panels.
    subs=defaultdict(list); pres=defaultdict(list); facts=defaultdict(list)
    panel_names={}
    for panel,table,path in panel_table_paths:
        panel_name=pathlib.Path(panel).name
        if table=='submissions.csv':
            with path.open('r',encoding='utf-8',newline='') as f:
                for row in csv.DictReader(f):
                    if row.get('adsh') in selected_adsh:
                        row['_panel']=panel_name; subs[row['adsh']].append(row)
        elif table=='presentation.csv':
            with path.open('r',encoding='utf-8',newline='') as f:
                for row in csv.DictReader(f):
                    if row.get('adsh') in selected_adsh:
                        row['_panel']=panel_name; pres[row['adsh']].append(row)
        elif table=='statement-facts.csv':
            with path.open('r',encoding='utf-8',newline='') as f:
                for row in csv.DictReader(f):
                    a=row.get('adsh')
                    if a in selected_adsh:
                        row['_panel']=panel_name; facts[a].append(row)

    filings=[]; fact_rows=[]; structure_counts=Counter(); reconcile=[]; missing_sub=[]
    status_counts=Counter(); selected_date_count=Counter(); period_fields={'adsh','cik','name','sic','form','fy','fp','period','accepted','filed','fye','instance','prevrpt','nciks','aciks'}
    for adsh, obj in selected.items():
        evals=obj['evaluations']; base=evals[0]
        date_candidates=set()
        for e in evals:
            for d in e.get('raw_rounded_date_candidates',e.get('rounded_date_candidate',[])):
                if d: date_candidates.add(str(d).replace('-',''))
        if not date_candidates and base.get('sub_period_rounded_candidate'):
            date_candidates.add(str(base['sub_period_rounded_candidate']).replace('-',''))
        subrows=subs.get(adsh,[])
        if not subrows:
            missing_sub.append(adsh); sub={}
        else:
            # Preserve possible SUB duplicates; choose only a row matching candidate CIK and rounded period where possible.
            desired_ciks={str(x.get('candidate_cik','')).lstrip('0') for x in evals}
            def sub_score(r):
                return (int(str(r.get('cik','')).lstrip('0') in desired_ciks), int(str(r.get('period','')) in date_candidates), int(r.get('form') in {'10-K','10-K/A'}))
            sub=sorted(subrows,key=sub_score,reverse=True)[0]
        meta={k:sub.get(k,'') for k in period_fields}
        meta.update({'adsh':adsh,'source_submission_panels_json':json.dumps(sorted({r['_panel'] for r in subrows}),ensure_ascii=False),
                     'candidate_month_ticker_keys_json':json.dumps(sorted(set((x['month'],x['ticker']) for x in obj['keys'])),ensure_ascii=False),
                     'candidate_evaluation_count':len(evals),'candidate_rounded_dates_json':json.dumps(sorted(date_candidates),ensure_ascii=False),
                     'submission_variants_json':json.dumps([{k:r.get(k,'') for k in period_fields if k in r}|{'source_panel':r['_panel']} for r in subrows],ensure_ascii=False,sort_keys=True),
                     'normal_nonfinancial_sic':bool(str(sub.get('sic','')).isdigit() and not str(sub.get('sic','')).startswith('6'))})
        matched_pres=defaultdict(list)
        for p in pres.get(adsh,[]):
            stmt=p.get('stmt','')
            if stmt not in {'IS','BS','CF'}: continue
            matched_pres[p.get('tag','')].append({'stmt':stmt,'line':p.get('line',''),'report':p.get('report',''),'inpth':p.get('inpth',''),'rfile':p.get('rfile',''),'version':p.get('version',''),'row_name':p.get('plabel',''),'panel':p['_panel']})
        chosen=[]
        for f in facts.get(adsh,[]):
            d=str(f.get('ddate',''))
            if d not in date_candidates: continue
            if f.get('uom')!='USD' or f.get('segments','').strip() or f.get('coreg','').strip(): continue
            group=concept(f.get('tag',''))
            if group is None or f.get('qtrs')!=expected_qtrs(group): continue
            value=dec(f.get('value'))
            fact={**{k:f.get(k,'') for k in ['tag','version','ddate','qtrs','uom','value','segments','coreg','source_zip']},
                  'concept':group,'panel':f['_panel'],'finite_value':None if value is None else str(value),
                  'presentation_rows':matched_pres.get(f.get('tag',''),[])}
            chosen.append(fact)
            fact_rows.append({**meta,**{k:fact[k] for k in ['concept','tag','version','ddate','qtrs','uom','value','finite_value','segments','coreg','source_zip','panel']},
                              'presentation_rows_json':json.dumps(fact['presentation_rows'],ensure_ascii=False,sort_keys=True)})
        # Aggregate each concept without merging distinct tags/amounts by priority.
        bydate=defaultdict(lambda:defaultdict(list))
        for f in chosen: bydate[f['ddate']][f['concept']].append(f)
        date_summaries=[]; presence=set()
        for d, groups in sorted(bydate.items()):
            gs={}
            for g, fs in groups.items():
                vals=sorted({f['finite_value'] for f in fs if f['finite_value'] is not None},key=lambda x:decimal.Decimal(x))
                if vals: presence.add(g)
                gs[g]={'fact_count':len(fs),'distinct_finite_amount_count':len(vals),'unique_amount':vals[0] if len(vals)==1 else None,
                       'facts':[{'tag':f['tag'],'version':f['version'],'value':f['value'],'finite_value':f['finite_value'],'qtrs':f['qtrs'],
                                 'source_zip':f['source_zip'],'panel':f['panel'],'presentation_rows':f['presentation_rows']} for f in fs]}
            # Reconcile only when each amount is unique at this same date. This is an identity check, not an OP calculation.
            r=gs.get('revenue',{}).get('unique_amount'); c=gs.get('cogs',{}).get('unique_amount'); s=gs.get('sga',{}).get('unique_amount'); oi=gs.get('operating_income',{}).get('unique_amount'); rd=gs.get('rd',{}).get('unique_amount')
            if all(x is not None for x in (r,c,s,oi)):
                residual_base=decimal.Decimal(r)-decimal.Decimal(c)-decimal.Decimal(s)-decimal.Decimal(oi)
                residual_rd=None if rd is None else decimal.Decimal(r)-decimal.Decimal(c)-decimal.Decimal(s)-decimal.Decimal(rd)-decimal.Decimal(oi)
                direct_common=any(x['tag']=='CommonStockholdersEquity' for x in gs.get('equity',{}).get('facts',[]))
                reconcile.append({'adsh':adsh,'ticker_keys_json':meta['candidate_month_ticker_keys_json'],'cik':meta.get('cik',''),'sic':meta.get('sic',''),'normal_nonfinancial_sic':meta['normal_nonfinancial_sic'],
                                  'form':meta.get('form',''),'fy':meta.get('fy',''),'fp':meta.get('fp',''),'period':meta.get('period',''),'accepted':meta.get('accepted',''),
                                  'rounded_date':d,'revenue_unique_amount':r,'cogs_unique_amount':c,'literal_sga_unique_amount':s,'rd_unique_amount':rd,'reported_operating_income_unique_amount':oi,
                                  'revenue_minus_cogs_minus_sga_minus_reported_operating_income_usd':str(residual_base),
                                  'revenue_minus_cogs_minus_sga_minus_rd_minus_reported_operating_income_usd':None if residual_rd is None else str(residual_rd),
                                  'literal_sga_identity_matches':residual_base==0,'including_rd_identity_matches':residual_rd==0 if residual_rd is not None else None,
                                  'direct_common_equity_unique':direct_common})
            def exact_tag_amount(group, tag):
                fs=[f for f in gs.get(group,{}).get('facts',[]) if f['tag']==tag and f['finite_value'] is not None]
                values=sorted({f['finite_value'] for f in fs},key=decimal.Decimal)
                return {'fact_count':len(fs),'distinct_finite_amount_count':len(values),'unique_amount':values[0] if len(values)==1 else None,
                        'facts':[{'tag':f['tag'],'value':f['value'],'version':f['version'],'source_zip':f['source_zip'],'presentation_rows':f['presentation_rows']} for f in fs]}
            common_eq=exact_tag_amount('equity','CommonStockholdersEquity')
            parent_eq=exact_tag_amount('equity','StockholdersEquity')
            inclusive_eq=exact_tag_amount('equity_including_nci','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest')
            nci_by_tag={}
            for f in gs.get('minority_interest',{}).get('facts',[]):
                nci_by_tag.setdefault(f['tag'],exact_tag_amount('minority_interest',f['tag']))
            pref_by_tag={}
            for f in gs.get('preferred',{}).get('facts',[]):
                pref_by_tag.setdefault(f['tag'],exact_tag_amount('preferred',f['tag']))
            nci_unique_tags=[k for k,v in nci_by_tag.items() if v['unique_amount'] is not None]
            pref_unique_tags=[k for k,v in pref_by_tag.items() if v['unique_amount'] is not None]
            equity_paths={
                'direct_common_equity_plus_explicit_nci':{'candidate_components_complete':common_eq['unique_amount'] is not None and len(nci_unique_tags)==1,
                    'common_equity':common_eq,'explicit_nci_tags':nci_by_tag,'not_a_scoring_approval':True},
                'inclusive_equity_minus_explicit_preferred':{'candidate_components_complete':inclusive_eq['unique_amount'] is not None and len(pref_unique_tags)==1,
                    'inclusive_equity':inclusive_eq,'explicit_preferred_tags':pref_by_tag,'not_a_scoring_approval':True},
                'parent_equity_plus_explicit_nci_minus_explicit_preferred':{'candidate_components_complete':parent_eq['unique_amount'] is not None and len(nci_unique_tags)==1 and len(pref_unique_tags)==1,
                    'parent_equity':parent_eq,'explicit_nci_tags':nci_by_tag,'explicit_preferred_tags':pref_by_tag,'not_a_scoring_approval':True},
                'parent_inclusive_equal_amount_nci_zero_crosscheck':{'same_unique_amount':parent_eq['unique_amount'] is not None and inclusive_eq['unique_amount'] is not None and parent_eq['unique_amount']==inclusive_eq['unique_amount'],
                    'parent_equity':parent_eq,'inclusive_equity':inclusive_eq,'inference_not_automatic':True}}
            date_summaries.append({'rounded_date':d,'groups':gs,'equity_pathway_component_candidates':equity_paths})
        # A stable structure signature emphasizes the main income statement and equity presentations.
        latest_sub=sub
        equity_tags=sorted({f['tag'] for f in chosen if f['concept'] in {'equity','equity_including_nci'}})
        primary_presence={g:(g in presence) for g in ['revenue','cogs','sga','rd','operating_income','interest','equity','equity_including_nci','preferred','minority_interest','aoci','retained_earnings','common_stock_treasury','deferred_tax','liabilities','depreciation_amortization']}
        sig={
            'R':primary_presence['revenue'],'C':primary_presence['cogs'],'SGA':primary_presence['sga'],'RD':primary_presence['rd'],'OperatingIncomeLoss':primary_presence['operating_income'],'Interest':primary_presence['interest'],
            'direct_CommonStockholdersEquity':'CommonStockholdersEquity' in equity_tags,'StockholdersEquity':'StockholdersEquity' in equity_tags,
            'Equity_including_NCI':primary_presence['equity_including_nci'],'Preferred':primary_presence['preferred'],'MinorityInterest_or_NCI':primary_presence['minority_interest'],
            'InterestExpenseNonOperating':any(f['tag']=='InterestExpenseNonOperating' for f in chosen),
            'DepreciationAmortization':primary_presence['depreciation_amortization']}
        signature=json.dumps(sig,sort_keys=True,separators=(',',':'))
        structure_counts[signature]+=1
        filings.append({**meta,'candidate_cik':base.get('candidate_cik',''),'candidate_status':base.get('status',''),
                        'sic_class':'nonfinancial_sic_candidate' if meta['normal_nonfinancial_sic'] else ('financial_sic' if str(meta.get('sic','')).startswith('6') else 'unknown_sic'),
                        'rounded_date_group_count':len(date_summaries),'concept_presence_json':json.dumps(primary_presence,sort_keys=True),
                        'equity_tags_json':json.dumps(equity_tags,ensure_ascii=False),'structure_signature_json':signature,
                        'date_group_summaries_json':json.dumps(date_summaries,ensure_ascii=False,sort_keys=True),
                        'relevant_fact_count':len(chosen),'submission_missing':not bool(subrows)})

    # Choose the most frequent full signature among normal nonfinancial SIC filings, then earliest accepted instances.
    nonfin_counts=Counter(r['structure_signature_json'] for r in filings if r['normal_nonfinancial_sic'])
    most_sig,most_count=nonfin_counts.most_common(1)[0] if nonfin_counts else ('{}',0)
    examples=sorted([r for r in filings if r['normal_nonfinancial_sic'] and r['structure_signature_json']==most_sig],key=lambda r:(r.get('accepted',''),r['adsh']))[:2]
    rows_by_adsh={r['adsh']:r for r in filings}
    summary={
        'selected_member_month_rows':selected_month_rows,'selected_unique_adsh':len(selected),'candidate_monthly_readiness_rows_scanned':candidate_rows,
        'unique_tickers':len({x['ticker'] for obj in selected.values() for x in obj['keys']}),'unique_candidate_ciks':len({x['candidate_cik'] for obj in selected.values() for x in obj['keys']}),
        'filings_found_in_panel_submissions':len(selected)-len(missing_sub),'submission_missing_count':len(missing_sub),
        'duplicate_submission_adsh_count':sum(len(v)>1 for v in subs.values()),
        'normal_nonfinancial_sic_filings':sum(bool(r['normal_nonfinancial_sic']) for r in filings),
        'financial_sic_filings':sum(r['sic_class']=='financial_sic' for r in filings),'unknown_sic_filings':sum(r['sic_class']=='unknown_sic' for r in filings),
        'most_common_normal_nonfinancial_primary_structure_count':most_count,
        'most_common_normal_nonfinancial_primary_structure':json.loads(most_sig),
        'earliest_two_examples':[{k:r.get(k) for k in ['adsh','cik','name','sic','form','fy','fp','period','accepted','candidate_rounded_dates_json','equity_tags_json','concept_presence_json']} for r in examples],
        'direct_CommonStockholdersEquity_filings':sum('CommonStockholdersEquity' in json.loads(r['equity_tags_json']) for r in filings),
        'direct_CommonStockholdersEquity_in_normal_nonfinancial_filings':sum(bool(r['normal_nonfinancial_sic']) and 'CommonStockholdersEquity' in json.loads(r['equity_tags_json']) for r in filings),
        'same_date_unique_R_C_SGA_OI_reconciliation_cases':len(reconcile),
        'same_date_R_C_SGA_equals_reported_OperatingIncomeLoss':sum(r['literal_sga_identity_matches'] for r in reconcile),
        'same_date_R_C_SGA_RD_equals_reported_OperatingIncomeLoss':sum(r['including_rd_identity_matches'] is True for r in reconcile),
        'reconciliation_cases_with_direct_common_equity':sum(r['direct_common_equity_unique'] for r in reconcile),
        'missing_submission_accessions':missing_sub,
        'selection_rule':'Existing annual-formation monthly candidates where revenue, cogs, sga, interest and equity each had finite_unique_amount and equity was positive; selection inherited, not recalculated as an effect.',
        'date_filter':'Only rounded NUM.ddate values already listed as nearest rounded-date candidates; USD; flows qtrs=4; balance fields qtrs=0; no coreg/segments.',
        'accounting_identity_limit':'Only compared same-date unique candidate amounts R-C-SGA and R-C-SGA-RD to reported OperatingIncomeLoss, without calculating a factor measure, ratio, or return. No missing value was filled.',
        'normal_nonfinancial_sic_rule':'SIC must be numeric and not begin with 6; no other industry exclusion.',
        'zero_network_or_effect_calculation':True,
        'input_hashes':input_bindings
    }
    out.mkdir(parents=True,exist_ok=False)
    # CSV fields are JSON strings for nested evidence so values remain valid JSON, never Python repr.
    filing_path=out/'filing-structure-candidates.csv'
    with filing_path.open('w',encoding='utf-8',newline='') as f:
        cols=list(filings[0].keys()); w=csv.DictWriter(f,fieldnames=cols,lineterminator='\n');w.writeheader();w.writerows(filings)
    fact_path=out/'fact-rows.csv'
    with fact_path.open('w',encoding='utf-8',newline='') as f:
        cols=list(fact_rows[0].keys()) if fact_rows else ['adsh','concept','tag','version','ddate','qtrs','uom','value','finite_value','segments','coreg','source_zip','panel','presentation_rows_json']
        w=csv.DictWriter(f,fieldnames=cols,lineterminator='\n');w.writeheader();w.writerows(fact_rows)
    rec_path=out/'operating-income-identity-checks.csv'
    with rec_path.open('w',encoding='utf-8',newline='') as f:
        cols=list(reconcile[0].keys()) if reconcile else ['adsh','rounded_date','literal_sga_identity_matches','including_rd_identity_matches']
        w=csv.DictWriter(f,fieldnames=cols,lineterminator='\n');w.writeheader();w.writerows(reconcile)
    sig_rows=[]
    for sig,count in nonfin_counts.most_common(): sig_rows.append({'normal_nonfinancial_primary_structure_json':sig,'filing_count':count})
    with (out/'structure-counts.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['normal_nonfinancial_primary_structure_json','filing_count'],lineterminator='\n');w.writeheader();w.writerows(sig_rows)
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    outfiles=[]
    for name in ['filing-structure-candidates.csv','fact-rows.csv','operating-income-identity-checks.csv','structure-counts.csv','summary.json']:
        p=out/name; outfiles.append({'path':name,'sha256':sha(p),'bytes':p.stat().st_size,'rows':sum(1 for _ in p.open('rb'))-1 if p.suffix=='.csv' else None})
    manifest={'created_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'output_path':str(out),'outputs':outfiles,
              'inputs':input_bindings,'summary_key_counts':{k:v for k,v in summary.items() if isinstance(v,(int,bool))},'source_only':True}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    # Read back the whitelist and verify actual CSV structure, row counts and SHA values.
    readback={}
    for item in outfiles:
        p=out/item['path']; actual=sha(p)
        if actual!=item['sha256']: raise SystemExit(f'output hash readback mismatch: {p}')
        if p.suffix=='.csv':
            with p.open('r',encoding='utf-8',newline='') as f: count=sum(1 for _ in csv.DictReader(f))
            if count!=item['rows']: raise SystemExit(f'output row readback mismatch: {p} {count}!={item["rows"]}')
            readback[p.name]={'rows':count,'sha256':actual}
    if len(load_csv(filing_path))!=1201: raise SystemExit('expected 1201 unique filings from frozen screen')
    print(json.dumps({'status':'success','output':str(out),'summary':summary,'manifest_sha256':sha(out/'manifest.json'),
                      'outputs':readback,'elapsed_seconds':round(time.monotonic()-t0,3)},ensure_ascii=False))

if __name__=='__main__':
    main()
