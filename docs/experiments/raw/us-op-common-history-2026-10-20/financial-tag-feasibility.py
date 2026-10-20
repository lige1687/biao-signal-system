#!/usr/bin/env python3
"""Read-only field-availability inventory for the finished 2014Q1 SEC annual filing sample."""
import argparse,csv,datetime as dt,decimal,hashlib,json,re,time,zipfile,io
from collections import Counter,defaultdict
from pathlib import Path

CONTRACT_DEFAULT=Path(__file__).with_name('luna-financial-tag-contract.json')
REVENUE=['Revenues','SalesRevenueNet','RevenueFromContractWithCustomerExcludingAssessedTax','RevenueFromContractWithCustomerIncludingAssessedTax','SalesRevenueGoodsNet','SalesRevenueServicesNet']
COGS=['CostOfRevenue','CostOfGoodsAndServicesSold','CostOfGoodsSold','CostOfServices']
SGA=['SellingGeneralAndAdministrativeExpense']
INTEREST=['InterestExpense','InterestAndDebtExpense','InterestExpenseDebt','InterestExpenseNonOperating']
EQUITY=['StockholdersEquity','CommonStockholdersEquity']
PREFERRED=['PreferredStockValue','PreferredStockCarryingValue','PreferredStockRedemptionValue']
GROUPS={'revenue':REVENUE,'cogs':COGS,'sga':SGA,'interest':INTEREST,'equity':EQUITY,'preferred':PREFERRED}
FLOW=['revenue','cogs','sga','interest']
SEMANTIC_WORDS={
 'revenue':['revenue','revenues','sales','turnover'],
 'cogs':['cost of revenue','cost of goods','cost of services','cost of sales','cost of products'],
 'sga':['selling','general and administrative','selling general','administrative expense','sg&a'],
 'interest':['interest expense','interest and debt','debt expense','borrowing cost','finance cost']}

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def norm_cik(v):
 try:return str(int(str(v).strip()))
 except (ValueError,TypeError):return str(v).strip().lstrip('0')
def to_date(v):return dt.datetime.strptime(v,'%Y%m%d').date()
def as_decimal(v):
 try:return decimal.Decimal(v)
 except (decimal.InvalidOperation,TypeError):return None
def semantic_hits(tag,label):
 s=(tag+' '+label).lower();return [k for k,words in SEMANTIC_WORDS.items() if any(w in s for w in words)]
def read_csv_rows(path):
 with Path(path).open('r',encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def run(contract_path):
 started=dt.datetime.now(dt.timezone.utc); t0=time.monotonic(); cp=Path(contract_path).resolve();contract=json.loads(cp.read_text(encoding='utf-8'))
 paths=[Path(x) for x in contract['read_only_paths']]
 hashes={str(p):sha(p) for p in paths}
 for p in paths:assert p.is_file(),f'missing input {p}'
 annual_path,presentation_path,facts_path,zip_path,candidate_path=paths
 candidate_obj=json.loads(candidate_path.read_text(encoding='utf-8'));candidate_ids={norm_cik(x) for x in candidate_obj['ciks']}
 assert len(candidate_ids)==899 and len(candidate_obj['ciks'])==899
 annual_rows=[r for r in read_csv_rows(annual_path) if norm_cik(r['cik']) in candidate_ids]
 annual_by_adsh={r['adsh']:r for r in annual_rows}
 assert len(annual_by_adsh)==len(annual_rows),'duplicate accession in annual-submissions sample'
 # Validate filing forms from the already-bound Q1 SEC archive SUB table; retain only 10-K/10-K/A.
 forms={}
 with zipfile.ZipFile(zip_path) as z:
  with z.open('sub.txt') as binary:
   text=io.TextIOWrapper(binary,encoding='utf-8',newline='')
   for r in csv.DictReader(text,delimiter='\t'):
    if r.get('adsh') in annual_by_adsh:forms[r['adsh']]=r.get('form','')
 annual_adshs=set(annual_by_adsh)
 form_adshs={a for a in annual_adshs if forms.get(a) in {'10-K','10-K/A'}}
 form_rows=[annual_by_adsh[a] for a in sorted(form_adshs)]
 # Presentation facts: statement placement, primary labels, and candidate semantic custom labels.
 target_tags=set(sum(GROUPS.values(),[])); pre_map=defaultdict(set); pre_meta=defaultdict(list); semantic_pre=defaultdict(set); presentation_rows=0
 with presentation_path.open('r',encoding='utf-8',newline='') as f:
  for r in csv.DictReader(f):
   if r['adsh'] not in form_adshs or r.get('stmt') not in {'IS','BS'}:continue
   presentation_rows+=1;tag=r['tag'];stmt=r['stmt'];label=r.get('plabel','');pre_map[(r['adsh'],tag)].add(stmt)
   if tag in target_tags:
    pre_meta[(r['adsh'],tag)].append({'stmt':stmt,'tag':tag,'version':r.get('version',''),'plabel':label,'line':r.get('line',''),'inpth':r.get('inpth','')})
   hits=semantic_hits(tag,label)
   if hits:
    key=(tag,stmt,r.get('version',''),label)
    for group in hits:semantic_pre[group].add(key)
 # Full NUM date inventory for these submitted accessions; retain raw target facts only.
 dates=defaultdict(set); target_fact_rows=defaultdict(list); fact_rows_seen=0
 with facts_path.open('r',encoding='utf-8',newline='') as f:
  for r in csv.DictReader(f):
   if r['adsh'] not in form_adshs:continue
   fact_rows_seen+=1
   try:d=to_date(r['ddate'])
   except (ValueError,TypeError):continue
   dates[r['adsh']].add(d)
   if r['tag'] in target_tags:target_fact_rows[r['adsh']].append(r)
 # Select nearest NUM.ddate to SUB.period, retaining ties at minimum distance and requiring <=7 days.
 selected={}; date_status={}
 for a in form_adshs:
  sub=annual_by_adsh[a]
  try:period=to_date(sub['period'])
  except (ValueError,TypeError):date_status[a]={'status':'invalid_sub_period','period':sub.get('period','')};continue
  if not dates.get(a):date_status[a]={'status':'no_num_date','period':sub['period']};continue
  best=min(abs((d-period).days) for d in dates[a])
  if best>7:date_status[a]={'status':'no_date_within_7_days','period':sub['period'],'nearest_abs_days':best};continue
  ds=sorted(d for d in dates[a] if abs((d-period).days)==best)
  selected[a]=set(ds);date_status[a]={'status':'candidate_date','period':sub['period'],'dates':[d.isoformat() for d in ds],'offset_days':[ (d-period).days for d in ds]}
 # Filing-level field availability based on the tag, selected date, expected qtrs, and displayed IS/BS statement.
 tag_stats=defaultdict(lambda:{'filings':set(),'IS_filings':set(),'BS_filings':set(),'raw_fact_rows':0})
 filing_results={}; cik_filing_map=defaultdict(list)
 for a in sorted(form_adshs):
  sub=annual_by_adsh[a]; selected_dates=selected.get(a,set()); present=defaultdict(list); fact_evidence=[]
  for r in target_fact_rows.get(a,[]):
   try:d=to_date(r['ddate'])
   except (ValueError,TypeError):continue
   tag=r['tag']; expected_qtrs='0' if tag in EQUITY+PREFERRED else '4'
   if d not in selected_dates or r.get('qtrs')!=expected_qtrs:continue
   stmts=sorted(pre_map.get((a,tag),set()))
   # Keep the original fact even when presentation does not place it on IS/BS.
   if not stmts:stmts=['presentation_statement_missing']
   rec={'tag':tag,'qtrs':r.get('qtrs',''),'ddate':r.get('ddate',''),'value':r.get('value',''),'uom':r.get('uom',''),'segments':r.get('segments',''),'version':r.get('version',''),'statements':stmts,'plabels':sorted({x['plabel'] for x in pre_meta.get((a,tag),[])})}
   fact_evidence.append(rec);present[tag].append(rec)
   st=tag_stats[tag];st['filings'].add(a);st['raw_fact_rows']+=1
   for s in stmts:
    if s in {'IS','BS'}:st[s+'_filings'].add(a)
  groups={}
  for group,tags in GROUPS.items():groups[group]=sorted(t for t in tags if t in present)
  flow_joint=all(groups[g] for g in FLOW)
  equity_any=bool(groups['equity']);pref_tags=groups['preferred']
  pref_values=[as_decimal(x['value']) for t in pref_tags for x in present[t]]
  pref_zero=any(x is not None and x==0 for x in pref_values)
  pref_nonzero=any(x is not None and x!=0 for x in pref_values)
  row={'adsh':a,'cik':norm_cik(sub['cik']),'name':sub.get('name',''),'form':forms.get(a,''),'period':sub.get('period',''),'fy':sub.get('fy',''),'fp':sub.get('fp',''),'filed':sub.get('filed',''),'accepted':sub.get('accepted',''),'date_match':date_status.get(a,{'status':'no_match'}),'field_tags':groups,'four_flow_groups_joint':flow_joint,'four_flows_plus_any_explicit_equity':flow_joint and equity_any,'four_flows_plus_equity_plus_explicit_preferred':flow_joint and equity_any and bool(pref_tags),'explicit_preferred_tag_present':bool(pref_tags),'explicit_preferred_zero_value_present':pref_zero,'explicit_preferred_nonzero_value_present':pref_nonzero,'raw_candidate_facts':fact_evidence}
  filing_results[a]=row;cik_filing_map[row['cik']].append(row)
 # Definitions for the requested standard tags only, plus custom flag lookup for presentation-derived semantic candidates.
 definitions=defaultdict(list); candidate_tag_names={x[0] for group in semantic_pre.values() for x in group}; lookup_tags=target_tags|candidate_tag_names
 with zipfile.ZipFile(zip_path) as z, z.open('tag.txt') as binary:
  text=io.TextIOWrapper(binary,encoding='utf-8',newline='')
  for r in csv.DictReader(text,delimiter='\t'):
   if r.get('tag') not in lookup_tags:continue
   item={'tag':r.get('tag',''),'version':r.get('version',''),'custom':r.get('custom',''),'abstract':r.get('abstract',''),'datatype':r.get('datatype',''),'iord':r.get('iord',''),'crdr':r.get('crdr',''),'tlabel':r.get('tlabel',''),'doc':re.sub(r'\s+',' ',r.get('doc','')).strip()[:450]}
   definitions[r['tag']].append(item)
 standard_definitions={t:definitions.get(t,[]) for t in sorted(target_tags)}
 custom_semantic=[]
 for group,keys in semantic_pre.items():
  for tag,stmt,version,label in keys:
   defs=definitions.get(tag,[]); custom_vals={d['custom'] for d in defs}
   if '1' not in custom_vals:continue
   filing_ids=sorted({r['adsh'] for r in form_rows if (r['adsh'],tag) in pre_map and stmt in pre_map[(r['adsh'],tag)]})
   custom_semantic.append({'tag':tag,'group_label_hits':[g for g,ks in semantic_pre.items() if (tag,stmt,version,label) in ks],'stmt':stmt,'presentation_version':version,'original_pre_label':label,'custom_flags_in_tag_txt':sorted(custom_vals),'filing_count':len(filing_ids),'sample_accessions':filing_ids[:5],'tag_definitions':[{'version':d['version'],'custom':d['custom'],'crdr':d['crdr'],'tlabel':d['tlabel'],'doc':d['doc']} for d in defs[:3]],'interpretation':'semantic search candidate only; no mapping or interchangeability asserted'})
 custom_semantic.sort(key=lambda x:(x['group_label_hits'],x['tag'],x['stmt'],x['presentation_version'],x['original_pre_label']))
 # Filing counts per target tag and statement.
 tag_by_statement={}
 for tag in sorted(target_tags):
  st=tag_stats[tag]
  tag_by_statement[tag]={'filings_with_selected_date_and_expected_qtrs':len(st['filings']),'IS_filings':len(st['IS_filings']),'BS_filings':len(st['BS_filings']),'raw_fact_rows':st['raw_fact_rows'],'expected_qtrs':'0' if tag in EQUITY+PREFERRED else '4'}
 # 899-CIK denominator, preserve absence and per-accession variations.
 per_cik=[]
 for cik in sorted(candidate_ids,key=lambda x:int(x) if x.isdigit() else 10**30):
  rows=cik_filing_map.get(cik,[]); group_counts={g:sum(bool(r['field_tags'][g]) for r in rows) for g in GROUPS}
  per_cik.append({'cik':cik,'name':rows[0]['name'] if rows else None,'annual_submission_records':sum(1 for x in annual_rows if norm_cik(x['cik'])==cik),'validated_10k_or_10ka_filings':len(rows),'current_period_date_matched_filings':sum(r['date_match']['status']=='candidate_date' for r in rows),'filings_with_field_group':group_counts,'four_flow_joint_filing_count':sum(r['four_flow_groups_joint'] for r in rows),'four_flows_plus_equity_filing_count':sum(r['four_flows_plus_any_explicit_equity'] for r in rows),'four_flows_plus_equity_plus_preferred_filing_count':sum(r['four_flows_plus_equity_plus_explicit_preferred'] for r in rows),'explicit_preferred_tag_filing_count':sum(r['explicit_preferred_tag_present'] for r in rows),'explicit_preferred_zero_filing_count':sum(r['explicit_preferred_zero_value_present'] for r in rows),'adshs':[r['adsh'] for r in rows]})
 def cik_row(cik):return next((x for x in per_cik if x['cik']==norm_cik(cik)),None)
 priority_ciks={'AAPL':'320193','MSFT':'789019','GOOG':'1652044','AMZN':'1018724'}
 priority=[]
 for label,cik in priority_ciks.items():
  c=cik_row(cik);priority.append({'label':label,'cik':norm_cik(cik),'sample_scope_status':'matched_in_bound_sample' if c and c['validated_10k_or_10ka_filings'] else 'no_annual_submission_record_in_bound_2014q1_sample','scope_note':'Absence here is limited to the bound Q1 artifact; it does not establish that the issuer had no filing outside this sample.','availability':c})
 # Five actual incomplete filings with original target-tag evidence; prefer varied missing groups.
 matched_filings=[r for r in filing_results.values() if r['date_match']['status']=='candidate_date']
 incomplete=[]
 for r in matched_filings:
  missing=[g for g in FLOW if not r['field_tags'][g]]
  present=[g for g in FLOW if r['field_tags'][g]]
  if missing and present and r['raw_candidate_facts']:incomplete.append((r,missing,present))
 missing_examples=[]
 chosen=[];chosen_adsh=set()
 for group in FLOW:
  candidates=sorted((x for x in incomplete if group in x[1] and x[0]['adsh'] not in chosen_adsh),key=lambda x:(-len(x[2]),int(x[0]['cik']) if x[0]['cik'].isdigit() else 10**30))
  if candidates:
   item=candidates[0];chosen.append(item);chosen_adsh.add(item[0]['adsh'])
 for item in sorted(incomplete,key=lambda x:(-len(x[2]),len(x[1]),int(x[0]['cik']) if x[0]['cik'].isdigit() else 10**30)):
  if len(chosen)>=5:break
  if item[0]['adsh'] not in chosen_adsh:chosen.append(item);chosen_adsh.add(item[0]['adsh'])
 for r,missing,present in chosen[:5]:
  missing_examples.append({'adsh':r['adsh'],'cik':r['cik'],'name':r['name'],'form':r['form'],'period':r['period'],'filed':r['filed'],'candidate_date':r['date_match'],'present_flow_groups':present,'missing_flow_groups':missing,'reported_candidate_tag_facts':r['raw_candidate_facts']})
 counts={
  'candidate_ciks_total':len(candidate_ids),'candidate_ciks_with_annual_submission_row':len({norm_cik(x['cik']) for x in annual_rows}),
  'annual_submission_rows_candidate_ciks':len(annual_rows),'unique_candidate_accessions':len(annual_by_adsh),
  'accessions_found_in_sec_sub':len(forms),'accessions_form_10k_or_10ka':len(form_adshs),
  'candidate_ciks_with_validated_10k_or_10ka':len(cik_filing_map),
  'candidate_ciks_with_at_least_one_near_date':sum(x['current_period_date_matched_filings']>0 for x in per_cik),
  'filings_with_candidate_date_within_7_days':sum(r['date_match']['status']=='candidate_date' for r in filing_results.values()),
  'filings_no_date_within_7_days':sum(r['date_match']['status']=='no_date_within_7_days' for r in filing_results.values()),
  'filings_no_num_date':sum(r['date_match']['status']=='no_num_date' for r in filing_results.values()),
  'four_flow_joint_filings':sum(r['four_flow_groups_joint'] for r in filing_results.values()),
  'four_flows_plus_equity_filings':sum(r['four_flows_plus_any_explicit_equity'] for r in filing_results.values()),
  'four_flows_plus_equity_plus_explicit_preferred_filings':sum(r['four_flows_plus_equity_plus_explicit_preferred'] for r in filing_results.values()),
  'explicit_preferred_tag_filings':sum(r['explicit_preferred_tag_present'] for r in filing_results.values()),
  'explicit_preferred_zero_value_filings':sum(r['explicit_preferred_zero_value_present'] for r in filing_results.values()),
  'explicit_preferred_nonzero_value_filings':sum(r['explicit_preferred_nonzero_value_present'] for r in filing_results.values())}
 started_text=started.isoformat(); finished=dt.datetime.now(dt.timezone.utc).isoformat(); elapsed=time.monotonic()-t0
 output={
  'status':'completed_small_sample_field_availability_inventory','contract_sha256':sha(cp),'input_sha256':hashes,
  'execution':{'command':f'PYTHONDONTWRITEBYTECODE=1 python3 -B {Path(__file__).name} --contract {cp.name}','runner_sha256':sha(Path(__file__)),'started_at_utc':started_text,'finished_at_utc':finished,'elapsed_seconds':round(elapsed,3),'return_code':0,'network_requests':0,'market_effect_or_factor_statistics':False},
  'scope_and_limits':{'candidate_universe_ciks':899,'sample':'bound 2014Q1 SEC filing extract only','current_date_rule':'For each SUB.period, selected the nearest NUM.ddate among all accession facts when absolute difference is <=7 calendar days; ties retained. A candidate date is a join aid, not an accepted financial date.','period_semantics':'period and fy are preserved from SUB; filings submitted in 2014Q1 often report SUB.period=2013-12-31. No calendar-year/FY substitution.','form_validation':'Form was absent from annual-submissions.csv; each accession was checked against the already-bound SEC ZIP sub.txt and only 10-K or 10-K/A rows were included.','missing_records':'No missing CIK, accession, date, tag or equity field was filled with zero or inferred from another field.','tag_policy':'Requested concepts counted by the exact listed tags only. Alternative tags are reported separately; no automatic mapping or interchangeability.','ratios_or_factor':'No ratios, operating profitability, factor values or returns computed.'},
  'counts':counts,'per_cik':per_cik,'filings':list(filing_results.values()),
  'tag_filing_counts_by_statement':tag_by_statement,'standard_tag_definitions':standard_definitions,
  'semantic_custom_tag_candidates':custom_semantic,
  'priority_company_examples':priority,'five_incomplete_filing_examples':missing_examples,
  'aggregate_group_definitions':{'revenue':'any one of exact revenue tags in list','cogs':'any one of exact cost tags in list','sga':'SellingGeneralAndAdministrativeExpense exact tag','interest':'any one of exact interest tags in list','equity':'either StockholdersEquity or CommonStockholdersEquity explicit qtrs=0 tag','preferred':'any one of three exact PreferredStock* tags with qtrs=0; absence is unknown, not zero'},
  'readback_checks':{'annual_accessions_unique':True,'form_confirmed_from_sub_txt':True,'selected_dates_within_7_days_only':True,'target_tag_facts_require_expected_qtrs':True,'per_cik_rows':len(per_cik),'periods_preserved_as_submitted':True}
 }
 dest=Path(contract['write_paths'][1]);assert not dest.exists(),'refusing to overwrite output JSON';dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 # Read-back and reconcile after writing.
 reread=json.loads(dest.read_text(encoding='utf-8'));assert len(reread['per_cik'])==899 and reread['counts']==counts
 print(json.dumps({'output':str(dest),'output_sha256':sha(dest),'counts':counts,'custom_tags':len(custom_semantic),'runner_sha256':output['execution']['runner_sha256'],'elapsed_seconds':output['execution']['elapsed_seconds']},ensure_ascii=False))
 return output

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--contract',default=str(CONTRACT_DEFAULT));a=p.parse_args();run(a.contract)
